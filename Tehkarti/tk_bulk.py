"""Bulk parameter editing and norm calculation for the open TechKart tree.

The tree remains the editor's source of truth.  Neither dialog writes a TK file;
the normal Save button persists the resulting tree.
"""

from __future__ import annotations

import ast
import copy
import math
from dataclasses import dataclass, field

from PyQt5 import QtCore, QtWidgets

from project_cust_38 import Cust_Functions as F
from project_cust_38 import Cust_config as CFG
from project_cust_38 import operacii


@dataclass
class ParamUse:
    item: QtWidgets.QTreeWidgetItem
    names: list[str]
    values: list[str]
    index: int
    label: str
    original_raw: str
    kind: str
    enabled: bool = True

    @property
    def value(self) -> str:
        return self.values[self.index]


@dataclass
class ParamGroup:
    name: str
    uses: list[ParamUse] = field(default_factory=list)

    @property
    def kinds(self):
        return {use.kind for use in self.uses}


def operations(tree):
    for i in range(tree.topLevelItemCount()):
        card = tree.topLevelItem(i)
        if card.text(20) != '0':
            continue
        for j in range(card.childCount()):
            op = card.child(j)
            if op.text(20) == '1':
                yield op


def declared_params(window, item):
    xl = window.xl_formulas
    if item.text(20) == '1':
        name = item.text(0)
        if xl.check_op(name, True):
            return [(key, 'float') for key in xl.get_op_params(name)]
        if window.place.poki == 0 and name in operacii.Data_oper_norm.DICT_OPERS_CALC:
            return [(key, str(value.get('type', ''))) for key, value in
                    operacii.Data_oper_norm.DICT_OPERS_CALC[name].items()]
        var_string = window.DICT_OPERS.get(name, {}).get('Vars') or ''
        return [split_name_type(value) for value in var_string.split(';') if value.strip()]

    parent = item.parent()
    op_name, pereh_name = parent.text(0), item.text(0)
    if xl.check_per(op_name, pereh_name, True):
        return [(key, 'float') for key in xl.get_per_params(op_name, pereh_name)]
    path = xl.get_pereh_txt_path(op_name)
    if not F.existence_file_c(path):
        return []
    for row in F.open_file_c(path, False, '|'):
        if row[0] == pereh_name and len(row) > 2:
            return [split_name_type(value) for value in row[2].split(';') if value.strip()]
    return []


def split_name_type(value):
    name, _, kind = value.partition(':')
    return name.strip(), kind.strip().lower()


def stored_values(item, names):
    raw = item.text(14)
    values = raw.split('$') if raw else [''] * len(names)
    if len(values) != len(names):
        raise ValueError(f'Ожидалось {len(names)} значений, в ТК найдено {len(values)}')
    return values


def item_label(item):
    if item.text(20) == '2':
        parent = item.parent()
        return f'{parent.text(2)} — {parent.text(0)} → {item.text(0)}'
    return f'{item.text(2)} — {item.text(0)}'


def collect_parameters(window):
    groups = {}
    warnings = []
    for op in operations(window.ui.tree):
        for item in [op] + [op.child(i) for i in range(op.childCount()) if op.child(i).text(20) == '2']:
            try:
                descriptors = declared_params(window, item)
                names = [name for name, _ in descriptors]
                if len(names) != len(set(names)):
                    raise ValueError('Повторяется имя параметра в одном элементе')
                if not names:
                    if item.text(14):
                        warnings.append(f'{item_label(item)}: не найдено описание параметров')
                    continue
                values = stored_values(item, names)
                for index, (name, kind) in enumerate(descriptors):
                    if not name:
                        continue
                    group = groups.setdefault(name, ParamGroup(name))
                    group.uses.append(ParamUse(item, names, values[:], index, item_label(item), item.text(14), kind,
                                               enabled=';' not in values[index]))
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                warnings.append(f'{item_label(item)}: {exc}')
    return sorted(groups.values(), key=lambda group: group.name.casefold()), warnings


