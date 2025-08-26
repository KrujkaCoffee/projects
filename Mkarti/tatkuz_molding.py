from __future__ import annotations
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
from attr._make import fields
from project_cust_38 import Cust_config as CFG
import project_cust_38.Cust_docs as CDCS
from typing import TYPE_CHECKING
import project_cust_38.api_erp_commands as APIERP
from PyQt5.QtWidgets import QLabel
import project_cust_38.Cust_resource_creator as CRES
if TYPE_CHECKING:
    from MKart import mywindow

PARAMS_FIELDS_MOLDING_DB = CMS.DocumentedVariables('tatkuz_molding')
TYPES_MOLDING_ORDERS_TCH:dict = CSQ.dict_types_tbl(CFG.Config.project.db_dse,"molding_orders_tch")


class Stages_order_mold:
    _DICT_STAGES =  CSQ.custom_request_c(CFG.Config.project.db_dse, f"""SELECT * 
                  FROM molding_order_stages;
                """, rez_dict=True)
    _DICT_STAGES_BY_NUM = F.deploy_dict_c(_DICT_STAGES, 's_num')
    _DICT_STAGES_BY_NAME = F.deploy_dict_c(_DICT_STAGES, 'name')
    def __init__(self,snum:int):
        self.snum = snum
        self.name = Stages_order_mold._DICT_STAGES_BY_NUM[self.snum]['name']
        self.description = Stages_order_mold._DICT_STAGES_BY_NUM[self.snum]['description']
        self.percent = Stages_order_mold._DICT_STAGES_BY_NUM[self.snum]['percent']

    def next(self):
        if self.snum + 1 in Stages_order_mold._DICT_STAGES_BY_NUM:
            self.__init__(self.snum + 1)

    def __str__(self):
        return self.name
    def __repr__(self):
        return self.snum
class Ttkz_tmp_settings:
    def __init__(self,lbl_info:QLabel):
        self._lbl_info = lbl_info
        self.current_snum:int|None=None
        self.current_order:OrderMold|None=None
        self.current_stage:int|None=None
        self.allow_stage:int|None=None
        self.list_res:list[dict]|None=None
        self.view_mode:bool|None =None

    def clear(self):
        self.current_stage=0
        self.current_order=None
        self.current_snum=None
        self.view_mode = True
        self.allow_stage=0

    def update_lbl_info(self: mywindow,modify=False):
        info_str = ''
        postfix = ''
        if modify:
            postfix = ' *'
        if self.current_order:
            name = Stages_order_mold._DICT_STAGES_BY_NUM[self.current_stage]["name"]
            info_str = f"""№ {self.current_snum} - {self.current_order.tkp_name_proc_docs} (Стадия: "{name}"){postfix}"""
        self._lbl_info.setText(info_str)



class OrdersDocs:
    def __init__(self,):
        self.DICT_ALIASES = {
            "iD_card": "id_card_docs",
            "шифрИзделия_card": "product_code_card_docs",
            "номерПроекта_card": "project_number_card_docs",
            "номерПозиции_card": "position_number_card_docs",
            "наименование_card": "card_name_card_docs",
            "датаСоздания_card": "card_date_create_card_docs",
            "названиеВарианта_card": "card_variant_card_docs",
            "ссылкаДокс_card": "link_card_docs",
            "iD_proc": "id_processes_tkp_proc_docs",
            "ответственный_proc": "responsible_proc_docs",
            "комментарий_proc": "comment_proc_docs",
            "наименование_proc": "tkp_name_proc_docs",
            "этап_proc": "stage_proc_docs",
            "исполнитель_proc": "executor_proc_docs",
            "датаЗапуска_proc": "start_date_proc_docs",
            "статус_proc": "status_proc_docs",
            "желаемаяДата_proc": "wish_date_proc_docs",
            "кодРС_proc": "res_code_proc_docs",
            "ссылкаДокс_proc": "link_proc_docs",

        }
        self.SET_EXCLUDED_FIELDS = {
'wish_date_proc_docs',"res_code_proc_docs"
        }
        
        self._db = CFG.Config.project.db_dse
        LIMIT_SECS = 300
        data_cach = CMS.load_tmp_stukt("orders_tatkuz_for_molding",False)
        fl_load_from_srv = True
        if data_cach:
            delta = (F.now('') - F.strtodate(data_cach['date'])).seconds
            if delta < LIMIT_SECS:
                fl_load_from_srv = False
        if fl_load_from_srv:
            with CDCS.TFlexTkpProcessClient() as client:
                key, data  = client.get_process_tkp_from_fittings_folder()
            if not key == 200:
                CQT.msgbox(f'Ошибка получения данных из DOCs код {key}')
                data = data_cach['data']
            else:
                CMS.save_tmp_stukt({"data": data, "date": F.now()}, "orders_tatkuz_for_molding")
        else:
            data = data_cach['data']
        self.list_orders_docs = []


        for i, item in enumerate(data):
            new_item = dict()
            for k,v in item.items():
                if k in self.DICT_ALIASES and self.DICT_ALIASES[k] not in self.SET_EXCLUDED_FIELDS :
                    new_item[k] = v
            data[i] = new_item

        data = CSQ.apply_alias_list(data,self.DICT_ALIASES)

        self.list_orders_docs = data
        list_mes = CSQ.custom_request_c(self._db, f"""SELECT s_num 
                         FROM molding_orders;
                       """, one_column=True,hat_c=False)
        set_orders_mes = set(list_mes)

        list_keys = ['s_num','date']
        list_vals = []
        for docs_order in self.list_orders_docs:
            id_proc = docs_order["id_processes_tkp_proc_docs"]
            date = F.datetostr(F.strtodate(docs_order["start_date_proc_docs"],"%Y-%m-%dT%H:%M:%S"),"%Y-%m-%d %H:%M:%S")
            if id_proc not in set_orders_mes:
                list_vals.append([id_proc,date])
        if list_vals:
            result = CSQ.custom_request_c(self._db,
                                          f"""Insert INTO molding_orders ({CSQ.prepare_list_to_tuple(list_keys)}) VALUES ({CSQ.questions_for_mask(list_keys)})""",
                                          list_of_lists_c=list_vals)
            if not result:
                CQT.msgbox(f'Ошибка объединения с DOCs')
                return
        for item in self.list_orders_docs:
            item.pop("start_date_proc_docs",None)
            if item["link_card_docs"]:
                item['id_card_docs'] = '|'.join([item["link_card_docs"],str(item['id_card_docs'])])
            item.pop("link_card_docs", None)
            item["link_proc_docs"] = '|'.join([item["link_proc_docs"],str(item['id_processes_tkp_proc_docs'])])

class OrdersMolding:
    def __init__(self):
        self.resp_objs = None
        self._db = CFG.Config.project.db_dse
        self._obj_list_docs_data = OrdersDocs()

    def load_orders(self,where:str=None):
        postfix= ''
        if where:
            postfix = f""" WHERE {where}"""
        resp = CSQ.custom_request_c(self._db,f"""SELECT * 
                  FROM molding_orders {postfix};
                """,rez_dict=True)
        resp = F.left_join(resp,self._obj_list_docs_data.list_orders_docs,"s_num","id_processes_tkp_proc_docs")
        resp_objs = []
        for item in resp:
            obj_mold = OrderMold(item)
            resp_objs.append(obj_mold)
        self.resp_objs = resp_objs

    def load_order_by_num(self,num:int)->OrderMold:
        orders = self.load_orders(where=f"""s_num == {num}""")
        return self.resp_objs[0]

    def get_list_dict(self):
        data = [_.get_dict() for _ in self.resp_objs]
        return data

    def get_headers_orders(self):
        headers = CSQ.list_of_columns_c(self._db,'molding_orders',False)
        return headers


class OrderMold:
    def __init__(self,data:dict|None=None):
        if data == None:
            data = dict()
            data['date'] = F.now()
            data['user'] = F.user_name()
        self._ttkz_tmp_settings:Ttkz_tmp_settings|None = None
        self._db = CFG.Config.project.db_dse
        self._modify:bool= False
        self.s_num = None
        self.order_stage: Stages_order_mold | int | None = None
        self.date = None
        self.documents_link = None
        self.kolichestvo_otlivok_v_1_peschanoi_forme = None
        self.massa_1_otlivki_netto_godnogo = None
        self.massa_godnogo = None
        self.tvg = None
        self.massa_metalla_v_forme_brutto = None
        self.gabarity_koma_dlina = None
        self.gabarity_koma_shirina = None
        self.gabarity_koma_vysota = None
        self.massa_peschanoi_formy_bez_zhidkogo_metalla_kg = None
        self.ploshchad_vnutrennei_poverkhnosti_yashchika = None
        self.perimetr_razema_koma = None
        self.diametr_otkrytoi_pribyli = None
        self.kolichestvo_sterzhnevykh_yashchikov = None
        self.dlina_sterzhnevogo_yashchika = None
        self.shirina_sterzhnevogo_yashchika = None
        self.vysota_sterzhnevogo_yashchika = None
        self.kolichestvo_ekzotermicheskikh_vstavok_na_1_kom = None
        self.id_card_docs = None
        self.id_processes_tkp_proc_docs = None
        self.product_code_card_docs = None
        self.project_number_card_docs = None
        self.position_number_card_docs = None
        self.card_name_card_docs = None
        self.responsible_proc_docs = None
        self.comment_proc_docs = None
        self.tkp_name_proc_docs = None
        self.stage_proc_docs = None
        self.executor_proc_docs = None
        self.status_proc_docs = None
        self.card_date_create_card_docs = None
        self.card_variant_card_docs = None
        self.link_card_docs = None
        self.id_processes_tkp_proc_docs = None
        self.link_proc_docs = None
        self.materials_for_alloy:str|None = None
        self.materials_for_lining:str|None = None
        self.name_nomen_for_forming:str|None = None
        self.materials_for_forming:str|None = None
        self._tch: OrderMoldTch|None = None
        self._tch_res_product: OrderMoldTch|None = None
        if data:
            self._row = data
            for key in self._row.keys():
                exec(f'self.{str(key).replace(".", "_")} = self._row[key]')
        self.order_stage = Stages_order_mold(self.order_stage)
        print()

    def is_modify(self):
        return self._modify
    def set_modify(self, val:bool=True):
        self._modify = val
        self._ttkz_tmp_settings.update_lbl_info(self._modify)

    def get_name_by_val(self,val):
        data = self.get_dict(wo_docs=True)
        for k, v in data.items():
            if str(v).strip() ==  str(val).strip():
                return k

    def set_next_stage(self):
        self.order_stage.next()
        if not CFG.Config.user_config.is_developer: # 25.07.25
            CMS.send_info_mk_b24_by_action(
                f'''[B]Перевод в стадию '{self.order_stage.name}'[/B]:
                        >> ТКП: {self._ttkz_tmp_settings._lbl_info.text()}
                        >> ФИО: {CMS.b24_notation_user_fio()}
                        ''',
                'ТКП ТатКуз')

    def save(self):
        data = self.get_dict(wo_docs=True)
        data['order_stage'] = data['order_stage'].snum
        if self.s_num:
            list_keys = list(data.keys())
            list_vals = [data[_] for _ in list_keys]
            result = CSQ.custom_request_c(self._db, f"""UPDATE molding_orders SET 
            ({CSQ.prepare_list_to_tuple(list_keys)}) = ({CSQ.questions_for_mask(list_keys)}) WHERE s_num == {self.s_num} """,
                                 list_of_lists_c=[list_vals])
        else:
            data.pop('s_num')
            data = {k:v for k,v in data.items() if v != None}
            list_keys = list(data.keys())
            list_vals = [data[_] for _ in list_keys]
            result = CSQ.custom_request_c(self._db,
                                 f"""Insert INTO molding_orders 
                                 ({CSQ.prepare_list_to_tuple(list_keys)}) VALUES ({CSQ.questions_for_mask(list_keys)})""",
                                 list_of_lists_c=[list_vals])

        self.set_modify()
        return result

    def delete_order(self):
        result = CSQ.custom_request_c(self._db,f"""DELETE FROM molding_orders WHERE s_num == {self.s_num}""")
        return result

    def get_dict(self,wo_docs=False):
        if  wo_docs:
            res_dict = {k:v for k,v in self.__dict__.items() if k[0] != "_" and not k.endswith("_docs")}
        else:
            res_dict = {k:v for k,v in self.__dict__.items() if k[0] != "_"}
        return res_dict

    def load_tch(self) -> OrderMoldTch:
        stage_order = 2
        tchs_data = CSQ.custom_request_c(self._db,f"""SELECT * FROM molding_orders_tch WHERE order_mold == {self.s_num} and stage_order == {stage_order}""",rez_dict=True)
        self._tch = OrderMoldTch(self.s_num,stage_order,tchs_data)
        return self._tch

    def load_tch_res_product(self) -> OrderMoldTch:
        stage_order = 3
        tchs_data = CSQ.custom_request_c(self._db,f"""SELECT * FROM molding_orders_tch WHERE order_mold == {self.s_num} and stage_order == {stage_order}""",rez_dict=True)
        self._tch_res_product = OrderMoldTch(self.s_num,stage_order,tchs_data)
        return self._tch_res_product

    def get_tch_tbl(self):
        return self._tch.get_list()

    def get_tch_res_product_tbl(self):
        return self._tch_res_product.get_list()


