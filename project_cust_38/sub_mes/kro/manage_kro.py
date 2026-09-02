from __future__ import annotations

if __name__ == "__main__":
    import sys
    import os
    os.environ['MODIFIED_CFG'] = '{"BD_users": "SRV:BD_users.db"}'

import copy
import datetime
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_config as CFG
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_mes as CMS

import project_cust_38.Cust_emoji as CEMOJ
import project_cust_38.Cust_docs as CDCS
import project_cust_38.Cust_b24 as CB24
import project_cust_38.Cust_RichTextEditor as RTE
import project_cust_38.sub_mes.kro.kro_ui as kro_ui

from project_cust_38 import dynamic_db_models as DDM
from project_cust_38 import Cust_orm as CORM
from dataclasses import dataclass
from project_cust_38.sub_mes.kro.dataClass_kro import data_app as DTCLS
from typing import  TYPE_CHECKING

if TYPE_CHECKING:
    from Viewer import mywindow

if DTCLS.CONFIG.user_config.is_developer:
    CQT.convert_UI_into_PY_c(str(F.Cust_path(kro_ui)) + F.sep())

DTKRO = DTCLS.module_manage_kro
STORE = DTCLS.ReferenceStore



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

    def __bool__(self)->bool:
        if self.dt is None:
            return False
        return True

    def now(self)->Cdt:
        self.dt=F.now('')
        return self


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


    def __bool__(self):
        if self.dt is None or self.dt == '':
            return False
        return True


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

class Result_state():
    def __init__(self,id,name,text,emoj,for_all_approve):
        self.id: int = id
        self.text: str = text
        self.name: str = name
        self.emoj:str = emoj
        self.for_all_approve:bool = for_all_approve


    def as_row_ui(self)->str:
        return f'{self.emoj} {self.text}'

    def __repr__(self):
        return f"Result_state({self.id}, '{self.name}')"

class Result_states(_MiniManager):
    _child_class = Result_state
    none_state:Result_state = Result_state(0,'none_state', 'В работе', CEMOJ.EmojiMain.СтатусыПроизводства.idle.symbol,False)
    approved:Result_state = Result_state(1,'approved', 'Утверждена',CEMOJ.EmojiMain.СтатусыПроизводства.normal.symbol,True)
    rejected:Result_state = Result_state(2,'rejected', 'Отклонена',CEMOJ.EmojiMain.СтатусыПроизводства.stopped.symbol,False)
    for_delete:Result_state = Result_state(3,'for_delete', 'На удаление',CEMOJ.EmojiMain.СтатусыПроизводства.error.symbol,False)

    def __init__(self):
        pass



DTKRO.result_states = Result_states()



class Regime():
    def __init__(self,name,description,icon,tooltip,start_mode=False):
        #start_mode - показать в меню
        self.name = name
        self.description = description
        self.icon = icon
        self.tooltip = tooltip
        self.start_mode = start_mode
@dataclass
class Regimes():
    report:Regime = Regime('report','Отчет',CEMOJ.EmojiMain.ДокументыДанные.analysis.symbol,
                           'Просмотр КРО',True)
    edit:Regime = Regime('edit','Отчет',CEMOJ.EmojiMain.ДокументыДанные.document_sign.symbol,
                         'Подписание КРО',False)
    insert:Regime = Regime('insert','Занесение',CEMOJ.EmojiMain.ДокументыДанные.document_new.symbol,
                           'Создание КРО',True)


