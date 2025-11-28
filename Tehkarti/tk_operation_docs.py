import pprint
import hashlib
import typing
import os
import re
from pathlib import Path

from PyQt5 import QtWidgets

from project_cust_38 import Cust_docs as CDOCS
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_config as CFG
import project_cust_38.Cust_storage as CSTORE


if typing.TYPE_CHECKING:
    from TehKart import mywindow

DOCS_NAME_FORMAT = 'docs://{file_id}/{full_name}'
DOCS_PATTERN = r'docs://(\d+)/(.+)'
DOCS_SEP = '%20'
# тк_просмотр_добавление_документов_докс

class OperationDocs:
    def __init__(self, window: 'mywindow', main_tbl: QtWidgets.QTableWidget):
        self.window = window
        self.main_tbl = main_tbl
        self.modal_tbl = None
        self.dialog: CQT.Dialog_tbl = None
        self.add_btn_state = False
        self.storage = CSTORE.FileStorage(CFG.Config.project.tk_storage_reestr)

    def show_modal(self, *args):
        docs = self.get_oper_docs(include_tflex_data=True)
        self.dialog = CQT.Dialog_tbl(
            self.window,
            WindowTitle='Просмотр документов',
            msg='Просмотр документов',
            dict_or_list=docs,
            func_oform_tbl=self.oform_tbl,
            btn0_name='Прикрепить документ',
            btn1_name='Выход',
            func_btn0=self.dob_doc
        )
        self.modal_tbl = self.dialog.ui.tbl
        self.btn_attach_file = QtWidgets.QPushButton('Загрузить с диска ...')
        self.btn_attach_file.setFixedHeight(30)
        self.btn_attach_file.setFixedWidth(self.dialog.yes_btn.width())
        self.btn_attach_file.setAutoDefault(False)
        self.btn_attach_file.clicked.connect(self.load_user_file)
        font = self.btn_attach_file.font()
        font.setPixelSize(14)
        self.btn_attach_file.setFont(font)
        self.dialog.ui.lbl_text.hide()
        self.dialog.ui.buttonBox.addButton(self.btn_attach_file, QtWidgets.QDialogButtonBox.ActionRole)
        self.dialog.accept = lambda *_: None
        # self.dialog.yes_btn.setEnabled(self.add_btn_state)
        returnValue = self.dialog.exec()

    def oform_tbl(self, tbl: QtWidgets.QTableWidget):
        docs = self.get_oper_docs()
        if len(docs) > 0:
            add_columns = {
                '👁': self.doc_view_clicked,
                '❌': self.doc_del_clicked,
                '📌': ''
            }
            for row in range(tbl.rowCount()):
                for ico, fn in add_columns.items():
                    col_ico = CQT.num_col_by_name_c(tbl, ico)
                    if ico == '📌' and self.is_attached(tbl, row):
                        tbl.item(row, col_ico).setText(ico)
                    elif self.is_attached(tbl, row) or ico == '👁':
                        CQT.add_btn(tbl, row, col_ico, text=ico, conn_func_checked_row_col=fn)

    def doc_view_clicked(self, row, *args):
        place_nk = CQT.num_col_by_name_c(self.modal_tbl, 'Хранилище')
        id_nk = CQT.num_col_by_name_c(self.modal_tbl, 'ID')
        rez = None
        if place_nk:
            place = self.modal_tbl.item(row, place_nk).text()
            filename = self.get_filename(self.modal_tbl, row)
            if place == 'МЕС':
                # rez = db_files_load(self.window, filename)
                # # put_file_tmp = CMS.tmp_dir() + os.sep + 'tmp_files' + os.sep + \
                # #                str(F.get_time_shtamp_c()).split('.')[-1] + "_" + \
                # #                F.transliterate(filename.replace('ь', ''))
                rez = self.storage.get_file_by_name(filename,
                                                                                                )
                if rez == False:
                    return
            if place == 'DOCS':
                file_id = self.modal_tbl.item(row, id_nk).text()
                rez = self.load_docs_file(filename)
            if rez is None:
                return CQT.msgbox('Не удалось открыть документ')
            F.run_file_os_c(rez)

    def get_file_content(self, file_id: int | str, nn: str):
        with CDOCS.TFlexFileClient() as client:
            files = client.get_filenames_by_nomen_name(nn)
            for file in files:
                if file['s_ObjectID'] == int(file_id):
                    return client.get_binary_file(
                        srv_name=file['source'],
                        object_id=file['s_ObjectID'],
                        revision=file['s_Version']
                    )

    @CQT.onerror
    def load_docs_file(self, name: str):
        nn = self.window.ui.lineEdit_dse.text()
        file_id, ext, name, filename = self.unpack_include_format(name)
        content = self.get_file_content(file_id, nn)
        if content is None:
            CQT.msgbox(f'Файл не найден')
            return
        put_tmp = CMS.tmp_dir() + os.sep + 'tmp_files'
        if F.existence_file_c(put_tmp):
            F.ochist_papky(put_tmp)
        else:
            F.create_dir_c(put_tmp)
        put_file_tmp = CMS.tmp_dir() + os.sep + 'tmp_files' + os.sep + \
                       str(F.get_time_shtamp_c()).split('.')[-1] + "_" + \
                       F.transliterate(filename.replace('ь', ''))
        F.save_binary_convert_to_file(content, put_file_tmp)
        return put_file_tmp

    @CQT.onerror
    def doc_del_clicked(self, row, *args):
        tree = self.window.ui.tree
        nk_batch = CQT.num_col_by_name_c(self.modal_tbl, 'Хранилище')
        nk_filename = CQT.num_col_by_name_c(self.modal_tbl, 'Полное имя')
        filename = self.modal_tbl.item(row, nk_filename).text()
        item = tree.currentItem()
        batch = CQT.cells(self.modal_tbl.currentRow(), nk_batch, self.modal_tbl)
        if item == None or item.text(15) == "":
            return
        if batch == 'МЕС':
            self.storage.delete_file(filename, self.window.nom_tk)
        self.drop_oper_doc(row)
        self.window.save_tk()
        self.refill_doc_tables(self.main_tbl, self.modal_tbl)
        CQT.msgbox("Файл откреплен успешно")

    def check_dxf_exists(self):
        filenames = self.oper_filenames()
        for filename in filenames:
            if not filename.startswith('docs://') and F.keep_extention_c(filename) == '.dxf':
                return filename

    def load_user_file(self, *args):
        try:
            tree = self.window.ui.tree
            item = tree.currentItem()
            if item == None: return
            ima_det = self.window.glob_tk_title.split('$')[1].replace('*', '')
            clean_name, *other = ima_det.split(' ')
            tmp_putt = CMS.load_tmp_path("tmp_addtk_doc")
            putf = CQT.f_dialog_name(self.window, 'Выбрать файл', tmp_putt,
                                     fr"Файлы (*{clean_name}*.dxf *.jpg *.pdf)")
            if putf == '' or putf == '.': return
            CMS.save_tmp_path("tmp_addtk_doc", putf, True)
            filename = Path(putf).name
            if F.keep_extention_c(filename) == '.dxf':
                if exist_dxf := self.check_dxf_exists():
                    filename_for_replace = self.check_dxf_exists()
                    if not CQT.msgboxgYN(f'Файл dxf с именем {filename_for_replace!r} уже прикреплен к операции \nПерезаписать существующий?'):
                        return
                    self.storage.delete_file(filename, self.window.nom_tk)
                    tree_item = self.window.ui.tree.currentItem()
                    exists_docs = self.oper_filenames()
                    exists_docs.remove(filename_for_replace)
                    tree_item.setText(15, DOCS_SEP.join(exists_docs))
            file_name_bd = self.storage.put_file(putf, self.window.nom_tk)
            if file_name_bd == None: return
            self.add_oper_doc(modal_tbl=self.modal_tbl, row=self.modal_tbl.currentRow(), tree_item=item,
                                          filename=filename)
            self.refill_doc_tables(main_tbl=self.main_tbl, modal_tbl=self.modal_tbl)
            CQT.msgbox("Файл прикреплен успешно")
            sp_soh = self.window.save_tk()
        except Exception as e:
            CQT.msgbox("Не удалось сохранить файл после прикрепления")
            return
        sp_tree = []
        for i in range(10, len(sp_soh)):
            sp_tree.append(sp_soh[i].split('|'))
        self.window.load_param_from_dxf(sp_tree)


    def dob_doc(self, *args):
        if self.modal_tbl.currentRow() == -1:
            return CQT.msgbox('Чтобы прикрепить документ выберите строчку')
        nk_batch = CQT.num_col_by_name_c(self.modal_tbl, 'Хранилище')
        tree = self.window.ui.tree
        item = tree.currentItem()
        batch = CQT.cells(self.modal_tbl.currentRow(), nk_batch, self.modal_tbl)
        if batch == 'DOCS':
            try:
                self.add_oper_doc(modal_tbl=self.modal_tbl, row=self.modal_tbl.currentRow(), tree_item=item)
                self.refill_doc_tables(main_tbl=self.main_tbl, modal_tbl=self.modal_tbl)
                sp_soh = self.window.save_tk()
            except Exception as e:
                CQT.msgbox("Не удалось сохранить файл после прикрепления")
                return
            sp_tree = []
            for i in range(10, len(sp_soh)):
                sp_tree.append(sp_soh[i].split('|'))
            self.window.load_param_from_dxf(sp_tree)

    def get_oper_docs(self, *args, include_tflex_data = False):
        tree = self.window.ui.tree
        item = tree.currentItem()
        if item == None: return
        data = [[ '📌', 'ID', 'Хранилище', 'Имя', 'Формат', 'Полное имя', '👁', '❌']]
        filenames = self.oper_filenames()
        attached_ids = set()
        for filename in filenames:
            batch = 'МЕС'
            if filename.startswith('docs://'):
                batch = 'DOCS'
            else:
                rez = self.storage.get_file_by_name(filename)
                if rez == False:
                    continue
            file_id, ext, name, filename = self.unpack_include_format(filename)
            if file_id: attached_ids.add(int(file_id))
            data.append(['', file_id, batch, name, ext, filename])
        self.add_btn_state = include_tflex_data
        if include_tflex_data:
            is_access_user = CMS.user_access(
                self.window.db_naryad,
                'тк_просмотр_добавление_документов_докс',
                F.user_name(),
                msg=False
            ) #17.11.25
            nn = self.window.ui.lineEdit_dse.text()
            with CDOCS.TFlexFileClient() as client:
                docs_filenames = client.get_filenames_by_nomen_name(nn)
                if not docs_filenames:
                    self.add_btn_state = False
                else:
                    for item in docs_filenames:
                        fullname = item.get('name', '')
                        n, e = os.path.splitext(fullname)
                        if not is_access_user and e != '.dxf':
                            continue
                        file_id = item.get('s_ObjectID')
                        if file_id not in attached_ids:
                            filename = item.get('name')
                            *name_parts, format = filename.split('.')
                            name = '.'.join(name_parts)
                            data.append(['', file_id, 'DOCS', name, format, filename])
        return data

    def refill_doc_tables(self, main_tbl = None, modal_tbl = None):
        if main_tbl:
            main_tbl.show()
            self.fill_docs_table()
        if modal_tbl:
            CQT.fill_wtabl(self.get_oper_docs(include_tflex_data=True), modal_tbl, height_row=25, set_editeble_col_nomera={})
            self.oform_tbl(modal_tbl)

    def fill_docs_table(self, *args):
        row_height = 22
        space = 10
        data = self.get_oper_docs()
        if isinstance(data, list) and len(data) > 1:
            self.main_tbl.show()
            CQT.fill_wtabl(data, self.main_tbl, height_row=row_height)
            self.main_tbl.setMaximumHeight(len(data) * row_height + space)
            for col in range(self.main_tbl.columnCount()):
                self.main_tbl.setColumnHidden(col, len(self.main_tbl.horizontalHeaderItem(col).text()) == 1)
        else:
            self.main_tbl.hide()

    def get_filename(self, tbl: QtWidgets.QTableWidget, row: int):
        id_nk = CQT.num_col_by_name_c(tbl, 'ID')
        batch_nk = CQT.num_col_by_name_c(tbl, 'Хранилище')
        full_name_nk = CQT.num_col_by_name_c(tbl, 'Полное имя')
        batch = tbl.item(row, batch_nk).text()
        full_name = tbl.item(row, full_name_nk).text()
        file_id = tbl.item(row, id_nk).text()
        match batch:
            case 'МЕС':
                return full_name
            case 'DOCS':
                return DOCS_NAME_FORMAT.format(file_id=file_id, full_name=full_name)

    def oper_filenames(self) -> list | None:
        item: QtWidgets.QTreeWidgetItem = self.window.ui.tree.currentItem()
        if item is None: return
        text = item.text(15) or ''
        if text == '': return []
        return text.split(DOCS_SEP)

    def is_attached(self, tbl: QtWidgets.QTableWidget, row: int):
        return self.get_filename(tbl, row) in self.oper_filenames()

    def unpack_include_format(self, filename):
        file_id = ''
        if match := re.search(DOCS_PATTERN, filename):
            file_id = match.group(1)
            filename = match.group(2)
        name, ext = filename.rsplit('.', 1)
        return file_id, ext, name, filename

    @CQT.onerror
    def add_oper_doc(self, modal_tbl: QtWidgets.QTableWidget, row: int, tree_item: QtWidgets.QTreeWidgetItem,
                     filename: str = ''):
        exists_docs = self.oper_filenames()
        if not filename:
            filename = self.get_filename(modal_tbl, row)
        if filename in exists_docs: return
        exists_docs.append(filename)
        tree_item.setText(15, DOCS_SEP.join(exists_docs))
        file_id, ext, name, filename = self.unpack_include_format(filename)

        CQT.msgbox(f'Документ {filename!r} успешно прикреплен')

    @CQT.onerror
    def drop_oper_doc(self, row: int):
        tree_item = self.window.ui.tree.currentItem()
        exists_docs = self.oper_filenames()
        filename = self.get_filename(self.modal_tbl, row)
        if filename in exists_docs:
            exists_docs.remove(filename)
            tree_item.setText(15, DOCS_SEP.join(exists_docs))
            file_id, ext, name, filename = self.unpack_include_format(filename)

            CQT.msgbox(f'Документ {filename!r} успешно откреплен')


