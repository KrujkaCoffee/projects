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
        data_bio_client = CSQ.custom_request_c(self.db_users,
                       f"""SELECT Пномер, ФИО,Должность,Подразделение FROM employee 
                        WHERE computer_name == '{self.hostname}' ORDER BY Пномер DESC LIMIT 1;""",rez_dict=True, one=True)
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
        CSQ.custom_request_c(self.db_flet,f"""UPDATE user_config SET {name_param} = {val} WHERE ip = '{self.ip}';""")

    def update_user_theme_mode(self,dark=False):
        self._update_user_param('theme_mode_dark', int(dark))

    def update_user_theme_color(self,color_scheme_seed):
        self._update_user_param('color_scheme_seed', color_scheme_seed)

class Client_data():
    def __init__(self,page:ft.Page):
        print(f'==== INIT Client_data {page.client_ip} =======')
        self.ip =  page.client_ip
        self.platform =  page.platform
        self.window_size =  (page.width,   page.height)
        self.user_agent =  page.client_user_agent or "неопределен"
        self.route =  page.route
        self.db_flet = MESCNF.Config.project.db_flet
        self.user_config:Client_config|None = None

    def _load_user_config_data(self):
        conf = CSQ.custom_request_c(self.db_flet, f"""SELECT * FROM user_config WHERE ip = '{self.ip}';""",
                                    rez_dict=True)
        return conf
    def get_user_config(self):
        conf =  self._load_user_config_data()
        if not conf:
            if not self.add_new_user():
                raise ConnectionError('Ошибка добавления нового юзера')
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
        add_row = [self.ip,self.get_hostname().split('.')[0]]
        rez = CSQ.custom_request_c(self.db_flet,"""INSERT INTO user_config (ip,hostname) VALUES (?,?);""",list_of_lists_c=[add_row])
        return rez


    def get_hostname(self):
        name = CMF.ip_to_hostname(self.ip)
        if name:
            name = name.upper()# Т.К В Windows переменные окружения COMPUTERNAME и USERNAME традиционно хранятся в верхнем регистре
        return name
class Module_cfg():
    _dict_routes = dict()
    def __init__(self,alias:str|None='genesis',route:str|None=None,name:str='',icon:ft.Icons|None=None, tooltip:str='',sub_module:Optional['Module_cfg']=None):
        self.alias:str = alias
        self.route:str = route
        self.sub_dir:str|None = None
        if self.alias:
            self.sub_dir = os.sep.join([SRVCFG.DIR_ROOT,'Modules_data',self.alias])
        self.cust_data:Any = None
        self.name = name
        self.icon = icon
        self.tooltip = tooltip

        self.sub_modules:dict[str, Module_cfg] = dict()
        if sub_module:
            self.sub_modules[sub_module.alias] = sub_module
        Module_cfg._dict_routes[route] = self
    def add_submodule(self, module: 'Module_cfg'):
        """Добавляет подмодуль к текущему модулю"""
        self.sub_modules[module.alias] = module

    def get_module_by_route(self,route:str):
        if route in Module_cfg._dict_routes:
            return Module_cfg._dict_routes[route]
class Srv_data(metaclass=SingletonMeta):
    def __init__(self):
        self.ip =  SRVCFG.HOST
        self.port = SRVCFG.PORT
        self.platform =  SRVCFG.IN_BROUSER

    def get_prefix_url(self):
        return f'http://{self.ip}:{self.port}'

class Data_page():
    def __init__(self,page:ft.Page):
        print(f'==== INIT Data_page =======')
        self.Data_vars:_Data_vars = _Data_vars()
        client_data:Client_data = Client_data(page)
        client_data.get_user_config()
        self.Data_user:Client_data = client_data
        self.Data_srv:Srv_data = Srv_data()
        self.Data_module:Module_cfg = Module_cfg(None,None)


