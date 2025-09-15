import dataclasses
import os
import typing
from urllib.parse import urlparse, parse_qs, quote, unquote

from requests import Session, Response, get

from project_cust_38 import Cust_Functions as F
from project_cust_38 import Cust_SQLite as CSQ


class Utils:
    def __init__(self, tmp_path: str):
        self.tmp_path = tmp_path

    def save_filename(self, filename: str, content: bytes):
        with open(os.path.join(self.tmp_path, filename), 'wb') as f:
            f.write(content)

    def humanize_text(self, text: str):
        return unquote(text)

    def unpack_header(self, headers: dict[str, str], name: str, param: str):
        if head := headers.get(name):
            dispositions = head.split(';')
            for disposition in dispositions:
                if disposition.strip().startswith(param):
                    return self.humanize_text(disposition.strip().split('=')[1])

    def unpack_filenames(self, data: list, key: str):
        chain = []
        for item in data:
            chain.extend(item.get(key))
        return chain

    @staticmethod
    def check_dxf_exists(lst: list):
        filenames = lst[15] or ''
        for filename in filenames.split('%20'):
            if not filename.startswith('docs://') and F.keep_extention_c(filename) == '.dxf':
                return filename

def get_file_object_id_by_nomen_name_from_MES(nomen_name: str):
    poki = 0
    db_response = CSQ.custom_request_c(
        'SRV:BD_dse.db',
        f'SELECT Путь_docs FROM dse WHERE Номенклатурный_номер = {nomen_name!r} and poki = {poki}',
        rez_dict=True,
        one=True
    )
    if isinstance(db_response, dict):
        try:
            url = db_response['Путь_docs']
            parsed_url = urlparse(url)
            # subdomain = parsed_url.netloc.split('.')[0]
            query_params = parse_qs(parsed_url.query)
            return int(query_params.get('objID', [None])[0])
        except Exception as e:
            print(e)

class HTTPClient:
    methods = ('POST', 'GET')
    def __init__(self):
        self.__session = None

    @property
    def session(self):
        if self.__session is None:
            raise Exception('Перед использованием session необходимо инициализировать контекстный менеджер with')
        return self.__session

    def __enter__(self):
        self.__session = Session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.__session.close()
            #print('[project_cust_38.Cust_docs]', exc_type, exc_val, exc_tb)
        except Exception as e:
            print(e)

    def get(self, url, params: dict[str, ...] | str):
        response = self.__session.get(url, params=params)
        content_types = response.headers.get('Content-Type', '')
        if 'application/json' not in content_types or not response.ok:
            return
        return response.json()

    def post(self, url, body: dict[str, ...] | str):
        response = self.__session.post(url, json=body)
        content_types = response.headers.get('Content-Type', '')
        if 'application/json' not in content_types or not response.ok:
            return
        return response.json()

class TFlexHttpClient(HTTPClient):
    BASE_URL = 'http://srv-tdocs:30100'

    # KOD ERP ENDPOINTS
    GET_CODE_ERP_BY_MATERIAL_NAME = '/api/kod-erp/mat/one/'
    GET_CODE_ERP_BY_STANDARD_PROD_NAME = '/api/kod-erp/standart/one/'

    # FILES ENDPOINTS
    GET_FILENAMES_BY_NOMEN_NAME = '/api/files/file/objectid'
    GET_BINARY_CONTENT_BY_OBJECT_ID = '/api/files/objectid'

    # Process TKP ENDPOINTS
    _GET_ALL_PROCESS_TKP_FROM_FITTING_FOLDER = '/api/process_tkp/armatura'
    _GET_ALL_PROCESS_TKP = '/api/process_tkp/all'
    _GET_ALL_PROCESS_TKP_FOLDERS = '/api/process_tkp/tkp-folders/all'
    _GET_ALL_PROCESS_TKP_SCHEMAS = '/api/process_tkp/stage/all'

    def make_url(self, endpoint: str):
        return f'{self.BASE_URL}{endpoint}'


class FolderTkp(typing.NamedTuple):
    id: int                             #[Папка процесса ТКП2] id
    uuid: str                           #[Папка процесса ТКП2] uuid
    name: str                           #[Папка процесса ТКП2] Наименование

class SchemaTkp(typing.NamedTuple):
    id: int                             #[Схема] ID
    uuid: str                           #[Схема] uuid
    name: str                           #[Схема] Наименование

