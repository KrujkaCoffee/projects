import datetime
import os


def log_sql_callback(statement):
    try:
        file = datetime.datetime.now().strftime("%d.%m.%y")
        logs_dir = 'logs'
        if not os.path.exists(logs_dir):
            os.mkdir(logs_dir)

        with open(os.path.join(logs_dir, f'{file}.log'), 'a', encoding='utf-8') as file:
            file.write(f'{datetime.datetime.now()} {statement}\n')
    except Exception:
        ...
