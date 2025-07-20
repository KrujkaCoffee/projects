from PyQt5 import QtWidgets, QtGui, QtCore  # , QtWebEngineWidgets
from PyQt5.QtWinExtras import QtWin
import os
import project_cust_38.Cust_Qt as CQT

CQT.convert_UI_into_PY_c()
from mydesign import Ui_MainWindow  # импорт нашего сгенерированного файла
import config
import sys
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Excel as CEX
import project_cust_38.report_ci as OTCH
from datetime import datetime as DT, timedelta
from dataclasses import dataclass
import project_cust_38.Zamechaniya as ZMCH
import project_cust_38.Cust_config as USRCNF
import project_cust_38.Cust_odata_erp as ODAT
import arm_pr_oper as ARMOPER
cfg = config.Config(r'Config\CFG.cfg')  # файл конфига, находится в папке конфиг
import json as JS
F.test_path()


@dataclass()
class Data:
    bd_naryad = F.bdcfg('Naryad')
    bd_act = F.bdcfg('BDact')
    bd_users = F.bdcfg('BD_users')
    bd_mat = F.bdcfg('nomenklatura_erp')
    bd_selector = F.bdcfg('BD_selector')
    db_dse = F.bdcfg('BD_dse')
    db_resxml = F.bdcfg('db_resxml')
    db_kplan = F.bdcfg('DB_kplan')
    files_tmp = F.scfg('files_tmp')
    data_f = F.scfg('data_f')

    DICT_ETAPI = dict()
    custom_request_c = f'''SELECT * FROM operacii'''
    SPIS_OP = CSQ.custom_request_c(bd_naryad, custom_request_c, hat_c=False, rez_dict=True)
    if SPIS_OP != False:
        for i in range(len(SPIS_OP)):
            DICT_ETAPI[SPIS_OP[i]['name']] = SPIS_OP[i]['etap']
    DICT_ETAPI_FULL = F.deploy_dict_c(CSQ.custom_request_c(bd_naryad, f'''SELECT * FROM etaps''', rez_dict=True),'name')
    VID_RABOT_PO_EMPL = CMS.VID_RABOT_PO_EMPL(bd_users)
    VID_RABOT_PO_DOLGN = CMS.VID_RABOT_PO_DOLGN(bd_users)
    ETAP_BY_FIO = CMS.ETAP_BY_FIO(bd_users,bd_naryad)
    NAPRAVL_D= CSQ.custom_request_c(db_kplan, f"""SELECT * FROM napravl_deyat WHERE poki = {USRCNF.Config.place.poki};""", hat_c=False, rez_dict=True)
    NAPRAVL_DEYAT = F.deploy_dict_c(NAPRAVL_D, 'Имя')
    NAPRAVL_DEYAT_KOD = F.deploy_dict_c(NAPRAVL_D, 'Пномер')
    NAPR = CSQ.custom_request_c(db_kplan, f'''SELECT * FROM napravlenie''', hat_c=False,
                                                        rez_dict=True)
    #DICT_NAPR_DEYAT_NAME = F.deploy_dict_c(NAPR_DEYAT, 'name')
    DICT_NAPRAVL = F.deploy_dict_c(NAPR, 'name')

    KAT_VNEPL = CSQ.custom_request_c(bd_naryad, f'''SELECT * FROM kategor_vnepl''', hat_c=False,
                                                        rez_dict=True)

    DICT_TYPE_MK_NAMES = F.deploy_dict_c(
        CSQ.custom_request_c(bd_naryad, f"""SELECT * FROM Тип_мк""", rez_dict=True),
        'Имя')
    DICT_TYPE_DOREZ = CSQ.custom_request_c(bd_naryad, f"""SELECT * FROM тип_дорезок""", rez_dict=True)
    DICT_TYPE_DORAB = CSQ.custom_request_c(bd_naryad, f"""SELECT * FROM тип_доработок""", rez_dict=True)

    DICT_KAT_VNEPL = F.deploy_dict_c(KAT_VNEPL, 'kod')
    DICT_KAT_VNEPL_NAME = F.deploy_dict_c(KAT_VNEPL, 'value')
    # VID_PO_NAPR = CSQ.custom_request_c(db_kplan, f"""SELECT * FROM виды_по_напр""", rez_dict=True)
    VID_PO_NAPR = CMS.TypesWorkingByDirections().get_old_view_response() # виды_по_направлениям 18.07.25
    DICT_VID_PO_NAPR = F.deploy_dict_c(VID_PO_NAPR, 'Пномер')
    DICT_VID_PO_NAPR_NAME = F.deploy_dict_c(VID_PO_NAPR, 'Имя')

    custom_request_c = f'''SELECT * FROM professions INNER JOIN vid_rab_po_dolg 
    ON vid_rab_po_dolg.Вид_работ = professions.вид_работ,
     group_vid_rab_for_plan ON group_vid_rab_for_plan.name=vid_rab_po_dolg.group_for_plan WHERE Вкл = 1 and group_vid_rab_for_plan.composite = 0'''
    SPIS_prof = CSQ.custom_request_c(bd_users, custom_request_c, hat_c=False,rez_dict=True)
    LIST_PROFESSIONS = SPIS_prof
    DICT_PROFESSIONS = F.deploy_dict_c(SPIS_prof,'код')
    DICT_PROFESSIONS_NAME = F.deploy_dict_c(SPIS_prof, 'имя')
    DICT_PROFESSIONS_PSEUDONAME = F.deploy_dict_c(SPIS_prof, 'Псевдоним')
    DICT_VID_RABOT = F.deploy_dict_c(SPIS_prof, 'вид_работ')
    group_vid_rab_for_plan = CSQ.custom_request_c(bd_users, f"""SELECT 
        * FROM group_vid_rab_for_plan WHERE composite = 0;""", rez_dict=True)
    DICT_GROUP_VID_RAB_FOR_PLAN_NICKNAME = DICT_PROFESSIONS_NICKNAME = F.deploy_dict_c(group_vid_rab_for_plan,'nick_name')
    DICT_GROUP_VID_RAB_FOR_PLAN_NAME = F.deploy_dict_c(group_vid_rab_for_plan, 'name')
    DICT_EMPL_FULL = F.deploy_dict_c(CSQ.custom_request_c(bd_users, f"""SELECT * FROM employee WHERE Пномер IN( SELECT Пномер FROM (SELECT
        	MAX(Пномер) as Пномер,
        	ФИО
        FROM
        	employee
        GROUP BY
        	ФИО
        HAVING COUNT(*) >= 1 )) order by ФИО;""", rez_dict=True), 'ФИО')

    DICT_REF_USERS = { v['ID_ФизЛица']:k for k,v in DICT_EMPL_FULL.items()}

    DICT_BASES_ERP = F.deploy_dict_c(CSQ.custom_request_c(bd_users, f"""SELECT * FROM bases_ERP""", rez_dict=True),
                                      'name')

    DICT_DOLGN_ETAP = F.deploy_dict_c(CSQ.custom_request_c(bd_naryad, f"""SELECT * FROM dolgn_etap""", rez_dict=True),
                                      'Должность')
    m = ODAT.OrdersComposit()
    type_workers = m.get_response('Catalog_ВидыРаботСотрудников',
                                               f"""?$filter=DeletionMark eq false &$select=Ref_Key, Description""")
    if type_workers is None:
        CQT.msgbox('Не удалось установить соединение с сервром ERP')
    else:
        DICT_TRDZ = F.deploy_dict_c(type_workers, "Ref_Key")


class mywindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(mywindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.versia = '1.6.8.4'
        self.NAME_MODULE_BASE = f"Просмотр"
        self.name_module = f'{self.NAME_MODULE_BASE}'
        self.USER_CONFIG : USRCNF.User_config = None
        self.place : USRCNF.Place = None

        USRCNF.Config.user_config.load_user_config(self)
        CQT.load_icons(self)
        CQT.connect_to_resize(self, CMS.tmp_dir())
        CMS.add_action_config_save_tbl_filtrs(self, self.ui)
        OTCH.vibor_sort_c_report_c(self)

        # =================add_ui============================
        self.parent_for_grafic = self.ui.verticalLayout_8
        # ===========================================connects
        self.bd_naryad = F.bdcfg('Naryad')
        self.bd_act = F.bdcfg('BDact')
        self.bd_users = F.bdcfg('BD_users')
        self.bd_mat = F.bdcfg('nomenklatura_erp')
        self.bd_selector = F.bdcfg('BD_selector')
        self.db_dse = F.bdcfg('BD_dse')
        self.db_resxml = F.bdcfg('db_resxml')
        self.db_kplan = F.bdcfg('DB_kplan')
        self.files_tmp = F.scfg('files_tmp')
        self.data_f = F.scfg('data_f')
        #===================actions

        self.ui.actionexcel.triggered.connect(self.export_table)
        self.ui.action_txt.triggered.connect(self.export_table_txt)

        self.ui.action_tmp.triggered.connect(self.action_tmp)
        # ==================BTN
        self.ui.btn_report_c.clicked.connect(lambda: OTCH.report_c(self))
        self.ui.btn_grafic_load.clicked.connect(lambda _, x=self: OTCH.create_podreport_c(x))
        self.ui.btn_save_txt.clicked.connect(self.save_txt)
        self.ui.btn_udown.clicked.connect(self.up_down)
        self.ui.btn_get_exel.clicked.connect(self.get_exel_for_compare_tdz)
        self.ui.btn_add_zamech.clicked.connect(lambda _, x=self: ZMCH.add_zamech(x))
        self.ui.btn_set_cld_month.clicked.connect(lambda : OTCH.calendar_select(self,'m'))
        self.ui.btn_set_cld_year.clicked.connect(lambda: OTCH.calendar_select(self,'y'))
        self.ui.btn_post_block_to_erp.clicked.connect(lambda: ARMOPER.post_block_to_erp(self))
        self.ui.btn_del_block_to_erp.clicked.connect(lambda: ARMOPER.del_block_to_erp(self))
        self.ui.btn_post_all_block_to_erp.clicked.connect(lambda: ARMOPER.post_all_block_to_erp(self))
        self.ui.btn_start_etap_erp.clicked.connect(lambda: ARMOPER.btn_start_etap_erp(self))
        self.ui.btn_delete_block_from_etap.clicked.connect(lambda: ARMOPER.btn_delete_block_from_etap(self))
        self.ui.btn_show_history_nar.clicked.connect(lambda: ARMOPER.show_history_nar(self))
        self.ui.btn_show_structure_nar.clicked.connect(lambda: ARMOPER.show_structure_nar(self))
        # ==================lines

        # ==================TABLES
        self.ui.tbl_mk.setSelectionBehavior(1)
        self.ui.tbl_mk.setSelectionMode(1)
        self.ui.tbl_mk.currentItemChanged.connect(self.select_mk)
        self.ui.tbl_jur.setSelectionBehavior(1)
        self.ui.tbl_jur.setSelectionMode(1)
        self.ui.tbl_jur.currentItemChanged.connect(self.select_jur)
        self.ui.tbl_report_c.doubleClicked.connect(lambda _, x=self: OTCH.dbl_clck_otch(x))
        self.ui.tbl_report_c.currentItemChanged.connect(lambda: OTCH.clck_otch(self))
        self.ui.tbl_report_c.horizontalScrollBar().valueChanged.connect(
            self.ui.tbl_report_c_filtr.horizontalScrollBar().setValue)
        self.ui.tbl_report_c.itemSelectionChanged.connect(self.tbl_report_itemSelectionChanged)
        self.ui.tbl_report_add.itemSelectionChanged.connect(self.tbl_report_add_itemSelectionChanged)
        self.ui.tbl_viev_etaps_name.currentItemChanged.connect(self.tbl_viev_etaps_name_itemSelectionChanged)
        # ==================TABS
        self.ui.tabWidget.currentChanged[int].connect(self.tab_click)
        # ===================CHECKBOX
        self.ui.chk_autohide.clicked.connect(self.clck_chk_autohide)
        # ===================COMBOBOX
        self.ui.cmb_sort_c_report.activated.connect(lambda _, x=self: OTCH.vibor_sort_c_report_c(x))
        self.ui.cmb_podrazdelenie.activated.connect(lambda _, x=self: OTCH.vibor_additional_sort_report(x))
        # self.ui.cmb_sort_c_report.highlighted.connect(self.cmb_sort_c_report_primech)
        self.ui.cmb_napr.activated.connect(self.choose_direction)
        self.ui.cmb_gant_vert.activated.connect(lambda _, x=self: OTCH.vibor_pole_gant(x))
        # ===================RADIOBOX

        # ================CALENDAR===================================
        self.ui.calendarWidget.clicked.connect(lambda : OTCH.calendar_click(self))

        # ++++++++++++++++++++++++++++++++++++++++++++

        CMS.dict_emploee_rc(self)
        CMS.dict_rc_po_oper(self, self.bd_naryad)
        CMS.dict_rc(self, self.bd_users)
        CMS.dict_professions(self, self.bd_users)
        CMS.dict_napravl(self, self.db_kplan)
        CMS.dict_opers(self, self.bd_naryad)
        CMS.dict_etapi(self, self.bd_naryad)
        self.DICT_EMPLOEE = CMS.dict_emploee(self.bd_users)
        self.DICT_PRICE_BRAK = CMS.DICT_PRICE_BRAK(self.bd_naryad)
        self.DICT_EMPLOEE_FULL = CMS.dict_emploee_full(self.bd_users)
        self.DICT_EMPLOEE_FULL_WITH_DEL = CMS.dict_emploee_full_with_del(self.bd_users)
        self.DICT_MK = CSQ.custom_request_c(self.bd_naryad,
                                            f"""SELECT Пномер, Номер_заказа || "$" || Номер_проекта as NPPY FROM mk""",
                                            rez_dict=True)
        self.DICT_MK = F.deploy_dict_c(self.DICT_MK, 'NPPY')
        self.LIST_ZAMECH = self.load_remarks()
        self.DICT_KOD_VP = F.deploy_dict_c(
            CSQ.custom_request_c(self.bd_naryad, f"""SELECT * FROM kod_zamech_vp""", rez_dict=True),
            'Имя')
        self.DICT_KOD_ZAM = F.deploy_dict_c(
            CSQ.custom_request_c(self.bd_naryad, f"""SELECT * FROM kod_zamech""", rez_dict=True),
            'Имя')
        # ==== GLOBALS
        self.plan_for_gant = ''
        self.global_arm_oper_user_fio = None

        # =======loads
        self.Data = Data
        self.ui.rbut_start_of_per.setChecked(True)
        self.LIST_VID_MAT = ['Отводы',
                             'Переходы',
                             'Тройники',
                             'Трубопроводная арматура',
                             'Фланцы',
                             'Штуцера',
                             'Паронит ГОСТ 481-80',
                             'Фторопласт',
                             'Шнуры',
                             'Труба ГОСТ 9941-81 (нерж)',
                             'Труба квадратная (10,01)',
                             'Трубы по ГОСТ (10,01)',
                             'Трубы по ТУ (10,01)',
                             'Шпилька  ГОСТ 22042',
                             'Шпилька ГОСТ 9066 (без шаблона)',
                             'Шпилька для фланцевых соединений ГОСТ 9066',
                             'Шпильки DIN 975',
                             'Двутавр (10,01)',
                             'Зубчатые рейки (10.01)',
                             'Квадрат (10,01)',
                             'Круги (10,01)',
                             'Листовой металл (10,01)',
                             'Прутки (10,01)',
                             'Уголок (10,01)',
                             'Швеллер (10,01)',
                             'Шестигранник (10,01)',
                             ]
        # self.app_icons()

        self.chk_autohide = CMS.load_tmp_val('chk_autohide',False,True)
        self.ui.chk_autohide.blockSignals(True)
        self.ui.chk_autohide.setChecked(self.chk_autohide)
        self.ui.chk_autohide.blockSignals(False)

        self.dict_sort_c_report_c = OTCH.DICT_VID_OTCH

        #for i, report_c in enumerate(self.dict_sort_c_report_c.keys()):
        #    self.ui.cmb_sort_c_report.addItem(report_c)
        #    self.ui.cmb_sort_c_report.setItemData(i, self.dict_sort_c_report_c[report_c], QtCore.Qt.ToolTipRole)
        self.vid_report_c = ''
        self.fill_cmb_sorts_repot()

        spis_napravl = list(self.DICT_NAPRAVL.keys())
        for napravl in spis_napravl:
            self.ui.cmb_napr.addItem(napravl)
        self.ui.btn_save_txt.setDisabled(True)


        self.ui.fr_save_txt.setHidden(True)
        self.ui.fr_addition_tbl.setHidden(True)
        self.ui.fr_mk_zamech.setHidden(True)
        ZMCH.init_zamech_const(self)
        self.DICT_MAT = F.deploy_dict_c(CSQ.custom_request_c(self.bd_mat, f"""SELECT * FROM nomen""", rez_dict=True),
                                        'Код')
        self.DICT_NOMEN = self.DICT_MAT

        if self.DICT_NOMEN == False:
            CQT.msgbox(f'база номенклатуры занята')
            quit()

        self.ARM_oper_using = True


        # ============DB
        # ====ВРЕМЕННО
        #self.tmp_func()



    @CQT.onerror
    def action_tmp(self,*args):
        CQT.load_css(self)
        return


    @CQT.onerror
    def tmp_func(self,*args):

        def get_id(item_row,dict_id):
            for item in item_row:
                dict_id[item['name']] = item['id']
                if  'children' in item:
                    dict_id = get_id(item['children'], dict_id)
            return dict_id

        path = fr'C:\Users\a.belyakov\Downloads\division.json'
        data = '\n'.join(F.load_file(path,'||'))
        json_file  = JS.loads(data)
        dict_id = dict()
        dict_id = get_id(json_file,dict_id)
        print()



    @CQT.onerror
    def select_base_erp(self, base:str, *args):
        self.ERP_base_name = base
        CMS.save_tmp_val('ERP_base_name',base)
        print(self.ERP_base_name)
        self.name_module = f'{self.ERP_base_name}-{self.NAME_MODULE_BASE}'
        CMS.Organization(self.bd_naryad,self).set_tooltip()
        self.clear_tabels()

    @CQT.onerror
    def clear_tabels(self):
        CQT.clear_tbl(self.ui.tbl_report_c)
        CQT.clear_tbl(self.ui.tbl_report_add)
        CQT.clear_tbl(self.ui.tbl_report_add_summ)
        CQT.clear_tbl(self.ui.tbl_viev_etaps_name)
        CQT.clear_tbl(self.ui.tbl_viev_etaps_erp)
        CQT.clear_tbl(self.ui.tbl_zamech_add_field)

    @CQT.onerror
    def clck_chk_autohide(self,*args):
        CMS.save_tmp_val('chk_autohide', self.ui.chk_autohide.isChecked())
        self.chk_autohide = self.ui.chk_autohide.isChecked()
    @CQT.onerror
    def fill_cmb_sorts_repot(self, *args):
        name_last = CMS.load_tmp_path('last_used_report')
        list_bold = [True if _ == name_last else False for _ in list(self.dict_sort_c_report_c.keys())]
        CQT.fill_list_combobx(self,self.ui.cmb_sort_c_report,list(self.dict_sort_c_report_c.keys()),[],list(self.dict_sort_c_report_c.values()),list_bold=list_bold)
        self.ui.cmb_sort_c_report.setCurrentText(name_last)
        self.vid_report_c = name_last
        OTCH.vibor_sort_c_report_c(self)

    @CQT.onerror
    def get_exel_for_compare_tdz(self, *args):
        LIST_EXCLUDE_PODR  = [ 'Конструкторский отдел (Пауэрз)', 'Отдел комплектации (Пауэрз)', 'Отдел логистики (Пауэрз)']
        CQT.clear_tbl(self.ui.tbl_compare_exel)
        name_type_path = 'viewer_exel_compare_tdz'
        cust_path = CMS.load_tmp_path(name_type_path)
        path = CQT.f_dialog_name(self,'Выбрать эксель с отчетом',cust_path,'*.txt')
        if path == '.':
            return
        CMS.save_tmp_path(name_type_path,path,True)
        self.ui.lbl_path_exel.setText(path)
        sheet = F.load_file(path,'\t')
        res_dict = dict()
        rc = ''
        fio = ''
        pu = ''
        date = ''
        min_date = '2042-09-01 00:00:00'
        max_date = '2003-09-01 00:00:00'
        for item in sheet:
            if len(item)<6:
                continue
            if '(Пауэрз)' in item[0]  and 'ПУ' not in item[3]:
                rc = item[0]

            else:
                if F.is_date(item[0],'%d.%m.%Y %H:%M:%S'):
                    date = F.strtodate(item[0],'%d.%m.%Y %H:%M:%S')
                    if date > F.strtodate(max_date):
                        max_date = F.datetostr(date)
                    if date < F.strtodate(min_date):
                        min_date = F.datetostr(date)
                else:
                    if item[1] != '' and 'ПУ' in item[3]:
                        pu = item[3].split()[3]
                        time_min = F.valm(item[4])

                        if rc in LIST_EXCLUDE_PODR:
                            continue

                        mes_time = 0
                        delta = 100
                        key = '|'.join([F.datetostr(date, "%Y-%m-%d"),fio,pu])
                        res_dict[key] = {'РЦ':rc,
                        'Дата':F.datetostr(date, "%Y-%m-%d"),
                        "ПУ":pu,
                        "ФИО":fio,
                        "Время ЕРП":time_min,
                        "Время МЕС":mes_time,
                        'Отколнение %':delta}
                    else:
                        fio = item[0]

        custom_request_c = f"""SELECT jurnal.ФИО, jurnal.Подытог,mk.Номер_заказа, jurnal.Дата  FROM jurnal INNER JOIN 
        naryad ON naryad.Пномер = jurnal.Номер_наряда,
        mk ON mk.Пномер = naryad.Номер_мк
        WHERE jurnal.Подытог <> 0 AND jurnal.Статус = 'Начат'
            and datetime(jurnal.Дата) > datetime("{min_date}") 
            and datetime(jurnal.Дата) <= datetime("{max_date}");"""
        rez_jur_pre = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True, rez_dict=True)
        rez_jur = []
        for item in rez_jur_pre:
            if item['ФИО'] in self.DICT_EMPLOEE:
                if item['ФИО'] + " " +self.DICT_EMPLOEE[item['ФИО']] in self.DICT_EMPLOEE_RC:
                    if  self.DICT_EMPLOEE_RC[item['ФИО'] + " " +self.DICT_EMPLOEE[item['ФИО']] ][:2] == '01' :
                        rez_jur.append(item)
                else:
                    rez_jur.append(item)
            else:
                rez_jur.append(item)

        for i in range(len(rez_jur)):
            fio = rez_jur[i]['ФИО']
            time = rez_jur[i]['Подытог']
            if '\\' in rez_jur[i]['Номер_заказа']:
                pu = rez_jur[i]['Номер_заказа'].split('\\')[-1]
            else:
                pu = rez_jur[i]['Номер_заказа']

            date_jur = rez_jur[i]['Дата']

            key = '|'.join([F.datetostr(F.strtodate(date_jur), "%Y-%m-%d"),fio,pu])
            if key in res_dict:
                res_dict[key]["Время МЕС"] += time
                rez_jur[i]['del'] = 1
        for i in range(len(rez_jur)):
            if 'del' not in rez_jur[i]:
                fio = rez_jur[i]['ФИО']
                time = rez_jur[i]['Подытог']
                if '\\' in rez_jur[i]['Номер_заказа']:
                    pu = rez_jur[i]['Номер_заказа'].split('\\')[-1]
                else:
                    pu = rez_jur[i]['Номер_заказа']

                date_jur = rez_jur[i]['Дата']
                key = '|'.join([F.datetostr(F.strtodate(date_jur), "%Y-%m-%d"), fio, pu])
                if key in res_dict:
                    res_dict[key]["Время МЕС"] += time
                else:
                    pdr = 'MES'
                    if fio in self.DICT_EMPLOEE_FULL:
                        pdr = self.DICT_EMPLOEE_FULL[fio]['Подразделение']
                    res_dict[key] = {'РЦ':pdr,
                            'Дата':F.datetostr(F.strtodate(date_jur), "%Y-%m-%d"),
                            "ПУ":pu,
                            "ФИО":fio,
                            "Время ЕРП":0,
                            "Время МЕС":time,
                            'Отколнение %':-100}
        for key in res_dict.keys():
            delta = 100
            if res_dict[key]["Время МЕС"] != 0:
                delta = round ((1 - res_dict[key]["Время ЕРП"] / res_dict[key]["Время МЕС"])*100)
            res_dict[key]['Отколнение %'] = delta

        CQT.fill_wtabl( [res_dict[k] for k in res_dict.keys()],self.ui.tbl_compare_exel)
        CMS.fill_filtr_c(self,self.ui.tbl_compare_exel_filtr,self.ui.tbl_compare_exel)
        CMS.update_width_filtr(self.ui.tbl_compare_exel,self.ui.tbl_compare_exel_filtr)

    def up_down(self):
        fr = self.ui.fr_cal
        btn = self.ui.btn_udown
        if fr.isHidden():
            btn.setText('/\\')
            fr.setHidden(False)
            CQT.show_fullscreen(app,self,False)

        else:
            btn.setText(r'\/')
            fr.setHidden(True)
            CQT.show_fullscreen(app,self,True)
    @CQT.onerror
    def save_txt(self,*args):
        def check_save_txt_trdzt(self):
            count_err = 0
            list = CQT.list_from_wtabl_c(self.ui.tbl_report_c, sep='', hat_c=True, rez_dict=True)
            for item in list:
                val_of_proc = F.valm(item['Соответствие_%'])
                if val_of_proc < self.PROC_OTKL_TRUDOZATRAT[0] or val_of_proc > self.PROC_OTKL_TRUDOZATRAT[1]:
                    count_err += 1
            if count_err:
                if CQT.msgboxgYN(
                    f'{count_err} значений выходят за диапазон от {self.PROC_OTKL_TRUDOZATRAT[0]} до'
                    f' {self.PROC_OTKL_TRUDOZATRAT[1]}, необходимо править наряды/табель',
                        "Все равно выгрузить","Возврат"):
                    return True
                else:
                    return False
            return True

        def check_path_save(self):
            path = self.ui.le_path_save.text()
            if F.existence_file_c(path) and path.strip() != '':
                CMS.save_tmp_path('tdz_dir', path, False)
                return True
            CQT.msgbox('Выбранный путь недоступен')
            self.ui.le_path_save.setText(CMS.tmp_dir())
            return False

        if self.vid_report_c == 'Трудозатраты':
            if not check_path_save(self):
                return
            if not check_save_txt_trdzt(self):
                return


            if self.ui.cmb_podrazdelenie.currentText() not in self.DICT_PODR_RC:
                CQT.msgbox(f'{self.ui.cmb_podrazdelenie.currentText()} не найдено в rab_c empl_Подразделение')
                return

            mk = None
            if self.ui.cmb_gant_tochnost_dat.currentText() != '':
                mk = int(self.ui.cmb_gant_tochnost_dat.currentText().split('|')[0])

            rab_centr = self.DICT_PODR_RC[self.ui.cmb_podrazdelenie.currentText()]['Код']
            list = CQT.list_from_wtabl_c(self.ui.tbl_report_c, sep='', hat_c=True, rez_dict=True)
            list_users = [_['ФИО'] for _ in list]

            by_norm = False
            if F.strtodate(self.ui.le_start_of_period.text()) >= F.strtodate('2024-07-01 00:00:00'):
                by_norm = True
                CQT.msgbox('Выгрузка по режиму "учет трудов по нормам"')
            dir_tdz_user_rc_3 = CMS.upload_work_productivity_3(self, self.ui.le_start_of_period.text(),
                                                               self.ui.le_end_of_period.text(),
                                                               list_users,
                                                               self.ui.cmb_podrazdelenie.currentText(), mk,by_norm)
            if dir_tdz_user_rc_3 == None:
                return
            if CQT.msgboxgYN('Успешно выгружено!\nОткрыть папку?'):
                if dir_tdz_user_rc_3 != None:
                    F.open_dir_c(dir_tdz_user_rc_3)
            date_name_per = F.datetostr(F.strtodate(self.ui.le_start_of_period.text()), "d_%Y_%m_%d")
            name_book = F.datetostr(F.strtodate(self.ui.le_start_of_period.text()), 'jurnaltdz_%Y_%m_01')
            CSQ.custom_request_c(self.bd_users,
                                 f"""UPDATE {name_book} SET {date_name_per} = 1 WHERE РЦ == "{rab_centr}" """)

        if self.vid_report_c == 'Усредненная удельная трудоемкость сборки по видам':
            tbl = self.ui.tbl_report_c
            list = CQT.list_from_wtabl_c(tbl, hat_c=True, only_visible=True, rez_dict=True)
            for item in list:
                list_of_lists = [[int(item['Выборка,шт.']),
                                  F.valm(item['кг_на_пост_см_средн']),
                                  F.valm(item['Лазерная резка']),
                                  F.valm(item['Сборка+сварка']),
                                  F.valm(item['Покраска']),
                                  F.valm(item['Токарка+фрезеровка']),
                                  F.valm(item['Зачистка']),
                                  F.valm(item['Вспомогательная']),
                                  F.valm(item['Термическая']),
                                  F.valm(item['Подготовка монтажного комплекта']),
                                  F.valm(item['Упаковка и комплектование ЗИП']),
                                  ]]
                kod = int(item['Код из бд'])
                rez = CSQ.custom_request_c(self.db_kplan, f'''UPDATE виды_по_напр SET (Выборка, 
                кг_на_пост_см, 
                Лазерная_резка, 
                Сборка_сварка, 
                Покраска, 
                Токарка_фрезеровка, 
                Зачистка, 
                Вспомогательная, 
                Термическая, 
                Подготовка_монтажного_комплекта, 
                Упаковка_и_комплектование_ЗИП) = ({'?,'.join(['' for _ in list_of_lists[0]]) + '?'}) 
                WHERE  Пномер = {kod}''', list_of_lists_c=list_of_lists)
                if rez == False:
                    CQT.msgbox(f'Ошибка')
                    return
            CQT.msgbox(f'Успешно обновлено')

        if self.vid_report_c == 'Выработка сотрудников':
            CQT.msgbox(f'В разарботке')
            return
            tbl = self.ui.tbl_report_c
            start = self.ui.le_start_of_period.text()
            end = self.ui.le_end_of_period.text()
            dir = self.ui.le_path_save.text()
            if dir == '':
                dir = CQT.getDirectory(self,F.dir_workdesc_c())
                if dir == None or dir == [''] or dir == '.':
                    return
            for i in range(tbl.rowCount()):
                row = CQT.get_dict_line_form_tbl(tbl,i)
                if row['Профес.'] in ('Мастер',"=SUMM="):
                    continue
                user_name_prof = row['ФИО'] + " " + row['Профес.']
                rez_spis = OTCH.virabotka_sotr(self, start, end, user_name_prof)
                F.save_file(dir + F.sep() + f"{row['ФИО']}_{F.datetostr(F.strtodate(start),'%Y_%m_%d')}.txt",
                            rez_spis ,utf=True, sep='\t')



    def generate_list_plan(self, rez_list):
        plan = []
        if rez_list == None:
            return
        for deistvie in rez_list:
            plan.append([])
            len_hat_c = 0
            if plan == [[]]:
                for key in deistvie.keys():
                    plan[0].append(key)
                plan.append([])
                len_hat_c = len(plan[0])
            for key in deistvie.keys():
                plan[-1].append(str(deistvie[key]))
            if len(plan[-1]) < len_hat_c:
                for i in range(len_hat_c - len(plan[-1])):
                    plan[0].append('')
        return plan

    def save_excell_plan(self, rez_list, path, name):
        if rez_list == None:
            return
        plan = self.generate_list_plan(rez_list)
        CEX.zap_spis(plan, path, name, '1', 1, 1)

    def keyReleaseEvent(self, e):
        if e.key() == 80 and e.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
            if CQT.focus_is_QTableWidget():
                CQT.refill_tbl_into_msgbox_get_table(self,QtWidgets.QApplication.focusWidget())
        if self.ui.tbl_viev_etaps_erp_filtr.hasFocus():
            if e.key() == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_viev_etaps_erp_filtr, self.ui.tbl_viev_etaps_erp)
        if self.ui.tbl_compare_exel_filtr.hasFocus():
            if e.key() == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_compare_exel_filtr, self.ui.tbl_compare_exel)
        if e.key() == 67 and e.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
            if CQT.focus_is_QTableWidget():
                CQT.copy_bufer_table(QtWidgets.QApplication.focusWidget())
        if self.ui.tbl_filtr_dse.hasFocus():
            if e.key() == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_filtr_dse, self.ui.tbl_dse)
        if self.ui.tbl_zamech_filtr.hasFocus():
            if e.key() == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_zamech_filtr, self.ui.tbl_zamech)
        if self.ui.tbl_report_c_filtr.hasFocus():
            if e.key() == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_report_c_filtr, self.ui.tbl_report_c)
                if self.ui.cmb_sort_c_report.currentText() == 'Журнал работ':
                    CMS.apply_summ_с(self,
                                                                                                      self.ui.tbl_report_c)
                if self.ui.cmb_sort_c_report.currentText() == 'Выработка цеха понарядно':
                    CMS.apply_summ_с(self,
                                                                                                      self.ui.tbl_report_c,
                                                                                                      sredn=True)
                if self.ui.cmb_sort_c_report.currentText() == 'Выработка сотрудника':
                    CMS.apply_summ_с(self,
                                                                                                      self.ui.tbl_report_c)
                if self.ui.cmb_sort_c_report.currentText() == 'Понедельный график выработки и отгрузок':
                    CMS.apply_summ_с(self,
                                                                                                      self.ui.tbl_report_c,
                                                                                                      sredn=True)
                if self.ui.cmb_sort_c_report.currentText() == 'Статистика нормо-весовых харктеристик МК':
                    CMS.apply_summ_с(self,
                                                                                                      self.ui.tbl_report_c,
                                                                                                      sredn=True)
                if self.ui.cmb_sort_c_report.currentText() == 'План работ':
                    CMS.apply_summ_с(self,
                                                                                                      self.ui.tbl_report_c,
                                                                                                      sredn=True)
                if self.ui.cmb_sort_c_report.currentText() == 'Норматив материалов по завершенным нарядам':
                    CMS.apply_summ_с(self,
                                                                                                      self.ui.tbl_report_c,
                                                                                                      sredn=True)
                if self.ui.cmb_sort_c_report.currentText() == 'Журнал_техкарт':
                    CMS.apply_summ_с(self,
                                                                                                      self.ui.tbl_report_c,
                                                                                                      sredn=True)
                if self.ui.cmb_sort_c_report.currentText() == 'Журнал_замечаний':
                    CMS.apply_summ_с(self,
                                                                                                      self.ui.tbl_report_c,
                                                                                                      sredn=True)
                if self.ui.cmb_sort_c_report.currentText() == 'График удельной производительности сборочного цеха':
                    CMS.apply_summ_с(self,
                                                                                                      self.ui.tbl_report_c,
                                                                                                      sredn=True)
                self.ui.tbl_report_c.isRowHidden(1)
        if self.ui.tbl_mk_filtr.hasFocus():
            if e.key() == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_mk_filtr, self.ui.tbl_mk)
        if self.ui.tbl_jur_filtr.hasFocus():
            if e.key() == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_jur_filtr, self.ui.tbl_jur)
        if e.key() == QtCore.Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
    def tbl_report_itemSelectionChanged(self):
        CQT.summ_selct_tbl(self, self.ui.tbl_report_c)


    @CQT.onerror
    def tbl_report_add_itemSelectionChanged(self,*args):

        ARMOPER.report_add_itemSelectionChanged(self)

        CQT.clear_tbl(self.ui.tbl_viev_etaps_erp)

    @CQT.onerror
    def tbl_viev_etaps_name_itemSelectionChanged(self,*args):
        ARMOPER.viev_etaps_name_itemSelectionChanged(self)

    def tab_click(self, ind):
        tab = self.ui.tabWidget
        if tab.tabText(ind) == 'Отчеты':
            dat = F.datetostr(DT.today() - timedelta(days=7))
            konec = F.start_end_dates_c(date=dat, vid='n')[1]
            nach = F.start_end_dates_c(date=dat, vid='n')[0]
            self.ui.le_end_of_period.setText(konec)
            self.ui.le_start_of_period.setText(nach)
            CQT.clear_tbl(self.ui.tbl_report_c)
            CQT.clear_tbl(self.ui.tbl_report_c_filtr)

    def OTCH_report_c(self, val):
        pass

    def calc_stage(self, fio):
        """расчет этпапа"""


        #name =' '.join(key.split(' ')[:3])
        if fio in self.DICT_EMPLOEE_FULL_WITH_DEL:
            podr = self.DICT_EMPLOEE_FULL_WITH_DEL[fio]['Подразделение']
            for rc in self.DICT_RC:
                if self.DICT_RC[rc]['empl_Подразделение'] == podr:
                    return rc
        for key in self.DICT_EMPLOEE_RC:
            if fio in key:
                return self.DICT_EMPLOEE_RC[key]
        return

    def fill_dse(self):
        tbl_mk = self.ui.tbl_mk
        nk_nom_mk = CQT.num_col_by_name_c(tbl_mk, 'Пномер')

        r = tbl_mk.currentRow()
        nom_mk = int(tbl_mk.item(r, nk_nom_mk).text())
        if nom_mk == 0:
            return
        self.glob_nom_mk = nom_mk
        if nom_mk not in self.dict_res:
            CQT.msgbox(f'Ресурная не найдена')
            return
        res = F.from_binary_pickle(self.dict_res[nom_mk])

        if res == '':
            conn_res, cur_res = CSQ.connect_bd(self.db_resxml)
            res = CMS.load_res(nom_mk, conn=conn_res, cur=cur_res)
            CSQ.close_bd(conn_res, cur_res)

        # print(filtr)
        tabl_dse = self.ui.tbl_dse

        spis_shap_mk = [
            ['Чек', "Наименование", "Обозначение", "В работу,шт.", 'Уровень', "Количество,шт.", "Освоено,шт.",
             'Закрыто,шт.',
             'Ном_оп', "Операция",
             "Масса/М1,М2,М3", "Ссылка", "ID",
             "Примечание", "ПКИ", "Тпз", "Тшт", 'РЦ', 'Оборудование', "Профессия", "Вид_работ",
             "КР", "КОИД", "Документы", 'Переходы']]
        spis_shab_mk = []

        set_etapi = set()
        for i, dse in enumerate(res):
            naim = CMS.level_decor_c(dse['Наименование'], dse['Уровень'])
            nn = CMS.level_decor_c(dse['Номенклатурный_номер'], dse['Уровень'])
            kolich = dse['Количество']
            mat = dse['Мат_кд']
            ssil = dse['Ссылка']
            id = dse['Номерпп']
            prim = dse['Прим']
            pki = dse['ПКИ']
            ur = dse['Уровень']

            for j, oper in enumerate(dse['Операции']):
                if 'Освоено,шт.' not in oper:
                    res[i]['Операции'][j]['Освоено,шт.'] = 0
                if 'Закрыто,шт.' not in oper:
                    res[i]['Операции'][j]['Закрыто,шт.'] = 0
                flag_strukturn_dostup = True
                # print(flag_strukturn_dostup)
                if flag_strukturn_dostup:
                    zakrito = oper['Закрыто,шт.']
                    osvoeno = oper['Освоено,шт.']
                    oper_naim = oper['Опер_наименование']
                    oper_nom = oper['Опер_номер']
                    oper_rc_kod = oper['Опер_РЦ_код']
                    oper_oborud = oper['Опер_оборудование_наименование']
                    oper_tpz = oper['Опер_Тпз']
                    oper_tst = round(F.valm(oper['Опер_Тшт']) / kolich, 6)
                    oper_prof = oper['Опер_профессия_наименование']

                    oper_sort_crab = oper['Опер_профессия_код']
                    if oper_sort_crab in self.DICT_PROFESSIONS:
                        oper_sort_crab = self.DICT_PROFESSIONS[oper_sort_crab]['вид работ']
                    oper_kr = oper['Опер_КР']
                    oper_koid = oper['Опер_КОИД']
                    docs = '; '.join(dse['Документы']) + "; " + '; '.join(oper['Опер_документы'])
                    perehod = '; '.join(oper['Переходы'])
                    v_raboty = kolich - osvoeno
                    spis_shab_mk.append(
                        ['', naim, nn, v_raboty, ur, kolich, osvoeno, zakrito, oper_nom, oper_naim, mat, ssil, id,
                         prim, pki, oper_tpz, oper_tst, oper_rc_kod, oper_oborud,
                         oper_prof, oper_sort_crab, oper_kr, oper_koid, docs, perehod])

        spis_shab_mk = sorted(spis_shab_mk, key=lambda ppor: ppor[F.num_col_by_name_in_hat_c(spis_shap_mk, 'ID')],
                              reverse=True)
        spis_shab_mk.insert(0, spis_shap_mk[0])
        set_red = {F.num_col_by_name_in_hat_c(spis_shab_mk, "В работу,шт.")}
        CQT.fill_wtabl_old_c(self, spis_shab_mk, tabl_dse, 0, set_red, '', '', 600, True, '', 40)
        tabl_dse.setColumnWidth(CQT.num_col_by_name_c(tabl_dse, 'Наименование'), 350)
        tabl_dse.setColumnWidth(CQT.num_col_by_name_c(tabl_dse, 'Обозначение'), 350)
        tabl_dse.setColumnWidth(CQT.num_col_by_name_c(tabl_dse, 'Масса/М1,М2,М3'), 200)
        tabl_dse.setColumnWidth(CQT.num_col_by_name_c(tabl_dse, 'Ссылка'), 70)
        tabl_dse.setColumnHidden(CQT.num_col_by_name_c(tabl_dse, 'ID'), True)
        nk_check = CQT.num_col_by_name_c(tabl_dse, 'Чек')

        CMS.fill_filtr_c(self, self.ui.tbl_filtr_dse, tabl_dse)
        CMS.load_column_widths(self, tabl_dse)
        self.info_label()
        self.formalize_dse()

    @CQT.onerror
    def formalize_dse(self):
        tbl = self.ui.tbl_dse
        nk_ur = CQT.num_col_by_name_c(tbl, 'Уровень')
        nk_v_rab = CQT.num_col_by_name_c(tbl, 'В работу,шт.')
        max_ur = 0
        for i in range(tbl.rowCount()):
            ur = int(tbl.item(i, nk_ur).text())
            if ur > max_ur:
                max_ur = ur
        if max_ur == 0:
            shag = 55
        else:
            shag = 155 // max_ur
        for i in range(tbl.rowCount()):
            ur = int(tbl.item(i, nk_ur).text())
            ed = 255 - (max_ur - ur) * shag
            CQT.set_color_row_wtab_c(tbl, i, 0 + ed, 225, 0 + ed)
            CQT.add_color_wtab_c(tbl, i, nk_v_rab, 0, 15, 15)

    @CQT.onerror
    def info_label(self):
        lbl = self.ui.lbl_curr_mk
        tabl_sp_mk = self.ui.tbl_mk
        flag = None
        for i in range(tabl_sp_mk.rowCount()):
            if tabl_sp_mk.item(i, 0) == None:
                break
            if tabl_sp_mk.item(i, 0).text() == str(self.glob_nom_mk):
                tabl_sp_mk.setCurrentCell(i, 0)
                flag = i
                break
        if flag == None:
            lbl.setText('')
        else:
            lbl.setText(
                f'МК {tabl_sp_mk.item(flag, 0).text()} - {tabl_sp_mk.item(flag, 3).text()} '
                f'({tabl_sp_mk.item(flag, 6).text()})')

    def fill_jurnal(self):
        nk_nom_mk = CQT.num_col_by_name_c(self.ui.tbl_mk, 'Пномер')
        nom_mk = int(self.ui.tbl_mk.item(self.ui.tbl_mk.currentRow(), nk_nom_mk).text())
        custom_request_c = f'''SELECT jurnal.Дата, jurnal.Статус, 
                    jurnal.Номер_наряда, jurnal.Примечание AS "Примеч_журнал", 
                    naryad.ФИО, naryad.Фвремя, naryad.ФИО2, 
                    naryad.Фвремя2, naryad.Задание, 
                    naryad.Внеплан, naryad.Примечание AS "Примеч_наряд" FROM jurnal 
                    INNER JOIN naryad ON jurnal.Номер_наряда == naryad.Пномер 
                    INNER JOIN mk ON naryad.Номер_мк == mk.Пномер 
                    WHERE mk.Пномер == {nom_mk} AND jurnal.Статус == "Завершен"'''
        rez = CSQ.custom_request_c(self.bd_naryad, custom_request_c)
        CQT.fill_wtabl_old_c(self, rez, self.ui.tbl_jur, separ='', isp_hat_c=True)
        CMS.fill_filtr_c(self, self.ui.tbl_jur_filtr, self.ui.tbl_jur)
        CQT.clear_tbl(self.ui.tbl_zadanie)

    def load_jkzam_excel(self, query):
        list = CEX.read_file(
            'O:\Журналы и графики\Журнал конструкторских замечаний\Журнал конструкторских замечаний.xlsm', 'Лист1', 1,
            '*', 2, 17)
        list_dicts = F.list_to_dict(list)
        for item in list_dicts[1:]:
            pr_py = str(item['Заказ']).replace('.0', '') + '$' + str(item['Проект'])
            if pr_py not in self.DICT_MK:
                continue
            query.append(
                [str(item['№']) + "_z", F.datetostr(item['Дата ']), self.DICT_MK[pr_py], '', item['Содержание'],
                 item['Отдел'],
                 item['Простой/мин'], item['Трудозатры раб/мин'], item['Материал (брак неиспр)'],
                 '', item['Код замечания'], item['Прим. СГК']])
        return query

    def load_remarks(self):
        query = CSQ.custom_request_c(self.bd_naryad, f"""SELECT * FROM zamech""")
        if F.existence_file_c(
                'O:\Журналы и графики\Журнал конструкторских замечаний\Журнал конструкторских замечаний.xlsm'):
            query = self.load_jkzam_excel(query)
        else:
            CQT.msgbox(f'Нет доступа к журналу конструкторскиих замечаний')
        return query

    def fill_remarks(self):
        tbl_mk = self.ui.tbl_mk
        nk_nom_mk = CQT.num_col_by_name_c(tbl_mk, 'Пномер')
        r = tbl_mk.currentRow()
        nom_mk = int(tbl_mk.item(r, nk_nom_mk).text())
        if nom_mk == 0:
            return
        self.glob_nom_mk = nom_mk
        nk_mk = F.num_col_by_name_in_hat_c(self.LIST_ZAMECH, 'МК')
        rez_list = [self.LIST_ZAMECH[0]]
        for i in range(len(self.LIST_ZAMECH)):
            if self.LIST_ZAMECH[i][nk_mk] == nom_mk:
                rez_list.append(self.LIST_ZAMECH[i])
        CQT.fill_wtabl(rez_list, self.ui.tbl_zamech)
        CMS.fill_filtr_c(self, self.ui.tbl_zamech_filtr, self.ui.tbl_zamech)

    def select_mk(self):
        if self.ui.tbl_mk.currentRow() == -1:
            return

        self.fill_jurnal()
        self.fill_dse()
        self.fill_remarks()

    def select_jur(self):
        if self.ui.tbl_jur.currentRow() == -1:
            return
        nk_zadanie = CQT.num_col_by_name_c(self.ui.tbl_jur, 'Задание')

        zad = self.ui.tbl_jur.item(self.ui.tbl_jur.currentRow(), nk_zadanie).text().split('\n')
        zad = [[_] for _ in zad]
        zad.insert(0, ['Задание'])
        CQT.fill_wtabl_old_c(self, zad, self.ui.tbl_zadanie, separ='', isp_hat_c=True)

    def load_mk(self, napr):
        custom_request_c = f'''SELECT DISTINCT mk.Пномер, mk.Статус, mk.Вид, mk.Номенклатура, mk.Номер_заказа, mk.Номер_проекта, 
                            mk.Примечание, mk.Основание, mk.Приоритет, mk.Направление, mk.Вес, mk.Количество, "" as Ресурсная,
                            zagot.Прим_резка, '' as "Прогресс_01",  '' as "Резка",  '' as "Мех_обр", 
                            '' as "Сборка",  '' as "Покрытие" 
                            FROM mk 
                    INNER JOIN zagot ON mk.Пномер = zagot.Ном_МК 
                    WHERE mk.Направление == "{napr}" ORDER BY mk.Приоритет DESC;'''
        spis = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True)
        nk_nom_mk = F.num_col_by_name_in_hat_c(spis, 'Пномер')
        nk_res = F.num_col_by_name_in_hat_c(spis, 'Ресурсная')
        nk_obsh = F.num_col_by_name_in_hat_c(spis, 'Прогресс_01')
        nk_zag = F.num_col_by_name_in_hat_c(spis, 'Резка')
        nk_meh = F.num_col_by_name_in_hat_c(spis, 'Мех_обр')
        nk_sb = F.num_col_by_name_in_hat_c(spis, 'Сборка')
        nk_mal = F.num_col_by_name_in_hat_c(spis, 'Покрытие')

        list_nom_mk = tuple([_[nk_nom_mk] for _ in spis[1:]])

        dict_res = CSQ.custom_request_c(self.db_resxml, f"""SELECT * FROM res WHERE Номер_мк in {list_nom_mk}""",
                                        rez_dict=True)
        self.dict_res = F.deploy_dict_c(dict_res, 'Номер_мк')

        for i in range(1, len(spis)):
            if spis[i][nk_nom_mk] not in self.dict_res:
                print(f'МК№ {spis[i][nk_nom_mk]} не найдена ресурсная')
                continue
            res = F.from_binary_pickle(self.dict_res[spis[i][nk_nom_mk]])
            if res == None:
                print(f'МК№ {spis[i][nk_nom_mk]} не корректная ресурсная')
                continue
            spis[i][nk_obsh] = CMS.percent_of_completion_c(res, '01')
            spis[i][nk_zag] = CMS.percent_of_completion_c(res, '0101')
            spis[i][nk_meh] = CMS.percent_of_completion_c(res, '0102')
            spis[i][nk_sb] = CMS.percent_of_completion_c(res, '0103')
            spis[i][nk_mal] = CMS.percent_of_completion_c(res, '0104')
        red_col = {}
        set_isp_col = {_ for _ in range(len(spis[0])) if _ != nk_res}
        CQT.fill_wtabl_old_c(self, spis, self.ui.tbl_mk, set_isp_col, red_col, (), '', 200, True, '', )
        nk_obsh_t = CQT.num_col_by_name_c(self.ui.tbl_mk, 'Прогресс_01')
        nk_zag_t = CQT.num_col_by_name_c(self.ui.tbl_mk, 'Резка')
        nk_meh_t = CQT.num_col_by_name_c(self.ui.tbl_mk, 'Мех_обр')
        nk_sb_t = CQT.num_col_by_name_c(self.ui.tbl_mk, 'Сборка')
        nk_mal_t = CQT.num_col_by_name_c(self.ui.tbl_mk, 'Покрытие')
        CQT.fill_progress_c(self, self.ui.tbl_mk, nk_obsh_t)
        CQT.fill_progress_c(self, self.ui.tbl_mk, nk_zag_t, isp_poc=False)
        CQT.fill_progress_c(self, self.ui.tbl_mk, nk_meh_t, isp_poc=False)
        CQT.fill_progress_c(self, self.ui.tbl_mk, nk_sb_t, isp_poc=False)
        CQT.fill_progress_c(self, self.ui.tbl_mk, nk_mal_t, isp_poc=False)

    def choose_direction(self):
        napr = self.ui.cmb_napr.currentText()
        if napr == '':
            CQT.clear_tbl(self.ui.tbl_jur)
            CQT.clear_tbl(self.ui.tbl_jur_filtr)
            CQT.clear_tbl(self.ui.tbl_mk)
            CQT.clear_tbl(self.ui.tbl_mk_filtr)
        else:
            self.load_mk(napr)
            CMS.load_column_widths(self, self.ui.tbl_mk)
            self.filtr = CMS.fill_filtr_c(self, self.ui.tbl_mk_filtr, self.ui.tbl_mk)
            nk_status = CQT.num_col_by_name_c(self.ui.tbl_mk_filtr, 'Статус')
            self.ui.tbl_mk_filtr.item(0, nk_status).setText('!Закрыта')
            CMS.apply_filtr_c(self, self.ui.tbl_mk_filtr, self.ui.tbl_mk)

    def export_table_txt(self):
        tab = self.ui.tabWidget
        if tab.currentIndex() == CQT.number_table_by_name_c(tab, 'Отчеты'):
            dir_folder = CMS.load_tmp_folder(self, "export_table")
            if dir_folder == None:
                return
            imaf = f'Отчет_{str(self.ui.cmb_sort_c_report.currentText())}_{F.now("%d.%m.%Y %H;%M")}.txt'
            spis = CQT.list_from_wtabl_c(self.ui.tbl_report_c, hat_c=True)
            spis = F.list_txt_table_c(spis)
            F.save_file(dir_folder + F.sep() + imaf, spis)
            F.open_dir_c(dir_folder)
        if tab.currentIndex() == CQT.number_table_by_name_c(tab, 'Маршрутные карты'):
            table_name = ''
            spis = ''
            if self.ui.tbl_jur.hasFocus():
                table_name = 'Журнал работ'
                spis = CQT.list_from_wtabl_c(self.ui.tbl_jur, hat_c=True, only_visible=True)
            if self.ui.tbl_mk.hasFocus():
                table_name = 'Маршрутные карты'
                spis = CQT.list_from_wtabl_c(self.ui.tbl_mk, hat_c=True, only_visible=True)
            if self.ui.tbl_zadanie.hasFocus():
                table_name = 'Задание'
                spis = CQT.list_from_wtabl_c(self.ui.tbl_zadanie, hat_c=True, only_visible=True)
            if table_name == '':
                CQT.msgbox('Не выбрана таблица для печати')
                return
            dir_folder = CMS.load_tmp_folder(self, "export_table")
            if dir_folder == None:
                return
            imaf = f'Таблица_{table_name}_{F.now("%d.%m.%Y %H;%M")}.txt'
            spis = F.list_txt_table_c(spis)
            F.save_file(dir_folder + F.sep() + imaf, spis)
            F.open_dir_c(dir_folder)

    def export_table(self):
        tab = self.ui.tabWidget
        if tab.currentIndex() == CQT.number_table_by_name_c(tab, 'Отчеты'):
            dir_folder = CMS.load_tmp_folder(self, "export_table")
            if dir_folder == None:
                return
            imaf = f'Отчет_{str(self.ui.cmb_sort_c_report.currentText())}_{F.now("%d.%m.%Y %H;%M")}.xlsx'
            #spis = CQT.list_from_wtabl_c(self.ui.tbl_report_c, hat_c=True, only_visible=True)
            #CEX.zap_spis(spis, dir_folder, imaf, '1', 1, 1, True, True, 'g')
            #F.open_dir_c(dir_folder)

            #row = CQT.get_dict_line_form_tbl(self.ui.tbl_kal_pl)
            putf = F.put_po_umolch()
            wb_name = imaf
            ws_name = '1'
            tbl = self.ui.tbl_report_c
            #hat = F.list_of_dicts_to_list_of_lists([row])
            #hat = F.transpose_list_of_lists(hat)
            wo_hide = CQT.msgboxgYN(f'Не выгружать скрытые элементы таблицы(строки/колонки)?')
            file_path = CEX.save_table_colour(tbl, putf, wb_name, ws_name,wo_hide_rows_cols=wo_hide)
            F.run_file_os_c(file_path)


        if tab.currentIndex() == CQT.number_table_by_name_c(tab, 'Маршрутные карты'):
            table_name = ''
            if self.ui.tbl_jur.hasFocus():
                table_name = 'Журнал работ'
                spis = CQT.list_from_wtabl_c(self.ui.tbl_jur, hat_c=True, only_visible=True)
            if self.ui.tbl_mk.hasFocus():
                table_name = 'Маршрутные карты'
                spis = CQT.list_from_wtabl_c(self.ui.tbl_mk, hat_c=True, only_visible=True)
            if self.ui.tbl_zadanie.hasFocus():
                table_name = 'Задание'
                spis = CQT.list_from_wtabl_c(self.ui.tbl_zadanie, hat_c=True, only_visible=True)
            if table_name == '':
                CQT.msgbox('Не выбрана таблица для печати')
                return
            dir_folder = CMS.load_tmp_folder(self, "export_table")
            if dir_folder == None:
                return
            imaf = f'Таблица_{table_name}_{F.now("%d.%m.%Y %H;%M")}.xlsx'
            CEX.zap_spis(spis, dir_folder, imaf, '1', 1, 1, True, True, 'g')
            F.open_dir_c(dir_folder)


app = QtWidgets.QApplication(['', '--no-sandbox'])

args = sys.argv[1:]
myappid = 'Powerz.BAG.SystCreateWork.1.0.4'  # !!!
QtWin.setCurrentProcessExplicitAppUserModelID(myappid)
app.setWindowIcon(QtGui.QIcon(os.path.join("icons", "icon.png")))
# ========================================================
application = mywindow()
if CMS.kontrol_ver(application.versia, "Просмотр") == False:
    sys.exit()
# =========================================================

S = cfg['Stile'].split(",")
app.setStyle(S[0])
application.showMaximized()
sys.exit(app.exec())