class ProcessTkp(typing.NamedTuple):
    iD_card: int | None                 #[Карточка проекта] Id
    шифрИзделия_card: str | None        #[Карточка проекта] Шифр изделия
    номерПроекта_card: str | None       #[Карточка проекта] Номер проекта
    номерПозиции_card: str | None       #[Карточка проекта] Номер позиции
    наименование_card: str | None       #[Карточка проекта] Наименование
    датаСоздания_card: str | None       #[Карточка проекта] Дата создания

    названиеВарианта_card: str | None   #[Карточка проекта] Название варианта
    ссылкаДокс_card: str | None         #[Карточка проекта] Ссылка
    iD_proc: int                        #[Процесс ТКП2] Id
    ответственный_proc: int             #[Процесс ТКП2] Ответственный
    комментарий_proc: int               #[Процесс ТКП2] Комментарий
    наименование_proc: int              #[Процесс ТКП2] Наименование
    наименование_папки_proc: int        #[Процесс ТКП2] Наименование
    этап_proc: int                      #[Процесс ТКП2] Этап
    папка_proc: str                     #[Процесс ТКП2] Этап
    схема_proc: str                     #[Процесс ТКП2] Этап
    исполнитель_proc: int               #[Процесс ТКП2] Исполнитель
    датаЗапуска_proc: int               #[Процесс ТКП2] Дата запуска процесса
    статус_proc: int                    #[Процесс ТКП2] Статус процесса
    желаемаяДата_proc: int              #[Процесс ТКП2] Желаемая дата
    кодРС_proc: int                     #[Процесс ТКП2] КОд ресурсной
    ссылкаДокс_proc: int                #[Процесс ТКП2] Ссылка


class TFlexMaterialFinderClient(TFlexHttpClient):
    """
    with TFlexMaterialFinderClient() as client:
        client.get_kod_erp_by_mat('Лист ...')
    """
    def get_kod_erp_by_mat(self, mat_name: str):
        url = self.make_url(self.GET_CODE_ERP_BY_MATERIAL_NAME)
        response = self.session.post(url, json=mat_name)
        if response.status_code != 200:
            return response.status_code, f'"Ошибка DOCs:"\n{response.text}\nuri: "{url}"\nМат.: "{mat_name}"\nОбратиться к администратору Docs'
        data = response.json()
        if isinstance(data, dict) and len(data) >= 1:
            [value, *others] = data.values()
            return response.status_code, value
        return response.status_code, ''

    def get_kod_erp_by_standard_izd(self, name: str):
        url = self.make_url(self.GET_CODE_ERP_BY_STANDARD_PROD_NAME)
        response = self.session.post(url, json=name)
        data = response.json()
        if isinstance(data, dict) and len(data) >= 1:
            [value, *others] = data.values()
            return value
        return ''

    def get_filenames_by_nomen_name(self, name: str):
        url = f'{self.BASE_URL}{self.GET_FILENAMES_BY_NOMEN_NAME}'
        response = self.session.post(url, json=name)
        data = response.json()
        if isinstance(data, dict) and len(data) >= 1:
            [value, *others] = data.values()
            return value
        return ''

class TFlexFileClient(TFlexHttpClient):
    """
    with TFlexFileClient() as client:
        client.get_filenames_by_nomen_name()
    """
    def get_filenames_by_nomen_name(self, name: str) -> list:
        """
        1. Если в выборке присутсвует несколько идентификаторов номенклатур -> поиск наличия ссылки docs
        2. Извлекаем объекты связанные с номенклатурой привязанной к ссылке docs
        3. Если ссылка отсутсвует или объект с id из ссылки отсутствуют, возвращаем пустой список
        """
        url = f'{self.BASE_URL}{self.GET_FILENAMES_BY_NOMEN_NAME}'
        files = self.post(url, body=name)
        set_pks = {file['nomenId'] for file in files}
        if len(set_pks) == 1:
            return files
        docs_object_id = get_file_object_id_by_nomen_name_from_MES(name)
        if docs_object_id:
            return [
                file
                for file in files
                if file['nomenId'] == docs_object_id
            ]
        return []

    def get_binary_file(self, srv_name: str, object_id: str | int, revision: str | int) -> None | bytes:
        """
        1. Если в выборке присутсвует несколько идентификаторов номенклатур -> поиск наличия ссылки docs
        2. Извлекаем объекты связанные с номенклатурой привязанной к ссылке docs
        3. Если ссылка отсутсвует или объект с id из ссылки отсутствуют, возвращаем пустой список
        """
        url = self.make_url(self.GET_BINARY_CONTENT_BY_OBJECT_ID)
        response = self.session.get(url, params={
            'srvName': srv_name,
            'folder': object_id,
            'fileName': revision,
        })
        if response.ok:
            return response.content


