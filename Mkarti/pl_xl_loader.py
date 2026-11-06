import re
import math
import os
import posixpath
import tempfile
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree

from PyQt5 import QtGui

import dateutil
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTableWidget, QComboBox
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from project_cust_38 import Cust_Qt as CQT
from project_cust_38 import Cust_SQLite as CSQ
from project_cust_38 import Cust_Functions as F
from project_cust_38 import Cust_mes as CMS
from project_cust_38 import Cust_progressBar as CPROG

_MAIN_NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
_DOC_REL_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
_PKG_REL_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'
_TAG = '{' + _MAIN_NS + '}'


def _worksheet_parts(archive):
    workbook_part = 'xl/workbook.xml'
    workbook = ElementTree.fromstring(archive.read(workbook_part))
    rels = ElementTree.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
    targets = {}
    for rel in rels.findall('{' + _PKG_REL_NS + '}Relationship'):
        if rel.get('TargetMode') == 'External':
            continue
        target = rel.get('Target', '').replace('\\', '/')
        if not target:
            continue
        if target.startswith('/'):
            target = posixpath.normpath(target.lstrip('/'))
        else:
            target = posixpath.normpath(posixpath.join('xl', target))
        targets[rel.get('Id')] = target
    result = {}
    for sheet in workbook.findall(_TAG + 'sheets/' + _TAG + 'sheet'):
        part = targets.get(sheet.get('{' + _DOC_REL_NS + '}id'))
        if part and part in archive.namelist():
            result[sheet.get('name')] = part
    return result


def _shared_strings(archive):
    if 'xl/sharedStrings.xml' not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read('xl/sharedStrings.xml'))
    result = []
    for item in root.findall(_TAG + 'si'):
        text = []
        for child in item:
            if child.tag == _TAG + 't':
                text.append(child.text or '')
            elif child.tag == _TAG + 'r':
                run_text = child.find(_TAG + 't')
                if run_text is not None:
                    text.append(run_text.text or '')
        result.append(''.join(text))
    return result


def _formula_signature(formula):
    return formula.text, tuple(sorted(formula.attrib.items()))


def _read_formula_caches(path):
    result = {}
    with ZipFile(path) as archive:
        strings = _shared_strings(archive)
        for sheet_name, part in _worksheet_parts(archive).items():
            root = ElementTree.fromstring(archive.read(part))
            caches = {}
            for cell in root.iter(_TAG + 'c'):
                formula = cell.find(_TAG + 'f')
                value = cell.find(_TAG + 'v')
                if formula is None or value is None or value.text is None:
                    continue
                cache_type = cell.get('t')
                cache_value = value.text
                if cache_type == 's':
                    cache_value = strings[int(cache_value)]
                    cache_type = 'str'
                caches[cell.get('r')] = (
                    _formula_signature(formula), cache_type, cache_value,
                )
            result[sheet_name] = caches
    return result


def _save_workbook_preserving_formula_caches(workbook, path):
    path = Path(path)
    caches = _read_formula_caches(path)
    mode = path.stat().st_mode & 0o777
    temporary_paths = []
    restored = 0
    try:
        for suffix in ('.xlsx', '.cached.xlsx'):
            fd, name = tempfile.mkstemp(
                prefix='.' + path.name + '.', suffix=suffix, dir=path.parent,
            )
            os.close(fd)
            temporary_paths.append(Path(name))
        saved_path, restored_path = temporary_paths
        workbook.save(saved_path)
        with ZipFile(saved_path) as saved, ZipFile(restored_path, 'w') as output:
            cache_parts = {
                part: caches.get(sheet_name, {})
                for sheet_name, part in _worksheet_parts(saved).items()
            }
            for entry in saved.infolist():
                data = saved.read(entry.filename)
                part_caches = cache_parts.get(entry.filename)
                if part_caches:
                    root = ElementTree.fromstring(data)
                    changed = False
                    for cell in root.iter(_TAG + 'c'):
                        cache = part_caches.get(cell.get('r'))
                        formula = cell.find(_TAG + 'f')
                        if cache is None or formula is None:
                            continue
                        signature, cache_type, cache_value = cache
                        if signature != _formula_signature(formula):
                            continue
                        if cache_type is None:
                            cell.attrib.pop('t', None)
                        else:
                            cell.set('t', cache_type)
                        value = cell.find(_TAG + 'v')
                        if value is None:
                            value = ElementTree.Element(_TAG + 'v')
                            cell.insert(list(cell).index(formula) + 1, value)
                        value.text = cache_value
                        changed = True
                        restored += 1
                    if changed:
                        ElementTree.register_namespace('', _MAIN_NS)
                        data = ElementTree.tostring(root, encoding='utf-8')
                output.writestr(entry, data)
        os.chmod(restored_path, mode)
        os.replace(restored_path, path)
        return restored
    finally:
        for temporary_path in temporary_paths:
            temporary_path.unlink(missing_ok=True)


