from __future__ import annotations

import datetime as dt
import json
import threading
from typing import Any

import psycopg
from PyQt5.QtCore import QObject, Qt, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QShortcut,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.theme import ThemeDefinition

from .analyzer import SqlSafetyError, analyze_sql
from .executor import (
    SqlExecutionCancelled,
    SqlExecutionRequest,
    SqlExecutionResult,
    SqlQueryRunner,
)
from .highlighter import SqlHighlighter


class _SqlExecutionWorker(QObject):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, runner: SqlQueryRunner, request: SqlExecutionRequest) -> None:
        super().__init__()
        self.runner = runner
        self.request = request

    @pyqtSlot()
    def run(self) -> None:
        try:
            self.succeeded.emit(self.runner.execute(self.request))
        except Exception as exc:  # noqa: BLE001 - worker reports a user-facing boundary
            self.failed.emit(format_sql_error(exc))
        finally:
            self.finished.emit()


def format_sql_error(exc: BaseException) -> str:
    if isinstance(exc, (SqlSafetyError, SqlExecutionCancelled)):
        return str(exc)
    if isinstance(exc, psycopg.Error):
        diag = getattr(exc, "diag", None)
        lines: list[str] = []
        sqlstate = str(getattr(exc, "sqlstate", "") or "").strip()
        severity = str(
            (getattr(diag, "severity_nonlocalized", "") if diag is not None else "")
            or ""
        ).strip()
        primary = str(
            (getattr(diag, "message_primary", "") if diag is not None else "") or ""
        ).strip()
        lines.append(
            ": ".join(part for part in (severity, primary) if part) or str(exc)
        )
        if sqlstate:
            lines.append(f"SQLSTATE: {sqlstate}")
        for label, attribute in (
            ("DETAIL", "message_detail"),
            ("HINT", "message_hint"),
            ("POSITION", "statement_position"),
        ):
            value = str(
                (getattr(diag, attribute, "") if diag is not None else "") or ""
            ).strip()
            if value:
                lines.append(f"{label}: {value}")
        return "\n".join(lines)
    return str(exc).strip() or exc.__class__.__name__


