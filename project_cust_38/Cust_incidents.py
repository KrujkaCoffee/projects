from __future__ import annotations

import atexit
import dataclasses
import enum
import getpass
import hashlib
import importlib
import json
import os
import re
import socket
import ssl
import sys
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


SCHEMA_VERSION = 1
GROUP_MARKER_PREFIX = "MES-INCIDENT"


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "да"}


def _env_int(name: str) -> int | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _env_ids(name: str) -> tuple[int, ...]:
    result: list[int] = []
    for item in os.getenv(name, "").split(","):
        try:
            value = int(item.strip())
        except (TypeError, ValueError):
            continue
        if value > 0 and value not in result:
            result.append(value)
    return tuple(result)


class IncidentMode(str, enum.Enum):
    OFF = "off"
    COLLECT = "collect"
    SILENT_TEST = "silent_test"
    PRODUCTION = "production"

    @classmethod
    def parse(cls, value: str | IncidentMode | None) -> IncidentMode:
        if isinstance(value, cls):
            return value
        normalized = str(value or "collect").strip().lower().replace("-", "_")
        aliases = {
            "0": cls.OFF,
            "disabled": cls.OFF,
            "1": cls.COLLECT,
            "test": cls.SILENT_TEST,
            "silent": cls.SILENT_TEST,
            "prod": cls.PRODUCTION,
        }
        if normalized in aliases:
            return aliases[normalized]
        try:
            return cls(normalized)
        except ValueError:
            return cls.COLLECT

    @property
    def creates_tasks(self) -> bool:
        return self in {self.SILENT_TEST, self.PRODUCTION}


@dataclasses.dataclass
class IncidentConfig:
    shared_root: Path = Path(r"Z:\MES_setup\errors\incidents")
    local_root: Path = dataclasses.field(
        default_factory=lambda: Path(tempfile.gettempdir()) / "mes_incidents"
    )
    mode: IncidentMode = IncidentMode.COLLECT
    b24_url: str = ""
    b24_responsible_id: int | None = None
    b24_test_user_id: int | None = None
    b24_created_by_id: int | None = None
    b24_auditors: tuple[int, ...] = ()
    allow_legacy_b24_url: bool = True
    verify_tls: bool = False
    request_timeout_sec: float = 8.0
    b24_batch_size: int = 5
    b24_retry_base_sec: float = 15.0
    flush_interval_sec: float = 20.0
    lock_timeout_sec: float = 8.0
    lock_stale_sec: float = 600.0
    raw_trace_limit: int = 256_000
    capture_qt_critical: bool = True
    capture_native_faults: bool = True
    debug: bool = False


@dataclasses.dataclass
class IncidentContext:
    app_name: str = "app"
    version: str = "-"
    user: str = ""
    computer: str = ""
    b24_user_id: int | None = None
    session_user: str = ""

    def __post_init__(self) -> None:
        if not self.session_user:
            try:
                self.session_user = getpass.getuser()
            except Exception:
                self.session_user = (
                    os.getenv("USERNAME") or os.getenv("USER") or "unknown"
                )
        if not self.user:
            self.user = self.session_user
        if not self.computer:
            try:
                self.computer = socket.gethostname()
            except Exception:
                self.computer = os.getenv("COMPUTERNAME") or "unknown"


