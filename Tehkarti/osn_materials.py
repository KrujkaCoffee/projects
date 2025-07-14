import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_Qt as CQT
import project_cust_38.nomenklatura as nomenklatura
import project_cust_38.Cust_SQLite as CSQ

def num_col_by_name_in_hat_c_bdmat(sp, ima, vid):
    if vid not in nomenklatura.DICT_POLE:
        CQT.msgbox(f'В словаре не нейден {vid}')
        return
    for key in nomenklatura.DICT_POLE[vid].keys():
        if nomenklatura.DICT_POLE[vid][key] == ima:
            return F.num_col_by_name_in_hat_c(sp, key)

@CQT.onerror
def zagr_sortament(self):
    tbl = self.ui.tbl_resch_mater
    CQT.clear_tbl(tbl)
    tbln = self.ui.tableW_oper_mat
    if tbln.currentRow() == None or tbln.currentRow() == -1:
        return
    if tbln.item(tbln.currentRow(), CQT.num_col_by_name_c(tbln, 'Код')) == None:
        return
    if 'f' in tbln.item(tbln.currentRow(), CQT.num_col_by_name_c(tbln, 'Код')).text():
        return
    spis = zag_param_mat(self,tbln.item(tbln.currentRow(), CQT.num_col_by_name_c(tbln, 'Код')).text())
    if spis == False or spis == None or len(spis) == 1:
        return
    vid = spis[-1][F.num_col_by_name_in_hat_c(spis, 'Вид')]
    if vid not in nomenklatura.DICT_POLE:
        return
    sort = spis[-1][num_col_by_name_in_hat_c_bdmat(spis, 'Сортамент',vid)]
    try:
        if sort == '1':
            self.ui.opt_but_list.setChecked(True)
            mat_list_load(self)
        if sort == '2':
            self.ui.opt_but_krug.setChecked(True)
            mat_krug_load(self)
        if sort == '3':
            self.ui.opt_but_truba.setChecked(True)
            mat_truba_load(self)
        if sort == '4':
            self.ui.opt_but_dvut.setChecked(True)
            mat_dvut_load(self)
        if sort == '5':
            self.ui.opt_but_ygol.setChecked(True)
            mat_ygol_load(self)
        if sort == '6':
            self.ui.opt_but_shvel.setChecked(True)
            mat_shvel_load(self)
        if sort == '7':
            self.ui.opt_but_truba_kv.setChecked(True)
            mat_truba_kv_load(self)
        if sort == '8':
            self.ui.opt_but_kv.setChecked(True)
            mat_kv_load(self)
        if sort == '9':
            self.ui.opt_but_truba_kv.setChecked(True)
            mat_shestigr_load(self)
        if sort == '10':
            self.ui.opt_but_nabivka.setChecked(True)
            mat_nabivka_load(self)
    except:
        CQT.msgbox(f'ОШибка загрузки сортамента')

def raschet_list(self,spis):
    n_k_tol_list = F.num_col_by_name_in_hat_c(spis, 'Толщина листа, мм')
    n_k_shir_zagot = F.num_col_by_name_in_hat_c(spis, 'Ширина загот., мм')
    n_k_dlin_zagot = F.num_col_by_name_in_hat_c(spis, 'Длина загот., мм')
    n_k_shir_list = F.num_col_by_name_in_hat_c(spis, 'Ширина листа, мм')
    n_k_dl_list = F.num_col_by_name_in_hat_c(spis, 'Длина листа, мм')
    n_k_plotnost = F.num_col_by_name_in_hat_c(spis, 'р -плотность(г/см2)')
    n_k_chislo_seg = F.num_col_by_name_in_hat_c(spis, 'Число сегментов, шт.')
    for i in range(len(spis[-1])):
        if F.is_numeric(spis[-1][i]) == False:
            CQT.msgbox(f'В колонке {spis[0][i]} не число')
            return
    tolshina = F.valm(spis[-1][n_k_tol_list])
    shir_zagot = F.valm(spis[-1][n_k_shir_zagot])
    lina_zagot = F.valm(spis[-1][n_k_dlin_zagot])
    shir_list = F.valm(spis[-1][n_k_shir_list])
    dlina_list = F.valm(spis[-1][n_k_dl_list])
    plotnost = F.valm(spis[-1][n_k_plotnost])
    segment_count = F.valm(spis[-1][n_k_chislo_seg])
    if dlina_list // lina_zagot * shir_list // shir_zagot > dlina_list // shir_zagot * shir_list // lina_zagot:
        ndl = dlina_list // shir_zagot
        nsh = shir_list // lina_zagot
        g1, g2 = shir_zagot, lina_zagot
    else:
        ndl = dlina_list // lina_zagot
        nsh = shir_list // shir_zagot
        g1, g2 = lina_zagot, shir_zagot

    b = shir_list - g2 * nsh
    l = dlina_list - g1 * ndl
    if nsh == 0 or ndl == 0:
        CQT.msgbox('Заготовка превышает габариты листа')
        Nr = 0
    else:
        Nr = tolshina * (shir_zagot + b / nsh) * (lina_zagot + l / ndl) * plotnost * segment_count / 1000000
    return Nr

