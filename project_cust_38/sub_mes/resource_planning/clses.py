import datetime
import project_cust_38.Cust_emoji as CEMOJ
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_SQLite as CSQ
from functools import partial
from dataclasses import dataclass
import project_cust_38.Cust_config as CFG
from project_cust_38.sub_mes.resource_planning.dataClass_res_pl import data_app as DTCLS
from typing import Generic, TypeVar
from project_cust_38.Cust_mes import Color
import copy
import project_cust_38.api_erp_commands as APIERP

T = TypeVar("T")

DTSUB = DTCLS.module_manage_sub_app
class Mes_type:
    pass

class Erp_type:
    @classmethod
    def _get_fields(cls):
        path =  DTSUB.custom_types.get_full_type_name(cls,drop_base=True)
        erp_base_name = CFG.Config.user_config.ERP_base.name

        code, data = APIERP.get_meta(erp_base_name , path)
        if code != 200 or data['data']['ЕстьОшибки']:
            return False, data['data']['Ошибки']
        return True, data['data']['Результат']
    @classmethod
    def template(cls):
        suc, data_erp = cls._get_fields()
        if not suc:
            CQT.msgbox(f'Ошибка получения полей: {data_erp}')
            return []
        rez = [{'_name':_['Имя'],'Поле':_['Синоним'],'Тип':_['Тип'], 'Стандартный':'⭐' if _['Стандартный'] else '',
                'Комментарий':_['Комментарий']} for _ in data_erp]
        return rez

class Plan(Mes_type):
    pass

class Naryad(Mes_type):
    pass

class MesMetaClass:
    plan = Plan
    naryad = Naryad


class ClientOrder(Erp_type):
    pass
class ProductionOrder(Erp_type):
    pass

class ErpDocuments:
    ClientOrder = ClientOrder
    ProductionOrder = ProductionOrder
class ErpReferences:
    pass

class ErpMetaClass:
    ErpDocuments = ErpDocuments
    ErpReferences = ErpReferences


class MainTypes:
    """Класс для хранения информации о типах данных"""

    def __init__(self, name: str, text: str, value:object, inner_data: dict = None, emoji:str = ''):
        self.name = name
        self.text = text
        self.value = value
        self.inner_data = inner_data if inner_data is not None else dict()
        self.emoji = emoji
    def __repr__(self):
        return f"MainTypes(name='{self.name}', text='{self.text}')"




class UiMode():
    LIST = "list"
    DETAILS = "details"
    NEW = "new"



class _AttributeInfoMeta():

    def __init__(self, type: type, val:object, name: str, comment:str, text: str, description: str, order: int,
                 show_new_templ:bool,emoj:str):
        self.type = type
        self.name = name
        self.comment = comment
        self.text = text
        self.description = description
        self.order = order
        self.val: object = val
        self.show_new_templ = show_new_templ
        self.emoj = emoj

    @property
    def alias_adduced(self)-> str:
        return  self.text

    def set_value(self,value):
        if self.type != type(value) and type(value) is not type(None):
            raise TypeError(f"_AttributeInfoMeta Expected {self.type}, got {type(value)}")
        self.val = value

    def to_ui(self):
        if self.name =='type':
            return DTSUB.custom_types.get_full_type_name(self.type)
        return f'{self.val}'

    def to_service_val(self):
        return self

    def __repr__(self):
        return f"_AttributeInfoMeta(name='{self.name}', type={self.type.__name__})"

@dataclass
class _AttributeInfo:
    def __init__(self):
        self.type: _AttributeInfoMeta = _AttributeInfoMeta(type, None,'type',  '', 'Тип','Тип данных', 0,True, '⚙️')
        self.alias: _AttributeInfoMeta = _AttributeInfoMeta(str, '','alias', 'для юзера','Имя','Имя атрибута', 5,True, '🏷️')
        self.description: _AttributeInfoMeta = _AttributeInfoMeta(str,'', 'description', '','Описание','Описание атрибута', 10,True, '📝')
        self.protected: _AttributeInfoMeta = _AttributeInfoMeta(bool, True, 'protected', 'для юзера','Изменяемый','Возможность изменить', 10,True, '🛡️')
        self.user_hidden:_AttributeInfoMeta = _AttributeInfoMeta(bool, False, 'user_hidden', 'для юзера аналог _','Скрытый','Видимость для пользователя', 15,True, '👀')
        self.for_list: _AttributeInfoMeta = _AttributeInfoMeta(bool, True, 'for_list', 'для списка','Вывод в таблицах','Вывод в таблице списка', 20,True, '📋')
        self.for_details: _AttributeInfoMeta = _AttributeInfoMeta(bool, True, 'for_details', 'для деталировки','Вывод в свойствах','Вывод в таблице свойства', 25,True, '🔍')
        self.for_new: _AttributeInfoMeta = _AttributeInfoMeta(bool, True, 'for_new', 'для создания','Вывод при создании','Вывод при создании нового объекта', 30,True, '✨')
        self.order: _AttributeInfoMeta = _AttributeInfoMeta(int, 99999, 'order', 'порядок отображения','Порядок вывода','Порядок вывода в таблицах', 35,True, '🔢')
        self.for_report: _AttributeInfoMeta = _AttributeInfoMeta(bool, True, 'for_report', 'для отчета','Вывод в отчетах','Вывод в отчетах', 40,True, '📊')
        self.report_user_hidden: _AttributeInfoMeta = _AttributeInfoMeta(bool, False, 'report_user_hidden', 'для юзера аналог _','Скрытый в отчетах','Скрытый в отчетах', 45,True, '👁️‍🗨️')
        self.attr_view: _AttributeInfoMeta = _AttributeInfoMeta(str, '', 'attr_view', 'имя поля представления типа составного','Представление типа','Как выглядит значение объекта в ячейках', 3,True, '🧩️')

    def __getattribute__(self, name):
        obj = object.__getattribute__(self, name)
        if isinstance(obj, _AttributeInfoMeta):
            return obj.val
        else:
            return obj
        raise AttributeError(f"_AttributeInfo object has no attribute '{name}'")

    def __setattr__(self, name, value):
        if hasattr(self, name):
            meta = self._meta(name)
            val = getattr(self, name)
            if isinstance(meta, _AttributeInfoMeta):
                meta.set_value(value )
                return
            else:
                super().__setattr__(name, value)
        # Иначе обычное присваивание
        super().__setattr__(name, value)

    def _meta(self,name):
        return object.__getattribute__(self, name)

    @property
    def alias_adduced(self)-> str:
        return f'_{self.alias}' if self.user_hidden else self.alias

    def _template_new(self):
        data_attrs = [v for k,v in  F.get_all_attrs(self).items() if  isinstance(v,_AttributeInfoMeta) and v.show_new_templ]
        data_attrs.sort(key=lambda x: x.order)
        return (
            {v.name:self.to_ui(v.name) for v in data_attrs},
            {v.name:self.to_service_val(v.name) for v in data_attrs},
            {v.name: v.alias_adduced for v in data_attrs},
            {v.name: v.description for v in data_attrs},
            {v.name: v.emoj for v in data_attrs},
        )
        return  data_attrs

    def to_ui(self,name:str):
        attr:_AttributeInfoMeta =  self._meta(name)
        return attr.to_ui()

    def to_service_val(self,name:str):
        attr:_AttributeInfoMeta = self._meta(name)
        return attr.to_service_val()

    def __repr__(self):
        return f"_AttributeInfo(type={str(self.type)}, alias='{self.alias}', desc='{self.description[:20]}{'...' if len(self.description) > 20 else ''}', protected={self.protected})"




@dataclass(slots=True)
class _Attribute(Generic[T]):
    info: _AttributeInfo
    value: T

    def set_value(self, value: T,forced: bool=False):
        if not forced and self.info.protected:
            return False
        type_attr = self.info.type
        if type_attr != type(value):
            raise TypeError(f"Expected {self.info.type}, got {type(value)}")
        if type_attr in (int, float):
            value = F.valm(value)
        if type_attr is bool:
            value = F.boolm(value)
        if type_attr is Cdt:
            pass
        self.value = value
        return True

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            if self.value == other.value:
                return True
        return False

    def __gt__(self, other):
        if isinstance(other, self.__class__):
            if self.value > other.value:
                return True
        return False

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return f"_Attribute({self.info.alias}={self.value})"
    @classmethod
    def template_new(cls)->tuple[list[dict],list[dict]]:
        dict_text_attrs, dict_data_attrs, dict_aliases,dict_descr,dict_emoj = _AttributeInfo()._template_new()
        rez_text = []
        rez_data = []
        for k,v in dict_text_attrs.items():
            tmp_dict_text = {'_name':k,'':dict_emoj[k], 'Свойство':dict_aliases[k],'Значение':v,'Описание':dict_descr[k]}
            tmp_dict_data = {'_name':k,'':dict_emoj[k], 'Свойство':dict_aliases[k],'Значение':dict_data_attrs[k],'Описание':dict_descr[k]}
            rez_text.append(tmp_dict_text)
            rez_data.append(tmp_dict_data)

        return rez_text, rez_data


    @classmethod
    def attr(cls,
            value: T,
             type_val: type,
            *,
            alias: str,
            description: str = "",
            protected: bool = True,
            user_hidden: bool = False,
            for_list: bool = True,
            for_details: bool = True,
            for_new: bool = True,
             order:int = 99999999,
             for_report:bool= True,
             report_user_hidden: bool = False,
             attr_view: str = ''

    ) -> '_Attribute[T]':
        obj_info =  _AttributeInfo()
        obj_info.type = type_val
        obj_info.alias = alias
        obj_info.description = description
        obj_info.protected = protected
        obj_info.user_hidden = user_hidden
        obj_info.for_list = for_list
        obj_info.for_details = for_details
        obj_info.for_new = for_new
        obj_info.order = order
        obj_info.for_report = for_report
        obj_info.report_user_hidden = report_user_hidden
        obj_info.attr_view = attr_view

        return cls(info=obj_info,
            value=value,
        )


