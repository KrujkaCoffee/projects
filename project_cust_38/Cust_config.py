import sys
import typing
import logging
import copy
import os
import dataclasses
from PyQt5 import QtWidgets
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
from project_cust_38 import Cust_Qt as CQT


class SingletonMeta(type):
    __instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances:
            instance = super().__call__(*args, **kwargs)
            cls.__instances[cls] = instance
        return cls.__instances[cls]


class Desc:
    def __init__(self, *, is_dynamic: bool=False, sep: str = '|', default = None) -> None:
        self.is_dynamic = is_dynamic
        self.default = default
        self.sep = sep

    def __set_name__(self, owner, name) -> None:
        self.name = name

    def __get__(self, instance, owner):
        expected_item = instance.__dict__.get(self.name)
        if self.is_dynamic or not expected_item:
            if instance.horizontal:
                instance._get_horizontal(self.name)
            else:
                instance._get_vertical(self.name)
            expected_item = instance.__dict__.get(self.name)
        return self.get_clean(instance, expected_item)

    def __set__(self, instance, value):
        attr_type = instance.hints.get(self.name)
        if hasattr(instance, f'clean_{self.name}'):
            return self.__dict__.update({self.name: getattr(instance, f'clean_{self.name}')(value)})
        if attr_type is None or attr_type is False:
            instance.__dict__[self.name] = self.default
        elif isinstance(value, str) and (attr_type is list or attr_type is set or attr_type is tuple):
            instance.__dict__[self.name] = attr_type(value.split(self.sep))
        elif attr_type is bool:
            instance.__dict__[self.name] = bool(int(value))
        elif value is None:
            instance.__dict__[self.name] = self.default
        else:
            instance.__dict__[self.name] = attr_type(value)

    def get_clean(self, instance, value):
        if hasattr(instance, f'clean_{self.name}'):
            return getattr(instance, f'clean_{self.name}')(value)
        return value


class BaseConfig(metaclass=SingletonMeta):
    _CONFIG_DB = F.scfg('BD_users')
    if _CONFIG_DB == '':
        print(f'BD_users not defined')
        raise Exception()
    __table__ = 'app_config'
    _key_col = 'name'
    _val_col = 'value'
    _description_col = None

    horizontal = False

    def __init__(self, **kwargs):
        self.is_disabled = False
        for key, val in kwargs.items():
            self._key_col = key
            self._val_col = val
        self.hints = typing.get_type_hints(self.__class__)
        if self.horizontal:
            self._get_horizontal()
        else:
            self._get_vertical()

    def _get_horizontal(self, name = None):
        select = name if name else '*'
        where = f' WHERE {self._key_col} = ("{self._val_col}")'
        count_articles = CSQ.custom_request_c(
            self._CONFIG_DB,
            f'SELECT COUNT(*) as cnt FROM {self.__table__} {where}',
            rez_dict=True, one=True
        )
        if not isinstance(count_articles, dict) or count_articles['cnt'] == 0:
            self.is_disabled = True
            return
        result = CSQ.custom_request_c(
            self._CONFIG_DB,
            f'SELECT {select} FROM {self.__table__} {where}',
            rez_dict=True,
            one=True
        )
        if result == False or not isinstance(result, dict):
            postfix = f'.{name}' if name else ''
            logging.error(f'Не удалось инициализировать конфигурацию {self.__class__.__name__}{postfix}')
            self.is_disabled = True
            return
        for key, value in result.items():
            setattr(self, key, value)

    def _get_vertical(self, name = None):
        where = f'WHERE {self._key_col} = ("{name}")' if name else ''
        query = f'SELECT * FROM {self.__table__} {where}'
        result = CSQ.custom_request_c(
            self._CONFIG_DB,
            query,
            rez_dict=True
        )
        if result == False or not isinstance(result, list):
            logging.error(f'Не удалось инициализировать конфигурации в {self.__class__.__name__}')
            self.is_disabled = True
            return
        for item in result:
            name = item.get(self._key_col)
            if name is None:
                logging.warning(f'Не найдена конфигурация {self.__class__.__name__}.{self._key_col}')
                break
            value = item.get(self._val_col)
            self.__dict__[f'info_{name}'] = item.get(self._description_col)
            setattr(self, name, value)

    def _set(self, query, **kwargs):
        if CSQ.custom_request_c(self._CONFIG_DB, query):
            fields = ', '.join(f'{key} {value}' for key, value in kwargs.items())
            logging.info(f'В "{self.__class__.__name__}" успешно обновил конфигурации "{fields}"')
            self.__dict__.update(kwargs)

    def __getitem__(self, key):
        return self.__dict__.get(key)

