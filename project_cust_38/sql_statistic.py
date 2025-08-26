import base64
import hashlib
import inspect
import json
import os
import sys
import time
from functools import wraps

from project_cust_38 import Cust_config as CFG


#18.08.25
class StatisticDecorator:
    config = None
    def __init__(self, function):
        self.function = function
        wraps(self.function)(self)

    def _encode_struct(self, obj):
        if isinstance(obj, dict):
            return {k: self._encode_struct(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._encode_struct(v) for v in obj]
        elif isinstance(obj, (set, frozenset)):
            return sorted([self._encode_struct(v) for v in obj], key=lambda x: str(x))
        elif isinstance(obj, bytes):
            return base64.b64encode(obj).decode("ascii")
        else:
            return obj

    def encode_struct(self, struct):
        """Преобразует структуру в сериализуемый вид с base64 для bytes"""
        return self._encode_struct(struct)

    def hash_for_http(self, data) -> str:
        encoded_data = self.encode_struct(data)
        serialized = json.dumps(
            encoded_data,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(serialized.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    def deep_size(self, obj, seen=None) -> int:
        if seen is None:
            seen = set()
        obj_id = id(obj)
        if obj_id in seen:
            return 0
        seen.add(obj_id)
        size = sys.getsizeof(obj)

        if isinstance(obj, dict):
            size += sum(self.deep_size(k, seen) + self.deep_size(v, seen) for k, v in obj.items())
        elif isinstance(obj, (list, tuple, set, frozenset)):
            size += sum(self.deep_size(i, seen) for i in obj)
        return size

    def unpack_argument(self, key: str, args, kwargs):
        sig = inspect.signature(self.function)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        return bound.arguments.get(key)

    def get_used_tables(self, bd, sql, attach_dbs):
        try:
            sql = sql.replace('?', "''")
            result = self.function(bd, f'EXPLAIN QUERY PLAN {sql}', attach_dbs=attach_dbs)
        except Exception as e:
            print(e)
            return []
        if not isinstance(result, (tuple, list, set)):
            return []
        return result

    def task(self, start, result, args, kwargs):
        try:
            end = time.time() - start # 1. Время затраченное на исполнение с учетом кодирования
            length = self.deep_size(result) # 2. Вес результата (в байтах)
            hash_body = self.hash_for_http(result) # 3. Хэш сумма ответа
            hash_args = self.hash_for_http((args, kwargs)) # 4. Хэш сумма аргументов
            query = self.unpack_argument('custom_request_c', args, kwargs) # 5. Запрос
            bd = self.unpack_argument('bd', args, kwargs) # 6. Имя базы данных
            attach_dbs = self.unpack_argument('attach_dbs', args, kwargs) # 6. Имя базы данных
            if CFG.Config.app.is_disabled or CFG.Config.user_CFG.Config.is_developer:
                return result
            if not bd or not result:
                return result
            app_name = CFG.Config.app.app
            files = CFG.Config.project.db_files
            if not app_name:
                return
            if files == '':
                return result
            used_tables = self.get_used_tables(bd, query, attach_dbs)
            body = {'query': query,
                    'app': app_name,
                    'size': length,
                    'db_name': bd,
                    'hash_body': hash_body,
                    'hash_args':  hash_args,
                    'completion_time': end,
                    'used_tables': ';'.join(used_tables)}
            questions = ','.join('?' for _ in body.values())
            keys = ', '.join(body.keys())
            insert_query = f""" INSERT INTO SqlEvents({keys}) VALUES ({questions})"""
            self.function(files, insert_query, list_of_lists_c=[list(body.values())])
        except Exception as e:
            print('[Ошибка]Сохранение статистики SQL: ', e)

    def __call__(self, *args, **kwargs):
        start = time.time()
        result = self.function(*args, **kwargs)
        if os.environ.get('MES_CFG.Config_INITIALIZED'):
            from concurrent.futures import ThreadPoolExecutor
            pool = ThreadPoolExecutor(max_workers=1)
            pool.submit(self.task, start, result, args, kwargs)
        return result
# --18.08.25