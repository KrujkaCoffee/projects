import calendar
from datetime import datetime, date, timedelta
import hashlib
import json
import logging
import os
from enum import IntEnum
from functools import wraps
from pathlib import Path
import tempfile
import time
from typing import List, Dict

from project_cust_38 import api_erp_commands as APIERP  # noqa
from project_cust_38 import Cust_Functions as F  # noqa
from project_cust_38 import Cust_config as CFG  # noqa


class ServiceNotRespond(Exception):
    pass


class DataError(Exception):
    pass


class DateType(IntEnum):
    WORKING = 0
    NOT_WORKING = 1
    SHORTENED = 2
    WORKING_DAY = 4


DAY_CODES = {
    'Рабочий': 0,
    'Предпраздничный': 2,
    'Суббота': 1,
    'Воскресенье': 1,
    'Праздник': 1,
}


def fetch_year(year: int, calendar_key: str) -> list[dict]:
    query = f'''
ВЫБРАТЬ
    УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Данные.ПроизводственныйКалендарь) КАК КлючКалендаря,
    ГОД(Данные.Дата) КАК Год,
    МЕСЯЦ(Данные.Дата) КАК Месяц,
    ДЕНЬ(Данные.Дата) КАК День,
    ПРЕДСТАВЛЕНИЕ(Данные.ВидДня) КАК ВидДня
ИЗ
    РегистрСведений.ДанныеПроизводственногоКалендаря КАК Данные
ГДЕ
    Данные.ПроизводственныйКалендарь = &Календарь
    И Данные.Дата >= ДАТАВРЕМЯ({year}, 1, 1)
    И Данные.Дата < ДАТАВРЕМЯ({year + 1}, 1, 1)
УПОРЯДОЧИТЬ ПО Данные.Дата'''
    refs = APIERP.Refs_wet(query)
    refs.add_ref(
        APIERP.Ref_wet('Календарь', 'Справочники.ПроизводственныеКалендари', calendar_key)
    )
    status_code, data = APIERP.get_wet_request(query, refs)
    if status_code != 200:
        raise ServiceNotRespond(f'Не удалось запросить календарь 1С за {year}')
    if not isinstance(data, dict) or not isinstance(data.get('data'), list):
        raise DataError(f'Календарь 1С за {year}: ожидался объект с массивом data')
    return data['data']


def _validate_rows(year: int, calendar_key: str, rows: list[dict]) -> tuple[str, ...]:
    if not isinstance(rows, list):
        raise DataError(f'Календарь 1С за {year}: ожидался список записей')
    days = {}
    for row in rows:
        try:
            _date = date(*(F.valm(row[key]) for key in ('Год', 'Месяц', 'День')))
            kind = row['ВидДня']
            if _date.year != year or _date in days:
                raise ValueError(f'Лишняя или повторная дата {_date}')
            if kind not in DAY_CODES:
                raise ValueError(f'Неизвестный вид дня {kind!r} на {_date}')
            days[_date] = kind
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise DataError(f'Некорректная запись календаря 1С за {year}: {exc}') from exc
    expected = 366 if calendar.isleap(year) else 365
    if len(days) != expected:
        raise DataError(
            f'Неполный календарь 1С за {year}: {len(days)} из {expected} дат '
            f'(календарь {calendar_key})'
        )
    return tuple(days[_date] for _date in sorted(days))