T = typing.TypeVar('T')


class VerticalConfig(BaseConfig, typing.Generic[T]):
    _key_col = 'name'
    _val_col = 'value'
    _description_col = 'comment'

    def set(self, key, new_value):
        query = f"""UPDATE {self.__table__} SET {self._val_col} = ("{new_value}") WHERE {self._key_col} = '{key}'"""
        return self._set(query, **{key: new_value})

    @property
    def info(self) -> T:
        return self.Meta(self)

    class Meta:
        def __init__(self, obj):
            self.object = obj

        def __getattr__(self, item):
            obj = self.__dict__.get('object')
            if obj:
                return obj.__dict__.get(f'info_{item}')


class HorizontalConfig(BaseConfig):
    horizontal = True
    def __init__(self):
        super().__init__(module=F.name_of_executable_file_c())

    def set(self, **kwargs):
        set_sql = ', '.join(f'{key} = ("{value}")' for key, value in kwargs.items())
        query = f"""UPDATE {self.__table__} SET {set_sql} WHERE {self._key_col} = '{self._val_col}'"""
        return self._set(query, **kwargs)


class ProjectConfig(VerticalConfig['ProjectConfig']):
    """
    config = ProjectConfig()
    config.info.check_vnesenie_trudozatrat # Вывод: В создании проверка на выгрузку турдоазтрат перед распределением

    для внесения своего валидатора можно назначить на метод "clean_ИмяАтрибута" (например def clean_developers(self, text):
    который принимает значение из БД и возвращает измененную версию
    """
    __table__ = 'config'

    developers: str = Desc()
    check_vnesenie_trudozatrat: bool = Desc(is_dynamic=True)
    db_naryad: str = Desc()
    db_files: str = Desc()
    db_kplan: str = Desc()
    db_users: str = Desc()
    db_resxml: str = Desc()
    db_dse: str = Desc()
    db_flet: str = Desc()
    ERB_BASE_URL: str = Desc()


class AppConfig(HorizontalConfig):
    __table__ = 'app_config'
    version: str = Desc(is_dynamic=True)
    last_update: str = Desc(is_dynamic=True, default='')
    params: list = Desc(sep='|')
    path: str = Desc()


def tmp_dir():
    ima_module = F.name_of_executable_file_c().split('.')[0]
    if F.existence_file_c(os.sep.join([F.put_po_umolch() ,'mes_tmp'])) == False:
        F.create_dir_c(os.sep.join([F.put_po_umolch() ,'mes_tmp']))
    if F.existence_file_c(os.sep.join([F.put_po_umolch() ,'mes_tmp' , ima_module])) == False:
        F.create_dir_c(os.sep.join([F.put_po_umolch() ,'mes_tmp' , ima_module]))
    return os.sep.join([F.put_po_umolch() ,'mes_tmp' , ima_module])

def save_tmp_stukt(data,name):
    puth_name = tmp_dir() + os.sep + name + '.pickle'
    F.save_file_pickle(puth_name,data)

def load_tmp_stukt(ima,default_val = None):
    puth_name = tmp_dir() + os.sep + ima + '.pickle'
    if F.existence_file_c(puth_name) == True:
        val = F.load_file_pickle(puth_name)
        return val
    return default_val