class SqlToolsTab(QWidget):
    executionStateChanged = pyqtSignal(bool)
    _cancelFailed = pyqtSignal(str)

    MAX_CELL_CHARS = 10_000
    MAX_CLIPBOARD_CHARS = 5_000_000

    def __init__(self, db, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self._runner: SqlQueryRunner | None = None
        self._thread: QThread | None = None
        self._worker: _SqlExecutionWorker | None = None
        self._running = False
        self._build_ui()
        self._cancelFailed.connect(self._show_cancel_error)

    @property
    def is_running(self) -> bool:
        return self._running

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(7)

        toolbar_frame = QFrame(self)
        toolbar_frame.setObjectName("sql_tools_toolbar")
        toolbar = QHBoxLayout(toolbar_frame)
        toolbar.setContentsMargins(7, 5, 7, 5)
        self.run_button = QPushButton("▶ Выполнить", toolbar_frame)
        self.run_button.setObjectName("sql_run_button")
        self.cancel_button = QPushButton("■ Остановить", toolbar_frame)
        self.cancel_button.setObjectName("sql_cancel_button")
        self.cancel_button.setEnabled(False)
        self.allow_writes = QCheckBox("Разрешить изменения", toolbar_frame)
        self.allow_writes.setObjectName("sql_allow_writes")
        self.timeout_spin = QSpinBox(toolbar_frame)
        self.timeout_spin.setRange(1, 3600)
        self.timeout_spin.setValue(30)
        self.timeout_spin.setSuffix(" с")
        self.timeout_spin.setToolTip("statement_timeout текущего запуска")
        self.row_limit_spin = QSpinBox(toolbar_frame)
        self.row_limit_spin.setRange(1, 10_000)
        self.row_limit_spin.setValue(1000)
        self.row_limit_spin.setPrefix("Строк: ")
        self.copy_button = QPushButton("Копировать TSV", toolbar_frame)
        self.clear_button = QPushButton("Очистить вывод", toolbar_frame)
        toolbar.addWidget(self.run_button)
        toolbar.addWidget(self.cancel_button)
        toolbar.addSpacing(8)
        toolbar.addWidget(self.allow_writes)
        toolbar.addStretch(1)
        toolbar.addWidget(QLabel("Timeout:", toolbar_frame))
        toolbar.addWidget(self.timeout_spin)
        toolbar.addWidget(self.row_limit_spin)
        toolbar.addWidget(self.copy_button)
        toolbar.addWidget(self.clear_button)
        root.addWidget(toolbar_frame)

        hint = QLabel(
            "F5 / Ctrl+Enter — выделенный SQL или весь редактор. Один statement за запуск; "
            "READ ONLY включён физически, пока не разрешены изменения. История SQL автоматически не сохраняется.",
            self,
        )
        hint.setObjectName("sql_tools_hint")
        hint.setWordWrap(True)
        root.addWidget(hint)

        splitter = QSplitter(Qt.Vertical, self)
        self.editor = QPlainTextEdit(splitter)
        self.editor.setObjectName("sql_editor")
        self.editor.setPlaceholderText(
            "SELECT table_schema, table_name\n"
            "FROM information_schema.tables\n"
            "ORDER BY table_schema, table_name;"
        )
        self.highlighter = SqlHighlighter(self.editor.document())

        output = QWidget(splitter)
        output_layout = QVBoxLayout(output)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.setSpacing(5)
        self.status_label = QLabel("SQL Tools готов", output)
        self.status_label.setObjectName("sql_tools_status")
        self.results = QTableWidget(output)
        self.results.setObjectName("sql_results")
        self.results.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.results.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.results.setAlternatingRowColors(True)
        self.results.setSortingEnabled(False)
        self.results.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.results.horizontalHeader().setStretchLastSection(True)
        self.messages = QPlainTextEdit(output)
        self.messages.setObjectName("sql_messages")
        self.messages.setReadOnly(True)
        self.messages.setMaximumHeight(135)
        self.messages.setPlaceholderText("Сообщения и ошибки PostgreSQL")
        output_layout.addWidget(self.status_label)
        output_layout.addWidget(self.results, 1)
        output_layout.addWidget(self.messages)
        splitter.addWidget(self.editor)
        splitter.addWidget(output)
        splitter.setSizes([330, 500])
        root.addWidget(splitter, 1)

        self.run_button.clicked.connect(self.execute_sql)
        self.cancel_button.clicked.connect(self.cancel_query)
        self.allow_writes.toggled.connect(self._write_mode_changed)
        self.copy_button.clicked.connect(self.copy_tsv)
        self.clear_button.clicked.connect(self.clear_output)
        QShortcut(QKeySequence("F5"), self, activated=self.execute_sql)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.execute_sql)

    def selected_or_all_sql(self) -> str:
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            return cursor.selection().toPlainText().strip()
        return self.editor.toPlainText().strip()

    def execute_sql(self) -> None:
        if self._running:
            return
        sql = self.selected_or_all_sql()
        try:
            analysis = analyze_sql(sql)
        except SqlSafetyError as exc:
            self._show_error(str(exc))
            return
        if analysis.is_write and not self.allow_writes.isChecked():
            self._show_error(
                f"{analysis.command} изменяет данные. Включите «Разрешить изменения»."
            )
            return
        if analysis.is_write:
            answer = QMessageBox.question(
                self,
                "Подтверждение изменяющего SQL",
                f"Команда {analysis.command} будет зафиксирована транзакцией после успешного выполнения. Продолжить?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

        request = SqlExecutionRequest(
            sql=analysis.statement,
            allow_writes=self.allow_writes.isChecked(),
            row_limit=self.row_limit_spin.value(),
            timeout_ms=self.timeout_spin.value() * 1000,
        )
        self.clear_output()
        self.status_label.setText(f"Выполняется: {analysis.command}…")
        runner = SqlQueryRunner(self.db)
        worker = _SqlExecutionWorker(runner, request)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._show_result)
        worker.failed.connect(self._show_error)
        worker.finished.connect(thread.quit, Qt.DirectConnection)
        thread.finished.connect(self._thread_finished)
        self._runner = runner
        self._worker = worker
        self._thread = thread
        self._set_running(True)
        thread.start()

    def cancel_query(self) -> None:
        if not self._running or self._runner is None:
            return
        self.cancel_button.setEnabled(False)
        self.status_label.setText("Отправляется отмена PostgreSQL…")
        runner = self._runner

        def cancel() -> None:
            try:
                runner.cancel(timeout=3.0)
            except Exception as exc:  # noqa: BLE001 - cancellation must not crash UI
                self._cancelFailed.emit(format_sql_error(exc))

        threading.Thread(
            target=cancel,
            name="admin-sql-cancel",
            daemon=True,
        ).start()

    def stop_and_wait(self, timeout_ms: int = 5000) -> bool:
        if not self._running:
            return True
        self.cancel_query()
        thread = self._thread
        return bool(thread is None or thread.wait(max(0, timeout_ms)))

    def _set_running(self, running: bool) -> None:
        self._running = running
        self.run_button.setEnabled(not running)
        self.cancel_button.setEnabled(running)
        self.allow_writes.setEnabled(not running)
        self.timeout_spin.setEnabled(not running)
        self.row_limit_spin.setEnabled(not running)
        self.executionStateChanged.emit(running)

    @pyqtSlot()
    def _thread_finished(self) -> None:
        self._set_running(False)
        self._worker = None
        thread = self._thread
        self._thread = None
        self._runner = None
        if thread is not None:
            thread.deleteLater()

    @pyqtSlot(object)
    def _show_result(self, result: SqlExecutionResult) -> None:
        self.results.setSortingEnabled(False)
        self.results.clear()
        self.results.setColumnCount(len(result.columns))
        self.results.setHorizontalHeaderLabels(list(result.columns))
        self.results.setRowCount(len(result.rows))
        for row_index, row in enumerate(result.rows):
            for column_index, value in enumerate(row):
                item = QTableWidgetItem(self._cell_text(value))
                item.setData(Qt.UserRole, value)
                if value is None:
                    item.setToolTip("NULL")
                self.results.setItem(row_index, column_index, item)
        self.results.setSortingEnabled(bool(result.columns))
        self.results.resizeColumnsToContents()
        if result.columns:
            summary = f"Получено строк: {len(result.rows)}"
            if result.truncated:
                summary += " · достигнут лимит вывода"
        elif result.affected_rows is not None:
            summary = f"Затронуто строк: {result.affected_rows}"
        else:
            summary = "Команда выполнена"
        self.status_label.setText(f"{summary} · {result.duration_ms} мс")
        if result.notices:
            self.messages.setPlainText("\n".join(result.notices))

    @pyqtSlot(str)
    def _show_error(self, message: str) -> None:
        self.status_label.setText("Ошибка выполнения SQL")
        self.messages.setPlainText(message)

    @pyqtSlot(str)
    def _show_cancel_error(self, message: str) -> None:
        existing = self.messages.toPlainText().strip()
        self.messages.setPlainText(
            "\n".join(part for part in (existing, f"Ошибка отмены: {message}") if part)
        )
        if self._running:
            self.cancel_button.setEnabled(True)

    def _write_mode_changed(self, enabled: bool) -> None:
        self.allow_writes.setProperty("armed", enabled)
        style = self.allow_writes.style()
        style.unpolish(self.allow_writes)
        style.polish(self.allow_writes)
        self.allow_writes.setToolTip(
            "Изменяющие команды разрешены до отключения флага или закрытия приложения"
            if enabled
            else "SQL выполняется в транзакции READ ONLY"
        )

    def clear_output(self) -> None:
        self.results.setSortingEnabled(False)
        self.results.clear()
        self.results.setRowCount(0)
        self.results.setColumnCount(0)
        self.messages.clear()
        if not self._running:
            self.status_label.setText("SQL Tools готов")

    def copy_tsv(self) -> None:
        if not self.results.columnCount():
            return
        ranges = self.results.selectedRanges()
        if ranges:
            top = min(value.topRow() for value in ranges)
            bottom = max(value.bottomRow() for value in ranges)
            left = min(value.leftColumn() for value in ranges)
            right = max(value.rightColumn() for value in ranges)
        else:
            top, bottom = 0, self.results.rowCount() - 1
            left, right = 0, self.results.columnCount() - 1
        lines = [
            "\t".join(
                self._tsv_text(self.results.horizontalHeaderItem(column).text())
                for column in range(left, right + 1)
            )
        ]
        total_chars = len(lines[0]) + 1
        for row in range(top, bottom + 1):
            line = "\t".join(
                self._tsv_text(self.results.item(row, column).text())
                if self.results.item(row, column) is not None
                else ""
                for column in range(left, right + 1)
            )
            if total_chars + len(line) + 1 > self.MAX_CLIPBOARD_CHARS:
                QMessageBox.warning(
                    self,
                    "Слишком большой результат",
                    "Копирование остановлено на безопасном лимите 5 МБ.",
                )
                break
            lines.append(line)
            total_chars += len(line) + 1
        QApplication.clipboard().setText("\n".join(lines))

    def apply_application_theme(self, theme: ThemeDefinition) -> None:
        self.highlighter.apply_theme(theme)

    @staticmethod
    def _tsv_text(text: str) -> str:
        return (
            str(text)
            .replace("\r\n", "\\n")
            .replace("\r", "\\n")
            .replace("\n", "\\n")
            .replace("\t", "\\t")
        )

    @classmethod
    def _cell_text(cls, value: Any) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bytes):
            text = f"\\x{value.hex()}"
        elif isinstance(value, (dict, list, tuple)):
            try:
                text = json.dumps(value, ensure_ascii=False, default=str)
            except (TypeError, ValueError):
                text = str(value)
        elif isinstance(value, (dt.date, dt.time)):
            text = (
                value.isoformat(sep=" ")
                if isinstance(value, dt.datetime)
                else value.isoformat()
            )
        else:
            text = str(value)
        if len(text) > cls.MAX_CELL_CHARS:
            return text[: cls.MAX_CELL_CHARS] + "…"
        return text


__all__ = ["SqlToolsTab", "format_sql_error"]
