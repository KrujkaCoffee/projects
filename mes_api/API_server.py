from __future__ import annotations
import os
import importlib
import traceback
from threading import Thread
import socket
import time
import sys, io
from typing import Union, List, Any

import uvicorn
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, BackgroundTasks, Request, HTTPException, Response, Depends
from fastapi.responses import FileResponse

from project_cust_38 import Cust_b24 as B24
import project_cust_38.Cust_Functions as F
from dependencies import import_for1c_depend
import api_srv_config

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from project_cust_38 import for_1c

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PORT = api_srv_config.PORT
HOST = api_srv_config.HOST

fl_route_cust_files = False
try:
    import API_files_route

    fl_route_cust_files = True

except:
    pass

app = FastAPI()

app.add_middleware(
    CORSMiddleware,  # type: ignore
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
try:  # Revit router
    import revit_router

    app.include_router(revit_router.router, tags=["revit"])
except Exception as e:
    print(e)
# Автоматическое перенаправление HTTP → HTTPS
# app.add_middleware(HTTPSRedirectMiddleware)

if fl_route_cust_files:
    app.include_router(API_files_route.router)  # Маршрутизатор раздачи файлов(для пользовательского обновления)

try:
    from sync_b24_router import router as b24_router

    app.include_router(b24_router)
except Exception as e:
    print(e)
try:
    from route import app as router_1c

    app.include_router(router_1c)
except Exception as e:
    print(e)


class budget(BaseModel):  # noqa
    direction_key: Union[str, None] = None
    month: Union[str, None] = None
    list_month: Union[list, None] = None
    year: Union[int, None] = None


class data_compare_res(BaseModel):  # noqa
    ref_zp: str


class item_parse_prices(BaseModel):  # noqa
    nomen_cod: Union[str, None] = None,
    search_name: Union[str, None] = None,
    search_val: Union[str, None] = None,
    sensitivity_registr: Union[bool, None] = None,
    compars_oper_and: Union[bool, None] = None,
    uri: Union[str, None] = None
    return_name: Union[str, None] = None


class data_parse_prices(BaseModel):  # noqa
    data_nomens: List[item_parse_prices]


class data_get_file(BaseModel):  # noqa
    path_file: Union[str, None] = None,


class data_get_files(BaseModel):  # noqa
    path_files: List[data_get_file]


class data_send_drawback_fields(BaseModel):  # noqa
    STAGE_ID: Union[str, None] = None
    UF_CRM_1737711083528: Union[str, None] = None
    UF_CRM_1737727925: Union[str, None] = None


class data_send_drawback_journal(BaseModel):  # noqa
    ID: str | int | None = None
    FIELDS: Union[data_send_drawback_fields, None] = None


class data_nd_price_calculation(BaseModel):  # noqa
    RefKey: str | None = None
    Товары2_5: Any = None  # noqa
    RefKeyND: str | None = None


class data_calc_alloy_price(BaseModel):  # noqa
    data_mats_prices: list[dict] | None = None
    alloy_composition: list[dict] | None = None
    analog_threshold: float | None = None


class AuthModel(BaseModel):
    fio: str
    password: str
    update_date: bool = True


@app.post("/authenticate")  # 06.03.2026
def authenticate(body: AuthModel):
    from project_cust_38 import Cust_mes as CMS
    if not F.existence_file_c(api_srv_config.PASSWORD_STORAGE):
        raise HTTPException(status_code=500, detail='Не найден файл паролей')
    passwords = F.load_file_pickle(api_srv_config.PASSWORD_STORAGE)
    for i in range(len(passwords)):
        log = passwords[i][0]
        par = passwords[i][1]
        if CMS.shifr(body.fio.strip()) in log.strip():
            form_hash = CMS.shifr(body.password)
            return par == form_hash
    return None


@app.post("/register")
def register(body: AuthModel) -> str:
    from project_cust_38 import Cust_mes as CMS
    if not F.existence_file_c(api_srv_config.PASSWORD_STORAGE):
        F.save_file_pickle(api_srv_config.PASSWORD_STORAGE, [['', '', F.now('')]])
    rez = authenticate(body)
    if rez is not None:
        return "Пользователь уже зарегистрирован"
    current_year = F.date(vid='yyyy')
    passwords = F.load_file_pickle(api_srv_config.PASSWORD_STORAGE)
    passwords.append([CMS.shifr(body.fio), CMS.shifr(current_year), F.now('')])
    F.save_file_pickle(api_srv_config.PASSWORD_STORAGE, passwords)
    return f"Новый пользователь зарегистрирован: \n {body.fio} \n {current_year}"


@app.post("/change-password")
def change_password(body: AuthModel) -> bool:
    from project_cust_38 import Cust_mes as CMS
    passwords = F.load_file_pickle(api_srv_config.PASSWORD_STORAGE)
    now = F.now('')
    for i in range(len(passwords)):
        if passwords[i][0] == CMS.shifr(body.fio):
            passwords[i][1] = CMS.shifr(body.password)
            if len(passwords[i]) == 2:
                passwords[i].append(now)
            else:
                passwords[i][2] = now if body.update_date else ''
            break
    F.save_file_pickle(api_srv_config.PASSWORD_STORAGE, passwords)
    F.save_file_pickle(api_srv_config.PASSWORD_STORAGE + f'_back_{F.now("%Y%m%d")}', passwords)
    return True


@app.post("/check-actual-password")
def check_actual_password(body: AuthModel) -> bool:
    from project_cust_38 import Cust_mes as CMS
    import datetime
    current_year = datetime.datetime.now().year
    default_passwords = [CMS.shifr(str(current_year + i)) for i in range(-5, 6)]

    if not body.fio:
        return True
    if not F.existence_file_c(api_srv_config.PASSWORD_STORAGE):
        raise HTTPException(status_code=500, detail='Не найден файл паролей')
    passwords = F.load_file_pickle(api_srv_config.PASSWORD_STORAGE)
    for i in range(len(passwords)):
        if CMS.shifr(body.fio.strip()) in passwords[i][0].strip():
            if len(passwords[i]) == 2:
                return False
            try:
                if passwords[i][1] in default_passwords and F.add_months(passwords[i][2], 1) < F.now(''):
                    return False
            except:
                return False
            return True
    return True


def eval_1c_test_v1(data):
    return 'ok'


def list_of_dicts_to_list_of_lists_dicts(data):
    rez = []
    for dict in data:
        row = []
        for k, v in dict.items():
            tmp_list = [{k: v}]
            row.append(tmp_list)
        rez.append(row)
    return rez


@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc):
    line_wrap = f"\n\n{'-' * 36}\n\n"
    b24_err_msg_form = f'%(title)s{line_wrap}%(body)s{line_wrap}'
    rel_url = request.url.path
    stack = traceback.format_exception(type(exc), value=exc, tb=exc.__traceback__)
    body = '\n'.join(element for element in stack if 'site-packages' not in element)
    func_name = request.scope["endpoint"].__name__
    message = b24_err_msg_form % {'title': f'route: {rel_url}\nroute_handler: {func_name}\nexception: {exc}',
                                  'body': body}
    if not api_srv_config.IS_PROD:
        print(message)
    else:
        B24.B24Sender().send_msg_by_chat_id('chat77068', message)
    # if rel_url.startswith('/hs/1c/'): #20.10.25 reload в depends
    #     thread = Thread(target=relaod_modules)
    #     thread.start()
    return JSONResponse(content={"detail": "Сервер временно недоступен"}, status_code=500)