class OrderMoldTch:
    DICT_BASE_MATS = {
    "00-00153566": {"fnc": "pesok_dla_hts_processa"},
    "00-00151960": {"fnc": "smola_dla_alfaset_processa"},
    "00-00153161": {"fnc": "otverditel_dla_alfaset_processa_20"},
    "00-00167505": {"fnc": "vsp_pesok_dla_hts_processa"},
    "00-00160602": {"fnc": "litejnoe_razdelitelnoe_pokrytie_lrp_2001"},
    "00-00161379": {"fnc": "litejnyj_klej_masterm"},
    "00-00153565": {"fnc": "protivoprigarnoe_pokrytie_cirkon_dla_alfaset_processa"},
    "00-00157077": {"fnc": "vstavka_ekzotermicheskaya_shp_3"},
    "00-00151950": {"fnc": "ekzotermicheskaya_pokrovnaya_smes_poroshok"}
}
    DICT_BASE_MATS_RES_PRODUCT = {
        "materials_for_alloy": {"fnc": "calc_materials_for_alloy"},
        "materials_for_forming": {"fnc": "calc_materials_for_forming"},
        "materials_for_lining": {"fnc": "calc_materials_for_lining"},
    }

    @classmethod
    def dict_base_mats_snum(cls, DICT_NOMEN:dict):
        return {str(DICT_NOMEN[k]['Пномер']):v for k,v in cls.DICT_BASE_MATS.items()}


    DICT_ALIASES = {"val":"Значение",
                    "mat_kod": "Материал код",
                    's_num':'s_num',
                    'order_mold':'order_mold',
                    'autocalc':'АвтоРасчет',
                    'stage_order':'stage_order',
                    }
    def __init__(self,order_num:int,stage_order:int,data:list|None=None):
        self.order_num = order_num
        self._db = CFG.Config.project.db_dse
        if data == None:
            data = CSQ.custom_request_c(self._db,f"""SELECT * FROM molding_orders_tch WHERE order_mold == {self.order_num} and stage_order == {stage_order}""",rez_dict=True)
        self._list:list|None = None
        self.data = []
        self._list = data
        self._stage_order = stage_order
        for row in self._list:
            self.data.append(OrderMoldTchRow(row))

    def find_row_by_s_num(self, snum:int) -> OrderMoldTchRow|None:
        for item in self.data:
            if item.s_num == snum:
                return item

    def add_new_row(self) -> OrderMoldTchRow:
        vals = [self.order_num,self._stage_order]
        result = CSQ.custom_request_c(self._db,f"""INSERT INTO molding_orders_tch (order_mold,stage_order) VALUES ({CSQ.questions_for_mask(vals)}) RETURNING *""",
                                      list_of_lists_c=vals, rez_dict=True)
        self.data.append(OrderMoldTchRow(result[0]))
        return self.data[-1]
    def get_list(self):
        return [_.get_dict() for _ in self.data]

    def get_val_by_code(self,code:str):
        for item in self.data:
            if item.mat_kod == code:
                return item.val


    def save_data(self):
        for row in self.data:
            row.save_row_tch()

    def delete_row(self,snum:int):
        row = self.find_row_by_s_num(snum)
        if row:
            row._delete()
        for item in self.data:
            if item.s_num == snum:
                self.data.remove(item)
                break
class OrderMoldTchRow:
    DICT_ALIASES = OrderMoldTch.DICT_ALIASES
    def __init__(self,row:dict|None=None):
        if row == None:
            row = dict()
        self._db = CFG.Config.project.db_dse
        self.s_num = None
        self.order_mold = None
        self.mat_kod = None
        self.val = None
        self.autocalc = None
        if row:
            self._row = row
            for key in self._row.keys():
                exec(f'self.{str(key).replace(".", "_")} = self._row[key]')

    def get_dict(self):
        res_dict = {k:v for k,v in self.__dict__.items() if k[0] != "_"}
        return res_dict

    def save_row_tch(self):
        data = self.get_dict()
        list_keys = list(data.keys())
        list_vals = [data[_] for _ in list_keys]
        result = CSQ.custom_request_c(self._db, f"""UPDATE molding_orders_tch SET 
                    ({CSQ.prepare_list_to_tuple(list_keys)}) = ({CSQ.questions_for_mask(list_keys)}) WHERE s_num == {self.s_num} """,
                                      list_of_lists_c=[list_vals])
        return  result

    def load_row_tch_by_snum(self,s_num:int):
        data = CSQ.custom_request_c(self._db,f"""SELECT * FROM molding_orders_tch WHERE s_num == {s_num}""",rez_dict=True,one=True)
        self.__init__(data)

    def name_from_aliases(self,alias:str):

        for k,v in OrderMoldTchRow.DICT_ALIASES.items():
            if v == alias:
                return k
        return alias

    def _delete(self):
        CSQ.custom_request_c(self._db, f"""DELETE FROM molding_orders_tch WHERE s_num == {self.s_num}""", rez_dict=True,
                             one=True)


def ______________Tch__________________():
    pass

@CQT.onerror
def tab_rs_tch_currentChanged(self: mywindow):
    if self._ttkz_tmp_settings.view_mode:
        return
    self.ui.btn_add_row_mold_tch.setEnabled(False)
    self.ui.btn_del_row_mold_tch.setEnabled(False)
    self.ui.btn_upload_1c_mold_tch.setEnabled(False)
    tab = self.ui.tab_rs_tch
    if self._ttkz_tmp_settings.current_stage == 2:
        if tab.currentIndex() == CQT.number_table_by_name_c(tab,'Материалы на формовку'):
            self.ui.btn_add_row_mold_tch.setEnabled(True)
            self.ui.btn_del_row_mold_tch.setEnabled(True)
            self.ui.btn_upload_1c_mold_tch.setEnabled(True)
    if self._ttkz_tmp_settings.current_stage == 3:
        if tab.currentIndex() == CQT.number_table_by_name_c(tab,'Итоговая РС на изделие'):
            self.ui.btn_add_row_mold_tch.setEnabled(True)
            self.ui.btn_del_row_mold_tch.setEnabled(True)
            self.ui.btn_upload_1c_mold_tch.setEnabled(True)


@CQT.onerror
def mold_tch_itemSelectionChanged(self: mywindow):
    if self._ttkz_tmp_settings.view_mode:
        self.ui.btn_del_row_mold_tch.setEnabled(False)
        return
    self.ui.btn_del_row_mold_tch.setEnabled(True)
    tbl = self.ui.tbl_data_mold_tch
    row = tbl.currentRow()
    row_data = CQT.get_dict_line_form_tbl(tbl, row)
    if row_data['Материал код'] in OrderMoldTch.DICT_BASE_MATS:
        self.ui.btn_del_row_mold_tch.setEnabled(False)
@CQT.onerror
def mold_tch_res_product_itemSelectionChanged(self: mywindow):
    if self._ttkz_tmp_settings.view_mode:
        self.ui.btn_del_row_mold_tch.setEnabled(False)
        return
    self.ui.btn_del_row_mold_tch.setEnabled(True)
    tbl = self.ui.tbl_data_mold_tch_res_product
    row = tbl.currentRow()
    row_data = CQT.get_dict_line_form_tbl(tbl, row)
    mat = row_data['Материал код']
    if not F.is_numeric(mat):
        mat = self._ttkz_tmp_settings.current_order.get_name_by_val(mat)
    if mat in OrderMoldTch.DICT_BASE_MATS_RES_PRODUCT:
        self.ui.btn_del_row_mold_tch.setEnabled(False)


@CQT.onerror
def mold_tch_res_product_cellchanged(self: mywindow,row:int,col:int):
    tbl = self.ui.tbl_data_mold_tch_res_product
    row_data = CQT.get_dict_line_form_tbl(tbl,row)
    s_num = row_data['s_num']
    key_name = tbl.horizontalHeaderItem(col).text()
    new_val = tbl.item(row,col).text()
    row_obj = OrderMoldTchRow()
    row_obj.load_row_tch_by_snum(int(s_num))
    name_attr = row_obj.name_from_aliases(key_name)
    old_val = row_obj.__dict__[name_attr]
    err = False
    if key_name== 'Материал код':
        dict_nomen = get_mat_data(self.DICT_NOMEN_BY_SNUM,new_val)
        if dict_nomen:
            new_val = dict_nomen['КодИсточник']
        else:
            err = True
    if not err:
        try:
            if TYPES_MOLDING_ORDERS_TCH[name_attr] in (int,float):
                new_val_form = F.valm(new_val)
            else:
                new_val_form =f'"{str(new_val)}"'
            exec(f"row_obj.{name_attr} = {new_val_form}")
        except:
            err = True
    if not err:
        if not row_obj.save_row_tch():
            err = True

    if err:
        CQT.msgbox(f'Ошибка сохранения')
        CQT.tbl_set_val_wo_signal(tbl,row,col,str(old_val))
            #tbl.item(row,col).setText(str(old_val))
    recalc_base_complex_mold_tch(self)
    load_order_tch_res_product(self, self._ttkz_tmp_settings.current_order,False)