def numeric_kind(kind):
    return kind in ('int', 'float', "<class 'float'>", "<class 'int'>")


def validate_value(value, kind):
    value = value.strip()
    if not value or any(char in value for char in '$|;\r\n') or value in ('-', '+') or value.startswith("f'"):
        raise ValueError('Укажите одно значение без разделителей $, |, ;')
    if numeric_kind(kind):
        number = float(value.replace(',', '.'))
        if not math.isfinite(number) or ('int' in kind and not number.is_integer()):
            raise ValueError('Требуется корректное число указанного типа')
        return value.replace(',', '.')
    return value


class BulkParametersDialog(QtWidgets.QDialog):
    def __init__(self, groups, warnings, parent):
        super().__init__(parent)
        self.groups = groups
        self.setWindowTitle('Общие параметры текущей техкарты')
        self.resize(1050, 650)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel('Выберите параметры и места применения. Разные текущие значения не заменяются автоматически.'))
        self.table = QtWidgets.QTableWidget(len(groups), 5, self)
        self.table.setHorizontalHeaderLabels(['Применить', 'Параметр', 'Новое значение', 'Текущие значения', 'Операции / переходы'])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
        self.table.setColumnWidth(0, 90)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 145)
        self.table.setColumnWidth(3, 175)
        for row, group in enumerate(groups):
            values = {use.value for use in group.uses if use.value not in ('', '-')}
            kinds = group.kinds
            incompatible = len(kinds) > 1 and not all(numeric_kind(kind) for kind in kinds)
            conflict = len(values) > 1 or incompatible
            toggle = QtWidgets.QTableWidgetItem()
            toggle.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
            toggle.setCheckState(QtCore.Qt.Unchecked if conflict else QtCore.Qt.Checked)
            self.table.setItem(row, 0, toggle)
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(
                group.name + (f' ({", ".join(sorted(kinds))})' if any(kinds) else '')))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(''))
            current = 'РАЗЛИЧАЮТСЯ: ' + ', '.join(sorted(values)) if len(values) > 1 else (next(iter(values)) if values else 'не заполнено')
            if incompatible:
                current += '; разные типы'
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(current))
            self.table.setItem(row, 4, QtWidgets.QTableWidgetItem('; '.join(use.label for use in group.uses)))
        layout.addWidget(self.table)
        layout.addWidget(QtWidgets.QLabel('Места применения выбранного параметра (многозначные параметры недоступны для общей замены):'))
        self.targets = QtWidgets.QTreeWidget(self)
        self.targets.setHeaderLabels(['Операция / переход', 'Сейчас'])
        self.targets.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        layout.addWidget(self.targets)
        if warnings:
            label = QtWidgets.QLabel('Пропущено при сборе: ' + '; '.join(warnings), self)
            label.setWordWrap(True)
            layout.addWidget(label)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Apply | QtWidgets.QDialogButtonBox.Cancel, self)
        buttons.button(QtWidgets.QDialogButtonBox.Apply).setText('Применить к выбранным')
        buttons.button(QtWidgets.QDialogButtonBox.Cancel).setText('Отмена')
        buttons.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.apply_values)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.table.itemSelectionChanged.connect(self.show_targets)
        self.targets.itemChanged.connect(self.target_changed)
        if groups:
            self.table.selectRow(0)

    def show_targets(self):
        self.targets.blockSignals(True)
        self.targets.clear()
        row = self.table.currentRow()
        if row >= 0:
            for use in self.groups[row].uses:
                typed_value = use.value or 'не заполнено'
                if use.kind:
                    typed_value += f' ({use.kind})'
                item = QtWidgets.QTreeWidgetItem(self.targets, [use.label, typed_value])
                item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
                item.setCheckState(0, QtCore.Qt.Checked if use.enabled else QtCore.Qt.Unchecked)
                if ';' in use.value:
                    item.setFlags(QtCore.Qt.ItemIsEnabled)
                    item.setToolTip(0, 'Многозначный параметр меняется в диалоге отдельной операции')
        self.targets.blockSignals(False)

    def target_changed(self, item, column):
        row = self.table.currentRow()
        if row >= 0:
            self.groups[row].uses[self.targets.indexOfTopLevelItem(item)].enabled = item.checkState(0) == QtCore.Qt.Checked

    def apply_values(self):
        changes = {}
        try:
            for row, group in enumerate(self.groups):
                if self.table.item(row, 0).checkState() != QtCore.Qt.Checked:
                    continue
                raw_value = self.table.item(row, 2).text().strip()
                if not raw_value:
                    continue
                for use in group.uses:
                    if not use.enabled:
                        continue
                    value = validate_value(raw_value, use.kind)
                    key = use.item
                    if key not in changes:
                        changes[key] = (use.names, use.values[:])
                    names, values = changes[key]
                    if names != use.names:
                        raise ValueError(f'{use.label}: изменился набор параметров')
                    values[use.index] = value
            if not changes:
                raise ValueError('Нет выбранных изменений')
            for item, (names, values) in changes.items():
                originals = [use.original_raw for group in self.groups for use in group.uses if use.item is item]
                if not originals or any(item.text(14) != raw for raw in originals):
                    raise ValueError('Техкарта изменилась после открытия окна. Откройте список заново')
        except (ValueError, OverflowError) as exc:
            QtWidgets.QMessageBox.warning(self, 'Общие параметры', str(exc))
            return
        for item, (names, values) in changes.items():
            item.setText(14, '$'.join(values))
            item.setText(16, str(dict(zip(names, values))))
        self.changed_count = len(changes)
        self.accept()


