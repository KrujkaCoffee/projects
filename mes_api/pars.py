import json
import re
import difflib
import sys
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag

"""
* ВХОДНЫЕ ДАННЫЕ
** Запуск парсинга происходит через функцию run_parse
** Функция принимает структуру [{}, {}], где каждый словарь должен иметь следующую структуру
  {
    "nomen_cod": "00-00052335",
    "uri": "https://mc.ru/metalloprokat/kvadrat_nerzhaveyushchij_nikelsoderzhashchij",
    "search_name": "Марка|Размер",
    "search_val": "AISI 304 (08Х18Н10)|12",
    "sensitivity_registr": false,
    "compars_oper_and": true,
    "return_name": "Цена"
  }
* НАСТРОЙКА ВХОДНЫХ КЛЮЧЕЙ
** Для модификаций или изменения входных параметров параметров структура описана в классе PrepareParams, а не в ключах
    т.к. не найденные атрибуты проще идентифицировать в исключениях

* НАСТРОЙКА СЕПАРАТОРОВ/КЛЮЧЕЙ
** Настройка ключей и сепараторов используемых в коде производится через класс ParsConfig, в случае смены сепаратора мы его меняем в одном месте

* ОТВЕТ
** Возвращает функция структуру [[{}, {}], []], где: 
- первый список содержит ответ на каждый запрос парсинга
- в каждом словаре содержится структура {'nomen_cod': '00-00052335', 'data': [{}]}
- в ключе data содержится список совпадений по результатам поиска в виде {'ключ запрашиваемой колонки': 'значение'}
- второй список содержит список ошибок структуры ['Не найдена таблица', 'колонки не существует']
- в случае любой непредвиденной ошибки возвращается структура [], ['Что-то пошло не так...']


Парсинг происходит в этапы
- Запрос
- Поиск заголовков get_headers
- Поиск строк соответствующих заголовкам get_rows
- Поиск индексов find_indexes 1.строк, которые участвуют в поиске 2.строк, которые мы собираемся возвращать
- Поиск запрошенных значений condition
"""

REPLACE_SYMBOLS = [
    '\xa0', ''
]

