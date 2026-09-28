import datetime as dt
import hashlib
import json
import logging
import ntpath
import os
from pathlib import Path
import queue
import re
import socket
import sys
import tempfile
import threading
import time
from urllib.parse import urlsplit
import uuid


USE_SQLITE = object()
ENABLED = os.environ.get('MES_PG_PILOT_ENABLED', '1') != '0'
CHAT_ID = 'chat78766'
READ_BUDGET_SEC = 1.5
POOL_WAIT_SEC = 0.5
STATEMENT_TIMEOUT_MS = 700
LOCK_TIMEOUT_MS = 300

_state_lock = threading.Lock()
_attempt_lock = threading.Lock()
_disabled = False
_successes = 0
_failure = None
_notification = 'not_needed'
logger = logging.getLogger(__name__)


def get_state():
    """Локальная диагностика без обращения к базам/сети."""
    with _state_lock:
        return {
            'enabled': ENABLED,
            'sqlite_only': _disabled,
            'postgres_successes': _successes,
            'notification': _notification,
            'failure': dict(_failure) if _failure else None,
        }


def _safe_text(value):
    text = str(value).splitlines()[0] if str(value) else ''
    text = re.sub(r'\b(?:postgres(?:ql)?|https?)://\S+', '<URL скрыт>', text,
                  flags=re.IGNORECASE)
    text = re.sub(r"(?i)\b(password|pwd|token|secret)\s*[=:]\s*(?:'[^']*'|\"[^\"]*\"|\S+)",
                  r'\1=<скрыто>', text)
    return text.replace('[', '(').replace(']', ')')[:500]


def _error_summary(exc):
    parts, seen = [], set()
    while exc is not None and id(exc) not in seen and len(parts) < 4:
        seen.add(id(exc))
        state = getattr(exc, 'sqlstate', None)
        label = type(exc).__name__ + (f' SQLSTATE={state}' if state else '')
        parts.append(f'{label}: {_safe_text(exc)}')
        exc = exc.__cause__ or exc.__context__
    return ' <- '.join(parts)


def _webhook_url():
    base = os.environ.get('MES_PG_PILOT_B24_WEBHOOK', '').strip().rstrip('/')
    parsed = urlsplit(base)
    if parsed.scheme != 'https' or not parsed.netloc or not parsed.path.startswith('/rest/'):
        raise RuntimeError('Задайте MES_PG_PILOT_B24_WEBHOOK: HTTPS URL входящего вебхука Б24')
    return base + '/im.message.add.json'