def params_for_calc(window, item):
    descriptors = declared_params(window, item)
    names = [name for name, _ in descriptors]
    if not names and item.text(16):
        data = ast.literal_eval(item.text(16))
        if isinstance(data, dict):
            names = list(data)
    if not names:
        return None
    values = stored_values(item, names)
    if any(value.strip() in ('', '-', '+') or value.startswith("f'") for value in values):
        raise ValueError(f'{item_label(item)}: не все параметры заполнены')
    for (name, kind), value in zip(descriptors, values):
        if kind in ('int', 'float', "<class 'float'>", "<class 'int'>"):
            for part in value.split(';'):
                try:
                    number = float(part.replace(',', '.'))
                except ValueError:
                    raise ValueError(f'{item_label(item)}: {name} не число') from None
                if not math.isfinite(number) or ('int' in kind and not number.is_integer()):
                    raise ValueError(f'{item_label(item)}: {name} не число указанного типа')
    return [names, values]


def number_or_error(value, label):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
        raise ValueError(f'{label}: формула вернула некорректное время ({value!r})')
    return value


def merge_materials(old, calculated):
    result = [part for part in old.split('{') if part]
    for part in calculated.split('{'):
        if not part:
            continue
        code = part.split('$', 1)[0]
        if not code or len(part.split('$')) < 4:
            raise ValueError('Формула вернула некорректную строку материала')
        for index, prior in enumerate(result):
            if prior.split('$', 1)[0] == code:
                result[index] = part
                break
        else:
            result.append(part)
    return '{'.join(result)


def check_formula_sources(window):
    """Do not silently substitute legacy formulas for approved Excel formulas."""
    xl = window.xl_formulas
    xl.get_actual_srv_data()
    missing = []
    for op in operations(window.ui.tree):
        if xl.check_approved(operation=op.text(0)) and not xl.check_op(op.text(0), True):
            missing.append(item_label(op))
        for index in range(op.childCount()):
            pereh = op.child(index)
            if pereh.text(20) == '2' and xl.check_approved(operation=op.text(0), pereh=pereh.text(0)) \
                    and not xl.check_per(op.text(0), pereh.text(0), True):
                missing.append(item_label(pereh))
    if missing:
        QtWidgets.QMessageBox.warning(window, 'Excel формулы недоступны',
                                      'Не удалось получить действующие параметры формул для:\n' + '\n'.join(missing[:20]))
        return False
    return True