@CQT.onerror
def mold_tch_cellchanged(self: mywindow,row:int,col:int):
    tbl = self.ui.tbl_data_mold_tch
    row_data = CQT.get_dict_line_form_tbl(tbl,row)
    s_num = row_data['s_num']
    key_name = tbl.horizontalHeaderItem(col).text()
    new_val = tbl.item(row,col).text()
    row_obj = OrderMoldTchRow()
    row_obj.load_row_tch_by_snum(int(s_num))
    name_attr = row_obj.name_from_aliases(key_name)
    old_val = row_obj.__dict__[name_attr]
    err = False
    if key_name== 'Материал код':
        try:
            new_val = self.DICT_NOMEN[new_val]['Пномер']
        except:
            CQT.msgbox(f'Материал с кодом {new_val} не найден в MES')
            err = True
    if not err:
        try:
            if TYPES_MOLDING_ORDERS_TCH[name_attr] in (int,float):
                new_val_form = F.valm(new_val)
            else:
                new_val_form =f'"{str(new_val)}"'
            exec(f"row_obj.{name_attr} = {new_val_form}")
        except:
            err = True
    if not err:
        if not row_obj.save_row_tch():
            err = True

    if err:
        CQT.msgbox(f'Ошибка сохранения')
        CQT.tbl_set_val_wo_signal(tbl,row,col,str(old_val))
            #tbl.item(row,col).setText(str(old_val))
    recalc_base_complex_mold_tch(self)
    load_order_tch(self, self._ttkz_tmp_settings.current_order,False)
@CQT.onerror
def recalc_base_complex_res_product_tch(self:mywindow):
    order:OrderMold = self._ttkz_tmp_settings.current_order
    def code_to_snum(code:str):
        return self.DICT_NOMEN[code]['Пномер']
    def snum_to_code(snum:int):
        return self.DICT_NOMEN_BY_SNUMEN[snum]['Код']
    def calc_materials_for_alloy(order: OrderMold, row: OrderMoldTchRow) -> float:
        return order.massa_1_otlivki_netto_godnogo/order.tvg*100
    def calc_materials_for_forming(order: OrderMold, row: OrderMoldTchRow) -> float:
        return 1/order.kolichestvo_otlivok_v_1_peschanoi_forme
    def calc_materials_for_lining(order: OrderMold, row: OrderMoldTchRow) -> float:
        kg_litya_20gl = order.massa_1_otlivki_netto_godnogo/order.tvg*100  # кг. Литья 20ГЛ
        iz_600_kg_litya_poluchitsya_kryshek = F.round_down(600/kg_litya_20gl)   # из 600 кг литья получится крышек
        na_1_kryshku_kg_uydet_litya_20gl = 600/iz_600_kg_litya_poluchitsya_kryshek  # на 1 крышку кг уйдет литья 20ГЛ
        kryshek_iz_litya_na_ves_cikl_dejstviya_futerovki = (600*25)/na_1_kryshku_kg_uydet_litya_20gl  # крышек из литья на весь цикл действия футеровки
        return 1/kryshek_iz_litya_na_ves_cikl_dejstviya_futerovki

    tch: OrderMoldTch = order.load_tch_res_product()

    for row in tch.data:
        mat_name = order.get_name_by_val(row.mat_kod)
        if row.autocalc and mat_name and mat_name in OrderMoldTch.DICT_BASE_MATS_RES_PRODUCT :
            fnc = OrderMoldTch.DICT_BASE_MATS_RES_PRODUCT[mat_name]['fnc']
            try:
                row.val =round(eval(f'{fnc}(order,row)'),2)
            except:
                pass
    tch.save_data()
    #load_order_tch_res_product(self,order)
@CQT.onerror
def recalc_base_complex_mold_tch(self:mywindow):
    order:OrderMold = self._ttkz_tmp_settings.current_order
    def code_to_snum(code:str):
        return self.DICT_NOMEN[code]['Пномер']
    def snum_to_code(snum:int):
        return self.DICT_NOMEN_BY_SNUMEN[snum]['Код']
    def pesok_dla_hts_processa(order: OrderMold, row: OrderMoldTchRow) -> float:
        """Возвращает количество песка для ХТС-процесса."""
        return order.massa_peschanoi_formy_bez_zhidkogo_metalla_kg/2

    def smola_dla_alfaset_processa(order: OrderMold, row: OrderMoldTchRow) -> float:
        """Возвращает количество смолы для Альфасет-процесса."""
        return  order.massa_peschanoi_formy_bez_zhidkogo_metalla_kg*0.02

    def otverditel_dla_alfaset_processa_20(order: OrderMold, row: OrderMoldTchRow) -> float:
        """Возвращает количество отвердителя для Альфасет-процесса (20%)."""

        smola_dla_alfaset_processa = tch.get_val_by_code(code_to_snum('00-00151960'))
        if smola_dla_alfaset_processa:
            return smola_dla_alfaset_processa/4
        return 0

    def vsp_pesok_dla_hts_processa(order: OrderMold, row: OrderMoldTchRow) -> float:
        """Возвращает количество ВСП песка для ХТС-процесса."""
        return order.massa_peschanoi_formy_bez_zhidkogo_metalla_kg/2

    def litejnoe_razdelitelnoe_pokrytie_lrp_2001(order: OrderMold, row: OrderMoldTchRow) -> float:
        """Возвращает количество литейного разделительного покрытия ЛРП-2001."""
        return order.ploshchad_vnutrennei_poverkhnosti_yashchika*0.06

    def litejnyj_klej_masterm(order: OrderMold, row: OrderMoldTchRow) -> float:
        """Возвращает количество литейного клея MASTERM."""
        return order.perimetr_razema_koma*0.00003

    def protivoprigarnoe_pokrytie_cirkon_dla_alfaset_processa(order: OrderMold, row: OrderMoldTchRow) -> float:
        """Возвращает количество противопригарного покрытия Циркон для Альфасет-процесса."""
        return order.ploshchad_vnutrennei_poverkhnosti_yashchika*0.05

    def vstavka_ekzotermicheskaya_shp_3(order: OrderMold, row: OrderMoldTchRow) -> int:
        """Возвращает количество экзотермических вставок СХП-3."""
        return order.kolichestvo_ekzotermicheskikh_vstavok_na_1_kom

    def ekzotermicheskaya_pokrovnaya_smes_poroshok(order: OrderMold, row: OrderMoldTchRow) -> float:
        """Возвращает количество экзотермической покровной смеси (порошок)."""
        return order.diametr_otkrytoi_pribyli*0.0015

    tch: OrderMoldTch = order.load_tch()
    base_code_erp = set(OrderMoldTch.DICT_BASE_MATS.keys())
    for row in tch.data:
        if row.autocalc and row.mat_kod in base_code_erp :
            fnc = OrderMoldTch.DICT_BASE_MATS[row.mat_kod]['fnc']
            try:
                row.val =round(eval(f'{fnc}(order,row)'),2)
            except:
                pass
    tch.save_data()
    #load_order_tch(self,order)


@CQT.onerror
def add_base_complex_res_product_tch(self:mywindow):
    order = self._ttkz_tmp_settings.current_order
    num_res_alloy= order.materials_for_alloy
    num_res_forming= order.materials_for_forming
    num_res_lining= order.materials_for_lining
    tch_res_product:OrderMoldTch = order.load_tch_res_product()
    attended_codes = {_.mat_kod for _ in tch_res_product.data}
    for mat_kod in (num_res_alloy,num_res_forming,num_res_lining):
        if mat_kod not in attended_codes:
            new_row:OrderMoldTchRow = tch_res_product.add_new_row()
            new_row.mat_kod = mat_kod
    tch_res_product.save_data()
    recalc_base_complex_res_product_tch(self)
    pass
@CQT.onerror
def add_base_complex_mold_tch(self:mywindow):
    order = self._ttkz_tmp_settings.current_order
    tch:OrderMoldTch = order.load_tch()
    attended_codes = { self.DICT_NOMEN_BY_SNUM[int(_.mat_kod)]['Код'] if F.is_numeric(_.mat_kod) else _.mat_kod  for _ in tch.data}

    #base_code_mes = set(OrderMoldTch.dict_base_mats_snum(self.DICT_NOMEN).keys())
    base_code_erp = set(OrderMoldTch.DICT_BASE_MATS.keys())

    for mat_kod in base_code_erp:
        if mat_kod not in attended_codes:
            new_row:OrderMoldTchRow = tch.add_new_row()
            new_row.mat_kod = mat_kod
    tch.save_data()
    recalc_base_complex_mold_tch(self)
    pass


def load_order_tch_res_product(self: mywindow, order_obj: OrderMold, view_mode: bool):
    def fnc_set_autocalc_mode(checked, row, col):

        tbl_tch.item(row, col).setText(str(F.valm(checked)))

    tbl_tch = self.ui.tbl_data_mold_tch_res_product
    tbl_tchf = self.ui.tbl_data_mold_tch_res_product_filtr
    order_obj.load_tch_res_product()
    tch_data = order_obj.get_tch_res_product_tbl()
    editeble_col_nomera = {}
    if not view_mode:
        editeble_col_nomera = {"Значение", "Материал код"}
    tch_data_al = CSQ.apply_alias_list(tch_data, OrderMoldTch.DICT_ALIASES)
    for row in tch_data_al:
        row["Наименование"] = "Не найден в номенклатуре"
        row["ЕдиницаИзмерения"] = ''
        if row["Материал код"]:
            dict_nomen = get_mat_data(self.DICT_NOMEN_BY_SNUM, row["Материал код"])
            if dict_nomen:
                row["Наименование"] = dict_nomen['Наименование']
                row["ЕдиницаИзмерения"] = dict_nomen['ЕдиницаИзмерения']
                row["Материал код"] = dict_nomen['КодИсточник']

    CQT.fill_wtabl(tch_data_al, tbl_tch, set_editeble_col_nomera=editeble_col_nomera,
                   list_column_widths=CMS.load_column_widths(self, tbl_tch), save_column_sort_hh=True, auto_type=False,
                   min_width_col=0)

    nf_mat = CQT.num_col_by_name_c(tbl_tch, 'Материал код')
    nf_autocalc = CQT.num_col_by_name_c(tbl_tch, 'АвтоРасчет')

    for i in range(tbl_tch.rowCount()):
        row = CQT.get_dict_line_form_tbl(tbl_tch, i)
        for j in range(tbl_tch.columnCount()):
            if not view_mode and tbl_tch.horizontalHeaderItem(j).text() in editeble_col_nomera:
                CQT.set_cell_editable(tbl_tch, i, j, True)
            else:
                CQT.set_cell_editable(tbl_tch, i, j, False)
                CQT.set_font_color_wtab_c(tbl_tch, i, j, 100, 100, 100)
        mat_name = row['Материал код']
        if not F.is_numeric(mat_name):
            mat_name = order_obj.get_name_by_val(row['Материал код'])
        if mat_name in OrderMoldTch.DICT_BASE_MATS_RES_PRODUCT:
            CQT.set_cell_editable(tbl_tch, i, nf_mat, False)
            CQT.set_font_color_wtab_c(tbl_tch, i, nf_mat, 100, 100, 100)
            CQT.add_check_box(tbl_tch, i, nf_autocalc, val=F.boolm(row['АвтоРасчет']),
                              conn_func_checked_row_col=fnc_set_autocalc_mode, enabled=not view_mode)
        else:
            CQT.tbl_set_val_wo_signal(tbl_tch, i, nf_autocalc, '')
            # tbl_tch.item(i,nf_autocalc).setText('')
    if not CFG.Config.user_config.is_developer: # 25.07.25
        tbl_tch.setColumnHidden(CQT.num_col_by_name_c(tbl_tch,"s_num",-1),True)
        tbl_tch.setColumnHidden(CQT.num_col_by_name_c(tbl_tch,"order_mold",-1),True)
        tbl_tch.setColumnHidden(CQT.num_col_by_name_c(tbl_tch,"stage_order",-1),True)
    CMS.fill_filtr_c(self, tbl_tchf, tbl_tch, hidden_scroll=True)