class Krowindow(CQT.QtWidgets.QMainWindow):
    def __init__(self,app_self,regime:Regime=Regimes.report,filter_mk:list|int|None=None):
        super(Krowindow, self).__init__()
        self.ui = kro_ui.Ui_KroWindow()
        self.ui.setupUi(self)
        self.NAME_MODULE_BASE = 'Создание КРО v0.1'
        self.app_self = app_self
        DTKRO.self_ui = self
        DTKRO.filter_mk = filter_mk
        self.set_regime(regime)
        if self.app_self:
            self.setStyleSheet(self.app_self.styleSheet())
        self.setAttribute(CQT.Qt.WA_DeleteOnClose)
        CQT.connect_to_resize(self, CMS.tmp_dir())
        CQT.load_resize_splitters(self, CQT.qt_tmp_dir())
        CQT.load_icons(self, 26,dir= str(F.Cust_path(kro_ui)) + F.sep() + 'icons'+  F.sep())
        DTCLS.CONFIG.user_config.set_sub_window_title(self)
        self.setWindowModality(CQT.Qt.ApplicationModal)
        DTCLS.init_data()
        self.load_regime_ui()

        #CONNECTS
        self.ui.btn_make_new.clicked.connect(self.make_new)
        self.ui.btn_edit.clicked.connect(self.edit_kro)
        self.ui.tbl_main.clicked.connect(lambda :self.select_element(None))
        self.ui.btn_add.clicked.connect(self.add_new_sub_item)
        self.ui.btn_del.clicked.connect(self.del_from_sub_item)
        self.ui.btn_ok.clicked.connect(self.save_kro)
        self.ui.tbl_list_kro.clicked.connect(self.load_kro_from_preview)
        self.ui.btn_exit.clicked.connect(self.exit)
        self.ui.btn_save_local_shablon.clicked.connect(self.save_local_shablon)
        self.ui.btn_load_local_shablon.clicked.connect(self.load_local_shablon)
        self.ui.btn_info_dates.clicked.connect(self.show_info_dates)
        self.ui.btn_chats.clicked.connect(self.show_chats)
        self.ui.btn_duplicate.clicked.connect(self.duplicate)
        self.ui.btn_save_as_file.clicked.connect(self.save_as_file)

    def keyReleaseEvent(self,e):
        key = e.key()
        mod = e.modifiers()

        if self.ui.tbl_tch.hasFocus():
            if key == 86 and mod == (CQT.QtCore.Qt.ControlModifier):
                self.paste_data_from_buffer()
                pass


    def closeEvent(self, event):
        if DTKRO.regime in (Regimes.edit, Regimes.insert):
            if not CQT.msgboxgYN(f"""Измененные данные потеряются, продолжить?"""):
                event.ignore()
                return
            if DTKRO.current_kro_o:
                block = DTKRO.current_kro_o.get_block()
                block.clear_block_for_user()

    def paste_data_from_buffer(self):
        t = CQT.TableContext(self.ui.tbl_tch)
        name, data = CQT.get_clipboard_data()
        if t.current_column_name() in ('before_file','after_file'):
            if name == 'files':
                self.on_file_dropped(t,t.current_row().i,t.tbl.currentColumn(),data[0])
            if name == 'image':
                file_founding = CQT.qimage_to_binary(data,'JPG')
                file_o =  self.get_file_o_by_curren_clmn(t.current_row(),t.current_column_name())
                self.check_and_apply_blob_file(file_founding, file_o,str(F.get_time_shtamp_c()),'.jpg')
                self.fill_tbl_deviations()

    def upd_regime_lbl(self):
        self.ui.lbl_regime.setText(f"{DTKRO.regime.icon} Основные данные ({DTKRO.regime.tooltip})")

    def set_regime(self,regime:Regime)->bool:
        DTKRO.regime = regime

        if DTKRO.regime is Regimes.insert:
            self.ui.btn_load_local_shablon.setEnabled(True)
            self.ui.btn_save_local_shablon.setEnabled(True)


        if DTKRO.regime is Regimes.edit:
            self.ui.btn_load_local_shablon.setEnabled(False)
            self.ui.btn_save_local_shablon.setEnabled(False)

            block = DTKRO.current_kro_o.get_block()
            if block.is_blocked(DTCLS.CONFIG.user_config.User):
                user_blocker_ref = block.user
                user_blocker_o = UserPh(user_blocker_ref)
                user_blocker_name = ''
                user_blocker_department = ''
                if user_blocker_o:
                    user_blocker_name = user_blocker_o.ФИОк
                    user_blocker_department = user_blocker_o.department.Наименование
                CQT.msgbox(f'{CEMOJ.Эмоции.confused.symbol} Блокировка объекта.\nC {block.date.to_string_ru()}\n'
                           f'на редактировании: {user_blocker_name}'
                           f'\n{user_blocker_department}',
                           icon_str='Information', app_self=self)
                return False
            block.set_block()

        if DTKRO.regime is Regimes.report:
            self.ui.btn_load_local_shablon.setEnabled(False)
            self.ui.btn_save_local_shablon.setEnabled(False)
            if not DTKRO.current_kro_o is None:
                block = DTKRO.current_kro_o.get_block()
                block.clear_block_for_user()
                DTKRO.current_kro_o.clear_action()

        self.upd_regime_lbl()
        return True

    @CQT.onerror
    def exit(self):
        if DTKRO.regime is Regimes.report:
            self.close()
        else:
            if DTKRO.regime in (Regimes.edit, Regimes.insert):
                if not CQT.msgboxgYN(f"""Измененные данные потеряются, продолжить?"""):
                    return

            if DTKRO.regime is Regimes.insert:
                self.set_regime(Regimes.report)
                self.load_regime_ui()
            else:
                self.set_regime(Regimes.report)
                self.load_kro_from_preview()


    @CQT.onerror
    def save_local_shablon(self):
        if DTKRO.regime is not Regimes.insert:
            CQT.msgbox("""Сохранять можно только новый документ!""",app_self=self)
            return
        path = CQT.f_dialog_save(self,'Сохрать черновик',CMS.load_tmp_path(Kro._TYPE_CLS_SHABLON),'*.pickle')
        if path == '.':
            return
        CMS.save_tmp_path(Kro._TYPE_CLS_SHABLON, path, True)
        F.save_file_pickle(path, {"data":DTKRO.current_kro_o,'version':Kro._VERSION_CLS,'type':Kro._TYPE_CLS_SHABLON})
        CQT.msgbox(f'Сохранено',time_life=1,app_self=self)

    @CQT.onerror
    def load_local_shablon(self):
        path = CQT.f_dialog_name(self, 'Выбрать черновик', CMS.load_tmp_path(Kro._TYPE_CLS_SHABLON), '*.pickle')
        if path == '.':
            return
        CMS.save_tmp_path(Kro._TYPE_CLS_SHABLON, path, True)
        try:
            data = F.load_file_pickle(path)
        except:
            CQT.msgbox("Файл повреждён или версия файла отличается от версии программы", app_self=self)
            return

        if not isinstance(data,dict) or 'type' not in data or  'version' not in data:
            CQT.msgbox("Файл повреждён или имеет стороннее происхождение",app_self=self)
            return
        if data['type'] != Kro._TYPE_CLS_SHABLON:
            CQT.msgbox("Файл имеет стороннее происхождение", app_self=self)
            return
        if data['version'] != Kro._VERSION_CLS:
            CQT.msgbox(f'Версия файла отличается от версии программы',app_self=self)
            return
        tmp_kro:Kro = data["data"]
        dict_mk = set([_["Номер МК"] for _ in self.load_list_accesed_mk()])

        if tmp_kro.mk not in dict_mk:
            CQT.msgbox(f"МК №{tmp_kro.mk} не доступна к выбору")
            return
        DTKRO.current_kro_o = tmp_kro
        DTKRO.current_kro_o.date= Cdt().now()
        DTKRO.current_kro_o.initiator= DTCLS.CONFIG.user_config.User.ID_ФизЛица
        self.load_kro(DTKRO.current_kro_o,True)
        CQT.msgbox(f'Загружено', time_life=1, app_self=self)

    @CQT.onerror
    def save_as_file(self):
        CQT.msgbox(f'Отключено - в разрботке')
        return


    @CQT.onerror
    def duplicate(self):
        CQT.msgbox(f'Отключено - в разрботке')
        return

    @CQT.onerror
    def show_chats(self):
        def fnc_oform(tbl:CQT.QtWidgets.QTableWidget, *args):#
            def fnc_dbl_ckick(t:CQT.TableContext,i:int,clmn_name,*args):
                if DTCLS.CONFIG.user_config.is_developer:
                    user_o = CMS.Emploee_usr('Беляков Антон Геннадьевич',DTCLS.CONFIG.project.db_users)
                else:
                    user_o = DTCLS.CONFIG.user_config.User

                link = t.get_row(i).value('_Ссылка')
                name = t.get_row(i).value('Тип')
                #template = CB24.MessageBuilder(f'[B]Привет {user_o.Имя}! Запрос ссылки на "{name}" выполнен.[/B]')
                #template.add_delimiter()  # Добавить разделитель
                #template.add_message(f'[URL={link}]{CEMOJ.EmojiMain.ОборудованиеИнструменты.link.symbol} Перейти в чат[/URL]')
                #template.add_delimiter()
                #template.add_message(f'Если возникнут вопросы, обращайся к администратору MES')
                #
                #template.send_by_chat_id(str(user_o.id_bitrix) )  # Итоговая отправка
                F.open_in_bitrix24(link)

            t = CQT.TableContext(tbl)
            for row in t.rows():
                row.set_color_font(*CMS.Colors.link_blue.rgb,col_name='Действие')


            t.add_column_events('Действие',on_double_click=fnc_dbl_ckick)
            t.hide_if_not_dev(DTCLS.CONFIG)

        list_chats = []
        for chat_type in F.get_all_attrs_with_properties(Chat_types).values():
            name, link = DTKRO.alerts.gen_link(chat_type)
            if link:
                list_chats.append({'Тип':name,
                                   '_Ссылка':link,
                                   'Действие':f'{CEMOJ.EmojiMain.ОборудованиеИнструменты.link.symbol} Получить ссылку в Б24'})
        if not list_chats:
            CQT.msgbox(f'Ссылкок на чаты нет')
            return
        CQT.msgboxg_get_table_ok_inf(self,"Чаты:",list_chats,func_oform_tbl=fnc_oform,styleSheet=CQT.MES_CSS)

    @CQT.onerror
    def show_info_dates(self):

        if DTKRO.current_kro_o is None :
            CQT.msgbox(f'Не выбрано КРО')
            return
        start_date_dt = DTKRO.current_kro_o.date.dt

        data = [{'Этап':'Создано','Дата':DTKRO.current_kro_o.date.to_string_ru(),'Автор': UserPh(DTKRO.current_kro_o.initiator),
                 'Дней':0}]
        for it in DTKRO.current_kro_o.list_agreements:
            if it.enabled:
                dates_diff = ''
                if it.date:
                    dates_diff = (it.date.dt - start_date_dt).days
                data.append({'Этап':it.description,'Дата':it.date.to_string_ru(),'Автор':UserPh(it.user_key) if it.user_key else '',
                 'Дней':dates_diff})
        dates_diff = ''
        if DTKRO.current_kro_o.result_state_date:
            dates_diff = (DTKRO.current_kro_o.result_state_date.dt - start_date_dt).days
        data.append({'Этап':'Итоговый\nстатус','Дата':DTKRO.current_kro_o.result_state_date.to_string_ru(),
                     'Автор':UserPh(DTKRO.current_kro_o.initiator),'Дней':dates_diff})
        CQT.msgboxg_get_table_ok_inf(self,'Журнал изменений:',data,styleSheet=CQT.MES_CSS)

    @CQT.onerror
    def save_kro(self):
        def err_warn(list_err):
            str_event_name = 'сохранения'
            if DTKRO.regime is Regimes.insert:
                str_event_name = 'создания'
            list_err.insert(0,'Ошибки заполненности полей')
            CQT.msgboxg_get_table_ok_inf(self,f'Ошибка {str_event_name}',list_err, styleSheet=CQT.MES_CSS,)
        kro_o = DTKRO.current_kro_o

        suc, list_err = kro_o.check_filling()
        if not suc:
            err_warn(list_err)
            return

        if DTKRO.regime is Regimes.insert:
            list_prewiew = [{"Параметр":'Этап','Значение':_.description} for _ in kro_o.list_agreements if _.enabled]
            list_prewiew.insert(0, {"Параметр": '', 'Значение': '          Этапы обязательные для согласования:'})
            list_prewiew.insert(0,{"Параметр":'Причина','Значение':kro_o.cause.text})
            list_prewiew.insert(0,{"Параметр":'Изделие','Значение':kro_o.nomen_name})
            if not CQT.msgboxg_get_table(self,   'Выбраны для согласования КРО:',
                                         list_prewiew ,
                                     styleSheet=CQT.MES_CSS,WindowTitle='Внимание!',show_filtr=False,
                                         btn0_name=f'✔ Продолжить',yesNoMode=True):
                return

        if not DTKRO.current_kro_o.is_changes():
            DTKRO.current_kro_o.get_block().clear_block_for_user()
            self.set_regime(Regimes.report)
            self.load_kro(DTKRO.current_kro_o)
            CQT.msgbox('Нет изменений')
            return

        suc, list_err = kro_o.save_db()
        if not suc:
            err_warn(list_err)
            return
        DTKRO.current_kro_o.get_block().clear_block_for_user()
        DTKRO.alerts.send_alert()
        self.set_regime(Regimes.report)
        self.load_list_kro()
        self.load_kro(DTKRO.current_kro_o)

    def sub_buttons_set_enabled(self,value=True):
        self.ui.btn_add.setEnabled(value)
        self.ui.btn_del.setEnabled(value)

    def load_regime_ui(self):
        self.set_current_tch()
        if DTKRO.regime is Regimes.insert:
            self.ui.fr_list.setVisible(False)
            self.make_new()
        else:
            self.ui.fr_list.setVisible(True)
            self.load_list_kro()


    def load_list_kro(self):
        DTKRO.kros.load_preview()
        template = DTKRO.kros.template()
        CQT.fill_wtabl(template,self.ui.tbl_list_kro,styleSheet=CQT.MES_CSS,auto_type=False,
                       selectionBehavior='SelectRows',selectionMode='SingleSelection',
                       aliases_header=Kros.ALIASES,list_column_widths=CMS.load_column_widths(self,self.ui.tbl_list_kro))
        spis_znach = ''
        if DTKRO.filter_mk:
            if isinstance(DTKRO.filter_mk,int):
                spis_znach = {'mk':str(DTKRO.filter_mk)}
            if isinstance(DTKRO.filter_mk, list):
                spis_znach = {'mk': '|'.join([str(_) for _ in DTKRO.filter_mk])}
        t = CQT.TableContext(self.ui.tbl_list_kro)
        t.hide_if_not_dev(DTCLS.CONFIG.user_config.is_developer)
        t.hide_if_not_dev(DTCLS.CONFIG.user_config.is_developer,forced_text=True)

        CQT.fill_filtr_c(self,self.ui.tbl_list_kro_filtr,self.ui.tbl_list_kro,show_header=False,spis_znach=spis_znach,
                         combo_dict={'result_state':None,'cur_user_agreement_state':None},
                         check_box_dict={'cause':None,'name_nd':None},
                         hidden_scroll=True)
        if spis_znach:
            CQT.apply_filtr_c(self,self.ui.tbl_list_kro_filtr,self.ui.tbl_list_kro,False)

    @CQT.onerror
    def duplicate_ui(self):
        if DTKRO.current_kro_o.result_state in (
                DTKRO.result_states.rejected,
                DTKRO.result_states.for_delete
                                                ):
            self.ui.btn_duplicate.setEnabled(True)
        else:
            self.ui.btn_duplicate.setEnabled(False)

    @CQT.onerror
    def load_kro_from_preview(self):
        if DTKRO.regime in (Regimes.edit, Regimes.insert):
            if not CQT.msgboxgYN(f"""Измененные данные потеряются, продолжить?"""):
                return

        self.set_regime( Regimes.report)
        t = CQT.TableContext(self.ui.tbl_list_kro)
        row = t.current_row()
        if row.no_selection:
            return
        id = int(row.value('id'))
        DTKRO.current_kro_o =  DTKRO.kros.load_one(id)
        self.load_kro(DTKRO.current_kro_o,True)
        self.duplicate_ui()
    @CQT.onerror
    def edit_kro(self):
        if DTKRO.current_kro_o is None:
            CQT.msgbox(f'Не выбрана строка КРО')
            return
        if DTKRO.current_kro_o.result_state in (Result_states.approved, Result_states.rejected, Result_states.for_delete):
            if DTCLS.CONFIG.user_config.User.ID_ФизЛица != DTKRO.current_kro_o.initiator:
                CQT.msgbox(f"Статус КРО '{DTKRO.current_kro_o.result_state.text}' не допускает изменения")
                return




        if not self.set_regime( Regimes.edit):
            return

        self.load_kro(DTKRO.current_kro_o, True)


        pass

    @CQT.onerror
    def make_new(self):
        self.set_regime( Regimes.insert)
        new_kro_o = DTKRO.kros.new()
        DTKRO.current_kro_o = new_kro_o
        self.load_kro(new_kro_o,True)

    def load_list_accesed_mk(self)->list[dict]:
        text = f"""
                SELECT знпр.№ERP,  
                    знпр.№проекта, plan.Пномер as "КПЛ",
                   status_poz.Имя AS "Статус КПЛ", plan.Позиция,  mk.Номенклатура as "Номенклатура МК", 
                    mk.Пномер as "Номер МК", "20" || mk.Дата AS "Дата МК", 
                     napravl_deyat.Псевдоним as "Направление МК",
                    mk.Количество as "Количество МК",
                    mk.Примечание as "Примечание МК",
                   status_poz.emoj AS _emoj,
                   status_poz.color AS _color
              FROM plan
                   INNER JOIN
                   napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности,
                   status_poz ON status_poz.Пномер = plan.Статус, 
                   mk ON mk.НомКплан == plan.Пномер, 
                  пл_оуп ON пл_оуп.НомПл = mk.НомКплан,  
                    знпр ON знпр.s_num = пл_оуп.Пномер_ЗП
             WHERE plan.Статус IN ( 3, 5, 7, 8) and mk.Статус == "Открыта" and plan.Пномер != 3345 and plan.poki = {DTCLS.CONFIG.place.poki}
            """
        list_mk = CSQ.custom_request_c(DTCLS.CONFIG.project.db_kplan, text, rez_dict=True,
                                       attach_dbs=DTCLS.CONFIG.project.db_naryad)
        return list_mk
        
    def load_kro(self,kro_o:Kro,reset_current_tch:bool=False):

        def fnc_select_mk(lbl:CQT.InteractiveLabelInstance,
                          self,i,j,row_o):
            def fnc_oform(tbl):
                t = CQT.TableContext(tbl)
                for row in t.rows():
                    clr_str = row.value('_color')
                    clr_o = CMS.Color(clr_str)
                    row.set_color_background(*clr_o.rgb,col_name="Статус КПЛ")
                t.hide_if_not_dev(DTCLS.CONFIG)


            list_mk = self.load_list_accesed_mk()

            for it in list_mk:
                emoji: CEMOJ.EmojiItem = eval(f'CEMOJ.EmojiMain.{it["_emoj"]}')
                it["Статус КПЛ"] = f'{emoji.symbol} {it["Статус КПЛ"]}'
                it["Дата МК"]= F.dateStrToStr(it["Дата МК"],"%Y-%m-%d","%d.%m.%Y",'')

            rez = CQT.msgboxg_get_table(self,f'Выбор МК',list_mk,showMaximized=True,selection_from_tbl=True,
                                  styleSheet=CQT.MES_EDIT_CSS,ExtendedSelection=False,selectRows=True,func_oform_tbl=fnc_oform)
            if not rez:
                return
            row_o.set_value('Значение',rez['Номер МК'])
            lbl.set_text(rez['Номер МК'])
            DTKRO.current_kro_o.mk = rez['Номер МК']

        def fnc_select_result_state(self,data,i:int,j:int,*args,**kwargs):
            t = CQT.TableContext(self.ui.tbl_main)
            row = t.get_row(i)
            row.set_value('Значение',data)
            DTKRO.current_kro_o.set_result_state(DTKRO.result_states.as_dict[data])



        def fnc_select_state_agreement(self,data,i:int,j:int,addit_data:CQT.TableContext,*args,**kwargs):
            t = addit_data
            row = t.get_row(i)
            row.set_value('agreement_state',data)
            id  = int(row.value('id'))
            agr_o =DTKRO.current_kro_o.get_agreement(id)
            DTKRO.current_kro_o.set_agereement_state(DTKRO.states_agreement.as_dict[data],agr_o,
                                                     DTCLS.CONFIG.user_config.User.ID_ФизЛица,
                                                     DTCLS.CONFIG.user_config.User.ФИОк)

            self.load_kro(DTKRO.current_kro_o)

        def fnc_select_cause(self,data,i:int,j:int,*args,**kwargs):
            t = CQT.TableContext(self.ui.tbl_main)
            row = t.get_row(i)
            row.set_value('Значение',data)
            DTKRO.current_kro_o.cause = data

        def fnc_swipe(sub_self, tbl:CQT.QtWidgets.QTableWidget, val:bool, i:int,j:int, *args):
            t = CQT.TableContext(tbl)
            row = t.get_row(i)
            row.set_value(t.name_by_idx(j),str(val))
            if not val:
                row.set_color_font(*CMS.Colors.dull_black.rgb)
            else:
                row.set_color_font(*CMS.Colors.black.rgb)
            kro_o = DTKRO.current_kro_o
            id_agr = int(row.value('id'))
            agree_o = kro_o.get_agreement(id_agr)
            agree_o.enabled = val

        def fnc_cell_edit(tbl:CQT.QtWidgets.QTableWidget,item:CQT.QtWidgets.QTableWidgetItem ,add_data=None):
            t = CQT.TableContext(tbl)
            clnm_name = t.name_by_idx(item.column())
            if clnm_name == 'Значение':
                row = t.get_row(item.row())
                name_row = row.value("_name")
                if name_row == 'complects':
                    val = row.value(clnm_name)
                    DTKRO.current_kro_o.complects = val
                    return True


            return False


       
        template = kro_o.get_template_main()

        CQT.fill_wtabl(template, self.ui.tbl_main,styleSheet=CQT.MES_EDIT_CSS,auto_type=False,
                       list_column_widths=CMS.load_column_widths(self,self.ui.tbl_main),
                       aliases_header=Agreement.ALIASES)
        t = CQT.TableContext(self.ui.tbl_main)


        CQT.connect_cell_edit(t.tbl, fnc_cell_edit)

        field_val_str_name = 'Значение'

        for row in t.rows():
            name_row = row.value('_name')
            val = row.value(field_val_str_name)
            if name_row == 'mk' and val=='':
                if DTKRO.regime is Regimes.insert:

                    widg = CQT.add_interactive_label(t.tbl, row.i, t.nf[field_val_str_name], val,
                                                     parent_self=self, grab_style_from_cell=True)
                    widg.add_button('', 'Выбор МК',
                                    fnc_select_mk,
                                    cell_val=row, img_path=F.sep().join([F.path_to_caller_file_c(),
                                                                          'icons', 'btn_select']))

            if name_row == 'complects':
                pass #fnc_cell_edit
            if name_row == 'result_state':
                current_text = None
                if F.is_numeric(val) and int(val) in DTKRO.result_states.as_dict:
                    current_text = DTKRO.result_states.as_dict[int(val)].text
                if DTKRO.current_kro_o.filled_agreements:
                    list_result_states = [_.text for _ in DTKRO.result_states.as_dict.values()]
                    list_data = [_.id for _ in DTKRO.result_states.as_dict.values()]
                else:
                    list_result_states = [_.text for _ in DTKRO.result_states.as_dict.values() if not _.for_all_approve]
                    list_data = [_.id for _ in DTKRO.result_states.as_dict.values() if not _.for_all_approve]
                CQT.add_combobox(self, t.tbl, row.i, t.nf[field_val_str_name], list_result_states
                                 , False,
                                 fnc_select_result_state,
                                 list_data=list_data, return_data=True,
                                 current_text=current_text,
                                 enabled=DTKRO.regime is Regimes.edit
                                 and (DTCLS.CONFIG.user_config.User.ID_ФизЛица == DTKRO.current_kro_o.initiator or DTCLS.CONFIG.user_config.is_developer))

            if name_row == 'cause':
                current_text = None
                if F.is_numeric(val) and int(val) in STORE.DICT_KroCauses:
                    current_text = STORE.DICT_KroCauses[int(val)].text

                CQT.add_combobox(self,t.tbl,row.i,t.nf[field_val_str_name],[_.text for _ in STORE.DICT_KroCauses.values()],False,
                                 fnc_select_cause,list_data=[_ for _  in STORE.DICT_KroCauses.keys()],return_data=True,
                                 current_text=current_text,enabled=DTKRO.regime is Regimes.insert)
            if name_row == 'list_agreements':
                t_sub = row.value(field_val_str_name, sub_table=True,as_table_context=True)
                for row_sub in t_sub.rows():

                    CQT.add_check_box_switcher(row_sub.tbl,row_sub.i,t_sub.nf['enabled'],F.boolm(row_sub.value('enabled')),
                                               fnc_swipe,self,enabled=DTKRO.regime is Regimes.insert)

                    state_agrement_int = int(row_sub.value('agreement_state'))
                    current_text = None
                    if F.is_numeric(state_agrement_int) and int(state_agrement_int) in DTKRO.states_agreement.as_dict:
                        current_text = DTKRO.states_agreement.as_dict[int(state_agrement_int)].as_row_ui()

                    CQT.add_combobox(self, t_sub.tbl, row_sub.i, t_sub.nf['agreement_state'],
                                     [_.as_row_ui() for _ in DTKRO.states_agreement.as_dict.values()], False,
                                     fnc_select_state_agreement,
                                     list_data=[_.id for _ in DTKRO.states_agreement.as_dict.values()], return_data=True,
                                     current_text=current_text,addit_data=t_sub,
                                     enabled= (DTKRO.regime is  Regimes.edit) and F.boolm(row_sub.value('enabled'))
                                     and F.boolm(row_sub.value('permition')) )

                    if not F.boolm(row_sub.value('enabled')):
                        row_sub.set_color_font(*CMS.Colors.dull_black.rgb)

                    if F.boolm(row_sub.value('permition')):
                        row_sub.set_value('permition', CEMOJ.EmojiMain.ПерсоналРоли.key.symbol)
                    else:
                        row_sub.set_value('permition',  CEMOJ.EmojiMain.СтатусыПроизводства.not_allowed.symbol)


                t_sub.hide_if_not_dev(DTCLS.CONFIG.user_config.is_developer,True)
                CQT.connect_cell_edit(t_sub.tbl, fnc_cell_edit)
                t_sub.tbl.clicked.connect(lambda :self.select_element(t_sub.tbl))




        t.set_editable(field_val_str_name,DTKRO.regime is Regimes.insert)
        for row in t.rows():
            name_row = row.value('_name')
            text_row = row.value('Параметр')
            val = row.value(field_val_str_name)
            if name_row in ('tbl_nomens','tbl_deviations'):
                row.set_editable(field_val_str_name,False)
            if text_row.startswith('_'):
                if not DTCLS.CONFIG.user_config.is_developer:
                    row.hide()

        t.hide_if_not_dev(DTCLS.CONFIG)
        #CQT.fill_wtabl(template_nomen, self.ui.tbl_viev_etaps_name)
        if reset_current_tch:
            self.set_current_tch()




    def ________________nomen___________________():pass
    def oform_nomens(self):
        def fnc_open_docs(lbl:CQT.InteractiveLabelInstance,self_ui,i,j,nomen_o: Nomen, *args):
            if nomen_o.docs_link:
                CMS.run_link_DOCs_c('','','',link= nomen_o.docs_link)
                #F.run_file_os_c(nomen_o.docs_link,False)
            else:
                CQT.msgbox("Нет ссылки на документы!",app_self=self)

        def fnc_select_dse(lbl:CQT.InteractiveLabelInstance,self_ui,i,j,nomen_o: Nomen, *args):

            id_mk = DTKRO.current_kro_o.mk
            if id_mk is None:
                CQT.msgbox(f'МК не выбрана',app_self=self)
                return

            res = CMS.ResSpec(id_mk)

            def fnc_oform_nomen(tbl:CQT.QtWidgets.QTableWidget,*args):
                pass

            list_dse = [{"Номерпп":_.Номерпп,
                         "Наименование": f"{'    '*_.Уровень} {_.emoj_item} {_.Наименование}",
                         "Номенклатурный номер": '    '*_.Уровень + _.Номенклатурный_номер,
                         "Количество":_.Количество,"Прим":_.Прим} for _ in res.data]

            rez = CQT.msgboxg_get_table(self_ui,'Выбор ДСЕ',list_dse,styleSheet=CQT.MES_CSS,selectRows=True,
                                  ExtendedSelection=False,
                                  selection_from_tbl=True,func_oform_tbl=fnc_oform_nomen)
            if not rez:
                return
            id = int(rez['Номерпп'])
            selected_it = res.get_dse(id)
            head_nomen = res.mk.Номенклатура
            nomen_o.id_dse = selected_it.Номерпп
            nomen_o.head_nomen = head_nomen
            nomen_o.nn = selected_it.Номенклатурный_номер
            nomen_o.name = selected_it.Наименование
            nomen_o.dse_emoj = selected_it.emoj_item
            nomen_o.docs_link = selected_it.Ссылка
            self.fill_tbl_nomens()
            pass


        t = CQT.TableContext(self.ui.tbl_tch)
        if DTKRO.regime is not Regimes.insert:
            for row in t.rows():
                val = row.value('nn')
                it_nomen = DTKRO.current_kro_o.get_nomen(int(row.value('order')))
                widg = CQT.add_interactive_label(t.tbl, row.i, t.nf['nn'], val,
                                                 parent_self=self, grab_style_from_cell=True)

                if val:
                    widg.add_button('', 'Открыть документ в Docs',
                                    fnc_open_docs,
                                    cell_val=it_nomen, img_path=F.sep().join([F.path_to_caller_file_c(),
                                                                              'icons', 'btn_show']))
            return
        else:
            t.set_editable('count')
            t.set_editable('pozition')
            for row in t.rows():
                val = row.value('nn')
                it_nomen = DTKRO.current_kro_o.get_nomen(int(row.value('order')))
                widg = CQT.add_interactive_label(t.tbl, row.i, t.nf['nn'], val,
                                                 parent_self=self, grab_style_from_cell=True)
                widg.add_button('', 'Выбор ДСЕ',
                                fnc_select_dse,
                                cell_val=it_nomen, img_path=F.sep().join([F.path_to_caller_file_c(),
                                                                     'icons', 'btn_select']))
                if val:
                    widg.add_button('', 'Открыть документ в Docs',
                                    fnc_open_docs,
                                    cell_val=it_nomen, img_path=F.sep().join([F.path_to_caller_file_c(),
                                                                              'icons', 'btn_show']))


        def corr_mk(tbl: CQT.QtWidgets.QTableWidget, item: CQT.QtWidgets.QTableWidgetItem , add_data=None)-> bool:
            t = CQT.TableContext(tbl)
            clnm_name = t.name_by_idx(item.column())
            row = t.get_row(item.row())
            id_nomen = int(row.value('order'))
            nomen_o = DTKRO.current_kro_o.get_nomen(id_nomen)
            val = row.value(clnm_name)
            if clnm_name == 'count':
                if not F.is_numeric(val):
                    CQT.msgbox(f'Не число',app_self=self)
                    return False
                nomen_o.count = int(val)
            if clnm_name=="pozition":
                nomen_o.pozition = val.strip()
            return True

        CQT.connect_cell_edit(t.tbl,corr_mk)

    def fill_tbl_nomens(self):
        DTKRO.self_ui.fill_sub_tbl(DTKRO.current_kro_o.get_template_nomen(), Nomen.ALIASES)
        self.oform_nomens()


    def ________________deviations___________________():pass

    def run_doc(self,file_data ,ext: str)->str:
        tmp_win_dir = F.save_tmp_win_dir_file(file_data, extention=ext)
        F.run_file_c(tmp_win_dir)
        return tmp_win_dir

    @staticmethod
    def fnc_show_img(lbl: CQT.InteractiveLabelInstance, self_ui, i, j, name_field: str, *args):
        t = CQT.TableContext(self_ui.ui.tbl_tch)
        row = t.get_row(i)
        deviation_o = DTKRO.current_kro_o.get_deviation(int(row.value('order')))
        name_field = t.name_by_idx(j)
        if name_field == 'before_file':
            file_o = deviation_o.before_file
        else:
            file_o = deviation_o.after_file

        ext = file_o.extension

        if file_o.size_packed_bytes:
            unpacked_file = F.unpack_byte_file(file_o.byte_data_packed)
            if not file_o.tmp_win_dir_file:
                file_o.tmp_win_dir_file = F.save_tmp_win_dir_file(unpacked_file, extention=ext)
            F.run_file_c(file_o.tmp_win_dir_file)

    def fill_tbl_deviations(self):
        DTKRO.self_ui.fill_sub_tbl(DTKRO.current_kro_o.get_template_deviations(), Deviantion.ALIASES)
        self.oform_deviations()

    def load_file(self, path: str|None, file_o: File_kro) -> bool | None:
        if path is None:
            file_o.clear()
            return
        path_o = F.Cust_path(path)
        if path_o.extension not in File_kro.ACCEPTABLE_EXTENTION_FILES_FOR_LOAD_INTO_DB:
            CQT.msgbox(f"Недопустимый тип файлов", app_self=self)
            return False
        CMS.save_tmp_path('file_kro', path, True)
        file_founding = F.load_file_convert_to_binary(path)
        name_user = path_o.stem
        extension = path_o.extension
        return self.check_and_apply_blob_file(file_founding,file_o,name_user,extension)


    @staticmethod
    def check_and_apply_blob_file(file_founding:bytes,file_o:File_kro,name_user:str,extension:str)->bool:
        if F.get_size_of_object(file_founding) > 1048576:
            file_founding = ''
            CQT.msgbox(f'Размер файла должен быть не более 1 мб', app_self=DTKRO.self_ui)
            return False
        file_founding_packed = F.pack_byte_file(file_founding)

        file_o.size_packed_bytes = F.get_size_of_object(file_founding_packed)
        file_o.name_user = name_user
        file_o.extension = extension

        file_o.byte_data_packed = file_founding_packed
        file_o.tmp_win_dir_file = None
        return True

    @staticmethod
    def get_file_o_by_curren_clmn(row:CQT.TableRow,name_field:str)->File_kro:

        deviation_o = DTKRO.current_kro_o.get_deviation(int(row.value('order')))
        if name_field == 'before_file':
            file_o = deviation_o.before_file
        else:
            file_o = deviation_o.after_file
        return file_o


    @staticmethod
    def fnc_delete_img(lbl: CQT.InteractiveLabelInstance, self_ui, i, j, name_field: str, path: str | None = None,
                       *args):
        t = CQT.TableContext(self_ui.ui.tbl_tch)
        row = t.get_row(i)
        file_o = self_ui.get_file_o_by_curren_clmn(row,name_field)

        self_ui.load_file(None, file_o)
        self_ui.fill_tbl_deviations()


    @staticmethod
    def fnc_select_img(lbl: CQT.InteractiveLabelInstance, self_ui, i, j, name_field: str, path: str | None = None,
                       *args):
        if path is None:
            str_ext_names = ', '.join([_ for _ in File_kro.ACCEPTABLE_EXTENTION_FILES_FOR_LOAD_INTO_DB.values()])
            str_ext_vals = ';'.join([f'*{_}' for _ in File_kro.ACCEPTABLE_EXTENTION_FILES_FOR_LOAD_INTO_DB.keys()])
            path = CQT.f_dialog_name(self_ui, 'Выбрать файл', CMS.load_tmp_path('file_kro'),
                                     f"{str_ext_names} files ({str_ext_vals})")
            if path == '.':
                return
        t = CQT.TableContext(self_ui.ui.tbl_tch)
        row = t.get_row(i)
        file_o = self_ui.get_file_o_by_curren_clmn(row, name_field)
        bytes_file = self_ui.load_file(path, file_o)
        if bytes_file is None or not bytes_file:
            return
        self_ui.fill_tbl_deviations()

    def on_file_dropped(self,t: CQT.TableContext, row: int, col: int, file_path: str):
        row_o = t.get_row(row)
        clmn_name = t.name_by_idx(col)
        lbl = row_o.widget(clmn_name)

        self.fnc_select_img(lbl,self,row,col,clmn_name,file_path)

    def oform_deviations(self):


        def fnc_plain_text(lbl: CQT.InteractiveLabelInstance, self_ui, i, j, name_field: str, *args):
            def fnc_validate(text_html: str, plain_text: str, *args) -> bool:
                if not plain_text.strip():
                    return True, None
                return True,text_html

            t = CQT.TableContext(self_ui.ui.tbl_tch)
            row = t.get_row(i)
            deviation_o = DTKRO.current_kro_o.get_deviation(int(row.value('order')))



            initial_view = CQT.RichTextViewMode.VIEW_ONLY
            placeholder_text = "Описание"
            msg = "Описание (Просмотр):"
            start_html = f"Тут ничего не написали {CEMOJ.Эмоции.confused.symbol}"
            if DTKRO.regime is Regimes.insert:
                initial_view = CQT.RichTextViewMode.EDIT
                placeholder_text = "Опишите ситуацию..."
                msg = "Введите описание:"
                start_html = "<p>Введите <b>описание</b> изменения</p>"

            if name_field == 'before_file':
                if deviation_o.describe_before:
                    start_html = deviation_o.describe_before
            if name_field == 'after_file':
                if deviation_o.describe_after:
                    start_html = deviation_o.describe_after

            rez, html = CQT.get_dialog_choose_rich_text(
                self_ui,
                msg=msg,
                start_html=start_html,
                placeholder_text=placeholder_text,
                func_validate=fnc_validate,
                initial_view= initial_view,

            )

            if not  rez:
                return

            if DTKRO.regime is Regimes.insert:
                if name_field == 'before_file':
                    deviation_o.describe_before = html
                if name_field == 'after_file':
                    deviation_o.describe_after = html
                self_ui.fill_tbl_deviations()

        def add_widg_select_file(name_clmn:str):
            val = row.value(name_clmn)
            # it_deviation = DTKRO.current_kro_o.get_deviation(int(row.value('order')))
            widg = CQT.add_interactive_label(t.tbl, row.i, t.nf[name_clmn], val,
                                             parent_self=self, grab_style_from_cell=True)
            widg.add_button('', 'Просмотр файла',
                            self.fnc_show_img,
                            cell_val=name_clmn, img_path=F.sep().join([F.path_to_caller_file_c(),
                                                                       'icons', 'btn_show']))
            tooltip = 'Просмотр описания'
            if DTKRO.regime is Regimes.insert:
                tooltip = 'Описание'
                widg.add_button('', 'Выбор Файла',
                            self.fnc_select_img,
                            cell_val=name_clmn, img_path=F.sep().join([F.path_to_caller_file_c(),
                                                                          'icons', 'btn_select']))

                widg.add_button('', 'Очистка Файла',
                            self.fnc_delete_img,
                            cell_val=name_clmn, img_path=F.sep().join([F.path_to_caller_file_c(),
                                                                          'icons', 'btn_delete']))

            widg.add_button('', tooltip,
                            fnc_plain_text,
                            cell_val=name_clmn, img_path=F.sep().join([F.path_to_caller_file_c(),
                                                                       'icons', 'btn_rich_text']))




        t = CQT.TableContext(self.ui.tbl_tch)
        if DTKRO.regime is  Regimes.insert:
            t.set_editable('before')
            t.set_editable('after')

        for row in t.rows():
            add_widg_select_file('before_file')
            add_widg_select_file('after_file')




        if DTKRO.regime is Regimes.insert:
            t.add_file_drop(self.on_file_dropped, column_name="before_file")
            t.add_file_drop(self.on_file_dropped, column_name="after_file")



        def corr_mk(tbl: CQT.QtWidgets.QTableWidget, item: CQT.QtWidgets.QTableWidgetItem , add_data=None)-> bool:
            t = CQT.TableContext(tbl)
            clnm_name = t.name_by_idx(item.column())
            row = t.get_row(item.row())
            id_dev = int(row.value('order'))
            dev_o = DTKRO.current_kro_o.get_deviation(id_dev)
            val = row.value(clnm_name)
            if clnm_name == 'before':
                dev_o.before = val
                return True
            if clnm_name == 'after':
                dev_o.after = val
                return True
            return False

        CQT.connect_cell_edit(t.tbl,corr_mk)



    def ________________agreements___________________():pass


    def oform_agreement(self,agr_o:Agreement):
        def fnc_edit(self:Krowindow,text:str,i,j, addit_data, *args):
            row:CQT.TableRow = addit_data['row']
            t:CQT.TableContext = addit_data['t']
            with CQT.table_updating(t):
                row.set_value(t.name_by_idx(j),text)
            DTKRO.current_agreement_o.comment =  text
            DTKRO.current_kro_o._set_action(Completed_actions.change_agreemtent_text, agreement=DTKRO.current_agreement_o)
            self.load_kro(DTKRO.current_kro_o)

        t = CQT.TableContext(self.ui.tbl_tch)
        t.set_rows_height(t.tbl.height())
        t.set_editable('comment')
        t.tbl.verticalHeader().hide()
        for row in t.rows():
            plain_text = CQT.add_plaintext(self,t.tbl,row.i,0,fnc_edit, addit_data={'t':t,'row':row},current_text= row.value('comment'),
                              placeholder= Agreement.ALIASES['comment'])
            fnt = plain_text.font()
            fnt.setPointSize(16)
            plain_text.setFont(fnt)
            plain_text.setEnabled((DTKRO.regime is  Regimes.edit) and agr_o.enabled and agr_o.permition)


    def fill_tbl_agr_comment(self,agr_o:Agreement):

        DTKRO.self_ui.fill_sub_tbl(agr_o.template_comment(), Agreement.ALIASES)
        self.oform_agreement(agr_o)

    def ________________common___________________():pass

    @CQT.onerror
    def add_new_sub_item(self):
        if DTKRO.current_main_elem == 'tbl_nomens':
            DTKRO.current_kro_o.insert_nomen()
            self.fill_tbl_nomens()
            self.load_kro(DTKRO.current_kro_o)

        if DTKRO.current_main_elem == 'tbl_deviations':
            DTKRO.current_kro_o.insert_deviation()
            self.fill_tbl_deviations()
            self.load_kro(DTKRO.current_kro_o)

    @CQT.onerror
    def del_from_sub_item(self):
        t = CQT.TableContext(self.ui.tbl_tch)
        row = t.current_row()
        if row.no_selection:
            return
        if DTKRO.current_main_elem == 'tbl_nomens':
            id_nomen = int(row.value("order"))
            if not CQT.msgboxgYN(f"удалить строку №{id_nomen}?"):
                return
            DTKRO.current_kro_o.delete_nomen(id_nomen)
            self.fill_tbl_nomens()
        if DTKRO.current_main_elem == 'tbl_deviations':
            id_deviation = int(row.value("order"))
            if not CQT.msgboxgYN(f"удалить строку №{id_deviation}?"):
                return
            DTKRO.current_kro_o.delete_deviation(id_deviation)
            self.fill_tbl_deviations()


    def set_current_tch(self, name: str | None=None,aliases:dict|None=None,addit_str:str = ''):
        self.ui.fr_tch_inf.setEnabled(not name is None)
        self.sub_buttons_set_enabled(False)
        DTKRO.current_main_elem = name
        alias = ''
        if name is None:
            self.fill_sub_tbl()
            self.ui.lbl_current_name_tch.setText('')
            return

        if name in Kros.ALIASES:
            alias = Kros.ALIASES[name]
        if name in Agreement.ALIASES:
            alias = Agreement.ALIASES[name]

        self.ui.lbl_current_name_tch.setText(alias + addit_str)



    def fill_sub_tbl(self,data:list[dict]|None = None,aliases:dict | None=None):
        if data is None:
            CQT.clear_tbl(self.ui.tbl_tch)
            return 
        CQT.fill_wtabl(data,self.ui.tbl_tch,styleSheet=CQT.MES_EDIT_CSS,aliases_header=aliases,auto_type=False,
                       list_column_widths=CMS.load_column_widths(self,self.ui.tbl_tch))

    @CQT.onerror
    def select_element(self,sub_tbl:CQT.QtWidgets.QTableWidget|None = None):

        def blink(name_row:str|CQT.QtWidgets.QPushButton):
            if isinstance(name_row,str):
                CQT.migat(self, DTKRO.self_ui.ui.tbl_main,
                      t.find_row({'_name': name_row}, True).i, t.nf['Параметр'],
                      1, clr=CMS.Colors.red_blinking.rgb)
            else:
                try:
                    CQT.blink_widget_border(name_row, blinks=2, delay=0.2, clr=CMS.Colors.red_blinking.rgb)
                except:
                    pass
        def blink_sub_tch_add():
            blink(DTKRO.self_ui.ui.fr_tch_inf)
            blink(DTKRO.self_ui.ui.tbl_tch)
            blink(DTKRO.self_ui.ui.fr_tch_inf_control)
            blink(DTKRO.self_ui.ui.btn_add)

        self.set_current_tch()

        if sub_tbl:
            t = CQT.TableContext(sub_tbl)
            row = t.current_row()

            if row.no_selection:
                return

            name = 'comment'# t.current_column_name()
            if name == 'comment':
                agr_o = DTKRO.current_kro_o.get_agreement(int(row.value('id')))
                DTKRO.current_agreement_o = agr_o
                self.set_current_tch(name,Agreement.ALIASES,agr_o.description)
                self.fill_tbl_agr_comment(agr_o)

            return

        t = CQT.TableContext(self.ui.tbl_main)
        row = t.current_row()
        if row.no_selection:
            return
        name = row.value('_name')
        if name=='mk':
            pass
        if name =="cause":
            pass
        if name == 'tbl_nomens':
            if DTKRO.current_kro_o.mk is None:
                blink('mk')
                return
            self.set_current_tch(name,Kros.ALIASES)
            self.fill_tbl_nomens()
            self.sub_buttons_set_enabled(DTKRO.regime is Regimes.insert)
            if DTKRO.regime is Regimes.insert:
                if not DTKRO.current_kro_o.tbl_nomens:
                    blink_sub_tch_add()
        if name == 'tbl_deviations':
            if DTKRO.current_kro_o.mk is None:
                blink('mk')
                return
            self.set_current_tch(name,Kros.ALIASES)
            self.fill_tbl_deviations()
            self.sub_buttons_set_enabled(DTKRO.regime is Regimes.insert)
            if DTKRO.regime is Regimes.insert:
                if not DTKRO.current_kro_o.tbl_deviations:
                    blink_sub_tch_add()
            pass






