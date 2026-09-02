"""MES bridge for Adaptive Schedule 0.5, stage 5.

The legacy QTableWidget remains populated and is the fallback.  The adapter reads
the already calculated ``CMS.Gant`` snapshot; it does not introduce extra SQL
reads.  Database writeback stays opt-in.
"""

from __future__ import annotations

import datetime
import os
from collections.abc import Hashable, Sequence
from dataclasses import replace
from typing import TYPE_CHECKING

from PyQt5 import QtCore

import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_mes as CMS
from data_class import Data_plan as DTCLS

from adaptive_schedule import (
    CommitResult,
    ScheduleCommand,
    ScheduleModel,
    ScheduleServices,
    ScheduleWidget,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)
from mes_adapter_core import MesAdapterConfig, MesGantAdapterCore

if TYPE_CHECKING:
    from MKart import mywindow


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() not in {"0", "false", "no", "off"}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)).replace(",", "."))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


ADAPTIVE_GANT_ENABLED = _env_flag("MES_ADAPTIVE_GANT", True)
WRITEBACK_ENABLED = _env_flag("MES_ADAPTIVE_GANT_WRITEBACK", False)
DRAG_ENABLED = _env_flag("MES_ADAPTIVE_GANT_DRAG", True)
FIT_TO_WIDTH = _env_flag("MES_ADAPTIVE_GANT_FIT", True)
SEPARATE_ROWS = _env_flag("MES_ADAPTIVE_GANT_SEPARATE_ROWS", True)
NORM_SHIFT_MINUTES = max(1.0, _env_float("MES_NORM_SHIFT_MINUTES", 480.0))
DEFAULT_CAPACITY_HOURS = max(
    0.0,
    _env_float("MES_ADAPTIVE_GANT_DEFAULT_CAPACITY", 8.0),
)
PADDING_DAYS = max(0, _env_int("MES_ADAPTIVE_GANT_PADDING_DAYS", 2))
RANGE_MODE = os.getenv("MES_ADAPTIVE_GANT_RANGE", "content").strip().casefold()


class MesGantAdapter(MesGantAdapterCore):
    """Bind the Qt-free converter to concrete MES plan/fact type objects."""

    def __init__(self, gant: CMS.Gant, *, writeback: bool = False) -> None:
        timezone = datetime.datetime.now().astimezone().tzinfo
        if timezone is None:
            raise RuntimeError("Local timezone is unavailable")
        super().__init__(
            gant,
            plan_type=CMS.Types_day_gant.plan,
            fact_type=CMS.Types_day_gant.fact,
            config=MesAdapterConfig(
                timezone=timezone,
                norm_shift_minutes=NORM_SHIFT_MINUTES,
                default_capacity_hours=DEFAULT_CAPACITY_HOURS,
                drag_enabled=DRAG_ENABLED,
                writeback_enabled=writeback,
                fit_to_width=FIT_TO_WIDTH,
                separate_rows=SEPARATE_ROWS,
                range_mode=RANGE_MODE,
                padding_days=PADDING_DAYS,
            ),
        )


class MesScheduleValidator:
    """Keep client-specific edit restrictions outside the reusable widget."""

    def validate(
        self,
        command: ScheduleCommand,
        snapshot: ScheduleModel,
        proposed: ScheduleModel,
    ) -> ValidationResult:
        issues: list[ValidationIssue] = []
        before = snapshot.item_by_id
        after = proposed.item_by_id
        for item_id in command.touched_item_ids:
            old = before.get(item_id)
            new = after.get(item_id)
            if old is None or new is None:
                continue
            if old.lane_id != new.lane_id:
                issues.append(
                    ValidationIssue(
                        ValidationSeverity.FORBIDDEN,
                        "Перенос между подразделениями в MES запрещён",
                        frozenset((item_id,)),
                        "mes_cross_lane",
                    )
                )
            if old.layer != CMS.Types_day_gant.plan.name:
                issues.append(
                    ValidationIssue(
                        ValidationSeverity.FORBIDDEN,
                        "Фактические значения доступны только для просмотра",
                        frozenset((item_id,)),
                        "mes_fact_readonly",
                    )
                )
        return ValidationResult(tuple(issues))