def raschet_krug(self,spis):
    n_k_diam = F.num_col_by_name_in_hat_c(spis, 'Диаметр, мм')
    n_k_dl_z = F.num_col_by_name_in_hat_c(spis, 'Длина загот., мм')
    n_k_dl_k = F.num_col_by_name_in_hat_c(spis, 'Длина круга., мм')
    n_k_plotnost = F.num_col_by_name_in_hat_c(spis, 'р -плотность(г/см2)')
    for i in range(len(spis[-1])):
        if F.is_numeric(spis[-1][i]) == False:
            CQT.msgbox(f'В колонке {spis[0][i]} не число')
            return
    d = F.valm(spis[-1][n_k_diam])
    lz = F.valm(spis[-1][n_k_dl_z])
    pl = F.valm(spis[-1][n_k_plotnost])
    lk = F.valm(spis[-1][n_k_dl_k])
    n = lk // lz
    lo = lk - n * lz
    Nr = 3.141592 * d ** 2 / 4 * (lz + lo) * pl / 1000000
    return Nr

def raschet_truba(self,spis):
    n_k_diam_naruj = F.num_col_by_name_in_hat_c(spis, 'Диаметр наружний, мм')
    n_k_diam_vnutr = F.num_col_by_name_in_hat_c(spis, 'Диаметр внутренний, мм')
    n_k_dlina_zagotovk = F.num_col_by_name_in_hat_c(spis, 'Длина загот., мм')
    n_k_dlina_trub = F.num_col_by_name_in_hat_c(spis, 'Длина трубы., мм')
    n_k_plotnost = F.num_col_by_name_in_hat_c(spis, 'р -плотность(г/см2)')

    for i in range(len(spis[-1])):
        if F.is_numeric(spis[-1][i]) == False:
            CQT.msgbox(f'В колонке {spis[0][i]} не число')
            return 0

    diametr_naruj = F.valm(spis[-1][n_k_diam_naruj])
    diametr_vnutr = F.valm(spis[-1][n_k_diam_vnutr])
    dlina_zagotovki = F.valm(spis[-1][n_k_dlina_zagotovk])
    plotn = F.valm(spis[-1][n_k_plotnost])
    dlina_trub = F.valm(spis[-1][n_k_dlina_trub])
    kolvo_det = dlina_trub // dlina_zagotovki
    nedel_othod = dlina_trub % dlina_zagotovki
    norm_trub = dlina_zagotovki + nedel_othod / kolvo_det
    massa_diametr_naruj = diametr_naruj ** 2 / 4 * norm_trub
    massa_diametr_vnutr = diametr_vnutr ** 2 / 4 * norm_trub
    Nr = 3.141592 * (massa_diametr_naruj - massa_diametr_vnutr) * plotn / 1000000
    return Nr


def raschet_dvut(self,spis):
    n_k_B_shirina_polki = F.num_col_by_name_in_hat_c(spis, 'b–ширина полки')
    n_k_S_tolschina_stenki = F.num_col_by_name_in_hat_c(spis, 's–толщина стенки')
    n_k_T_tolschina_polki = F.num_col_by_name_in_hat_c(spis, 't-толщина полки')
    n_k_H_visota_balki = F.num_col_by_name_in_hat_c(spis, 'h–высота балки')
    n_k_dlina_dvutavra = F.num_col_by_name_in_hat_c(spis, 'Длина двутавра, мм')
    n_k_dlina_zagotovki = F.num_col_by_name_in_hat_c(spis, 'Длина загот., мм')
    n_k_plotnost = F.num_col_by_name_in_hat_c(spis, 'р -плотность(г/см2)')

    for i in range(len(spis[-1])):
        if F.is_numeric(spis[-1][i]) == False:
            CQT.msgbox(f'В колонке {spis[0][i]} не число')
            return

    b_shirina_polki = F.valm(spis[-1][n_k_B_shirina_polki])
    s_tolschina_stenki = F.valm(spis[-1][n_k_S_tolschina_stenki])
    t_tolschina_polki = F.valm(spis[-1][n_k_T_tolschina_polki])
    h_visota_balki = F.valm(spis[-1][n_k_H_visota_balki])
    dlina_dvutavra = F.valm(spis[-1][n_k_dlina_dvutavra])
    dlina_zagotovki = F.valm(spis[-1][n_k_dlina_zagotovki])
    plotn = F.valm(spis[-1][n_k_plotnost])
    kolvo_det = dlina_dvutavra // dlina_zagotovki
    nedel_othod = dlina_dvutavra % dlina_zagotovki / kolvo_det

    norm_trub = dlina_zagotovki + nedel_othod
    slagaem = (h_visota_balki - 2 * t_tolschina_polki) * s_tolschina_stenki
    mnojit = 2 * b_shirina_polki * t_tolschina_polki + slagaem
    Nr = mnojit * norm_trub * plotn / 1000000
    return Nr