def fill_cmb_to_select_regime():
    from dataClass import data_app as DTCLS_main
    cmb = DTCLS_main.app_self.ui.cmb_podrazdelenie
    cmb.clear()
    all_regimes = F.get_all_attrs_with_properties(Regimes)
    list_descr =    [
                           f'{v.icon} {v.description}' for v in all_regimes.values() if v.start_mode
                           ]
    list_names =    [
                          v.name for v in all_regimes.values() if v.start_mode
                           ]

    list_tooltips =    [
                          v.tooltip for v in all_regimes.values() if v.start_mode
                           ]

    CQT.fill_list_combobx(DTCLS_main.app_self,cmb,
                          list_descr,
                          first_void=True,list_data=list_names,list_tooltip=list_tooltips)


class Cause(DDM.KroCauses):
    def test(self):
        pass

class File_kro():
    ACCEPTABLE_EXTENTION_FILES_FOR_LOAD_INTO_DB = {'.jpeg':'JPEG',
                                                   '.pdf':'PDF',
                                                   '.jpg':'JPG',
                                                   ".docx":"DOCX",
                                                   ".xlsx":"XLSX"}
    def __init__(self
                 ):
        self.name_user:str|None = None

        self.size_packed_bytes:int|None = None
        self.extension:str|None = None
        self.byte_data_packed:bytes|None = None
        self.tmp_win_dir_file:str|None = None
        self.id:int|None=None

    @property
    def user_icon(self):
        if self.size_packed_bytes:
            return f'{CEMOJ.EmojiMain.ДокументыДанные.image.symbol}'
        return  ''

    def clear(self):
        self.name_user = None

        self.size_packed_bytes = None
        self.extension = None
        self.byte_data_packed = None
        self.tmp_win_dir_file = None
        self.id = None