def load_order_tch(self: mywindow, order_obj: OrderMold, view_mode: bool):
    def fnc_set_autocalc_mode(checked, row, col):

        tbl_tch.item(row, col).setText(str(F.valm(checked)))

    tbl_tch = self.ui.tbl_data_mold_tch
    tbl_tchf = self.ui.tbl_data_mold_tch_filtr
    order_obj.load_tch()
    tch_data = order_obj.get_tch_tbl()
    editeble_col_nomera = {}
    if not view_mode:
        editeble_col_nomera = {"Значение", "Материал код"}
    tch_data_al = CSQ.apply_alias_list(tch_data, OrderMoldTch.DICT_ALIASES)
    for row in tch_data_al:
        row["Наименование"] = "Не найден в номенклатуре"
        row["ЕдиницаИзмерения"] = ''
        if row["Материал код"]:
            dict_nomen = get_mat_data(self.DICT_NOMEN_BY_SNUM, row["Материал код"])
            if dict_nomen:
                row["Наименование"] = dict_nomen['Наименование']
                row["ЕдиницаИзмерения"] = dict_nomen['ЕдиницаИзмерения']
                row["Материал код"] = dict_nomen['КодИсточник']


    CQT.fill_wtabl(tch_data_al, tbl_tch, set_editeble_col_nomera=editeble_col_nomera,
                   list_column_widths=CMS.load_column_widths(self, tbl_tch), save_column_sort_hh=True, auto_type=False,
                   min_width_col=0)

    nf_mat = CQT.num_col_by_name_c(tbl_tch, 'Материал код')
    nf_autocalc = CQT.num_col_by_name_c(tbl_tch, 'АвтоРасчет')

    for i in range(tbl_tch.rowCount()):
        row = CQT.get_dict_line_form_tbl(tbl_tch, i)
        for j in range(tbl_tch.columnCount()):
            if not view_mode and tbl_tch.horizontalHeaderItem(j).text() in editeble_col_nomera:
                CQT.set_cell_editable(tbl_tch, i, j, True)
            else:
                CQT.set_cell_editable(tbl_tch, i, j, False)
                CQT.set_font_color_wtab_c(tbl_tch, i, j, 100, 100, 100)

        if row['Материал код'] in OrderMoldTch.DICT_BASE_MATS:
            CQT.set_cell_editable(tbl_tch, i, nf_mat, False)
            CQT.set_font_color_wtab_c(tbl_tch, i, nf_mat, 100, 100, 100)
            CQT.add_check_box(tbl_tch, i, nf_autocalc, val=F.boolm(row['АвтоРасчет']),
                              conn_func_checked_row_col=fnc_set_autocalc_mode, enabled=not view_mode)
        else:
            CQT.tbl_set_val_wo_signal(tbl_tch, i, nf_autocalc, '')
            # tbl_tch.item(i,nf_autocalc).setText('')
    if not CFG.Config.user_config.is_developer: #25.07.25
        columns_for_hide = ("s_num", "order_mold", "stage_order")
        for column in columns_for_hide:
            current_index = CQT.num_col_by_name_c(tbl_tch,column)
            if CQT.num_col_by_name_c(tbl_tch,column) is not None:
                tbl_tch.setColumnHidden(current_index, True)
    CMS.fill_filtr_c(self, tbl_tchf, tbl_tch, hidden_scroll=True)

@CQT.onerror
def del_row_mold_tch(self:mywindow):
    if not self._ttkz_tmp_settings.current_stage in (2, 3):
        return
    order = OrdersMolding().load_order_by_num(self._ttkz_tmp_settings.current_snum)
    if self._ttkz_tmp_settings.current_stage == 2:
        tbl = self.ui.tbl_data_mold_tch
        tch = order.load_tch()
    if self._ttkz_tmp_settings.current_stage == 3:
        tbl = self.ui.tbl_data_mold_tch_res_product
        tch = order.load_tch_res_product()
    row_data = CQT.get_dict_line_form_tbl(tbl)
    if not row_data:
        return
    s_num = row_data['s_num']
    tch.delete_row(int(s_num))
    self._ttkz_tmp_settings.view_mode = False
    if self._ttkz_tmp_settings.current_stage == 2:
        load_order_tch(self, order,self._ttkz_tmp_settings.view_mode)
    if self._ttkz_tmp_settings.current_stage == 3:
        load_order_tch_res_product(self, order, self._ttkz_tmp_settings.view_mode)



@CQT.onerror
def add_row_mold_tch(self:mywindow):
    if not self._ttkz_tmp_settings.current_stage in (2,3):
        return
    order = OrdersMolding().load_order_by_num(self._ttkz_tmp_settings.current_snum)
    self._ttkz_tmp_settings.view_mode = False
    if self._ttkz_tmp_settings.current_stage == 2:
        tch = order.load_tch()
        tch.add_new_row()
        load_order_tch(self, order, self._ttkz_tmp_settings.view_mode)
    if self._ttkz_tmp_settings.current_stage == 3:
        tch = order.load_tch_res_product()
        tch.add_new_row()
        load_order_tch_res_product(self, order, self._ttkz_tmp_settings.view_mode)



def ___________Orders_____________():
    pass
@CQT.onerror
def oform_tbl(self:mywindow,data:list[dict]):
    dict_states = {
    'Отменён':0,
    'Завершён':100,
    'В очереди':30,
    'В работе':55
    }
    tbl = self.ui.tbl_list_orders_mold
    nf_state_docs = CQT.num_col_by_name_c(tbl,'Cтатус в\nDocs')
    nf_state_mes = CQT.num_col_by_name_c(tbl,'Стадия ТКП')

    for i in range(tbl.rowCount()):
        if nf_state_docs:
            state = tbl.item(i,nf_state_docs).text()
            clr = CMS.Color_tbl(dict_states[state])
            CQT.set_color_wtab_c(tbl,i,nf_state_docs,clr.r,clr.g,clr.b)
        if nf_state_mes:
            state:Stages_order_mold = data[i]['Стадия ТКП']
            clr =  CMS.Color_tbl(state.percent)
            CQT.set_color_wtab_c(tbl,i,nf_state_mes,clr.r,clr.g,clr.b)


@CQT.onerror
def load_form_rs_for_molding(self:mywindow, *args):

    tbl = self.ui.tbl_list_orders_mold
    CQT.set_color_sort_cell_table_c(tbl)
    selected_row = tbl.currentRow()
    selected_ind = tbl.currentIndex()
    orders = OrdersMolding()
    orders.load_orders()
    data = orders.get_list_dict()
    if not data:
        data = [orders.get_headers_orders()]
    data = PARAMS_FIELDS_MOLDING_DB.apply_alias_list(data)
    CQT.fill_wtabl(data, tbl,load_links=True,selectionBehavior='SelectRows',selectionMode='SingleSelection',
                   sortingEnabled=True,list_column_widths=CMS.load_column_widths(self,tbl),
                   save_column_sort_hh=True)
    CMS.fill_filtr_c(self,self.ui.tbl_list_orders_mold_filtr,tbl,hidden_scroll=True)
    self._ttkz_tmp_settings.clear()
    self._ttkz_tmp_settings.update_lbl_info()
    oform_tbl(self,data)
    load_lists_res(self)
    tbl.setCurrentIndex(selected_ind)
    self.ui.fr_data_mold.setVisible(False)
    if not selected_row == -1:
        load_order_data(self)
    print()


@CQT.onerror
def load_lists_res(self:mywindow):
    LIMIT_SECS = 300
    NAME_TMP_STUKT = "lists_res_tatkuz_for_molding"
    data_cach = CMS.load_tmp_stukt(NAME_TMP_STUKT, False)
    fl_load_from_srv = True
    if data_cach:
        delta = (F.now('') - F.strtodate(data_cach['date'])).seconds
        if delta < LIMIT_SECS:
            fl_load_from_srv = False
    if fl_load_from_srv:
        wet_req_text = f"""ВЫБРАТЬ
        РесурсныеСпецификации.Наименование КАК Наименование,
        РесурсныеСпецификации.Код КАК Код,
        РесурсныеСпецификации.Статус КАК Статус,
        РесурсныеСпецификации.НачалоДействия КАК НачалоДействия,
        РесурсныеСпецификации.КонецДействия КАК КонецДействия,
        РесурсныеСпецификации.ПометкаУдаления КАК ПометкаУдаления,
        РесурсныеСпецификации.Описание КАК Описание
    ИЗ
        Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
    ГДЕ
        РесурсныеСпецификации.ПометкаУдаления = ЛОЖЬ
        И РесурсныеСпецификации.ЭтоГруппа = ЛОЖЬ
        И РесурсныеСпецификации.Родитель.Код = "00-058862";"""
        key, data_rez = APIERP.get_wet_request(wet_req_text)
        if key != 200:
            CQT.msgbox(f'Ошибка получения данных код ({key}) из ERP')
            return
        CMS.save_tmp_stukt({"data": data_rez, "date": F.now()}, NAME_TMP_STUKT)
    else:
        data_rez = data_cach['data']

    self._ttkz_tmp_settings.list_res = data_rez['data']



@CQT.onerror
def select_order(self: mywindow):
    if self._ttkz_tmp_settings.current_order:
        if self._ttkz_tmp_settings.current_order.is_modify():
            if CQT.msgboxgYN(f'Имеются не сохраненные изменения. Продолжить редактирование?'):
                return
    self._ttkz_tmp_settings.view_mode = True
    load_order_data(self)


@CQT.onerror
def new_order(self: mywindow):
    self._ttkz_tmp_settings.clear()
    load_order_data(self, 0)

@CQT.onerror
def add_sand_data(self: mywindow):
    self._ttkz_tmp_settings.view_mode = False
    load_order_data(self, 1)




@CQT.onerror
def mat_mold_calc(self: mywindow):
    self._ttkz_tmp_settings.view_mode = False
    load_order_data(self, 2)


