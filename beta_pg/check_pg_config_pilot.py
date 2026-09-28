
from collections import Counter
import json
import os


def compare_rows(sqlite_rows, postgres_rows):
    def fingerprint(rows):
        return Counter(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) for row in rows)
    return fingerprint(sqlite_rows) == fingerprint(postgres_rows)


def main():
    os.environ['PG_CONN'] = '0'
    os.environ['MES_PG_PROBE_ENABLED'] = '0'
    os.environ['MES_PG_PILOT_ENABLED'] = '0'
    from project_cust_38 import Cust_pg_pilot as pilot
    try:
        from project_cust_38 import Cust_SQLite as csq
        from project_cust_38 import Cust_postgresql_executor as pg
        executor = pg.configure_default_runtime(
            pg.ExecutorConfig.from_env(), schema_map=pg.SchemaRegistry.from_env(),
        )
        database = csq.DB_NAMES.db_users
        equal = True
        try:
            for table in ('config', 'app_config'):
                query = f'SELECT * FROM "{table}"'
                sqlite_rows = csq.custom_request_c(database, query, rez_dict=True, debug=False)
                with executor.transaction(database, read_only=True, timeout_sec=2) as tx:
                    tx.custom_request_c("SELECT set_config('statement_timeout', '3000ms', true)")
                    postgres_rows = tx.custom_request_c(query, rez_dict=True)
                if not isinstance(sqlite_rows, list) or not isinstance(postgres_rows, list):
                    raise RuntimeError(f'{table}: получен некорректный формат результата')
                match = bool(sqlite_rows) and compare_rows(sqlite_rows, postgres_rows)
                print(f'{table}: SQLite={len(sqlite_rows)}, PostgreSQL={len(postgres_rows)}, '
                      f'совпадение={match}')
                equal = equal and match
        finally:
            executor.close()
        print('READY: обе таблицы совпали' if equal else 'STOP: таблицы различаются или пусты')
        return 0 if equal else 2
    except Exception as exc:
        print('STOP: ' + pilot._error_summary(exc))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
