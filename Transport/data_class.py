from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import project_cust_38.Cust_config as MESCNF
import os
import Config.srv_config as SRVCFG
import flet as ft
import project_cust_38.Cust_SQLite as CSQ
import components.common_funcs as CMF
from typing import Any
import project_cust_38.Cust_Functions as F
from middleware import current_win_user

"""
Роль	Описание / Назначение
PRIMARY	Основной фирменный цвет приложения (акценты, кнопки, индикаторы)
ON_PRIMARY	Цвет элементов/текста поверх primary
PRIMARY_CONTAINER	Контейнер с оттенком primary (фон для кнопок, карточек)
ON_PRIMARY_CONTAINER	Цвет текста/элементов поверх primary_container
SECONDARY	Вторичный акцент (менее заметный, чем primary)
ON_SECONDARY	Цвет текста/элементов на фоне secondary
SECONDARY_CONTAINER	Контейнер с оттенком secondary
ON_SECONDARY_CONTAINER	Цвет текста/элементов на фоне secondary_container
TERTIARY	Третичный акцент (доп. визуальная палитра)
ON_TERTIARY	Цвет элементов/текста поверх tertiary
TERTIARY_CONTAINER	Контейнер с оттенком tertiary
ON_TERTIARY_CONTAINER	Цвет текста/элементов поверх tertiary_container
ERROR	Цвет ошибок (сообщения, индикаторы)
ON_ERROR	Цвет текста/элементов на фоне error
ERROR_CONTAINER	Контейнер для ошибок (мягкий фон ошибки)
ON_ERROR_CONTAINER	Контрастный цвет поверх error_container
BACKGROUND	Базовый цвет фона всего приложения
ON_BACKGROUND	Цвет текста и элементов на фоне background
SURFACE	Поверхности (карточки, диалоги, панели)
ON_SURFACE	Цвет текста/элементов на фоне surface
SURFACE_VARIANT	Вариация поверхности для отделения блоков
ON_SURFACE_VARIANT	Цвет текста/элементов на фоне surface_variant
OUTLINE	Цвет контуров и разделителей
OUTLINE_VARIANT	Более мягкий цвет разделителей
SHADOW	Тени (elevation)
SCRIM	Цвет для затемнения заднего фона (например, за модалкой)
INVERSE_SURFACE	Инверсный цвет поверхности (исп. в статус-баре, тулбаре)
INVERSE_ON_SURFACE	Цвет текста/элементов на inverse_surface
INVERSE_PRIMARY	Инверсный primary для выделений в обратной палитре
SURFACE_TINT	Оттенок поверхности для имитации elevation
"""

class SingletonMeta(type):
    __instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances:
            instance = super().__call__(*args, **kwargs)
            cls.__instances[cls] = instance
        return cls.__instances[cls]


@dataclass()
class _Data_vars(metaclass=SingletonMeta):
    print(f'==== INIT _Data_vars =======')
    db_kplan: str = MESCNF.Config.project.db_kplan
    width:int = 1900
    height:int = 800
    DOWNLOAD_TEMP_FILE = 20011

class Bio_client():
    def __init__(self,s_num:int|None , fio:str|None , position:str|None, department:str|None ):
        print(f'==== INIT Bio_client {fio} =======',end='\n\n')
        self.s_num:int =s_num
        self.fio:str =fio
        self.position:str =position
        self.department:str  =department


