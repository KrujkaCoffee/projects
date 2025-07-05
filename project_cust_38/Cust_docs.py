import os
from urllib.parse import urlparse, parse_qs, quote

from requests import Session

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
            print('[project_cust_38.Cust_docs]', exc_type, exc_val, exc_tb)
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

class TFlexMaterialFinderClient(HTTPClient):
    BASE_URL = 'http://srv-docs:30100'

    GET_CODE_ERP_BY_MATERIAL_NAME = '/api/kod-erp/mat/one/'
    GET_CODE_ERP_BY_STANDARD_PROD_NAME = '/api/kod-erp/standart/one/'
    GET_FILENAMES_BY_NOMEN_NAME = '/api/files/file/objectid'

    def get_kod_erp_by_mat(self, mat_name: str):
        url = f'{self.BASE_URL}{self.GET_CODE_ERP_BY_MATERIAL_NAME}'
        response = self.session.post(url, json=mat_name)
        if response.status_code != 200:
            return response.status_code, f'"Ошибка DOCs:"\n{response.text}\nuri: "{url}"\nМат.: "{mat_name}"\nОбратиться к администратору Docs'
        data = response.json()
        if isinstance(data, dict) and len(data) >= 1:
            [value, *others] = data.values()
            return response.status_code, value
        return response.status_code, ''

    def get_kod_erp_by_standard_izd(self, name: str):
        url = f'{self.BASE_URL}{self.GET_CODE_ERP_BY_STANDARD_PROD_NAME}'
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

class TFlexFileClient(HTTPClient):
    BASE_URL = 'http://srv-docs:30100'

    GET_FILENAMES_BY_NOMEN_NAME = '/api/files/file/objectid'
    GET_BINARY_CONTENT_BY_OBJECT_ID = '/api/files/objectid'

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
        url = f'{self.BASE_URL}{self.GET_BINARY_CONTENT_BY_OBJECT_ID}'
        response = self.session.get(url, params={
            'srvName': srv_name,
            'folder': object_id,
            'fileName': revision,
        })
        if response.ok:
            return response.content
