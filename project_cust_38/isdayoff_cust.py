import datetime
from functools import wraps
from typing import Dict, List, NoReturn
from enum import IntEnum
from typing_extensions import TypedDict

from requests import Session


class ServiceNotRespond(Exception):
    pass

class DataError(Exception):
    pass

class ParamsApi(TypedDict):
    locale: str
    pre: bool
    sd: bool
    covid: bool

class DateType(IntEnum):
    WORKING = 0
    NOT_WORKING = 1
    SHORTENED = 2
    WORKING_DAY = 4


class ProdCalendar:
    LOCALES = ('ru', 'ua', 'kz', 'by', 'us')
    DELIMETER = '%7C'
    _FORMAT_DATE = '%Y%m%d'
    __version__ = 1.0

    def __init__(self,
                 locale: str = 'ru',
                 base_url: str = 'https://isdayoff.ru',
                 format_date: str = '%Y.%m.%d'
                 ) -> NoReturn:
        self.format_date = format_date
        self.locale = self._is_valid_locale(locale)
        self.base_url = base_url
        self._session = Session()
        self._session.headers.update({
            'User-Agent': f'python/{self.__version__} Contact with the developer by email - wg7831@gmail.com'
        })

    def _get(self, url, *args, **kwargs):
        response = self._session.get(self.base_url + url, *args, **kwargs)
        if response.status_code == 400:
            raise DataError('Date error')
        if response.status_code != 200:
            raise ServiceNotRespond('No data found')
        return response.text

    def _is_valid_locale(self, locale):
        if locale not in self.LOCALES:
            raise ValueError(f'locale must be in {self.LOCALES}')
        return locale

    def _filter_dict(self, dict_: dict):
        return {key: value for key, value in dict_.items() if value}

    def format_result(self, date: datetime.date, result: List[str]):
        return {
            (date + datetime.timedelta(days=day)).strftime(self.format_date): DateType(int(value))
            for day, value in zip(range(0, len(result)), result)
        }

    def result_date_type(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            return DateType(int(f(*args, **kwargs)))

        return wrapper

    def _get_date_work(self,
                             data: datetime.date,
                             is_day=True, is_month=True,
                             locale=False, pre=False, sd=False, covid=False
                             ) -> str:
        return self._get(
            '/api/getdata',
            params=self._filter_dict({
                'year': data.year,
                'month': is_month and data.month,
                'day': is_day and data.day,
                'delimeter': not (is_month and is_day) and self.DELIMETER,
                'cc': self._is_valid_locale(locale if locale else self.locale),
                'pre': int(pre),
                'sd': int(sd),
                'covid': int(covid)
            })
        )

    def _get_range_date_work(self,
                                   start_date: datetime.date, end_date: datetime.date,
                                   locale=False, pre=False, sd=False, covid=False
                                   ) -> str:
        return self._get(
            '/api/getdata',
            params=self._filter_dict({
                'date1': start_date.strftime(self._FORMAT_DATE),
                'date2': end_date.strftime(self._FORMAT_DATE),
                'delimeter': self.DELIMETER,
                'cc': self._is_valid_locale(locale if locale else self.locale),
                'pre': int(pre),
                'sd': int(sd),
                'covid': int(covid)
            })
        )

    def range_date(self, start_date: datetime.date, end_date: datetime.date, **kwargs: ParamsApi) -> Dict[
        str, DateType]:
        result = (self._get_range_date_work(start_date, end_date, **kwargs)).split(self.DELIMETER)
        return self.format_result(datetime.date(start_date.year, start_date.month, start_date.day), result)

    def month(self, date: datetime.date, **kwargs: ParamsApi) -> Dict[str, DateType]:
        result = (self._get_date_work(date, is_day=False, **kwargs)).split(self.DELIMETER)
        return self.format_result(datetime.date(date.year, date.month, 1), result)

    def year(self, date: datetime.date, **kwargs: ParamsApi) -> Dict[str, DateType]:
        result = (self._get_date_work(date, is_day=False, is_month=False, **kwargs)).split(self.DELIMETER)
        return self.format_result(datetime.date(date.year, 1, 1), result)

    @result_date_type
    def date(self, date: datetime, **kwargs: ParamsApi) -> DateType:
        return self._get_date_work(date, **kwargs)

    @result_date_type
    def tomorrow(self, **kwargs: ParamsApi) -> DateType:
        return self._get_date_work((datetime.datetime.now() + datetime.timedelta(days=1)), **kwargs)

    @result_date_type
    def today(self, **kwargs: ParamsApi) -> DateType:
        return self._get_date_work(datetime.datetime.now(), **kwargs)

    def is_leap(self, date: datetime.date) -> bool:
        return date.year % 4 == 0 and date.year % 100 != 0 or date.year % 400 == 0

    def close(self) -> NoReturn:
        self._session.close()