def raschet_shvel(self,spis):
    n_k_ploschad_poper_sechen = F.num_col_by_name_in_hat_c(spis, 's-площадь поперечного сеч.')
    n_k_dlina_zagotovki = F.num_col_by_name_in_hat_c(spis, 'Длина загот., мм')
    n_k_dlina_shveler = F.num_col_by_name_in_hat_c(spis, 'Длина швеллера, мм')
    n_k_plotnost = F.num_col_by_name_in_hat_c(spis, 'р -плотность(г/см2)')

    for i in range(len(spis[-1])):
        if F.is_numeric(spis[-1][i]) == False:
            CQT.msgbox(f'В колонке {spis[0][i]} не число')
            return

    ploschad_poper_sechen = F.valm(spis[-1][n_k_ploschad_poper_sechen])
    dlina_shveler = F.valm(spis[-1][n_k_dlina_shveler])
    dlina_zagotovki = F.valm(spis[-1][n_k_dlina_zagotovki])
    plotn = F.valm(spis[-1][n_k_plotnost])
    kolvo_det = dlina_shveler // dlina_zagotovki
    nedel_othod = dlina_shveler % dlina_zagotovki / kolvo_det


    norm_trub = dlina_zagotovki + nedel_othod
    Nr = norm_trub * ploschad_poper_sechen * plotn / 1000000
    return Nr


def raschet_ygol(self,spis):
    n_k_tolschina = F.num_col_by_name_in_hat_c(spis, 'Толщина, мм')
    n_k_A_shirina = F.num_col_by_name_in_hat_c(spis, 'a-ширина, мм')
    n_k_B_shirina = F.num_col_by_name_in_hat_c(spis, 'b-ширина, мм')
    n_k_dlina_zagotovki = F.num_col_by_name_in_hat_c(spis, 'Длина загот., мм')
    n_k_dlina_ugolka = F.num_col_by_name_in_hat_c(spis, 'Длина уголка, мм')
    n_k_plotnost = F.num_col_by_name_in_hat_c(spis, 'р -плотность(г/см2)')

    for i in range(len(spis[-1])):
        if F.is_numeric(spis[-1][i]) == False:
            CQT.msgbox(f'В колонке {spis[0][i]} не число')
            return

    tolschina = F.valm(spis[-1][n_k_tolschina])
    a_shirina = F.valm(spis[-1][n_k_A_shirina])
    b_shirina = F.valm(spis[-1][n_k_B_shirina])
    plotn = F.valm(spis[-1][n_k_plotnost])
    dlina_ugolka = F.valm(spis[-1][n_k_dlina_ugolka])
    dlina_zagotovki = F.valm(spis[-1][n_k_dlina_zagotovki])
    kolvo_det = dlina_ugolka // dlina_zagotovki
    nedel_othod = dlina_ugolka % dlina_zagotovki / kolvo_det
    norm_trub = dlina_zagotovki + nedel_othod
    summ_profile = a_shirina + b_shirina - tolschina
    koef = 1 - 3.14159265 / 4
    Nr = (koef + tolschina * summ_profile) * norm_trub * plotn / 1000000
    return Nr


def raschet_nabivka(self,spis):
    n_k_kolvo = F.num_col_by_name_in_hat_c(spis, 'кол-во шт (из КД)')
    n_k_dlina = F.num_col_by_name_in_hat_c(spis, 'длина набивки (из кд)')
    n_k_koef = F.num_col_by_name_in_hat_c(spis, 'коэффициент (из таблицы)')


    for i in range(len(spis[-1])):
        if F.is_numeric(spis[-1][i]) == False:
            CQT.msgbox(f'В колонке {spis[0][i]} не число')
            return

    kolvo = F.valm(spis[-1][n_k_kolvo])
    dlina = F.valm(spis[-1][n_k_dlina])
    koef = F.valm(spis[-1][n_k_koef])

    Nr = kolvo * dlina * koef / 1000
    return Nr


def raschet_shestig(self,spis):
    n_k_diametr_inscribe_c_okruj = F.num_col_by_name_in_hat_c(spis, 'Диаметр вписанной окружности, мм')
    n_k_dlina_shestigrannicka = F.num_col_by_name_in_hat_c(spis, 'Длина шестигранника, мм')
    n_k_dlina_zagotovki = F.num_col_by_name_in_hat_c(spis, 'Длина загот., мм')
    n_k_plotnost = F.num_col_by_name_in_hat_c(spis, 'р -плотность(г/см2)')

    for i in range(len(spis[-1])):
        if F.is_numeric(spis[-1][i]) == False:
            CQT.msgbox(f'В колонке {spis[0][i]} не число')
            return

    diametr_inscribe_c_okruj = F.valm(spis[-1][n_k_diametr_inscribe_c_okruj])
    dlina_shestigrannicka = F.valm(spis[-1][n_k_dlina_shestigrannicka])
    dlina_zagotovki = F.valm(spis[-1][n_k_dlina_zagotovki])
    plotn = F.valm(spis[-1][n_k_plotnost])
    kolvo_det = dlina_shestigrannicka // dlina_zagotovki
    nedel_othod = dlina_shestigrannicka % dlina_zagotovki / kolvo_det

    norm_trub = dlina_zagotovki + nedel_othod
    Nr = 0.87 * diametr_inscribe_c_okruj ** diametr_inscribe_c_okruj * norm_trub * plotn / 1000000
    return Nr