class _ImportDb():

    def parce_row_dict(self,item:dict):
        attrs = F.get_all_attrs_with_properties(self,include_private=True)
        for key,val in item.items():
            fix_key = str(key).replace(".", "_")
            if fix_key not in attrs:
                print(f'class {self.__class__.__name__} ImportDbRow attr not declared :{fix_key}' )
            exec(f'self.{fix_key} = val')



    def __repr__(self):
        return (f"{', '.join([f'"{k}" : {v if F.is_numeric(v) else f'"{v}"'}' for k,v in self.__dict__.items()])}")


class _MiniManager[T]:
    def __init__(self):
        pass

    _child_class: type[T]
    @property
    def as_dict(self) -> dict[int, T]:
        if not getattr(self, '_child_class', False):
            raise AttributeError(f'В классе не указано свойство _child_class')

        if not getattr(self,'_dict_states',False):
            rez = dict()
            for it in F.get_all_attrs_with_properties(self.__class__).values():
                if isinstance(it,self._child_class):
                    rez[it.id]=it
            self._dict_states = rez
        return self._dict_states

class Cdt():
    def __init__(self, date:datetime.datetime = None):
        self.dt: datetime.datetime | None = None
        if date is None:
            self.dt = None#F.now('')
        if isinstance(date,str):
            if F.is_date(date):
                self.dt = F.strtodate(date)
            else:
                raise TypeError(f'date must be %Y-%m-%d %H:%M:%S format')
        if isinstance(date,datetime.datetime):
            self.dt = date
        if type(date) is datetime.date:
            self.dt = datetime.datetime.combine(date,datetime.time(0,0,0))

    def now(self)->'Cdt':
        self.dt=F.now('')
        return self

    def set_time(self,time:datetime.time,copy_obj=False)->'Cdt|None':
        if copy_obj:
            return Cdt(self.dt.combine(self.dt,time))
        self.dt = self.dt.combine(self.dt,time)
    def to_db(self):
        if self.dt is None:
            return None
        return F.datetostr(self.dt)


    def to_string(self):
        if self.dt is None:
            return ''
        return F.datetostr(self.dt)


    def to_string_ru(self):
        if self.dt is None:
            return ''
        return F.datetostr(self.dt,"%d.%m.%Y %H:%M:%S")
    def to_string_ru_wo_s(self):
        if self.dt is None:
            return ''
        return F.datetostr(self.dt,"%d.%m.%Y %H:%M")


    def __bool__(self):
        if self.dt is None or self.dt == '':
            return False
        return True

    def __gt__(self, other):
        if self.dt and other.dt:
            if self.dt > other.dt:
                return True
        return False

    def __eq__(self, other):
        if isinstance(other, Cdt):
            if self.dt == other.dt:
                return True
        return False

    def __repr__(self):
        if self.dt:
            return f"Cdt('{self.to_string_ru()}')"
        return "Cdt(None)"


class CustomTypes:
    TYPE_MAP = {
        "str": MainTypes("str", "Текст", value=str, emoji="🔠"),
        "int": MainTypes("int", "Целое число", value=int, emoji="🔢"),
        "float": MainTypes("float", "Число с плавающей точкой", value=float, emoji="➗"),
        "bool": MainTypes("bool", "Логический (Истина/Ложь)", value=bool, emoji="✅"),
        "Cdt": MainTypes("Cdt", "Дата", value=Cdt, emoji="📅"),

        # Пользовательские типы
        "MesMetaClass": MainTypes(
            "MesMetaClass",
            "Данные МЕС",
            value=MesMetaClass,
            inner_data={
                "plan": MainTypes("plan", "План производства", value=MesMetaClass.plan, emoji="📈"),
                "naryad": MainTypes("naryad", "Наряды", value=MesMetaClass.naryad, emoji="🧾"),
            },
            emoji="🏭"
        ),

        "ErpMetaClass": MainTypes(
            "ErpMetaClass",
            "Данные ERP",
            value=ErpMetaClass,
            inner_data={
                "Документы": MainTypes(
                    "Документы",
                    "Документы",
                    value=ErpMetaClass.ErpDocuments,
                    inner_data={
                        "ЗаказКлиента": MainTypes(
                            "ЗаказКлиента",
                            "Заказ клиента",
                            value= ErpMetaClass.ErpDocuments.ClientOrder
                        ),
                        "ЗаказНаПроизводство2_2": MainTypes(
                            "ЗаказНаПроизводство2_2",
                            "Заказ на производство",
                            value=ErpMetaClass.ErpDocuments.ProductionOrder
                        ),
                    },
                    emoji="📄"
                ),
                "Справочники": MainTypes(
                    "Справочники",
                    "Справочники",
                    value=ErpMetaClass.ErpReferences,
                    emoji="📚"
                ),
            },
            emoji="💼"
        ),
    }

    def __init__(self):
        pass

    def _find_type_by_path(self, data: dict, path_parts: list) -> MainTypes:

        if not path_parts:
            return None

        current_key = path_parts[0]

        if current_key in data:
            current_type = data[current_key]

            if len(path_parts) == 1:
                return current_type

            if isinstance(current_type, MainTypes) and current_type.inner_data:
                return self._find_type_by_path(current_type.inner_data, path_parts[1:])

        return None

    def get_type(self, full_name: str) -> MainTypes:

        if not full_name:
            return None

        path_parts = full_name.split('.')
        return self._find_type_by_path(self.TYPE_MAP, path_parts)

    def _find_type_by_value(self,data: dict, target_value, path: list = None) -> tuple:

        if path is None:
            path = []

        for key, main_type in data.items():
            if isinstance(main_type, MainTypes):
                if main_type.value == target_value:
                    return main_type, path + [main_type.name]
                if main_type.inner_data:
                    found, found_path = self._find_type_by_value(
                        main_type.inner_data,
                        target_value,
                        path + [main_type.name]
                    )
                    if found:
                        return found, found_path

        return None, None

    def get_full_type_name(self,obj_or_value:object|MainTypes,drop_base:bool=False) -> str:
        if isinstance(obj_or_value, MainTypes):
            target_value = obj_or_value.value
        else:
            target_value = obj_or_value
        found, path = self._find_type_by_value(self.TYPE_MAP, target_value)

        if found:
            if drop_base:
                path = path[1:]
            return '.'.join(path)


        if hasattr(obj_or_value, '__name__'):
            return f"Неизвестный_тип.{obj_or_value.__name__}"
        return f"Неизвестный_тип.{str(obj_or_value)}"
    def template(self)->tuple[list,list]:
        template = []
        template_data = []
        template, template_data = self._add_types_tmplate(template, template_data, self.TYPE_MAP)
        return template, template_data
    def _add_types_tmplate(self, template, template_data, inner_data, parent: str = '', lvl=0) -> tuple[list, list]:
        if parent:
            parent = f'{parent}.'
        for k, v in inner_data.items():
            name = v.name

            tmp_dict_text = {'_name': name, "": v.emoji, '_parent': parent, 'Тип': f'{" " * 4 * lvl}{v.text}'}
            tmp_dict_data = {'_name': name, "": v.emoji, '_parent': parent, 'Тип': v}

            template.append(tmp_dict_text)
            template_data.append(tmp_dict_text)
            if v.inner_data:
                template, template_data = self._add_types_tmplate(template, template_data, v.inner_data, parent=f'{parent}{name}',
                                                            lvl=lvl + 1)
        return template, template_data




class UserPh():
    def __init__(self, ref:str):
        self.ref_ph:str = ref
        self.ph:DDM.ФизическиеЛица = None
        self.department:DDM.Подразделения = None
        self._load_ph()
        self._load_department()
    def __bool__(self)->bool:
        if self.ph:
            return True
        return False
    def __str__(self):
        return self.ФИОк
    def __repr__(self):
        return self.ФИОк


    def _load_ph(self):
        if self.ref_ph not in STORE.DICT_ФизическиеЛица_by_ref:
            print(f'Не найдена в DICT_ФизическиеЛица_by_ref запись {self.ref_ph}')
            return
        self.ph = STORE.DICT_ФизическиеЛица_by_ref[self.ref_ph]

    def _load_department(self):
        if not self.ph:
            return
        if self.ph.ФизическоеЛицо_Key not in STORE.DICT_КадроваяИстория_by_ref:
            raise ValueError(f'Не найдена в DICT_КадроваяИстория_by_ref запись {self.ph.ФизическоеЛицо_Key}')
            return
        data = STORE.DICT_КадроваяИстория_by_ref[self.ph.ФизическоеЛицо_Key]
        self.department = STORE.DICT_Подразделения_by_ref[data.Подразделение_Key]
    @property
    def ФИОк(self)->str:
        if not self.ph:
            return ''
        return f'{self.ph.Фамилия} {self.ph.Имя[0]}.{self.ph.Отчество[0]}'

