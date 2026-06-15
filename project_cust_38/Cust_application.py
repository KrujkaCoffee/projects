from __future__ import annotations

import atexit
import faulthandler
import hashlib
import linecache
import os
import re
import shutil
import sys
import tempfile
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

from PyQt5 import QtCore, QtWidgets


LOG_DIR = Path(r"Z:\MES_setup\errors\crash")
LOCAL_NATIVE_DIR = Path(tempfile.gettempdir()) / "mes_native_faults"


def safe_file_part(value: object, default: str = "unknown") -> str:
    text = str(value or default).strip()
    text = re.sub(r'[\\/:*?"<>|]+', "_", text)
    text = re.sub(r"\s+", "_", text)
    return text[:120] or default


class CrashReporter(QtCore.QObject):
    popup = QtCore.pyqtSignal(str, str)

    QT_LEVELS = {
        0: "DEBUG",
        1: "WARNING",
        2: "CRITICAL",
        3: "FATAL",
        4: "INFO",
    }

    QT_NOISE_PATTERNS = (
        "QWindowsWindow::setGeometry",
        "QBackingStore::endPaint",
        "QWidget::repaint: Recursive repaint detected",
        "QPainter::begin: Paint device returned engine",
        "QBasicTimer::stop: Failed. Possibly trying to stop from a different thread",
    )

    QT_INTERESTING_WORDS = (
        "traceback",
        "exception",
        "error",
        "failed",
        "cannot",
        "critical",
        "fatal",
        "assert",
        "segmentation",
        "access violation",
        "database is locked",
        "qthread",
        "different thread",
    )

    def __init__(
        self,
        user_name: str,
        app_name: str = "",
        show_popup: bool = True,
        log_qt_warnings: bool = False,
        log_qt_debug_info: bool = False,
        parent=None,
    ):
        super().__init__(parent)

        self.app_name = app_name or ""
        self.app_slug = safe_file_part(app_name or "app")
        self.current_user = user_name or ""
        self.current_user_slug = safe_file_part(user_name or "user")

        self.log_dir = LOG_DIR / self.app_slug
        self.local_native_dir = LOCAL_NATIVE_DIR / self.app_slug

        self._ensure_dir(self.log_dir)
        self._ensure_dir(self.local_native_dir)

        self.show_popup_enabled = show_popup
        self.log_qt_warnings = log_qt_warnings
        self.log_qt_debug_info = log_qt_debug_info

        self._lock = threading.RLock()
        self._fault_file = None
        self._local_fault_path: Path | None = None
        self._shutdown_done = False
        self._handling_exception = False

        self._qt_recent: dict[str, float] = {}

        self._old_sys_excepthook = sys.excepthook
        self._old_threading_excepthook = getattr(threading, "excepthook", None)
        self._old_unraisablehook = getattr(sys, "unraisablehook", None)

        self.popup.connect(self._show_popup, QtCore.Qt.QueuedConnection)

    def _ensure_dir(self, path: Path) -> bool:
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    def stamp(self) -> str:
        return datetime.now().strftime("%Y_%m_%d___%H-%M_%S_%f")

    def dump_folder(self) -> Path:
        if self._ensure_dir(self.log_dir) and self.log_dir.exists():
            return self.log_dir

        fallback = Path(tempfile.gettempdir()) / "mes_crashes" / self.app_slug
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback

    def crash_path(self, prefix: str = "crash") -> Path:
        return self.dump_folder() / (
            f"{prefix}_{self.stamp()}_{self.app_slug}_{self.current_user_slug}.log"
        )

    def write_text(self, path: Path, text: str) -> Path:
        """Пишем в заданный путь. Если сетевой диск недоступен — падаем в TEMP."""
        fallback = Path(tempfile.gettempdir()) / "mes_crashes" / self.app_slug / path.name

        with self._lock:
            for candidate in (path, fallback):
                try:
                    candidate.parent.mkdir(parents=True, exist_ok=True)
                    with open(candidate, "a", encoding="utf-8", errors="backslashreplace") as f:
                        f.write(text)
                        f.write("\n")
                        f.flush()
                        os.fsync(f.fileno())
                    return candidate
                except Exception:
                    continue

        return path

    def format_error_message(
        self,
        exc_type,
        exc_value,
        exc_tb,
        *,
        source: str,
    ) -> str:
        frames = traceback.extract_tb(exc_tb) if exc_tb is not None else []
        root = frames[-1] if frames else None

        if root is not None:
            root_file = Path(root.filename).name
            root_fnc_name = root.name
            root_line = root.lineno
            code_line = root.line or linecache.getline(root.filename, root.lineno).strip()
        else:
            root_file = "-"
            root_fnc_name = "-"
            root_line = "-"
            code_line = ""

        trace_lines = []
        for counter, frame in enumerate(frames, start=1):
            trace_lines.append(
                f"Step {counter}: file='{Path(frame.filename).name}', "
                f"line={frame.lineno}:"
            )
            trace_lines.append(
                f"   fnc {frame.name}\n"
                f"        line {frame.lineno}\n"
            )

        tracer = "\n".join(trace_lines)

        code_block = "\n".join(
            f"            {_}" for _ in str(code_line).split("\n")
        )

        return (
            f"Источник: {source}\n"
            f"Пользователь: {self.current_user}\n"
            f"Приложение: {self.app_name}\n"
            f"File: {root_file}\n"
            f"    fnc {root_fnc_name} \n"
            f"        line {root_line}:\n"
            f"{code_block}\n "
            f"unexpected error:\n"
            f"   \"{exc_value}\"\n"
            f"===============FRAMES START===================\n" 
            f"{tracer}\n"
            f"===============FRAMES END===================\n\n"
        )

    def handle_exception(
        self,
        exc_type,
        exc_value,
        exc_tb,
        *,
        source: str = "python",
        show: bool = True,
    ) -> Path:
        if self._handling_exception:
            traceback.print_exception(exc_type, exc_value, exc_tb)
            return self.crash_path("crash_recursion")

        self._handling_exception = True
        try:
            path = self.crash_path("crash")

            onerror_text = self.format_error_message(
                exc_type,
                exc_value,
                exc_tb,
                source=source,
            )

            full_tb_text = "".join(
                traceback.format_exception(exc_type, exc_value, exc_tb)
            )

            header = (
                f"=== CRASH REPORT ===\n"
                f"Приложение: {self.app_name}\n"
                f"Пользователь: {self.current_user}\n"
                f"Источник: {source}\n"
                f"Дата: {datetime.now():%Y-%m-%d %H:%M:%S}\n"
                f"thread: {threading.current_thread().name}\n"
                f"pid: {os.getpid()}\n\n"
            )

            path = self.write_text(
                path,
                header
                + onerror_text
                + "\n=== FULL TRACEBACK ===\n"
                + full_tb_text,
            )

            try:
                with open(path, "a", encoding="utf-8", errors="backslashreplace") as f:
                    f.write("\n=== ALL THREADS TRACEBACK ===\n")
                    faulthandler.dump_traceback(file=f, all_threads=True)
                    f.flush()
                    os.fsync(f.fileno())
            except Exception:
                pass

            if show and self._show_popup:
                popup_text = f"{onerror_text}\nМЕТКА:\n{path}"

                self.popup.emit("Критическая ошибка", popup_text)

            return path
        finally:
            self._handling_exception = False

    def sys_excepthook(self, exc_type, exc_value, exc_tb):
        if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
            return self._old_sys_excepthook(exc_type, exc_value, exc_tb)

        self.handle_exception(
            exc_type,
            exc_value,
            exc_tb,
            source="sys.excepthook",
        )

        self._old_sys_excepthook(exc_type, exc_value, exc_tb)

    def threading_excepthook(self, args):
        if args.exc_type is SystemExit:
            return

        self.handle_exception(
            args.exc_type,
            args.exc_value,
            args.exc_traceback,
            source=f"threading.excepthook thread={getattr(args.thread, 'name', '')}",
        )

        old_hook = self._old_threading_excepthook
        if old_hook and old_hook is not self.threading_excepthook:
            try:
                old_hook(args)
            except Exception:
                pass

    def unraisablehook(self, unraisable):
        self.handle_exception(
            unraisable.exc_type,
            unraisable.exc_value,
            unraisable.exc_traceback,
            source=f"sys.unraisablehook object={repr(unraisable.object)[:500]}",
        )

        old_hook = self._old_unraisablehook
        if old_hook and old_hook is not self.unraisablehook:
            try:
                old_hook(unraisable)
            except Exception:
                pass

    def qt_message_key(self, level: str, message: str) -> str:
        raw = f"{level}|{message}".encode("utf-8", errors="backslashreplace")
        return hashlib.sha1(raw).hexdigest()

    def is_duplicate_qt_message(self, level: str, message: str, seconds: int = 20) -> bool:
        """
        Не пишем одинаковые Qt-сообщения пачками.
        """
        key = self.qt_message_key(level, message)
        now = time.time()

        prev = self._qt_recent.get(key)
        if prev is not None and now - prev < seconds:
            return True

        self._qt_recent[key] = now

        if len(self._qt_recent) > 300:
            old_keys = sorted(self._qt_recent, key=self._qt_recent.get)[:100]
            for old_key in old_keys:
                self._qt_recent.pop(old_key, None)

        return False

    def qt_message_should_log(self, level: str, message: str) -> bool:
        msg = str(message or "").strip()
        if not msg:
            return False

        msg_low = msg.lower()

        if level in ("FATAL", "CRITICAL"):
            return True

        if any(pattern.lower() in msg_low for pattern in self.QT_NOISE_PATTERNS):
            return False

        if level in ("DEBUG", "INFO"):
            return bool(self.log_qt_debug_info)

        if level == "WARNING":
            if self.log_qt_warnings:
                return True
            return any(word in msg_low for word in self.QT_INTERESTING_WORDS)

        return False

    def qt_message_handler(self, mode, context, message):
        try:
            mode_int = int(mode)
        except Exception:
            mode_int = getattr(mode, "value", -1)

        level = self.QT_LEVELS.get(mode_int, str(mode))
        msg = str(message or "").strip()

        if not self.qt_message_should_log(level, msg):
            return

        if self.is_duplicate_qt_message(level, msg):
            return

        file = getattr(context, "file", "") or ""
        line = getattr(context, "line", "") or ""
        function = getattr(context, "function", "") or ""
        category = getattr(context, "category", "") or ""

        text = (
            f"[{datetime.now():%Y-%m-%d %H:%M:%S}] "
            f"{level} {category} {file}:{line} {function} | {msg}"
        )

        qt_log = self.dump_folder() / f"qt_messages_{self.app_slug}.log"
        self.write_text(qt_log, text)

        if level == "FATAL":
            fatal_path = self.crash_path("qt_fatal")
            self.write_text(fatal_path, text)

    def copy_native_fault_to_network(self, local_path: Path) -> bool:
        """Переносим краш дамп qt/c на Z: при следующем старте если процесс умер до переноса ."""

        try:
            if not local_path.exists() or local_path.stat().st_size <= 0:
                return False

            if not self._ensure_dir(self.log_dir):
                return False

            target = self.log_dir / local_path.name
            shutil.copy2(str(local_path), str(target))
            return True
        except Exception:
            return False

    def flush_previous_native_faults(self):
        """Переносим краш дамп процесса на Z: при следующем старте если процесс умер до переноса ."""
        try:
            self.local_native_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            return

        for path in self.local_native_dir.glob("process_faults_*.log"):
            if self._local_fault_path is not None and path == self._local_fault_path:
                continue

            try:
                size = path.stat().st_size
            except Exception:
                continue

            if size <= 0:
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    pass
                continue

            if self.copy_native_fault_to_network(path):
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    pass

    def enable_fault_handler(self):
        """обработка краша на уровне qt/c++"""
        self.flush_previous_native_faults()

        fault_path = self.local_native_dir / (
            f"qt_c_crash_{self.stamp()}_{self.app_slug}_{self.current_user_slug}.log"
        )

        self._local_fault_path = fault_path
        self._fault_file = open(
            fault_path,
            "a+",
            encoding="utf-8",
            errors="backslashreplace",
        )

        faulthandler.enable(file=self._fault_file, all_threads=True)

    def shutdown_cleanup(self):
        """обработка штатного выхода"""
        if self._shutdown_done:
            return

        self._shutdown_done = True

        try:
            faulthandler.disable()
        except Exception:
            pass

        fault_path = self._local_fault_path

        try:
            if self._fault_file is not None:
                self._fault_file.flush()
                os.fsync(self._fault_file.fileno())
                self._fault_file.close()
        except Exception:
            pass

        self._fault_file = None

        if fault_path is None:
            return

        try:
            if not fault_path.exists():
                return

            if fault_path.stat().st_size <= 0:
                fault_path.unlink(missing_ok=True)
                return

            if self.copy_native_fault_to_network(fault_path):
                fault_path.unlink(missing_ok=True)

        except Exception:
            pass

    def _show_popup(self, title: str, text: str):
        app = QtWidgets.QApplication.instance()
        if app is None:
            return

        try:
            from project_cust_38 import Cust_Qt as CQT
            CQT.msgbox(
                text[:5000],
                time_life=10,
                icon=QtWidgets.QMessageBox.Critical,
                app_self=app.activeWindow(),
                fontsize=8,
            )
            return
        except Exception:
            pass

        QtWidgets.QMessageBox.critical(None, title, text[:3000])