class ExcelParser:
    def __init__(self, path) -> None:
        self.stop_column_index = None
        self.stop_row_index = None
        self.path = path
        self.get_need_column_index = 2
        self.need_time_index = 41
        self.absence_type = 55  # колонка с названием неявки
        self.absence_time = 57  # колонка с часами неявки

        self.table_name = 'сводная таблица'
        self.result = {}
        self.depatment = None
        self.month = None
        self.is_plan = None

    def get_start_stop_rows(self):
        self.max_row = self.ws.max_row
        self.start_row_index = + 2
        self.stop_row_index = self.max_row
        return True

    def load_page(self):
        sub_res = self.preparate_excel()
        if sub_res == 1:
            return
        return True

    def get_depatment_name(self):
        dep = self.ws.cell(row=8, column=2).value
        if not isinstance(dep, str) or not dep.strip():
            raise ValueError('Не найдено подразделение в ячейке B8')
        self.depatment = dep.strip().lower()

    def get_month(self):
        found = self.find_cell('Отчетный период')
        if not found:
            return False
        row, col = found
        month = self.ws.cell(row=row + 2, column=col).value
        if month:
            if isinstance(month, str):
                month = datetime.strptime(month.strip(), "%d.%m.%Y")
            if not isinstance(month, (date, datetime)):
                return False
            self.month = datetime(month.year, month.month, 1)
            return True

    def preparate_excel(self):
        if self.get_start_stop_rows():
            self.get_position()
            self.get_depatment_name()
            return 0
        else:
            return 1

    def get_work_time(self, num_row, name):
        cell = self.ws.cell(row=num_row + 2, column=self.need_time_index)
        pre_time = cell.value
        original = self.wb[self.ws.title][cell.coordinate]
        if pre_time is None and original.data_type == 'f':
            raise ValueError(f'Нет рассчитанного значения формулы в {cell.coordinate}. '
                             'Откройте табель в Excel, пересчитайте и сохраните его')
        if pre_time is None or pre_time == '':
            value = 0.0
        else:
            prepared_value = re.sub(r'\s+', '', str(pre_time)).replace(',', '.')
            try:
                value = float(prepared_value)
            except (TypeError, ValueError):
                raise ValueError(f'Не удалось прочитать часы в ячейке {cell.coordinate}: {pre_time}')
            if not math.isfinite(value) or value < 0:
                raise ValueError(f'Некорректные часы в ячейке {cell.coordinate}: {pre_time}')
        self.add_in_inner_dict(name, 'Часы', value)

    def add_in_inner_dict(self, name, key, float_val):
        if not self.result.get(name):
            inner_di = {}
            inner_di[key] = float_val
            self.result[name] = inner_di
        else:
            if self.result[name].get(key):
                self.result[name][key] += float_val
            else:
                self.result[name][key] = float_val

    def get_absence(self, num_row, name, is_additional=False):
        sum_num = 0
        if is_additional:
            sum_num = 4
        for i in range(4):
            absence_type = self.ws.cell(row=num_row + i, column=self.absence_type + sum_num).value
            absence_time = self.ws.cell(row=num_row + i, column=self.absence_time + sum_num).value
            if absence_type and absence_time:
                absence_time_compile = re.compile(r'\(\s*(\d+(?:[.,]\d+)?)\s*\)')
                absence_time_minutes = absence_time_compile.search(str(absence_time))
                if absence_time_minutes:
                    value = float(absence_time_minutes.group(1).replace(',', '.'))
                    code = re.sub(r'\s+', ' ', str(absence_type)).strip().upper()
                    self.add_in_inner_dict(name, code, value)

    def get_position(self):
        self.result = {}
        for num_row in range(self.start_row_index, self.stop_row_index):
            row = self.ws[num_row]
            value = row[self.get_need_column_index].value
            employee_num = self.ws.cell(row=num_row, column=2).value
            if isinstance(value, str) and str(employee_num).strip().isdigit():
                find = re.search(r'\((.*)\)\s*$', value, re.DOTALL)
                if find:
                    name = re.sub(r'\s+', ' ', find.group(1)).strip()
                    if not name:
                        continue
                    self.get_work_time(num_row, name)
                    self.get_absence(num_row, name)
                    self.get_absence(num_row, name, is_additional=True)

    def check_file_data(self):
        self.wb = load_workbook(self.path)
        self.data_wb = load_workbook(self.path, data_only=True)
        self.sheet_names = self.data_wb.sheetnames
        sheet_name = self.wb.sheetnames[0]
        self.ws = self.data_wb[sheet_name]
        if not self.find_cell("рабочего времени"):
            return True

    def find_cell(self, find_val):
        for row in range(1, self.ws.max_row + 1):
            for col in range(1, self.ws.max_column + 1):
                val = self.ws.cell(row=row, column=col).value
                if val and isinstance(val, str) and find_val.strip().lower() in val.lower():
                    return row, col

    def check_file(self):
        msg = None
        if not str(self.path).lower().endswith('.xlsx'):
            msg = 'Выбран не верный файл'
        elif self.check_file_data() or not self.get_month():
            msg = 'Выбран не верный файл'
        if msg:
            raise ValueError(msg)

    def run(self, hook_prog_bar):
        try:
            hook_prog_bar.set(20)
            hook_prog_bar.text('Проверка документа')
            if err_msg := self.check_file():
                return err_msg
            hook_prog_bar.set(30)
            hook_prog_bar.text('Распаковка документа')
            if self.load_page():
                if not self.result:
                    raise ValueError('В табеле не найдены строки сотрудников с должностями')
                return True
        except PermissionError as e:
            CQT.msgbox('Перед выгрузкой закройте Excel!')
            return
        except Exception as e:
            CQT.msgbox(f'Произошла ошибка во время выгрузки excel:\n{e}')
            return

    def close(self):
        for name in ('wb', 'data_wb'):
            workbook = getattr(self, name, None)
            if workbook is not None:
                workbook.close()

    def get_name_headers(self):
        all_times = set()
        for position_di in self.result.values():
            all_times.update(set(position_di.keys()))
        all_times.discard("Часы")
        li = ["Должность", "Часы", "Минуты"]
        li.extend(sorted(all_times))
        return li

    def get_table_headers(self):
        colunmn_name = self.get_name_headers()
        head_index = {}
        for num, name in enumerate(colunmn_name, start=1):
            self.save_ws.cell(column=num, row=1, value=name)
            head_index[name] = num
        return head_index

    def save_result(self, work_time, position_worktypes, failed_worktypes=()):
        absence_codes = sorted({code for data in self.result.values() for code in data if code != 'Часы'})
        column_count = 4 + len(absence_codes)
        last_column = get_column_letter(column_count)
        imported_absences = defaultdict(lambda: defaultdict(float))
        all_absences = defaultdict(float)
        for position, data in self.result.items():
            work_type = position_worktypes.get(position)
            for code, hours in data.items():
                if code == 'Часы':
                    continue
                all_absences[code] += hours
                if work_type in work_time:
                    imported_absences[work_type][code] += hours
        if self.table_name in self.wb.sheetnames:
            self.wb.remove(self.wb[self.table_name])
        self.save_ws = self.wb.create_sheet(title=self.table_name, index=1)
        ws = self.save_ws
        ws.append(['Период', self.month.strftime('%Y-%m-%d'), 'Режим', 'План' if self.is_plan else 'Факт'])
        ws.append(['Подразделение', self.depatment])
        ws.merge_cells(f'B2:{last_column}2')
        ws.append([])
        ws.append(['Вид работ', 'Подразделение', 'Часы', 'Нормосмены', *absence_codes])
        work_header_row = ws.max_row
        header_rows = [work_header_row]
        for work_type, hours in sorted(work_time.items()):
            ws.append([work_type, self.depatment, hours, round(hours / 8, 2),
                       *(imported_absences[work_type].get(code) for code in absence_codes)])
        ws.append(['Итого', None, sum(work_time.values()),
                   round(sum(round(hours / 8, 2) for hours in work_time.values()), 2),
                   *(sum(imported_absences[work_type].get(code, 0.0) for work_type in work_time)
                     for code in absence_codes)])
        total_row = ws.max_row
        total_rows = [total_row]
        ws.append([])
        ws.append(['Расшифровка часов, вошедших в выгрузку'])
        ws.merge_cells(start_row=ws.max_row, start_column=1, end_row=ws.max_row, end_column=column_count)
        ws.append(['Вид работ', 'Должность', 'Часы', 'Нормосмены до округления', *absence_codes])
        header_rows.append(ws.max_row)
        detail_start_row = ws.max_row + 1
        for position, data in sorted(self.result.items()):
            work_type = position_worktypes.get(position)
            if work_type in work_time:
                hours = data.get('Часы', 0.0)
                ws.append([work_type, position, hours, hours / 8,
                           *(data.get(code) for code in absence_codes)])
        detail_end_row = ws.max_row
        excluded = [(position, data.get('Часы', 0.0)) for position, data in sorted(self.result.items())
                    if not position_worktypes.get(position)]
        if excluded:
            ws.append([])
            ws.append(['Не вошли в выгрузку: должности без вида работ'])
            ws.merge_cells(start_row=ws.max_row, start_column=1, end_row=ws.max_row, end_column=4)
            ws.append(['Должность', 'Причина', 'Часы'])
            header_rows.append(ws.max_row)
            for position, hours in excluded:
                ws.append([position, 'Нет сопоставления в справочнике', hours])
        if failed_worktypes:
            ws.append([])
            ws.append(['Не вошли в выгрузку: ошибка записи в БД'])
            ws.merge_cells(start_row=ws.max_row, start_column=1, end_row=ws.max_row, end_column=4)
            for work_type in sorted(failed_worktypes):
                ws.append([work_type])
        if absence_codes:
            ws.append([])
            ws.append(['Сводка кодов отсутствия по табелю'])
            ws.merge_cells(start_row=ws.max_row, start_column=1, end_row=ws.max_row, end_column=column_count)
            ws.append(['Код отсутствия', 'Часы'])
            header_rows.append(ws.max_row)
            for code in absence_codes:
                ws.append([code, all_absences[code]])
                ws.cell(ws.max_row, 2).number_format = '0.00'
            ws.append(['Итого отсутствий', sum(all_absences.values())])
            ws.cell(ws.max_row, 2).number_format = '0.00'
            total_rows.append(ws.max_row)
            ws.append([])
            ws.append(['Отсутствия по должностям (коды — часы)'])
            ws.merge_cells(start_row=ws.max_row, start_column=1, end_row=ws.max_row, end_column=column_count)
            ws.append(['Должность', 'Часы', 'Минуты', *absence_codes])
            header_rows.append(ws.max_row)
            for position, data in sorted(self.result.items()):
                hours = data.get('Часы', 0.0)
                ws.append([position, hours, hours * 60,
                           *(data.get(code) for code in absence_codes)])
                ws.cell(ws.max_row, 2).number_format = '0.00'
            ws.append(['Итого по табелю', sum(data.get('Часы', 0.0) for data in self.result.values()),
                       sum(data.get('Часы', 0.0) for data in self.result.values()) * 60,
                       *(all_absences[code] for code in absence_codes)])
            ws.cell(ws.max_row, 2).number_format = '0.00'
            total_rows.append(ws.max_row)
        ws.freeze_panes = f'C{work_header_row + 1}'
        ws.auto_filter.ref = f'A{work_header_row}:{last_column}{max(work_header_row, total_row - 1)}'
        for column, width in {'A': 45, 'B': 52, 'C': 18, 'D': 30}.items():
            ws.column_dimensions[column].width = width
        for column_index in range(5, column_count + 1):
            ws.column_dimensions[get_column_letter(column_index)].width = 14
        for row in ws:
            ws.row_dimensions[row[0].row].height = 30
            for cell in row:
                cell.alignment = Alignment(vertical='center', wrap_text=True)
                if cell.column >= 3 and isinstance(cell.value, (int, float)):
                    cell.number_format = '0.00'
        for row_index in range(detail_start_row, detail_end_row + 1):
            ws.cell(row_index, 4).number_format = '0.00####'
        for row_index in [1, *header_rows]:
            for cell in ws[row_index]:
                cell.font = Font(bold=True, color='FFFFFF')
                cell.fill = PatternFill('solid', fgColor='31566F')
        for row_index in total_rows:
            for cell in ws[row_index]:
                cell.font = Font(bold=True)
        _save_workbook_preserving_formula_caches(self.wb, self.path)