class User_config(metaclass=SingletonMeta):
    def __init__(self, common_config: ProjectConfig = None):
        self.common_config = common_config #18.07.25
        orgnizations = CSQ.custom_request_c(ProjectConfig().db_naryad, f"""SELECT Имя FROM places""",
                                            hat_c=False, one_column=True)
        orgnizations.insert(0, '')
        path_files = F.sep().join([F.path_to_execut_file_c(), 'css'])

        erp_bases = CSQ.custom_request_c(ProjectConfig().db_users , f"""SELECT name FROM bases_ERP""",
                                            hat_c=False, one_column=True)

        list_thems = []
        if os.path.exists(path_files):
            list_thems = [_.split('.')[0] for _ in F.list_of_files_c(path_files)[0][2] if _.split('.')[-1] == 'qss']

        data_config_sample = {
            'reset_tbl_filtrs': {'Параметр': 'Сброс фильтров',
                                 'Значение': '',
                                 'Примечание': 'при каждой генерации таблицы, фильтры буду сборшены',
                                 'Default_val': '0',
                                 'type': 'check_box',
                                 'list': None,
                                 'necessary_reload': False,
                                 },
            'ERP_base_name': {
                'Параметр': 'Имя базы ЕРП',
                'Значение': '',
                'Примечание': 'Имя, с которой взаимодействует приложение',
                'Default_val': 'ERP',
                'type': 'combo_box',
                'list': erp_bases,
                'necessary_reload': True,
            },
            'Organization': {
                'Параметр': 'Организация',
                'Значение': '',
                'Примечание': '',
                'Default_val': '',
                'type': 'combo_box',
                'list': orgnizations,
                'necessary_reload': True,
            },
            'css_theme': {
                'Параметр': 'Тема',
                'Значение': '',
                'Примечание': 'Оформление',
                'Default_val': 'default',
                'type': 'combo_box',
                'list': list_thems,
                'necessary_reload': False,
            }
        }
        self.__data_config_sample = data_config_sample
        self.reset_tbl_filtrs = None
        self.ERP_base_name = None
        self.css_theme = None
        self.Organization = None
        self.load_config()

    @property
    def is_developer(self): #18.07.25
        current_login = F.user_name()
        return current_login in self.common_config.developers.split('|')

    def load_config(self):
        data = load_tmp_stukt('user_config', {})
        data_config = copy.deepcopy(self.__data_config_sample)
        for param, dic in data_config.items():
            if param in data:
                dic['Значение'] = data[param]['Значение']
            if dic['Значение'] == '':
                if dic['Default_val']=='':
                    if isinstance(dic['list'],list):
                        dic['Значение'] = dic['list'][0]
                else:
                    dic['Значение'] = dic['Default_val']
            dic['list'] = str(dic['list'])
            exec(f'self.{param} = {dic}')
        self._data_config = data_config

    def save_config(self, new_tbl: dict):
        data_config = copy.deepcopy(self.__data_config_sample)
        for param, dic in data_config.items():
            if param in new_tbl:
                dic['Значение'] = new_tbl[param]['Значение']
        save_tmp_stukt(data_config, 'user_config')
        self.load_config()

    def tbl_config(self):
        tbl = F.dict_of_dicts_to_list_of_lists(self._data_config, 'Nick_name')
        tbl = F.list_of_lists_to_list_of_dicts(tbl)
        return tbl

    def load_user_config(self, window):
        self.load_config()
        
        window.USER_CONFIG = self
        window.ERP_base_name = f'{self.ERP_base_name["Значение"]}'
        erp_tool_tip = f'База 1С: {self.ERP_base_name["Значение"]}'
        window.name_module = f'Приложение "{window.NAME_MODULE_BASE}": {f" {F.user_full_namre()}({F.curr_user_c()})"}({self.Organization["Значение"]})-{erp_tool_tip}'
        CQT.load_css(window)
        self.set_tooltip(window)
        window.place = Config.place

    def set_tooltip(self, window):
        window.setWindowTitle(f"{window.name_module}")

    def select_organiztion(self, self_ui):
        self.gui_load(self_ui)

    def gui_load(self, window, *args):
        data_config = self.tbl_config()

        def oforml(tbl: QtWidgets.QTableWidget):
            def set_val_int(val, i, j):
                tbl.item(i, j).setText(str(F.valm(val)))

            def set_val_str(val, i, j):
                tbl.item(i, j).setText(val)

            nf_val = CQT.num_col_by_name_c(tbl, 'Значение')
            nf_type = CQT.num_col_by_name_c(tbl, 'type')
            nf_list = CQT.num_col_by_name_c(tbl, 'list')
            for i in range(tbl.rowCount()):
                if tbl.item(i, nf_list).text() == None:
                    continue
                CQT.set_cell_editable(tbl, i, nf_val, True)
                if tbl.item(i, nf_type).text() == 'check_box':
                    val = F.boolm(tbl.item(i, nf_val).text())
                    CQT.add_check_box(tbl, i, nf_val, val=val, conn_func_checked_row_col=set_val_int)
                if tbl.item(i, nf_type).text() == 'combo_box':
                    val = tbl.item(i, nf_val).text()
                    CQT.add_combobox('', tbl, i, nf_val, list=eval(tbl.item(i, nf_list).text()), first_void=False,
                                     conn_func=set_val_str)
                    tbl.cellWidget(i, nf_val).setCurrentText(val)
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'Nick_name'), True)
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'Default_val'), True)
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'type'), True)
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'list'), True)
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'necessary_reload'), True)
            tbl.setColumnWidth(nf_val, 90)

        def apply_new_vals(tbl):
            data = F.deploy_dict_c(CQT.list_from_wtabl_c(tbl, rez_dict=True), 'Nick_name')
            User_config().save_config(data)

        old_config = copy.deepcopy(data_config)
        NAME_MODULE_BASE = ''
        if 'NAME_MODULE_BASE' in window.__dict__:
            NAME_MODULE_BASE = window.NAME_MODULE_BASE
        rez = CQT.msgboxg_get_table(window, 'Настройки', data_config, 'Принять',
                                    WindowTitle=NAME_MODULE_BASE + ' Пользовательские настройки',
                                    style_icon='SP_MessageBoxQuestion', func_oform_tbl=oforml,
                                    func_btn0=apply_new_vals)

        if not rez == False:
            data_config = self.tbl_config()
            fl_reload = False
            for elem in data_config:
                for elem_old in old_config:
                    if elem['Nick_name'] == elem_old['Nick_name']:
                        if elem['Значение'] != elem_old['Значение'] and elem['necessary_reload']:
                            fl_reload = True
                            break
                if fl_reload:
                    break
            if fl_reload:
                CQT.msgbox(f'Перезапустить приложение')
                quit()
            self.load_user_config(window)

