# pervar_core.py
from __future__ import annotations
import ast, inspect, json, os, re, shutil, time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

PERVAR_TAG = "PERVAR"

# ------------------------
# Конфиг по умолчанию (+ env)
# ------------------------
DEF_SHADOW_DIR = os.getenv("PERVAR_SHADOW_DIR", ".pervar_shadow")
DEF_MAX_ENTRIES = int(os.getenv("PERVAR_MAX_ENTRIES", "1"))
DEF_MAX_DEPTH = int(os.getenv("PERVAR_MAX_DEPTH", "3"))
DEF_MAX_STR   = int(os.getenv("PERVAR_MAX_STR", "600"))

# ------------------------
# Проект и теневая копия
# ------------------------
def project_root_from(path: Path) -> Path:
    p = path.resolve()
    for parent in [p] + list(p.parents):
        if (parent / ".git").exists() or (parent / "pyproject.toml").exists() or (parent / "setup.cfg").exists():
            return parent
    return p if p.is_dir() else p.parent

def ensure_shadow_copy(src_root: Path, shadow_root: Path) -> None:
    shadow_root.mkdir(parents=True, exist_ok=True)
    marker = shadow_root / ".pervar_src"
    if not marker.exists():
        def _ignore(dirpath, names):
            bad = {".git", ".idea", ".vscode", "__pycache__", ".mypy_cache", ".pytest_cache", "venv", ".venv", shadow_root.name}
            return {n for n in names if n in bad}
        shutil.copytree(src_root, shadow_root, dirs_exist_ok=True, ignore=_ignore)
        marker.write_text(f"{src_root}\n{time.time()}", encoding="utf-8")

def shadow_path_for(original_file: Path, shadow_root: Path, project_root: Path) -> Path:
    try:
        rel = original_file.resolve().relative_to(project_root.resolve())
    except Exception:
        rel = Path("_sitepkgs") / original_file.name
    dst = shadow_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists() and original_file.exists():
        try:
            shutil.copy2(original_file, dst)
        except Exception:
            dst.write_text(original_file.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
    return dst

# ------------------------
# Безопасная свёртка значений
# ------------------------
def _brief(x: Any) -> str:
    cls = type(x).__name__
    try:
        rid = hex(id(x))
    except Exception:
        rid = "<?>"
    try:
        extra = f" len={len(x)}" if hasattr(x, "__len__") else ""
    except Exception:
        extra = ""
    return f"<{cls}{extra} at {rid}>"

def _safe_preview(x: Any, depth: int, max_depth: int, max_str: int) -> Any:
    if depth >= max_depth:
        return _brief(x)
    if isinstance(x, (int, float, bool)) or x is None:
        return x
    if isinstance(x, (bytes, bytearray)):
        return f"<bytes len={len(x)}>"
    if isinstance(x, str):
        return x if len(x) <= max_str else x[:max_str] + f"... <{len(x)-max_str} more>"
    if isinstance(x, dict):
        out, n = {}, 0
        for k, v in x.items():
            if n >= 50:
                out["<...>"] = f"{len(x)-50} more"
                break
            out[str(k)] = _safe_preview(v, depth+1, max_depth, max_str)
            n += 1
        return out
    if isinstance(x, (list, tuple, set, frozenset)):
        seq = list(x)
        out = [_safe_preview(v, depth+1, max_depth, max_str) for v in seq[:50]]
        if len(seq) > 50:
            out.append(f"<{len(seq)-50} more>")
        return out if not isinstance(x, tuple) else {"__tuple__": out}
    # array-like
    try:
        import numpy as _np
        if isinstance(x, _np.ndarray):
            return {"__ndarray__": True, "shape": list(x.shape), "dtype": str(x.dtype)}
    except Exception:
        pass
    if hasattr(x, "shape") and hasattr(x, "dtype"):
        try:
            return {"__array_like__": True, "shape": list(x.shape), "dtype": str(x.dtype)}
        except Exception:
            return _brief(x)
    return _brief(x)

def snapshot_dict(d: Dict[str, Any], max_depth: int = DEF_MAX_DEPTH, max_str: int = DEF_MAX_STR) -> Dict[str, Any]:
    out = {}
    for k, v in d.items():
        if k.startswith("__"):
            continue
        try:
            out[k] = _safe_preview(v, 0, max_depth, max_str)
        except Exception as e:
            out[k] = f"<unserializable: {e}>"
    return out

# ------------------------
# Аннотирование исходников (# PERVAR [...])
# ------------------------
_PERVAR_LINE_RE = re.compile(rf"#\s*{PERVAR_TAG}\s*(\[.*\])\s*$")

def _load(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""

def _save(p: Path, s: str) -> None:
    p.write_text(s, encoding="utf-8")

def _insert_or_update(lines: List[str], def_line_idx0: int, payload: Dict[str, Any], max_entries: int) -> List[str]:
    json_compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    pervar_new_line = f"# {PERVAR_TAG} [{json_compact}]\n"
    target = def_line_idx0 + 1
    if target < len(lines):
        m = _PERVAR_LINE_RE.search(lines[target])
        if m:
            try:
                arr = json.loads(m.group(1))
                if not isinstance(arr, list):
                    arr = [arr]
            except Exception:
                arr = []
            arr.insert(0, payload)
            if max_entries > 0:
                arr = arr[:max_entries]
            merged = json.dumps(arr, ensure_ascii=False, separators=(",", ":"))
            lines[target] = f"# {PERVAR_TAG} {merged}\n"
            return lines
    lines.insert(target, pervar_new_line)
    return lines

def annotate_function_decl(source_file: Path, func_name: str, payload: Dict[str, Any], max_entries: int) -> None:
    s = _load(source_file)
    if not s:
        return
    try:
        tree = ast.parse(s)
    except SyntaxError:
        return
    target_line = None
    class V(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef):
            nonlocal target_line
            if node.name == func_name and target_line is None:
                target_line = node.lineno
        def visit_AsyncFunctionDef(self, node):
            self.visit_FunctionDef(node)
    V().visit(tree)
    if target_line is None:
        return
    lines = s.splitlines(keepends=True)
    idx0 = max(0, min(len(lines)-1, target_line-1))
    lines = _insert_or_update(lines, idx0, payload, max_entries)
    _save(source_file, "".join(lines))

# ------------------------
# Пакетный снимок для call/return
# ------------------------
def build_payload(event: str,
                  run_id: str,
                  file: Path,
                  lineno: int,
                  func: Optional[str],
                  args: Dict[str, Any],
                  locals_dict: Dict[str, Any],
                  max_depth: int = DEF_MAX_DEPTH,
                  max_str: int = DEF_MAX_STR) -> Dict[str, Any]:
    return {
        "event": event,
        "time": time.time(),
        "run_id": run_id,
        "file": str(file),
        "line": lineno,
        "func": func,
        "args": snapshot_dict(args, max_depth, max_str),
        "locals": snapshot_dict(locals_dict, max_depth, max_str),
        "pid": os.getpid(),
    }