class Deviantion():
    ALIASES = {
        'order':'№',
        'before_file':'Изображение\nв РКД',
        'before': 'Имеется\nв РКД',
        'after_file':'Изображение\nпосле отклонения',
        'after': 'Должно быть\nпосле отклонения',
    }
    def __init__(self,parent:Kro,new_order:int):
        self.parent:Kro = parent
        self.order = new_order
        self.before_file:File_kro|None= File_kro()
        self.describe_before:str|None = None
        self.before:str = ''
        self.after_file:File_kro|None= File_kro()
        self.describe_after: str | None = None
        self.after: str = ''

    @property
    def describe_before_icon(self):
        if self.describe_before is None or self.describe_before=='' :
            return ''
        return CEMOJ.EmojiMain.ДокументыДанные.report.symbol
    @property
    def describe_after_icon(self):
        if self.describe_after is None or self.describe_after=='' :
            return ''
        return CEMOJ.EmojiMain.ДокументыДанные.report.symbol

    def __repr__(self):
        before_preview = self.before[:20] + "..." if len(self.before) > 20 else self.before
        after_preview = self.after[:20] + "..." if len(self.after) > 20 else self.after
        has_before_img = "📷" if self.before_file else ""
        has_after_img = "📷" if self.after_file else ""
        return f"Deviantion(order={self.order}, before='{before_preview}'{has_before_img}, after='{after_preview}'{has_after_img})"

    def template(self)-> dict[str,str]:
        data = {name: getattr(self,name) for name, alias in Deviantion.ALIASES.items()}
        data['before_file'] = f'{self.before_file.user_icon} {self.describe_before_icon}'
        data['after_file'] =  f'{self.after_file.user_icon} {self.describe_after_icon}'
        return data

class Nomen():
    ALIASES = {
        'order':'№',
        'head_nomen':'Документ',
        'nn':'Чертеж',
        'pozition':'Позиция',
        'name':'Наименование',
        'count':'Кол-во'
    }
    def __init__(self,parent:Kro ,new_order:int,count:int=0):
        self.parent: Kro = parent
        self.order = new_order
        self.dse_emoj: str|None = None
        self.id_dse: int|None = None
        self.head_nomen: str = ''
        self.name: str = ''
        self.nn:str = ''
        self.pozition: str = ''
        self.count:int = count
        self.docs_link:str|None = None

    def __repr__(self):
        name_preview = self.name[:30] + "..." if len(self.name) > 30 else self.name
        return f"Nomen(order={self.order}, name='{name_preview}', nn='{self.nn}', count={self.count})"

    def template(self)-> dict[str,str]:
        data = {name: getattr(self,name) for name, alias in Nomen.ALIASES.items()}
        if self.head_nomen:
            data['head_nomen'] = f'{CEMOJ.EmojiMain.ДокументыДанные.document.symbol} {self.head_nomen}'
        if self.name and self.dse_emoj:
            data['name'] = f'{self.dse_emoj} {self.name}'
        return data

class State_agreement():
    def __init__(self,
                 id,
                 text,
                 name,
                 emoj:str,
                 is_agreement=False):
        self.id:int = id
        self.text:str = text
        self.name:str = name
        self.emoj:str = emoj
        self.is_agreement:bool = is_agreement

    def as_row_ui(self)->str:
        return f'{self.emoj} {self.text}'

class State_mine():
    def __init__(self,
                 id,
                 text,
                 name,
                 emoj:str,
                 is_agreement=False):
        self.id:int = id
        self.text:str = text
        self.name:str = name
        self.emoj:str = emoj


    def as_row_ui(self)->str:
        return f'{self.emoj} {self.text}'