def _report(event):
    global _notification
    report_path = None
    try:
        folder = Path(os.environ.get('LOCALAPPDATA') or tempfile.gettempdir()) / 'mes_pg_pilot'
        folder.mkdir(parents=True, exist_ok=True)
        report_path = folder / f"fallback-{os.getpid()}-{event['id']}.json"
        report_path.write_text(json.dumps(event, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        logger.error('PG pilot: не удалось сохранить локальный отчёт')
    status, notification_error = 'failed', ''
    try:
        import requests
        message = (
            '[B]MES: PostgreSQL → SQLite[/B]\n'
            f"Событие: {event['id']}\nUTC: {event['utc']}\n"
            f"Пользователь: {event['user']}\nПК: {event['host']}\n"
            f"Приложение: {event['app']}; PID: {event['pid']}\n"
            f"База: {event['database']}; запрос: {event['query_id']}\n"
            f"Причина: {event['error']}\n"
            'Пилот отключён до перезапуска процесса; текущий запрос направлен в SQLite.'
        )
        with requests.post(
            _webhook_url(),
            json={'DIALOG_ID': CHAT_ID, 'MESSAGE': message, 'URL_PREVIEW': 'N'},
            timeout=(2, 3), allow_redirects=False,
        ) as response:
            if response.status_code != 200:
                raise RuntimeError(f'HTTP {response.status_code}')
            data = response.json()
            if not isinstance(data, dict):
                raise RuntimeError('Б24 вернул неожиданный формат ответа')
            if data.get('error'):
                raise RuntimeError(f"Б24: {_safe_text(data['error'])}")
            if type(data.get('result')) is not int or data['result'] <= 0:
                raise RuntimeError('Б24 не вернул идентификатор сообщения')
        status = 'sent'
    except Exception as exc:
        notification_error = _error_summary(exc)
        logger.error('PG pilot: уведомление Б24 не подтверждено (%s)', type(exc).__name__)
    finally:
        with _state_lock:
            _notification = status
        if report_path is not None:
            try:
                report_path.write_text(json.dumps(dict(event, notification=status,
                                                      notification_error=notification_error),
                                                 ensure_ascii=False, indent=2), encoding='utf-8')
            except Exception:
                pass


def _trip(exc, bd, sql):
    global _disabled, _failure, _notification
    with _state_lock:
        if _disabled:
            return
        _disabled = True
        event = {
            'id': uuid.uuid4().hex[:12],
            'utc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'user': _safe_text(os.environ.get('USERNAME') or os.environ.get('USER') or 'unknown'),
            'host': _safe_text(socket.gethostname()),
            'app': _safe_text(ntpath.basename(sys.argv[0] or sys.executable)),
            'pid': os.getpid(),
            'database': _safe_text(getattr(bd, 'alias', ntpath.basename(str(bd)))),
            'query_id': hashlib.sha256(sql.encode('utf-8')).hexdigest()[:12],
            'error': _error_summary(exc),
        }
        _failure, _notification = event, 'pending'
    try:
        threading.Thread(target=_report, args=(event,), name='mes-pg-pilot-report', daemon=True).start()
    except Exception:
        with _state_lock:
            _notification = 'failed'


def _read(pg, bd, sql, options, reply):
    try:
        _webhook_url()
        if pg is None:
            raise ImportError('Cust_postgresql_executor недоступен')
        try:
            executor = pg.get_default_executor()
        except pg.PostgresConfigurationError:
            executor = pg.configure_default_runtime(
                pg.ExecutorConfig.from_env(), schema_map=pg.SchemaRegistry.from_env(),
            )
        with executor.transaction(bd, attach_dbs=options.get('attach_dbs', ()),
                                  read_only=True, timeout_sec=POOL_WAIT_SEC) as tx:
            tx.custom_request_c(
                "SELECT set_config('statement_timeout', %s, true), "
                "set_config('lock_timeout', %s, true)",
                list_of_lists_c=[f'{STATEMENT_TIMEOUT_MS}ms', f'{LOCK_TIMEOUT_MS}ms'],
            )
            result = tx.custom_request_c(sql, **{
                key: options[key] for key in
                ('hat_c', 'list_of_lists_c', 'rez_dict', 'one', 'one_column') if key in options
            })
        reply.put((True, result))
    except Exception as exc:
        reply.put((False, exc))


def try_read(pg, bd, sql, *, conn='', cur='', **options):
    """Возвращает PG-результат или USE_SQLITE. Только самостоятельные SELECT.

    None/False/0/пустые коллекции не считаются ошибками SQL.
    Внешняя транзакция/курсор остаётся в исходном SQLite-пути.
    """
    global _successes
    if not ENABLED or conn not in ('', None, False) or cur not in ('', None, False):
        return USE_SQLITE
    if not isinstance(sql, str) or not re.match(r'^\s*SELECT\b', sql, re.IGNORECASE):
        return USE_SQLITE
    with _state_lock:
        if _disabled:
            return USE_SQLITE
    deadline = time.monotonic() + READ_BUDGET_SEC
    acquired = _attempt_lock.acquire(timeout=READ_BUDGET_SEC)
    try:
        if not acquired:
            raise TimeoutError('Истёк срок ожидания очереди пилотного чтения')
        with _state_lock:
            if _disabled:
                return USE_SQLITE
        reply = queue.Queue(maxsize=1)
        threading.Thread(target=_read, args=(pg, bd, sql, options, reply),
                         name='mes-pg-pilot-read', daemon=True).start()
        try:
            ok, value = reply.get(timeout=max(0, deadline - time.monotonic()))
        except queue.Empty:
            raise TimeoutError(f'Пилотное чтение превысило {READ_BUDGET_SEC} с') from None
        if time.monotonic() > deadline:
            raise TimeoutError(f'Пилотное чтение превысило {READ_BUDGET_SEC} с')
        if not ok:
            raise value
        with _state_lock:
            if _disabled:
                return USE_SQLITE
            _successes += 1
        return value
    except Exception as exc:
        _trip(exc, bd, sql)
        return USE_SQLITE
    finally:
        if acquired:
            _attempt_lock.release()