class SubjectPl:
    def __init__(self, name, text, descr):
        self.name = name
        self.text = text
        self.descr = descr


class SubjectsPl:
    rab_place = SubjectPl('rab_place', 'Рабочее место', 'План по постам, По ТЗ 100066480')
    supervising_еngineer = SubjectPl('supervising_еngineer', 'Шеф-инженер', 'По ТЗ 100057602')

    @classmethod
    def get(cls, name)->SubjectPl|None:
        for sbj in F.get_all_attrs(cls).values():
            if sbj.name == name:
                return sbj

    @classmethod
    def get_all(cls)->list[SubjectPl]:
        return [_ for _ in F.get_all_attrs(SubjectsPl).values() if isinstance(_, SubjectPl)]

class Type_entity:
    def __init__(self,id,name,name_one,text,descr):
        self.id=id
        self.name=name
        self.name_one=name_one
        self.text=text
        self.descr=descr

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def serialize(self)->int:
        return self.id

    @property
    def for_ui(self):
        return self.text

class Type_entitys:
    Res = Type_entity(0,'Res', 'Шаблон ресуров','Ресурс', 'Manage Resource Planning')
    Eve = Type_entity(1,'Eve', 'Шаблон событий', 'Событие','Manage Event Planning')

    @classmethod
    def get(cls, id:int):
        for it in F.get_all_attrs_with_properties(cls):
            if it.id == id:
                return it
    @classmethod
    def get_by_name(cls, name:str):
        for it in F.get_all_attrs_with_properties(cls).values():
            if isinstance(it,Type_entity) and it.name == name:
                return it

    @classmethod
    def deserialize(cls, data:int):
        for it in F.get_all_attrs_with_properties(cls).values():
            if isinstance(it,Type_entity) and it.id == data:
                return it
class FocusTypes():
    EVENT:str = "event"
    RESOURCE:str = "resource"
class Info():

    def __init__(self,ui_tbl,ui_btn_ok,ui_btn_cancel,ui_btn_new_attr):
        self._ui:CQT.QtWidgets.QTableWidget = ui_tbl
        self._ui_ok:CQT.QtWidgets.QPushButton = ui_btn_ok
        self._ui_cancel:CQT.QtWidgets.QPushButton = ui_btn_cancel
        self._ui_new_attr:CQT.QtWidgets.QPushButton = ui_btn_new_attr
        self.t:CQT.TableContext = CQT.TableContext(self._ui)
        self._raw_data = None
        self._dict_data = None
        self.dict_aliases = None
        self.editable_val = None
        self.fnc_oform = None
        self.fnc_update_data = None
        self.protected_names:list|tuple|set = None
        self._ui_cancel.clicked.connect(self._fill_data)
        self._ui_new_attr.clicked.connect(self._new_attr)

    def clear(self):
        CQT.soft_clear_tbl(self.t.tbl)
        self._ui_ok.setEnabled(False)
        self._ui_cancel.setEnabled(False)

    def update_info(self,template:dict,dict_data:dict,editable_val:bool=False,dict_aliases:dict=None,
                    fnc_oform=None,fnc_update_data=None,fnc_edit_cells=None,protected_names=None,fnc_add_attr=None):
        """
        def fnc_update_data(t:CQT.TableContext,delta:dict):
            pass

        :param template:
        :param editable_val:
        :param dict_aliases:
        :param dict_data:
        :param fnc_oform:
        :param fnc_update_data:
        :return:
        """
        self._raw_data = copy.deepcopy(template)
        self._dict_data = copy.deepcopy(dict_data)
        self.dict_aliases = dict_aliases

        self.editable_val = editable_val
        self.fnc_oform = fnc_oform
        self.fnc_update_data = fnc_update_data
        self.fnc_edit_cells = fnc_edit_cells
        self.fnc_add_attr = fnc_add_attr
        self.protected_names = protected_names
        self._fill_data()
        self._ui_ok.setEnabled(True)
        self._ui_cancel.setEnabled(True)
    @CQT.onerror
    def _new_attr(self):
        def fnc_oform(tbl:CQT.QtWidgets.QTableWidget,*args):

            def fnc_cell_edit_bool(tbl:CQT.QtWidgets.QTableWidget, item:CQT.QtWidgets.QTableWidgetItem, t:CQT.TableContext):
                i = item.row()
                j = item.column()
                row = t.get_row(i)
                clmn_name = t.name_by_idx(j)
                row.set_value(clmn_name, item.text(),set_cust_content=True)
                return True


            def fnc_switch(tbl:CQT.QtWidgets.QTableWidget,val:bool,i,j,*args):
                pass

            t = CQT.TableContext(tbl)
            for row in t.rows():
                attr_o:_AttributeInfoMeta = row.value('Значение',get_cust_content=True)
                attr_o_type = attr_o.type
                if attr_o_type is type:
                    @CQT.onerror
                    def fnc_select_type(lbl: CQT.InteractiveLabelInstance, sub_self, i, j, row: CQT.TableRow):
                        def fnc_oform_tbl_type(tbl:CQT.QtWidgets.QTableWidget,*args):
                            t = CQT.TableContext(tbl)
                            for row in t.rows():
                                pass
                            t.hide_if_not_dev(CFG)

                        template, template_data = DTSUB.custom_types.template()

                        rez = CQT.msgboxg_get_table(DTSUB.sub_self,'Выбор типа данных',template,
                                        styleSheet=CQT.MES_EDIT_CSS,func_oform_tbl=fnc_oform_tbl_type,
                                                    dict_or_list_user_data=template_data,selectRows=True,selection_from_tbl=True
                                        )
                        if not rez:
                            return
                        rez = rez[0]
                        new_type_name = rez['_parent'] + rez['_name']
                        new_type:MainTypes = DTSUB.custom_types.get_type(new_type_name)
                        new_meta:_AttributeInfoMeta = row.value('Значение',get_cust_content=True)
                        row.set_value('Значение', new_type.text)
                        #DTSUB.custom_types.get_full_type_name(new_type)
                        new_meta.set_value(new_type.value)
                        row.set_value('Значение', new_meta,set_cust_content=True)
                        lbl.set_text(new_type.text)

                        #====================clear view=================================
                        row_view_type = row.ctx.find_row({'_name':'attr_view'},first=True)
                        meta_view_type: _AttributeInfoMeta = row_view_type.value('Значение', get_cust_content=True)
                        meta_view_type.set_value('')
                        row_view_type.set_value('Значение', meta_view_type,set_cust_content=True)
                        row_view_type.set_value('Значение', meta_view_type.to_ui())
                        # ================================================================
                        if issubclass(new_meta.val,(Erp_type,Mes_type)):
                            row_view_type.hide(False)
                        else:
                            row_view_type.hide(True)


                    widg = CQT.add_interactive_label(t.tbl, row.i, t.nf['Значение'], row.value('Значение'),
                                                     parent_self=DTSUB.sub_self, grab_style_from_cell=True,
                                                     autoupdate_column_size=False)
                    widg.add_button('...', 'Выбор',
                                    fnc_select_type,
                                    cell_val=row, img_path=F.sep().join([F.path_to_caller_file_c(),
                                                                             'icons', 'btn_select']))

                elif attr_o_type in (str,int,float):
                    if attr_o.name == 'attr_view':
                        def fnc_select_type_attr_view(lbl: CQT.InteractiveLabelInstance, sub_self, i, j, row: CQT.TableRow):
                            t = row.ctx
                            row_type = t.find_row({'_name':'type'},True)
                            meta:_AttributeInfoMeta = row_type.value('Значение',get_cust_content=True)
                            if meta.val is None:
                                CQT.msgbox(f'Не выбран Тип')
                                return
                            type = meta.val
                            full_path = DTSUB.custom_types.get_full_type_name(type)

                            if issubclass(type, Erp_type):
                                template = type.template()
                                def fnc_oform_tbl_type_attr_view(tbl:CQT.QtWidgets.QTableWidget,*args):
                                    t = CQT.TableContext(tbl)
                                    for row in t.rows():
                                        row.set_font_format(italic=True, col_name='Тип')
                                        if row.value('Стандартный'):
                                            row.set_font_format(bold=True,col_name='Поле')

                                    t.hide_if_not_dev(CFG)

                                rez = CQT.msgboxg_get_table(DTSUB.sub_self, 'Выбор поля представления', template,
                                                            styleSheet=CQT.MES_CSS,
                                                            func_oform_tbl=fnc_oform_tbl_type_attr_view,
                                                            selectRows=True,
                                                            selection_from_tbl=True,
                                                            sortingEnabled=True
                                                            )
                                if not rez:
                                    return

                                new_type_attr_view =';'.join([_['_name'] for _ in rez])
                                new_type_attr_view_meta: _AttributeInfoMeta = row.value('Значение', get_cust_content=True)
                                row.set_value('Значение', new_type_attr_view)
                                # DTSUB.custom_types.get_full_type_name(new_type)
                                new_type_attr_view_meta.set_value(new_type_attr_view)
                                row.set_value('Значение', new_type_attr_view_meta, set_cust_content=True)
                                lbl.set_text(new_type_attr_view)




                            if issubclass(type, Mes_type):
                                data = type.template()
                                #TODO для МЕС
                            pass

                        widg = CQT.add_interactive_label(t.tbl, row.i, t.nf['Значение'], row.value('Значение'),
                                                         parent_self=DTSUB.sub_self, grab_style_from_cell=True,
                                                         autoupdate_column_size=False)
                        widg.add_button('...', 'Выбор',
                                        fnc_select_type_attr_view,
                                        cell_val=row, img_path=F.sep().join([F.path_to_caller_file_c(),
                                                                             'icons', 'btn_select']))
                    else:
                        row.set_editable('Значение', True)
                elif attr_o_type is bool:
                    CQT.add_check_box_switcher(t.tbl,row.i,t.nf['Значение'],attr_o.val,fnc_switch)
                else:
                    raise Exception(f'Неизвестный тип {attr_o_type}')

            t.hide_if_not_dev(CFG,True)

            CQT.connect_cell_edit(t.tbl,fnc_cell_edit_bool,t)

        if self._raw_data is None:
            return
        if DTSUB.current_settings_mode == Type_entitys.Res:

            def fnc_validate(t:CQT.TableContext):
                rez = dict()
                for row in t.rows():
                    value = row.value('Значение',get_cust_content=True)
                    if isinstance(value,_AttributeInfoMeta):
                        value= value.val
                    rez[row.value('_name')] = value
                return rez

            list_text, list_data = _Attribute.template_new()
            rez = CQT.msgboxg_get_table(DTSUB.sub_self,'Создание атрибута',list_text,dict_or_list_user_data=list_data,
                                        styleSheet=CQT.MES_EDIT_CSS,func_oform_tbl=fnc_oform,func_validate_t=fnc_validate
                                        )
            if not  rez:
                return
            new_attr:_Attribute = _Attribute.attr(None,type_val= rez['type'],  alias=rez['alias'], attr_view=rez['attr_view'],
                                   description=rez['description'], protected=rez['protected'],
                                 user_hidden=rez['user_hidden'], for_list=rez['for_list'], for_details=rez['for_details'],
                                for_new=rez['for_new'], order=rez['order'], for_report=rez['for_report'],
                                                  report_user_hidden=rez['report_user_hidden'])

            id = self._dict_data['id']
            res_o:ShablonRes = DTSUB.shablons_res.get(id)
            res_o.add_new_custom_attr(new_attr)
            if self.fnc_add_attr:
                self.fnc_add_attr()

            #TODO добавить
    def _fill_data(self):
        if self._raw_data is None:
            return
        CQT.fill_wtabl(self.transponate(self._raw_data,self.dict_aliases,self._dict_data),self.t.tbl,
                       {},
                       styleSheet=CQT.MES_EDIT_CSS if self.editable_val else CQT.MES_CSS,auto_type=False,
                       selectionMode='SingleSelection',dict_or_list_user_data=self.transponate(self._dict_data,self.dict_aliases,self._dict_data))

        CQT.load_column_widths(tbl=self.t.tbl,tmp_dir= CQT.qt_tmp_dir())

        self.t = CQT.TableContext(self._ui)
        self.t.set_editable('Значение',True)
        for row in self.t.rows():
            name = row.value('_name')
            text = row.value('Свойство')
            if name in self.protected_names or not self.editable_val:
                row.set_editable('Значение',False)
            if text.startswith('_') and not CFG.Config.user_config.is_developer:
                row.hide(True)

        if self.fnc_oform:
            self.fnc_oform(self.t)

        self._ui_ok.setVisible(self.editable_val)
        self._ui_cancel.setVisible(self.editable_val)

        self.clear_and_connect_btn(self._ui_ok, self.fnc_update_data)
        if self.editable_val:
            CQT.connect_cell_edit(self.t.tbl, self.fnc_edit_cells)
        pass
    def _calc_delta(self):
        delta = dict()
        for row in self.t.rows():
            val = row.value('Значение',get_cust_content=True)
            name = row.value('_name')
            if val == self._dict_data[name]:
                continue

            delta[name] = val
        return delta
    def clear_and_connect_btn(self,btn, new_func):
        # Отключаем ВСЕ слоты от сигнала
        try:
            btn.clicked.disconnect()
        except TypeError:
            # Если слотов не было
            pass
        if new_func:
        # Подключаем новый
            def new_wrapper():
                new_func(self.t,self._calc_delta())
            btn.clicked.connect(new_wrapper)

    @staticmethod
    def transponate(template:dict,dict_aliases:dict=None,dict_data:dict=None)->list[dict]:
        if template is None:
            return
        if dict_aliases is None:
            dict_aliases = dict()
        if dict_data is None:
            dict_data = dict()
        return [{'_name':k, '_data':dict_data.get(k,v), 'Свойство':dict_aliases.get(k,k),'Значение':v}  for k,v in template.items()]