class Client_config():
    def __init__(self,        db_flet:str,         ip:str,        hostname:str,    theme_mode_dark:bool|int,    color_scheme_seed:str    ):
        print(f'==== INIT Client_config {ip} =======')
        self.ip:str = ip
        self.hostname:str = hostname
        self.theme_mode_dark:bool = bool(theme_mode_dark)
        self.color_scheme_seed:str = color_scheme_seed
        self.db_flet:str = db_flet
        self.db_users = MESCNF.Config.project.db_users
        self.login = current_win_user.get() or None
        if self.login:
            print('Поиск пользователя по WINDOWS AUTH LOGIN')
            data_bio_client = CSQ.custom_request_c(
                self.db_users,
                f"""
                    SELECT e.Пномер, e.ФИО, e.Должность, e.Подразделение 
                    FROM employee AS e
                        INNER JOIN ФизическиеЛица ON ФизическиеЛица.ФизическоеЛицо_Key = e.ID_ФизЛица
                    WHERE SUBSTR(ФизическиеЛица.login, 3) = "{self.login}" ORDER BY Пномер DESC LIMIT 1
                """, rez_dict=True, one=True)
        else:
            print('Поиск пользователя по HOSTNAME')
            data_bio_client = CSQ.custom_request_c(self.db_users,
                           f"""SELECT Пномер, ФИО,Должность,Подразделение FROM employee 
                            WHERE computer_name == '{self.hostname}';""",rez_dict=True, one=True)
        print(f'data_bio_client = {data_bio_client} for self.hostname ={self.hostname}')
        if not data_bio_client:
            print(f'data_bio_client = None')
            data_bio_client = {'Пномер':None,'ФИО':None,'Должность':None,'Подразделение':None}
        self.bio = Bio_client(data_bio_client['Пномер'],
                              data_bio_client['ФИО'],
                              data_bio_client['Должность'],
                              data_bio_client['Подразделение'])

    def _update_user_param(self,name_param:str,val:int|float|str):
        if isinstance(val, str):
            val = "'" + val + "'"
        where = f'ip = "{self.ip}"'
        if self.login:
            where = f'login = "{self.login}"'
        CSQ.custom_request_c(self.db_flet,f"""UPDATE user_config SET {name_param} = {val} WHERE {where};""")

    def update_user_theme_mode(self,dark=False):
        self._update_user_param('theme_mode_dark', int(dark))

    def update_user_theme_color(self,color_scheme_seed):
        self._update_user_param('color_scheme_seed', color_scheme_seed)

class Client_data():
    def __init__(self,page:ft.Page):
        self.ip = None
        self.login = current_win_user.get()
        self.platform = None
        self.window_size = (None, None)
        self.user_agent = None
        self.route = None
        self.db_flet = MESCNF.Config.project.db_flet
        self.user_config: Client_config | None = None

        if page:
            print(f'==== INIT Client_data {page.client_ip} =======')
            ip4 = str(page.client_ip).split(':')[0]
            if len(ip4) < 1:
                ip4 = str(page.client_ip)
            self.ip = ip4
            self.platform =  page.platform
            self.window_size =  (page.width,   page.height)
            self.user_agent =  page.client_user_agent or "неопределен"
            self.route =  page.route
            self.db_flet = MESCNF.Config.project.db_flet
            self.user_config:Client_config|None = None

    def _load_user_config_data(self):
        where = f'ip = "{self.ip}"'
        if self.login:
            where = f'login = "{self.login}"'
        return CSQ.custom_request_c(self.db_flet, f"""SELECT * FROM user_config WHERE {where};""",
                                    rez_dict=True)

    def get_user_config(self):
        conf =  self._load_user_config_data()
        if not self.ip and not self.login:
            print('NOT FINED IP AND LOGIN')
            return
        if not conf:
            if not self.add_new_user():
                print(f'Ошибка добавления нового юзера для {self.ip}')
                return
            conf =  self._load_user_config_data()
            print(f'====== {F.now()} REG_NEW_CLIENT=======')
            print(self.db_flet)
            print(conf)
            print()

        print(f'====== {F.now()} LOAD_CLIENT=======')
        self.user_config = Client_config(self.db_flet,
                                        conf[0]['ip'],
                                       conf[0]['hostname'],
                                       conf[0]['theme_mode_dark'],
                                       conf[0]['color_scheme_seed'])

    def apply_theme_mode(self,page):
        if self.user_config.theme_mode_dark:
            page.theme_mode = ft.ThemeMode.DARK
        else:
            page.theme_mode = ft.ThemeMode.LIGHT

    def apply_theme(self,page):
        page.theme = page.dark_theme = ft.Theme(color_scheme_seed=self.user_config.color_scheme_seed)

    def update_theme_color(self,color_scheme_seed:str):
         self.user_config.update_user_theme_color(color_scheme_seed)

    def update_theme_mode(self,ThemeMode:ft.ThemeMode):
        self.user_config.update_user_theme_mode(ThemeMode == ft.ThemeMode.DARK)

    def add_new_user(self):
        hostname = None
        try:
            hostname = self.get_hostname().split('.')[0]
        except Exception as e:
            print(e)
        # if hostname == '192':
        #     return False
        add_row = [self.ip, hostname, self.login]
        rez = CSQ.custom_request_c(self.db_flet,"""INSERT INTO user_config (ip,hostname,login) VALUES (?,?, ?);""",list_of_lists_c=[add_row])
        return rez

    def get_hostname(self):
        name = CMF.ip_to_hostname(self.ip)
        if name:
            name = name.upper()# Т.К В Windows переменные окружения COMPUTERNAME и USERNAME традиционно хранятся в верхнем регистре
        return name