def raschet_kv(self,spis):
    n_k_S_plosch_sechen = F.num_col_by_name_in_hat_c(spis, 's-площадь поперечного сечения')
    n_k_dlina_kvadrata = F.num_col_by_name_in_hat_c(spis, 'Длина квадрата, мм')
    n_k_dlina_zagotovki = F.num_col_by_name_in_hat_c(spis, 'Длина загот., мм')
    n_k_plotnost = F.num_col_by_name_in_hat_c(spis, 'р -плотность(г/см2)')

    for i in range(len(spis[-1])):
        if F.is_numeric(spis[-1][i]) == False:
            CQT.msgbox(f'В колонке {spis[0][i]} не число')
            return

    s_plosch_sechen = F.valm(spis[-1][n_k_S_plosch_sechen])
    dlina_kvadrata = F.valm(spis[-1][n_k_dlina_kvadrata])
    dlina_zagotovki = F.valm(spis[-1][n_k_dlina_zagotovki])
    plotn = F.valm(spis[-1][n_k_plotnost])
    kolvo_det = dlina_kvadrata // dlina_zagotovki
    nedel_othod = dlina_kvadrata % dlina_zagotovki / kolvo_det


    norm_trub = dlina_zagotovki + nedel_othod
    Nr = s_plosch_sechen**2 * norm_trub * plotn / 1000000
    return Nr


def raschet_kvadr_truba(self,spis):
    n_k_tolschina = F.num_col_by_name_in_hat_c(spis, 'Толщина, мм')
    n_k_visota = F.num_col_by_name_in_hat_c(spis, 'Высота, мм')
    n_k_shirina = F.num_col_by_name_in_hat_c(spis, 'Ширина, мм')
    n_k_dlina_zagotovk = F.num_col_by_name_in_hat_c(spis, 'Длина загот., мм')
    n_k_dlina_trub = F.num_col_by_name_in_hat_c(spis, 'Длина трубы, мм')
    n_k_plotnost = F.num_col_by_name_in_hat_c(spis, 'р -плотность(г/см2)')

    for i in range(len(spis[-1])):
        if F.is_numeric(spis[-1][i]) == False:
            CQT.msgbox(f'В колонке {spis[0][i]} не число')
            return

    tolschina = F.valm(spis[-1][n_k_tolschina])
    visota = F.valm(spis[-1][n_k_visota])
    shirina = F.valm(spis[-1][n_k_shirina])
    plotn = F.valm(spis[-1][n_k_plotnost])
    dlina_trub = F.valm(spis[-1][n_k_dlina_trub])
    dlina_zagotovki = F.valm(spis[-1][n_k_dlina_zagotovk])
    kolvo_det = dlina_trub // dlina_zagotovki
    nedel_othod = (dlina_trub % dlina_zagotovki)/kolvo_det
    norm_trub = dlina_zagotovki + nedel_othod

    summ_profile = shirina + visota
    Nr = 2 * tolschina * summ_profile * norm_trub * plotn / 1000000
    return Nr



def vvod_rasch_mat(self):
    tbln = self.ui.tableW_oper_mat
    if tbln.currentRow() == None or tbln.currentRow() == -1:
        return
    Nr = 0
    spis = CQT.list_from_wtabl_c(self.ui.tbl_resch_mater, '', True)
    if self.ui.opt_but_list.isChecked():
        Nr = raschet_list(self,spis)
    if self.ui.opt_but_krug.isChecked():
        Nr = raschet_krug(self, spis)
    if self.ui.opt_but_truba.isChecked():
        Nr = raschet_truba(self, spis)
    if self.ui.opt_but_ygol.isChecked():
        Nr = raschet_ygol(self, spis)
    if self.ui.opt_but_shvel.isChecked():
        Nr = raschet_shvel(self, spis)
    if self.ui.opt_but_dvut.isChecked():
        Nr = raschet_dvut(self, spis)
    if self.ui.opt_but_truba_kv.isChecked():
        Nr = raschet_kvadr_truba(self, spis)
    if self.ui.opt_but_kv.isChecked():
        Nr = raschet_kv(self, spis)
    if self.ui.opt_but_shestig.isChecked():
        Nr = raschet_shestig(self, spis)
    if self.ui.opt_but_nabivka.isChecked():
        Nr = raschet_nabivka(self, spis)
    if Nr == 0:
        return
    Nr = round(Nr, 6)
    tbln.item(tbln.currentRow(), CQT.num_col_by_name_c(tbln, 'Норма')).setText(str(Nr))

