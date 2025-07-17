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
if TYPE_CHECKING:
    from MKart import mywindow

PARAMS_FIELDS_MOLDING_DB = CMS.DocumentedVariables('tatkuz_molding')
TYPES_MOLDING_ORDERS_TCH:dict = CSQ.dict_types_tbl(CFG.Config.project.db_dse,"molding_orders_tch")
class Ttkz_tmp_settings:
    def __init__(self):
        self.current_snum:int|None=None
        self.current_order:OrderMold|None=None
        self.current_stage:int|None=None
        self.list_res:list[dict]|None=None

    def clear(self):
        self.current_stage=0
        self.current_order=None
        self.current_snum=None




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
            key, data = CDCS.get_orders_tatkuz()
            CMS.save_tmp_stukt({"data": data, "date": F.now()}, "orders_tatkuz_for_molding")
        else:
            key = 200
            data = data_cach['data']
        self.list_orders_docs = []
        if not key == 200:
            CQT.msgbox(f'Ошибка получения данных из DOCs код {key}')
            return

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

    def load_order_by_num(self,num:int):
        orders = self.load_orders(where=f"""s_num == {num}""")
        return self.resp_objs[0]

    def get_list_dict(self):
        return [_.get_dict() for _ in self.resp_objs]

    def get_headers_orders(self):
        headers = CSQ.list_of_columns_c(self._db,'molding_orders',False)
        return headers


class OrderMold:
    def __init__(self,data:dict|None=None):
        if data == None:
            data = dict()
            data['date'] = F.now()
            data['user'] = F.user_name()
        self._db = CFG.Config.project.db_dse
        self.s_num = None
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
        self.materials_for_alloy = None
        self.materials_for_lining = None

        self._tch: OrderMoldTch|None = None
        if data:
            self._row = data
            for key in self._row.keys():
                exec(f'self.{str(key).replace(".", "_")} = self._row[key]')
        print()

    def save(self):
        data = self.get_dict(wo_docs=True)
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

    def load_tch(self):
        tchs_data = CSQ.custom_request_c(self._db,f"""SELECT * FROM molding_orders_tch WHERE order_mold == {self.s_num}""",rez_dict=True)
        self._tch = OrderMoldTch(self.s_num,tchs_data)
        return self._tch
    def get_tch_tbl(self):
        return self._tch.get_list()
class OrderMoldTch:
    DICT_ALIASES = {"val":"Значение",
                    "mat_kod": "Материал",
                    }
    def __init__(self,order_num:int,data:list|None=None):
        self.order_num = order_num
        self._db = CFG.Config.project.db_dse
        if data == None:
            data = CSQ.custom_request_c(self._db,f"""SELECT * FROM molding_orders_tch WHERE order_mold == {self.order_num}""",rez_dict=True)
        self._list:list|None = None
        self.data = []
        self._list = data
        for row in self._list:
            self.data.append(OrderMoldTchRow(row))

    def add_new_row(self):
        result = CSQ.custom_request_c(self._db,f"""INSERT INTO molding_orders_tch (order_mold) VALUES (?) RETURNING *""",
                                      list_of_lists_c=[self.order_num], rez_dict=True)
        return OrderMoldTchRow(result[0])
    def get_list(self):
        return [_.get_dict() for _ in self.data]
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


@CQT.onerror
def add_base_complex_mold_tch(self:mywindow):
    #TODO
    order = OrdersMolding().load_order_by_num(self._ttkz_tmp_settings.current_snum)
    tch = order.load_tch()
    tch.add_new_row()
    pass

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
def calc_stage(self:mywindow):
    tbl = self.ui.tbl_list_orders_mold
    row = CQT.get_dict_line_form_tbl(tbl)
    s_num = int(row['Пномер'])
    order_obj: OrderMold = OrdersMolding().load_order_by_num(s_num)
    row = order_obj.get_dict()
    stage = 3
    for k,v in row.items():
        name = k
        if name == None or name not in PARAMS_FIELDS_MOLDING_DB.dict_vars or name.endswith("_docs"):
            continue
        if  PARAMS_FIELDS_MOLDING_DB.dict_vars[name].Этап == 0:
            continue
        stage_field = PARAMS_FIELDS_MOLDING_DB.dict_vars[name].Этап+1
        if PARAMS_FIELDS_MOLDING_DB.dict_vars[name].is_numeric:
            v = F.valm(v)
        if stage_field <= stage and not v:
            stage = stage_field -1

    self._ttkz_tmp_settings.current_order = order_obj
    self._ttkz_tmp_settings.current_snum = int(row['s_num'])
    self._ttkz_tmp_settings.current_stage = stage


