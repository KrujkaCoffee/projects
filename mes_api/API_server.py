import os
import importlib
import traceback
from threading import Thread
import socket
import time
import sys, io
from typing import Union, List

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
    CORSMiddleware, # type: ignore
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Автоматическое перенаправление HTTP → HTTPS
#app.add_middleware(HTTPSRedirectMiddleware)

if fl_route_cust_files:
    app.include_router(API_files_route.router) # Маршрутизатор раздачи файлов(для пользовательского обновления)

try:
    from sync_b24_router import router as b24_router
    app.include_router(b24_router)
except Exception as e:
    print(e)

class budget(BaseModel):
    direction_key: Union[str, None] = None
    month: Union[str, None] = None
    list_month: Union[list, None] = None
    year: Union[int, None] = None

class data_compare_res(BaseModel):
    ref_zp: str

class item_parse_prices(BaseModel): # noqa
    nomen_cod: Union[str, None] = None,
    search_name: Union[str, None] = None,
    search_val: Union[str, None] = None,
    sensitivity_registr: Union[bool, None] = None,
    compars_oper_and: Union[bool, None] = None,
    uri: Union[str, None] = None
    return_name: Union[str, None] = None

class data_parse_prices(BaseModel): # noqa
    data_nomens: List[item_parse_prices]

class data_get_file(BaseModel): # noqa
    path_file: Union[str, None] = None,

class data_get_files(BaseModel): # noqa
    path_files: List[data_get_file]

class data_send_drawback_fields(BaseModel): # noqa
    STAGE_ID: Union[str, None] = None
    UF_CRM_1737711083528: Union[str, None] = None
    UF_CRM_1737727925: Union[str, None] = None

class data_send_drawback_journal(BaseModel): # noqa
    ID: str | int | None = None
    FIELDS: Union[data_send_drawback_fields, None] = None




def eval_1c_test_v1(data):
    return 'ok'


def list_of_dicts_to_list_of_lists_dicts(data):
    rez = []
    for dict in data:
        row = []
        for k,v in dict.items():
            tmp_list = [{k:v}]
            row.append(tmp_list)
        rez.append(row)
    return rez

# def relaod_modules():
#     STEP_HOURS_RELOAD_DATA_1C = 1
#     if F.now('') > F.date_add_time(F.strtodate(for_1c.DATA_1С_VERSION),hours=STEP_HOURS_RELOAD_DATA_1C):
#         print(f'======Old data 1c ver: {for_1c.DATA_1С_VERSION}==============',end='\n')
#         importlib.reload(for_1c)
#         print(f'======New data 1c ver: {for_1c.DATA_1С_VERSION}==============',end='\n\n\n')


@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc):
    line_wrap = f"\n\n{'-' * 36}\n\n"
    b24_err_msg_form = f'%(title)s{line_wrap}%(body)s{line_wrap}'
    rel_url = request.url.path
    stack = traceback.format_exception(type(exc), value=exc, tb=exc.__traceback__)
    body = '\n'.join(element for element in stack if 'site-packages' not in element)
    func_name = request.scope["endpoint"].__name__
    message = b24_err_msg_form % {'title': f'route: {rel_url}\nroute_handler: {func_name}\nexception: {exc}', 'body': body}
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
        resp =f'{F.now()} for_1c.DATA_1С_VERSION: {for_1c.DATA_1С_VERSION}'
        print(resp)
    except Exception as e:
        print("/ping ошибка: ", e)
    return JSONResponse("pong", status_code=200)


@app.get("/hs/mes/open_local_path_dir/{module_name}/{filename}")
async def open_local_dir(
        module_name:str,
        filename: str
):
    PREFIX_PATH = api_srv_config.PREFIX_OPEN_LOCAL_DIR

    def gen_path():
        return  os.sep.join([PREFIX_PATH,module_name])

    def gen_shortcut_name():
        return  filename
    def gen_pathf():
        return  os.sep.join([PREFIX_PATH,module_name,filename])
    file_path = gen_path()
    filename = gen_shortcut_name()
    if not F.existence_file_c(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    with open("Setup.url", "w") as f:
        f.write(f"[InternetShortcut]\nURL=file:///{gen_pathf()}\n")

    return FileResponse("Setup.url", filename="MES_Setup.url")


@app.get("/hs/mes/download-temp/{module_name}/{filename}")
async def download_temp_file(
        module_name:str,
        filename: str,
        background_tasks: BackgroundTasks,
        response: Response
):
    PREFIX_PATH = api_srv_config.PREFIX_DOWNLOAD_PATH
    def delete_file(file_path:str):
        """Функция для безопасного удаления файла"""
        try:
            F.delete_file_c(file_path)

            print(f"Файл {file_path} успешно удален")
        except Exception as e:
            print(f"Ошибка удаления файла {file_path}: {str(e)}")
    def gen_path():
        return  os.sep.join([PREFIX_PATH,module_name,filename])


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



@app.post("/hs/1c/{item_id}/{version}")
def create_upload_file(item_id,version,data:budget|data_parse_prices|data_get_files|data_compare_res,
                       for_1c = Depends(import_for1c_depend)):

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
                answ= for_1c.eval_1c_parse_prices_v1(data)
                resp = {"Данные":list_of_dicts_to_list_of_lists_dicts(answ)}
                status_code = 200
            except:
                pass

    if item_id == 'compare_res':
        if version == 'v1':
            resp = None
            try:
                answ, list_err ,max_width = for_1c.compare_res_1c_v1(data.ref_zp)
                resp = {"Данные": {'ОбщееШирина':max_width, 'Таблица':list_of_dicts_to_list_of_lists_dicts(answ)} , "Ошибки": list_err}
                status_code = 200
            except:
                pass

    print(f'{F.now()} Req: {item_id} {version}\nResp:{status_code}')

    return JSONResponse(resp, status_code=status_code)


@app.get("/hs/mes/{item_id}/{version}")
def mes_methods_get(item_id,version,data:data_get_files, for_1c = Depends(import_for1c_depend)):
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
                resp = {"Данные":answ,"Ошибки":list_err}
                status_code = 200
            except:
                pass

    print(f'{F.now()} Req: {item_id} {version}\nResp:{status_code}')

    return JSONResponse(resp, status_code=status_code)


@app.post("/hs/mes/{item_id}/{version}")
def mes_methods_post(item_id, version, data:  data_send_drawback_journal, for_1c = Depends(import_for1c_depend)):
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