def mat_list_load(self):
    tbl = self.ui.tbl_resch_mater
    tree = self.ui.tree
    spis_dreva = CQT.list_from_tree_c(tree)
    tbl_oper_mat = self.ui.tbl_oper_mat
    nk_id = CQT.num_col_by_name_c(tbl_oper_mat, 'ID')
    oper = tbl_oper_mat.item(tbl_oper_mat.currentRow(), nk_id).text()
    if oper == None:
        CQT.msgbox(f'Не выбрана операция')
        return
    for i in range(len(spis_dreva)):
        if spis_dreva[i][3] == oper:
            segment_count = '1'
            if spis_dreva[i][4] == '010101' and 'ЧПУ' in spis_dreva[i][0]:
                if len(spis_dreva) > i+1:
                    if spis_dreva[i+1][20] == '2':
                        if 'част' in spis_dreva[i+1][0].lower() or \
                                'егмент' in spis_dreva[i+1][0].lower() or \
                                'сектор' in spis_dreva[i+1][0].lower():
                            if F.is_numeric(spis_dreva[i+1][0].split()[-1]):
                                segment_count = int(spis_dreva[i+1][0].split()[-1])
                                break
    CQT.clear_tbl(tbl)
    spis = [['Толщина листа, мм', 'Ширина загот., мм', 'Длина загот., мм', "Ширина листа, мм", "Длина листа, мм",
             "р -плотность(г/см2)", 'Число сегментов, шт.']]
    spis.append(['' for _ in spis[0]])
    set_edit = {_ for _ in range(len(spis[0]))}
    tbln = self.ui.tableW_oper_mat
    spis[1][F.num_col_by_name_in_hat_c(spis, 'Число сегментов, шт.')] = '1'
    if tbln.currentRow() != -1:
        if tbln.item(tbln.currentRow(), CQT.num_col_by_name_c(tbln, 'Код')) == None:
            return
        nn = tbln.item(tbln.currentRow(), CQT.num_col_by_name_c(tbln, 'Код')).text()
        spis_mat = zag_param_mat(self,nn)
        if spis_mat != None and len(spis_mat) == 2:
            vid = spis_mat[-1][F.num_col_by_name_in_hat_c(spis_mat, 'Вид')]
            nk_nn = F.num_col_by_name_in_hat_c(spis_mat, 'Код')
            nk_tol = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Толщина', vid)
            nk_shir = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Ширина', vid)
            nk_dl = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Длина', vid)
            nk_pl = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Плотность', vid)
            #nk_sort = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Сортамент', vid)
            #tol = ''
            for i in range(1, len(spis_mat)):
                if spis_mat[i][nk_nn].strip() == nn.strip():
                    if nk_tol != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'Толщина листа, мм')] = spis_mat[i][nk_tol]
                    if nk_shir != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'Ширина листа, мм')] = spis_mat[i][nk_shir]
                    if nk_dl != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'Длина листа, мм')] = spis_mat[i][nk_dl]
                    if nk_pl != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'р -плотность(г/см2)')] = spis_mat[i][nk_pl]
                    if self.global_param_tk_dxf != '':
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'Ширина загот., мм')] = self.global_param_tk_dxf['rect_hmm']
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'Длина загот., мм')] = self.global_param_tk_dxf['rect_lmm']
                    spis[1][F.num_col_by_name_in_hat_c(spis, 'Число сегментов, шт.')] = segment_count
                    #sort = spis_mat[i][nk_sort]

    CQT.fill_wtabl_old_c(self, spis, tbl, set_editeble_col_nomera=set_edit, separ='', isp_hat_c=True)


def mat_krug_load(self):
    tbl = self.ui.tbl_resch_mater
    CQT.clear_tbl(tbl)
    spis = [['Диаметр, мм', 'Длина загот., мм', 'Длина круга., мм', "р -плотность(г/см2)"]]
    spis.append(['' for _ in spis[0]])
    set_edit = {_ for _ in range(len(spis[0]))}
    tbln = self.ui.tableW_oper_mat  # это что?
    if tbln.currentRow() != -1:
        nn = tbln.item(tbln.currentRow(), CQT.num_col_by_name_c(tbln, 'Код')).text()
        spis_mat = zag_param_mat(self,
            nn)  # эта функция будет, та же. она выдаст тебе O:\Производство Powerz\Отдел технолога\ТД\TehKart\Data\bin\bd_mater.txt
        if spis_mat != None and len(spis_mat) == 2:
            vid = spis_mat[-1][F.num_col_by_name_in_hat_c(spis_mat, 'Вид')]
            nk_nn = F.num_col_by_name_in_hat_c(spis_mat, 'Код')
            nk_diametr = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Диаметр', vid)
            nk_pl = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Плотность', vid)
            nk_dlin = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Длина', vid)
            for i in range(1, len(spis_mat)):
                if spis_mat[i][nk_nn].strip() == nn.strip():
                    if nk_diametr != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'Диаметр, мм')] = spis_mat[i][nk_diametr]
                    if nk_pl != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'р -плотность(г/см2)')] = spis_mat[i][nk_pl]
                    if nk_dlin != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'Длина круга., мм')] = spis_mat[i][nk_dlin]
                    break

    CQT.fill_wtabl_old_c(self, spis, tbl, set_editeble_col_nomera=set_edit, separ='', isp_hat_c=True)


def mat_truba_load(self):
    tbl = self.ui.tbl_resch_mater
    CQT.clear_tbl(tbl)
    spis = [['Толщина, мм', 'Диаметр наружний, мм', 'Диаметр внутренний, мм', 'Длина загот., мм',
             'Длина трубы., мм', "р -плотность(г/см2)"]]
    spis.append(['' for _ in spis[0]])
    set_edit = {_ for _ in range(len(spis[0]))}
    tbln = self.ui.tableW_oper_mat  # это что?
    if tbln.currentRow() != -1:
        nn = tbln.item(tbln.currentRow(), CQT.num_col_by_name_c(tbln, 'Код')).text()
        spis_mat = zag_param_mat(self,
            nn)  # эта функция будет, та же. она выдаст тебе O:\Производство Powerz\Отдел технолога\ТД\TehKart\Data\bin\bd_mater.txt
        if spis_mat != None and len(spis_mat) == 2:
            vid = spis_mat[-1][F.num_col_by_name_in_hat_c(spis_mat, 'Вид')]
            nk_nn = F.num_col_by_name_in_hat_c(spis_mat, 'Код')
            nk_tolschina = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Толщина', vid)
            nk_diametr_naruj = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Нар.диаметр', vid)
            nk_diametr_vnutr = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Вн.диаметр', vid)
            nk_plotn = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Плотность', vid)
            nk_dl = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Длина трубы', vid)
            for i in range(1, len(spis_mat)):
                if spis_mat[i][nk_nn].strip() == nn.strip():
                    if nk_tolschina != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'Толщина, мм')] = spis_mat[i][nk_tolschina]
                    if nk_diametr_naruj != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'Диаметр наружний, мм')] = spis_mat[i][nk_diametr_naruj]
                    if nk_diametr_vnutr != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'Диаметр внутренний, мм')] = spis_mat[i][nk_diametr_vnutr]
                    if nk_plotn != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'р -плотность(г/см2)')] = spis_mat[i][nk_plotn]
                    if nk_dl != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'Длина трубы., мм')] = spis_mat[i][nk_dl]
                    break
    CQT.fill_wtabl_old_c(self, spis, tbl, set_editeble_col_nomera=set_edit, separ='', isp_hat_c=True)