domains = {
    'mc.ru': 'NomParseMc',
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Referer": "https://www.google.com/",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}


class ParsConfig:
    sep = '|'
    nom_key = 'nomen_cod'
    uri_key = 'uri'


@dataclass
class PrepareParams:
    nomen_cod: str
    uri: str
    search_name: str | list
    search_val: str | list
    sensitivity_registr: bool
    compars_oper_and: bool
    return_name: str | list

    def __post_init__(self):
        self.search_name = self.search_name.split(ParsConfig.sep)
        self.search_val = self.search_val.split(ParsConfig.sep)
        self.return_name = self.return_name.split(ParsConfig.sep)


class ParseUtils:
    def find_match(self, text: str, lst: list[str]):
        """Совершает поиск левенштейна указанной @string строки в указанному списке @lst"""
        closest_match = difflib.get_close_matches(text, lst, n=1, cutoff=0.8)
        if closest_match:
            return lst.index(closest_match[0])
        else:
            return None

    def cleaning_text(self, text: str) -> str:
        text = self.strip_string(text)
        if self.is_number(text):
            return self.replace_comma_with_dot(text)
        return text

    def strip_string(self, text: str) -> str:
        """Преобразовывает различные комбинации табуляций и переводов строки в один пробел"""
        replace_enter = re.sub(r'[\r\n\t]+', ' ', text.strip())
        replace_space = re.sub(r'[\u202f\xa0\u2007]+', '', replace_enter)
        return replace_space

    def replace_comma_with_dot(self, text: str):
        """Регулярное выражение для поиска чисел с запятой"""
        pattern = r'(?<=\d),(?=\d)'
        return re.sub(pattern, '.', text)

    def is_number(self, string: str):
        """Регулярное выражение для проверки, является ли строка числом"""
        pattern = r'^[+-]?(\d+(\.\d*)?|\.\d+)$'
        return re.match(pattern, string) is not None


class NomParse:
    def __init__(self, **kwargs) -> None:
        self.session = requests.Session()
        self.params = PrepareParams(**kwargs)
        self.utils = ParseUtils()
        self.errors = set()

    def __enter__(self):
        self.session = requests.Session()
        self.session.headers.update(headers)
        response = self.session.get(self.params.uri)
        self.bs = BeautifulSoup(response.text, 'html.parser')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def get_headers(self) -> list[str]:
        """Возвращает заголовки таблицы в виде структуры [str, ...]"""
        headers = []
        trs = self.bs.find_all('tr', parent=self.bs.thead)
        if len(trs) > 0:
            for li in trs[0].find_all('th'):
                if 'display:none;' not in li.get('style', ''):
                    box = li.select('a')
                    if len(box) > 0:
                        li = box[0]
                    headers.append(
                        self.utils.strip_string(
                            ''.join(child.get_text() for child in li.children if child.name != 'span'))
                    )
        else:
            self.errors.add('Не найдены подходящие заголовки')
        return headers

    def get_rows(self) -> list[list[str]]:
        """Возвращает строки таблицы в виде структуры [[], []]"""
        table = self.bs.find('table')
        if not table:
            self.errors.add("Таблица не найдена")
            return []
        rows = table.find_all('tr', parent=self.bs.tbody)
        data = []
        for row in rows:
            cells = row.find_all('td')
            if cells:
                data.append([
                    self.utils.cleaning_text(cell.text)
                    for cell in cells if 'display:none;' not in cell.get('style', '')
                ])
        return data

    def find_indexes(self, headers: list[str]) -> tuple[dict, dict]:
        """
        Возвращает два словаря
            искомые имена {ключ в шапке таблицы: ключ в искомых значениях}
            ожидаемые колонки {ключ в шапке таблицы: запрашиваемое имя}
        Примечание: имя будет совпадать с введенным
        """
        names_idx, return_idx = {}, {}
        for idx, name in enumerate(self.params.search_name):
            if key := self.utils.find_match(name, headers):
                names_idx[key] = idx
            else:
                self.errors.add(f'Запрашиваемой для поиска колонки {name!r} не существует')
        for name in self.params.return_name:
            if key := self.utils.find_match(name, headers):
                return_idx[key] = name
            else:
                self.errors.add(f'Запрашиваемой для возврата колонки {name!r} не существует')
        return names_idx, return_idx

    def parse_table(self):
        headers = self.get_headers()
        name_idx, return_idx = self.find_indexes(headers)
        rows = self.get_rows()
        if self.errors:
            return [], self.errors
        result = []
        for row_idx, row in enumerate(rows):
            if self.condition(row, name_idx):
                result.append(
                    {name: row[idx] for idx, name in return_idx.items()}
                )
        return result, self.errors

    def condition(self, row, name_idx):
        """Совершает поиск значений в строке row
        используя указанные индексы в аргументе name_idx"""
        tmp = []
        for head, source in name_idx.items():
            if self.params.sensitivity_registr:
                tmp.append(row[head] == self.params.search_val[source])
            else:
                tmp.append(self.utils.find_match(row[head], [self.params.search_val[source]]) is not None)
        if self.params.compars_oper_and:
            return all(tmp) and len(tmp) == len(self.params.search_name)
        else:
            return any(tmp) and len(tmp) == len(self.params.search_name)


class NomParseMc(NomParse):
    DATA_ATTRS = ('data-price',)
    HEAD_TOGGLES = ('Цена', )

    def first_match_data_attr(self, tag: Tag = None) -> tuple[str, list[Tag]] | tuple[None, None]:
        if tag is None:
            tag = self.bs
        for key in self.DATA_ATTRS:
            result = tag.select(f'a[{key}]')
            if len(result) > 1:
                return (key, result)
        return None, None

    def get_headers(self):
        headers = []
        for li in self.bs.select('ul.catalogItemsFilters._normal>li'):
            if 'display:none;' not in li.get('style', ''):
                attr, values = self.first_match_data_attr(li)
                # toggle = li.select('a[data-price]')
                filter_group = li.select_one('.categoryGroup[data-filtersgroupi="cena"]')
                box = li.select('a.catalogFilter')
                if len(box) > 0:
                    li = box[0]
                text = self.utils.cleaning_text(''.join(child.get_text() for child in li.children if child.name != 'span'))
                if values:
                    postfix = lambda a: self.utils.cleaning_text(a.get_text(strip=True))
                    li = [f'{text} {postfix(a)}' for a in values]
                    headers.extend(li)
                elif filter_group and text in self.HEAD_TOGGLES:
                    postfix = self.utils.cleaning_text(filter_group.get_text(strip=True))
                    headers.append(f'%s %s' % (text, postfix))
                else:
                    headers.append(
                        text
                    )
        return headers

    def get_rows(self) -> list[list[str]]:
        """Возвращает строки таблицы в виде структуры [[], []]"""
        table = self.bs.find('table')
        if not table:
            self.errors.add("Таблица не найдена")
            return []
        rows = table.find_all('tr', parent=self.bs.tbody)
        data = []
        tgl_attr, tgl_value = self.first_match_data_attr()
        for row in rows:
            cells = row.find_all('td')
            if cells:
                tmp = []
                for cell in cells:
                    style = cell.get('style', '')
                    attr = [cell.get(f'{attr}-val') for attr in self.DATA_ATTRS if cell.get(f'{attr}-val')]
                    if 'display:none;' not in style:
                        if not tgl_attr and attr and not attr == ["2"]:
                            continue
                        tmp.append(self.utils.cleaning_text(cell.text))
                data.append(tmp)
        return data


def err_handler(fn):
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            print(e)
            return [], ['Что-то пошло не так..']

    return wrapper


@err_handler
def run_parse(lst: list[dict]):
    """
    :return: [
                {
                    'nomen_cod': '00-00052335',
                    'data': [{'Цена руб/м': '3189', 'Цена, руб от 0,1 до 1т': '431500'}],
                    'errors': ["Запрашиваемой для возврата колонки 'gsdgуб/мsad' не существует"]
                },
        ]
    """
    resp_data, resp_errors = [], set()
    for elem in lst:
        if not isinstance(elem,dict):
            elem = elem.__dict__
        url = elem.get(ParsConfig.uri_key, '')
        parsed_url = urlparse(url)
        cls = getattr(sys.modules[__name__], domains.get(parsed_url.netloc, 'NomParse'))
        with cls(**elem) as obj:
            data, errors = obj.parse_table()
        resp_data.append(
            {ParsConfig.nom_key: elem.get(ParsConfig.nom_key, ''), 'data': data, 'errors': list(errors)}
        )
    return resp_data


if __name__ == '__main__':
    data = [
        {
            "nomen_cod": "00-00052335",
            "uri": "https://mc.ru/metalloprokat/kvadrat_nerzhaveyushchij_nikelsoderzhashchij",
            "search_name": "Марка|Размер",
            "search_val": "AISI 321 12Х18Н10Т|30",
            "sensitivity_registr": True,
            "compars_oper_and": True,
            "return_name": "Цена руб/м|Цена, руб от 0,1 до 1т"
        }
    ]
    data1 = [
        {
            "nomen_cod": "00-00052335",
            "uri": "https://mc.ru/metalloprokat/stal_listovaya_g_k/mark/09g2s",
            "search_name": "Марка|Размер",
            "search_val": "09Г2С|3",
            "sensitivity_registr": True,
            "compars_oper_and": True,
            "return_name": "Продукция|Цена руб/т|Цена, руб от 0,1 до 1т"
        }
    ]
    result = run_parse(data)
    print(result)