def apply_stage(self:mywindow,view_mode=False):
    stage = self._ttkz_tmp_settings.current_stage
    btn_sand_data = self.ui.btn_sand_data
    btn_mat_mold_calc = self.ui.btn_mat_mold_calc

    btn_add_row_mold_tch = self.ui.btn_add_row_mold_tch
    btn_del_row_mold_tch = self.ui.btn_del_row_mold_tch
    btn_apply_data_mold = self.ui.btn_apply_data_mold
    btn_cancel_data_mold = self.ui.btn_cancel_data_mold
    btn_res_product = self.ui.btn_res_product
    gr_mold_tch = self.ui.gr_mold_tch
    btn_sand_data.setEnabled(False)
    btn_mat_mold_calc.setEnabled(False)
    gr_mold_tch.setVisible(False)
    btn_add_row_mold_tch.setEnabled(False)
    btn_del_row_mold_tch.setEnabled(False)
    btn_apply_data_mold.setEnabled(False)
    btn_cancel_data_mold.setEnabled(False)
    btn_res_product.setEnabled(False)

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
        gr_mold_tch.setVisible(True)
        btn_add_row_mold_tch.setEnabled(True)
        btn_del_row_mold_tch.setEnabled(True)
        btn_apply_data_mold.setEnabled(True)
        btn_cancel_data_mold.setEnabled(True)
    if stage == 3:  # ресурсная
        btn_sand_data.setEnabled(False)
        btn_mat_mold_calc.setEnabled(False)
        gr_mold_tch.setVisible(True)
        btn_res_product.setEnabled(True)


    if view_mode:
        btn_apply_data_mold.setEnabled(False)
        btn_cancel_data_mold.setEnabled(False)
        btn_add_row_mold_tch.setEnabled(False)
        btn_del_row_mold_tch.setEnabled(False)
    CQT.clear_tbl(self.ui.tbl_data_mold_tch)

def load_order_tch(self: mywindow, order_obj:OrderMold,view_mode = True):
    tbl_tch = self.ui.tbl_data_mold_tch
    tbl_tchf = self.ui.tbl_data_mold_tch_filtr
    order_obj.load_tch()
    tch_data = order_obj.get_tch_tbl()
    editeble_col_nomera = {}
    if not view_mode:
        editeble_col_nomera = {"Значение","Материал"}
    tch_data_al = CSQ.apply_alias_list(tch_data,OrderMoldTch.DICT_ALIASES)
    CQT.fill_wtabl(tch_data_al, tbl_tch, set_editeble_col_nomera=editeble_col_nomera, )
    CMS.fill_filtr_c(self, tbl_tchf, tbl_tch, hidden_scroll=True)

    for i in range(tbl_tch.rowCount()):
        for j in range(tbl_tch.columnCount()):
            if not view_mode and tbl_tch.horizontalHeaderItem(j).text() in editeble_col_nomera :
                CQT.set_cell_editable(tbl_tch, i, j, True)
            else:
                CQT.set_cell_editable(tbl_tch, i, j, False)
                CQT.set_font_color_wtab_c(tbl_tch, i, j, 100, 100, 100)


@CQT.onerror
def load_order_data(self: mywindow, edit_etap_num=9,view_mode=False):
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


    if edit_etap_num:
        calc_stage(self)
    if edit_etap_num == 2:
        load_lists_res(self)
        add_base_complex_mold_tch(self)

    apply_stage(self,view_mode)
    update_lbl_info(self)
    cancel_new_or_edit_order(self)
    order_obj_dict = dict()
    if self._ttkz_tmp_settings.current_snum:
        order_obj: OrderMold = OrdersMolding().load_order_by_num(self._ttkz_tmp_settings.current_snum)
        order_obj_dict = order_obj.get_dict()
        load_order_tch(self, order_obj,view_mode)
    tbl = self.ui.tbl_data_mold
    data = [{"stage": v.Этап, "Name": _, "Реквизит": v.БуквенноеОбозначение, "Значение": v.Default_val, "Ед.Изм.":v.ЕдиницаИзмерения, "Описание":v.Описание}
            for _, v in PARAMS_FIELDS_MOLDING_DB.dict_vars.items() if v.Видимый and v.Этап <= edit_etap_num]
    for item in data:
        if item['Name'] in order_obj_dict:
            item['Значение'] = order_obj_dict[item['Name']]
    data = F.sort_by_column_c(data,"stage",)
    CQT.fill_wtabl(data, tbl, set_editeble_col_nomera={"Значение"}, )
    CMS.fill_filtr_c(self, self.ui.tbl_data_mold_filtr, tbl, hidden_scroll=True)
    nf_val = CQT.num_col_by_name_c(tbl,"Значение")
    for i in range(tbl.rowCount()):
        row = CQT.get_dict_line_form_tbl(tbl,i)
        if int(row['stage']) != edit_etap_num or not PARAMS_FIELDS_MOLDING_DB.dict_vars[row['Name']].editable:
            for j in range(tbl.columnCount()):
                CQT.set_cell_editable(tbl,i,j,False)
                CQT.set_font_color_wtab_c(tbl,i,j,100,100,100)
        else:
            CQT.set_cell_editable(tbl,i,nf_val,True)
            if row['Name'] in ('materials_for_alloy','materials_for_lining'):
                link_name = row['Значение'].strip()
                if not link_name:
                    link_name = 'Выбор...'
                CQT.add_label_link(tbl,i,nf_val,link_name,link_name,fcn_select_res,self)
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

