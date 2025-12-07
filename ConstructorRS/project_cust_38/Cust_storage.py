import hashlib
import os
import pprint
import shutil
from dataclasses import dataclass

from PyQt5 import QtWidgets

from project_cust_38 import Cust_SQLite as CSQ
from project_cust_38 import Cust_config as CFG
from project_cust_38 import Cust_Functions as F
from project_cust_38 import Cust_Qt as CQT
from project_cust_38 import Cust_mes as CMS
import project_cust_38.Cust_docs as CDOCS


# Exceptions
@dataclass(frozen=True)
class FileSignature:
    """Сигнатура файла в хранилище."""
    sha1: str
    size: int


class FileIntegrityError(Exception):
    """Ошибка целостности файла при копировании / хранении."""
    pass



class BaseStorage:
    db_files = CFG.Config.project.db_files

    def __init__(self, local_storage_dir: str):
        """
        @param local_storage Папка локального хранилищая искомых файлов
        """
        self.base_dir = os.path.abspath(local_storage_dir)

    def _delete_file(self, filename: str):
        try:
            os.remove(os.path.join(self.base_dir, filename))
        except Exception as e:
            print(e)

    def _get_file_by_hash(self, hash_hex: str, size: int):
        custom_request_c = f"""
            SELECT * 
            FROM reestr 
            WHERE [size] = {size} and [hesh] = ? ;"""
        query = CSQ.custom_request_c(
            self.db_files,
            custom_request_c,
            rez_dict=True,
            one=True,
            list_of_lists_c=[hash_hex]
        )
        return query

    def _get_file_info(self, by_value: str, by_attr: str = 'name', many: bool = False):
        custom_request_c = f"""SELECT * FROM names WHERE {by_attr} == ?"""
        return CSQ.custom_request_c(self.db_files, custom_request_c,
                                    rez_dict=True, one=not many,
                                    list_of_lists_c=[by_value])

    def _add_data(self, size, hash_, bin_file, date, usr, storage = 'filesystem'):
        if storage == 'database':
            result = CSQ.custom_request_c(self.db_files, """INSERT INTO reestr(size, hesh, file, Date_edit, usr)
                             VALUES (?,?,?,?,?) RETURNING Пномер;""",
                list_of_lists_c=[size, hash_, bin_file, date, usr],
                hat_c=False,
                one_column=True)
            if not result or not isinstance(result, list):
                return
            return result[0]
        elif storage == 'filesystem':
            is_done = self.store_file(hash_, size, binary=bin_file) # 3
            if is_done:
                result = CSQ.custom_request_c(self.db_files, """INSERT INTO reestr(size, hesh, Date_edit, usr, storage)
                                 VALUES (?,?,?,?,?) RETURNING Пномер;""",
                    list_of_lists_c=[size, hash_, date, usr, 3],
                    hat_c=False,
                    one_column=True)
                if not result or not isinstance(result, list):
                    return
                return result[0]


    def _add_name(self, nom_data, name, date_edit, usr):
        result = CSQ.custom_request_c(self.db_files, """INSERT INTO names(nom_data, name, date_edit, usr)
                                 VALUES (?,?,?,?) RETURNING Пномер;""",
            list_of_lists_c=[nom_data, name, date_edit, usr],
            hat_c=False,
            one_column=True
        )
        if not result or not isinstance(result, list):
            return
        return result[0]

    def _update_data(self, size, hash_, bin_file, date, usr, pnom, storage = 'filesystem'):
        if storage == 'filesystem':
            if self.store_file(hash_, size, binary=bin_file):
                return CSQ.custom_request_c(self.db_files, f"""UPDATE reestr SET (size, hesh, file, Date_edit, usr, storage)
                             = (?,?,?,?,?) WHERE Пномер == {pnom};""",
                       list_of_lists_c=[size, hash_, None, date, usr, 3])
        elif storage == 'database':
            return CSQ.custom_request_c(self.db_files, f"""UPDATE reestr SET (size, hesh, file, Date_edit, usr)
                         = (?,?,?,?,?) WHERE Пномер == {pnom};""",
                   list_of_lists_c=[size, hash_, bin_file, date, usr])

    def _compute_signature(self, path: str) -> FileSignature:
        """Считает sha1 и размер для файла по пути."""
        h = hashlib.sha1()
        size = 0

        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                size += len(chunk)
                h.update(chunk)

        return FileSignature(sha1=h.hexdigest(), size=size)

    def _verify_copy(self, expected: FileSignature, dest_path: str) -> None:
        actual = self._compute_signature(dest_path)
        if actual != expected:
            raise FileIntegrityError(
                f"Хэш сумма файла {dest_path} не равна: "
                f"{expected} != {actual}"
            )

    def store_file(self, sha1_hex: str, size: int, binary: bytes) -> FileSignature | None:
        dest_dir = os.path.join(self.base_dir, sha1_hex)
        with open(dest_dir, 'wb+') as f:
            f.write(binary)
        signature = self._compute_signature(dest_dir)
        if signature.size == size and signature.sha1 == sha1_hex:
            return signature
        return None

    def retrieve_by_path(self, sha1_hex: str, dest_path: str) -> str | None:
        """
        Возвращает файл из хранилища по известному пути stored_path.
        Копирует его в dest_path (полный путь файла у пользователя).
        Делает проверку целостности копии.
        """
        path = os.path.join(self.base_dir, sha1_hex)
        if not os.path.isfile(path):
            return None
        full_stored = os.path.abspath(path)
        shutil.copy2(full_stored, dest_path)

        signature = self._compute_signature(full_stored)
        self._verify_copy(signature, dest_path)
        return dest_path

    def add_tkart(self, file_name, t_kard_name):
        query = CSQ.custom_request_c(self.db_files,f"""SELECT file_name,t_kard_name FROM t_kards WHERE file_name == '{file_name}' AND t_kard_name == '{t_kard_name}' """)
        if len(query)==1:
            CSQ.custom_request_c(self.db_files, """INSERT INTO t_kards(file_name,t_kard_name)
                                         VALUES (?,?);""",
                   list_of_lists_c=[[file_name,t_kard_name]])

