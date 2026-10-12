import dataclasses

import requests

"""
Пример использования 
client = PerkoClient() 
params = PerkoParams(
    dateBegin='2024-09-01', 
    dateEnd='2024-09-30', 
    division='79,91,94'
)
result = client.time_tracking(params)
Ответ:
Список словарей вида: 
[
    {
        "id": 685,
        "fio": "Тестов Тест Тестович",
        "tabel_number": "00846",
        "position_name": "Слесарь-сборщик 1 разряда",
        "division_name": "Powerz Сборочный цех Производства",
        "work_time": "183:16"
    },
]
"""

@dataclasses.dataclass
class PerkoParams:
    """
    Параметры Perko
    * dateBegin, dateEnd: дата начала, дата конца(указывается в формате %Y-%m-%d)
    * division: id подразделения(указывается строкой через запятую нпр. 79,80,33)
    * sord: сортировка
    * rows: количество возвращаемых значений
    """
    dateBegin: str
    dateEnd: str
    division: str = ''
    sord: str = 'asc'
    rows: str = 10000


class PerkoClient:
    BASE_URL = 'http://192.168.52.198/api'
    user = 'BotMes'
    password = 'e94b0f652173'

    def __init__(self):
        self.session = requests.session()
        response = self.session.post(
            f'{self.BASE_URL}/system/auth',
            json={'login': self.user, 'password': self.password}
        )
        token = response.json().get('token')
        if not token:
            raise Exception('Не удалось войти в систему Perko')
        self.session.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }

    def get_division(self):
        url = f'{self.BASE_URL}/divisions/list'
        return self.session.get(url)

    def time_tracking(
            self,
            params: PerkoParams
    ) -> list[dict[str, str | int]]:
        """
        Возвращает журнал рабочего времени, где
        * fio Имя
        * tabel_number Номер табеля
        * position_name Должность
        * division_name Подразделение
        * work_time Количество отработанных часов
        :param params:
        :return:
        """
        url = f'{self.BASE_URL}/taReports/timetracking'
        response = self.session.get(url, params=dataclasses.asdict(params))
        ct = response.headers.get('Content-Type')
        if not response.ok and not 'application/json' in ct:
            raise Exception('Некорректный ответ от сервера')
        return response.json().get('rows', [])