@app.get("/")
def ping():
    try:
        resp = f'{F.now()} for_1c.DATA_1С_VERSION: {for_1c.DATA_1С_VERSION}'
        print(resp)
    except Exception as e:
        print("/ping ошибка: ", e)
    return JSONResponse("pong", status_code=200)


@app.get("/hs/mes/open_local_path_dir/{module_name}/{filename}")
async def open_local_dir(
        module_name: str,
        filename: str
):
    PREFIX_PATH = api_srv_config.PREFIX_OPEN_LOCAL_DIR

    def gen_path():
        return os.sep.join([PREFIX_PATH, module_name])

    def gen_shortcut_name():
        return filename

    def gen_pathf():
        return os.sep.join([PREFIX_PATH, module_name, filename])

    file_path = gen_path()
    filename = gen_shortcut_name()
    if not F.existence_file_c(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    with open("Setup.url", "w") as f:
        f.write(f"[InternetShortcut]\nURL=file:///{gen_pathf()}\n")

    return FileResponse("Setup.url", filename="MES_Setup.url")


@app.get("/hs/mes/download-temp/{module_name}/{filename}")
async def download_temp_file(
        module_name: str,
        filename: str,
        background_tasks: BackgroundTasks,
        response: Response
):
    PREFIX_PATH = api_srv_config.PREFIX_DOWNLOAD_PATH

    def delete_file(file_path: str):
        """Функция для безопасного удаления файла"""
        try:
            F.delete_file_c(file_path)

            print(f"Файл {file_path} успешно удален")
        except Exception as e:
            print(f"Ошибка удаления файла {file_path}: {str(e)}")

    def gen_path():
        return os.sep.join([PREFIX_PATH, module_name, filename])

    file_path = gen_path()

    if not F.existence_file_c(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        # Устанавливаем важные security headers
    # response.headers["Content-Security-Policy"] = "default-src 'self'"
    # response.headers["X-Content-Type-Options"] = "nosniff"

    # Для смешанного контента (если必須 использовать HTTP)
    # response.headers["Upgrade-Insecure-Requests"] = "1"
    # Добавляем задачу на удаление после отправки
    background_tasks.add_task(delete_file, file_path)

    return FileResponse(
        path=file_path,
        filename=filename,
        # media_type='application/octet-stream',
        headers={
            "Content-Disposition": f"attachment; filename={filename}"}
    )


# ---------------1C----------------------------------
@app.post("/hs/1c/{item_id}/{sub_id}/{version}")
def table_part_processing(item_id, sub_id, version, data: data_nd_price_calculation,
                          for_1c=Depends(import_for1c_depend)):
    resp = "err"
    status_code = 500
    if item_id == 'table_part_processing':
        if sub_id == 'test':
            resp = eval_1c_test_v1(data)
            if resp:
                status_code = 200

        # //БеляковАГ, Пауэрз, 11.12.2025
        # //Постановщик: Захарова
        # //Краткое описание цели: 100062960 чтобы расчет вычисляемых полей был завязан на направление деятельности, по которому производится данная продукция.
        # //Краткое описание правки: добавлен вывод на АПИ с доп. расчетами
        # //Журнал: https://bitrix24.kelast.ru/docs/pub/34b9c2938b7d2fccaad26e33ac866397/goToEdit/?&
        # //+++++++++++++++++++++++++++++++++++++
        # На ПАУЗЕ
        # if sub_id == 'nd_price_calculation':
        #    if version == 'v1':
        #        tch = list_of_lists_dicts_to_list_of_dicts(data.Товары2_5)
        #        status_code, data, errs = for_1c.eval_1c_nd_price_calculation_v1(data.RefKey, data.RefKeyND, tch)
        #        if status_code == 200:
        #            resp = list_of_dicts_to_list_of_lists_dicts(data)
        #        else:
        #            resp = errs

    print(f'{F.now()} Req: {item_id} {sub_id} {version}\nResp:{status_code}')

    return JSONResponse(resp, status_code=status_code)


@app.post("/hs/1c/{item_id}/{version}")
def create_upload_file(item_id, version, data:
budget | data_parse_prices | data_get_files | data_compare_res | data_send_drawback_journal | data_calc_alloy_price,
                       for_1c=Depends(import_for1c_depend)):
    resp = "err"
    status_code = 500
    if item_id == 'test':
        if version == 'v1':
            resp = eval_1c_test_v1(data)
            if resp:
                status_code = 200
    if item_id == 'budget':
        if version == 'v1':
            resp = None
            try:
                resp = list_of_dicts_to_list_of_lists_dicts(for_1c.eval_1c_budget_v1(data))
                status_code = 200
            except:
                pass

    if item_id == 'budgetzvp':
        if version == 'v1':
            resp = None
            try:
                answ, list_err = for_1c.eval_1c_budgetzvp_v1(data)
                resp = {"Данные": list_of_dicts_to_list_of_lists_dicts(answ), "Ошибки": list_err}
                status_code = 200
            except:
                pass

    if item_id == 'parse_prices':
        if version == 'v1':
            resp = None
            try:
                answ = for_1c.eval_1c_parse_prices_v1(data)
                resp = {"Данные": list_of_dicts_to_list_of_lists_dicts(answ)}
                status_code = 200
            except:
                pass

    if item_id == 'compare_res':
        if version == 'v1':
            resp = None
            try:
                answ, list_err, max_width = for_1c.compare_res_1c_v1(data.ref_zp)
                resp = {"Данные": {'ОбщееШирина': max_width, 'Таблица': list_of_dicts_to_list_of_lists_dicts(answ)},
                        "Ошибки": list_err}
                status_code = 200
            except Exception as e:
                import sys
                import logging
                logging.basicConfig(level=logging.INFO)

                logging.error('Ошибка', exc_info=e)
                pass

    if item_id == 'calc_alloy_price':
        if version == 'v1':
            resp = None
            try:
                answ, list_err = for_1c.calc_alloy_price(data.data_mats_prices,
                                                         data.alloy_composition,
                                                         data.analog_threshold)
                resp = {"Данные": {'Стоимость': answ}, "Ошибки": list_err}
                status_code = 200
            except:
                pass

    print(f'{F.now()} Req: {item_id} {version}\nResp:{status_code}')

    return JSONResponse(resp, status_code=status_code)


# ---------------MES----------------------------
@app.get("/hs/mes/{item_id}/{version}")
def mes_methods_get(item_id, version, data: data_get_files, for_1c=Depends(import_for1c_depend)):
    resp = "err"
    status_code = 500
    if item_id == 'test':
        if version == 'v1':
            resp = eval_1c_test_v1(data)
            if resp:
                status_code = 200
    if item_id == "get_file":
        if version == 'v1':
            resp = None
            try:
                answ, list_err = for_1c.get_file(data.path_files)
                resp = {"Данные": answ, "Ошибки": list_err}
                status_code = 200
            except:
                pass

    print(f'{F.now()} Req: {item_id} {version}\nResp:{status_code}')

    return JSONResponse(resp, status_code=status_code)


@app.post("/hs/mes/{item_id}/{version}")
def mes_methods_post(item_id, version, data: data_send_drawback_journal, for_1c=Depends(import_for1c_depend)):
    resp = "err"
    status_code = 500

    if item_id == "send_drawback_journal":
        if version == 'v1':
            resp = None
            try:
                # data_dict = {"ID":data.ID,"FIELDS":{"STAGE_ID":data.FIELDS.STAGE_ID}}
                data_dict = data.model_dump()
                answ, list_err = for_1c.update_drawback_journal(data.ID, data_dict)
                resp = {"Данные": answ, "Ошибки": list_err}
                status_code = 200
            except:
                pass

    print(f'{F.now()} Req: {item_id} {version}\nResp:{status_code}')

    return JSONResponse(resp, status_code=status_code)


if __name__ == "__main__":
    while True:
        uvicorn.run("API_server:app", host=HOST, port=PORT, reload=False)
        print('OK')
        F.sleep(3)