class States_mine(_MiniManager[State_mine]):
    _child_class = State_mine
    acces: State_mine = State_mine(0,'Доступно','acces',CEMOJ.EmojiMain.ПерсоналРоли.key.symbol)
    mine: State_mine = State_mine(1,'Мной','mine',CEMOJ.EmojiMain.ПерсоналРоли.operator.symbol)
    alien: State_mine = State_mine(2,'Коллегой','alien',CEMOJ.EmojiMain.ПерсоналРоли.team.symbol)

class States_agreement(_MiniManager[State_agreement]):
    _child_class = State_agreement
    state_none: State_agreement = State_agreement(0,'К постановке','state_none',CEMOJ.EmojiMain.СтатусыПроизводства.ellipsis.symbol)
    agreement: State_agreement = State_agreement(1,'Разрешено','agreement',CEMOJ.EmojiMain.СтатусыПроизводства.success.symbol,True)
    rejected: State_agreement = State_agreement(2,'Отклонено','rejected',CEMOJ.EmojiMain.СтатусыПроизводства.error.symbol)

DTKRO.states_agreement = States_agreement()

class Agreement(_ImportDb):
    ALIASES = {
        'id':'_id',
      'order_it':'_order',
      'enabled': 'Исп-ть',
      'description':'Этап',
        'permition': 'Доступ',
        'comment':'Заключение',
      'agreement_state':'    Резолюция    ',
      'user_name':'ФИО',
        'date': 'Дата'
    }
    def __init__(self,item:dict):
        self.id:int|None=None
        self.ref_depatments: str|None = None
        self.ref_dolgn: str|None = None
        self.order_it:int|None = None
        self.description:str|None = None
        self.comment:str|None = None
        self.enabled: bool|None = True
        self.agreement_state: State_agreement = DTKRO.states_agreement.state_none
        self.date: Cdt|None = Cdt()
        self.user_key: str|None = None
        self.user_name:str|None = None
        self.permition:bool|None = False
        self.parce_row_dict(item)
        self.calc_permision()

    @property
    def is_agreement(self)->bool:
        return self.agreement_state.is_agreement
    @property
    def is_rejected(self)->bool:
        return self.agreement_state is DTKRO.states_agreement.rejected

    @staticmethod
    def is_permitted(ref_depatments:str,ref_dolgn:str):
        permition = False
        user_o = DTCLS.CONFIG.user_config.User
        if ref_depatments:
            if user_o.current_Подразделение_Key in ref_depatments:
                permition = True
        if ref_dolgn:
            if user_o.current_Должность_Key in ref_dolgn:
                permition = True
        return permition

    def calc_permision(self):
        self.permition = self.is_permitted(self.ref_depatments,self.ref_dolgn)


    def template(self):
        rez = {n: str(getattr(self,n)) for n,a in Agreement.ALIASES.items()}
        for k,v in rez.items():
            if k == 'order_it':
                rez[k] = str(int(v) + 1)
            if k == 'agreement_state':
                rez[k] = self.agreement_state.id
            if k == 'date':
                if v == 'None':
                    rez[k] = ''
            if k == 'user_name':
                if v == 'None':
                    rez[k] = ''
            if k == 'date':
                    rez[k] = self.date.to_string()
            if k == 'permition':
                pass

        return rez

    def template_comment(self)->list[dict]:
        return [{'comment':self.comment}]

    def __repr__(self):
        date_str = self.date.strftime("%Y-%m-%d") if self.date else "None"
        desc_preview = self.description[:20] + "..." if self.description and len(
            self.description) > 20 else self.description
        return f"Agreement(order_it={self.order_it}, desc='{desc_preview}', date={date_str}, enabled={self.enabled}, agreed={self.is_agreement})"


class Block():
    def __init__(self,id:int):
        self.date:Cdt = Cdt()
        self.user:str = ''
        self._id = id
        self.update_state()

    def update_state(self):
        if self._id:
            data = CSQ.custom_request_c(DTCLS.CONFIG.project.db_naryad,
            f'SELECT _blocked_user, _blocked_date FROM kro WHERE id = {self._id}; -- {F.now("%H:%M:%S")}',
            rez_dict=True,one=True)
            self.date = Cdt(data['_blocked_date'])
            self.user = data['_blocked_user']


    def is_blocked(self,user_o:CFG.User_emploee)->bool:
        if self.date and self.user:
            if user_o.ID_ФизЛица != self.user:
                return True
        return False

    @staticmethod
    def clear_block_for_user():
        rez = CSQ.custom_request_c(DTCLS.CONFIG.project.db_naryad,
                                   f"""UPDATE kro
                        SET  (_blocked_user, _blocked_date)
                            = (?, ?)
                   WHERE _blocked_user = "{DTCLS.CONFIG.user_config.User.ID_ФизЛица}";""", list_of_lists_c=[[None, None]])
        return

    def set_block(self)->bool:
        if self.is_blocked(DTCLS.CONFIG.user_config.User):
            print(f'Заблокировано')
            return False
        if self._id is None:
            print(f'Не сохранен объект')
            return False
        self.date = Cdt().now()
        self.user = DTCLS.CONFIG.user_config.User.ID_ФизЛица
        self.clear_block_for_user()
        rez = CSQ.custom_request_c(DTCLS.CONFIG.project.db_naryad,
                f"""UPDATE kro
                SET  (_blocked_user, _blocked_date)
                    = (?, ?)
                            WHERE id = {self._id};""",list_of_lists_c=[[self.user,self.date.to_string()]])
        if not rez:
            return False
        return True

class Completed_action():
    def __init__(self,name:str,date:Cdt,agr:Agreement|None,result:Result_state|None):
        self.name:str = name
        self.date:Cdt = date
        self.agr:Agreement|None = agr
        self.result:Result_state|None = result

    def __eq__(self, other):
        if isinstance(other,Completed_action):
            return self.name == other.name
        return False

    def __repr__(self):
        date_str = self.date.to_string_ru() if self.date and self.date.dt else "None"
        result_str = self.result.name if self.result else "None"
        return f"Completed_action(name='{self.name}', date={date_str}, result={result_str})"

class Completed_actions():
    none:Completed_action = Completed_action('none',Cdt(),None,None)
    new_kro:Completed_action = Completed_action('new_kro',Cdt(),None,None)
    change_agreemtent:Completed_action = Completed_action('change_agreemtent',Cdt(),None,None)
    change_agreemtent_text:Completed_action = Completed_action('change_agreemtent_text',Cdt(),None,None)
    last_agreement:Completed_action = Completed_action('last_agreement',Cdt(),None,None)
    change_result_state:Completed_action = Completed_action('change_result_state',Cdt(),None,None)



