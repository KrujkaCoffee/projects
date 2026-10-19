from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field

from PyQt5 import QtCore, QtWidgets, Qt, QtGui

from project_cust_38 import Cust_Functions as F
from project_cust_38 import Cust_config as CFG
from project_cust_38 import operacii


@dataclass(frozen=True)
class ChoiceOption:
    label: str
    note: str = ''
    show: tuple[str, ...] | None = None


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
    choices: dict[str, ChoiceOption] = field(default_factory=dict)
    name: str = ''
    symbol: str = ''

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


def choices_for_item(window, item):
    xl = window.xl_formulas
    if item.text(20) == '1':
        name = item.text(0)
        if xl.check_op(name, True):
            definitions = xl.convert_old_struct(name)
        elif window.place.poki == 0:
            definitions = operacii.Data_oper_norm.DICT_OPERS_CALC.get(name, {})
        else:
            definitions = {}
    else:
        parent = item.parent()
        operation, transition = parent.text(0), item.text(0)
        definitions = xl.convert_old_struct(operation, transition) if xl.check_per(operation, transition, True) else {}

    result = {}
    for name, definition in definitions.items():
        if not isinstance(definition, dict):
            continue
        options = {}
        for key, entry in definition.get('vals', {}).items():
            if not isinstance(entry, dict) or 'val' not in entry:
                continue
            show = entry.get('show')
            if isinstance(show, (list, tuple)):
                show = tuple(show)
            else:
                show = None
            options[str(key)] = ChoiceOption(str(entry['val']), str(entry.get('prim', '')), show)
        if options:
            result[name] = options
    return result


def excel_symbols_for_item(window, item):
    xl = window.xl_formulas
    data = xl.xl_srv_data if isinstance(xl.xl_srv_data, dict) else {}
    if item.text(20) == '1':
        operation = item.text(0)
        if not xl.check_op(operation, True):
            return {}
        struct = data.get('Операции', {}).get(operation, {})
    else:
        operation, transition = item.parent().text(0), item.text(0)
        if not xl.check_per(operation, transition, True):
            return {}
        key = xl.srv_key_oper(operation, transition)
        struct = data.get('Переходы', {}).get(key, {})

    if not isinstance(struct, dict):
        return {}
    symbols = struct.get('vars', {})
    result = {}
    for name, cell in struct.get('desc', {}).items():
        if isinstance(cell, str) and cell.startswith('D') and cell[1:].isdigit():
            symbol = symbols.get(f'A{cell[1:]}', '')
            if isinstance(symbol, str) and symbol.strip():
                result[name] = symbol.strip()
    return result


def split_name_type(value):
    name, _, kind = value.partition(':')
    return name.strip(), kind.strip().lower()


def stored_values(item, names):
    raw = item.text(14)
    values = raw.split('$') if raw else [''] * len(names)
    if len(values) != len(names):
        if len(values) < len(names):
            raise ValueError(f'Ожидалось {len(names)} значений, в ТК найдено {len(values)}')
        return values[:len(names)]

    return values


def item_label(item):
    if item.text(20) == '2':
        parent = item.parent()
        return f'{parent.text(2)} — {parent.text(0)} → {item.text(0)}'
    return f'{item.text(2)} — {item.text(0)}'


def collect_parameter_uses(window):
    uses = []
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
                choices = choices_for_item(window, item)
                symbols = excel_symbols_for_item(window, item)
                for index, (name, kind) in enumerate(descriptors):
                    if not name:
                        continue
                    uses.append(ParamUse(item, names, values[:], index, item_label(item), item.text(14), kind,
                                         enabled=';' not in values[index], choices=choices.get(name, {}),
                                         name=name, symbol=symbols.get(name, '')))
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                warnings.append(f'{item_label(item)}: {exc}')
    return uses, warnings


def group_parameter_uses(uses, mode='name'):
    groups = {}
    for use in uses:
        name = use.name or use.names[use.index]
        if mode == 'symbol' and use.symbol:
            key = ('symbol', use.symbol)
            title = use.symbol
        else:
            key = ('name', name)
            title = f'{name} (без обозначения)' if mode == 'symbol' else name
        groups.setdefault(key, ParamGroup(title)).uses.append(use)
    return sorted(groups.values(), key=lambda group: group.name.casefold())


def collect_parameters(window, mode='name'):
    uses, warnings = collect_parameter_uses(window)
    return group_parameter_uses(uses, mode), warnings


def group_choices(group):
    choices = {}
    for use in group.uses:
        for key, option in use.choices.items():
            choices.setdefault((key, option.label), option)
    return choices


