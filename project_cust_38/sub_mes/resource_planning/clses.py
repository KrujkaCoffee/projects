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
T = TypeVar("T")

DTSUB = DTCLS.module_manage_sub_app

class UiMode():
    LIST = "list"
    DETAILS = "details"
    NEW = "new"




@dataclass(slots=True, frozen=True)
class _AttributeInfo:
    type: type
    alias: str#для юзера
    description: str
    protected: bool=True#для юзера
    user_hidden: bool=False#для юзера аналог _
    for_list: bool = True#для списка
    for_details: bool= True#для деталировки
    for_new: bool = True#для создания
    order: int = 99999#для юзера
    for_report: bool = True#для отчета
    report_user_hidden: bool = False#для юзера аналог _


def __repr__(self):
    return f"_AttributeInfo(type={self.type.__name__}, alias='{self.alias}', desc='{self.description[:20]}{'...' if len(self.description) > 20 else ''}', protected={self.protected})"




@dataclass(slots=True)
class _Attribute(Generic[T]):
    info: _AttributeInfo
    value: T

    def set_value(self, value: T,forced: bool=False):
        if not forced and self.info.protected:
            return False
        if self.info.type != type(value):
            raise TypeError(f"Expected {self.info.type}, got {type(value)}")

        if self.info.type in (int, float):
            value = F.valm(value)
        if self.info.type is bool:
            value = F.boolm(value)
        if self.info.type is Cdt:
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

    def __repr__(self):
        return f"_Attribute({self.info.alias}={self.value})"

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
             report_user_hidden: bool = False

    ) -> '_Attribute[T]':

        return cls(
            info=_AttributeInfo(
                type=type_val,
                alias=alias,
                description=description,
                protected=protected,
                user_hidden=user_hidden,
                for_list=for_list,
                for_details=for_details,
                for_new=for_new,
                order=order,
                for_report = for_report,
                report_user_hidden = report_user_hidden
            ),
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

    def __init__(self,ui_tbl,ui_btn_ok,ui_btn_cancel):
        self._ui:CQT.QtWidgets.QTableWidget = ui_tbl
        self._ui_ok:CQT.QtWidgets.QPushButton = ui_btn_ok
        self._ui_cancel:CQT.QtWidgets.QPushButton = ui_btn_cancel
        self.t:CQT.TableContext = CQT.TableContext(self._ui)
        self._raw_data = None
        self._dict_data = None
        self.dict_aliases = None
        self.editable_val = None
        self.fnc_oform = None
        self.fnc_update_data = None
        self.protected_names:list|tuple|set = None
        self._ui_cancel.clicked.connect(self._fill_data)

    def clear(self):
        CQT.soft_clear_tbl(self.t.tbl)
        self._ui_ok.setEnabled(False)
        self._ui_cancel.setEnabled(False)
    def update_info(self,template:dict,dict_data:dict,editable_val:bool=False,dict_aliases:dict=None,
                    fnc_oform=None,fnc_update_data=None,fnc_edit_cells=None,protected_names=None):
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
        self.protected_names = protected_names
        self._fill_data()
        self._ui_ok.setEnabled(True)
        self._ui_cancel.setEnabled(True)
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
                print('Установка атрибута только через метод .set_value')
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
                {k : f'_{v.info.alias}' if v.info.user_hidden else v.info.alias for k,v in data.items()})

    def template(self)->dict:
        data = F.get_all_attrs_with_properties(self)
        data = F.sort_dict_by_key(data, lambda k: data[k].info.order)
        return ({k: self.to_ui(k) for k,v in data.items() if  v.info.for_list},
                {k: self.to_service_val(k) for k, v in data.items() if v.info.for_list},
                {k : f'_{v.info.alias}' if v.info.user_hidden else v.info.alias for k,v in data.items()})


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
                {k : f'_{v.info.alias}' if v.info.user_hidden else v.info.alias for k,v in data.items()})

    def template(self)->dict:
        data = F.get_all_attrs_with_properties(self)
        data = F.sort_dict_by_key(data, lambda k: data[k].info.order)
        return ({k: self.to_ui(k) for k,v in data.items() if  v.info.for_list},
                {k: self.to_service_val(k) for k, v in data.items() if v.info.for_list},
                {k : f'_{v.info.alias}' if v.info.user_hidden else v.info.alias for k,v in data.items()})

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
                {k: f'_{v.info.alias}' if v.info.user_hidden else v.info.alias for k, v in data.items()})

    def template_list(self) -> dict:
        data = F.get_all_attrs_with_properties(self)
        data = F.sort_dict_by_key(data, lambda k: data[k].info.order)
        return ({k: self.to_ui(k) for k, v in data.items() if v.info.for_list},
                {k: self.to_service_val(k) for k, v in data.items() if v.info.for_list},
                {k: f'_{v.info.alias}' if v.info.user_hidden else v.info.alias for k, v in data.items()})

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

    def template(self)->dict:
        dict_text = dict()
        dict_data = dict()
        dict_aliases = dict()

        list_cross_entity_attrs = [(name,_) for name, _ in F.get_all_attrs(self).items() if isinstance(_,_Attribute) and _.info.for_report]
        list_cross_entity_attrs.sort(key= lambda k: k[1].info.order)

        for cross_entity_attr_name, cross_entity_attr_o in list_cross_entity_attrs:
            cross_entity_attr_alias = cross_entity_attr_o.info.alias
            if isinstance(cross_entity_attr_o.value,Cdt):
                dict_text[cross_entity_attr_name] = cross_entity_attr_o.value.to_string_ru_wo_s()
                dict_data[cross_entity_attr_name] = cross_entity_attr_o.value
                alias = cross_entity_attr_o.info.alias
                if cross_entity_attr_o.info.report_user_hidden:
                    alias = f'_{alias}'
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

                alias_full = dim_o.info.alias
                name_full = dim_attr_name
                if cross_entity_attr_name:
                    alias_full = f'{cross_entity_attr_alias}'
                    name_full = cross_entity_attr_name
                    if dim_o.info.alias:
                        alias_full = f'{cross_entity_attr_alias}.{dim_o.info.alias}'
                        name_full = f'{cross_entity_attr_name}.{dim_attr_name}'
                if dim_o.info.report_user_hidden:
                    alias_full = f'_{alias_full}'
                dict_aliases[name_full] = alias_full
                dict_text[name_full] = val
                dict_data[name_full] = dim_o.value

        return dict_text,dict_data ,dict_aliases


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
    def templates(list_crosses:list[CrossEntity])->tuple[list[dict],list[dict],dict]:
        if not list_crosses:
            return ([],[],{})
        return (
            [_.template()[0] for _ in list_crosses],
            [_.template()[1] for _ in list_crosses],
            [_.template()[2] for _ in list_crosses][0],
        )


class Report():
    def __init__(self, name, descr,text):
        self.name = name
        self.descr = descr
        self.text = text

class Reports():
    table = Report("table", "", "Таблица")
    gant = Report("gant", "", "Гант")

    @classmethod
    def template(cls):
        dict_attrs = F.get_all_attrs(cls)
        return  [_ for _ in dict_attrs.values() if isinstance(_,Report)]