def mat_ygol_load(self):
    tbl = self.ui.tbl_resch_mater
    CQT.clear_tbl(tbl)
    spis = [
        ['Толщина, мм', 'a-ширина, мм', 'b-ширина, мм', 'Длина загот., мм', 'Длина уголка, мм', "р -плотность(г/см2)"]]
    spis.append(['' for _ in spis[0]])
    set_edit = {_ for _ in range(len(spis[0]))}
    tbln = self.ui.tableW_oper_mat
    if tbln.currentRow() != -1:
        if tbln.item(tbln.currentRow(), CQT.num_col_by_name_c(tbln, 'Код')) == None:
            return
        nn = tbln.item(tbln.currentRow(), CQT.num_col_by_name_c(tbln, 'Код')).text()
        spis_mat = zag_param_mat(self, nn)
        if spis_mat != None and len(spis_mat) == 2:
            vid = spis_mat[-1][F.num_col_by_name_in_hat_c(spis_mat, 'Вид')]
            nk_nn = F.num_col_by_name_in_hat_c(spis_mat, 'Код')
            nk_tolschina = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Толщина', vid)
            nk_a_shirina = num_col_by_name_in_hat_c_bdmat(spis_mat, 'a-ширина', vid)
            nk_b_shirina = num_col_by_name_in_hat_c_bdmat(spis_mat, 'b-ширина', vid)
            nk_dlina_ugolok = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Длина уголка', vid)
            nk_plotn = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Плотность', vid)
            for i in range(1, len(spis_mat)):
                if spis_mat[i][nk_nn].strip() == nn.strip():
                    if nk_tolschina != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'Толщина, мм')] = spis_mat[i][nk_tolschina]
                    if nk_a_shirina != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'a-ширина, мм')] = spis_mat[i][nk_a_shirina]
                    if nk_b_shirina != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'b-ширина, мм')] = spis_mat[i][nk_b_shirina]
                    if nk_dlina_ugolok != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'Длина уголка, мм')] = spis_mat[i][nk_dlina_ugolok]
                    if nk_plotn != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'р -плотность(г/см2)')] = spis_mat[i][nk_plotn]
                    break
    CQT.fill_wtabl_old_c(self, spis, tbl, set_editeble_col_nomera=set_edit, separ='', isp_hat_c=True)

def mat_shvel_load(self):
    tbl = self.ui.tbl_resch_mater
    CQT.clear_tbl(tbl)
    spis = [['s-площадь поперечного сеч.', 'Длина загот., мм', 'Длина швеллера, мм', "р -плотность(г/см2)"]]
    spis.append(['' for _ in spis[0]])
    set_edit = {_ for _ in range(len(spis[0]))}
    tbln = self.ui.tableW_oper_mat
    if tbln.currentRow() != -1:
        if tbln.item(tbln.currentRow(), CQT.num_col_by_name_c(tbln, 'Код')) == None:
            return
        nn = tbln.item(tbln.currentRow(), CQT.num_col_by_name_c(tbln, 'Код')).text()
        spis_mat = zag_param_mat(self, nn)
        if spis_mat != None and len(spis_mat) == 2:
            vid = spis_mat[-1][F.num_col_by_name_in_hat_c(spis_mat, 'Вид')]
            nk_nn = F.num_col_by_name_in_hat_c(spis_mat, 'Код')
            nk_ploschad_poper_sechen = num_col_by_name_in_hat_c_bdmat(spis_mat, 's-площадь поперечного сечения', vid)
            nk_a_dlina_shveler = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Длина швеллера', vid)
            nk_plotn = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Плотность', vid)
            for i in range(1, len(spis_mat)):
                if spis_mat[i][nk_nn].strip() == nn.strip():
                    if nk_ploschad_poper_sechen != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 's-площадь поперечного сеч.')] = spis_mat[i][nk_ploschad_poper_sechen]
                    if nk_a_dlina_shveler != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'Длина швеллера, мм')] = spis_mat[i][nk_a_dlina_shveler]
                    if nk_plotn != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'р -плотность(г/см2)')] = spis_mat[i][nk_plotn]
                    break
    CQT.fill_wtabl_old_c(self, spis, tbl, set_editeble_col_nomera=set_edit, separ='', isp_hat_c=True)


