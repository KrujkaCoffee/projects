import sys

from PyQt5 import QtWidgets, QtCore, QtGui

from project_cust_38 import Cust_Excel as CEX
from project_cust_38 import Cust_Qt as CQT
from project_cust_38 import Cust_SQLite as CSQ
from project_cust_38 import Cust_config as CFG
from project_cust_38 import Cust_mes as CMS



class ExcelNomenclatureImporter:
    DEFAULT_LABELS = {
        'Обозначение': 'Назначьте колонку из excel',
        'Наименование': 'Назначьте колонку из excel',
        'Комментарий': 'Назначьте колонку из excel',
        'Ошибки': ' ' * 240
    }

    def __init__(self, window):
        self.last_bad_rows = []
        self.window = window

        path = CMS.load_tmp_path(ExcelNomenclatureImporter.__class__.__name__)
        dir = CQT.f_dialog_name(window, 'Выберите excel', path, '*.xlsx')
        if dir == '.':
            return
        CMS.save_tmp_path(ExcelNomenclatureImporter.__class__.__name__, dir, True)
        parser = CEX.ExcelParser(dir)
        if not parser.worksheets:
            return
        current_sheet = parser.worksheets[0]
        decor_sheet_table = lambda sheet_table: sheet_table.verticalHeader().hide()
        if len(parser.worksheets) > 1:
            result = CQT.msgboxg_get_table(
                window,
                'Выберите лист excel',
                [{'Лист': sheet} for sheet in parser.worksheets],
                show_filtr=False,
                ExtendedSelection=False,
                func_oform_tbl=decor_sheet_table
            )
            if not result:
                return
            current_sheet = result['Лист']
        data = parser.data_by_worksheet(current_sheet)
        data = [{key: val for key, val in item.items() if key} for item in data]

        if not data or not isinstance(data, list):
            CQT.msgbox('Выбранный лист пуст')
            return
        first_row = data[0]
        headers = first_row.keys()
        self.data = data
        self.headers = headers
        data.insert(0, dict.fromkeys(headers, ''))

        data_for_table = [self.DEFAULT_LABELS]

        result_dse = CQT.msgboxg_get_table(
            window,
            '',
            data_for_table,
            func_oform_tbl=self.decor_table,
            show_filtr=False,
            func_validate=self.validate_data_for_insert,
            func_btn0=self.validate_dialog,
            not_standart_close=True
        )
        if not result_dse or (isinstance(result_dse, list) and len(result_dse) <= 1):
            return
        data_for_insert = []
        seen = set()
        for dse in result_dse[1:]:
            nn = dse['Обозначение']
            if nn in seen:
                continue
            seen.add(dse['Обозначение'])
            data_for_insert.append([dse['Наименование'], dse['Обозначение'], dse['Комментарий'],
                                    CFG.Config.place.poki]
                                   )
        query = 'INSERT INTO dse(Наименование, Номенклатурный_номер, Примечание, poki) VALUES (?, ?, ?, ?)'
        is_success = CSQ.custom_request_c(CSQ.DB_NAMES.db_dse, query, list_of_lists_c=data_for_insert)
        CQT.msgbox('Запись произведена успешно!') if is_success else CQT.msgbox('Ошибка записи')

    def validate_dialog(self, btn, dialog, tbl: QtWidgets.QTableWidget):
        if tbl.rowCount() <= 1:
            return CQT.msgbox('Не найдены строки для записи')
        if self.check(tbl, check_all=True, silence=True):
            return dialog.accept()
        return CQT.msgbox('Найдены ошибки! Исправьте ошибки чтобы продолжить')

    @staticmethod
    def validate_data_for_insert(data):
        is_correct = not any(str(row['Ошибки']).strip() for row in data)
        if is_correct:
            return data
        return False

    def fill_table(self, table, data_for_table = None, label_row: dict = None):
        if label_row is None:
            label_row = self.DEFAULT_LABELS
        if data_for_table is None:
            data_for_table = []
        data_for_table.insert(0, label_row)
        CQT.fill_wtabl(data_for_table, table)
        self.decor_table(table)

    def select_column(self, instance: CQT.InteractiveLabelInstance, row, col, parent_table: QtWidgets.QTableWidget, *args, **kwargs):
        selector_column_key = 'Наименование колонки'
        result = CQT.msgboxg_get_table(
            self.window,
            'Выберите колонку',
            [{selector_column_key: head} for head in self.headers],
            ExtendedSelection=False,
            show_filtr=False
        )
        if not result:
            return
        instance.set_text(result[selector_column_key])
        labels = {}

        for column in range(instance.table.columnCount() - 1):
            item = instance.get_label_instance(instance.table, 0, column)
            if item is None:
                return
            current_head = instance.table.horizontalHeaderItem(column).text()
            labels[current_head] = item.label.text()
        data_for_table = []
        for row_excel in self.data:
            row_for_table = {}

            for head_for_mes, current_head_excel in labels.items():
                row_for_table[head_for_mes] = row_excel.get(current_head_excel, '') or ''
            if any(row_for_table.values()):
                data_for_table.append(row_for_table)
        template = {
            lbl: labels[lbl] if lbl in labels else ''
            for lbl, val in self.DEFAULT_LABELS.items()
        }
        self.fill_table(parent_table, data_for_table, label_row=template)

    @staticmethod
    def remove_row(table: QtWidgets.QTableWidget):
        if 1 <= table.currentRow() < table.rowCount():
            table.removeRow(table.currentRow())

    def remove_error_rows(self, table):
        cnt = table.rowCount()
        for row in sorted(self.last_bad_rows, reverse=True):
            if 1 <= row < cnt:
                table.removeRow(row)
        self.last_bad_rows = []
        self._set_column_error_status(table)

    def _set_column_error_status(self, table):
        column_error = CQT.num_col_by_name_c(table, 'Ошибки')
        if column_error is not None:
            table.setColumnHidden(column_error, not bool(self.last_bad_rows))

    def check(self, table: QtWidgets.QTableWidget, check_all: bool = False, silence: bool = False) -> bool:
        current_row = table.currentRow()
        if not check_all and (1 > current_row > table.rowCount()):
            return False
        db_dse = CSQ.custom_request_c(
            CSQ.DB_NAMES.db_dse,
            f'SELECT Номенклатурный_номер FROM dse WHERE poki = {CFG.Config.place.poki}',
            rez_dict=True
        )
        if not db_dse or not isinstance(db_dse, list):
            return False
        db_combinations = [
            dse['Номенклатурный_номер']
            for dse in db_dse
        ]
        issues = {}
        seen = []
        rows = CQT.list_from_wtabl_c(table, rez_dict=True, only_current_row=not check_all)
        for idx, row in enumerate(rows[1:], 1):
            nn = str(row['Обозначение']).strip()
            name = str(row['Наименование']).strip()
            if not nn or not name:
                issues.setdefault(idx, list()).append('Имеет пустое Обозначение/Наименование')
            elif nn in db_combinations:
                issues.setdefault(idx, list()).append('Существует в БД МЕС')
            seen.append((nn, name))
        column_error = CQT.num_col_by_name_c(table, 'Ошибки')
        if column_error is None or (0 > column_error > table.columnCount()):
            return False
        palette = table.palette()
        cu_range = range(table.rowCount()) if check_all else (current_row,)
        for row in cu_range:
            comment = ''
            rgb = CQT.ThemeManager.readonly_cell(palette)[:3]
            if row in issues:
                rgb = (244, 12, 12)
                comment = '; '.join(issues[row])
            item = table.item(row, column_error)
            if item is None:
                return False
            CQT.set_color_row_wtab_c(table, row, *rgb)
            item.setText(comment)
        if check_all:
            self.last_bad_rows = list(issues.keys())
        table.setColumnHidden(column_error, not bool(self.last_bad_rows))
        if not issues:
            msg = 'Все строки корректны!' if check_all else 'Строка корректна'
            if not silence:
                CQT.msgbox(msg)
            return True
        if not silence:
            CQT.msgbox(f'Найдены проблемные строки ({len(issues)})')
        return False

    def show_menu(self, pos, table):
        row = table.rowAt(pos.y())
        if row < 1: return
        menu = QtWidgets.QMenu()
        delete_action = QtWidgets.QAction("Удалить строку", menu)
        delete_action.triggered.connect(lambda *args: self.remove_row(table))
        remove_error_rows = QtWidgets.QAction("Удалить ошибочные строки", menu)
        remove_error_rows.triggered.connect(lambda *args: self.remove_error_rows(table))
        check_row_action = QtWidgets.QAction("Проверить текущую строку", menu)
        check_row_action.triggered.connect(lambda *args: self.check(table, check_all=False))
        check_all_action = QtWidgets.QAction("Проверить все строки", menu)
        check_all_action.triggered.connect(lambda *args: self.check(table, check_all=True))

        menu.addAction(delete_action)
        menu.addAction(remove_error_rows)
        menu.addSeparator()
        menu.addAction(check_row_action)
        menu.addAction(check_all_action)
        menu.exec(table.viewport().mapToGlobal(pos))

    def decor_table(self, table: QtWidgets.QTableWidget):
        attr = 'customContextMenuRequested_mutated'
        table.setSelectionMode(QtWidgets.QTableWidget.SingleSelection)
        table.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        table.verticalHeader().hide()
        column_error = CQT.num_col_by_name_c(table, 'Ошибки')
        if column_error is not None:
            table.setColumnHidden(column_error, not bool(self.last_bad_rows))
        for column in range(table.columnCount() - 1):
            if table.columnWidth(column) < 200:
                table.setColumnWidth(column, 200)
            table.item(0, column)
            label = CQT.add_interactive_label(table, 0, column)
            label.add_button(' 📝', tooltip='Изменить колонку', on_clicked=self.select_column, cell_val=table)
        if not hasattr(table, attr):
            setattr(table, attr, attr)
            table.customContextMenuRequested.connect(lambda pos: self.show_menu(pos, table))




if __name__ == '__main__':
    from project_cust_38 import Cust_application as CAPP

    CFG.Config.place.poki = 0

    app = CAPP.SafeApplication(sys.argv)
    CAPP.install_crash_guard(app, user_name='', app_name='', log_qt_warnings=False, log_qt_debug_info=False, enable_native_fault_handler=False)
    window = QtWidgets.QMainWindow()
    ExcelNomenclatureImporter(window)

    app.exec_()