class _BaseEntity():
    _TYPE_ENTITY: Type_entity = None
    def __setattr__(self, key, value):
        attr = getattr(self,key,'_None')
        if attr !='_None':
            if isinstance(attr,_Attribute):
                print('Установка атрибута только через метод _Attribute .set_value')
                return
        super().__setattr__(key,value)

    def __init__(self, type_entity:Type_entity, id:int|None=None, name:str = '', description:str = '',
                 emoj:str = CEMOJ.СтатусыПроизводства.selected.symbol,for_delete:bool=False,color:Color|None=None):
        if color is None:
            color = Color.random()
        self.id:_Attribute[int] =            _Attribute.attr(id, int,        alias= '№',       description='', protected=True,user_hidden=True,for_list=True, for_details=True,for_new=True, report_user_hidden=True, order=1)
        self.type_entity:_Attribute[Type_entity] =   _Attribute.attr(type_entity, Type_entity, alias= 'Тип',     description='', protected=True,user_hidden=True,for_list=True,  for_details=True)
        self.emoj:_Attribute[str] =          _Attribute.attr(emoj, str,         alias= '',        description='', protected=False,user_hidden=False,for_list=True,   for_details=True,order=23)
        self.name:_Attribute[str]  =         _Attribute.attr(name, str,         alias= 'Имя',     description='', protected=False,user_hidden=False,for_list=True,   for_details=True,order=44)
        self.description:_Attribute[str] =   _Attribute.attr(description, str,         alias= 'Описание',description='', protected=False,user_hidden=False,for_list=True,    for_details=True,order=55)
        self.for_delete:_Attribute[bool] =   _Attribute.attr(for_delete, bool,         alias= 'Удал.',description='', protected=False,user_hidden=False,for_list=True,    for_details=True, for_report = False, order=12)
        self.color:_Attribute[Color] =   _Attribute.attr(color, Color,         alias= 'Цвет',description='', protected=False,user_hidden=False,for_list=False,    for_details=True, report_user_hidden = True, order=33)


    def _gen_new_cust_attr_name(self):
        return f'custattr_{F.get_time_shtamp_c()}'
    def add_new_custom_attr(self,data:_Attribute):
        name = self._gen_new_cust_attr_name()
        self.__setattr__(name,data)
        print(f'New attr {name} added')
        pass

    def to_dump(self,attr_name):
        attr_value:_Attribute = getattr(self,attr_name)
        val = attr_value.value
        if attr_name == 'type_entity':
            val = val.serialize()
        if attr_name == 'color':
            val = val.serialize()
        if isinstance(val, (CSQ.SQLITE_TYPES)):
            return val
        else:
            try:
                val = val.serialize()
                return val
            except:
                pass
            raise Exception("Not supported")



    def to_ui(self,attr_name)-> str:
        attr_val:_Attribute = getattr(self,attr_name)

        if attr_name == 'for_delete':
            return CEMOJ.СтатусыПроизводства.error.symbol  if attr_val.value else ''
        if attr_name == 'color':
            val: Color = attr_val.value
            return ''
        if attr_name == 'type_entity':
            attr_in: Type_entity = attr_val.value
            return attr_in.for_ui
        return attr_val.value
    def from_ui(self,attr_name, value):
        if attr_name == 'for_delete':
            return value
        if attr_name == 'color':
            if isinstance(value,str):
                try:
                    clr_o = Color(value)
                    return clr_o
                except:
                    pass
            if isinstance(value, Color):
                clr_o: Color = value
                return clr_o
            raise ValueError(f"Invalid color value: {value}")
        return value

    def to_service_val(self,attr_name)-> str:
        attr_val: _Attribute = getattr(self, attr_name)

        if attr_name == 'color':
            val: Color = attr_val.value
            return val
        if attr_name == 'type_entity':
            val: Type_entity = attr_val.value
            return val.name

        return attr_val.value

    def serialize(self)-> dict:
        data: dict = F.get_all_attrs(self)
        return {k: self.to_dump(k) for k, v in data.items()}

    def __str__(self):
        return f'{self.emoj.value} {self.name.value}'
    def get_protected_names(self)->list[str]:
        data:dict[str,_Attribute] = F.get_all_attrs_with_properties(self)
        return [k for k, v in data.items() if v.info.protected]
    def get_attr(self,name:str)->_Attribute:
        return getattr(self,name)

    def set_id(self,id:int)->bool:
        if not self.id.set_value(id,forced=True):
            return False
        return True

    def full_template(self)->dict:
        data:dict = F.get_all_attrs_with_properties(self)
        data = F.sort_dict_by_key(data,lambda k: data[k].info.order)
        return ({k :self.to_ui(k) for k,v in data.items() if  v.info.for_details} ,
                {k :self.to_service_val(k) for k,v in data.items() if  v.info.for_details} ,
                {k : v.info.alias_adduced for k,v in data.items()})


    def template(self)->dict:
        data = F.get_all_attrs_with_properties(self)
        data = F.sort_dict_by_key(data, lambda k: data[k].info.order)
        return ({k: self.to_ui(k) for k,v in data.items() if  v.info.for_list},
                {k: self.to_service_val(k) for k, v in data.items() if v.info.for_list},
                {k : v.info.alias_adduced for k,v in data.items()})


    def __repr__(self):
        type_name = self.type_entity.value.name if self.type_entity.value else "None"
        return f"_BaseEntity(id={self.id.value}, name='{self.name.value}', type='{type_name}', emoj='{self.emoj.value}')"

    def set_data(self, data:dict[str,str])->bool:
        fl = False
        for k,v in data.items():
            attr = self.get_attr(k)
            if attr.info.protected:
                continue
            attr.set_value(self.from_ui(k,v))
            fl = True
        return fl