def confirm_editor_state(window):
    return QtWidgets.QMessageBox.question(
        window, 'Текущая техкарта',
        'Если вы правили обычные таблицы операции, переходов или материалов, сначала нажмите их «Применить».\n'
        'Продолжить работу с текущими значениями дерева ТК?',
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
        QtWidgets.QMessageBox.Cancel,
    ) == QtWidgets.QMessageBox.Yes


def recalc_one(window, op, with_materials):
    if op.text(7).startswith('=') or op.text(6).startswith('='):
        return None, 'ручная норма (=)'
    try:
        op_params = params_for_calc(window, op)
    except ValueError as exc:
        op_params = None
        missing_operation_params = str(exc)
    else:
        missing_operation_params = ''
    changes = []
    total = 0
    has_transition_time = False
    material = op.text(10)
    if with_materials and op_params:
        result = operacii.materiali(window, op.text(0), copy.deepcopy(op_params))
        if result is not None:
            material = merge_materials(material, result)

    for index in range(op.childCount()):
        pereh = op.child(index)
        if pereh.text(20) != '2':
            continue
        pereh_params = params_for_calc(window, pereh)
        if pereh_params:
            time = operacii.vremya_tsht_perehodi(op.text(0), pereh.text(0),
                                                 copy.deepcopy(pereh_params),
                                                 op.text(14).split('$') if op.text(14) else [])
            if time is None and not window.xl_formulas.check_approved(
                    operation=op.text(0), pereh=pereh.text(0)) and F.is_numeric(pereh.text(7)):
                time = number_or_error(F.valm(pereh.text(7)), item_label(pereh))
            else:
                time = number_or_error(time, item_label(pereh))
                changes.append((pereh, 7, str(time)))
        elif F.is_numeric(pereh.text(7)):
            time = number_or_error(F.valm(pereh.text(7)), item_label(pereh))
        else:
            raise ValueError(f'{item_label(pereh)}: не задано время и нет параметров')
        total += time
        has_transition_time = True
        if with_materials and pereh_params:
            result = operacii.materiali(window, op.text(0), copy.deepcopy(pereh_params))
            if result is not None:
                material = merge_materials(material, result)

    operation_time = 0
    setup_time = None
    if op_params:
        result = operacii.vremya_tsht(op.text(0), copy.deepcopy(op_params))
        if isinstance(result, tuple) and len(result) == 2:
            operation_time, setup_time = result
            setup_time = number_or_error(setup_time, item_label(op) + ' Тпз')
        else:
            operation_time = result
        if operation_time is None and not window.xl_formulas.check_approved(operation=op.text(0)):
            operation_time = 0
        else:
            operation_time = number_or_error(operation_time, item_label(op))
    if not operation_time and not has_transition_time:
        if with_materials and material != op.text(10):
            return [(op, 10, material)], 'нет расчёта времени; материалы пересчитаны'
        return None, 'нет рассчитанного времени или переходов'
    time = operation_time if operation_time > 0 else total
    if time == 0 and window.xl_formulas.check_strict_calc(operation=op.text(0)):
        raise ValueError('Операция с обязательным расчётом вернула нулевое Тшт')
    limit = CFG.Config.place.limit_time_on_naryad
    if time >= limit:
        raise ValueError(f'Тшт {time} превышает лимит {limit}')
    changes.append((op, 7, str(round(time, 3))))
    if setup_time is not None:
        changes.append((op, 6, str(setup_time)))
    if with_materials and material != op.text(10):
        changes.append((op, 10, material))
    source = 'формула операции' if operation_time > 0 else 'сумма переходов'
    message = f'Тшт: {op.text(7)} → {round(time, 3)} ({source})'
    if material != op.text(10):
        message += '; материалы пересчитаны'
    if missing_operation_params:
        message += '; ' + missing_operation_params
    return changes, message