@CQT.onerror
def create_res_product(self: mywindow):
    self._ttkz_tmp_settings.view_mode = False
    load_order_data(self, 3)
    pass




def ___________Order_____________():
    pass

@CQT.onerror
def calc_stage(self:mywindow):
    tbl = self.ui.tbl_list_orders_mold
    row = CQT.get_dict_line_form_tbl(tbl)
    s_num = int(row['Пномер'])
    order_obj: OrderMold = OrdersMolding().load_order_by_num(s_num)
    order_obj._ttkz_tmp_settings=self._ttkz_tmp_settings
    row = order_obj.get_dict()
    stage = 4
    for k,v in row.items():
        name = k
        if name == None or name not in PARAMS_FIELDS_MOLDING_DB.dict_vars or name.endswith("_docs"):
            continue
        if  PARAMS_FIELDS_MOLDING_DB.dict_vars[name].Этап == 0:
            continue
        stage_field = PARAMS_FIELDS_MOLDING_DB.dict_vars[name].Этап+1
        if PARAMS_FIELDS_MOLDING_DB.dict_vars[name].is_numeric:
            v = F.valm(v)
        if PARAMS_FIELDS_MOLDING_DB.dict_vars[name].РазрешенНульИПусто:
            v = True
        if stage_field <= stage and not v:
            stage = stage_field -1
    if stage == 3 and not order_obj.load_tch().data:
        stage = 2
    self._ttkz_tmp_settings.current_order = order_obj
    self._ttkz_tmp_settings.current_snum = int(row['s_num'])
    self._ttkz_tmp_settings.allow_stage = stage
    self._ttkz_tmp_settings.current_stage = self._ttkz_tmp_settings.current_order.order_stage.snum
    if self._ttkz_tmp_settings.allow_stage < self._ttkz_tmp_settings.current_order.order_stage.snum:
        self._ttkz_tmp_settings.current_order.order_stage.snum = self._ttkz_tmp_settings.allow_stage
        self._ttkz_tmp_settings.current_order.save()

def apply_next_stage(self:mywindow):
    stage = self._ttkz_tmp_settings.current_stage
    allow_stage = self._ttkz_tmp_settings.allow_stage
    if stage >= allow_stage:
        return
    self._ttkz_tmp_settings.current_order.set_next_stage()
    self._ttkz_tmp_settings.current_order.save()
    load_form_rs_for_molding(self)

def apply_stage(self:mywindow):
    stage = self._ttkz_tmp_settings.current_order.order_stage.snum
    allow_stage = self._ttkz_tmp_settings.allow_stage
    btn_sand_data = self.ui.btn_sand_data
    btn_mat_mold_calc = self.ui.btn_mat_mold_calc
    btn_upload_1c_mold_tch = self.ui.btn_upload_1c_mold_tch
    btn_add_row_mold_tch = self.ui.btn_add_row_mold_tch
    btn_del_row_mold_tch = self.ui.btn_del_row_mold_tch
    btn_apply_data_mold = self.ui.btn_apply_data_mold
    btn_cancel_data_mold = self.ui.btn_cancel_data_mold
    btn_res_product = self.ui.btn_res_product
    btn_apply_next_stage = self.ui.btn_apply_next_stage


    tab_rs_tch = self.ui.tab_rs_tch
    fr_rs_tch = self.ui.fr_rs_tch

    tab_materials_for_forming_ind = CQT.number_table_by_name_c(tab_rs_tch,'Материалы на формовку')
    tab_res_product_ind = CQT.number_table_by_name_c(tab_rs_tch,'Итоговая РС на изделие')


    btn_sand_data.setEnabled(False)
    btn_mat_mold_calc.setEnabled(False)


    fr_rs_tch.setVisible(False)
    tab_rs_tch.setTabVisible(tab_materials_for_forming_ind, False)
    tab_rs_tch.setTabVisible(tab_res_product_ind, False)

    btn_add_row_mold_tch.setEnabled(False)
    btn_del_row_mold_tch.setEnabled(False)
    btn_apply_data_mold.setEnabled(False)
    btn_cancel_data_mold.setEnabled(False)
    btn_res_product.setEnabled(False)
    btn_upload_1c_mold_tch.setEnabled(False)
    btn_apply_next_stage.setEnabled(False)

    btn_apply_next_stage.setText(f'Завершить стадию {Stages_order_mold._DICT_STAGES_BY_NUM[stage]["name"]}')
    if stage< allow_stage:
        btn_apply_next_stage.setEnabled(True)


    if stage == 0:
        btn_sand_data.setEnabled(False)
        btn_mat_mold_calc.setEnabled(False)

        btn_add_row_mold_tch.setEnabled(False)
        btn_del_row_mold_tch.setEnabled(False)
        btn_apply_data_mold.setEnabled(True)
        btn_cancel_data_mold.setEnabled(True)
    if stage == 1:  # песочная форма
        btn_sand_data.setEnabled(True)
        btn_mat_mold_calc.setEnabled(False)
        btn_add_row_mold_tch.setEnabled(False)
        btn_del_row_mold_tch.setEnabled(False)
        btn_apply_data_mold.setEnabled(True)
        btn_cancel_data_mold.setEnabled(True)
    if stage == 2:  # материалы
        btn_sand_data.setEnabled(False)
        btn_mat_mold_calc.setEnabled(True)

        fr_rs_tch.setVisible(True)
        tab_rs_tch.setTabVisible(tab_materials_for_forming_ind, True)
        btn_add_row_mold_tch.setEnabled(True)
        btn_del_row_mold_tch.setEnabled(True)
        btn_upload_1c_mold_tch.setEnabled(True)
        btn_apply_data_mold.setEnabled(True)
        btn_cancel_data_mold.setEnabled(True)
    if stage == 3:  # ресурсная
        btn_sand_data.setEnabled(False)
        btn_mat_mold_calc.setEnabled(False)
        btn_add_row_mold_tch.setEnabled(True)
        btn_del_row_mold_tch.setEnabled(True)
        btn_upload_1c_mold_tch.setEnabled(True)
        btn_apply_data_mold.setEnabled(True)
        btn_cancel_data_mold.setEnabled(True)
        fr_rs_tch.setVisible(True)
        tab_rs_tch.setTabVisible(tab_materials_for_forming_ind, True)
        tab_rs_tch.setTabVisible(tab_res_product_ind, True)
        tab_rs_tch.setCurrentIndex(CQT.number_table_by_name_c(tab_rs_tch, 'Итоговая РС на изделие'))
        btn_res_product.setEnabled(True)
    if stage == 4:  # готово
        btn_sand_data.setEnabled(False)
        btn_mat_mold_calc.setEnabled(False)
        btn_add_row_mold_tch.setEnabled(False)
        btn_del_row_mold_tch.setEnabled(False)
        btn_apply_data_mold.setEnabled(False)
        btn_cancel_data_mold.setEnabled(False)
        fr_rs_tch.setVisible(True)
        tab_rs_tch.setTabVisible(tab_materials_for_forming_ind, True)
        tab_rs_tch.setTabVisible(tab_res_product_ind, True)
        tab_rs_tch.setCurrentIndex(CQT.number_table_by_name_c(tab_rs_tch, 'Итоговая РС на изделие'))
        btn_upload_1c_mold_tch.setEnabled(False)
        btn_res_product.setEnabled(False)
        if CFG.Config.user_config.is_developer: #25.07.25
            btn_upload_1c_mold_tch.setEnabled(True)
            btn_res_product.setEnabled(True)

    if self._ttkz_tmp_settings.view_mode:
        btn_apply_data_mold.setEnabled(False)
        btn_cancel_data_mold.setEnabled(False)
        btn_add_row_mold_tch.setEnabled(False)
        btn_del_row_mold_tch.setEnabled(False)
        btn_upload_1c_mold_tch.setEnabled(False)
    CQT.clear_tbl(self.ui.tbl_data_mold_tch)
    CQT.clear_tbl(self.ui.tbl_data_mold_tch_res_product)
    self.ui.fr_data_mold.setVisible(True)