class Kro(_ImportDb):
    _TYPE_CLS_SHABLON = '_path_kro_local_shablon'
    _VERSION_CLS = 0.1
    ATTRS_FOR_NEW = {
        'mk',
        'cause',
        'tbl_nomens',
        'tbl_deviations',
        'complects',
        'list_agreements',
        'result_state'
    }
    ATTRS_FOR_SHOW = {
        'id',
        'num',
        'version',
        'mk',
        'cause',
        'tbl_nomens',
        'tbl_deviations',
        'complects',
        'list_agreements',
        'result_state'
    }

    def __setattr__(self, key, value):
        super().__setattr__(key, value)
        if key == 'cause':
            if isinstance(value, int):
                super().__setattr__(key, Cause.object_manager.get(self.cause))
        if key == 'date':
            if isinstance(value, (str,datetime.datetime)):
                super().__setattr__(key, Cdt(value))
        if key == 'result_state_date':
            if value is None:
                super().__setattr__(key, Cdt(value))
            if isinstance(value, (str,datetime.datetime)):
                super().__setattr__(key, Cdt(value))

    def __init__(self,parent:Kros, item:dict=None):
        self.parent:Kros = parent
        self.id:int|None = None
        self.num:int|None = None
        self.version: int = 1
        self.date: Cdt = Cdt().now()
        self.initiator:CMS.Emploee_usr|str = F.user_full_namre()
        self.mk:int|None = None
        self.cause:Cause|int|None = 0
        self.complects:str|None = None
        self.tbl_nomens:list[Nomen] = []
        self.tbl_deviations:list[Deviantion] = []
        self.list_agreements:list[Agreement] = []
        self.result_state: Result_state = Result_states.none_state
        self.result_state_date: Cdt = Cdt()
        self.completed_actions:list[Completed_action] = [Completed_actions.none]
        self._load_agreements()
        if item:
            self.parce_row_dict(item)
        self._calc_result_state()


        if self.id: # old kro
            self._load_nomens()
            self._load_deviations()
            self._overlay_agreement_states()
        else:           #new kro
            if item:
                raise Exception('KRO id not found in item')
            self._set_action(Completed_actions.new_kro)
            self.initiator = DTCLS.CONFIG.user_config.User.ID_ФизЛица
            if DTKRO.filter_mk:
                if isinstance(DTKRO.filter_mk,int):
                    self.mk = DTKRO.filter_mk


    def clear_action(self):
        self.completed_actions = [Completed_actions.none]

    def _set_action(self,action:Completed_action,agreement:Agreement|None=None,result_state:Result_state|None=None):
        completed_action = copy.deepcopy(action)
        completed_action.date = Cdt().now()
        if action in (Completed_actions.change_agreemtent,Completed_actions.last_agreement,Completed_actions.change_agreemtent_text):
            if agreement is None:
                raise ValueError("'agreement' must be provided when setting the Change_Result_State completed action.")
            completed_action.agr = agreement
        if action is Completed_actions.change_result_state:
            if result_state is None:
                return ValueError("'result_state' must be specified.")
            completed_action.result = result_state
        self.completed_actions.append(completed_action)

    @property
    def nomen_name(self):
        name = ''
        if self.tbl_nomens:
            name = self.tbl_nomens[0].head_nomen
        return name

    def set_result_state(self,state:Result_state):
        self.result_state = state
        self.upd_date_result_state()
        self._set_action(Completed_actions.change_result_state, result_state= state)

    def set_agereement_state(self,state:States_agreement, agreement:Agreement,ref_user:str,name_user:str):
        agreement.agreement_state = state
        if agreement.agreement_state is States_agreement.state_none:
            agreement.user_key = ''
            agreement.user_name = ''
            agreement.date = Cdt()
        else:
            agreement.user_key = DTCLS.CONFIG.user_config.User.ID_ФизЛица
            agreement.user_name = DTCLS.CONFIG.user_config.User.ФИОк
            agreement.date = Cdt().now()

        if self.filled_agreements:
            self._set_action(Completed_actions.last_agreement, agreement= agreement)
        else:
            self._set_action(Completed_actions.change_agreemtent, agreement= agreement)


    def calc_agreemtens_state(self)->str:
        agr = []
        rejected = []
        total = []
        for it in self.list_agreements:
            if it.enabled:
                total.append(it)
            if it.is_agreement:
                agr.append(it)
            if it.is_rejected:
                rejected.append(it)
        return (f'Всего:{len(total)} ({CEMOJ.EmojiMain.СтатусыПроизводства.success.symbol}:{len(agr)}|'
                f'{CEMOJ.EmojiMain.СтатусыПроизводства.error.symbol}:{len(rejected)}|'
                f'{CEMOJ.EmojiMain.СтатусыПроизводства.progress.symbol}:{len(total)-(len(agr)+len(rejected))})')

    def upd_date_result_state(self):
        if self.result_state is not Result_states.none_state:
            self.result_state_date = Cdt().now()

    def get_block(self) ->Block:
        return Block(self.id)

    @property
    def result_state_ui(self)->str:
        return self.result_state.as_row_ui()

    @property
    def filled_agreements(self)->bool:
        for it in self.list_agreements:
            if it.enabled and it.agreement_state is States_agreement.state_none:
                return False
        return True

    def _calc_result_state(self):
        if isinstance(self.result_state,int):
            self.result_state = DTKRO.result_states.as_dict[self.result_state]

    def check_filling(self)->tuple[bool,list[str]]:
        if DTKRO.regime is Regimes.report:

            return False ,['Нельзя сохранить в режиме отчет']
        list_err=[]
        if DTKRO.regime is Regimes.insert:
            if self.mk is None :
                list_err.append(f'Не указан параметр "{Kros.ALIASES["mk"]}"')
            if self.cause is None or self.cause.name == 'unselected':
                list_err.append(f'Не указан параметр "{Kros.ALIASES["cause"]}"')
            if self.complects is None or self.complects.strip() == '' :
                list_err.append(f'Не указан параметр "{Kros.ALIASES["complects"]}"')
            if not self.tbl_nomens :
                list_err.append(f'Не указан параметр "{Kros.ALIASES["tbl_nomens"]}"')
            for nomen in self.tbl_nomens:
                if nomen.nn is None or nomen.nn == '':
                    list_err.append(f'"{Kros.ALIASES["tbl_nomens"]}": Не выбран документ "{Nomen.ALIASES["nn"]}" в строке №{nomen.order}')
                if nomen.count is None or nomen.count == 0:
                    list_err.append(f'"{Kros.ALIASES["tbl_nomens"]}": Не указано  "{Nomen.ALIASES["count"]}" в строке №{nomen.order}')
            if not self.tbl_deviations :
                list_err.append(f'Не указан параметр "{Kros.ALIASES["tbl_deviations"]}"')
            for dev in self.tbl_deviations:
                if dev.after is None or dev.after=='':
                    list_err.append(f'"{Kros.ALIASES["tbl_deviations"]}": Не указано изменение "{Deviantion.ALIASES["after"]}" в строке №{dev.order}')
            count_enabled_agrs=len([1 for _ in self.list_agreements if _.enabled])
            if not count_enabled_agrs:
                list_err.append(f'Не выбран ни один этап согласвания.')

        if DTKRO.regime is Regimes.edit:
            if not self.filled_agreements:
                if self.result_state is Result_states.approved:
                    list_err.append(
                        f'"Не подписаны все согласования. Проверьте изменения и повторите "{Kros.ALIASES["list_agreements"]}"')

        if list_err:
            return False,list_err
        return True, []


    def save_db(self) -> tuple[bool,list[str]]:
        main_data = {
            'date': self.date.to_db(),
            'initiator': self.initiator,
            'mk': self.mk,
            'num': self.num,
            'cause': self.cause.id if self.cause else None,
            'complects': self.complects,
            'result_state': self.result_state.id,
            'result_state_date': self.result_state_date.to_db(),
            'poki': DTCLS.CONFIG.place.poki,
            'version': self.version,
        }

        fl_new = False
        if self.id is None:
            if self.num is None:
                last_clmn = CSQ.custom_request_c(DTCLS.CONFIG.project.db_naryad,
                                               f"""SELECT MAX(num) FROM kro; """,
                                               one_column=True,one=True, hat_c=False)
                if last_clmn:
                    new_num = last_clmn+1
                else:
                    new_num = 1
                main_data['num'] = new_num

            str_fields = list(main_data.keys())
            fl_new = True
            id_data = CSQ.custom_request_c(DTCLS.CONFIG.project.db_naryad,
                                 f"""        
                    INSERT INTO kro ({', '.join(str_fields)})
                    VALUES ({CSQ.questions_for_mask(str_fields)}) RETURNING id ;""",
                                           list_of_lists_c=[_ for _ in main_data.values()],

                                            rez_dict=True
                                )
            if id_data:
                self.id = id_data[0]['id']
                self.num = new_num
            else:

                return False , [f'Ошибка сохранения']
        else:
            str_fields = list(main_data.keys())
            rez = CSQ.custom_request_c(DTCLS.CONFIG.project.db_naryad,
                                 f"""        
                    UPDATE kro SET ({', '.join(str_fields)})
                    = ({CSQ.questions_for_mask(str_fields)}) WHERE id = {self.id}
                        ;""", list_of_lists_c= [_ for _ in main_data.values()]
                                 )
            if not rez:

                return False , [f'Ошибка сохранения']

        if not self._save_agreement_states(DTCLS.CONFIG.project.db_naryad):
            if fl_new:
                self.rollback_agreement_states(DTCLS.CONFIG.project.db_naryad)
                self.rollback_kro(DTCLS.CONFIG.project.db_naryad)
                self.id = None
            return False , [f'Ошибка сохранения']

        if not self._save_nomens(DTCLS.CONFIG.project.db_naryad):
            if fl_new:
                self.rollback_nomens(DTCLS.CONFIG.project.db_naryad)
                self.rollback_agreement_states(DTCLS.CONFIG.project.db_naryad)
                self.rollback_kro(DTCLS.CONFIG.project.db_naryad)
                self.id = None
            return False , [f'Ошибка сохранения']

        if not self._save_deviations(DTCLS.CONFIG.project.db_naryad):
            if fl_new:
                self.rollback_deviations(DTCLS.CONFIG.project.db_naryad)
                self.rollback_nomens(DTCLS.CONFIG.project.db_naryad)
                self.rollback_agreement_states(DTCLS.CONFIG.project.db_naryad)
                self.rollback_kro(DTCLS.CONFIG.project.db_naryad)
                self.id = None
            return False , [f'Ошибка сохранения']



        return True , []

    def _save_nomens(self, db):
        CSQ.custom_request_c(db, f"DELETE FROM kro_nomens WHERE kro_id = {self.id}")
        list_data = []
        for n in self.tbl_nomens:
            list_data.append({
                'kro_id': self.id,
                'order_it': n.order,
                'id_dse': n.id_dse,
                'dse_emoj': n.dse_emoj,
                'head_nomen': n.head_nomen,
                'name': n.name,
                'nn': n.nn,
                'pozition': n.pozition,
                'count': n.count,
                'docs_link': n.docs_link,
            })
        if not  list_data:
            return
        str_fields = list_data[0].keys()

        rez  = CSQ.custom_request_c(db,
                             f"""        
                            INSERT INTO kro_nomens ({', '.join(str_fields)})
                            VALUES ({CSQ.questions_for_mask(str_fields)});""",
                             list_of_lists_c=[list(_.values()) for _ in list_data])
        if not rez:
            return False
        return True

    def _save_file(self, db, file: File_kro) -> int | bool:
        """Сохраняет BLOB, возвращает id или None если файла нет."""
        if not file or not file.byte_data_packed:
            return None

        list_data = []
        list_data.append({
            'name_user': file.name_user,

            'size_packed_bytes': file.size_packed_bytes,
            'extension': file.extension,
            'byte_data_packed': file.byte_data_packed
                })
        if not list_data:
            return False
        str_fields = list_data[0].keys()

        rez = CSQ.custom_request_c(DTCLS.CONFIG.project.db_files,
                                   f"""        
                                            INSERT INTO kro_files ({', '.join(str_fields)})
                                            VALUES ({CSQ.questions_for_mask(str_fields)}) RETURNING id;""",
                                   list_of_lists_c=list(list_data[0].values()), rez_dict=True,one=True)
        if not rez:
            return False
        file.id = rez["id"]
        return file.id

    def _save_deviations(self, db)->bool:
        #чистим старые файлы
        old = CSQ.custom_request_c(db,
                                   f"SELECT before_file_id, after_file_id FROM kro_deviations WHERE kro_id = {self.id}",
                                   rez_dict=True)
        for row in old:
            for fid in filter(None, [row.get('before_file_id'), row.get('after_file_id')]):
                CSQ.custom_request_c(DTCLS.CONFIG.project.db_files, f"DELETE FROM kro_files WHERE id = {fid}")

        CSQ.custom_request_c(db, f"DELETE FROM kro_deviations WHERE kro_id = {self.id}")
        #добавляем новые

        list_data = []
        for d in self.tbl_deviations:
            tmp_dev_data = {
                'kro_id': self.id,
                'order_it': d.order,
                'before_text': F.sanitize_text(d.before,multiline=True),
                'after_text': F.sanitize_text(d.after,multiline=True),
                'describe_before': d.describe_before,
                'describe_after': d.describe_after,
                'before_file_id': self._save_file(db, d.before_file),
                'after_file_id': self._save_file(db, d.after_file),
            }

            if tmp_dev_data['after_file_id'] == False or tmp_dev_data['before_file_id'] == False:
                return False
            list_data.append(tmp_dev_data)
        if not list_data:
            return False
        str_fields = list_data[0].keys()

        rez = CSQ.custom_request_c(db,
                                   f"""        
                                    INSERT INTO kro_deviations ({', '.join(str_fields)})
                                    VALUES ({CSQ.questions_for_mask(str_fields)});""",
                                   list_of_lists_c=[list(_.values()) for _ in list_data])
        if not rez:
            return False
        return True

    def rollback_kro(self, db):
        CSQ.custom_request_c(db,
                             f"DELETE FROM kro WHERE id = {self.id}")

    def rollback_nomens(self, db):
        CSQ.custom_request_c(db,
                             f"DELETE FROM kro_nomens WHERE kro_id = {self.id}")

    def rollback_deviations(self, db):
        # чистим старые файлы
        old = CSQ.custom_request_c(db,
                                   f"SELECT before_file_id, after_file_id FROM kro_deviations WHERE kro_id = {self.id}",
                                   rez_dict=True)
        for row in old:
            for fid in filter(None, [row.get('before_file_id'), row.get('after_file_id')]):
                CSQ.custom_request_c(DTCLS.CONFIG.project.db_files, f"DELETE FROM kro_files WHERE id = {fid}")

        CSQ.custom_request_c(db, f"DELETE FROM kro_deviations WHERE kro_id = {self.id}")


    def rollback_agreement_states(self, db):
        CSQ.custom_request_c(db,
                             f"DELETE FROM kro_agreement_states WHERE kro_id = {self.id}")

    def _save_agreement_states(self, db):
        CSQ.custom_request_c(db,
                             f"DELETE FROM kro_agreement_states WHERE kro_id = {self.id}")

        list_data = []
        for ag in self.list_agreements:
            if not ag.enabled:
                continue
            tmp_agr_data = {
                'kro_id': self.id,
                'agreement_id': ag.id,
                'comment': F.sanitize_text(ag.comment,multiline=True),
                'agreement_state': ag.agreement_state.id,
                'user_key': ag.user_key,
                'user_name': ag.user_name,
                'date': ag.date.to_string(),
            }

            list_data.append(tmp_agr_data)
        if not list_data:
            return False
        str_fields = list_data[0].keys()

        rez = CSQ.custom_request_c(db,
                                   f"""        
                                            INSERT INTO kro_agreement_states ({', '.join(str_fields)})
                                            VALUES ({CSQ.questions_for_mask(str_fields)});""",
                                   list_of_lists_c=[list(_.values()) for _ in list_data])
        if not rez:
            return False
        return True

    def _load_agreements(self):
        if DTKRO.agreements_list is None :
            self._generate_agreements()
        self.list_agreements = copy.deepcopy(DTKRO.agreements_list)


    @staticmethod
    def _generate_agreements():
        list_agreements = []
        data = CSQ.custom_request_c(DTCLS.CONFIG.project.db_naryad,
                                    f"""SELECT * FROM kro_agreements 
                                    WHERE kro_agreements.poki = {DTCLS.CONFIG.place.poki} order by order_it""",rez_dict=True)

        for it in data :
            list_agreements.append(Agreement(it))

        DTKRO.agreements_list = list_agreements

    def _load_nomens(self):
        rows = CSQ.custom_request_c(DTCLS.CONFIG.project.db_naryad,
                                    f"SELECT * FROM kro_nomens WHERE kro_id = {self.id} ORDER BY order_it",
                                    rez_dict=True)
        self.tbl_nomens = []
        for row in rows:
            n = Nomen(self, row['order_it'])
            n.id_mk = row.get('id_mk')
            n.id_dse = row.get('id_dse')
            n.dse_emoj = row.get('dse_emoj')
            n.head_nomen = row.get('head_nomen', '')
            n.name = row.get('name', '')
            n.nn = row.get('nn', '')
            n.pozition = row.get('pozition', '')
            n.count = row.get('count', 0)
            n.docs_link = row.get('docs_link', '')
            self.tbl_nomens.append(n)

    def _load_file(self, file_id: int | None) -> File_kro:
        f = File_kro()
        if not file_id:
            return f
        rows = CSQ.custom_request_c(DTCLS.CONFIG.project.db_files,
                                    f"SELECT * FROM kro_files WHERE id = {file_id}", rez_dict=True)
        if rows:
            row = rows[0]
            f.id = row.get('id')
            f.name_user = row.get('name_user')

            f.size_packed_bytes = row.get('size_packed_bytes')
            f.extension = row.get('extension')
            f.byte_data_packed = row.get('byte_data_packed')
        return f

    def _load_deviations(self):
        rows = CSQ.custom_request_c(DTCLS.CONFIG.project.db_naryad,
                                    f"SELECT * FROM kro_deviations WHERE kro_id = {self.id} ORDER BY order_it",
                                    rez_dict=True)
        self.tbl_deviations = []
        for row in rows:
            d = Deviantion(self, row['order_it'])
            d.before = row.get('before_text', '')
            d.after = row.get('after_text', '')
            d.before_file = self._load_file(row.get('before_file_id'))
            d.after_file = self._load_file(row.get('after_file_id'))
            d.describe_after = row.get('describe_after')
            d.describe_before = row.get('describe_before')
            self.tbl_deviations.append(d)

    def _overlay_agreement_states(self):
        """Шаблон уже загружен через _load_agreements(), просто обновляем состояния."""

        rows = CSQ.custom_request_c(DTCLS.CONFIG.project.db_naryad,
                                    f"SELECT * FROM kro_agreement_states WHERE kro_id = {self.id}",
                                    rez_dict=True)
        saved = {r['agreement_id']: r for r in rows}
        for ag in self.list_agreements:
            ag.enabled = False
            if ag.id not in saved:
                continue
            s = saved[ag.id]
            ag.enabled = True
            ag.comment = s.get('comment')
            ag.user_key = s.get('user_key')
            ag.user_name = s.get('user_name')
            ag.date = Cdt(s['date']) if s.get('date') else Cdt()
            ag.agreement_state = DTKRO.states_agreement.as_dict[s['agreement_state']]

    def delete_nomen(self,order:int)->bool:
        for i in range(len(self.tbl_nomens)):
            if self.tbl_nomens[i].order == order:
                self.tbl_nomens.pop(i)
                break
        self._update_orders_nomens()

    def _update_orders_nomens(self):
        self.tbl_nomens.sort(key=lambda x:x.order)
        for i in range((len(self.tbl_nomens))):
            self.tbl_nomens[i].order = i+1

    def insert_nomen(self):
        new_nomen = Nomen(self,9999999)
        self.tbl_nomens.append(new_nomen)
        self._update_orders_nomens()

    def get_nomen(self,order:int)->Nomen|None:
        for it in self.tbl_nomens:
            if it.order == order:
                return it

    def get_agreement(self,id:int|None=None,last=False)->Agreement|None:
        if last:
            date_lst = None
            it_lst = None
            for it in self.list_agreements:
                if it.date:
                    if date_lst is None or it.date.dt > date_lst:
                        date_lst = it.date.dt
                        it_lst = it
            return it_lst


            return  it
        for it in self.list_agreements:
            if it.id == id:
                return it

    def delete_deviation(self,order:int)->bool:
        for i in range(len(self.tbl_deviations)):
            if self.tbl_deviations[i].order == order:
                self.tbl_deviations.pop(i)
                break
        self._update_orders_deviation()

    def _update_orders_deviation(self):
        self.tbl_deviations.sort(key=lambda x:x.order)
        for i in range((len(self.tbl_deviations))):
            self.tbl_deviations[i].order = i+1

    def insert_deviation(self):
        new_deviation = Deviantion(self,9999999)
        self.tbl_deviations.append(new_deviation)
        self._update_orders_deviation()

    def get_deviation(self,order:int)->Deviantion|None:
        for it in self.tbl_deviations:
            if it.order == order:
                return it

    def get_template_main(self)->list[dict]:
        emo_conveyor =  CEMOJ.EmojiMain.ОборудованиеИнструменты.conveyor.symbol
        emo_document =  CEMOJ.EmojiMain.ДокументыДанные.document.symbol
        emo_pushpin2 =  CEMOJ.EmojiMain.ДокументыДанные.pushpin2.symbol
        data = F.get_all_attrs_with_properties(self)
        if DTKRO.regime is Regimes.insert:
            attrs = self.ATTRS_FOR_NEW
        elif DTKRO.regime is Regimes.report:
            attrs = self.ATTRS_FOR_SHOW
        elif DTKRO.regime is Regimes.edit:
            attrs = self.ATTRS_FOR_SHOW

        rez = [{'_name': k ,'Параметр': self.parent.ALIASES.get(k,k) , 'Значение': v} for  k,v in data.items() if k in attrs]
        for it in rez:
            if it['_name'] == 'id':
                it['Значение'] = '' if self.id is None else self.id
            if it['_name']=='tbl_nomens':
                count_nomens = len(self.tbl_nomens)
                if count_nomens>1:
                    msg = f'{emo_conveyor} {count_nomens} записей: ...'
                elif count_nomens == 1:
                    msg = (f'{emo_document} {count_nomens} запись: {self.tbl_nomens[0].nn} {self.tbl_nomens[0].name} '
                           f'- {self.tbl_nomens[0].count}шт.')
                else:
                    msg= ''
                it['Значение'] = msg
            if it['_name']=='tbl_deviations':
                count_deviations = len(self.tbl_deviations)
                if count_deviations > 1:
                    msg = f'{emo_conveyor} {count_deviations} записей: ...'
                elif count_deviations == 1:
                    describe_before = ''
                    if self.tbl_deviations[0].describe_before:
                        describe_before = f' +{self.tbl_deviations[0].describe_before_icon}'
                    describe_after = ''
                    if self.tbl_deviations[0].describe_after:
                        describe_after = f' +{self.tbl_deviations[0].describe_after_icon}'

                    before = ''
                    if self.tbl_deviations[0].before:
                        before = f'было: {self.tbl_deviations[0].before}{describe_before}, '
                    after = ''
                    if self.tbl_deviations[0].after:
                        after = f'стало: {self.tbl_deviations[0].after}{describe_after}'
                    msg = f'{emo_pushpin2} {count_deviations} запись: {before}{after}'
                else:
                    msg = ''
                it['Значение'] = msg

            if it['_name'] == 'list_agreements':
                it['Значение'] = [_.template() for _ in it['Значение']]
            if it['_name'] == 'cause':
                it['Значение'] = self.cause.id
            if it['_name'] == 'result_state':
                it['Значение'] = self.result_state.id

        return rez

    def get_template_nomen(self)->list[dict]:
        data = self.tbl_nomens
        rez = [it.template() for it in data]
        return rez

    def get_template_deviations(self)->list[dict]:
        data = self.tbl_deviations
        rez = [it.template() for it in data]
        return rez

    def template(self)->dict:
        return {k:getattr(self,k) for k in self.parent.ALIASES.keys()}

    def is_changes(self)->bool:
        for action in self.completed_actions:
            if action == Completed_actions.none:
                continue
            else:
                return True
        return False

