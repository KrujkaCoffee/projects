import os
import importlib
import time

FOR1C_RETRY_DELAY = 60 * 60

def import_for1c_depend():
    now_stamp = str(time.time())
    limit_stamp = str(time.time() + FOR1C_RETRY_DELAY)
    last_update = os.environ.get('LAST_UPDATE_FOR1C_MODULE', limit_stamp)
    try:
        from project_cust_38 import for_1c
        if (float(last_update) - float(now_stamp)) >= FOR1C_RETRY_DELAY:
            importlib.reload(for_1c)
            os.environ['LAST_UPDATE_FOR1C_MODULE'] = now_stamp
        yield for_1c
    except (NameError, ModuleNotFoundError) as e:
        print(e)
        # Если словим повторную ошибку прыгаем -> global_exception_handler и ловим оповещение
        from project_cust_38 import for_1c
        os.environ['LAST_UPDATE_FOR1C_MODULE'] = now_stamp
        yield for_1c