def mat_dvut_load(self):
    tbl = self.ui.tbl_resch_mater
    CQT.clear_tbl(tbl)
    spis = [['b–ширина полки', 's–толщина стенки', 't-толщина полки', 'h–высота балки', 'Длина двутавра, мм',
             'Длина загот., мм', "р -плотность(г/см2)"]]
    spis.append(['' for _ in spis[0]])
    set_edit = {_ for _ in range(len(spis[0]))}
    tbln = self.ui.tableW_oper_mat
    if tbln.currentRow() != -1:
        if tbln.item(tbln.currentRow(), CQT.num_col_by_name_c(tbln, 'Код')) == None:
            return
        nn = tbln.item(tbln.currentRow(), CQT.num_col_by_name_c(tbln, 'Код')).text()
        spis_mat = zag_param_mat(self, nn)
        if spis_mat != None and len(spis_mat) == 2:
            vid = spis_mat[-1][F.num_col_by_name_in_hat_c(spis_mat, 'Вид')]
            nk_nn = F.num_col_by_name_in_hat_c(spis_mat, 'Код')
            nk_B_shirina_polki = num_col_by_name_in_hat_c_bdmat(spis_mat, 'b-ширина полки', vid)
            nk_S_tolschina_stenki = num_col_by_name_in_hat_c_bdmat(spis_mat, 's-толщина стенки', vid)
            nk_T_tolschina_polki = num_col_by_name_in_hat_c_bdmat(spis_mat, 't-толщина полки', vid)
            nk_H_visota_balki = num_col_by_name_in_hat_c_bdmat(spis_mat, 'h-высота балки', vid)
            nk_dlina_dvutvr = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Длина двутавра', vid)
            nk_plotn = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Плотность', vid)
            for i in range(1, len(spis_mat)):
                if spis_mat[i][nk_nn].strip() == nn.strip():
                    if nk_B_shirina_polki != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'b–ширина полки')] = spis_mat[i][nk_B_shirina_polki]
                    if nk_S_tolschina_stenki != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 's–толщина стенки')] = spis_mat[i][nk_S_tolschina_stenki]
                    if nk_T_tolschina_polki != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 't-толщина полки')] = spis_mat[i][nk_T_tolschina_polki]
                    if nk_H_visota_balki != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'h–высота балки')] = spis_mat[i][nk_H_visota_balki]
                    if nk_dlina_dvutvr != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'Длина двутавра, мм')] = spis_mat[i][nk_dlina_dvutvr]
                    if nk_plotn != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'р -плотность(г/см2)')] = spis_mat[i][nk_plotn]
                    break
    CQT.fill_wtabl_old_c(self, spis, tbl, set_editeble_col_nomera=set_edit, separ='', isp_hat_c=True)

def mat_nabivka_load(self):
    tbl = self.ui.tbl_resch_mater
    CQT.clear_tbl(tbl)
    spis = [['кол-во шт (из КД)', 'длина набивки (из кд)', 'коэффициент (из таблицы)']]
    spis.append(['' for _ in spis[0]])
    set_edit = {_ for _ in range(len(spis[0]))}
    tbln = self.ui.tableW_oper_mat
    if tbln.currentRow() != -1:
        if tbln.item(tbln.currentRow(), CQT.num_col_by_name_c(tbln, 'Код')) == None:
            return
        nn = tbln.item(tbln.currentRow(), CQT.num_col_by_name_c(tbln, 'Код')).text()
        spis_mat = zag_param_mat(self, nn)
        if spis_mat != None and len(spis_mat) == 2:
            vid = spis_mat[-1][F.num_col_by_name_in_hat_c(spis_mat, 'Вид')]
            nk_nn = F.num_col_by_name_in_hat_c(spis_mat, 'Код')
            nk_koef = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Коэффициент', vid)
            for i in range(1, len(spis_mat)):
                if spis_mat[i][nk_nn].strip() == nn.strip():
                    if nk_koef != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'коэффициент (из таблицы)')] = spis_mat[i][nk_koef]
                    break
    CQT.fill_wtabl_old_c(self, spis, tbl, set_editeble_col_nomera=set_edit, separ='', isp_hat_c=True)

def mat_shestigr_load(self):
    tbl = self.ui.tbl_resch_mater
    CQT.clear_tbl(tbl)
    spis = [['Диаметр вписанной окружности, мм', 'Длина шестигранника, мм', 'Длина загот., мм', "р -плотность(г/см2)"]]
    spis.append(['' for _ in spis[0]])
    set_edit = {_ for _ in range(len(spis[0]))}
    tbln = self.ui.tableW_oper_mat
    if tbln.currentRow() != -1:
        if tbln.item(tbln.currentRow(), CQT.num_col_by_name_c(tbln, 'Код')) == None:
            return
        nn = tbln.item(tbln.currentRow(), CQT.num_col_by_name_c(tbln, 'Код')).text()
        spis_mat = zag_param_mat(self, nn)
        if spis_mat != None and len(spis_mat) == 2:
            vid = spis_mat[-1][F.num_col_by_name_in_hat_c(spis_mat, 'Вид')]
            nk_nn = F.num_col_by_name_in_hat_c(spis_mat, 'Код')
            nk_diametr_inscribe_c_okruj = num_col_by_name_in_hat_c_bdmat(spis_mat, 'd–диаметр вписанной окружности', vid)
            nk_dlina_shestigrannicka = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Длина шестигранника', vid)
            nk_plotn = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Плотность', vid)
            for i in range(1, len(spis_mat)):
                if spis_mat[i][nk_nn].strip() == nn.strip():
                    if nk_diametr_inscribe_c_okruj != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'Диаметр вписанной окружности, мм')] = spis_mat[i][nk_diametr_inscribe_c_okruj]
                    if nk_dlina_shestigrannicka != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'Длина шестигранника, мм')] = spis_mat[i][nk_dlina_shestigrannicka]
                    if nk_plotn != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'р -плотность(г/см2)')] = spis_mat[i][nk_plotn]
                    break
    CQT.fill_wtabl_old_c(self, spis, tbl, set_editeble_col_nomera=set_edit, separ='', isp_hat_c=True)

