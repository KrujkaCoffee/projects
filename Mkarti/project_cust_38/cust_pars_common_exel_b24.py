import requests
import bs4

from project_cust_38 import Cust_Excel as CEH
from project_cust_38 import Cust_Functions as F

class GetBitrixFiles:
    BASE_URL = 'https://bitrix24.kelast.ru'
    PUBLICATIONS_PART = '/docs/pub/{key}/default/?&'
    """
        Принимает ключ публикации файла из Битркс24 и скачивает его
        - EXCEL .parse_xlsx_data(sheet_name='Имя листа')  Получить структуру list[dict] выбранной таблицы
            
        ПРИМЕР:
        bitrix_file_reader = GetBitrixFiles('89a19d9b18995d279d8e7aa189cfb495')
        bitrix_file_reader.parse_xlsx_data(sheet_name='Диаграмма Ганта')
        
        ИЗВЛЕЧЕНИЕ КОДА ПУБЛИКАЦИИ:
        Ссылка на публикацию: https://bitrix24.kelast.ru/docs/pub/89a19d9b18995d279d8e7aa189cfb495/default/?&
        Где:
         - 89a19d9b18995d279d8e7aa189cfb495 это ключ публикации необходимый для инициализации класса
    """

    def __init__(self, target_publication_key: str = '89a19d9b18995d279d8e7aa189cfb495'):
        self.session = requests.Session()
        self.target_publication_key = target_publication_key
        self.token = self.make_token()
        self.path = self.make_file()

    def make_token(self):
        url = f'{self.BASE_URL}{self.PUBLICATIONS_PART.format(key=self.target_publication_key)}'
        response = self.session.get(url)
        if response.ok:
            dom = bs4.BeautifulSoup(response.text, 'lxml')
            header = dom.select_one('.disk-fe-office-header')
            btn_download = header.select_one('a.ui-btn.ui-btn-sm.ui-btn-light-border.ui-btn-round')
            return btn_download.get('href')

    def make_file(self) -> str:
        if self.token is None:
            print('Не удалось извлечь токен. Получение файла невозможно')
            return
        url = f'{self.BASE_URL}{self.token}'
        response = self.session.get(url)
        if response.ok:
            return F.save_tmp_win_dir_file(response.content, '.xlsx')

    def parse_xlsx_data(self, sheet_name: str = 'Диаграмма Ганта'):
        if self.path is None:
            print('Некорректный путь для парсинга')
            return
        xlsx_parser = CEH.ExcelParser(self.path)
        return xlsx_parser.data_by_worksheet(sheet_name)