class SafeApplication(QtWidgets.QApplication):
    crash_reporter: CrashReporter | None = None

    def notify(self, receiver, event):
        try:
            return super().notify(receiver, event)
        except Exception:
            reporter = getattr(self, "crash_reporter", None)
            if reporter is not None:
                receiver_name = ""
                try:
                    receiver_name = receiver.objectName()
                except Exception:
                    pass

                reporter.handle_exception(
                    *sys.exc_info(),
                    source=(
                        "QApplication.notify "
                        f"receiver={type(receiver).__name__}({receiver_name}) "
                        f"event={event.type() if event else None}"
                    ),
                )
            else:
                traceback.print_exc()

            return False


def install_crash_guard(
    app: QtWidgets.QApplication,
    *,
    app_name: str,
    user_name: str,
    show_popup: bool = True,
    log_qt_warnings: bool = False,
    log_qt_debug_info: bool = False,
    enable_native_fault_handler: bool = True,
) -> CrashReporter:
    reporter = CrashReporter(
        app_name=app_name,
        user_name=user_name,
        show_popup=show_popup,
        log_qt_warnings=log_qt_warnings,
        log_qt_debug_info=log_qt_debug_info,
    )

    if isinstance(app, SafeApplication):
        app.crash_reporter = reporter

    sys.excepthook = reporter.sys_excepthook

    if hasattr(threading, "excepthook"):
        threading.excepthook = reporter.threading_excepthook

    if hasattr(sys, "unraisablehook"):
        sys.unraisablehook = reporter.unraisablehook

    QtCore.qInstallMessageHandler(reporter.qt_message_handler)

    if enable_native_fault_handler:
        reporter.enable_fault_handler()

    app.aboutToQuit.connect(reporter.shutdown_cleanup)
    atexit.register(reporter.shutdown_cleanup)

    return reporter