class ShablonRes(_BaseEntity):
    _TYPE_ENTITY = Type_entitys.Res
    def __init__(self):
        super().__init__(self._TYPE_ENTITY)

    def smth(self):
        pass


    def __repr__(self):
        return f"ShablonRes(id={self.id.value}, name='{self.name.value}', emoj='{self.emoj.value}')"
class ShablonEve(_BaseEntity):
    _TYPE_ENTITY = Type_entitys.Eve
    def __init__(self):
        super().__init__(self._TYPE_ENTITY)


    def smth(self):
        pass

    def __repr__(self):
        return f"ShablonEve(id={self.id.value}, name='{self.name.value}', emoj='{self.emoj.value}')"

class _BaseShablons():
    _TYPE_SHABLON:ShablonEve|ShablonRes = None


    def __init__(self):
        self.dict_shablons:dict[int,ShablonRes|ShablonEve] = dict()


    def add(self):
        new_shablon = self._new()
        if not new_shablon.set_id(self.gen_new_id()):
            return False

        self.dict_shablons[new_shablon.id.value] = new_shablon
        return new_shablon
    def gen_new_id(self)->int:
        last_id = -1
        if self.dict_shablons:
            last_id = max(list(self.dict_shablons.keys()))
        return last_id + 1


    def _new(self)->ShablonEve|ShablonRes:
        return self._TYPE_SHABLON()


    def _load(self):
        self.dict_shablons = dict()

    @CQT.onerror
    def full_template(self,include_deleted:bool=True)->tuple[list[dict],list[dict],dict]:

        accessed_shablons = [_ for _ in self.dict_shablons.values() if not _.for_delete.value or include_deleted]
        if not accessed_shablons:
            return [],[],{}
        return ([_.full_template()[0] for _ in accessed_shablons],
                [_.full_template()[1] for _ in accessed_shablons],
                [_.full_template()[2] for _ in accessed_shablons][0])

    @CQT.onerror
    def template(self,include_deleted:bool=True)->tuple[list[dict],list[dict],dict]:
        accessed_shablons = [_ for _ in self.dict_shablons.values() if not _.for_delete.value or include_deleted]
        if not accessed_shablons:
            return [],[],{}
        return ([_.template()[0]  for _ in accessed_shablons],
                [_.template()[1] for _ in accessed_shablons],
                [_.template()[2]  for _ in accessed_shablons][0])

    def get(self,id:int)->ShablonEve|ShablonRes:
        if id in self.dict_shablons:
            return self.dict_shablons[id]
        else:
            print(f"Нет такого шаблона {id}")
            return _BaseEntity(self._TYPE_SHABLON)

    def __repr__(self):
        type_name = self._TYPE_SHABLON.__name__ if self._TYPE_SHABLON else "None"
        return f"_BaseShablons(type='{type_name}', count={len(self.dict_shablons)})"

class ShablonsRes(_BaseShablons):
    _TYPE_SHABLON = ShablonRes
    def __init__(self):
        super().__init__()

    def __repr__(self):
        return f"ShablonsRes(count={len(self.dict_shablons)})"


class ShablonsEve(_BaseShablons):
    _TYPE_SHABLON = ShablonEve
    def __init__(self):
        super().__init__()

    def __repr__(self):
        return f"ShablonsEve(count={len(self.dict_shablons)})"

class _BaseShablonsDB():
    _TYPE_SHABLON:ShablonsRes|ShablonsEve = None
    @staticmethod
    def _parse(attr_name:str,val):
        if attr_name == 'id':
            if isinstance(val,int):
                return val
            raise TypeError(f'Not supported type while deserialization (attr_name= "{attr_name}")')
        if attr_name == 'type_entity':
            if isinstance(val,int):
                return Type_entitys.deserialize(val)
            raise TypeError(f'Not supported type while deserialization (attr_name= "{attr_name}")')
        if attr_name == 'emoj':
            if isinstance(val,str):
                return val
            raise TypeError(f'Not supported type while deserialization (attr_name= "{attr_name}")')
        if attr_name == 'name':
            if isinstance(val,str):
                return val
            raise TypeError(f'Not supported type while deserialization (attr_name= "{attr_name}")')
        if attr_name == 'description':
            if isinstance(val,str):
                return val
            raise TypeError(f'Not supported type while deserialization (attr_name= "{attr_name}")')
        if attr_name == 'for_delete':
            if isinstance(val,int):
                return bool(val)
            raise TypeError(f'Not supported type while deserialization (attr_name= "{attr_name}")')
        if attr_name == 'color':
            if isinstance(val,str):
                return Color.deserialize(val)
            raise TypeError(f'Not supported type while deserialization (attr_name= "{attr_name}")')

        raise ValueError(f'Not supported attribute while deserialization (attr_name= "{attr_name}")')


    @staticmethod
    def to_dict(base_shablons: _TYPE_SHABLON) -> dict:
        return [it.serialize() for it in base_shablons.dict_shablons.values()]

    @classmethod
    def from_dict(cls,lst_rows: list[dict]) -> _TYPE_SHABLON:
        shablons=  cls._TYPE_SHABLON()
        for row in lst_rows:
            new_shabl = shablons.add()
            new_shabl.id.set_value(cls._parse('id',row['id']))
            new_shabl.type_entity.set_value(cls._parse('type_entity',row['type_entity']))
            new_shabl.emoj.set_value(cls._parse('emoj',row['emoj']))
            new_shabl.name.set_value(cls._parse('name',row['name']))
            new_shabl.description.set_value(cls._parse('description',row['description']))
            new_shabl.for_delete.set_value(cls._parse('for_delete',row['for_delete']))
            new_shabl.color.set_value(cls._parse('color',row['color']))
        return shablons


class ShablonsResDB(_BaseShablonsDB):
    _TYPE_SHABLON = ShablonsRes
    def __init__(self):
        super().__init__()
class ShablonsEveDB(_BaseShablonsDB):
    _TYPE_SHABLON = ShablonsEve

    def __init__(self):
        super().__init__()