class CodeNaryad:
    Плановая: int = None
    НеподтвержденныйВнеплан: int = None
    ПодтвержденныйВнеплан: int = None
    Простой: int = None

    def __init__(self, poki, bd: str):
        code_naryads = CSQ.custom_request_c(
            bd,
            f'SELECT name, code FROM коды_веплана_для_наряда WHERE poki = {poki}',
            hat_c=False
        )
        if isinstance(code_naryads, list):
            for k, v in code_naryads:
                setattr(self, k, v)
        else:
            logging.info('[Cust_config.CodeNaryad] Не удалось инициализировать коды нарядов из-за недоступности БД')


class Evaluation_department_podrazdel_for_reports:
    Имя: str = None

    def __init__(self, eval_podr, bd_kplan: str):
        data = CSQ.custom_request_c(
            bd_kplan,
            f'SELECT Имя FROM podrazdel WHERE Пномер = {eval_podr}', one_column=True,one=True,
            hat_c=False
        )
        if isinstance(data, list):
            self.Имя = data[0]
        else:
            logging.info('[Cust_config.Evaluation_department_podrazdel_for_reports] Не удалось инициализировать имя оценочного подразделения из-за недоступности БД')

@dataclasses.dataclass
class Place(metaclass=SingletonMeta):
    Код: str = None
    Имя: str = None
    Примечание: str = None
    Организация_Key: str = None
    poki: int = None
    letter: str = None
    doc_prefix: str = None
    ИспПроверкуВнесенияТрудозатрат: int = None
    ИспПроверкуТехартыВнесениеВидаИВесаТО: int = None
    РодительВидаРабот: str = None
    ИспользоватьФильтрМКПоплану: int = None
    prefix_projects_localnet_path: str = None
    projects_localnet_path: str = None
    УИД_ЕРП_Отдел_снабжения: str = None
    evaluation_department: Evaluation_department_podrazdel_for_reports = None
    КодыНарядов: CodeNaryad = None

    def __init__(self, organization_name: str | None = None) -> None:
        if not organization_name:
            if AppConfig().is_disabled:
                return
            user_config = User_config()
            if not isinstance(user_config.Organization, dict) or not user_config.Organization.get('Значение'):
                if QtWidgets.QApplication.instance() is None:
                    app = QtWidgets.QApplication(sys.argv)
                widget = QtWidgets.QMainWindow()
                CQT.msgbox('Не выбрана организация')
                user_config.gui_load(widget)
                return
            organization_name = user_config.Organization.get('Значение')
        # db_naryad = F.scfg('Naryad')
        db_naryad = ProjectConfig().db_naryad
        row = CSQ.custom_request_c(db_naryad, f"""SELECT * FROM places WHERE Имя = "{organization_name}";""", one=True,
                                   rez_dict=True)
        self.КодыНарядов = CodeNaryad(row['poki'], db_naryad)
        self.evaluation_department = Evaluation_department_podrazdel_for_reports(row['evaluation_department_podrazdel_for_reports'],ProjectConfig().db_kplan)

        for key in row.keys():
            exec(f'self.{str(key).replace(".", "_")} = row[key]')


class Config(metaclass=SingletonMeta):
    project: ProjectConfig = ProjectConfig()
    app: AppConfig = AppConfig()
    user_config: User_config = User_config(common_config=project) #18.07.25
    place: Place = Place()