@CQT.onerror
def mold_tch_cellchanged(self: mywindow,row:int,col:int):
    tbl = self.ui.tbl_data_mold_tch
    row_data = CQT.get_dict_line_form_tbl(tbl,row)
    s_num = row_data['s_num']
    key_name = tbl.horizontalHeaderItem(col).text()
    new_val = row_data["Значение"]
    row_obj = OrderMoldTchRow()
    row_obj.load_row_tch_by_snum(int(s_num))
    name_attr = row_obj.name_from_aliases(key_name)
    old_val = row_obj.__dict__[name_attr]
    err = False
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
        tbl.blockSignals(True)
        tbl.item(row,col).setText(old_val)

@CQT.onerror
def select_order(self: mywindow):
    load_order_data(self,view_mode=True)


@CQT.onerror
def new_order(self: mywindow):
    self._ttkz_tmp_settings.clear()
    load_order_data(self, 0)

@CQT.onerror
def add_sand_data(self: mywindow):
    load_order_data(self, 1)

@CQT.onerror
def mat_mold_calc(self: mywindow):
    load_order_data(self, 2)
def update_lbl_info(self:mywindow):
    info_str = ''
    if self._ttkz_tmp_settings.current_order:
        info_str = f"({self._ttkz_tmp_settings.current_stage})№ {self._ttkz_tmp_settings.current_snum} - {self._ttkz_tmp_settings.current_order.tkp_name_proc_docs}"
    self.ui.lbl_data_mold.setText(info_str)
@CQT.onerror
def load_form_rs_for_molding(self:mywindow, *args):
    orders = OrdersMolding()
    orders.load_orders()
    data = orders.get_list_dict()
    if not data:
        data = [orders.get_headers_orders()]
    data = PARAMS_FIELDS_MOLDING_DB.apply_alias_list(data)
    CQT.fill_wtabl(data, self.ui.tbl_list_orders_mold,load_links=True,selectionBehavior='SelectRows',selectionMode='SingleSelection',
                   sortingEnabled=True,list_column_widths=CMS.load_column_widths(self,self.ui.tbl_list_orders_mold))

    CMS.fill_filtr_c(self,self.ui.tbl_list_orders_mold_filtr,self.ui.tbl_list_orders_mold,hidden_scroll=True)
    self._ttkz_tmp_settings.clear()
    update_lbl_info(self)
    oform_tbl(self)
    load_lists_res(self)
    pass
@CQT.onerror
def oform_tbl(self:mywindow):
    dict_states = {
    'Отменён':0,
    'Завершён':100,
    'В очереди':30,
    'В работе':55
    }
    tbl = self.ui.tbl_list_orders_mold
    nf_state = CQT.num_col_by_name_c(tbl,'Cтатус')
    for i in range(tbl.rowCount()):
        state = tbl.item(i,nf_state).text()
        clr = CMS.Color_tbl(dict_states[state])
        CQT.set_color_wtab_c(tbl,i,nf_state,clr.r,clr.g,clr.b)

@CQT.onerror
def apply_new_or_edit_order(self:mywindow):

    def check_new_order_data(data:list):
        return True

    tbl = self.ui.tbl_data_mold
    data = CQT.list_from_wtabl_c(tbl,rez_dict=True)
    if not check_new_order_data(data):
        return
    if self._ttkz_tmp_settings.current_stage > 0:
        order: OrderMold = OrdersMolding().load_order_by_num(self._ttkz_tmp_settings.current_snum)
    else:
        order = OrderMold()
    for item in data:
        if PARAMS_FIELDS_MOLDING_DB.dict_vars[item["Name"]].is_numeric:
            exec(f'order.{item["Name"]} = {F.valm(item["Значение"])}')
        else:
            exec(f'order.{item["Name"]} = "{item["Значение"]}"')
    if order.save():
        load_form_rs_for_molding(self)
        cancel_new_or_edit_order(self)


@CQT.onerror
def cancel_new_or_edit_order(self:mywindow):
    CQT.clear_tbl(self.ui.tbl_data_mold)
    CQT.clear_tbl(self.ui.tbl_data_mold_filtr)
    CQT.clear_tbl(self.ui.tbl_data_mold_tch)
    CQT.clear_tbl(self.ui.tbl_data_mold_tch_filtr)

    


@CQT.onerror
def add_row_mold_tch(self:mywindow):
    if not self._ttkz_tmp_settings.current_stage == 2:
        return
    order = OrdersMolding().load_order_by_num(self._ttkz_tmp_settings.current_snum)
    tch = order.load_tch()
    tch.add_new_row()
    load_order_tch(self, order, view_mode= False)

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