class _BaseDimension:
    _TYPE_DIMENSION:Type_entity = None

    def __init__(self,id_shablon:int, id:int ,name:str='',descr:str=''):
        self.id: _Attribute[int] = _Attribute.attr(id,int,  alias='№',description='',protected=True,user_hidden=True,for_list=True,for_details=True,for_new=False,report_user_hidden=True, order=0)
        self.name: _Attribute[str] = _Attribute.attr(name,str,  alias='Название',description='',protected=False,user_hidden=False,for_list=True,for_details=True,for_new=True, order=3)
        self.descr: _Attribute[str] = _Attribute.attr(descr,str, alias='Описание',description='',protected=False,user_hidden=False,for_list=True,for_details=True,for_new=True, order= 9)
        self.shablon: _Attribute[int] = _Attribute.attr(id_shablon,int,  alias='Шаблон',description='',protected=True,user_hidden=False,for_list=True,for_details=True,for_new=True, order=8)
        self.emoj: _Attribute[str] = _Attribute.attr('',str,  alias='', description='', protected=False, user_hidden=False,for_list=True, for_details=True,for_new=False,  order=2)
        self.for_delete: _Attribute[bool] = _Attribute.attr(False,bool,  alias='❌', description='На удаление',protected=False, user_hidden=False, for_list=True, for_details=True,   for_new=False, for_report= False, order=1)
        self.color: _Attribute[Color] = _Attribute.attr(Color.random(), Color, alias='Цвет', description='', protected=False, user_hidden=False, for_list=False, for_details=True,for_new=False, report_user_hidden=True,  order=3)

    def __str__(self):
        return f'{self.emoj.value} {self.name.value}'

    @classmethod
    def _manager_shablons(cls)->'ShablonsRes|ShablonsEve':
        raise NotImplementedError
    def check_order_dates(self,*args,**kwargs)->bool:
        return True
    def get_protected_names(self)->list[str]:
        data:dict[str,_Attribute] = F.get_all_attrs_with_properties(self)
        return [k for k, v in data.items() if v.info.protected]
    def get_shablon(self)->ShablonRes:
        shabl_o = self._manager_shablons.get(self.shablon.value)
        if shabl_o is None:
            CQT.msgbox(f'Шаблон {self.shablon} не найден в DTSUB')
        return shabl_o

    def to_dump(self, attr_name) -> str:
        attr_value: _Attribute = getattr(self, attr_name)
        val = attr_value.value
        if attr_name == 'type_entity':
            val = val.serialize()
        if attr_name == 'color':
            val = val.serialize()
        if attr_name in ('start','end'):
            value:Cdt =val
            return value.to_db()

        if isinstance(val, (CSQ.SQLITE_TYPES)):
            return val
        else:
            try:
                val = val.serialize()
                return val
            except:
                pass
            raise Exception("Not supported")
    def to_ui(self, attr_name) -> str:
        attr_val: _Attribute = getattr(self, attr_name)
        if attr_name == 'shablon':
            return str(self.get_shablon())
        if attr_name == 'color':
            return ''
        if attr_name == 'for_delete':
            return  CEMOJ.СтатусыПроизводства.error.symbol  if attr_val.value else ''
        if attr_name in ('start','end'):
            value:Cdt =attr_val.value
            return value.to_string_ru_wo_s()
        return attr_val.value

    def to_service_val(self, attr_name) -> str:
        attr_val: _Attribute = getattr(self, attr_name)
        if attr_name == 'shablon':
            val:int = attr_val.value
            return val
        if attr_name in ('start','end'):
            value:Cdt =attr_val.value
            return value
        return attr_val.value


    def template_info(self)->dict:
        data:dict = F.get_all_attrs_with_properties(self)
        data = F.sort_dict_by_key(data,lambda k: data[k].info.order)
        return ({k :self.to_ui(k) for k,v in data.items() if  v.info.for_details} ,
                {k :self.to_service_val(k) for k,v in data.items() if  v.info.for_details} ,
                {k : v.info.alias_adduced for k,v in data.items()})

    def template(self)->dict:
        data = F.get_all_attrs_with_properties(self)
        data = F.sort_dict_by_key(data, lambda k: data[k].info.order)
        return ({k: self.to_ui(k) for k,v in data.items() if  v.info.for_list},
                {k: self.to_service_val(k) for k, v in data.items() if v.info.for_list},
                {k : v.info.alias_adduced for k,v in data.items()})


    def template_new(self)->tuple[list[dict],list[dict]]:
        attrs:list[tuple[str,_Attribute]] = [(k,_) for k, _ in F.get_all_attrs(self).items() if isinstance(_,_Attribute)]
        text = [{'_name':t[0],'_data': str(self.to_service_val(t[0])),'Параметр':t[1].info.alias,'Значение':self.to_ui(t[0])} for t in attrs if t[1].info.for_new]
        data = [{'_name':t[0],'_data': str(self.to_service_val(t[0])),'Параметр':t[1].info.alias,'Значение':self.to_service_val(t[0])} for t in attrs if t[1].info.for_new]
        return text, data

    def serialize(self)->dict[str]:
        data: dict = F.get_all_attrs(self)
        return {k: self.to_dump(k) for k, v in data.items()}

    def get_attr(self,name:str)->_Attribute:
        return getattr(self,name)


    def from_ui(self,attr_name, value):
        if attr_name == 'for_delete':
            return value
        if attr_name == 'color':
            if isinstance(value,str):
                try:
                    clr_o = Color(value)
                    return clr_o
                except:
                    pass
            if isinstance(value, Color):
                clr_o: Color = value
                return clr_o
            raise ValueError(f"Invalid color value: {value}")
        if attr_name in ('start', 'end'):
            value: Cdt = value
            if not isinstance(value, Cdt):
                print(f"Warning: {attr_name} is not a Cust_date")
                return Cdt()
            return value
        return value


    def set_data(self, data:dict[str,str])->tuple[bool,str]:
        if not  self.check_order_dates(data):
            return False, 'Не корректный порядок дат'
        fl = False
        err = 'Нет изменений'
        for k,v in data.items():
            attr = self.get_attr(k)
            if attr.info.protected:
                continue
            attr.set_value(self.from_ui(k,v))
            fl = True
        return fl ,err


class Resource(_BaseDimension):
    _TYPE_DIMENSION = Type_entitys.Res

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

    @property
    def _manager_shablons(self):
        return DTSUB.shablons_res
class Event(_BaseDimension):
    _TYPE_DIMENSION = Type_entitys.Eve


    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.start: _Attribute[Cdt] = _Attribute.attr(Cdt(),Cdt, alias='Начало', description='Начало события', protected=False,
                                                      user_hidden=False, for_list=True, for_details=True, for_new=False,
                                                      order=22)
        self.end: _Attribute[Cdt] = _Attribute.attr(Cdt(),Cdt, alias='Конец', description='Конец события', protected=False,
                                                      user_hidden=False, for_list=True, for_details=True, for_new=False,
                                                      order=23)
    def check_order_dates(self,data)->bool:
        start = self.start.value
        end = self.end.value
        if 'start' in data:
            start = data['start']
        if 'end' in data:
            end = data['end']
        if not end or not start:
            return True
        if  start < end:
            return True
        return False


    @property
    def _manager_shablons(self):
        return DTSUB.shablons_eve

class _BaseDimensions:
    _TYPE: Type_entity = None
    _TYPE_CLS:Resource|Event = None
    def __init__(self):
        self.dict_elems:dict[int,_TYPE_CLS] = dict()

    def get(self, id:int)->_TYPE_CLS:
        return self.dict_elems[id]

    def add(self, id:int, name, descr,id_shablon)->_TYPE_CLS:
        new_dim = self._TYPE_CLS(id_shablon,id,name,descr)
        self.dict_elems[id] = new_dim
        return new_dim

    def new(self,id_shablon:int, name='', descr='')->_TYPE_CLS:
        id = self._gen_new_id()
        new_dim = self._TYPE_CLS(id_shablon,id,name,descr)
        self.dict_elems[id] = new_dim
        return new_dim

    def _gen_new_id(self)->int:
        last_id = -1
        if self.dict_elems:
            last_id = max(list(self.dict_elems.keys()))
        return last_id + 1

    def to_dict(self) -> dict:
        return [it.serialize() for it in self.dict_elems.values()]

    @classmethod
    def from_dict(cls,lst_rows: list[dict]) -> '_TYPE_CLS':
        mnger = cls()
        for row in lst_rows:
            id = row['id']
            shablon_id = row['shablon']
            name = row['name']
            descr = row['descr']
            new_dim:_TYPE_CLS =  mnger.add(id,name,descr,shablon_id)
            new_dim.color.set_value(Color(row['color']))
            new_dim.emoj.set_value(row['emoj'])
            new_dim.for_delete.set_value(row['for_delete'])
        return mnger

    def template_list(self,include_deleted:bool=True)->tuple[list[dict],list[dict],dict] :
        accessed_shablons = [_ for _ in self.dict_elems.values() if not _.for_delete.value or include_deleted]
        if not accessed_shablons:
            return [], [], {}
        return ([_.template()[0] for _ in accessed_shablons],
                [_.template()[1] for _ in accessed_shablons],
                [_.template()[2] for _ in accessed_shablons][0])

class Resources(_BaseDimensions):
    _TYPE = Type_entitys.Res
    _TYPE_CLS = Resource

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

class Events(_BaseDimensions):
    _TYPE = Type_entitys.Eve
    _TYPE_CLS = Event

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
    @classmethod
    def from_dict(cls,lst_rows: list[dict]):
        mnger = super().from_dict(lst_rows)
        for row in lst_rows:
            id = row['id']
            new_dim:Event = mnger.get(id)
            start = Cdt()
            if 'start' in row:
                start = Cdt(row['start'])
            new_dim.start.set_value(start)
            end = Cdt()
            if 'end' in row:
                end = Cdt(row['end'])
            new_dim.end.set_value(end)
        return mnger