class Kros():
    ALIASES = {
                'id':'_id',
                'num':'№ КРО',
                'version':'Версия',
                'date': 'Дата',
                'mk':'МК',
               'cause':'Причина',
               'tbl_nomens':'Изделие',
               'tbl_deviations':'Отклонения в РКД',
               'complects':'Заводской комплект',
               'list_agreements':'Этапы согласовния',
               'result_state':'Статус',
                'count_nomens':'Изделий',
                'cur_user_agreement_state':'Моё согласование',
                'count_deviations':'Откл-ий,шт.',
                'count_agreements_total':'Согл-ий,шт.',
                'count_agreements_donecount_agreements_done':'Согл-но,шт.',
                'name_nd':'Направление деятельности',
                'initiator':'Инициатор',
                }

    def __init__(self):
        self.list_kro:list[Kro] = []
        self.list_preview:list[dict] = []

    def load_preview(self) -> list[Kro]:

        def calc_permited(it):
            return Agreement.is_permitted(it['ref_depatments'],it['ref_dolgn'])

        poki = DTCLS.CONFIG.place.poki
        list_agrees = CSQ.custom_request_c(DTCLS.CONFIG.project.db_naryad,f"""SELECT 
                    kro_agreements.ref_depatments, kro_agreements.ref_dolgn, 
                    kro_agreement_states.agreement_state, kro_agreement_states.kro_id, kro_agreement_states.user_key 
                     FROM kro_agreement_states INNER JOIN 
                    kro ON kro.id = kro_agreement_states.kro_id,
                    kro_agreements ON kro_agreements.id = kro_agreement_states.agreement_id
                    WHERE kro.result_state = {Result_states.none_state.id} and kro.poki = {poki} 
                        """,rez_dict=True)

        dict_agrees = F.grouping_list_dicts(list_agrees,'kro_id')
        pass

        rows = CSQ.custom_request_c(
            DTCLS.CONFIG.project.db_naryad,
            f"""
                    SELECT
                        napravl_deyat.Имя || " (" || napravl_deyat.Псевдоним || ")" as name_nd,
                        k.id,
                        k.num,
                        k.version,
                        k.date,
                        ФизическиеЛица.Наименование as initiator,
                        пл_оуп.№проекта,
                        пл_оуп.№ERP,
                        пл_оуп.Номенклатура_ЕРП,
                        k.mk,
                        k.cause,
                        k.complects,
                        k.result_state,
                        "" as cur_user_agreement_state,
                        COUNT(DISTINCT kn.id)                                            AS count_nomens,
                        COUNT(DISTINCT kd.id)                                            AS count_deviations,
                        COUNT(DISTINCT CASE WHEN kas.agreement_state = 1 THEN kas.id END) AS count_agreements_donecount_agreements_done,
                        COUNT(DISTINCT kas.id)                                           AS count_agreements_total
                        
                    FROM kro k
                    LEFT JOIN kro_nomens           kn  ON kn.kro_id  = k.id
                    LEFT JOIN kro_deviations       kd  ON kd.kro_id  = k.id
                    LEFT JOIN kro_agreement_states kas ON kas.kro_id = k.id
                    LEFT JOIN ФизическиеЛица           ON ФизическиеЛица.ФизическоеЛицо_Key = k.initiator
                    INNER join mk ON mk.Пномер = k.mk
                    INNER join пл_оуп ON пл_оуп.НомПл = mk.НомКплан
                    INNER join plan ON plan.Пномер = mk.НомКплан
                    INNER join napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности
                    WHERE k.poki = {poki}
                    GROUP BY k.id
                    ORDER BY k.date DESC
                    """,
            rez_dict=True,attach_dbs=(DTCLS.CONFIG.project.db_users,DTCLS.CONFIG.project.db_kplan)
        )

        for it in rows:
            if it['id'] not in dict_agrees:
                continue
            main_state = ''
            for it_agr in dict_agrees[it['id']]:
                if calc_permited(it_agr):#ecть права
                    state:State_agreement = DTKRO.states_agreement.as_dict[it_agr['agreement_state']]#получаем состояние
                    state_mine = States_mine.acces
                    if state is not States_agreement.state_none:
                        if it_agr['user_key'] == DTCLS.CONFIG.user_config.User.ID_ФизЛица:
                            pass#есть моe соглосованние
                            state_mine = States_mine.mine
                        else:
                            pass#нет мое
                            state_mine = States_mine.alien
                    main_state = f'{state.as_row_ui()} {state_mine.as_row_ui()}'
            it['cur_user_agreement_state'] = main_state

        self.list_preview = rows


    def load_one(self, kro_id: int) -> Kro:
        rows = CSQ.custom_request_c(DTCLS.CONFIG.project.db_naryad,
                                    f"SELECT * FROM kro WHERE id = {kro_id}", rez_dict=True)
        return Kro(self, rows[0])

    def delete(self, kro_id: int) -> bool:

        CSQ.custom_request_c(DTCLS.CONFIG.project.db_naryad,
                             f"DELETE FROM kro WHERE id = {kro_id}")
        self.list_kro = [k for k in self.list_kro if k.id != kro_id]
        return True

    def new(self)->Kro:
        kro = Kro(self)
        return kro

    def template(self)->list[dict]:
        rez = []

        for it in self.list_preview:
            it['cause'] = STORE.DICT_KroCauses[it['cause']].text
            it['result_state'] = DTKRO.result_states.as_dict[it['result_state']].as_row_ui()
        return  self.list_preview

    @staticmethod
    def get_dict_kro()->dict[int,dict]:
        list_kro = CSQ.custom_request_c(DTCLS.CONFIG.project.db_naryad,
                             f"""WITH  vt as (SELECT 
                                kro_id,
                                GROUP_CONCAT(DISTINCT id_dse) AS id_dse_list
                            FROM kro_nomens
                            GROUP BY kro_id) 
                            
                            SELECT kro.id, kro.mk, kro.result_state_date,  kro.result_state, vt.id_dse_list FROM kro 
                            inner join vt ON vt.kro_id = kro.id 
                             WHERE kro.result_state in ({Result_states.approved.id}, {Result_states.none_state.id})""",rez_dict=True)
        for _ in list_kro:

            if _['result_state'] == Result_states.approved.id:
                date_ui = F.dateStrToStr(_['result_state_date'], "%Y-%m-%d %H:%M:%S", "%d.%m.%Y", '')
                _['msg'] = f'{Result_states.approved.emoj} №{_["id"]} c {date_ui}'
            else:
                _['msg'] = f'{Result_states.none_state.emoj} №{_["id"]} подготовка'
        dict_kro = F.grouping_list_dicts(list_kro,"mk",True)
        return dict_kro


DTKRO.kros = Kros()

class Alert():
    def __init__(self,name,msg,base_msg):

        self.name =name
        self.table:list[dict]|None=None
        self.msg = msg
        self.base_msg = base_msg
        self.id_chats:list[str]|None = None

    def __repr__(self):
        chats = self.id_chats if self.id_chats else []
        table_count = len(self.table) if self.table else 0
        return f"Alert(name='{self.name}', msg='{self.msg[:30]}{'...' if len(self.msg) > 30 else ''}', chats={len(chats)}, table_rows={table_count})"

    def _gen_table(self,kro_o:Kro):
        self.table = [
            {'Параметр':'Номер:','Значение':kro_o.id},
            {'Параметр':'Автор:','Значение':UserPh(kro_o.initiator)},
            {'Параметр':'Дата:','Значение':kro_o.date.to_string_ru()},
            {'Параметр':'МК:','Значение':kro_o.mk},
            {'Параметр':'Изделие:','Значение': kro_o.nomen_name},
            {'Параметр':'Комплекты:', 'Значение': kro_o.complects},
            {'Параметр':'Причина:','Значение':kro_o.cause.text},
            {'Параметр':'Согласований:','Значение':kro_o.calc_agreemtens_state()},
                      ]

    def _upd_base_msg(self,kro_o:Kro):
        for action in kro_o.completed_actions:
            if action == Completed_actions.change_result_state:
                state = action.result
                date_start_str = ''
                if state is Result_states.approved:
                    date_start_str= f'\nКРО действует с {kro_o.result_state_date.to_string_ru()}'
                self.base_msg = f'Установлен статус {state.as_row_ui()}{date_start_str}'
                return

        for action in kro_o.completed_actions:
            if action == Completed_actions.last_agreement:
                agr = action.agr
                self.base_msg = (f'{CEMOJ.EmojiMain.СтатусыПроизводства.success.symbol} '
                                 f'Изменение последней резолюции:\n {agr.agreement_state.as_row_ui()} ({agr.description})\n'
                                 f'Необходимо зафиксировать итоговый статус КРО')
                return


        for action in kro_o.completed_actions:
            if action == Completed_actions.change_agreemtent:
                agr = action.agr
                self.base_msg = (
                                 f'Изменение резолюции:\n{agr.description} - {agr.agreement_state.as_row_ui()}')
                return


        for action in kro_o.completed_actions:
            if action == Completed_actions.change_agreemtent_text:
                agr = action.agr
                self.base_msg = (
                                 f'Изменение текста резолюции:\n {agr.description} {agr.agreement_state.as_row_ui()} \n-"{agr.comment}"')
                return


        for action in kro_o.completed_actions:
            if action == Completed_actions.new_kro:
                self.base_msg = 'Запущен этап согласования'
                return

        for action in kro_o.completed_actions:
            if action == Completed_actions.none:
                self.base_msg = ''
                return


    def _get_id_chat(self):
        self.id_chats = [_.as_str for _ in DTKRO.alerts.list_chats if _.alert_type == self 
                         and _.poki == DTCLS.CONFIG.place.poki]
        DTKRO.alerts.list_chats[0] == self

    def __eq__(self, other):
        if isinstance(other,Alert):
            return self.name == other.name
        return False

    def send_alert(self,kro_o:Kro):
        self._get_id_chat()
        self._gen_table(kro_o)
        self._upd_base_msg(kro_o)
        template = CB24.MessageBuilder(self.base_msg)  # Инициализация (базовое сообщение)
        if self.table:
            template.add_table(self.table)  # Добавить табличную часть
            template.add_delimiter()  # Добавить разделитель
        template.add_message(self.msg)  # Добавить сообщение
        if self.id_chats:
            for id_chat_str in self.id_chats:
                template.send_by_chat_id(id_chat_str)  # Итоговая отправка

class Chat_type():
    def __init__(self,name,description):
        self.name = name
        self.description = description

    @property
    def for_ui(self)->str:
        return f'{self.description}'

class Chat_types():
    preparatory = Chat_type('preparatory','Чат согласований')
    resulting = Chat_type('resulting','Чат ввода КРО')

