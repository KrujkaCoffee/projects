import requests
import os
import base64



def encode_file_to_base64(file_path):
    """
    При корректном конвертировании возвращает base64 строку
    Если неудача None
    """
    try:
        if isinstance(file_path, str):
            with open(file_path, 'rb') as file:
                file_content = file.read()
        if isinstance(file_path, bytes):
            file_content = file_path
        encoded_content = base64.b64encode(file_content).decode('utf-8')# Декодируем в строку
    except Exception as e:
        encoded_content = None
    return encoded_content

def send_file(
        document_ref: str,
        author_ref: str,
        file_name: str,
        size: int,
        ext: str,
        data: str,
        name: str = None
):
    try:
        response = requests.post(
            url='http://srv-1c:8088/ERP_MES1/ru_RU/hs/mes/sysexchange/v1/upload_file/asd',#'http://srv-1c:8088/ERP_MES1/ru_RU/hs/mes/sysexchange/v1/upload_file/asd'
            json={
                'Description': file_name,# полный путь с расширением
                'name': name,# Наименование файла
                'autor_Ref_Key': author_ref,  # Catalog_Пользователи
                'size': size,
                'format': ext,#расширение
                'data': data,
                'Ref_Key': document_ref
            }, auth=('mes_user', '89Luham')#auth=('OdataZNP', 'znp')
        )
    except Exception as e:
        print(e)
        return 501, f'Ошибка при отправке post запроса {e}'
    content_type = response.headers.get('Content-Type', '')
    if response.ok:
        return response.status_code, response.json()
    try:
        print('\n'.join(response.json()['Ошибки']))
    except:
        print(response.text)
    return response.status_code, response


def attach_file_for_1c_document(
        document_ref: str,
        content: bytes,
        author_ref: str,
        file_name: str
):
    # if not os.path.isfile(file_path):
    #     return
    name, ext  = os.path.splitext(file_name)
    size = len(content)
    encoded_file_view = encode_file_to_base64(content)
    if encoded_file_view is None:
        # CQT.msgbox(f'Не удалось прикрепить файл {file_name}')
        return
    code, response = send_file(
        document_ref=document_ref,
        author_ref=author_ref,
        file_name=file_name,
        data=encoded_file_view,
        size=size,
        ext=ext,
    ) # {'ЕстьОшибки': False, 'Ошибки': [], 'ФайлСсылка': 'ШПС.2404156.01.01 - Первая ступень дросселирования - A'}
    return code, response


if __name__ == '__main__':
    doc_ref = "15b7162c-41ce-11f0-a3f0-30e1716be59f"
    author_ref = 'e21b03db-31f9-11ee-84b1-00d861dd2b4a'
    attach_file_for_1c_document(
        document_ref=doc_ref,
        author_ref=author_ref,
        file_path=r'C:\Users\A.A.Fedorov\Downloads\IMG_0263.dng',

    )