class Cross():
    def __init__(self,id_res,id_eve):
        self.id: _Attribute[int] = _Attribute.attr(-1,int, alias='№', description='', protected=True, user_hidden=True,
                                                   for_list=True, for_details=True, for_new=False, report_user_hidden=True, order=0)
        self.res: _Attribute[int] = _Attribute.attr(id_res,int, alias='Ресурс',description='',protected=True,user_hidden=False,for_list=True,for_details=True,for_new=True,report_user_hidden=True, order=1)
        self.eve: _Attribute[int] = _Attribute.attr(id_eve,int, alias='Событие',description='',protected=True,user_hidden=False,for_list=True,for_details=True,for_new=True,report_user_hidden=True, order=3)
        self.start_eve: _Attribute[None] = _Attribute.attr(None, None, alias='Начало соб.', description='Начало события', protected=True,
                                                      user_hidden=False, for_list=True, for_details=False, for_new=False, for_report=False,
                                                      order=22)
        self.end_eve: _Attribute[None] = _Attribute.attr(None, None, alias='Конец соб.', description='Конец события', protected=True,
                                                      user_hidden=False, for_list=True, for_details=False, for_new=False, for_report=False,
                                                      order=23)
        self.start: _Attribute[Cdt] = _Attribute.attr(Cdt(),Cdt, alias='С', description='Начало Участия', protected=False,
                                                      user_hidden=False, for_list=True, for_details=True, for_new=False,
                                                      order=25)
        self.end: _Attribute[Cdt] = _Attribute.attr(Cdt(),Cdt, alias='По', description='Конец Участия', protected=False,
                                                      user_hidden=False, for_list=True, for_details=True, for_new=False,
                                                      order=26)

    def __repr__(self):
        return f"Cross(res={self.res.value}, eve={self.eve.value})"

    def __hash__(self):
        return hash((self.res.value,self.eve.value))

    def _check_order_dates(self,data)->bool:
        start = self.start.value
        end = self.end.value
        if 'start' in data:
            start = data['start']
        if 'end' in data:
            end = data['end']
        if not end or not start:
            return True
        if  start < end:
            return True
        return False
    def from_ui(self,attr_name, value):

        if attr_name in ('start', 'end'):
            value: Cdt = value
            if not isinstance(value, Cdt):
                print(f"Warning: {attr_name} is not a Cust_date")
                return Cdt()
            return value
        return value

    def get_attr(self,name:str)->_Attribute:
        return getattr(self,name)

    def set_data(self, data:dict[str,str])->tuple[bool,str]:
        if not  self._check_order_dates(data):
            return False, 'Не корректный порядок дат'
        fl = False
        err = 'Нет изменений'
        for k,v in data.items():
            attr = self.get_attr(k)
            if attr.info.protected:
                continue
            attr.set_value(self.from_ui(k,v))
            fl = True
        return fl ,err

    def set_dates(self,start:str,end:str):
        self.start.set_value(Cdt(start))
        self.end.set_value(Cdt(end))

    def serialize(self)->dict[str]:
        data: dict = F.get_all_attrs(self)
        return {k: self.to_dump(k) for k, v in data.items()}

    def get_protected_names(self)->list[str]:
        data:dict[str,_Attribute] = F.get_all_attrs_with_properties(self)
        return [k for k, v in data.items() if v.info.protected]
    def to_dump(self, attr_name) -> str:
        attr_value: _Attribute = getattr(self, attr_name)
        val = attr_value.value

        if attr_name in ('start','end'):
            value:Cdt =val
            return value.to_db()

        if isinstance(val, (CSQ.SQLITE_TYPES)):
            return val
        else:
            try:
                val = val.serialize()
                return val
            except:
                pass
            raise Exception("Not supported")
    def to_ui(self, attr_name) -> str:
        attr_val: _Attribute = getattr(self, attr_name)

        if attr_name in ('start','end'):
            value:Cdt =attr_val.value
            return value.to_string_ru_wo_s()
        return attr_val.value

    def to_service_val(self, attr_name) -> str:
        attr_val: _Attribute = getattr(self, attr_name)

        if attr_name in ('start','end'):
            value:Cdt =attr_val.value
            return value
        return attr_val.value


    def template_info(self) -> dict:
        data: dict = F.get_all_attrs_with_properties(self)
        data = F.sort_dict_by_key(data, lambda k: data[k].info.order)
        return ({k: self.to_ui(k) for k, v in data.items() if v.info.for_details},
                {k: self.to_service_val(k) for k, v in data.items() if v.info.for_details},
                {k: v.info.alias_adduced for k, v in data.items()})

    def template_list(self) -> dict:
        data = F.get_all_attrs_with_properties(self)
        data = F.sort_dict_by_key(data, lambda k: data[k].info.order)
        return ({k: self.to_ui(k) for k, v in data.items() if v.info.for_list},
                {k: self.to_service_val(k) for k, v in data.items() if v.info.for_list},
                {k: v.info.alias_adduced for k, v in data.items()})

class Crosses():
    def __init__(self):
        self.dict_eve:dict[int,list[dict]]=dict()
        self.dict_res:dict[int,list[dict]]=dict()
        self.dict_crosses:dict[int,Cross]=dict()
        self.calc_dates()

    def get(self, id:int)->Cross|None:
        if id in self.dict_crosses:
            return self.dict_crosses[id]

    def calc_max(self)->dict[int,Cdt]:
        rez = dict()
        for id, data in self.dict_eve.items():
            tmp_data = []
            for it in data:
                cross:Cross = it['cross']
                if cross.start.value and cross.end.value:
                    tmp_data.append(cross.end.value)
            if tmp_data:
                rez[id] = max(tmp_data)
        return rez
    def calc_min(self)->dict[int,Cdt]:
        rez = dict()
        for id, data in self.dict_eve.items():
            tmp_data = []
            for it in data:
                cross:Cross = it['cross']
                if cross.start.value and cross.end.value:
                    tmp_data.append(cross.start.value)
            if tmp_data:
                rez[id] = min(tmp_data)
        return rez

    def _gen_new_id(self) -> int:
        last_id = -1
        if self.dict_crosses:
            last_id = max(list([_.id.value for _ in self.dict_crosses.values()]))
        return last_id + 1

    def load(self):
        data = ...

    def to_dict(self) -> dict:
        return [it.serialize() for it in self.dict_crosses.values()]
    @classmethod
    def from_dict(cls,lst_rows: list[dict]) -> 'Crosses':
        mnger = cls()
        for row in lst_rows:

            id = row['id']
            id_eve = row['eve']
            id_res = row['res']
            start = row['start']
            end = row['end']
            new_cross = mnger._add_cross(id_res, id_eve, id)
            new_cross.set_dates(start, end)
        mnger._reload_dict_dims()
        return mnger

    def calc_dates(self): #TODO расчет дат с приоритетом события( если не указана дата события, то берется крайние даты Участий)
        pass

    def _add_cross(self,id_res:int,id_ivent:int,id=-1)->Cross:
        cross = Cross(id_res, id_ivent)
        if id == -1:
            id = self._gen_new_id()

        self._insert_cross(id, cross)
        return cross

    def add(self,list_id_events:list[int],list_id_res:list[int])->bool:
        fl_add = False
        for id_ivent in list_id_events:
            for id_res in list_id_res:
                if self._is_exist_cross(id_res,id_ivent):
                    pass
                else:
                    self._add_cross(id_res, id_ivent)
                    fl_add = True
        if fl_add:
            self._reload_dict_dims()
        return fl_add

    def _is_exist_cross(self,id_res:int,id_ivent:int)->bool:
        for cross in self.dict_crosses.values():
            if cross.res.value == id_res and cross.eve.value == id_ivent:
                return True
        return False
    def _insert_cross(self,id:int,cross:Cross):
        cross.id.set_value(id,True)
        self.dict_crosses[id] = cross

    def _reload_dict_dims(self):
        data = [{'res':v.res.value,'eve':v.eve.value, 'cross':v} for v in self.dict_crosses.values()]
        self.dict_eve = F.grouping_list_dicts(data,'eve')
        self.dict_res = F.grouping_list_dicts(data,'res')

    def template_list(self,by_res:int=None,by_eve:int=None)->tuple[list[dict],list[dict],dict]:
        filtr = list(self.dict_crosses.keys())
        if by_res is not None:
            filtr = []
            if by_res in self.dict_res:
                filtr = [_['cross'].id.value for _ in self.dict_res[by_res]]
        if by_eve is not None:
            filtr = []
            if by_eve in self.dict_eve:
                filtr = [_['cross'].id.value for _ in self.dict_eve[by_eve]]

        data = [ _ for k,_ in self.dict_crosses.items() if k in filtr]

        if not data:
            return ([],[],{})
        return ([_.template_list()[0] for _ in data],
                [_.template_list()[1] for _ in data],
                [_.template_list()[2] for _ in data][0])

