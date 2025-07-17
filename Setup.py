
from project_cust_38 import Cust_SQLite as CSQ
from project_cust_38 import Cust_config as CFG
from project_cust_38 import Cust_Functions as F

# result = CSQ.custom_request_c(
#     CFG.Config.project.db_kplan,
#     """
#         SELECT
#             Пномер,
#             Имя,
#             Лазерная_резка as etap_Лазерная_резка,
#             Сборка_сварка as etap_Сборка_сварка,
#             Покраска as etap_Покраска,
#             Токарка_фрезеровка as etap_Токарка_фрезеровка,
#             Зачистка as etap_Зачистка,
#             Вспомогательная as etap_Вспомогательная,
#             Термическая as etap_Термическая,
#             Подготовка_монтажного_комплекта as etap_Подготовка_монтажного_комплекта,
#             Упаковка_и_комплектование_ЗИП as etap_Упаковка_и_комплектование_ЗИП
#         FROM виды_по_напр
#     """,
#     rez_dict=True
# )
# for vid_napr in result:
#     name = vid_napr['Имя']
#     pk = vid_napr['Пномер']
#     if pk == 1:
#         continue
#     for key, val in vid_napr.items():
#         if key.startswith('etap_'):
#             clean_etap = key.strip('etap_')
#             resp = CSQ.custom_request_c(CFG.Config.project.db_naryad,
#                                  """
#                                     INSERT INTO коэфф_норм_видов_направлений_по_этапам(etap_id, виды_по_напр_id, ratio, etap_desc)
#                                  VALUES(?, ?, ?, ?)""",
#                                  list_of_lists_c=[['', pk, val, clean_etap]])
#             print()
#
# print()
poki = 0
query = f"""
        SELECT
            виды_по_напр.Пномер as "Пномер",
            виды_по_напр.Имя as "Имя",
            виды_по_напр.Примечание as "Примечание",
            виды_по_напр.Выборка as "Выборка",
            виды_по_напр.кг_на_пост_см as "кг_на_пост_см",
            виды_по_напр.vneplan_percent as "vneplan_percent",
            виды_по_напр.Утверждены_нормы as "Утверждены_нормы",
            виды_по_напр.ВозможностьСозданияНоменМеталоармДляСозданияРесЕРП as "ВозможностьСозданияНоменМеталоармДляСозданияРесЕРП",
            napravl_deyat.Имя as "napravl_deyat.Имя",
            napravl_deyat.Псевдоним as "napravl_deyat.Псевдоним",
            коэфф.ratio as "коэфф.ratio",
            etaps.имя_в_виды_по_напр as "etaps.имя_в_виды_по_напр"
        FROM виды_по_напр
         LEFT JOIN коэфф_норм_видов_направлений_по_этапам коэфф ON коэфф.виды_по_напр_id = виды_по_напр.Пномер
         LEFT JOIN etaps ON etaps.s_num = коэфф.etap_id
        INNER JOIN napravl_deyat ON виды_по_напр.Направл = napravl_deyat.Пномер
        WHERE napravl_deyat.poki = {poki}
"""
db_result = CSQ.custom_request_c(CFG.Config.project.db_naryad,
                              query, rez_dict=True, attach_dbs=CFG.Config.project.db_kplan)

def group_by(collection, key: str):
    groups = {}
    for item in collection:
        groups.setdefault(item[key], []).append(item)
    return groups

def unpack_groups_on_column(grouped_collection: dict[int, list], column_key: str, value_key: str):
    result = []
    for group_key, group in grouped_collection.items():
        item = {'Пномер': group_key}
        for el in group:
            key_for_result = el.pop(column_key)
            val_for_result = el.pop(value_key)
            if key_for_result is not None and val_for_result is not None:
                item[key_for_result] = val_for_result


            for key, val in el.items():
                if key != column_key and key != value_key:
                    item[key] = val
        result.append(item)
    return result



grouped_types = group_by(db_result, 'виды_по_напр.Пномер')
result = unpack_groups_on_column(grouped_types, 'etaps.имя_в_виды_по_напр', value_key="коэфф.ratio")

print(grouped_types)