@dataclasses.dataclass(frozen=True)
class FrameInfo:
    file: str
    function: str
    line: int | None = None
    code: str = ""

    @classmethod
    def from_summary(cls, frame: traceback.FrameSummary) -> FrameInfo:
        return cls(
            file=str(frame.filename),
            function=str(frame.name),
            line=int(frame.lineno) if frame.lineno else None,
            code=str(frame.line or ""),
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> FrameInfo:
        return cls(
            file=str(data.get("file") or ""),
            function=str(data.get("function") or ""),
            line=data.get("line"),
            code=str(data.get("code") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class IncidentPayload:
    app_name: str
    version: str
    timestamp: str
    user: str
    computer: str
    exception_type: str
    exception_message: str
    frames: list[FrameInfo]
    source: str
    handled: bool
    decorated_function: str = ""
    raw_trace: str = ""
    b24_user_id: int | None = None
    session_user: str = ""

    def __post_init__(self) -> None:
        if not self.session_user:
            self.session_user = self.user

    @property
    def root_frame(self) -> FrameInfo | None:
        return self.frames[-1] if self.frames else None

    @property
    def root_file(self) -> str:
        frame = self.root_frame
        return Path(frame.file.replace("\\", "/")).name if frame else ""

    @property
    def root_function(self) -> str:
        frame = self.root_frame
        return frame.function if frame else self.decorated_function

    @property
    def root_line(self) -> int | None:
        return self.root_frame.line if self.root_frame else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "app_name": self.app_name,
            "version": self.version,
            "timestamp": self.timestamp,
            "user": self.user,
            "computer": self.computer,
            "exception_type": self.exception_type,
            "exception_message": self.exception_message,
            "frames": [frame.to_dict() for frame in self.frames],
            "source": self.source,
            "handled": self.handled,
            "decorated_function": self.decorated_function,
            "raw_trace": self.raw_trace,
            "b24_user_id": self.b24_user_id,
            "session_user": self.session_user,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> IncidentPayload:
        return cls(
            app_name=str(data.get("app_name") or "app"),
            version=str(data.get("version") or "-"),
            timestamp=str(data.get("timestamp") or _now()),
            user=str(data.get("user") or "unknown"),
            computer=str(data.get("computer") or "unknown"),
            exception_type=str(data.get("exception_type") or "Exception"),
            exception_message=str(data.get("exception_message") or ""),
            frames=[FrameInfo.from_dict(item) for item in data.get("frames") or []],
            source=str(data.get("source") or "python"),
            handled=bool(data.get("handled")),
            decorated_function=str(data.get("decorated_function") or ""),
            raw_trace=str(data.get("raw_trace") or ""),
            b24_user_id=data.get("b24_user_id"),
            session_user=str(data.get("session_user") or data.get("user") or ""),
        )


@dataclasses.dataclass(frozen=True)
class IncidentIds:
    group_hash: str
    case_hash: str

    @property
    def marker(self) -> str:
        return f"[{GROUP_MARKER_PREFIX}:{self.group_hash[:12]}]"

    def to_dict(self) -> dict[str, str]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> IncidentIds:
        return cls(
            group_hash=str(data["group_hash"]),
            case_hash=str(data["case_hash"]),
        )


@dataclasses.dataclass
class RegisterResult:
    ids: IncidentIds
    root: Path
    group_dir: Path
    marker: dict[str, Any]
    is_new_group: bool
    is_new_case: bool
    is_new_user: bool
    duplicate_event: bool = False


@dataclasses.dataclass
class CaptureReceipt:
    ids: IncidentIds
    event_id: str
    pending_path: Path | None = None
    local_result: RegisterResult | None = None
    error: str = ""


class IncidentLockTimeout(TimeoutError):
    pass


class IncidentUtils:
    _WIN_USER = re.compile(r"(?i)([A-Z]:[/\\]Users[/\\])([^/\\]+)")
    _TEMP = re.compile(
        r"(?i)([A-Z]:[/\\]Users[/\\](?:\{USER\}|[^/\\]+)[/\\]"
        r"AppData[/\\]Local[/\\]Temp[/\\])[^ \n\r\t'\"]+"
    )
    _HEX = re.compile(r"(?i)0x[0-9a-f]+")
    _UUID = re.compile(
        r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
        r"[0-9a-f]{4}-[0-9a-f]{12}\b"
    )
    _DATETIME = re.compile(
        r"\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?"
    )
    _LONG_NUMBER = re.compile(r"\b\d{7,}\b")
    _LINE_REFERENCE = re.compile(r"(?i)(\bline\s+)\d+")
    _B24_SECRET = re.compile(r"(?i)(/rest/)\d+/[^/\s]+/")
    _BEARER = re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+")
    _KEY_SECRET = re.compile(
        r"(?i)(password|passwd|token|api[_-]?key|secret)(\s*[:=]\s*)"
        r"([^\s,;'\"]+)"
    )
    _SOURCE_RECEIVER = re.compile(r"(receiver=[^ (]+)\([^)]*\)")
    _SOURCE_OBJECT = re.compile(r"(unraisablehook)\s+object=.*", re.IGNORECASE)

    @staticmethod
    def stable_json(data: Any) -> str:
        return json.dumps(
            data,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

    @classmethod
    def digest(cls, data: Any) -> str:
        return hashlib.sha256(cls.stable_json(data).encode("utf-8")).hexdigest()

    @classmethod
    def redact(cls, value: Any) -> str:
        text = str(value if value is not None else "")
        text = cls._B24_SECRET.sub(r"\1{ID}/{TOKEN}/", text)
        text = cls._BEARER.sub(r"\1{TOKEN}", text)
        return cls._KEY_SECRET.sub(r"\1\2{SECRET}", text)

    @classmethod
    def normalize(cls, value: Any, app_root: str = "") -> str:
        text = cls.redact(value).replace("\\", "/")
        if app_root:
            normalized_root = str(app_root).replace("\\", "/").rstrip("/")
            if normalized_root:
                text = text.replace(normalized_root, "{APP_ROOT}")
        try:
            home = str(Path.home()).replace("\\", "/").rstrip("/")
            if home:
                text = re.sub(re.escape(home), "{HOME}", text, flags=re.IGNORECASE)
        except Exception:
            pass
        text = cls._WIN_USER.sub(r"\1{USER}", text)
        text = cls._TEMP.sub("{TEMP_FILE}", text)
        text = text.replace("Z:/", "{MES_ROOT}/")
        text = cls._HEX.sub("0x{HEX}", text)
        text = cls._UUID.sub("{UUID}", text)
        text = cls._DATETIME.sub("{DATETIME}", text)
        return text.strip()

    @classmethod
    def normalize_message(cls, value: Any, app_root: str = "") -> str:
        text = cls._LONG_NUMBER.sub("{NUM}", cls.normalize(value, app_root))
        return cls._LINE_REFERENCE.sub(r"\1{LINE}", text)

    @classmethod
    def normalize_source(cls, value: Any) -> str:
        text = cls.normalize_message(value)
        text = cls._SOURCE_RECEIVER.sub(r"\1", text)
        text = cls._SOURCE_OBJECT.sub(r"\1 object={OMITTED}", text)
        return text[:240]

    @classmethod
    def safe_part(cls, value: Any, default: str = "unknown", limit: int = 96) -> str:
        text = re.sub(r"[^\w.\-]+", "_", cls.normalize(value), flags=re.UNICODE)
        return text.strip("_")[:limit] or default

    @classmethod
    def stable_frame_path(cls, value: Any, depth: int = 4) -> str:
        normalized = cls.normalize(value).replace("\\", "/")
        parts = [part for part in normalized.split("/") if part and part != "."]
        return "/".join(parts[-depth:]).lower()

    @classmethod
    def frame_for_hash(cls, frame: FrameInfo, with_line: bool) -> dict[str, Any]:
        result: dict[str, Any] = {
            "file": cls.stable_frame_path(frame.file),
            "function": frame.function,
        }
        if with_line:
            result["line"] = frame.line
        return result

    @classmethod
    def build_ids(cls, payload: IncidentPayload) -> IncidentIds:
        group_data = {
            "app": Path(payload.app_name.replace("\\", "/")).name.lower(),
            "exception_type": payload.exception_type,
            "exception_message": cls.normalize_message(payload.exception_message),
            "root": {
                "file": payload.root_file.lower(),
                "function": payload.root_function,
            },
            "frames": [cls.frame_for_hash(frame, False) for frame in payload.frames],
        }
        case_data = {
            **group_data,
            "version": payload.version,
            "frames": [cls.frame_for_hash(frame, True) for frame in payload.frames],
        }
        return IncidentIds(
            group_hash=cls.digest(group_data),
            case_hash=cls.digest(case_data),
        )


def _atomic_write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.tmp.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}"
    )
    try:
        with open(temporary, "w", encoding="utf-8", errors="backslashreplace") as file:
            json.dump(data, file, ensure_ascii=False, indent=2, default=str)
            file.flush()
            os.fsync(file.fileno())
        os.replace(str(temporary), str(path))
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except Exception:
            pass


def _read_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Ожидался JSON-объект: {path}")
    return data


def _append_jsonl(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", errors="backslashreplace") as file:
        file.write(IncidentUtils.stable_json(data) + "\n")
        file.flush()
        os.fsync(file.fileno())


class ExclusiveFileLock:

    def __init__(self, path: Path, timeout: float, stale_after: float):
        self.path = path
        self.timeout = max(0.0, timeout)
        self.stale_after = max(1.0, stale_after)
        self.token = uuid.uuid4().hex
        self.acquired = False

    def _try_remove_stale(self) -> None:
        try:
            stat = self.path.stat()
            if time.time() - stat.st_mtime <= self.stale_after:
                return
            before = self.path.read_text(encoding="utf-8", errors="ignore")
            if self.path.read_text(encoding="utf-8", errors="ignore") != before:
                return
            self.path.unlink(missing_ok=True)
        except Exception:
            return

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        while True:
            try:
                fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as file:
                        json.dump(
                            {
                                "token": self.token,
                                "pid": os.getpid(),
                                "thread": threading.get_ident(),
                                "created_at": _now(),
                            },
                            file,
                        )
                        file.flush()
                        os.fsync(file.fileno())
                except Exception:
                    try:
                        os.close(fd)
                    except Exception:
                        pass
                    try:
                        self.path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    raise
                self.acquired = True
                return
            except FileExistsError:
                self._try_remove_stale()
                if time.monotonic() - started >= self.timeout:
                    raise IncidentLockTimeout(f"Не удалось получить lock: {self.path}")
                time.sleep(0.05)

    def release(self) -> None:
        if not self.acquired:
            return
        try:
            owner = _read_json(self.path)
            if owner.get("token") == self.token:
                self.path.unlink(missing_ok=True)
        except Exception:
            pass
        finally:
            self.acquired = False

    def __enter__(self) -> ExclusiveFileLock:
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb) -> None:
        self.release()


class IncidentStore:
    def __init__(self, config: IncidentConfig):
        self.config = config

    def group_dir(self, root: Path, group_hash: str) -> Path:
        return root / "groups" / group_hash[:2] / group_hash

    def marker_path(self, root: Path, group_hash: str) -> Path:
        return self.group_dir(root, group_hash) / "marker.json"

    def pending_dir(self) -> Path:
        return self.config.local_root / "pending"

    def outbox_dir(self) -> Path:
        return self.config.shared_root / "outbox"

    def spool(self, payload: IncidentPayload, ids: IncidentIds, event_id: str) -> Path:
        path = self.pending_dir() / f"{event_id}.json"
        payload_data = payload.to_dict()
        payload_data["exception_message"] = IncidentUtils.redact(
            payload_data.get("exception_message", "")
        )[:4000]
        payload_data["raw_trace"] = IncidentUtils.redact(
            payload_data.get("raw_trace", "")
        )[: self.config.raw_trace_limit]
        payload_data["source"] = IncidentUtils.normalize_source(
            payload_data.get("source", "")
        )
        payload_data["decorated_function"] = str(
            payload_data.get("decorated_function") or ""
        )[:240]
        for frame in payload_data.get("frames") or []:
            frame["file"] = IncidentUtils.normalize(frame.get("file", ""))
            frame["code"] = IncidentUtils.redact(frame.get("code", ""))[:500]
        _atomic_write_json(
            path,
            {
                "schema": SCHEMA_VERSION,
                "event_id": event_id,
                "ids": ids.to_dict(),
                "payload": payload_data,
            },
        )
        return path

    def register(
        self,
        root: Path,
        payload: IncidentPayload,
        ids: IncidentIds,
        event_id: str,
    ) -> RegisterResult:
        group_dir = self.group_dir(root, ids.group_hash)
        group_dir.mkdir(parents=True, exist_ok=True)
        lock = ExclusiveFileLock(
            group_dir / ".lock",
            timeout=self.config.lock_timeout_sec,
            stale_after=self.config.lock_stale_sec,
        )
        with lock:
            event_path = group_dir / "events" / f"{event_id}.json"
            marker_path = group_dir / "marker.json"
            if event_path.exists():
                try:
                    marker = _read_json(marker_path) if marker_path.exists() else {}
                    if marker.get("group_hash"):
                        return RegisterResult(
                            ids=ids,
                            root=root,
                            group_dir=group_dir,
                            marker=marker,
                            is_new_group=False,
                            is_new_case=False,
                            is_new_user=False,
                            duplicate_event=True,
                        )
                except Exception:
                    pass
                self._move_aside(event_path, group_dir / "events_orphan")

            marker: dict[str, Any] = {}
            if marker_path.exists():
                try:
                    marker = _read_json(marker_path)
                except Exception:
                    self._move_aside(marker_path, group_dir / "corrupt")
                    marker = {}
            is_new_group = not bool(marker.get("group_hash"))
            if is_new_group:
                marker = self._new_marker(payload, ids)

            users = marker.setdefault("affected_users", {})
            cases = marker.setdefault("cases", {})
            versions = marker.setdefault("versions", {})
            sources = marker.setdefault("sources", {})

            user_identity = payload.session_user or payload.user or "unknown"
            user_key = f"session:{user_identity.casefold()}"
            is_new_user = user_key not in users
            user_data = users.setdefault(
                user_key,
                {
                    "user": user_key,
                    "computer": payload.computer,
                    "first_seen": payload.timestamp,
                    "last_seen": payload.timestamp,
                    "hits": 0,
                },
            )
            user_data["computer"] = payload.computer
            user_data["user"] = payload.user or user_data.get("user") or "unknown"
            user_data["last_seen"] = payload.timestamp
            user_data["hits"] = int(user_data.get("hits") or 0) + 1
            if payload.b24_user_id:
                user_data["b24_user_id"] = payload.b24_user_id

            case_path = group_dir / "cases" / f"{ids.case_hash}.json"
            is_new_case = not case_path.exists()
            case_data = cases.setdefault(
                ids.case_hash,
                {
                    "case_hash": ids.case_hash,
                    "version": payload.version,
                    "root_line": payload.root_line,
                    "first_seen": payload.timestamp,
                    "last_seen": payload.timestamp,
                    "hits": 0,
                },
            )
            case_data["last_seen"] = payload.timestamp
            case_data["hits"] = int(case_data.get("hits") or 0) + 1

            versions[payload.version] = int(versions.get(payload.version) or 0) + 1
            source_key = IncidentUtils.normalize_source(payload.source) or "unknown"
            sources[source_key] = int(sources.get(source_key) or 0) + 1

            marker["last_seen"] = payload.timestamp
            marker["hits_count"] = int(marker.get("hits_count") or 0) + 1
            marker["users_count"] = len(users)
            marker["cases_count"] = len(cases)
            if payload.b24_user_id and not marker.get("first_b24_user_id"):
                marker["first_b24_user_id"] = payload.b24_user_id

            if is_new_case:
                _atomic_write_json(case_path, self._case_record(payload, ids))

            raw_path = ""
            if is_new_case:
                raw_path = self._write_raw_trace(group_dir, payload, ids, event_id)
            _append_jsonl(
                group_dir / "hits.jsonl",
                {
                    "schema": SCHEMA_VERSION,
                    "event_id": event_id,
                    "timestamp": payload.timestamp,
                    "user": payload.user,
                    "computer": payload.computer,
                    "version": payload.version,
                    "source": source_key,
                    "handled": payload.handled,
                    "case_hash": ids.case_hash,
                    "raw_trace": raw_path,
                },
            )
            _atomic_write_json(marker_path, marker)
            _atomic_write_json(
                event_path,
                {
                    "event_id": event_id,
                    "timestamp": payload.timestamp,
                    "case_hash": ids.case_hash,
                },
            )

        return RegisterResult(
            ids=ids,
            root=root,
            group_dir=group_dir,
            marker=marker,
            is_new_group=is_new_group,
            is_new_case=is_new_case,
            is_new_user=is_new_user,
        )

    @staticmethod
    def _move_aside(path: Path, folder: Path) -> None:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / f"{path.name}.{int(time.time())}.{uuid.uuid4().hex}.bak"
            os.replace(str(path), str(target))
        except Exception:
            pass

    def _new_marker(self, payload: IncidentPayload, ids: IncidentIds) -> dict[str, Any]:
        location = ".".join(part for part in (payload.root_file, payload.root_function) if part)
        title = f"[{payload.app_name}] {payload.exception_type}"
        if location:
            title += f" в {location}"
        return {
            "schema": SCHEMA_VERSION,
            "group_hash": ids.group_hash,
            "marker": ids.marker,
            "title": title,
            "status": "new",
            "created_at": payload.timestamp,
            "first_seen": payload.timestamp,
            "last_seen": payload.timestamp,
            "hits_count": 0,
            "users_count": 0,
            "cases_count": 0,
            "app_name": payload.app_name,
            "first_version": payload.version,
            "first_user": payload.user,
            "first_session_user": payload.session_user,
            "first_b24_user_id": payload.b24_user_id,
            "exception_type": payload.exception_type,
            "exception_message": IncidentUtils.normalize_message(
                payload.exception_message
            )[:2000],
            "root_file": payload.root_file,
            "root_function": payload.root_function,
            "root_line": payload.root_line,
            "b24_task_id": None,
            "b24_task_url": "",
            "affected_users": {},
            "cases": {},
            "versions": {},
            "sources": {},
        }

    def _case_record(self, payload: IncidentPayload, ids: IncidentIds) -> dict[str, Any]:
        return {
            "schema": SCHEMA_VERSION,
            "group_hash": ids.group_hash,
            "case_hash": ids.case_hash,
            "created_at": payload.timestamp,
            "app_name": payload.app_name,
            "version": payload.version,
            "exception_type": payload.exception_type,
            "exception_message": IncidentUtils.normalize_message(
                payload.exception_message
            )[:4000],
            "decorated_function": payload.decorated_function,
            "root": {
                "file": payload.root_file,
                "function": payload.root_function,
                "line": payload.root_line,
            },
            "frames": [
                {
                    "file": Path(frame.file.replace("\\", "/")).name,
                    "function": frame.function,
                    "line": frame.line,
                    "code": IncidentUtils.redact(frame.code)[:500],
                }
                for frame in payload.frames[-30:]
            ],
        }

    def _write_raw_trace(
        self,
        group_dir: Path,
        payload: IncidentPayload,
        ids: IncidentIds,
        event_id: str,
    ) -> str:
        if not payload.raw_trace:
            return ""
        path = group_dir / "raw" / (
            f"{payload.timestamp[:19].replace(':', '').replace('-', '')}_"
            f"{IncidentUtils.safe_part(payload.user)}_{ids.case_hash[:10]}_{event_id[:8]}.txt"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        text = IncidentUtils.redact(payload.raw_trace)[: self.config.raw_trace_limit]
        with open(path, "w", encoding="utf-8", errors="backslashreplace") as file:
            file.write(text)
        return str(path.relative_to(group_dir))

    def ensure_outbox(self, result: RegisterResult) -> Path:
        path = self.outbox_dir() / f"{result.ids.group_hash}.json"
        if path.exists():
            return path
        marker = result.marker
        suffix = f" {result.ids.marker}"
        title_base = str(marker.get("title") or "Ошибка MES")
        title = title_base[: max(1, 240 - len(suffix))] + suffix
        _atomic_write_json(
            path,
            {
                "schema": SCHEMA_VERSION,
                "group_hash": result.ids.group_hash,
                "marker": result.ids.marker,
                "created_at": _now(),
                "attempts": 0,
                "last_attempt": "",
                "last_error": "",
                "next_attempt_epoch": 0,
                "source_user": marker.get("first_user") or "",
                "source_session_user": marker.get("first_session_user") or "",
                "created_by_id": marker.get("first_b24_user_id"),
                "title": title,
                "description": self._task_description(marker, result.ids),
            },
        )
        return path

    def _task_description(self, marker: Mapping[str, Any], ids: IncidentIds) -> str:
        message = IncidentUtils.normalize_message(marker.get("exception_message", ""))
        return "\n".join(
            (
                "Автоматически сгруппированный инцидент MES.",
                f"Приложение: {marker.get('app_name', '-')}",
                f"Версия первого случая: {marker.get('first_version', '-')}",
                f"Исключение: {marker.get('exception_type', '-')}: {message[:1200]}",
                f"Точка: {marker.get('root_file', '-')}.{marker.get('root_function', '-')}",
                f"Группа: {ids.group_hash}",
                f"Метка: {ids.marker}",
                "Полный traceback и повторы хранятся во внутреннем реестре инцидентов.",
            )
        )

    def update_b24(
        self,
        group_hash: str,
        task_id: str,
        task_url: str = "",
    ) -> dict[str, Any]:
        group_dir = self.group_dir(self.config.shared_root, group_hash)
        marker_path = group_dir / "marker.json"
        with ExclusiveFileLock(
            group_dir / ".lock",
            self.config.lock_timeout_sec,
            self.config.lock_stale_sec,
        ):
            marker = _read_json(marker_path)
            marker["b24_task_id"] = str(task_id)
            marker["b24_task_url"] = task_url
            marker["b24_synced_at"] = _now()
            marker["status"] = "task_created"
            _atomic_write_json(marker_path, marker)
            return marker


class B24Error(RuntimeError):
    pass


class B24Gateway:
    def __init__(self, base_url: str, timeout: float, verify_tls: bool):
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.verify_tls = verify_tls

    def call(self, method: str, body: Mapping[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            self.base_url + method,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        context = None if self.verify_tls else ssl._create_unverified_context()
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
                context=context,
            ) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise B24Error(f"Б24 недоступен: {exc}") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise B24Error("Б24 вернул некорректный JSON") from exc
        if not isinstance(data, dict):
            raise B24Error("Б24 вернул неожиданный ответ")
        if data.get("error"):
            raise B24Error(
                f"Б24: {data.get('error')} {data.get('error_description', '')}".strip()
            )
        return data

    def find_task(self, marker: str) -> tuple[str, str] | None:
        data = self.call(
            "tasks.task.list",
            {
                "filter": {"TITLE": f"%{marker}%"},
                "select": ["ID", "TITLE"],
                "order": {"ID": "DESC"},
            },
        )
        result = data.get("result") or {}
        if isinstance(result, dict):
            tasks = result.get("tasks") or result.get("TASKS") or []
        elif isinstance(result, list):
            tasks = result
        else:
            tasks = []
        for task in tasks:
            if not isinstance(task, Mapping):
                continue
            title = str(task.get("title") or task.get("TITLE") or "")
            task_id = str(task.get("id") or task.get("ID") or "")
            if task_id and marker in title:
                return task_id, title
        return None

    def add_task(
        self,
        *,
        title: str,
        description: str,
        responsible_id: int,
        created_by_id: int,
        auditors: Sequence[int],
    ) -> str:
        fields: dict[str, Any] = {
            "TITLE": title,
            "DESCRIPTION": description,
            "RESPONSIBLE_ID": responsible_id,
            "CREATED_BY": created_by_id,
        }
        if auditors:
            fields["AUDITORS"] = list(auditors)
        data = self.call("tasks.task.add", {"fields": fields})
        result = data.get("result") or {}
        if isinstance(result, Mapping):
            task = result.get("task") or result.get("TASK") or result
            if isinstance(task, Mapping):
                task_id = task.get("id") or task.get("ID")
            else:
                task_id = task
        else:
            task_id = result
        if not task_id:
            raise B24Error("Б24 не вернул ID созданной задачи")
        return str(task_id)


class IncidentManager:
    def __init__(
        self,
        config: IncidentConfig | None = None,
        context: IncidentContext | None = None,
        *,
        gateway_factory: Callable[[str, float, bool], B24Gateway] = B24Gateway,
    ):
        self.config = config or IncidentConfig()
        self.config.mode = IncidentMode.parse(self.config.mode)
        self.config.shared_root = Path(self.config.shared_root)
        self.config.local_root = Path(self.config.local_root)
        self.context = context or IncidentContext(app_name=self._default_app_name())
        self.store = IncidentStore(self.config)
        self.gateway_factory = gateway_factory
        self._state_lock = threading.RLock()
        self._capture_state = threading.local()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._worker: threading.Thread | None = None
        self._early_installed = False
        self._early_active = False
        self._original_sys_hook = None
        self._original_thread_hook = None
        self._original_unraisable_hook = None
        self._qt_bridge_installed = False
        self._qt_previous_handler = None
        self._qt_bridge_handler = None
        self._runtime_ready = False

    @staticmethod
    def _default_app_name() -> str:
        try:
            return Path(sys.argv[0]).stem or "app"
        except Exception:
            return "app"

    def debug(self, message: str) -> None:
        if not self.config.debug:
            return
        try:
            print(f"[MES incidents] {message}", file=sys.stderr)
        except Exception:
            pass

    def configure(
        self,
        *,
        app_name: str | None = None,
        version: str | None = None,
        user: str | None = None,
        computer: str | None = None,
        b24_user_id: int | None = None,
        mode: str | IncidentMode | None = None,
        b24_responsible_id: int | None = None,
        b24_test_user_id: int | None = None,
        b24_auditors: Sequence[int] | None = None,
        b24_url: str | None = None,
    ) -> None:
        with self._state_lock:
            if app_name:
                self.context.app_name = str(app_name)
            if version:
                self.context.version = str(version)
            if user:
                self.context.user = str(user)
            if computer:
                self.context.computer = str(computer)
            if b24_user_id is not None:
                self.context.b24_user_id = int(b24_user_id)
            if mode is not None:
                self.config.mode = IncidentMode.parse(mode)
            if b24_responsible_id is not None:
                self.config.b24_responsible_id = int(b24_responsible_id)
            if b24_test_user_id is not None:
                self.config.b24_test_user_id = int(b24_test_user_id)
            if b24_auditors is not None:
                self.config.b24_auditors = tuple(int(item) for item in b24_auditors)
            if b24_url is not None:
                self.config.b24_url = str(b24_url).strip()
        self._wake.set()

    def install_early_hooks(self) -> None:
        with self._state_lock:
            if self._early_installed:
                self._early_active = True
                return
            self._original_sys_hook = sys.excepthook
            self._original_thread_hook = getattr(threading, "excepthook", None)
            self._original_unraisable_hook = getattr(sys, "unraisablehook", None)
            sys.excepthook = self._early_sys_hook
            if hasattr(threading, "excepthook"):
                threading.excepthook = self._early_thread_hook
            if hasattr(sys, "unraisablehook"):
                sys.unraisablehook = self._early_unraisable_hook
            self._early_installed = True
            self._early_active = True

    def _early_sys_hook(self, exc_type, exc_value, exc_tb) -> None:
        if self._early_active and not issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
            self.safe_capture_exception(
                exc_type,
                exc_value,
                exc_tb,
                source="early.sys.excepthook",
                handled=False,
            )
        original = self._original_sys_hook
        if original and original is not self._early_sys_hook:
            original(exc_type, exc_value, exc_tb)

    def _early_thread_hook(self, args) -> None:
        if self._early_active and args.exc_type is not SystemExit:
            self.safe_capture_exception(
                args.exc_type,
                args.exc_value,
                args.exc_traceback,
                source=f"early.threading.excepthook thread={getattr(args.thread, 'name', '')}",
                handled=False,
            )
        original = self._original_thread_hook
        if original and original is not self._early_thread_hook:
            try:
                original(args)
            except Exception:
                pass

    def _early_unraisable_hook(self, unraisable) -> None:
        if self._early_active:
            self.safe_capture_exception(
                unraisable.exc_type,
                unraisable.exc_value,
                unraisable.exc_traceback,
                source="early.sys.unraisablehook",
                handled=False,
            )
        original = self._original_unraisable_hook
        if original and original is not self._early_unraisable_hook:
            try:
                original(unraisable)
            except Exception:
                pass

    def attach_safe_application(self, app: Any) -> bool:
        reporter = getattr(app, "crash_reporter", None)
        if reporter is None:
            self.debug("У SafeApplication не найден crash_reporter")
            return False

        self.configure(
            app_name=getattr(reporter, "app_name", None),
            user=getattr(reporter, "current_user", None),
        )

        bridge = getattr(reporter, "_mes_incident_bridge", None)
        if bridge is None:
            original_handle = reporter.handle_exception
            manager = self

            def bridged_handle_exception(
                exc_type,
                exc_value,
                exc_tb,
                *,
                source: str = "python",
                show: bool = True,
            ):
                try:
                    return original_handle(
                        exc_type,
                        exc_value,
                        exc_tb,
                        source=source,
                        show=show,
                    )
                finally:
                    manager.safe_capture_exception(
                        exc_type,
                        exc_value,
                        exc_tb,
                        source=source,
                        handled=False,
                    )

            reporter.handle_exception = bridged_handle_exception
            reporter._mes_incident_bridge = {
                "manager": self,
                "original_handle_exception": original_handle,
            }

        self._early_active = False
        self._install_qt_bridge()
        self.start_worker()
        if self.config.capture_native_faults:
            self._ingest_native_faults(reporter)
        self._wake.set()
        return True

    def _install_qt_bridge(self) -> None:
        if self._qt_bridge_installed or not self.config.capture_qt_critical:
            return
        try:
            from PyQt5 import QtCore
        except Exception:
            return

        manager = self

        def qt_bridge(mode, context, message) -> None:
            previous = manager._qt_previous_handler
            if previous:
                try:
                    previous(mode, context, message)
                except Exception:
                    pass
            try:
                value = int(mode)
            except Exception:
                value = getattr(mode, "value", -1)
            if value not in (2, 3):
                return
            level = "QtFatal" if value == 3 else "QtCritical"
            category = getattr(context, "category", "") or ""
            function = getattr(context, "function", "") or ""
            manager.safe_capture_message(
                exception_type=level,
                message=str(message or ""),
                source=f"qt.{category}",
                decorated_function=str(function),
                handled=False,
            )

        try:
            self._qt_previous_handler = QtCore.qInstallMessageHandler(qt_bridge)
            self._qt_bridge_handler = qt_bridge
            self._qt_bridge_installed = True
        except Exception:
            pass

    def _ingest_native_faults(self, reporter: Any) -> None:
        try:
            folder = Path(getattr(reporter, "local_native_dir"))
            current = getattr(reporter, "_local_fault_path", None)
            seen_dir = self.config.local_root / "native_seen"
            for path in folder.glob("*.log"):
                if current is not None and path == Path(current):
                    continue
                try:
                    if path.stat().st_size <= 0:
                        continue
                    raw = path.read_text(encoding="utf-8", errors="replace")
                    digest = hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()
                    seen = seen_dir / f"{digest}.json"
                    if seen.exists():
                        continue
                    sample = "\n".join(line for line in raw.splitlines()[-40:] if line.strip())
                    receipt = self.safe_capture_message(
                        exception_type="NativeFault",
                        message=sample[-4000:] or path.name,
                        source="faulthandler.previous_start",
                        decorated_function="native_fault",
                        raw_trace=raw,
                        handled=False,
                    )
                    if receipt is not None:
                        _atomic_write_json(
                            seen,
                            {"hash": digest, "source": path.name, "captured_at": _now()},
                        )
                except Exception:
                    continue
        except Exception:
            return

    def configure_from_application(self, application: Any) -> None:
        version = getattr(application, "versia", None)
        b24_user_id = None
        user = None
        try:
            config_module = importlib.import_module("project_cust_38.Cust_config")
            user_config = getattr(getattr(config_module, "Config", None), "user_config", None)
            runtime_user = getattr(user_config, "User", None)
            b24_user_id = getattr(runtime_user, "id_bitrix", None)
            user = getattr(runtime_user, "ФИО", None)
        except Exception:
            pass
        self.configure(
            version=str(version) if version else None,
            user=str(user) if user else None,
            b24_user_id=b24_user_id,
        )
        self._runtime_ready = True
        self._wake.set()

    def _payload_from_exception(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_tb: Any,
        *,
        source: str,
        handled: bool,
        decorated_function: str = "",
        version: str | None = None,
    ) -> IncidentPayload:
        frames = [FrameInfo.from_summary(frame) for frame in traceback.extract_tb(exc_tb)]
        try:
            raw_trace = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        except Exception:
            raw_trace = f"{getattr(exc_type, '__name__', exc_type)}: {exc_value}"
        return IncidentPayload(
            app_name=self.context.app_name,
            version=str(version or self.context.version or "-"),
            timestamp=_now(),
            user=self.context.user,
            computer=self.context.computer,
            exception_type=getattr(exc_type, "__name__", str(exc_type or "Exception")),
            exception_message=IncidentUtils.redact(exc_value),
            frames=frames,
            source=str(source or "python"),
            handled=handled,
            decorated_function=decorated_function,
            raw_trace=raw_trace,
            b24_user_id=self.context.b24_user_id,
            session_user=self.context.session_user,
        )

    def safe_capture_exception(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_tb: Any,
        *,
        source: str = "python",
        handled: bool = False,
        decorated_function: str = "",
        version: str | None = None,
    ) -> CaptureReceipt | None:
        if self.config.mode is IncidentMode.OFF:
            return None
        if getattr(self._capture_state, "active", False):
            return None
        self._capture_state.active = True
        try:
            payload = self._payload_from_exception(
                exc_type,
                exc_value,
                exc_tb,
                source=source,
                handled=handled,
                decorated_function=decorated_function,
                version=version,
            )
            return self._spool_payload(payload)
        except Exception as exc:
            self.debug(f"Не удалось сохранить исключение: {exc}")
            return None
        finally:
            self._capture_state.active = False

    def safe_capture_message(
        self,
        *,
        exception_type: str,
        message: str,
        source: str,
        decorated_function: str = "",
        raw_trace: str = "",
        handled: bool = False,
    ) -> CaptureReceipt | None:
        if self.config.mode is IncidentMode.OFF:
            return None
        if getattr(self._capture_state, "active", False):
            return None
        self._capture_state.active = True
        try:
            payload = IncidentPayload(
                app_name=self.context.app_name,
                version=self.context.version,
                timestamp=_now(),
                user=self.context.user,
                computer=self.context.computer,
                exception_type=str(exception_type or "Incident"),
                exception_message=IncidentUtils.redact(message),
                frames=[],
                source=source,
                handled=handled,
                decorated_function=decorated_function,
                raw_trace=raw_trace,
                b24_user_id=self.context.b24_user_id,
                session_user=self.context.session_user,
            )
            return self._spool_payload(payload)
        except Exception as exc:
            self.debug(f"Не удалось сохранить сообщение: {exc}")
            return None
        finally:
            self._capture_state.active = False

    def _spool_payload(self, payload: IncidentPayload) -> CaptureReceipt:
        payload.exception_message = IncidentUtils.redact(payload.exception_message)[:4000]
        payload.raw_trace = IncidentUtils.redact(payload.raw_trace)[
            : self.config.raw_trace_limit
        ]
        ids = IncidentUtils.build_ids(payload)
        event_id = uuid.uuid4().hex
        receipt = CaptureReceipt(ids=ids, event_id=event_id)
        try:
            receipt.pending_path = self.store.spool(payload, ids, event_id)
        except Exception as exc:
            receipt.error = f"local_spool: {exc}"
            try:
                receipt.local_result = self.store.register(
                    self.config.shared_root,
                    payload,
                    ids,
                    event_id,
                )
                return receipt
            except Exception as shared_exc:
                receipt.error += f"; shared_store: {shared_exc}"
                return receipt
        try:
            receipt.local_result = self.store.register(
                self.config.local_root,
                payload,
                ids,
                event_id,
            )
        except Exception as exc:
            receipt.error = f"local_index: {exc}"
        self._wake.set()
        return receipt

    def start_worker(self) -> None:
        with self._state_lock:
            if self._worker and self._worker.is_alive():
                return
            self._stop.clear()
            self._worker = threading.Thread(
                target=self._worker_loop,
                name="MESIncidentWorker",
                daemon=True,
            )
            self._worker.start()

    def _worker_loop(self) -> None:
        while not self._stop.is_set():
            self._wake.wait(max(0.5, self.config.flush_interval_sec))
            self._wake.clear()
            if self._stop.is_set():
                break
            try:
                self.flush_once()
            except Exception as exc:
                self.debug(f"Ошибка worker: {exc}")

    def flush_once(self, limit: int = 100) -> dict[str, int]:
        counters = {"pending": 0, "outbox": 0, "errors": 0}
        pending_dir = self.store.pending_dir()
        try:
            pending_paths = sorted(pending_dir.glob("*.json"))[:limit]
        except Exception:
            pending_paths = []
        for path in pending_paths:
            try:
                record = _read_json(path)
                payload = IncidentPayload.from_dict(record["payload"])
                if (
                    payload.b24_user_id is None
                    and self.context.b24_user_id is not None
                    and payload.session_user == self.context.session_user
                    and payload.computer == self.context.computer
                ):
                    payload.b24_user_id = self.context.b24_user_id
                ids = IncidentIds.from_dict(record["ids"])
                event_id = str(record["event_id"])
                result = self.store.register(
                    self.config.shared_root,
                    payload,
                    ids,
                    event_id,
                )
                if self.config.mode.creates_tasks and not result.marker.get("b24_task_id"):
                    self.store.ensure_outbox(result)
                path.unlink(missing_ok=True)
                counters["pending"] += 1
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                counters["errors"] += 1
                self._quarantine_pending(path, exc)
            except Exception as exc:
                counters["errors"] += 1
                self.debug(f"Не удалось выгрузить {path.name}: {exc}")

        if self.config.mode.creates_tasks:
            outbox_result = self.flush_outbox(limit=limit)
            counters["outbox"] += outbox_result["sent"]
            counters["errors"] += outbox_result["errors"]
        return counters

    def _quarantine_pending(self, path: Path, exc: BaseException) -> None:
        try:
            bad = self.config.local_root / "pending_bad" / path.name
            bad.parent.mkdir(parents=True, exist_ok=True)
            os.replace(str(path), str(bad))
            _atomic_write_json(
                bad.with_suffix(".error.json"),
                {"source": path.name, "error": str(exc), "timestamp": _now()},
            )
        except Exception:
            pass

    def _resolve_b24_url(self) -> str:
        if self.config.b24_url:
            return self.config.b24_url
        env_url = os.getenv("MES_INCIDENT_B24_URL", "").strip()
        if env_url:
            return env_url
        if not self.config.allow_legacy_b24_url:
            return ""
        try:
            module = sys.modules.get("project_cust_38.Cust_b24")
            if module is None:
                if not self._runtime_ready:
                    return ""
                module = importlib.import_module("project_cust_38.Cust_b24")
            sender = getattr(module, "B24Sender", None)
            return str(getattr(sender, "_URL", "") or "").strip()
        except Exception:
            return ""

    def _task_actors(
        self,
        item: Mapping[str, Any] | None = None,
    ) -> tuple[int | None, int | None]:
        if self.config.mode is IncidentMode.SILENT_TEST:
            test_user = self.config.b24_test_user_id
            return test_user, self.config.b24_responsible_id or test_user
        item = item or {}
        created_by = item.get("created_by_id")
        if (
            not created_by
            and item.get("source_session_user") == self.context.session_user
        ):
            created_by = self.context.b24_user_id
        if not created_by:
            created_by = self.config.b24_created_by_id
        return created_by, self.config.b24_responsible_id

    def flush_outbox(self, limit: int = 100) -> dict[str, int]:
        result = {"sent": 0, "errors": 0}
        try:
            candidates = sorted(self.store.outbox_dir().glob("*.json"))
        except Exception:
            return result
        paths: list[Path] = []
        batch_limit = min(max(1, limit), max(1, self.config.b24_batch_size))
        current_time = time.time()
        for path in candidates:
            try:
                item = _read_json(path)
                next_attempt = float(item.get("next_attempt_epoch") or 0)
                if next_attempt > current_time:
                    continue
            except Exception:
                pass
            paths.append(path)
            if len(paths) >= batch_limit:
                break
        if not paths:
            return result

        base_url = self._resolve_b24_url()
        _, responsible = self._task_actors()
        if not base_url or not responsible:
            reason = (
                "Ожидание конфигурации Б24: нужны URL и RESPONSIBLE_ID"
            )
            for path in paths:
                self._mark_outbox_error(path, reason, increment=False)
            return result

        gateway = self.gateway_factory(
            base_url,
            self.config.request_timeout_sec,
            self.config.verify_tls,
        )
        for path in paths:
            try:
                with ExclusiveFileLock(
                    path.with_suffix(".lock"),
                    self.config.lock_timeout_sec,
                    self.config.lock_stale_sec,
                ):
                    if not path.exists():
                        continue
                    try:
                        item = _read_json(path)
                        created_by, responsible = self._task_actors(item)
                        if not created_by or not responsible:
                            self._mark_outbox_error(
                                path,
                                "Ожидание CREATED_BY для пользователя инцидента",
                                increment=False,
                            )
                            continue
                        marker = str(item["marker"])
                        found = gateway.find_task(marker)
                        if found:
                            task_id = found[0]
                        else:
                            task_id = gateway.add_task(
                                title=str(item["title"]),
                                description=str(item["description"]),
                                responsible_id=int(responsible),
                                created_by_id=int(created_by),
                                auditors=self.config.b24_auditors,
                            )
                        self.store.update_b24(str(item["group_hash"]), task_id)
                        path.unlink(missing_ok=True)
                        result["sent"] += 1
                    except Exception as exc:
                        result["errors"] += 1
                        self._mark_outbox_error(path, str(exc), increment=True)
            except IncidentLockTimeout:
                continue
            except Exception as exc:
                result["errors"] += 1
                self._mark_outbox_error(path, str(exc), increment=True)
        return result

    def _mark_outbox_error(self, path: Path, error: str, increment: bool) -> None:
        try:
            item = _read_json(path)
            if increment:
                item["attempts"] = int(item.get("attempts") or 0) + 1
                power = min(max(0, item["attempts"] - 1), 7)
                delay = min(1800.0, self.config.b24_retry_base_sec * (2 ** power))
            else:
                delay = self.config.b24_retry_base_sec
            item["last_attempt"] = _now()
            item["last_error"] = IncidentUtils.redact(error)[:1000]
            item["next_attempt_epoch"] = time.time() + max(0.0, delay)
            _atomic_write_json(path, item)
        except Exception:
            pass

    def shutdown(self) -> None:
        self._stop.set()
        self._wake.set()
        worker = self._worker
        if (
            worker is not None
            and worker.is_alive()
            and worker is not threading.current_thread()
        ):
            worker.join(timeout=2.0)


_manager: IncidentManager | None = None
_manager_lock = threading.RLock()


def get_manager() -> IncidentManager:
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = IncidentManager()
        return _manager


def bootstrap_incidents(
    app_name: str,
    *,
    mode: str | IncidentMode | None = None,
) -> IncidentManager:
    manager = get_manager()
    try:
        manager.configure(app_name=app_name, mode=mode)
        manager.install_early_hooks()
    except Exception as exc:
        manager.debug(f"Не удалось установить ранние hooks: {exc}")
    return manager


def configure_incidents(**kwargs: Any) -> IncidentManager:
    manager = get_manager()
    try:
        manager.configure(**kwargs)
    except Exception as exc:
        manager.debug(f"Не удалось обновить конфигурацию: {exc}")
    return manager


def configure_from_application(application: Any) -> IncidentManager:
    manager = get_manager()
    try:
        manager.configure_from_application(application)
    except Exception as exc:
        manager.debug(f"Не удалось прочитать runtime-контекст: {exc}")
    return manager


def attach_safe_application(app: Any) -> bool:
    manager = get_manager()
    try:
        return manager.attach_safe_application(app)
    except Exception as exc:
        manager.debug(f"Не удалось подключиться к SafeApplication: {exc}")
        return False


def capture_exception(
    exc_type: type[BaseException] | None = None,
    exc_value: BaseException | None = None,
    exc_tb: Any = None,
    *,
    source: str = "python",
    handled: bool = False,
    decorated_function: str = "",
    version: str | None = None,
) -> CaptureReceipt | None:
    if exc_type is None and exc_value is None and exc_tb is None:
        exc_type, exc_value, exc_tb = sys.exc_info()
    return get_manager().safe_capture_exception(
        exc_type,
        exc_value,
        exc_tb,
        source=source,
        handled=handled,
        decorated_function=decorated_function,
        version=version,
    )


def capture_onerror(
    exc_type: type[BaseException] | None,
    exc_value: BaseException | None,
    exc_tb: Any,
    *,
    func: Any = None,
    app_self: Any = None,
) -> CaptureReceipt | None:
    version = getattr(app_self, "versia", None) if app_self is not None else None
    return get_manager().safe_capture_exception(
        exc_type,
        exc_value,
        exc_tb,
        source="Cust_Qt.onerror",
        handled=True,
        decorated_function=getattr(func, "__name__", ""),
        version=str(version) if version else None,
    )


def flush_incidents(limit: int = 100) -> dict[str, int]:
    return get_manager().flush_once(limit=limit)


def shutdown_incidents() -> None:
    manager = _manager
    if manager is not None:
        manager.shutdown()


atexit.register(shutdown_incidents)


def run_silent_test_probe(
    manager: IncidentManager | None = None,
) -> dict[str, Any]:
    manager = manager or get_manager()
    if manager.config.mode is not IncidentMode.SILENT_TEST:
        raise RuntimeError(
            "Silent probe разрешён только при MES_INCIDENT_MODE=silent_test"
        )
    if not manager.config.b24_test_user_id:
        raise RuntimeError("Для silent probe нужен MES_INCIDENT_TEST_USER_ID")

    manager._runtime_ready = True
    manager.configure(app_name="MES Incident Probe", version="probe-1")
    receipts: list[CaptureReceipt] = []

    def grouped_failure(order_number: int) -> None:
        raise LookupError(f"Тест: не найден заказ {order_number}")

    def separate_failure() -> None:
        raise PermissionError("Тест: отсутствует право на операцию")

    for order_number in (123456701, 987654309):
        try:
            grouped_failure(order_number)
        except LookupError as exc:
            receipt = manager.safe_capture_exception(
                type(exc),
                exc,
                exc.__traceback__,
                source="silent_test.probe",
                handled=True,
            )
            if receipt is not None:
                receipts.append(receipt)

    try:
        separate_failure()
    except PermissionError as exc:
        receipt = manager.safe_capture_exception(
            type(exc),
            exc,
            exc.__traceback__,
            source="silent_test.probe",
            handled=True,
        )
        if receipt is not None:
            receipts.append(receipt)

    flush_result = manager.flush_once()
    return {
        "events": len(receipts),
        "groups": sorted({receipt.ids.group_hash for receipt in receipts}),
        "cases": sorted({receipt.ids.case_hash for receipt in receipts}),
        "flush": flush_result,
    }


def _main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="MES incident manager")
    parser.add_argument(
        "--silent-probe",
        action="store_true",
        help="создать тестовые сгруппированные инциденты без UI",
    )
    parser.add_argument(
        "--flush",
        action="store_true",
        help="выгрузить локальный spool и очередь задач",
    )
    args = parser.parse_args(argv)
    if not args.silent_probe and not args.flush:
        parser.print_help()
        return 0

    try:
        if args.silent_probe:
            result = run_silent_test_probe()
        else:
            get_manager()._runtime_ready = True
            result = flush_incidents()
    except Exception as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