class TFlexTkpProcessClient(TFlexHttpClient):
    """
    with TFlexTkpProcessClient() as client:
        code, data = client.get_process_tkp_from_fittings_folder()
    """
    def get_process_tkp_from_fittings_folder(self) -> tuple[int, list | Response]:
        url = self.make_url(self._GET_ALL_PROCESS_TKP_FROM_FITTING_FOLDER)
        response = self.session.get(url)
        if response.ok:
            return response.status_code, response.json()
        return response.status_code, response

    def get_tkp_folders(self) -> tuple[int, list[FolderTkp] | Response]:
        """
        Возвращает список папок процессов

        Пример ответа:
        [
            FolderTkp(id=1, uuid='ece411b6-0d8d-41cb-9245-d11945b9daec', name='Компенсатор тканевый'),
            FolderTkp(id=5, uuid='8bcfbed5-eeea-4654-9e8a-ec447a889ecf', name='БСИ'),
            FolderTkp(id=48, uuid='1b0fa0e6-ac0b-4474-9ba3-d00ddc719b6c', name='Арматура литая'),
            FolderTkp(id=794, uuid='4a2f95f0-bf36-4738-b55c-cfcd47c8d7db', name='Фильтр рукавный'),
            FolderTkp(id=795, uuid='ff7bc7ec-280e-4117-882f-31c701471bac', name='Рукав фильтровальный'),
            FolderTkp(id=2, uuid='ed83f528-1f48-43c2-82d6-f5a33b299661', name='Шумоглушитель'),
            FolderTkp(id=4, uuid='b311643c-66b6-4c23-8e7f-d65756266028', name='Аппарат обдувки'),
            FolderTkp(id=7, uuid='aaa94090-996d-4d9b-91c0-b4e917dfffb9', name='Система золоудаления')
        ]
        """
        url = self.make_url(self._GET_ALL_PROCESS_TKP_FOLDERS)
        response = self.session.get(url)
        if response.ok:
            return response.status_code, [FolderTkp(**item) for item in response.json()]
        return response.status_code, response

    def get_schemas_by_tkp_folder(self, tkp_folder_uuid: str) -> tuple[int, list[SchemaTkp] | Response]:
        """
        Возвращает схемы по uuid папки процессов ткп

        Пример запроса:
            folder_uuid = 'e5e9df01-4344-46dd-9446-1cc68bfe7f83'                        # uuid папки процесса ткп
            code, schemas_from_folder = client.get_schemas_by_tkp_folder(folder_uuid)

        Пример ответа:
        [
            SchemaTkp(id=3, uuid='d40cc903-e82e-4abc-8dd3-9d927fd49bc5', name='АО'),
            SchemaTkp(id=53, uuid='2d8ccd32-fbaa-491c-a273-af80e51a5eb4', name='АО. Комплекс')
        ]
        """
        url = self.make_url(self._GET_ALL_PROCESS_TKP_SCHEMAS)
        response = self.session.get(url, params={'folderGuid': tkp_folder_uuid})
        if response.ok:
            return response.status_code, [SchemaTkp(**item) for item in response.json()]
        return response.status_code, response

    def get_process_tkp(
            self,
            folder_uuid_lst: list[str] = (),
            schema_uuid_lst: list[str] = (),
    ) -> tuple[int, list[ProcessTkp] | Response]:
        """
        Возвращает элементы из справочника "процессы ТКП 2"

        Если без параметров, то вернет все существующие процессы

        Принимает:
        folder_uuid_lst: str    Список уникальных идентификаторов папок процессов
        schema_uuid_lst: str    Список уникальных идентификаторов схем процессов

        Примеры:
            data = get_process_tkp(folder_uuid_lst=['1b0fa0e6-ac0b-4474-9ba3-d00ddc719b6c'])
            Получить процессы из папки 'Арматура литая'
                где: 1b0fa0e6-ac0b-4474-9ba3-d00ddc719b6c - это uuid полученный из метода get_tkp_folders()

        2.
            Получить процессы из папки 'Система золоудаления' и входящей в неё схемы "СЗУ. Комплекс"
            with TFlexTkpProcessClient() as client:
                folder_reference = 'aaa94090-996d-4d9b-91c0-b4e917dfffb9'   # uuid папки полученный из метода get_tkp_folders()
                schema_reference = 'e5e9df01-4344-46dd-9446-1cc68bfe7f83'   # uuid схемы полученный из метода get_schemas_by_tkp_folder('aaa94090-996d-4d9b-91c0-b4e917dfffb9')
                data = client.get_process_tkp(
                    folder_uuid_lst=[folder_reference],
                    schema_uuid_lst=[schema_reference]
                )
        """
        url = self.make_url(self._GET_ALL_PROCESS_TKP)
        response = self.session.post(url, json={'folders': list(folder_uuid_lst), 'schemas': list(schema_uuid_lst)})
        if response.ok:
            return response.status_code, [ProcessTkp(**item) for item in response.json()]
        return response.status_code, response

#================== DOCS fncs==============================

def get_orders_tatkuz():#TEST

    headers = dict(Accept='application/json')
    params = dict()
    try:
        url = f'http://srv-docs:30100/api/tatkuz/proccess_tkp/all'
        response = get(url, json= dict(), headers=headers, params=params)
        #print(F.convert_binary_to_data(response.content))
        return response.status_code, JS.loads(F.convert_binary_to_data(response.content))
    except:
        return 0, None

def test_request_tkp_process():
    import random
    from pprint import pprint

    with TFlexTkpProcessClient() as client:
        code, folders = client.get_tkp_folders()        # Этап 1. получаем все папки процессов
        random_folder = random.choice(folders)
        pprint(f'Выбрана папка: {random_folder}')

        code, schemas_from_folder = client.get_schemas_by_tkp_folder(random_folder.uuid) # Этап 2. Выбираем схему по папке

        random_schema = random.choice(schemas_from_folder)
        pprint(f'Выбрана схема: {random_folder}')

        code, data_by_schema = client.get_process_tkp( # Этап 3. Выбираем процессы по схеме
            schema_uuid_lst=[random_schema.uuid]
        )
        pprint(f'Результат: {data_by_schema[:1]}')

if __name__ == '__main__':
    test_request_tkp_process()