def mat_kv_load(self):
    tbl = self.ui.tbl_resch_mater
    CQT.clear_tbl(tbl)
    spis = [['s-площадь поперечного сечения', 'Длина квадрата, мм', 'Длина загот., мм', "р -плотность(г/см2)"]]
    spis.append(['' for _ in spis[0]])
    set_edit = {_ for _ in range(len(spis[0]))}
    tbln = self.ui.tableW_oper_mat
    if tbln.currentRow() != -1:
        if tbln.item(tbln.currentRow(), CQT.num_col_by_name_c(tbln, 'Код')) == None:
            return
        nn = tbln.item(tbln.currentRow(), CQT.num_col_by_name_c(tbln, 'Код')).text()
        spis_mat = zag_param_mat(self, nn)
        if spis_mat != None and len(spis_mat) == 2:
            vid = spis_mat[-1][F.num_col_by_name_in_hat_c(spis_mat, 'Вид')]
            nk_nn = F.num_col_by_name_in_hat_c(spis_mat, 'Код')
            nk_S_plosch_sechen = num_col_by_name_in_hat_c_bdmat(spis_mat, 's-площадь поперечного сечения', vid)
            nk_dlina_kvadrata = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Длина квадрата', vid)
            nk_plotn = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Плотность', vid)

            for i in range(1, len(spis_mat)):
                if spis_mat[i][nk_nn].strip() == nn.strip():
                    if nk_S_plosch_sechen != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 's-площадь поперечного сечения')] = spis_mat[i][nk_S_plosch_sechen]
                    if nk_dlina_kvadrata != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'Длина квадрата, мм')] = spis_mat[i][nk_dlina_kvadrata]
                    if nk_plotn != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'р -плотность(г/см2)')] = spis_mat[i][nk_plotn]
                    break
    CQT.fill_wtabl_old_c(self, spis, tbl, set_editeble_col_nomera=set_edit, separ='', isp_hat_c=True)

def mat_truba_kv_load(self):
    tbl = self.ui.tbl_resch_mater
    CQT.clear_tbl(tbl)
    spis = [['Толщина, мм', 'Высота, мм', 'Ширина, мм', 'Длина загот., мм', 'Длина трубы, мм', "р -плотность(г/см2)"]]
    spis.append(['' for _ in spis[0]])
    set_edit = {_ for _ in range(len(spis[0]))}
    tbln = self.ui.tableW_oper_mat
    if tbln.currentRow() != -1:
        if tbln.item(tbln.currentRow(), CQT.num_col_by_name_c(tbln, 'Код')) == None:
            return
        nn = tbln.item(tbln.currentRow(), CQT.num_col_by_name_c(tbln, 'Код')).text()
        spis_mat = zag_param_mat(self, nn)
        if spis_mat != None and len(spis_mat) == 2:
            vid = spis_mat[-1][F.num_col_by_name_in_hat_c(spis_mat, 'Вид')]
            nk_nn = F.num_col_by_name_in_hat_c(spis_mat, 'Код')
            nk_tolschina = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Толщина', vid)
            nk_visota = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Высота', vid)
            nk_shirina = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Ширина', vid)
            nk_dlina_kvadr_trub = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Длина трубы', vid)
            nk_plotn = num_col_by_name_in_hat_c_bdmat(spis_mat, 'Плотность', vid)
            for i in range(1, len(spis_mat)):
                if spis_mat[i][nk_nn].strip() == nn.strip():
                    if nk_tolschina != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'Толщина, мм')] = spis_mat[i][nk_tolschina]
                    if nk_visota != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'Высота, мм')] = spis_mat[i][nk_visota]
                    if nk_shirina != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'Ширина, мм')] = spis_mat[i][nk_shirina]
                    if nk_dlina_kvadr_trub != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'Длина трубы, мм')] = spis_mat[i][nk_dlina_kvadr_trub]
                    if nk_plotn != None:
                        spis[1][F.num_col_by_name_in_hat_c(spis, 'р -плотность(г/см2)')] = spis_mat[i][nk_plotn]
                    break
    CQT.fill_wtabl_old_c(self, spis, tbl, set_editeble_col_nomera=set_edit, separ='', isp_hat_c=True)

def zag_param_mat(self, nn):
    query = f'''
                SELECT * FROM nomen WHERE Код = "{nn.strip()}"'''
    return CSQ.custom_request_c(self.db_mater ,query)