def show_bulk_parameters(window):
    if not any(operations(window.ui.tree)):
        QtWidgets.QMessageBox.information(window, 'Общие параметры', 'В текущей техкарте нет операций')
        return
    if not confirm_editor_state(window) or not check_formula_sources(window):
        return
    groups, warnings = collect_parameters(window)
    if not groups:
        QtWidgets.QMessageBox.information(window, 'Общие параметры', 'Параметры не найдены. ' + '; '.join(warnings))
        return
    dialog = BulkParametersDialog(groups, warnings, window)
    if dialog.exec_() == QtWidgets.QDialog.Accepted:
        window.mark_tk_modified_status()
        window.obnovit_param_tablic()
        QtWidgets.QMessageBox.information(window, 'Общие параметры',
                                          f'Параметры изменены в {dialog.changed_count} элементах ТК. Для записи нажмите «Сохранить».')


def show_bulk_recalc(window):
    op_items = list(operations(window.ui.tree))
    if not op_items:
        QtWidgets.QMessageBox.information(window, 'Пересчёт', 'В текущей техкарте нет операций')
        return
    if not confirm_editor_state(window) or not check_formula_sources(window):
        return
    dialog = QtWidgets.QDialog(window)
    dialog.setWindowTitle('Пересчёт текущей техкарты')
    layout = QtWidgets.QVBoxLayout(dialog)
    layout.addWidget(QtWidgets.QLabel(f'Рассчитать {len(op_items)} операций и их переходы?'))
    materials = QtWidgets.QCheckBox('Пересчитать также нормы материалов', dialog)
    materials.setChecked(True)
    layout.addWidget(materials)
    buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, dialog)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    if dialog.exec_() != QtWidgets.QDialog.Accepted:
        return

    progress = QtWidgets.QProgressDialog('Расчёт операций…', 'Отмена', 0, len(op_items), window)
    progress.setWindowModality(QtCore.Qt.ApplicationModal)
    progress.setMinimumDuration(0)
    changes, report = [], []
    for index, op in enumerate(op_items):
        progress.setLabelText(item_label(op))
        progress.setValue(index)
        QtWidgets.QApplication.processEvents()
        if progress.wasCanceled():
            return
        try:
            result, message = recalc_one(window, op, materials.isChecked())
            if result:
                changes.extend(result)
            report.append((item_label(op), message, bool(result)))
        except Exception as exc:
            report.append((item_label(op), f'ОШИБКА: {exc}', False))
    progress.setValue(len(op_items))
    if progress.wasCanceled():
        return
    report_dialog = QtWidgets.QDialog(window)
    report_dialog.setWindowTitle('Результат пересчёта')
    report_dialog.resize(900, 500)
    layout = QtWidgets.QVBoxLayout(report_dialog)
    layout.addWidget(QtWidgets.QLabel('Изменения рассчитаны в памяти. Применить их к дереву техкарты?'))
    table = QtWidgets.QTableWidget(len(report), 2, report_dialog)
    table.setHorizontalHeaderLabels(['Операция', 'Результат'])
    table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
    table.setColumnWidth(0, 300)
    for row, (label, message, _) in enumerate(report):
        table.setItem(row, 0, QtWidgets.QTableWidgetItem(label))
        table.setItem(row, 1, QtWidgets.QTableWidgetItem(message))
    layout.addWidget(table)
    buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, report_dialog)
    buttons.button(QtWidgets.QDialogButtonBox.Ok).setText('Применить успешные')
    buttons.accepted.connect(report_dialog.accept)
    buttons.rejected.connect(report_dialog.reject)
    buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(bool(changes))
    layout.addWidget(buttons)
    if report_dialog.exec_() != QtWidgets.QDialog.Accepted:
        return
    for item, col, value in changes:
        item.setText(col, value)
    window.mark_tk_modified_status()
    window.obnovit_param_tablic()
    QtWidgets.QMessageBox.information(window, 'Пересчёт',
                                      'Результат применён в дереве техкарты. Для записи нажмите «Сохранить».')