@CQT.onerror
def load_order_data(self: mywindow, edit_etap_num=9):
    def fcn_select_res(lnk, i, j, name, file,parent_self, *args):
        def fnc_oform_tbl_res(tbl):
            pass
        def fnc_select_tbl_res(tbl):
            pass

        result = CQT.msgboxg_get_table(self,f'Выбор ресурсной',self._ttkz_tmp_settings.list_res,'Выбор',
                              func_oform_tbl=fnc_oform_tbl_res,
                              func_btn0=fnc_select_tbl_res,
                              ExtendedSelection=False,selectRows=True, styleSheet=CQT.ERP_CSS,sortingEnabled=True)
        if result:
            res_code = result['Код']
            tbl.item(i,j).setText(res_code)
            tbl.cellWidget(i,j).deleteLater()
            CQT.add_label_link(tbl, i, j, res_code, res_code, fcn_select_res, self)


    def fcn_select_name_nomen_for_forming(lnk, i, j, name, file,parent_self, *args):
            def fnc_oform_tbl(tbl):
                pass
            def fnc_select_tbl(tbl):
                pass

            wet_req_text = f"""ВЫБРАТЬ
    Номенклатура.Наименование КАК Наименование,
    Номенклатура.Код КАК Код,
    Номенклатура.ВидНоменклатуры.Наименование КАК ВидНоменклатуры
ИЗ
    Справочник.Номенклатура КАК Номенклатура
ГДЕ
    Номенклатура.ПометкаУдаления = ЛОЖЬ
    И Номенклатура.ВидНоменклатуры.Родитель.Наименование = "ТАТКУЗ"
    И (Номенклатура.ВидНоменклатуры.Наименование = "Стандартные изделия" ИЛИ Номенклатура.ВидНоменклатуры.Наименование = "Сырьё для сплава");"""
            key, data_rez = APIERP.get_wet_request(wet_req_text)
            if key != 200:
                CQT.msgbox(f'Ошибка получения данных код ({key}) из ERP')
                return
            result = CQT.msgboxg_get_table(self,f'Выбор номенклатуры',data_rez['data'],'Выбор',
                                  func_oform_tbl=fnc_oform_tbl,
                                  func_btn0=fnc_select_tbl,
                                  ExtendedSelection=False,selectRows=True, styleSheet=CQT.ERP_CSS,sortingEnabled=True)
            if result:
                res_code = result['Код']
                tbl.item(i,j).setText(res_code)
                tbl.cellWidget(i,j).deleteLater()
                CQT.add_label_link(tbl,i,nf_val,res_code,res_code,fcn_select_name_nomen_for_forming,self)



    if edit_etap_num:
        calc_stage(self)
    if edit_etap_num == 2:
        load_lists_res(self)
        if self._ttkz_tmp_settings.current_order.name_nomen_for_forming:
            add_base_complex_mold_tch(self)
    if edit_etap_num == 3:
        load_lists_res(self)
        if all((self._ttkz_tmp_settings.current_order.materials_for_alloy,
                self._ttkz_tmp_settings.current_order.materials_for_forming,
                self._ttkz_tmp_settings.current_order.materials_for_lining)) :
            add_base_complex_res_product_tch(self)
    apply_stage(self)
    self._ttkz_tmp_settings.update_lbl_info()
    cancel_new_or_edit_order(self)
    order_obj_dict = dict()
    if self._ttkz_tmp_settings.current_snum:
        order_obj: OrderMold = OrdersMolding().load_order_by_num(self._ttkz_tmp_settings.current_snum)
        order_obj_dict = order_obj.get_dict()
        view_mode = self._ttkz_tmp_settings.view_mode
        if not edit_etap_num == 2:
            view_mode = True
        load_order_tch(self, order_obj,view_mode)
        view_mode = self._ttkz_tmp_settings.view_mode
        if not edit_etap_num == 3:
            view_mode = True
        load_order_tch_res_product(self,order_obj,view_mode)
    tbl = self.ui.tbl_data_mold
    data = [{"stage": v.Этап, "Name": _, "Реквизит": v.БуквенноеОбозначение, "Значение": v.Default_val, "Ед.Изм.":v.ЕдиницаИзмерения, "Описание":v.Описание}
            for _, v in PARAMS_FIELDS_MOLDING_DB.dict_vars.items() if v.Видимый and v.Этап <= edit_etap_num]
    for item in data:
        if item['Name'] in order_obj_dict:
            item['Значение'] = order_obj_dict[item['Name']]
    data = F.sort_by_column_c(data,"stage",)

    CQT.fill_wtabl(data, tbl, set_editeble_col_nomera={"Значение"},list_column_widths=CMS.load_column_widths(self,tbl) )

    nf_val = CQT.num_col_by_name_c(tbl,"Значение")
    nf_req = CQT.num_col_by_name_c(tbl,"Реквизит")
    for i in range(tbl.rowCount()):
        row = CQT.get_dict_line_form_tbl(tbl,i)
        for j in range(tbl.columnCount()):
            CQT.set_cell_editable(tbl, i, j, False)
            CQT.set_font_color_wtab_c(tbl, i, j, 100, 100, 100)
            CQT.font_cell_size_format(tbl, i, j, bold=False)
        if int(row['stage']) == edit_etap_num:
            if PARAMS_FIELDS_MOLDING_DB.dict_vars[row['Name']].editable:
                CQT.set_cell_editable(tbl,i,nf_val,True)
                CQT.font_cell_size_format(tbl, i, nf_req,bold=True)

            if row['Name'] in ('materials_for_alloy','materials_for_lining'):
                link_name = row['Значение'].strip()
                if not link_name:
                    link_name = '     ...'
                CQT.add_label_link(tbl,i,nf_val,link_name,link_name,fcn_select_res,self)
                CQT.font_cell_size_format(tbl, i, nf_req, bold=True)
            if row['Name'] in ('name_nomen_for_forming','name_nomen_for_res_product'):
                link_name = row['Значение'].strip()
                if not link_name:
                    link_name = '     ...'
                CQT.add_label_link(tbl,i,nf_val,link_name,link_name,fcn_select_name_nomen_for_forming,self)
                CQT.font_cell_size_format(tbl, i, nf_req, bold=True)
    if not CFG.Config.user_config.is_developer: #25.07.25
        tbl.setColumnHidden(CQT.num_col_by_name_c(tbl,"stage",-1),True)
        tbl.setColumnHidden(CQT.num_col_by_name_c(tbl,"Name",-1),True)
    CMS.fill_filtr_c(self, self.ui.tbl_data_mold_filtr, tbl, hidden_scroll=True)
    print()

def ___________Order_data____________():
    pass
@CQT.onerror
def data_mold_cellchanged(self: mywindow,row:int,col:int):
    tbl = self.ui.tbl_data_mold
    data = CQT.list_from_wtabl_c(tbl,rez_dict=True)
    stage = self._ttkz_tmp_settings.current_stage
    if stage == 1:  # песочная форма
        calc_massa_godnogo(self,data)
        calc_tvg(self,data)
    if stage == 2:  # материалы
        pass
    self._ttkz_tmp_settings.current_order.set_modify()



@CQT.onerror
def apply_new_or_edit_order(self:mywindow):

    def check_new_order_data(data:list):
        return True

    tbl = self.ui.tbl_data_mold
    data = CQT.list_from_wtabl_c(tbl,rez_dict=True)
    if not check_new_order_data(data):
        return
    if self._ttkz_tmp_settings.current_stage > 0:
        order: OrderMold = self._ttkz_tmp_settings.current_order
    else:
        order = OrderMold()
    for item in data:
        if PARAMS_FIELDS_MOLDING_DB.dict_vars[item["Name"]].is_numeric:
            exec(f'order.{item["Name"]} = {F.valm(item["Значение"])}')
        else:
            exec(f'order.{item["Name"]} = "{item["Значение"]}"')
    if order.save():
        cancel_new_or_edit_order(self)
        load_form_rs_for_molding(self)
    if order.name_nomen_for_forming:
        add_base_complex_mold_tch(self)

@CQT.onerror
def cancel_new_or_edit_order(self:mywindow):
    CQT.clear_tbl(self.ui.tbl_data_mold)
    CQT.clear_tbl(self.ui.tbl_data_mold_filtr)
    CQT.clear_tbl(self.ui.tbl_data_mold_tch)
    CQT.clear_tbl(self.ui.tbl_data_mold_tch_filtr)
    self._ttkz_tmp_settings.current_order.set_modify(False)

def get_val_tbl_data_mold(data:list[dict],name:str):
    for item in data:
        if item['Name'] == name:
            return F.valm(item['Значение'])

def set_val_tbl_data_mold(self:mywindow,name:str,val):
    tbl = self.ui.tbl_data_mold
    nf_name = CQT.num_col_by_name_c(tbl,'Name')
    nf_val = CQT.num_col_by_name_c(tbl,'Значение')
    for i in range(tbl.rowCount()):
        if tbl.item(i,nf_name).text() == name:
            tbl.item(i, nf_val).setText(str(val))
            break
@CQT.onerror
def calc_massa_godnogo(self,data:list[dict]):
    try:
        kolichestvo_otlivok_v_1_peschanoi_forme = get_val_tbl_data_mold(data,'kolichestvo_otlivok_v_1_peschanoi_forme')
        massa_1_otlivki_netto_godnogo = get_val_tbl_data_mold(data,'massa_1_otlivki_netto_godnogo')
        massa_godnogo = kolichestvo_otlivok_v_1_peschanoi_forme * massa_1_otlivki_netto_godnogo
        massa_godnogo = round(massa_godnogo,PARAMS_FIELDS_MOLDING_DB.dict_vars['massa_godnogo'].КоличествоРазрядов)
        set_val_tbl_data_mold(self,'massa_godnogo',massa_godnogo)
    except:
        pass

@CQT.onerror
def calc_tvg(self,data:list[dict]):
    try:
        massa_metalla_v_forme_brutto = get_val_tbl_data_mold(data, 'massa_metalla_v_forme_brutto')
        massa_godnogo = get_val_tbl_data_mold(data, 'massa_godnogo')
        tvg = massa_godnogo / massa_metalla_v_forme_brutto * 100
        tvg = round(tvg, PARAMS_FIELDS_MOLDING_DB.dict_vars['tvg'].КоличествоРазрядов)
        set_val_tbl_data_mold(self, 'tvg', tvg)
    except:
        pass

def ___________SUPPORT__________():
    pass

def get_mat_data(DICT_NOMEN:dict, some_code:int|str, check_in_erp=False):
    if F.is_numeric(some_code):
        some_code = int(some_code)
        try:
            code = DICT_NOMEN[some_code]['Код']
        except:
            CQT.msgbox(f'Материал с кодом {some_code} не найден в MES')
            return
        Материалы_Статья_калькуляции = 'Сырье'
        if code in ('00-00167505'):
            Материалы_Статья_калькуляции = 'Возвратные отходы'

        Способы_получения_материала = "Обеспечивать"
        ЕдиницаИзмерения = DICT_NOMEN[some_code]['ЕдиницаИзмерения']
        КодИсточник = code
        code = code
        Наименование = DICT_NOMEN[some_code]['Наименование']
        is_found = None
        if check_in_erp:
            is_found = True
            wet_req_text = f"""ВЫБРАТЬ
                                Номенклатура.Наименование КАК Наименование,
                                Номенклатура.ЕдиницаИзмерения.Наименование КАК ЕдиницаИзмерения
                            ИЗ
                                Справочник.Номенклатура КАК Номенклатура

                            ГДЕ
                                Номенклатура.Код = "{code}"

                            ОБЪЕДИНИТЬ ВСЕ

                            ВЫБРАТЬ
                                РесурсныеСпецификации.Наименование,
                                РесурсныеСпецификации.ОсновноеИзделиеНоменклатура.ЕдиницаИзмерения.Наименование
                            ИЗ
                                Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
                            ГДЕ
                                РесурсныеСпецификации.Код = "{code}";"""
            key, data_rez = APIERP.get_wet_request(wet_req_text)
            if key != 200:
                CQT.msgbox(f'Ошибка получения данных код ({key}) из ERP')
                return
            if not data_rez['data']:
                CQT.msgbox(f'Материал с кодом {code} не найден в {CFG.Config.user_config.ERP_base_name["Значение"]}')
                is_found = False

    else:
        if len(some_code.strip())==11:
            wet_req_text = f"""ВЫБРАТЬ
                           Номенклатура.Наименование КАК Наименование,
                           Номенклатура.ЕдиницаИзмерения.Наименование КАК ЕдиницаИзмерения,
                            "Сырье" КАК Материалы_Статья_калькуляции,
                            "Обеспечивать" КАК Способы_получения_материала,
                            Номенклатура.Код  КАК КодНоменклатура,
                            Номенклатура.Код  КАК КодИсточник
                       ИЗ
                           Справочник.Номенклатура КАК Номенклатура

                       ГДЕ
                           Номенклатура.Код = "{some_code}"
                      ;"""

        else:

            wet_req_text = f"""
            ВЫБРАТЬ
                РесурсныеСпецификации.Наименование КАК  Наименование,
                РесурсныеСпецификации.ОсновноеИзделиеНоменклатура.ЕдиницаИзмерения.Наименование КАК ЕдиницаИзмерения,
                "Полуфабрикаты производимые в процессе" КАК Материалы_Статья_калькуляции,
                "Произвести по спецификации" КАК Способы_получения_материала,
                РесурсныеСпецификации.ОсновноеИзделиеНоменклатура.Код КАК КодНоменклатура,
                РесурсныеСпецификации.Код  КАК КодИсточник
            ИЗ
                Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
            ГДЕ
                РесурсныеСпецификации.Код = "{some_code}";"""

        key, data_rez = APIERP.get_wet_request(wet_req_text)
        if key != 200:
            CQT.msgbox(f'Ошибка получения данных код ({key}) из ERP')
            return
        if not data_rez['data']:
            CQT.msgbox(f'Материал с кодом {some_code} не найден в {CFG.Config.user_config.ERP_base_name["Значение"]}')
            return
        is_found = True
        code = data_rez['data'][0]['КодНоменклатура']
        ЕдиницаИзмерения = data_rez['data'][0]['ЕдиницаИзмерения']
        Материалы_Статья_калькуляции = data_rez['data'][0]['Материалы_Статья_калькуляции']
        Способы_получения_материала = data_rez['data'][0]['Способы_получения_материала']
        КодИсточник = data_rez['data'][0]['КодИсточник']
        Наименование = data_rez['data'][0]['Наименование']
    return {'code':code,
            'Наименование':Наименование,
            'ЕдиницаИзмерения':ЕдиницаИзмерения,
            'КодИсточник':КодИсточник,
            'Материалы_Статья_калькуляции':Материалы_Статья_калькуляции,
            'Способы_получения_материала':Способы_получения_материала,
            'is_found':is_found
            }


