import logging
import os
import re
import time
import datetime
from pathlib import Path

import openpyxl
from openpyxl.styles import Border, Side, Alignment, Font

from project_cust_38 import Cust_Functions as F


logging.basicConfig(level=logging.INFO)

TIME_CACHE = 120

class ProjectWriter:
    def __init__(self, data: dict[str, list]):
        self.data = self.prepare_data(data)
        self.wb = openpyxl.Workbook()
        self.ws = self.wb.active
        self.thin = Side(border_style="thin", color="000000")
        self.border = Border(left=self.thin, right=self.thin, top=self.thin, bottom=self.thin)

    def build(self):
        """
        1. Если время создания excel превышает константу TIME_CACHE происходит создание
        2. Если время ниже файл берется из текущего кэша
        """
        logging.info(f'Поиск кэша...')
        if filename := self.find_cache():
            logging.info(f'Взят актуальный кэш')
            return filename
        else:
            filename = fr".\templates\projects_{int(time.time())}.xlsx"
            logging.info(f'Кэш неактуален.')
            logging.info(f'Начало записи {filename} ...')

            self.write_rows()
            self.correct_cell_width()
            self.decor_cells()
            self.wb.save(filename)
            return filename


    def prepare_data(self, data: dict[str, list]) -> list[list]:
        logging.info('Подготовка данных')
        hat_c = None
        result = []
        for napr, rows in data.items():
            if hat_c is None:
                hat_c = rows[0]
            result.extend([elem.lstrip("'").lstrip("`") for elem in row] for row in rows[1:])
        result.insert(0, hat_c)
        return result

    def write_rows(self):
        logging.info('Запись данных в excel')
        for row in self.data:
            self.ws.append(row)

    def correct_cell_width(self):
        logging.info('Корректировка ширины колонок')

        for column in self.ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            adjusted_width = (max_length + 2)
            self.ws.column_dimensions[column_letter].width = adjusted_width

    def decor_cells(self):
        logging.info('Оформление ячеек')
        for row in self.ws.iter_rows(min_row=1, max_row=len(self.data), min_col=1, max_col=len(self.data[0])):
            for cell in row:
                cell.border = self.border
                cell.alignment = Alignment(wrapText=True)
                if cell.row == 1:
                    cell.font = Font(bold=True)
                if F.is_date(cell.value, "%d.%m.%Y"):
                    cell.value = datetime.datetime.strptime(cell.value, "%d.%m.%Y")
                    cell.number_format = 'DD/MM/YYYY'
                    cell.data_type = 'd'
                if F.is_numeric(cell.value):
                    cell.data_type = 'n'

    def find_cache(self):
        directory = Path() / 'templates'
        pattern = r'projects_(\d+)\.xlsx'
        for file in os.listdir(str(directory)):
            match = re.match(pattern, file)
            if match:
                remains = time.time() - int(match.group(1))
                if remains > TIME_CACHE:
                    os.remove(str(directory / file))
                    return
                return str((directory / file).absolute())