class Chat():
    def __init__(self,id_chat,alert_type,poki:int,chat_type:Chat_type):
        self.id:int = id_chat
        self.alert_type:Alert = alert_type
        self.chat_type:Chat_type = chat_type
        self.poki:int = poki
        
    @property
    def as_str(self)->str:
        return f'chat{self.id}'

    @property
    def as_link(self)->str:
        return  "https://bitrix24.kelast.ru/online/?IM_DIALOG=chat" + str(self.id)

class Alerts():
    _chats:dict[str,str]=dict()
    new:Alert = Alert('new','Создано новое КРО', '')
    edit:Alert = Alert('edit','Согласование КРО', '')
    result:Alert = Alert('result','Статус КРО', '')

    def __init__(self):
        self.list_chats:list[Chat] = []
        self._gen_chats()

        
    def _gen_chats(self):
        self.list_chats = [
            Chat(103872, self.new, 0,Chat_types.preparatory),
            Chat(103872, self.edit, 0,Chat_types.preparatory),
            Chat(103872, self.result, 0,Chat_types.preparatory),
            Chat(103888, self.result, 0,Chat_types.resulting),

            Chat(103961, self.new, 1,Chat_types.preparatory),
            Chat(103961, self.edit, 1,Chat_types.preparatory),
            Chat(103961, self.result, 1,Chat_types.preparatory),
            Chat(103962, self.result, 1,Chat_types.resulting),

            Chat(103963, self.new, 3,Chat_types.preparatory),
            Chat(103963, self.edit, 3,Chat_types.preparatory),
            Chat(103963, self.result, 3,Chat_types.preparatory),

        ]
    

    def gen_link(self,chat_type:Chat_type)->tuple[str,str]:
        list_chats:list[Chat] = [_ for _ in self.list_chats if _.chat_type == chat_type and _.poki == DTCLS.CONFIG.place.poki]
        if list_chats:
            return  f"{list_chats[0].chat_type.for_ui} ({DTCLS.CONFIG.place.Имя})",   list_chats[0].as_link
        return '', ''
        
        


    def send_alert(self):
        if not DTKRO.current_kro_o.is_changes():
            return
        alert_o = None
        if DTKRO.regime is Regimes.insert:
            alert_o = copy.deepcopy(DTKRO.alerts.new)
        if DTKRO.regime is Regimes.edit:
            for action in DTKRO.current_kro_o.completed_actions:
                if action == Completed_actions.change_result_state:
                    alert_o = copy.deepcopy(DTKRO.alerts.result)
                    break
            for action in DTKRO.current_kro_o.completed_actions:
                if action in (Completed_actions.change_agreemtent_text,Completed_actions.change_agreemtent):
                    alert_o = copy.deepcopy(DTKRO.alerts.edit)
                    break

        if alert_o:
            alert_o.send_alert(DTKRO.current_kro_o)


DTKRO.alerts = Alerts()


class Kro_manager():
    """
    kro_manager_o = MKRO()
    #======================Заполняем поле КРО==================================
    for it in data_mk:
        mk_num = int(it["Пномер"])
        it['КРО']= kro_manager_o.get_kro_info_by_mk(mk_num)
    # ========================================================
    def fnc_open_kro(t:CQT.TableContext, i:int,name_clm:str,self:mywindow, *args):
        mk = int(t.get_row(i).value('Пномер'))
        kro_manager_o.start_sub_app_kro(self, mk)

    t.add_column_events('КРО',on_double_click=fnc_open_kro,parent_self=self)
    """


    def __init__(self):
        self.dict_kro:dict[int,list[dict]]|None = None
        self.dict_gr_poz_mk:dict[int,list[dict]]|None = None
        self.update_dict_kros()

    def update_dict_kros(self):
        self.dict_kro = Kros.get_dict_kro()

    def get_kro_info_by_mk(self,mk:int,list_dse_id:list[int]|None =None)->str:

        if mk not in self.dict_kro:
            return ""

        filtred_kro_data = self.dict_kro[mk]
        if list_dse_id:
            filtred_kro_data = []
            set_dse_id = set(list_dse_id)

            for data_kro in self.dict_kro[mk]:

                set_dse_kro = set([int(_) for _ in data_kro['id_dse_list'].split(',')])
                intersection = set_dse_kro & set_dse_id
                if intersection:
                    filtred_kro_data.append(data_kro)

        count = len(filtred_kro_data)
        pref = ''
        if count>1:
            pref = f'{count} карт(ы):\n'
        return pref + ';\n'.join([_["msg"] for _ in filtred_kro_data])


    def start_sub_app_kro(self,app_self, mk:int|None=None,poz:int|None=None):
        if poz:
            dict_gr_poz_mk = self.calc_dict_gr_poz_mk()
            list_mk = []
            if poz in dict_gr_poz_mk:
                list_mk = [_['mk'] for _ in dict_gr_poz_mk[poz]]
            fl_is_kro_found = False
            for mk in list_mk:

                if mk in self.dict_kro:
                    fl_is_kro_found = True
                    break
            if fl_is_kro_found:
                window_kro = Krowindow(app_self, Regimes.report, filter_mk=list_mk)
                window_kro.showMaximized()
            else:
                window_kro = Krowindow(app_self, Regimes.insert)
                window_kro.showMaximized()
            return

        if mk not in self.dict_kro:
            window_kro = Krowindow(app_self, Regimes.insert, filter_mk=mk)
            window_kro.showMaximized()
            return
        window_kro = Krowindow(app_self, Regimes.report, filter_mk=mk)
        window_kro.showMaximized()

    def calc_dict_gr_poz_mk(self)->dict[int,list]:
        if self.dict_gr_poz_mk is None:
            self.dict_gr_poz_mk = F.grouping_list_dicts(CSQ.custom_request_c(DTCLS.CONFIG.project.db_naryad,
                                                   f"""SELECT Пномер as mk, НомКплан as kpl FROM mk;""",
                                                   rez_dict=True), 'kpl')
        return self.dict_gr_poz_mk

if __name__ == "__main__":
    app = CQT.QtWidgets.QApplication(sys.argv)
    window_kro = Krowindow(None, Regimes.report)
    window_kro.showMaximized()
    sys.exit(app.exec())

r"""
СТО-ОП2-1 
6.3.4 Карта разрешений отклонений от требований документации (КРО) оформляется в случаях: 

- необходимости изменений в конструкции изделий без изменения РКД по причине временного (единичного) отклонения от 
требований чертежа. В этом случае КД остается без изменений и в изначальном виде может быть применена для изготовления 
изделий в последующих заказах. 

- необходимости изменения в конструкции изделий с внесением изменений в РКД. Причем РКД может меняться как частично 
(к примеру, добавлены/исключены или исправлены позиции на чертежах, виды, технические требования, материал, сортамент 
и т.п.), так и чертеж заменен полностью в новой редакции. Это же относится и к спецификациям сборочных единиц, файлам 
dxf или csv, ресурсным спецификациям. 

6.3.5 КРО является официальным документом, позволяющим проводить и отслеживать изменения в КД в процессе изготовления 
изделий (см.п.6.3.4). 

6.3.6 Инициатором КРО считается подразделение Организации, по причине которого необходимо внести отклонение(я) в 
требования чертежа. 

6.3.7 Присваивание номера КРО должно быть с привязкой к проекту по направлениям оборудования: КТ, ШПС (ШСВ, ШСГ, ШДГ), 
КЛ, ЛК, АСО-ПГ (АСО-ВД-1, …) и т.д. 

Пример присвоения номера: КРО №1 КЛ.1903011.002. 

6.3.8 Если КРО на проект (заказ на производства) будет несколько, то различать КРО между собой необходимо по номеру 
(№1, №2 и т.д.) и дате запуска КРО. 

6.3.9 Номера КРО присваиваются и вносятся в таблицу файла «Журнал учета КРО» (Приложение Г) на общем диске О в папке 
O:\Журналы и графики\КРО. 

6.3.10 После присвоения номера и внесения его в Журнал учета КРО, инициатор заполняет файл КРО (образец файла КРО 
лежит на общем диске О в папке O:\Журналы и графики\КРО) и направляет его с прикрепленными документами (основанием 
для запуска КРО) главному конструктору, руководителю направления СГК и специалисту ОТД для заполнения КРО в своей 
ответственности и корректировки документации с учетом п.6.3.4. 

6.3.11 Руководитель направления СГК или специалист ОТД направляет сообщение на общую почту plan@powerz.ru (для примера:
 «Создана КРО №1 КЛ.1903011.002») для немедленного оповещения причастных служб и замены РКД в производстве 
 согласно СТО 18-2019 и одновременно выкладывает: 

- файл КРО на общий диск О в папку (для примера O:\Журналы и графики\КРО\1903011\КРО №1\) для заполнения КРО
причастными службами; 

- скорректированную документацию согласно этой КРО. 

6.3.12 Причастные службы (ОГТ, основное производство, производство-склад, ОТК, ОСиЛ) заполняют (при необходимости) и
 согласовывают КРО в установленном порядке не более 3-х рабочих дней. 

Контроль за заполнением и согласованием КРО осуществляет специалист ОТД СГК. 

6.3.13 После полного согласования КРО в электронном виде на общем диске О, специалист ОТД сообщает главному 
конструктору и руководителю направления СГК, после чего главный конструктор утверждает или отклоняет КРО (по 
объективным причинам, описанным в КРО при электронном согласовании). 

6.3.14 После утверждения/отклонения, КРО не подлежит дальнейшему редактированию без согласования с главным 
конструктором. 

6.3.15 Специалист ОТД распечатывает согласованную в электронном виде КРО на бумажный носитель и отдает на 
подпись специалистам причастных служб, ответственных за заполнение/согласование КРО, после чего КРО сканируется 
и прикрепляется к заказу в ERP. 


7.4.1. Изменения или замены редакций документов на всех стадиях жизненного цикла изделия вносят на основании КРО 
(Приложение А) или ИИ(Приложение Б), которые разрабатывает инициатор при появлении такой необходимости.
7.4.2 Внесение изменения в подлинники РКД, при необходимости, осуществляет конструктор направления - разработчика РКД.
7.4.3 Карта разрешений отклонений от требований документации (КРО) оформляется в случаях:
- необходимости изменений в конструкции изделий без изменения РКД по причине временного (единичного) отклонения от 
требований чертежа. В этом
случае КД остается без изменений и в изначальном виде может быть применена для изготовления изделий в последующих
 заказах. 

Причем РКД может меняться как частично (к примеру, добавлены/исключены или исправлены позиции на чертежах, виды, 
технические требования, материал, сортамент и т.п.), так и чертеж заменен полностью в новой редакции. Это же относится
 и к спецификациям сборочных единиц, файлам dxf или csv, ресурсным спецификациям.
7.4.4 Инициатором КРО считается подразделение Организации, по причине которого необходимо внести отклонение(я) в 

требования чертежа. Инициатор может поручить оформление КРО или ИИ от своего имени служебной запиской другому
 подразделению.
7.4.5 Присвоение номера КРО или ИИ должно быть с привязкой к проекту по направлениям оборудования: КТ, ШПС (ШСВ, 
ШСГ, ШДГ), КЛ, ЛК, АСО-ПГ (АСО-ВД-1, …) и т.д.
Пример присвоения номера КРО: №1 КЛ.1903011.002.
7.4.6 Если КРО на проект (заказ на производства) будет несколько, то различать КРО между собой необходимо по 
номеру (№1, №2 и т.д.) и дате запуска КРО.
7.4.7 Номера КРО и ИИ присваиваются и вносятся в таблицу файла «Журнал учета КРО» (Приложение В) на общем диске О 
в папке O:\Журналы и графики\КРО.
7.4.8 После присвоения номера и внесения его в Журнал учета КРО и ИИ, разработчик:
- заполняет файл преобразует его в pdf формат.
- подписывает и помещает его с прикрепленными документами (основанием для запуска КРО или ИИ) в папку для согласования и
- создаёт задачу в Битрикс (направляет по маршруту бизнес-процесса в PDM) для заполнения КРО или ИИ каждым специалистом 
в части своей ответственности и корректировки документации. Причастные службы (ОГТ, основное производство, 
производство-склад, ОТК, и др.) заполняют (при необходимости) и согласовывают КРО или ИИ в установленном порядке 
общим сроком не более 3-х рабочих дней. Контроль за заполнением и согласованием КРО или ИИ осуществляет разработчик.
7.4.9 После согласования КРО или ИИ, разработчик направляет его в Архив ОТД. Специалист ОТД направляет сообщения 
в соответствии с указаниями рассылки. Например, на общую почту plan@powerz.ru 
(для примера: «Создана КРО №1 КЛ.1903011.002») для немедленного оповещения причастных служб и замены РКД в Архиве ОТД 
и одновременно выкладывает ссылку на папку, содержащую:
- заполненный файл КРО в формате pdf;
- ссылку на скорректированную документацию согласно этой КРО.
7.4.10 После утверждения/отклонения, КРО или ИИ не подлежит дальнейшему редактированию без согласования с главным 
конструктором.
7.4.11 ИИ проводится как в РКД, так и в монтажно-сопроводительной документации после изготовления и завершения 
проекта в результате выявленных несоответствий как внутри Организации, так и со стороны заказчика.
7.4.12 Допускается выпускать одно ИИ по нескольким причинам изменения, относящихся к одной группе или нескольким 
группам однотипных изделий. Причины и коды указывают в соответствующей графе.
7.4.13 ИИ должно содержать не более 30 листов. Если изменения касаются одной группы, т.е. одной позиции проекта или 
группы однотипных изделий, то разрешают оформить объёмом более 30 листов.
7.4.14 Конструктор направления - разработчика РКД после оформления ИИ передает ее в ОТД, что является основанием для 
вывода, согласования и замены чертежей подлинников с последующим размножением измененных чертежей, выдачей их в 
подразделения Организации (при необходимости), а также внесения изменений в ЭА.
7.4.15 Подписи согласующих специалистов на КРО или ИИ подразумевают согласование изменений в РКД, которая к нему 
прилагается. Повторное согласование РКД не требуется. В штампе чертежа указывается номер изменения, обозначение
 документа на изменение и подпись разработчика. 
"""