class ProdCalendar:
    DELIMITER = '%7C'

    def __init__(self, locale, format_date='%Y.%m.%d', *, source=None):
        self.format_date = format_date
        self.calendar_key = CFG.Config.project.prod_calendar_uuid  # noqa
        self.cache_ttl = 6 * 60 * 60
        default_cache = Path(tempfile.gettempdir()) / '.cache' / 'prod_calendar1'
        self.cache_dir = Path(default_cache)
        self._source = source
        self._snapshots = {}
        self._closed = False

    def _cache_path(self, year: int) -> Path:
        day_mark = F.now('%Y%m%d')
        identity = f'{day_mark}|{self.calendar_key}|5'
        namespace = hashlib.sha256(identity.encode('utf-8')).hexdigest()
        return self.cache_dir / namespace / f'{year}.json'

    def _fresh(self, snapshot: dict) -> bool:
        age = time.time() - snapshot['fetched_at']
        return 0 <= age < self.cache_ttl

    def _read_cache(self, year: int) -> dict | None:
        path = self._cache_path(year)
        try:
            snapshot = json.loads(path.read_text(encoding='utf-8'))
            return snapshot if self._fresh(snapshot) else None
        except:
            return None

    def _write_cache(self, snapshot: dict):
        path = self._cache_path(snapshot['year'])
        temporary_path = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                    mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
                temporary_path = Path(stream.name)
                json.dump(snapshot, stream, ensure_ascii=False)
            os.replace(temporary_path, path)
        except OSError:
            logging.warning('Не удалось записать кэш календаря 1С за %s', snapshot['year'])
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass

    @staticmethod
    def _content_hash(kinds) -> str:
        return hashlib.sha256(''.join(str(DAY_CODES[kind]) for kind in kinds).encode('ascii')).hexdigest()

    def _load_year(self, year: int) -> dict:
        if self._closed:
            raise ValueError('ProdCalendar уже закрыт')
        snapshot = self._snapshots.get(year)
        if snapshot is not None and self._fresh(snapshot):
            return snapshot
        snapshot = self._read_cache(year)
        if snapshot is None:
            kinds = _validate_rows(year, self.calendar_key, fetch_year(year, self.calendar_key))
            snapshot = {
                'source': F.now('%Y%m%d'),
                'calendar_key': self.calendar_key,
                'year': year,
                'week_mode': 5,
                'fetched_at': time.time(),
                'kinds': list(kinds),
                'sha256': self._content_hash(kinds),
            }
            self._write_cache(snapshot)
        self._snapshots[year] = snapshot
        return snapshot

    def _get_date_work(self, data, is_day=True, is_month=True, pre=False, sd=False, covid=False):
        start = date(data.year, data.month if is_month else 1, data.day if is_day else 1)
        if is_day:
            end = start
        elif is_month:
            end = start.replace(day=calendar.monthrange(start.year, start.month)[1])
        else:
            end = start.replace(month=12, day=31)
        return self._get_range_date_work(start, end, pre, sd, covid)

    def _get_range_date_work(self, start_date, end_date, pre=False, sd=False, covid=False):
        if sd or covid:
            raise DataError('Календарь 1С поддерживает только пятидневку без режима COVID')
        start = date(start_date.year, start_date.month, start_date.day)
        end = date(end_date.year, end_date.month, end_date.day)
        length = (end - start).days + 1
        if not 1 <= length <= 366:
            raise DataError('Диапазон должен содержать от 1 до 366 дней включительно')
        values = []
        for year in range(start.year, end.year + 1):
            snapshot = self._load_year(year)
            jan1 = date(year, 1, 1)
            first = (max(start, jan1) - jan1).days
            last = (min(end, date(year, 12, 31)) - jan1).days + 1
            for kind in snapshot['kinds'][first:last]:
                code = DAY_CODES[kind]
                values.append(str(code if pre or code != 2 else 0))
        return self.DELIMITER.join(values)

    def close(self):
        if not self._closed:
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @staticmethod
    def _filter_dict(dict_: dict):
        return {key: value for key, value in dict_.items() if value}

    def format_result(self, _date: date, result: List[str]):
        return {
            (_date + timedelta(days=day)).strftime(self.format_date): DateType(int(value))
            for day, value in zip(range(0, len(result)), result)
        }

    @staticmethod
    def result_date_type(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            return DateType(int(f(*args, **kwargs)))

        return wrapper

    def range_date(self, start_date: date, end_date: date, **kwargs) -> Dict[
        str, DateType]:
        result = (self._get_range_date_work(start_date, end_date, **kwargs)).split(self.DELIMITER)
        return self.format_result(date(start_date.year, start_date.month, start_date.day), result)

    def month(self, _date: date, **kwargs) -> Dict[str, DateType]:
        result = (self._get_date_work(_date, is_day=False, **kwargs)).split(self.DELIMITER)
        return self.format_result(date(_date.year, _date.month, 1), result)

    def year(self, _date: date, **kwargs) -> Dict[str, DateType]:
        result = (self._get_date_work(_date, is_day=False, is_month=False, **kwargs)).split(self.DELIMITER)
        return self.format_result(date(_date.year, 1, 1), result)

    @staticmethod
    def is_leap(_date: date) -> bool:
        return _date.year % 4 == 0 and _date.year % 100 != 0 or _date.year % 400 == 0

    @result_date_type
    def date(self, _date: datetime, **kwargs) -> str:
        return self._get_date_work(_date, **kwargs)

    @result_date_type
    def tomorrow(self, **kwargs) -> str:
        return self._get_date_work((datetime.now() + timedelta(days=1)), **kwargs)

    @result_date_type
    def today(self, **kwargs) -> str:
        return self._get_date_work(datetime.now(), **kwargs)


if __name__ == '__main__':
    with ProdCalendar() as prod:
        calendar1 = prod.month(date(2016, 1, 1))
        print(calendar1)