def ___________upload_1c____________():
    pass

@CQT.onerror
def upload_1c_mold(self:mywindow):
    if self._ttkz_tmp_settings.current_stage == 2:
        upload_1c_mold_tch(self)
    if self._ttkz_tmp_settings.current_stage in (3,4):
        upload_1c_res_product_tch(self)

@CQT.onerror
def upload_1c_res_product_tch(self:mywindow):
    def check():
        if not self._ttkz_tmp_settings.current_order.name_nomen_for_res_product:
            CQT.msgbox(f'Не выбрана/применена `Номенклатура изделия` ')
            return False
        return True

    @CQT.onerror
    def clear_res(code):
        data = {"data": {'Код': code}}
        code_resp, answ = APIERP.clear_res_json(data, self.USER_CONFIG.ERP_base_name['Значение'])
        if code_resp == 200:
            CQT.msgbox(f'Очищена ресурсная. \n{code}')
            return True
        else:
            CQT.msgbox(f'Ошибка очистки ресурсной. Код ошибки {code_resp}\n{answ["Ошибки"]}')
        return False

    def generate(tch_mold:OrderMoldTch,code_old_res=None):
        err = []#TODO 00-064111
        hat = dict()
        ПодразделениеДиспетчер = 'Сталелитейный цех (ТатКуз)'
        hat['ОсновноеИзделиеКод'] = self._ttkz_tmp_settings.current_order.name_nomen_for_res_product

        wet_req_text = f"""ВЫБРАТЬ
                Номенклатура.Наименование КАК Наименование
            ИЗ                
                Справочник.Номенклатура КАК Номенклатура
            ГДЕ
                Номенклатура.Код = "{hat['ОсновноеИзделиеКод']}";"""
        key, data_rez = APIERP.get_wet_request(wet_req_text)
        if key != 200:
            CQT.msgbox(f'Ошибка получения данных код ({key}) из ERP')
            return
        if not data_rez['data']:
            CQT.msgbox(f'Не найдено изделие код ({hat["ОсновноеИзделиеКод"]}) из ERP')
            return
        hat["Наименование ресурсной"] = data_rez['data'][0]['Наименование']


        hat['ТекущийПользователь'] = F.user_full_namre()
        hat['НачалоДействия'] = F.now("%d.%m.%Y")
        hat['КонецДействия'] = F.date_add_days(F.now(""),7,format_out="%d.%m.%Y")
        hat['Сохранять'] = True
        hat['ИмяБазы'] = CFG.Config.user_config.ERP_base_name['Значение']
        hat['КластерСерверов'] = self.Data_plan.DICT_BASES_ERP[hat['ИмяБазы']]['КластерСерверов']
        hat['Описание'] = ''
        hat['ПодразделениеДиспетчер'] = ПодразделениеДиспетчер
        hat['ВыпускПроизвольнымиПорциями'] = False
        hat['РодительКод'] = '00-058862'
        hat['ВариантПодбораВДокументы'] = "Вручную"
        hat['СпособРаспределенияЗатратНаВыходныеИзделия'] = "ПоДолямСтоимости"


        if code_old_res:
            hat['Код'] = code_old_res

        list_etaps = []
        new_mats = []
        vid_rab = 'литье'
        guid_vid_rab = self.DICT_VID_RABOT[vid_rab]['ref_Key_erp']

        for mat in tch_mold.data:
            if mat.val:
                dict_nomen = get_mat_data(self.DICT_NOMEN_BY_SNUM, mat.mat_kod)
                if not dict_nomen:
                    CQT.msgbox(
                        f'Ошибка расчета \n`{self.DICT_NOMEN_BY_SNUM[mat.mat_kod]["Наименование"]}`')
                    return
                mat_data = {
                         'Мат_код' : dict_nomen['code'],
                         'Мат_норма' : mat.val,
                         'Материалы_Статья_калькуляции' : dict_nomen['Материалы_Статья_калькуляции'],
                         'Способы_получения_материала' : dict_nomen['Способы_получения_материала'],
                            'ИсточникПолученияПолуфабриката': dict_nomen['КодИсточник']
                        }
                new_mats.append(mat_data)
            else:
                CQT.msgbox(
                    f'пропущен материал \n`{self.DICT_NOMEN_BY_SNUM[mat.mat_kod]["Наименование"]}`\nт.к. кол-во = 0')
        new_trs = dict()
        new_trs[guid_vid_rab] = 73
        ДлительностьЭтапа = 1440
        new_v = {'Опер_наименование_подразделения': ПодразделениеДиспетчер,
                 'Материалы': new_mats,
                 'Трудозатраты': new_trs,
                 'ДлительностьЭтапа':ДлительностьЭтапа}
        list_etaps.append({'Этап': 'литье', "Данные": new_v})


        if err:
            err.insert(0, ['Ошибки'])
            if not CQT.msgboxg_get_table(self, 'Ошибки компоновки', err,
                                         'Продолжить выгрузку', 'Прервать',
                                         show_filtr=False, use_first_row_as_header=True, print_hat=True,
                                         yesNoMode=True):
                return

        if list_etaps == None:
            return

        return {'hat': hat, 'data': list_etaps}


    def generate_res(tch_mold:OrderMoldTch,code_old_res=None) -> CRES.ResourceSpecification|None:

        err = []

        ПодразделениеДиспетчер = CRES.SubdivisionsData._hnt_сталелитейный_цех_таткуз_таткуз_00_000164
        ОсновноеИзделиеКод = CRES.MainProduct.find_by_code(self._ttkz_tmp_settings.current_order.name_nomen_for_res_product)

        РодительКод = CRES.GroupResData._hnt_литье_таткуз_00_058862
        ВариантПодбораВДокументы = CRES.VariationsrespecificationdocumentsData._hnt_вручную_1
        СпособРаспределенияЗатратНаВыходныеИзделия = CRES.TheMethodOfAllocatingTheCostOfTheOutputProductsData._hnt_по_долям_стоимости_0

        # Шапка
        hat = CRES.ResourceHeader(
            ОсновноеИзделиеКод=ОсновноеИзделиеКод,
            ТекущийПользователь=CRES.CurrentUser(F.user_full_namre()),
            ДатаНачала=F.now("%Y-%m-%d"),
            ДатаОкончания=F.date_add_days(F.now(""),7,format_out="%Y-%m-%d"),
            ПодразделениеДиспетчер=ПодразделениеДиспетчер,
            РодительКод=РодительКод,
            ВариантПодбораВДокументы=ВариантПодбораВДокументы,
            Описание='Создан из MES(Мкарты)',
            СпособРаспределенияЗатратНаВыходныеИзделия=СпособРаспределенияЗатратНаВыходныеИзделия,
            Код=code_old_res
        )


        # Этап
        Подразделение = CRES.SubdivisionsData._hnt_сталелитейный_цех_таткуз_таткуз_00_000164
        stage_data = CRES.StageData(
            Подразделение=Подразделение,
            ДлительностьМинут= 1440
        )
        # Материалы
        for mat in tch_mold.data:
            if mat.val:
                dict_nomen = get_mat_data(self.DICT_NOMEN_BY_SNUM, mat.mat_kod,True)
                if not dict_nomen:
                    CQT.msgbox(
                        f'Ошибка расчета \n`{mat.mat_kod}`')
                    return
                if not dict_nomen['is_found']:
                    CQT.msgbox(
                        f'пропущен материал \n`{mat.mat_kod}`\nт.к. не найден в ЕРП')
                    continue

                СпособПолучения = CRES.MethodOfObtainingMaterialspecificationsData.find_by_name(dict_nomen['Способы_получения_материала'])
                СтатьяКалькуляции = CRES.ArticulationArticlesData.find_by_name(dict_nomen['Материалы_Статья_калькуляции'])
                if СтатьяКалькуляции.name == 'Полуфабрикаты производимые в процессе':
                    ИсточникПолученияПолуфабриката = CRES.SourceOfTheHalffactoryReceipt.find_by_code(dict_nomen['КодИсточник'])
                else:
                    ИсточникПолученияПолуфабриката = CRES.SourceOfTheHalffactoryReceipt()
                mat = CRES.Material(dict_nomen['code'], mat.val, СтатьяКалькуляции, СпособПолучения,ИсточникПолученияПолуфабриката)
                stage_data.add_material(mat)
            else:
                CQT.msgbox(
                    f'пропущен материал \n`{mat.mat_kod}`\nт.к. кол-во = 0')

        # Трудозатраты
        ВидРабот = CRES.TypeOfWorkData.find_by_name('литье')
        labor = CRES.LaborCost(ВидРабот, 90)

        stage_data.add_labor(labor)

        stage = CRES.Stage('литье', stage_data)

        # Итог
        spec = CRES.ResourceSpecification(hat)
        spec.add_stage(stage)


        if err:
            err.insert(0, ['Ошибки'])
            if not CQT.msgboxg_get_table(self, 'Ошибки компоновки', err,
                                         'Продолжить выгрузку', 'Прервать',
                                         show_filtr=False, use_first_row_as_header=True, print_hat=True,
                                         yesNoMode=True):
                return

        return spec


    @CQT.onerror
    def send(data) -> dict|bool:
        code, answ = APIERP.post_res_json(data, self.USER_CONFIG.ERP_base_name['Значение'])
        if code == 200:
            return answ
        else:
            CQT.msgbox(f'Ошибка создания ресурсной. Код {code}\n{answ["Ошибки"]}')
        return False


    if not check():
        return

    tbl = self.ui.tbl_data_mold_tch_res_product
    code_old_res = None
    fl_refilled = False



    if self._ttkz_tmp_settings.current_order.res_product:#'Перезаполнить'
        code_old_res = self._ttkz_tmp_settings.current_order.res_product
        if not clear_res(code_old_res):
            return
        fl_refilled = True

    tch_mold = self._ttkz_tmp_settings.current_order.load_tch_res_product()
    spec_to_ERP = generate_res(tch_mold, code_old_res)

    if not spec_to_ERP:
        return
    data_answ = spec_to_ERP.send()
    spec_to_ERP.to_dict()
    #data_to_ERP = generate(tch_mold,code_old_res)
    #if not data_to_ERP:
    #    return
    #data_answ = send(data_to_ERP)
    if not data_answ:
        return
    code = data_answ['Код'].strip()
    if code:
        link = data_answ['Ссылка']
        CQT.msgbox(f'Успешно создана Код "{code}"',time_life=3)
        pref = 'Создана'
        if fl_refilled:
            pref = 'Очищена и перезаполнена'
        if not CFG.Config.user_config.is_developer: # 25.07.25
            CMS.send_info_mk_b24_by_action(
            f'''[B]{pref} Итоговая РС на изделие[/B]:
            >> ФИО: {CMS.b24_notation_user_fio()}
            >> НАИМЕНОВАНИЕ:{spec_to_ERP.hat.Наименование}
            >> КОД: [URL={link}]{code}[/URL]
            ''',
            'ТКП ТатКуз')

        self._ttkz_tmp_settings.current_order.res_product = str(code).strip()
        self._ttkz_tmp_settings.current_order.save()
        create_res_product(self)