class PushWorkPlan:
    def __init__(
            self,
            window,
            plan_tbl,
            plan_tbl_fltr,
            fact_tbl,
            fact_tbl_fltr
    ):
        self.window = window
        self.buffered = None
        self.date_format = '%Y-%m-%d'
        self.bd_users = F.scfg('BD_users')
        self.bd_kplan = F.scfg('DB_kplan')
        self.naryad = F.scfg('Naryad')

        self.init_places()
        self.plan_tbl = plan_tbl
        self.plan_tbl_fltr = plan_tbl_fltr
        self.fact_tbl = fact_tbl
        self.fact_tbl_fltr = fact_tbl_fltr

        self.PODRAZDEL = F.deploy_dict_c(
            CSQ.custom_request_c(self.bd_kplan, f'SELECT Цвет, Наименование_ЕРП, Имя FROM podrazdel WHERE poki == {self.selected_poki} or poki is NULL', rez_dict=True),
            'Наименование_ЕРП'
        )

    @property
    def work_type_dep_lis(self):
        return self.get_vid_dep_list()

    @property
    def name_worktypes(self):
        return self.load_name_worktypes()

    @property
    def selected_place(self):
        current_poki = self.window.ui.cmb_pl_tabel_place.currentData()
        return self.PLACES_BY_POKI[current_poki]

    @property
    def selected_poki(self):
        return self.window.ui.cmb_pl_tabel_place.currentData()

    @property
    def months(self):
        return sorted(self.generate_months())

    def get_vid_dep_list(self):
        code_erp = self.selected_place.get('РодительВидаРабот')
        result = CSQ.custom_request_c(
            self.bd_users,
            f'''
            SELECT 
                vrpd.Вид_работ, 
                p.Наименование_ЕРП
            FROM vid_rab_po_dolg AS vrpd
            INNER JOIN podrazdel AS p ON p.Имя = vrpd.name_tbl
            WHERE vrpd.Родитель = {code_erp!r}
        ''', hat_c=False, attach_dbs=self.bd_kplan)
        if result == False:
            return CQT.msgbox('Не удалось запросить данные о видах работ и цехах')
        return [
            '\n'.join((vid, dep.lower()))
            for vid, dep in result
        ]

    def get_list_places(self):
        response = CSQ.custom_request_c(
            self.naryad,
            'SELECT * FROM places',
            rez_dict=True
        )
        if not isinstance(response, list):
            CQT.msgbox('Не удалось загрузить организации')
            return []
        return response

    def is_plan(self, err_msg: str = 'Штат->Планы\nНе вычислена таблица БД т.к. вкладка не распознана'):
        sub_tab_ind = self.window.ui.tabWidget_10.currentIndex()
        tab_text = self.window.ui.tabWidget_10.tabText(sub_tab_ind)
        if tab_text == 'План':
            return True
        if tab_text == 'Факт':
            return False
        raise Exception(err_msg)

    @property
    def table_name(self):
        if self.is_plan('Штат->Планы\nНе вычислена таблица БД т.к. вкладка не распознана'):
            return 'plan_tabel_workforce'
        return 'fact_tabel_workforce'

    @property
    def table_widget(self):
        if self.is_plan('Штат->Планы\nНе вычислен виджет таблицы т.к. вкладка не распознана'):
            return self.plan_tbl
        return self.fact_tbl

    @property
    def table_filter(self):
        if self.is_plan('Штат->Планы\nНе вычислен виджет таблицы т.к. вкладка не распознана'):
            return self.plan_tbl_fltr
        return self.fact_tbl_fltr

    @property
    def first_day_cur_month(self):
        date = datetime.now().replace(day=1)
        if not self.is_plan():
            date = date - dateutil.relativedelta.relativedelta(months=2)
        return date

    def load_name_worktypes(self):
        stmt = f"""
            SELECT имя, вид_работ 
            FROM professions 
            WHERE Вкл = 1 AND poki = {self.selected_poki}
        """
        work_types = F.deploy_dict_c(CSQ.custom_request_c(F.scfg('BD_users'), stmt, rez_dict=True), 'имя')
        if not work_types:
            CQT.msgbox('Не удалось загрузить виды работ')
            return
        return work_types

    def remove_month(self):
        if not CMS.user_access(self.naryad, 'мкарт_внесение_корректировка_планов_фактов', F.user_name()):
            return
        current_row = self.table_widget.currentRow()
        if current_row == -1:
            return
        name_month = self.table_widget.verticalHeaderItem(current_row).text()
        if not CQT.msgboxgYN(f'Вы уверены что хотите удалить месяц: {name_month}'):
            return
        response = CSQ.custom_request_c(
            self.bd_kplan,
            f"""
                DELETE FROM {self.table_name}
                WHERE month = "{name_month} AND poki = {self.selected_poki}"
            """
        )
        msg = 'Не удалось удалить месяц. Попробуйте ещё раз'
        if response:
            self.fill_tbl()
            CQT.fill_filtr_c(self, self.table_filter, self.table_widget)
            CMS.apply_filtr_c(self, self.table_filter, self.table_widget)
            msg = f'Месяц {name_month} успешно удален!'
        CQT.msgbox(msg)

    def copy_data(self):
        row = self.table_widget.currentRow()
        self.buffered = row
        text = self.table_widget.verticalHeaderItem(row).text()
        CQT.msgbox(f'Скопирован месяц: {text}')

    @CQT.onerror
    def delete_insert_vid_to_month(self, **kwargs):
        if all(value != '' for value in kwargs.values()):
            keys = ', '.join(kwargs.keys())
            placeholders = ', '.join('?' for _ in kwargs)
            vid_rabot = kwargs[
                'vid_rabot']  # через нотацию квадратных скобок для быстрого отказа в случае отсутствия ключа
            month = kwargs['month']
            depatment = kwargs['depatment']
            poki = self.selected_poki
            instructions = (
                (f'''DELETE FROM {self.table_name} WHERE vid_rabot = ? AND month = ? AND depatment = ? AND poki = ?''',
                 [vid_rabot, month, depatment, poki]),
                (f'''INSERT INTO {self.table_name}({keys}) VALUES ({placeholders})''', list(kwargs.values()))
            )
            for instruction, params in instructions:
                if not CSQ.custom_request_c(self.bd_kplan, instruction, list_of_lists_c=[params]):
                    return False
            return True

    def get_last_months(self):
        date = self.first_day_cur_month
        data = CSQ.custom_request_c(self.bd_kplan, f'''
            SELECT month, vid_rabot, depatment, normo_smen
            FROM {self.table_name} 
            WHERE poki = {self.selected_poki} AND date(month) >= date("{date.strftime("%Y-%m-%d")}")
        ''', rez_dict=True)
        if data is None or data is False:
            CQT.msgbox('Не удалось загрузить данные для таблицы')
            return
        return data

    def last_month(self):
        last_row = self.table_widget.rowCount() - 1
        if self.table_widget.rowCount() == 0:
            return datetime.now().replace(day=1).strftime(self.date_format)
        last_months_on_tbl = self.table_widget.verticalHeaderItem(last_row).text()
        if F.is_date(last_months_on_tbl, self.date_format):
            date_obj = datetime.strptime(last_months_on_tbl, self.date_format) + dateutil.relativedelta.relativedelta(
                months=1)
            return date_obj.strftime(self.date_format)

    def insert_one_month(self):
        if not CMS.user_access(self.naryad, 'мкарт_внесение_корректировка_планов_фактов', F.user_name()):
            return
        month = self.last_month()
        if not CQT.msgboxgYN(f'Вы действительно хотите добавить месяц: {month}?'):
            return
        months = self.get_last_months()
        data = self.aggregate_months(months)
        if data:
            self.fill_tbl([*data, [''] * len(self.work_type_dep_lis)])

    def paste_data(self):
        if not CMS.user_access(self.naryad, 'мкарт_внесение_корректировка_планов_фактов', F.user_name()):
            return
        if self.buffered is None:
            CQT.msgbox('СНачала нужно скопировать строчку!')
            return
        row = self.table_widget.currentRow()
        name_month = self.table_widget.verticalHeaderItem(row).text()
        if self.buffered == row:
            return
        for col in range(self.table_widget.columnCount()):
            copy_text = self.table_widget.item(self.buffered, col).text()
            self.table_widget.item(row, col).setText(copy_text)
            vert_head = self.table_widget.horizontalHeaderItem(col).toolTip()
            vid_rabot, depatment = vert_head.split('\n')
            self.delete_insert_vid_to_month(vid_rabot=vid_rabot, month=name_month, normo_smen=copy_text,
                                            depatment=depatment, poki=self.selected_poki)

    def generate_months(self):
        dates = []
        current_date = self.first_day_cur_month
        for i in range(16):
            new_date = current_date + dateutil.relativedelta.relativedelta(months=i)  # Добавляем i месяцев
            dates.append(new_date.strftime('%Y-%m-%d'))
        return sorted(dates)

    def aggregate_months(self, data: list):
        agg_months = {}
        start_month = self.first_day_cur_month.strftime("%Y-%m-%d")
        for row in data:
            if month := row.get('month'):
                key = f'{row.get("vid_rabot")}\n{row.get("depatment")}'
                if month >= start_month:
                    agg_months.setdefault(month, {})[key] = row.get('normo_smen')

        agg_vid = [self.work_type_dep_lis]
        for month in self.months:
            tmp = []
            for vid in agg_vid[0]:
                cur_month_data = agg_months.get(month, {})
                if (normo_smen := cur_month_data.get(vid)) is not None:
                    tmp.append(normo_smen)
                else:
                    tmp.append('')
            agg_vid.append(tmp)
        return agg_vid

    def get_department_data(self, key: str):
        for dep_erp in self.PODRAZDEL:
            if dep_erp.lower() == key.lower():
                return self.PODRAZDEL[dep_erp]

    def decor_table(self):
        col_count = self.table_widget.columnCount()
        for col in range(col_count):
            head_item = self.table_widget.horizontalHeaderItem(col)
            full_name = head_item.text()
            head_item.setToolTip(full_name)
            vid, dep = full_name.split('\n')
            if data := self.get_department_data(dep):
                r, g, b = data.get('Цвет', '255;255;255').split(';')
                name = data.get('Имя', '').replace('пл_', '')
                head_item.setText(f'{vid}({name})')
                color_inst = QtGui.QColor(int(r), int(g), int(b))
                head_item.setForeground(color_inst)
                color_inst = QtGui.QColor(int(r), int(g), int(b), 32)
                font = head_item.font()
                font.setBold(True)
                head_item.setFont(font)
                for row in range(self.table_widget.rowCount()):
                    item = self.table_widget.item(row, col)
                    item.setBackground(color_inst)
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setToolTip('нормо-смен')
        #self.table_widget.horizontalHeader().setFixedHeight(40)

    @CQT.onerror
    def fill_tbl(self, data=None):
        self.table_widget.setRowCount(0) or self.table_widget.setColumnCount(0)
        if data is None:
            months = self.get_last_months()
            data = self.aggregate_months(months)
        CQT.fill_wtabl(data, self.table_widget, height_row=24, min_width_col=0, ogr_maxshir_kol=500,
                       StretchLastSection=False,list_column_widths=CMS.load_column_widths(self,self.table_widget))
        self.table_widget.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_widget.setVerticalHeaderLabels(self.months)
        self.table_widget.verticalHeader().setStyleSheet("""
            QHeaderView::section {
                border: 1px solid #A9A9A9;
                padding: 5px;
                font-size: 14px;
            }
        """)
        self.decor_table()
        CQT.fill_filtr_c(self, self.table_filter, self.table_widget, hidden_scroll=True)
        CMS.update_width_filtr(self.table_widget, self.table_filter)
        CMS.apply_filtr_c(self, self.table_filter, self.table_widget)

    def accum_work_time(self, data):
        agr_vid_rabot = defaultdict(float)
        work_types = self.name_worktypes
        if not isinstance(work_types, dict):
            raise ValueError('Не удалось загрузить справочник видов работ')
        normalized = {}
        for name, record in work_types.items():
            key = re.sub(r'\s+', ' ', str(name)).strip().casefold()
            work_type = record.get('вид_работ') if isinstance(record, dict) else record
            if work_type:
                if key in normalized and normalized[key] != work_type:
                    raise ValueError(f'Должность {name} сопоставлена с несколькими видами работ')
                normalized[key] = work_type
        self.position_worktypes = {}
        self.unmapped_positions = []
        for position_name in data:
            key = re.sub(r'\s+', ' ', position_name).strip().casefold()
            vid_rabot = normalized.get(key)
            if vid_rabot:
                agr_vid_rabot[vid_rabot] += data[position_name].get('Часы', float())
                self.position_worktypes[position_name] = vid_rabot
            else:
                self.unmapped_positions.append(position_name)
        return agr_vid_rabot

    @CPROG.progress_decorator
    def load_xlsx(self, hook_prog_bar):
        if not CMS.user_access(self.naryad, 'мкарт_внесение_корректировка_планов_фактов', F.user_name()):
            return
        tmp_path = CMS.load_tmp_path('btn_load_plan_fact_xl')
        path = CQT.f_dialog_name(self.window, 'Выбрать файл', tmp_path, f"Файлы (*xlsx)")
        if path is None or path == '.':
            return
        hook_prog_bar.set(10)
        hook_prog_bar.text('Инициализация excel')
        ep = ExcelParser(path)
        CMS.save_tmp_path('btn_load_plan_fact_xl', path, True)
        try:
            if ep.run(hook_prog_bar) is not True:
                return
            ep.is_plan = self.is_plan()
            work_time = self.accum_work_time(ep.result)
            hook_prog_bar.set(70)
            hook_prog_bar.text('Сохранение результатов в БД')
            month = ep.month.strftime("%Y-%m-%d")
            imported_work_time = {}
            failed_worktypes = []
            for wt, time in work_time.items():
                normo_smen = round(time / 8, 2)
                if self.delete_insert_vid_to_month(
                    depatment=ep.depatment,
                    vid_rabot=wt,
                    month=month,
                    normo_smen=normo_smen,
                    poki=self.selected_poki
                ):
                    imported_work_time[wt] = time
                else:
                    failed_worktypes.append(wt)
            summary_error = None
            hook_prog_bar.text('Сохранение сводки в Excel')
            try:
                ep.save_result(imported_work_time, self.position_worktypes, failed_worktypes)
            except PermissionError:
                summary_error = 'Сводка не сохранена. Закройте Excel и повторите загрузку'
            except Exception as e:
                summary_error = f'Не удалось сохранить сводку в Excel:\n{e}'
            hook_prog_bar.set(90)
            hook_prog_bar.text('Заполнение таблицы актуальными данными')
            self.table_widget.clear()
            self.fill_tbl()
            if not work_time:
                msg = 'Ни одна должность из табеля не сопоставлена с видом работ. Данные не выгружены'
            elif failed_worktypes:
                msg = f'Месяц {month}: выгружено видов работ {len(imported_work_time)} из {len(work_time)}. '
                msg += 'Ошибка записи в БД: ' + ', '.join(failed_worktypes)
            else:
                msg = f'Месяц {month} успешно выгружен'
            if self.unmapped_positions:
                msg += '\nНе вошли в выгрузку (нет вида работ): ' + ', '.join(self.unmapped_positions)
            if summary_error:
                msg += '\n' + summary_error
            CQT.msgbox(msg)
        except Exception as e:
            CQT.msgbox(f'Не удалось завершить загрузку табеля:\n{e}')
        finally:
            ep.close()

    def init_places(self):
        self.PLACES_BY_POKI = F.deploy_dict_c(self.get_list_places(), 'poki')
        cmb: QComboBox = self.window.ui.cmb_pl_tabel_place
        for poki, place in self.PLACES_BY_POKI.items():
            cmb.addItem(place['Имя'], poki)
        # # TODO блок смены организации
        #cmb.setCurrentIndex(0)
        #cmb.setDisabled(True)