def display_current(use):
    value = use.value
    if value in ('', '-'):
        return 'не заполнено'
    option = use.choices.get(value)
    return f'{option.label} [{value}]' if option else value


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
        self.uses = [use for group in groups for use in group.uses]
        self.groups = []
        self.mode = 'name'
        self.setWindowTitle('Общие параметры текущей техкарты')
        self.resize(1050, 650)
        layout = QtWidgets.QVBoxLayout(self)
        mode_line = QtWidgets.QHBoxLayout()
        mode_line.addWidget(QtWidgets.QLabel('Группировка:'))
        self.mode_selector = QtWidgets.QComboBox(self)
        self.mode_selector.addItem('Сгруппировать по наименованию', 'name')
        self.mode_selector.addItem('Сгруппировать по обозначению', 'symbol')
        mode_line.addWidget(self.mode_selector)
        mode_line.addStretch()
        layout.addLayout(mode_line)
        layout.addWidget(QtWidgets.QLabel('Выберите параметры и места применения. Разные текущие значения не заменяются автоматически.'))
        self.table = QtWidgets.QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(['Применить', 'Параметр', 'Новое значение', 'Текущие значения', 'Операции / переходы'])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
        self.table.setColumnWidth(0, 90)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 145)
        self.table.setColumnWidth(3, 175)

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
        self.mode_selector.currentIndexChanged.connect(self.change_mode)
        self.fill_groups(groups)

    def use_label(self, use):
        if self.mode == 'symbol':
            return f'{use.label} — {use.name or use.names[use.index]}'
        return use.label

    def fill_groups(self, groups):
        self.groups = groups
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self.table.setRowCount(len(groups))
        for row, group in enumerate(groups):
            values = {display_current(use) for use in group.uses if use.value not in ('', '-')}
            kinds = group.kinds
            incompatible = len(kinds) > 1 and not all(numeric_kind(kind) for kind in kinds)
            variants = {frozenset((key, option.label) for key, option in use.choices.items())
                        for use in group.uses}
            choices = group_choices(group)
            conflict = len(values) > 1 or incompatible or (bool(choices) and len(variants) > 1)
            toggle = QtWidgets.QTableWidgetItem()
            toggle.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
            toggle.setCheckState(QtCore.Qt.Unchecked if conflict else QtCore.Qt.Checked)
            self.table.setItem(row, 0, toggle)
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(
                group.name + (' (варианты)' if choices else
                              (f' ({", ".join(sorted(kinds))})' if any(kinds) else ''))))
            if choices:
                selector = QtWidgets.QComboBox(self.table)
                selector.addItem('Выберите вариант…', None)
                for (key, label), option in choices.items():
                    selector.addItem(f'{label} [{key}]', (key, label))
                    if option.note:
                        selector.setItemData(selector.count() - 1, option.note, QtCore.Qt.ToolTipRole)
                self.table.setCellWidget(row, 2, selector)
            else:
                self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(''))
            current = 'РАЗЛИЧАЮТСЯ: ' + ', '.join(sorted(values)) if len(values) > 1 else (next(iter(values)) if values else 'не заполнено')
            if choices and len(variants) > 1:
                current += '; варианты различаются — проверьте места применения'
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(current))
            self.table.setItem(row, 4, QtWidgets.QTableWidgetItem('; '.join(self.use_label(use) for use in group.uses)))

        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                if col != 2:
                    cell = self.table.item(row, col)
                    if cell is not None:
                        cell.setFlags(cell.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                        cell.setBackground(QtGui.QColor("#e0e0e0"))
        if groups:
            self.table.selectRow(0)
        self.table.blockSignals(False)
        self.show_targets()

    def change_mode(self):
        mode = self.mode_selector.currentData()
        if mode == self.mode:
            return
        if any((self.table.cellWidget(row, 2).currentData() is not None
                if self.table.cellWidget(row, 2) is not None else self.table.item(row, 2).text().strip())
               for row in range(self.table.rowCount())):
            answer = QtWidgets.QMessageBox.question(
                self, 'Группировка параметров',
                'При смене группировки введённые значения будут сброшены. Продолжить?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
                QtWidgets.QMessageBox.Cancel)
            if answer != QtWidgets.QMessageBox.Yes:
                self.mode_selector.blockSignals(True)
                self.mode_selector.setCurrentIndex(0 if self.mode == 'name' else 1)
                self.mode_selector.blockSignals(False)
                return
        self.mode = mode
        self.fill_groups(group_parameter_uses(self.uses, mode))

    def show_targets(self):
        self.targets.blockSignals(True)
        self.targets.clear()
        row = self.table.currentRow()
        if row >= 0:
            for use in self.groups[row].uses:
                typed_value = display_current(use)
                if use.kind:
                    typed_value += f' ({use.kind})'
                item = QtWidgets.QTreeWidgetItem(self.targets, [self.use_label(use), typed_value])
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
        masks = {}
        try:
            for row, group in enumerate(self.groups):
                if self.table.item(row, 0).checkState() != QtCore.Qt.Checked:
                    continue
                selector = self.table.cellWidget(row, 2)
                selected = selector.currentData() if selector is not None else None
                raw_value = self.table.item(row, 2).text().strip() if selector is None else ''
                if selected is None and not raw_value:
                    continue
                for use in group.uses:
                    if not use.enabled:
                        continue
                    if selector is not None:
                        code, label = selected
                        option = use.choices.get(code)
                        if use.choices and (option is None or option.label != label):
                            raise ValueError(f'{use.label}: вариант «{label} [{code}]» недоступен')
                        value = validate_value(code, '' if use.choices else use.kind)
                    else:
                        option = None
                        value = validate_value(raw_value, use.kind)
                    key = id(use.item)
                    if key not in changes:
                        changes[key] = (use.item, use.names, use.values[:])
                    item, names, values = changes[key]
                    if names != use.names:
                        raise ValueError(f'{use.label}: изменился набор параметров')
                    values[use.index] = value
                    if option is not None and option.show is not None:
                        masks.setdefault(key, []).append((use.label, option.show))
            if not changes:
                raise ValueError('Нет выбранных изменений')
            for key, rules in masks.items():
                if len({show for _, show in rules}) > 1:
                    raise ValueError(f'{rules[0][0]}: выбранные варианты по-разному скрывают поля; измените их в редакторе операции')
                item, names, values = changes[key]
                show = rules[0][1]
                for index, name in enumerate(names):
                    if show and name not in show:
                        values[index] = '+'
                    elif values[index] == '+':
                        values[index] = '-'
            for item, names, values in changes.values():
                originals = [use.original_raw for group in self.groups for use in group.uses if use.item is item]
                if not originals or any(item.text(14) != raw for raw in originals):
                    raise ValueError('Техкарта изменилась после открытия окна. Откройте список заново')
        except (ValueError, OverflowError) as exc:
            QtWidgets.QMessageBox.warning(self, 'Общие параметры', str(exc))
            return
        for item, names, values in changes.values():
            item.setText(14, '$'.join(values))
            item.setText(16, str(dict(zip(names, values))))
        self.changed_count = len(changes)
        self.accept()


def params_for_calc(window, item):
    descriptors = declared_params(window, item)
    names = [name for name, _ in descriptors]
    if not names:
        return None
    values = stored_values(item, names)
    choices = choices_for_item(window, item)
    for (name, kind), value in zip(descriptors, values):
        if value.strip() in ('', '-'):
            raise ValueError(f'{item_label(item)}: не заполнена переменная «{name}»')
        if value == '+' or value.startswith("f'") or ';' in value:
            continue
        if value in choices.get(name, {}):
            continue
        if numeric_kind(kind):
            try:
                number = F.valm(value)
            except ValueError:
                raise ValueError(f'{item_label(item)}: переменная «{name}» не число') from None
            if not F.is_numeric(str(number)):
                raise ValueError(f'{item_label(item)}: переменная «{name}» не число ')
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


def transition_calc_enabled(window, op_name):
    for row in window.spis_op:
        if row[0] == op_name:
            return int(row[1]) > int(F.scfg('limit_p')) and F.existence_file_c(
                window.xl_formulas.get_pereh_txt_path(op_name))
    return False


def recalc_one(window, op, with_materials):
    if op.text(7).startswith('=') or op.text(6).startswith('='):
        return None, 'ручная норма (=)'
    name = op.text(0)
    xl = window.xl_formulas
    if xl.check_approved(operation=name) and not xl.check_op(name, True):
        raise ValueError('недоступна утверждённая формула операции')
    if name not in window.DICT_OPERS:
        raise ValueError(f'операция «{name}» отсутствует в справочнике')

    changes = []
    material = op.text(10)
    material_errors = []
    op_params = params_for_calc(window, op)
    deferred = bool(op_params and any(value.startswith("f'") for value in op_params[1]))
    operation_time = None
    setup_time = None
    if op_params:
        if deferred:
            operation_time = 0
        else:
            result = operacii.vremya_tsht(name, copy.deepcopy(op_params))
            if result is None:
                raise ValueError('формула операции не вернула время')
            if isinstance(result, tuple) and len(result) == 2:
                operation_time = number_or_error(result[0], item_label(op))
                setup_time = number_or_error(result[1], item_label(op) + ' Тпз')
            else:
                operation_time = number_or_error(result, item_label(op))
            if with_materials:
                try:
                    calculated = operacii.materiali(window, name, copy.deepcopy(op_params))
                    if calculated is not None:
                        material = merge_materials(material, calculated)
                except Exception as exc:
                    material_errors.append(f'материалы операции: {exc}')
        if name not in operacii.Data_oper_norm.DICT_OPERS_CALC and not xl.check_op(name, True):
            setup_time = number_or_error(F.valm(window.DICT_OPERS[name]['Tpz']), item_label(op) + ' Тпз')

    transition_total = 0
    transition_count = 0
    calculated_transitions = 0
    informative_count = 0
    can_calc_transitions = transition_calc_enabled(window, name)
    for index in range(op.childCount()):
        pereh = op.child(index)
        if pereh.text(20) != '2':
            continue
        per_name = pereh.text(0)
        approved = xl.check_approved(operation=name, pereh=per_name)
        if approved and not xl.check_per(name, per_name, True):
            raise ValueError(f'{item_label(pereh)}: недоступна утверждённая формула перехода')
        if approved and not can_calc_transitions:
            raise ValueError(f'{item_label(pereh)}: переход недоступен для расчёта в редакторе')
        per_params = params_for_calc(window, pereh) if can_calc_transitions else None
        if per_params:
            if any(value.startswith("f'") for value in per_params[1]):
                raise ValueError(f'{item_label(pereh)}: отложенную формулу требуется рассчитать индивидуально')
            result = operacii.vremya_tsht_perehodi(
                name, per_name, copy.deepcopy(per_params), op.text(14).split('$'))
            if result is None:
                raise ValueError(f'{item_label(pereh)}: формула перехода не вернула время')
            per_time = number_or_error(result, item_label(pereh))
            if per_time >= CFG.Config.place.limit_time_on_naryad:
                raise ValueError(f'{item_label(pereh)}: Тшт {per_time} превышает лимит')
            if str(per_time) != pereh.text(7):
                changes.append((pereh, 7, str(per_time)))
            calculated_transitions += 1
        elif F.is_numeric(pereh.text(7)):
            per_time = number_or_error(F.valm(pereh.text(7)), item_label(pereh))
        else:
            informative_count += 1
            continue
        transition_total += float(per_time)
        transition_count += 1

    if operation_time is not None and operation_time != 0:
        time = operation_time
        source = 'формула операции'
    elif transition_count:
        time = round(transition_total, 3)
        source = 'сумма переходов'
    elif operation_time is not None:
        time = 0
        source = 'нет рассчитанного времени'
    else:
        time = None
        source = 'нет параметров для автоматического расчёта'

    if time is not None:
        if time == 0 and xl.check_strict_calc(operation=name):
            raise ValueError('операция с обязательным расчётом вернула нулевое Тшт')
        if time >= CFG.Config.place.limit_time_on_naryad:
            raise ValueError(f'Тшт {time} превышает лимит {CFG.Config.place.limit_time_on_naryad}')
        if str(time) != op.text(7):
            changes.append((op, 7, str(time)))
    if setup_time is not None and str(setup_time) != op.text(6):
        changes.append((op, 6, str(setup_time)))

    if with_materials and calculated_transitions:
        parent_time = str(time) if time is not None else op.text(7)
        for _ in range(calculated_transitions):
            try:
                calculated = operacii.materiali(window, name, ['', parent_time.split('$')])
                if calculated is not None:
                    material = merge_materials(material, calculated)
            except Exception as exc:
                material_errors.append(f'материалы после перехода: {exc}')
    if with_materials and material != op.text(10):
        changes.append((op, 10, material))

    message = f'Тшт: {op.text(7)} → {time} ({source})' if time is not None else source
    if setup_time is not None:
        message += f'; Тпз: {op.text(6)} → {setup_time}'
    if deferred:
        message += "; отложенный расчёт f' сохранён"
    if informative_count:
        message += f'; информативных переходов: {informative_count}'
    if with_materials and material != op.text(10):
        message += '; материалы пересчитаны'
    if material_errors:
        message += '; ОШИБКА: ' + '; '.join(material_errors)
    return changes or None, message


def show_bulk_parameters(window):
    if not any(operations(window.ui.tree)):
        QtWidgets.QMessageBox.information(window, 'Общие параметры', 'В текущей техкарте нет операций')
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
    try:
        window.xl_formulas.get_actual_srv_data()
    except Exception:
        pass
    dialog = QtWidgets.QDialog(window)
    dialog.setWindowTitle('Пересчёт текущей техкарты')
    layout = QtWidgets.QVBoxLayout(dialog)
    layout.addWidget(QtWidgets.QLabel(f'Рассчитать {len(op_items)} операций и их переходы?'))
    materials = QtWidgets.QCheckBox('Пересчитать также нормы материалов', dialog)
    materials.setChecked(False)
    materials.setHidden(True)
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