@CQT.onerror
def db_files_nalich(self, put_file,nom_tk):
    def update_data(size, hesh, bin_file, date, usr, pnom):
        CSQ.custom_request_c(self.db_files, f"""UPDATE reestr SET (size, hesh, file, Date_edit, usr)
                         = (?,?,?,?,?) WHERE Пномер == {pnom};""",
                   list_of_lists_c=[[size, hesh, bin_file, date, usr]])
        return
    def add_data(size, hesh, bin_file, date, usr):
        CSQ.custom_request_c(self.db_files, """INSERT INTO reestr(size, hesh, file, Date_edit, usr)
                         VALUES (?,?,?,?,?);""",
                   list_of_lists_c=[[size, hesh, bin_file, date, usr]])
        query = CSQ.custom_request_c(self.db_files, f"""SELECT * FROM reestr WHERE size == '{size}' and hesh == '{hesh}'""",rez_dict=True)
        if query == []:
            return
        return query[0]['Пномер']
    def add_name(nom_data, name, date_edit, usr):
        CSQ.custom_request_c(self.db_files, """INSERT INTO names(nom_data, name, date_edit, usr)
                                 VALUES (?,?,?,?);""",
                   list_of_lists_c=[[nom_data, name, date_edit, usr]])

    def add_tkart(file_name,t_kard_name):
        query = CSQ.custom_request_c(self.db_files,f"""SELECT file_name,t_kard_name FROM t_kards WHERE file_name == '{file_name}' AND t_kard_name == '{t_kard_name}' """)
        if len(query)==1:
            CSQ.custom_request_c(self.db_files, """INSERT INTO t_kards(file_name,t_kard_name)
                                         VALUES (?,?);""",
                   list_of_lists_c=[[file_name,t_kard_name]])

    file = put_file.split(os.sep)[-1]

    size = os.path.getsize(put_file)
    bin_file = F.load_file_convert_to_binary(put_file)
    hesh = hashlib.sha1(bin_file).hexdigest()
    name = file

    """если есть файл
            если имя совпадает
                Ничего не далать предупредить
                    выход
            если имя не совпадает
                предупреждение добавлять файл и связанные карты
                    да запрос
                    нет выход
        если нет файла
            если имя существует
                 заменить файл и связанные карты
                    да запрос
                    нет выход
            если  имя не существует
                Ничего не далать занести
                    выход
                    """

    custom_request_c = f"""SELECT * FROM reestr WHERE size == {size} and hesh == '{hesh}'"""
    query = CSQ.custom_request_c(self.db_files, custom_request_c, rez_dict=True)
    if query == []: # если нет файла
        custom_request_c2 = f"""SELECT * FROM names WHERE name == '{name}'"""
        query2 = CSQ.custom_request_c(self.db_files, custom_request_c2, rez_dict=True)
        if query2 == []:#если имя не существует
            nom = add_data(size, hesh, bin_file, F.now("%Y-%m-%d %H-%M"), F.user_name())
            if nom == None:
                CQT.msgbox(f'Ошибка загрузки')
                return
            add_name(nom, name, F.now("%Y-%m-%d %H-%M"), F.user_name())
            add_tkart(name, nom_tk)

        else:#если имя существует
            nom = query2[0]['Пномер']
            custom_request_c3 = f"""SELECT t_kard_name, Пномер FROM t_kards WHERE file_name == '{name}'"""
            query3 = CSQ.custom_request_c(self.db_files, custom_request_c3, rez_dict=True)
            list_cards = [_['t_kard_name'] for _ in query3]
            if not CQT.msgboxgYN(f'файл с именем {name} уже существует, но с содержимое файла отличается от предложенного.\n'
                             f'Нужно убедиться что новый файл правильный и актуальный\n\n'
                             f'Обновить файл? Изменение затронет резку связанных техкарт:\n({str(list_cards)})'):
                return
            # занести
            update_data(size, hesh, bin_file, F.now("%Y-%m-%d %H-%M"), F.user_name(),nom)
            add_tkart(name, nom_tk)


    else:#если есть файл
        nom_data = query[0]['Пномер']
        custom_request_c2 = f"""SELECT * FROM names WHERE nom_data == {nom_data}"""
        query2 = CSQ.custom_request_c(self.db_files, custom_request_c2, rez_dict=True)
        if query2 == []:#если имя отсутсвует
            add_name(nom_data, name, F.now("%Y-%m-%d %H-%M"), F.user_name())
            add_tkart(name, nom_tk)
        else:
            names_from_db = [_['name'] for _ in query2]
            if not name in names_from_db:#если имя не совпадает
                list_other_names = CSQ.custom_request_c(self.db_files,f"""SELECT names.name, t_kards.t_kard_name FROM names INNER JOIN 
                t_kards ON  t_kards.file_name = names.name WHERE names.nom_data == {nom_data}""")
                if not CQT.msgboxgYN(f'Файл уже существует с другим наименованием :\n{pprint.pformat(list_other_names)}.'
                                 f' \n\n Вероятно это ошибка!\n\n Следует ли '
                                 f'вносить этому файлу дополнительное имя в БД?',icon = QtWidgets.QMessageBox.Warning):
                    return
                # занести
                add_name(nom_data, name, F.now("%Y-%m-%d %H-%M"), F.user_name())
                add_tkart(name, nom_tk)
                pass
            else:#если имя совпадает
                add_tkart(name, nom_tk)
    return file


