import sqlite3
import argparse
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format=(
        '%(asctime)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s'
    ),
    datefmt="%Y-%m-%d %H:%M:%S",
)


DB_PATH = Path(r'C:\Users\A.A.Fedorov\MES\ideal_context\te')

def execute_sql(db_path: Path, sql_text: str):
    with sqlite3.connect(db_path) as conn:
        conn.execute('PRAGMA foreign_keys = ON')
        conn.executescript(sql_text)
        conn.commit()


def execute_ddl(in_path: Path, out_path: Path):
    if not in_path.exists() or not in_path.is_dir():
        raise FileNotFoundError(f'Директории {in_path} не существует!')
    out_path.mkdir(parents=True, exist_ok=True)

    sql_files = in_path.glob('*.sql')
    for sql_file in sql_files:
        new_db_file = out_path / f'{sql_file.stem}.db'
        execute_sql(db_path=new_db_file, sql_text=sql_file.read_text(encoding='utf-8'))


if __name__ == '__main__':
    execute_ddl(in_path=Path(r'C:\Users\A.A.Fedorov\MES\ideal_context\sql\sqlite3_main\ddl'), out_path=DB_PATH)