@CQT.onerror
def upload_1c_mold_tch(self:mywindow):
    def check():
        if not self._ttkz_tmp_settings.current_order.name_nomen_for_forming:
            CQT.msgbox(f'Не выбрана/применена `Номенклатура изделия для формовки` ')
            return False
        return True

    @CQT.onerror
    def clear_res(code):
        data = {"data": {'Код': code}}
        code_resp, answ = APIERP.clear_res_json(data, self.USER_CONFIG.ERP_base_name['Значение'])
        if code_resp == 200:
            CQT.msgbox(f'Очищена ресурсная. \n{code}')
            return True
        else:
            CQT.msgbox(f'Ошибка очистки ресурсной. Код ошибки {code_resp}\n{answ["Ошибки"]}')
        return False

    def generate(tch_mold:OrderMoldTch,code_old_res=None):
        err = []
        hat = dict()
        ПодразделениеДиспетчер = 'Сталелитейный цех (ТатКуз)'
        hat['ОсновноеИзделиеКод'] = self._ttkz_tmp_settings.current_order.name_nomen_for_forming

        wet_req_text = f"""ВЫБРАТЬ
                Номенклатура.Наименование КАК Наименование
            ИЗ
                Справочник.Номенклатура КАК Номенклатура
            ГДЕ
                Номенклатура.Код = "{hat['ОсновноеИзделиеКод']}";"""
        key, data_rez = APIERP.get_wet_request(wet_req_text)
        if key != 200:
            CQT.msgbox(f'Ошибка получения данных код ({key}) из ERP')
            return
        if not data_rez['data']:
            CQT.msgbox(f'Не найдено изделие код ({hat["ОсновноеИзделиеКод"]}) из ERP')
            return
        hat["Наименование ресурсной"] = data_rez['data'][0]['Наименование']


        hat['ТекущийПользователь'] = F.user_full_namre()
        hat['НачалоДействия'] = F.now("%d.%m.%Y")
        hat['КонецДействия'] = F.date_add_days(F.now(""),7,format_out="%d.%m.%Y")
        hat['Сохранять'] = True
        hat['ИмяБазы'] = CFG.Config.user_config.ERP_base_name['Значение']
        hat['КластерСерверов'] = self.Data_plan.DICT_BASES_ERP[hat['ИмяБазы']]['КластерСерверов']
        hat['Описание'] = ''
        hat['ПодразделениеДиспетчер'] = None
        hat['ВыпускПроизвольнымиПорциями'] = False
        hat['РодительКод'] = '00-058862'
        hat['ВариантПодбораВДокументы'] = "Вручную"
        hat['СпособРаспределенияЗатратНаВыходныеИзделия'] = "ПоДолямСтоимости"
        if code_old_res:
            hat['Код'] = code_old_res

        list_etaps = []
        new_mats = []
        vid_rab = 'формовка'
        guid_vid_rab = self.DICT_VID_RABOT[vid_rab]['ref_Key_erp']

        for mat in tch_mold.data:
            if mat.val:
                dict_nomen = get_mat_data(self.DICT_NOMEN_BY_SNUM, mat.mat_kod,True)
                if not dict_nomen:
                    CQT.msgbox(
                        f'Ошибка расчета \n`{mat.mat_kod}`')
                    return
                if not dict_nomen['is_found']:
                    CQT.msgbox(
                        f'пропущен материал \n`{mat.mat_kod}`\nт.к. не найден в ЕРП')
                    continue
                mat_data = {
                    'Мат_код': dict_nomen['code'],
                    'Мат_норма': mat.val,
                    'Материалы_Статья_калькуляции': dict_nomen['Материалы_Статья_калькуляции'],
                    'Способы_получения_материала': dict_nomen['Способы_получения_материала']
                }
                new_mats.append(mat_data)
            else:
                CQT.msgbox(
                    f'пропущен материал \n`{mat.mat_kod}`\nт.к. кол-во = 0')
        new_trs = dict()
        new_trs[guid_vid_rab] = 90

        new_v = {'Опер_наименование_подразделения': ПодразделениеДиспетчер,
                 'Материалы': new_mats,
                 'Трудозатраты': new_trs}
        list_etaps.append({'Этап': 'формовка', "Данные": new_v})


        if err:
            err.insert(0, ['Ошибки'])
            if not CQT.msgboxg_get_table(self, 'Ошибки компоновки', err,
                                         'Продолжить выгрузку', 'Прервать',
                                         show_filtr=False, use_first_row_as_header=True, print_hat=True,
                                         yesNoMode=True):
                return

        if list_etaps == None:
            return

        return {'hat': hat, 'data': list_etaps}

    def generate_res(tch_mold:OrderMoldTch,code_old_res=None) -> CRES.ResourceSpecification|None:

        err = []

        ПодразделениеДиспетчер = CRES.SubdivisionsData._hnt_сталелитейный_цех_таткуз_таткуз_00_000164
        ОсновноеИзделиеКод = CRES.MainProduct.find_by_code(self._ttkz_tmp_settings.current_order.name_nomen_for_forming)

        РодительКод = CRES.GroupResData._hnt_литье_таткуз_00_058862
        ВариантПодбораВДокументы = CRES.VariationsrespecificationdocumentsData._hnt_автоматически_по_приоритету_0
        СпособРаспределенияЗатратНаВыходныеИзделия = CRES.TheMethodOfAllocatingTheCostOfTheOutputProductsData._hnt_по_долям_стоимости_0

        # Шапка
        hat = CRES.ResourceHeader(
            ОсновноеИзделиеКод=ОсновноеИзделиеКод,
            КоличествоУпаковок= 600,
            Наименование= f'{ОсновноеИзделиеКод.Наименование} (600 {ОсновноеИзделиеКод.ЕдИзм})'  ,
            ТекущийПользователь=CRES.CurrentUser(F.user_full_namre()),
            ДатаНачала=F.now("%Y-%m-%d"),
            ДатаОкончания=F.date_add_days(F.now(""),7,format_out="%Y-%m-%d"),
            ПодразделениеДиспетчер=ПодразделениеДиспетчер,
            РодительКод=РодительКод,
            ВариантПодбораВДокументы=ВариантПодбораВДокументы,
            Описание='Создан из MES(Мкарты)',
            СпособРаспределенияЗатратНаВыходныеИзделия=СпособРаспределенияЗатратНаВыходныеИзделия,
            Код=code_old_res
        )


        # Этап
        Подразделение = CRES.SubdivisionsData._hnt_сталелитейный_цех_таткуз_таткуз_00_000164
        stage_data = CRES.StageData(
            Подразделение=Подразделение,
            ДлительностьМинут= 1440
        )
        # Материалы
        for mat in tch_mold.data:
            if mat.val:
                dict_nomen = get_mat_data(self.DICT_NOMEN_BY_SNUM, mat.mat_kod,True)
                if not dict_nomen or not dict_nomen['is_found']:
                    CQT.msgbox(
                        f'пропущен материал \n`{mat.mat_kod}`\nт.к. не найден в ЕРП')
                    continue

                СпособПолучения = CRES.MethodOfObtainingMaterialspecificationsData.find_by_name(dict_nomen['Способы_получения_материала'])
                СтатьяКалькуляции = CRES.ArticulationArticlesData.find_by_name(dict_nomen['Материалы_Статья_калькуляции'])

                mat = CRES.Material(dict_nomen['code'], mat.val, СтатьяКалькуляции, СпособПолучения)
                stage_data.add_material(mat)
            else:
                CQT.msgbox(
                    f'пропущен материал \n`{mat.mat_kod}`\nт.к. кол-во = 0')

        # Трудозатраты
        ВидРабот = CRES.TypeOfWorkData.find_by_name('литье')
        labor = CRES.LaborCost(ВидРабот, 1440)

        stage_data.add_labor(labor)

        stage = CRES.Stage('литье', stage_data)

        # Итог
        spec = CRES.ResourceSpecification(hat)
        spec.add_stage(stage)


        if err:
            err.insert(0, ['Ошибки'])
            if not CQT.msgboxg_get_table(self, 'Ошибки компоновки', err,
                                         'Продолжить выгрузку', 'Прервать',
                                         show_filtr=False, use_first_row_as_header=True, print_hat=True,
                                         yesNoMode=True):
                return

        return spec

    @CQT.onerror
    def send(data) -> dict|bool:
        code, answ = APIERP.post_res_json(data, self.USER_CONFIG.ERP_base_name['Значение'])
        if code == 200:
            return answ
        else:
            CQT.msgbox(f'Ошибка создания ресурсной. Код {code}\n{answ["Ошибки"]}')
        return False

    if not check():
        return

    tbl = self.ui.tbl_data_mold_tch
    code_old_res = None
    fl_refilled = False
    tch_mold = self._ttkz_tmp_settings.current_order.load_tch()


    if self._ttkz_tmp_settings.current_order.materials_for_forming:#'Перезаполнить'
        code_old_res = self._ttkz_tmp_settings.current_order.materials_for_forming
        if not clear_res(code_old_res):
            return
        fl_refilled = True

    spec_to_ERP = generate_res(tch_mold,code_old_res)
    if not spec_to_ERP:
        return

    data_answ = spec_to_ERP.send()
    spec_to_ERP.to_dict()
    #data_to_ERP = generate(tch_mold,code_old_res)
    #if not data_to_ERP:
    #    return
    #data_answ = send(data_to_ERP)

    if not data_answ:
        return
    code = data_answ['Код'].strip()
    if code:
        link = data_answ['Ссылка']
        CQT.msgbox(f'Успешно создана Код "{code}"',time_life=3)
        pref = 'Создана'
        if fl_refilled:
            pref = 'Очищена и перезаполнена'
        if not CFG.Config.user_config.is_developer: # 25.07.25
            CMS.send_info_mk_b24_by_action(
            f'''[B]{pref} РС на формовку[/B]:
            >> ФИО: {CMS.b24_notation_user_fio()}
            >> НАИМЕНОВАНИЕ: {spec_to_ERP.hat.Наименование}
            >> КОД: [URL={link}]{code}[/URL]
            ''',
            'ТКП ТатКуз')

        self._ttkz_tmp_settings.current_order.materials_for_forming = str(code).strip()
        self._ttkz_tmp_settings.current_order.save()
        mat_mold_calc(self)