class StatusBar:
    def __init__(self,refConteiner=None,refStatusBarText=None):
        self._refConteiner:ft.Ref[ft.Container] = refConteiner
        self._refStatusBarText:ft.Ref[ft.Text] = refStatusBarText
        self._text = ''
    def set_visible(self,val:bool=True):
        self._refConteiner.current.visible = val
    def set_text(self,text:str=None):
        if text:
            self._text = text
            self.set_visible()
        else:
            self._text = ''
            self.set_visible(False)
        self._refStatusBarText.current.value = self._text


class ModuleCfg:
    _dict_routes = dict()
    def __init__(self, alias:str|None='genesis', route:str|None=None, name:str='', icon:ft.Icons|None=None, tooltip:str='', sub_module:Optional[
        'ModuleCfg']=None):
        self.alias:str = alias
        self.route:str = route
        self.sub_dir:str|None = None
        if self.alias:
            self.sub_dir = os.sep.join([SRVCFG.DIR_ROOT,'Modules_data',self.alias])
        self.cust_data:Any|None = None
        self.name = name
        self.icon = icon
        self.tooltip = tooltip

        self.status_bar: None | StatusBar = None

        self.sub_modules:dict[str, ModuleCfg] = dict()
        if sub_module:
            self.sub_modules[sub_module.alias] = sub_module
        ModuleCfg._dict_routes[route] = self
        self.settingsRef:None|ft.Ref[ft.Column] = None

    def set_status_bar(self,refContainer,refStatusBarText):
        self.status_bar = StatusBar(refContainer, refStatusBarText)

    def add_submodule(self, module: 'ModuleCfg'):
        """Добавляет подмодуль к текущему модулю"""
        self.sub_modules[module.alias] = module

    def get_module_by_route(self,route:str):
        if route in ModuleCfg._dict_routes:
            return ModuleCfg._dict_routes[route]
class Srv_data(metaclass=SingletonMeta):
    def __init__(self):
        self.ip =  SRVCFG.HOST
        self.port = SRVCFG.PORT
        self.platform =  SRVCFG.IN_BROUSER

    def get_prefix_url(self):
        return f'http://{self.ip}:{self.port}'

class Data_page(SingletonMeta):
    #def __init__(self,page:ft.Page):
    page:ft.Page = None
    Data_vars:_Data_vars = _Data_vars()
    client_data:Client_data = None
    Data_user:Client_data = None
    Data_srv:Srv_data = None
    Data_module:ModuleCfg = None
    @classmethod
    def reload(cls):
        print(f'==== INIT Data_page =======')
        cls.Data_vars: _Data_vars = _Data_vars()
        cls.client_data: Client_data = Client_data(cls.page)
        cls.client_data.get_user_config()
        cls.Data_user: Client_data = cls.client_data
        cls.Data_srv: Srv_data = Srv_data()
        cls.Data_module: ModuleCfg = ModuleCfg(None, None)