class CrossEntity():
    def __init__(self):
        self.res:_Attribute[Resource] = _Attribute.attr(None,Resource, alias='Ресурс', description='', protected=False,
                                                     user_hidden=False, for_list=True, for_details=True, for_new=True,
                                                     order=1)
        self.eve:_Attribute[Event]  = _Attribute.attr(None,Event, alias='Событие', description='', protected=False,
                                                     user_hidden=False, for_list=True, for_details=True, for_new=True,
                                                     order=5)
        self.res_sh:_Attribute[ShablonRes]  = _Attribute.attr(None,ShablonRes, alias='ШаблонРес', description='', protected=False,
                                                     user_hidden=False, for_list=True, for_details=True, for_new=True,
                                                     order=10)
        self.eve_sh:_Attribute[ShablonEve]  = _Attribute.attr(None,ShablonEve, alias='ШаблонСоб', description='', protected=False,
                                                     user_hidden=False, for_list=True, for_details=True, for_new=True,
                                                     order=15)
        self.cross:_Attribute[Cross]  = _Attribute.attr(None,Cross, alias='Участие', description='', protected=False,
                                                     user_hidden=False, for_list=True, for_details=True, for_new=True,
                                                     order=20)
        self.start: _Attribute[Cdt] = _Attribute.attr(None,Cdt, alias='Общее.Начало', description='', protected=False,
                                                     user_hidden=False, for_list=True, for_details=True, for_new=True,
                                                     order=25)
        self.end: _Attribute[Cdt] = _Attribute.attr(None,Cdt, alias='Общее.Конец', description='', protected=False,
                                                     user_hidden=False, for_list=True, for_details=True, for_new=True,
                                                     order=30)

    def full_name(self,cross_entity_attr_name,dim_attr_name)-> str:
        if dim_attr_name:
            return f'{cross_entity_attr_name}.{dim_attr_name}'
        return cross_entity_attr_name
    def full_alias(self,cross_entity_attr_name,dim_attr_name)-> str:
        at_cross_entity_attr_o = getattr(self,cross_entity_attr_name)
        dim_o = at_cross_entity_attr_o.value
        cross_entity_attr_alias = at_cross_entity_attr_o.info.alias
        attr_dim = getattr(dim_o,dim_attr_name)
        if isinstance(attr_dim,_Attribute) and attr_dim.info.alias:
            pref = ''
            if attr_dim.info.user_hidden:
                pref = '_'
            return f'{pref}{cross_entity_attr_alias}.{attr_dim.info.alias}'

        if cross_entity_attr_alias:
            return f'{cross_entity_attr_alias}'
        return dim_o.info.alias

    def template(self)->tuple[dict,dict,dict,dict]:
        dict_text = dict()
        dict_data = dict()
        dict_aliases = dict()
        dict_descr = dict()

        list_cross_entity_attrs = [(name,_) for name, _ in F.get_all_attrs(self).items() if isinstance(_,_Attribute) and _.info.for_report]
        list_cross_entity_attrs.sort(key= lambda k: k[1].info.order)

        for cross_entity_attr_name, cross_entity_attr_o in list_cross_entity_attrs:
            cross_entity_attr_alias = cross_entity_attr_o.info.alias
            if isinstance(cross_entity_attr_o.value,Cdt):
                dict_text[cross_entity_attr_name] = cross_entity_attr_o.value.to_string_ru_wo_s()
                dict_data[cross_entity_attr_name] = cross_entity_attr_o.value
                dict_descr[cross_entity_attr_name] = cross_entity_attr_o.info.description
                alias = cross_entity_attr_o.info.alias_adduced

                dict_aliases[cross_entity_attr_name] = alias
                continue


            list_data_fields = [(name,_) for name, _ in  F.get_all_attrs(cross_entity_attr_o.value).items() if isinstance(_ , _Attribute) and _.info.for_report]
            list_data_fields.sort(key= lambda k: k[1].info.order)
            for dim_attr_name, dim_o in list_data_fields:
                try:
                    val = cross_entity_attr_o.value.to_ui(dim_attr_name)
                except:
                    print(f'to_ui in {cross_entity_attr_o.value.__class__.__name__} not found')
                    val = dim_o.value
                    if isinstance(val,Cdt):
                        val = val.to_string_ru_wo_s()

                alias_full = self.full_alias(cross_entity_attr_name,dim_attr_name)

                name_full = self.full_name(cross_entity_attr_name,dim_attr_name)

                dict_aliases[name_full] = alias_full
                dict_text[name_full] = val
                dict_data[name_full] = dim_o.value
                dict_descr[name_full] = dim_o.info.description

        return dict_text,dict_data ,dict_descr, dict_aliases


    def __repr__(self):
        res_name = self.res.value.name.value if self.res.value else "None"
        eve_name = self.eve.value.name.value if self.eve.value else "None"

        start_str = self.start.value.to_string_ru() if self.start.value and self.start.value.dt else "None"
        end_str = self.end.value.to_string_ru() if self.end.value and self.end.value.dt else "None"

        return f"CrossEntity(res='{res_name}', eve='{eve_name}', start={start_str}, end={end_str})"


class CrossManager():
    @staticmethod
    def get_ordered_data(resources:Resources,events:Events,crosses:Crosses)->list[CrossEntity]:
        dict_crosses_min = crosses.calc_min()
        dict_crosses_max = crosses.calc_max()
        result = []
        for cross in crosses.dict_crosses.values():
            ent = CrossEntity()
            ent.res.set_value(resources.get(cross.res.value))
            if ent.res.value.for_delete.value:
                continue
            ent.eve.set_value(events.get(cross.eve.value))
            if ent.eve.value.for_delete.value:
                continue
            ent.res_sh.set_value(ent.res.value.get_shablon())
            ent.eve_sh.set_value(ent.eve.value.get_shablon())
            ent.cross.set_value(cross)

            if not ent.eve.value.start.value:
                if ent.eve.value.id.value in dict_crosses_min:
                    ent.start.set_value( dict_crosses_min[ent.eve.value.id.value])
            else:
                ent.start.set_value(ent.eve.value.start.value)

            if not ent.eve.value.end.value:
                if ent.eve.value.id.value in dict_crosses_max:
                    ent.end.set_value(dict_crosses_max[ent.eve.value.id.value])
            else:
                ent.end.set_value(ent.eve.value.end.value)

            if ent.start.value and ent.end.value:
                result.append(ent)
        result.sort(key=lambda x: x.start)
        return result

    @staticmethod
    def templates_pivot(list_crosses:list[CrossEntity],order_res:dict[int,int] = None)->tuple[list[dict],list[dict],list[dict],list[dict],dict,dict]:
        if not list_crosses:
            return ([],[],[],[],{},{})
        list_text_v_sub = []
        list_data_v_sub = []
        list_text = []
        list_data = []
        dict_aliases = dict()
        dict_descr = dict()

        dict_crosses:dict[tuple,CrossEntity] = {(_.res.value,_.eve.value):_ for _ in list_crosses}
        list_res:list[_Attribute[Resource]] = list(set([_.res for _ in list_crosses]))
        list_eve = list(set([_.eve for _ in list_crosses]))
        if not list_res:
            return ([],[],[],[],{},{})
        list_text_v_sub,list_data_v_sub,aliases = ([_.value.template()[0] for _ in list_res],
                                                   [_.value.template()[1] for _ in list_res],
                                                   [_.value.template()[2] for _ in list_res][0])
        dict_aliases = copy.deepcopy(aliases)
        [[dict_descr.update({k: v.info.description}) for k,v in F.get_all_attrs(_.value,attr_type=_Attribute).items()] for _ in list_res]
        dict_aliases['res.id'] =   list_crosses[0].full_alias('res','id')

        for at_res in list_res:
            res = at_res.value
            tmp_dict_text = {'res.id':res.to_ui('id')}
            tmp_dict_data = {'res.id':res.to_service_val('id')}


            for at_eve in list_eve:
                eve = at_eve.value
                val = ''
                cross = None
                if (res,eve) in dict_crosses:
                    cross = dict_crosses[(res,eve)]
                    val = f'{cross.start.value.to_string_ru_wo_s()} - {cross.end.value.to_string_ru_wo_s()}'
                tmp_dict_text[eve.to_service_val('id')] = val
                tmp_dict_data[eve.to_service_val('id')] = cross
                dict_aliases[eve.to_service_val('id')] = str(eve)
                dict_descr[eve.to_service_val('id')] = eve.to_ui('descr')
            list_text.append(tmp_dict_text)
            list_data.append(tmp_dict_data)
        if order_res:
            list_text.sort(key=lambda x:  order_res[x['res.id']] if x['res.id'] in order_res else 0)
            list_data.sort(key=lambda x:  order_res[x['res.id']] if x['res.id'] in order_res else 0)
            list_text_v_sub.sort(key=lambda x:  order_res[x['id']] if x['id'] in order_res else 0)
            list_data_v_sub.sort(key=lambda x:  order_res[x['id']] if x['id'] in order_res else 0)


        return  (list_text_v_sub,
                list_data_v_sub,
                list_text,
                list_data,
                dict_aliases,
                dict_descr)
    @staticmethod
    def templates(list_crosses:list[CrossEntity])->tuple[list[dict],list[dict],dict,dict]:
        if not list_crosses:
            return ([],[],[],{})
        return (
            [_.template()[0] for _ in list_crosses],
            [_.template()[1] for _ in list_crosses],
            [_.template()[2] for _ in list_crosses][0],
            [_.template()[3] for _ in list_crosses][0],
        )

    @staticmethod
    def get_cross_entity(resources:Resources,events:Events,crosses:Crosses,id_cross:int)->CrossEntity|None:
        ordered_data = CrossManager.get_ordered_data(resources=resources,events=events,crosses=crosses)
        for it in ordered_data:
            if it.cross.value.id.value == id_cross:
                return it

class Report():
    def __init__(self, name, descr,text):
        self.name = name
        self.descr = descr
        self.text = text

class Reports():
    table = Report("table", "", "Таблица")
    pivottable = Report("pivot_table", "", "Сводная таблица")
    gant = Report("gant", "", "Гант")

    @classmethod
    def template(cls):
        dict_attrs = F.get_all_attrs(cls)
        return  [_ for _ in dict_attrs.values() if isinstance(_,Report)]
    @classmethod
    def get_by_name(cls, name:str)->Report|None:
        for k,v in F.get_all_attrs(cls).items():
            if k == name:
                return v

class UserConfigSubPlanElement:
    def __init__(self, name:str, enable:bool, order:int):
        self.name = name
        self.enable = enable
        self.order = order

class UserConfigSubPlan:
    def __init__(self):
        self.oform_reports:dict[str,UserConfigSubPlanElement] = dict()

    def _gen_path(self,report:Report):
        user_dir = CQT.qt_tmp_dir()
        pathf = F.sep().join([user_dir, f'{report.name}.pickle'])
        return pathf
    def save_config(self,report:Report,data):
        dict_data = dict()
        tmp_list = []
        for it in data:
            tmp_list.append(UserConfigSubPlanElement(it['name'],it['enabled'],it['new_order']))
        tmp_list.sort(key=lambda x:x.order)
        for it in tmp_list:
            dict_data[it.name] = it


        F.save_file_pickle(self._gen_path(report),dict_data)
        self._apply_data(report,dict_data)


    def _apply_data(self,report:Report,data):
        self.oform_reports[report.name] = data

    def reload_config(self,report:Report):
        pathf = self._gen_path(report)
        data = dict()
        if F.existence_file_c(pathf):
            data = F.load_file_pickle(pathf)
        self._apply_data(report,data)
    def load_config(self):
        for report in F.get_all_attrs(Reports,attr_type=Report).values():

            pathf = self._gen_path(report)
            data = dict()
            if F.existence_file_c(pathf):
                data = F.load_file_pickle(pathf)
            self._apply_data(report,data)