@CQT.onerror
def db_files_load(self, name, available_ext = None):
    custom_request_c = f"""
        SELECT 
            reestr.file, 
            storage_types.name as storage,
            reestr.hesh
        FROM reestr 
        INNER JOIN names on names.nom_data = reestr.Пномер 
        LEFT JOIN storage_types ON storage_types.id = reestr.storage
        WHERE names.name == '{name}'"""
    query = CSQ.custom_request_c(CFG.Config.project.db_files, custom_request_c,rez_dict=True, one=True)
    if not isinstance(query, dict):
        return False
    #return query[1][nk_name]
    put_tmp = CMS.tmp_dir() + os.sep + 'tmp_files'
    if F.existence_file_c(put_tmp):
        F.ochist_papky(put_tmp)
    else:
        F.create_dir_c(put_tmp)

    put_file_tmp = CMS.tmp_dir() + os.sep + 'tmp_files' + os.sep + \
                   str(F.get_time_shtamp_c()).split('.')[-1] + "_" +\
                   F.transliterate(name.replace('ь', ''))

    if query['storage'] == 'database':
        F.save_binary_convert_to_file(query['file'],put_file_tmp)
        return put_file_tmp

    if query['storage'] == 'filesystem':
        storage = CSTORE.FileStorage(CFG.Config.project.tk_storage_reestr)
        return storage.retrieve_by_path(query['hesh'], put_file_tmp)


@CQT.onerror
def db_files_del(self,name,nom_tk = None):
    list_uses_tk = CSQ.custom_request_c(self.db_files,f"""SELECT * FROM t_kards WHERE file_name == '{name}'""",rez_dict=True)
    if len(list_uses_tk) == 1 or len(list_uses_tk) == 0:
        list_uses_names = CSQ.custom_request_c(self.db_files, f"""SELECT * FROM names WHERE name == '{name}'""", rez_dict=True)
        if len(list_uses_names) == 1:
            nom_data = list_uses_names[0]['nom_data']
            datas = CSQ.custom_request_c(self.db_files, f"""SELECT * FROM names WHERE nom_data == '{nom_data}'""", rez_dict=True)
            if len(datas)==1:
                CSQ.custom_request_c(self.db_files, f"""DELETE FROM reestr WHERE Пномер == {nom_data}""")
        CSQ.custom_request_c(self.db_files, f"""DELETE FROM names WHERE name == '{name}'""")
    CSQ.custom_request_c(self.db_files,f"""DELETE FROM t_kards WHERE file_name == '{name}'""")
    return
