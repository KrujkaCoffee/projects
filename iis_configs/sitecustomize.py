# sitecustomize.py
"""
Автоподключение PERVAR-трейсера.
Включается, если PERVAR_ENABLE=1 (или если обнаружен pydevd — можно выставить PERVAR_AUTO=1).
Фильтрует кадры по PERVAR_PROJECT_ROOT и/или PERVAR_INCLUDE/PERVAR_EXCLUDE.
Пишет # PERVAR [...] в теневую копию проекта после строк def функций (с «скользящим окном» записей).
"""
from __future__ import annotations
import os, re, sys, time, inspect
from pathlib import Path
from typing import Optional, Dict

# — ранняя проверка —
ENABLE = os.getenv("PERVAR_ENABLE", "0") == "1"
AUTO    = os.getenv("PERVAR_AUTO", "1") == "1"  # если в sys.modules есть pydevd — авто-вкл
if not ENABLE and AUTO and "pydevd" in sys.modules:
    ENABLE = True
if not ENABLE:
    # Не включаемся – позволяем обычной загрузке продолжиться
    raise SystemExit  # важно: НЕ падаем запуск; просто выходим из sitecustomize без трейсера

# Импорт ядра (должно быть в PYTHONPATH)
try:
    import pervar_core as core
except Exception as e:
    print(f"[pervar] failed to import pervar_core: {e}", file=sys.stderr)
    raise SystemExit

# ------------------------
# Конфиг
# ------------------------
PROJECT_ROOT = Path(os.getenv("PERVAR_PROJECT_ROOT", "") or core.project_root_from(Path.cwd()))
SHADOW_DIR   = Path(os.getenv("PERVAR_SHADOW_DIR", core.DEF_SHADOW_DIR))
MAX_ENTRIES  = int(os.getenv("PERVAR_MAX_ENTRIES", str(core.DEF_MAX_ENTRIES)))
MAX_DEPTH    = int(os.getenv("PERVAR_MAX_DEPTH",   str(core.DEF_MAX_DEPTH)))
MAX_STR      = int(os.getenv("PERVAR_MAX_STR",     str(core.DEF_MAX_STR)))
INCLUDE_RE   = re.compile(os.getenv("PERVAR_INCLUDE", "")) if os.getenv("PERVAR_INCLUDE") else None
EXCLUDE_RE   = re.compile(os.getenv("PERVAR_EXCLUDE", "")) if os.getenv("PERVAR_EXCLUDE") else None
RATE_LIMIT_HZ= float(os.getenv("PERVAR_RATE_HZ", "0"))   # 0 = без ограничения
SAMPLE       = float(os.getenv("PERVAR_SAMPLE", "1.0"))  # 0..1 выборочное логирование
MAX_FUNCS    = int(os.getenv("PERVAR_MAX_FUNCS", "0"))   # 0 = без лимита по числу функций за процесс
RUN_ID       = os.getenv("PERVAR_RUN_ID") or time.strftime("%Y%m%d-%H%M%S")

core.ensure_shadow_copy(PROJECT_ROOT, SHADOW_DIR)

# ------------------------
# Вспомогательные
# ------------------------
def _inside_project(filename: str) -> bool:
    try:
        p = Path(filename).resolve()
    except Exception:
        return False
    if not str(p).startswith(str(PROJECT_ROOT.resolve())):
        return False
    s = str(p)
    if INCLUDE_RE and not INCLUDE_RE.search(s):
        return False
    if EXCLUDE_RE and EXCLUDE_RE.search(s):
        return False
    # Отсеиваем саму тень и служебное
    if SHADOW_DIR.resolve() in p.parents:
        return False
    if any(part in {".venv", "venv", "__pycache__"} for part in p.parts):
        return False
    return True

_last_emit_ts = 0.0
_emitted_funcs = 0

def _rate_ok() -> bool:
    global _last_emit_ts
    if RATE_LIMIT_HZ <= 0:
        return True
    now = time.perf_counter()
    if now - _last_emit_ts >= 1.0 / RATE_LIMIT_HZ:
        _last_emit_ts = now
        return True
    return False

def _sample_ok() -> bool:
    import random
    return random.random() <= SAMPLE

# ------------------------
# Основной трейс
# ------------------------
def _tracer(frame, event, arg):
    global _emitted_funcs
    # фильтр файла
    code = frame.f_code
    filename = code.co_filename
    # if not _inside_project(filename):
    #     return _tracer  # продолжаем вглубь, но сами ничего не пишем
    func_name = code.co_name
    # Лимиты/сэмплинг
    if MAX_FUNCS and _emitted_funcs >= MAX_FUNCS:
        return _tracer
    if not _sample_ok() or not _rate_ok():
        return _tracer

    try:
        src_file = Path(filename)
        shadow_file = core.shadow_path_for(src_file, SHADOW_DIR, PROJECT_ROOT)
        defline = None
        try:
            # точная строка def из исходника
            defline = inspect.getsourcelines(frame.f_code)[1]
        except Exception:
            defline = frame.f_lineno

        if event == "call":
            # Аргументы функции возможны в frame.f_locals уже на call
            args_payload = {}
            try:
                # робко: забрать только имена первых co_argcount + kwonly
                varnames = code.co_varnames[: code.co_argcount + code.co_kwonlyargcount]
                for name in varnames:
                    if name in frame.f_locals:
                        args_payload[name] = frame.f_locals[name]
            except Exception:
                pass
            payload = core.build_payload(
                event="call",
                run_id=RUN_ID,
                file=src_file,
                lineno=defline,
                func=func_name,
                args=args_payload,
                locals_dict={},
                max_depth=MAX_DEPTH,
                max_str=MAX_STR,
            )
            core.annotate_function_decl(shadow_file, func_name, payload, MAX_ENTRIES)
            _emitted_funcs += 1
            return _tracer

        if event == "return":
            # На return локалы доступны полностью
            locals_payload = dict(frame.f_locals)
            # Добавим результат если доступен через arg
            try:
                locals_payload["<result>"] = arg
            except Exception:
                pass
            args_payload = {}
            try:
                varnames = code.co_varnames[: code.co_argcount + code.co_kwonlyargcount]
                for name in varnames:
                    if name in frame.f_locals:
                        args_payload[name] = frame.f_locals[name]
            except Exception:
                pass
            payload = core.build_payload(
                event="return",
                run_id=RUN_ID,
                file=src_file,
                lineno=defline,
                func=func_name,
                args=args_payload,
                locals_dict=locals_payload,
                max_depth=MAX_DEPTH,
                max_str=MAX_STR,
            )
            core.annotate_function_decl(shadow_file, func_name, payload, MAX_ENTRIES)
            _emitted_funcs += 1
            return _tracer

        # другие события (line, exception) пока игнорируем ради скорости
        return _tracer
    except Exception as e:
        # Не ломаем пользовательский ран — молча даунгрейдимся
        # print(f"[pervar] tracer error: {e}", file=sys.stderr)
        return _tracer

# Включаем трейсер максимально рано
sys.settrace(_tracer)
# Важно: также для уже импортированных потоков (PyQt может спаунить)
import threading
def _settrace_for_thread():
    sys.settrace(_tracer)
threading.settrace(_tracer)