class FileStorage(BaseStorage):
    def put_file(self, put_file: str = '', nom_tk: str = None):
        filename = put_file.split(os.sep)[-1]
        signature = self._compute_signature(put_file)
        size = signature.size
        bin_file = F.load_file_convert_to_binary(put_file)
        hash_ = signature.sha1
        query = self._get_file_by_hash(hash_hex=hash_, size=size)

        if query == {}:
            file_info = self._get_file_info(by_attr='name', by_value=filename)

            if file_info == {}:
                nom = self._add_data(size, hash_, bin_file, F.now("%Y-%m-%d %H-%M"), F.user_name())
                if nom == None:
                    CQT.msgbox(f'Ошибка загрузки')
                    return
                self._add_name(nom, filename, F.now("%Y-%m-%d %H-%M"), F.user_name())
            else:
                nom = file_info['Пномер']
                if nom_tk is not None:
                    custom_request_c3 = f"""SELECT t_kard_name, Пномер FROM t_kards WHERE file_name == ?"""
                    query3 = CSQ.custom_request_c(self.db_files, custom_request_c3, rez_dict=True,
                                                  list_of_lists_c=[filename])
                    list_cards = [_['t_kard_name'] for _ in query3]
                    if not CQT.msgboxgYN(
                            f'файл с именем {filename} уже существует, но с содержимое файла отличается от предложенного.\n'
                            f'Нужно убедиться что новый файл правильный и актуальный\n\n'
                            f'Обновить файл? Изменение затронет резку связанных техкарт:\n({str(list_cards)})'):
                        return
                self._update_data(size, hash_, bin_file, F.now("%Y-%m-%d %H-%M"), F.user_name(), nom)
        else:
            nom_data = query['Пномер']
            file_info = self._get_file_info(by_attr='nom_data', by_value=nom_data, many=True)

            if file_info == {}:
                self._add_name(nom_data, filename, F.now("%Y-%m-%d %H-%M"), F.user_name())
            else:
                names_from_db = [_['name'] for _ in file_info]
                if not filename in names_from_db:
                    if nom_tk is not None:
                        list_other_names = CSQ.custom_request_c(self.db_files, f"""SELECT names.name, t_kards.t_kard_name FROM names INNER JOIN 
                        t_kards ON  t_kards.file_name = names.name WHERE names.nom_data == {nom_data}""")
                        if not CQT.msgboxgYN(
                                f'Файл уже существует с другим наименованием :\n{pprint.pformat(list_other_names)}.'
                                f' \n\n Вероятно это ошибка!\n\n Следует ли '
                                f'вносить этому файлу дополнительное имя в БД?', icon=QtWidgets.QMessageBox.Warning):
                            return
                    self._add_name(nom_data, filename, F.now("%Y-%m-%d %H-%M"), F.user_name())
        if nom_tk is not None:
            self.add_tkart(filename, nom_tk)
        return filename
    
    def delete_file(self, name: str, nom_tk: str | int):
        list_uses_tk = CSQ.custom_request_c(self.db_files, f"""SELECT * FROM t_kards WHERE file_name == '{name}'""",
                                            rez_dict=True)
        if len(list_uses_tk) == 1 or len(list_uses_tk) == 0:
            list_uses_names = CSQ.custom_request_c(
                self.db_files,
    f"""SELECT names.*, reestr.hesh FROM names LEFT JOIN reestr ON reestr.Пномер = names.nom_data WHERE name == ?""",
                rez_dict=True,
                list_of_lists_c=[name]
            )
            if len(list_uses_names) == 1:
                nom_data = list_uses_names[0]['nom_data']
                datas = CSQ.custom_request_c(self.db_files, f"""SELECT * FROM names WHERE nom_data == '{nom_data}'""",
                                             rez_dict=True)
                if len(datas) == 1:
                    self._delete_file(list_uses_names[0]['hesh'])
                    CSQ.custom_request_c(self.db_files, f"""DELETE FROM reestr WHERE Пномер == {nom_data}""")
            CSQ.custom_request_c(self.db_files, f"""DELETE FROM names WHERE name == '{name}'""")
        CSQ.custom_request_c(self.db_files, f"""DELETE FROM t_kards WHERE file_name == '{name}'""")
        return

    def add_tkart(self, file_name, t_kard_name):
        query = CSQ.custom_request_c(self.db_files,f"""SELECT file_name,t_kard_name FROM t_kards WHERE file_name == '{file_name}' AND t_kard_name == '{t_kard_name}' """)
        if len(query)==1:
            CSQ.custom_request_c(self.db_files, """INSERT INTO t_kards(file_name,t_kard_name)
                                         VALUES (?,?);""",
                   list_of_lists_c=[[file_name,t_kard_name]])
    def get_file_by_name(self, name, destination_path: str = None):
        custom_request_c = f"""
            SELECT 
                reestr.file, 
                storage_types.name as storage,
                reestr.hesh
            FROM reestr 
            INNER JOIN names on names.nom_data = reestr.Пномер 
            LEFT JOIN storage_types ON storage_types.id = reestr.storage
            WHERE names.name == ?"""
        query = CSQ.custom_request_c(
            CFG.Config.project.db_files,
            custom_request_c,
            rez_dict=True,
            one=True,
            list_of_lists_c=[name]
        )
        if not query or not isinstance(query, dict):
            return False
        if destination_path is None:
            put_tmp = CMS.tmp_dir() + os.sep + 'tmp_files'
            if F.existence_file_c(put_tmp):
                F.ochist_papky(put_tmp)
            else:
                F.create_dir_c(put_tmp)
            put_file_tmp = CMS.tmp_dir() + os.sep + 'tmp_files' + os.sep + \
                           str(F.get_time_shtamp_c()).split('.')[-1] + "_" + \
                           F.transliterate(name.replace('ь', ''))
        else:
            put_file_tmp = destination_path

        if query['storage'] == 'database':
            F.save_binary_convert_to_file(query['file'], put_file_tmp)
            return put_file_tmp

        if query['storage'] == 'filesystem':
            return self.retrieve_by_path(query['hesh'], put_file_tmp)

    def get_dxf(self, file_names: str, nn: str, destination_dir: str = None, new_name: str | int = None) -> str | None:
        separated_names = file_names.split(CDOCS.DOCS_SEP)
        docs_manager = CDOCS.DocsFileManager()
        if destination_dir is None:
            destination_dir = CMS.tmp_dir() + os.sep + 'tmp_files'

        for filename in separated_names:
            if new_name is None:
                new_name = filename
            name, ext = os.path.splitext(filename)
            if ext != '.dxf': continue
            put_file_tmp = os.path.join(destination_dir, new_name)
            if docs_manager.is_docs_reference(filename):
                content = docs_manager.load_docs_file(filename, nn)
                put_file_tmp = os.path.join(destination_dir,new_name) #17.11.25 fix filename
                F.save_binary_convert_to_file(content.binary_content, put_file_tmp)
            else:
                if not self.get_file_by_name(filename, put_file_tmp):
                    return None
            return put_file_tmp
        return None
