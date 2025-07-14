from project_cust_38 import Cust_Qt as CQT
from project_cust_38 import Cust_SQLite as CSQ
from project_cust_38 import Cust_config as CFG
from project_cust_38 import Cust_Functions as F


def update_type_dse_validate_msg(*args, **kwargs):
    if CQT.msgboxgYN('Выбранный вид будет применен к полю пл_топ.Вид. Продолжить?'):
        ...

@CQT.onerror
def btn(self, nom_kpl = 5574, *args, **kwargs):
    query_type = """SELECT Пномер, Имя as Вид, НомерВидаНоменДляСозданияРесЕРП FROM виды_по_напр WHERE Имя != ''"""
    dse_types: list[dict] = CSQ.custom_request_c(CFG.Config.project.db_kplan, query_type, rez_dict=True)
    if dse_types == False:
        return CQT.msgbox('Не удалось запросить виды по направлениям')
    query_nomen_types = f'SELECT CAST(s_num AS TEXT) as s_num, name FROM ВидыНоменклатуры'
    nomen_types = CSQ.custom_request_c(self.bd_nomen, query_nomen_types, rez_dict=True)

    types_nomen_by_pk: dict[str, str] = F.deploy_dict_c(nomen_types, 's_num')
    if nomen_types == False:
        return CQT.msgbox('Не удалось запросить номенклатуру для видов')

    for idx in range(len(dse_types)):
        obj_nomen_types = dse_types[idx].pop('НомерВидаНоменДляСозданияРесЕРП')
        split_obj_nomen_types = obj_nomen_types.split(';') if obj_nomen_types else tuple()
        for obj_n_type in split_obj_nomen_types:
            if obj_n_type in types_nomen_by_pk:
                dse_types[idx].setdefault('Связанные виды номенклатуры', list()).append({'': types_nomen_by_pk[obj_n_type]})
    result = CQT.msgboxg_get_table(self, 'Для продолжения выберите пл_топ.Вид', dse_types,
                          show_filtr=False,
                          btn0_name='Применить',
                          ExtendedSelection=False)
    if not isinstance(result, dict) or not 'Пномер' in result:
        return
    selected_type = result['Пномер']
    name = result['Вид']
    if not CQT.msgboxgYN(f'Выбранный вид: {name!r} будет применен к полю пл_топ.Вид. Продолжить?'):
        return
    result = CSQ.custom_request_c(
        CFG.Config.project.db_kplan,
        f'UPDATE пл_топ SET Вид = {selected_type} WHERE НомКплан = {nom_kpl}'
    )
    if result:
        CQT.msgbox('Успешно')
        return True
    return CQT.msgbox('Не удалось обновить пл_топ.Вид')