class MesScheduleRepository:
    """Local preview by default; explicit opt-in for legacy date writeback."""

    def __init__(self, initial: ScheduleModel, *, writeback: bool) -> None:
        self._model = initial
        self.writeback = writeback

    def commit(
        self,
        commands: Sequence[ScheduleCommand],
        proposed: ScheduleModel,
        expected_version: str | int | None,
    ) -> CommitResult:
        del commands
        if expected_version != self._model.version:
            return CommitResult(
                False,
                self._model,
                self._model.version,
                "Гант уже обновлён другим действием",
            )

        if not self.writeback:
            return self._accept_local(proposed, expected_version)

        touched = [
            item
            for item in proposed.items
            if item.id in self._model.item_by_id
            and (
                item.start != self._model.item_by_id[item.id].start
                or item.end != self._model.item_by_id[item.id].end
            )
        ]
        for item in touched:
            metadata = item.metadata
            if not metadata.get("mes_writeback"):
                return CommitResult(
                    False,
                    self._model,
                    self._model.version,
                    f"Этап {metadata.get('mes_table', item.id)} нельзя сохранить",
                )
            if item.start is None or item.end is None:
                return CommitResult(
                    False,
                    self._model,
                    self._model.version,
                    "MES требует обе границы планового этапа",
                )
            table = metadata.get("mes_table")
            primary = metadata.get("mes_primary_field")
            start_field = metadata.get("mes_start_field")
            end_field = metadata.get("mes_end_field")
            position_id = metadata.get("mes_position_id")
            if not all((table, primary, start_field, end_field, position_id)):
                return CommitResult(
                    False,
                    self._model,
                    self._model.version,
                    "Не хватает MES-метаданных для сохранения",
                )
            start_value = item.start.date().isoformat()
            end_value = (item.end - datetime.timedelta(days=1)).date().isoformat()
            result = CSQ.custom_request_c(
                DTCLS.db_kplan,
                f"UPDATE {table} SET {start_field} = ?, {end_field} = ? "
                f"WHERE {primary} = ?;",
                list_of_lists_c=[[start_value, end_value, position_id]],
            )
            if not result:
                return CommitResult(
                    False,
                    self._model,
                    self._model.version,
                    f"Не удалось сохранить этап {table}",
                )

        version = int(expected_version or 0) + 1
        self._model = replace(proposed, version=version)
        return CommitResult(True, self._model, version, "Даты этапов сохранены в MES")

    def _accept_local(
        self,
        proposed: ScheduleModel,
        expected_version: str | int | None,
    ) -> CommitResult:
        version = int(expected_version or 0) + 1
        self._model = replace(proposed, version=version)
        return CommitResult(
            True,
            self._model,
            version,
            "Локальный предпросмотр: даты в MES не сохранены",
        )


class MesAdaptiveGantBridge(QtCore.QObject):
    def __init__(self, app_self: "mywindow") -> None:
        super().__init__(app_self)
        self.app_self = app_self
        self.legacy_table = app_self.ui.tbl_preview
        self.model = ScheduleModel()
        self.revision = 0
        self._syncing_selection = False
        self.widget = ScheduleWidget(parent=app_self.ui.fr_gant_local_tbl)
        self.widget.setObjectName("adaptive_mes_gant")
        app_self.ui.verticalLayout_35.addWidget(self.widget)
        self.widget.selectionChanged.connect(self._sync_legacy_selection)
        self.widget.commandCommitted.connect(self._on_command_committed)

    def update(self, gant: CMS.Gant) -> None:
        adapter = MesGantAdapter(gant, writeback=WRITEBACK_ENABLED)
        self.revision += 1
        self.model = adapter.to_model(self.revision)
        self.widget.set_view_options(adapter.view_options(self.model))
        self.widget.set_data(self.model)
        self.widget.set_services(
            ScheduleServices(
                validator=MesScheduleValidator(),
                repository=MesScheduleRepository(
                    self.model,
                    writeback=WRITEBACK_ENABLED,
                ),
            )
        )
        if WRITEBACK_ENABLED:
            message = "План перемещается по производственным дням и сохраняется в MES"
        else:
            message = "План перемещается локально; запись в MES отключена"
        self.widget.set_status_message(message)
        self.widget.setVisible(True)
        self.legacy_table.setVisible(False)

    def show_legacy(self) -> None:
        self.widget.setVisible(False)
        self.legacy_table.setVisible(True)

    def _sync_legacy_selection(self, item_ids: tuple[Hashable, ...]) -> None:
        if self._syncing_selection or not item_ids:
            return
        item = self.model.item_by_id.get(item_ids[0])
        if item is None:
            return
        metadata = item.metadata
        table_context = CQT.TableContext(self.legacy_table)
        target_row = None
        for row in table_context.rows():
            try:
                matches = (
                    int(row.value("_id_poz")) == metadata["mes_position_id"]
                    and row.value("_tbl_name") == metadata["mes_table"]
                    and row.value("_type_day") == metadata["mes_type"]
                )
            except (KeyError, TypeError, ValueError):
                continue
            if matches:
                target_row = row.i
                break
        if target_row is None:
            return

        target_column = 0
        for column_name, column_index in table_context.nf.items():
            if (
                isinstance(column_name, CMS.Month_cld_day)
                and item.start is not None
                and column_name.dt_datetime.date() == item.start.date()
            ):
                target_column = column_index
                break
        self._syncing_selection = True
        try:
            self.legacy_table.setCurrentCell(target_row, target_column)
        finally:
            self._syncing_selection = False

    def _on_command_committed(self, result) -> None:
        self.model = result.model
        if WRITEBACK_ENABLED:
            QtCore.QTimer.singleShot(0, self._reload_from_mes)

    def _reload_from_mes(self) -> None:
        import kal_plan as KPL

        position_ids = {
            item.metadata.get("mes_position_id") for item in self.model.items
        }
        position_ids.discard(None)
        if position_ids:
            KPL.update_local_graf(True, int(next(iter(position_ids))), True)


def update_local_gant(app_self: "mywindow", gant: CMS.Gant) -> bool:
    """Mount or refresh the adaptive view; return False for legacy fallback."""

    bridge = getattr(app_self, "_adaptive_mes_gant_bridge", None)
    if not ADAPTIVE_GANT_ENABLED:
        if bridge is not None:
            bridge.show_legacy()
        return False
    try:
        if bridge is None:
            bridge = MesAdaptiveGantBridge(app_self)
            app_self._adaptive_mes_gant_bridge = bridge
        bridge.update(gant)
        return True
    except Exception as error:
        print(f"Adaptive Gant fallback: {error}")
        if bridge is not None:
            bridge.show_legacy()
        else:
            app_self.ui.tbl_preview.setVisible(True)
        return False
