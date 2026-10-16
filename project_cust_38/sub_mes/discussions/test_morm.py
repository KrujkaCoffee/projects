
if __name__ == "__main__":
    from Cust_pre_config import reg_env_db_users
    reg_env_db_users()

import Cust_config as CFG
import project_cust_38.Cust_SQLite as CSQ
#================Обновление схемы================
from morm import update_schema_registry as MORM_UPD
#MORM_UPD.main(schema='discusess',apply=True)
#==================Генерация моделей================
from morm import generate as MORM_GEN
if True:
    MORM_GEN.main(schema='discusess',
                  with_repository_overrides=False)
    #===========================================================

from morm.reference_data_generated_container import ReferenceData


from morm.reference_data_generated_models import DiscussionMessagesMeta as META_DiscussionMessages
discussion_messages_columns_o = META_DiscussionMessages.COLUMNS_O


reference = ReferenceData(CSQ)   # CSQ — модуль с pg_request И pg_session (нужен для save_dirty())
# reference.naryad — репозиторий, уже с вашими my_repositories.py методами
from morm.reference_data_generated_models import DiscussionMessages

repo = reference.discussion_messages

# --- Загрузка ---
repo.load()                       # полный SELECT * (перезаписывает кэш)
repo.reload()                     # синоним load()
repo.partial_load(
    [discussion_messages_columns_o.created_at,
     discussion_messages_columns_o.author])  # SELECT только PK + autor; остальные поля NOT_LOADED
repo.ensure_full(repo[2])        # если объект НЕ is_full() — догружает недостающие поля (merge_row); иначе no-op
repo.refetch(repo[3], force=False)     # ВСЕГДА идёт в БД, полностью перезаписывает объект (refresh_from_row).
                                   # ValueError если is_dirty() и не передан force=True.
                                   # KeyError если строку удалили из БД.
"""
# --- Доступ ---
repo[5]                           # obj по PK (для составного PK — tuple: repo[(order_id, line_no)])
len(repo)
list(repo)                        # список PK
repo.all()                        # dict {pk: obj} — копия текущего кэша
repo.find(autor='fedor')          # list[obj] — простой фильтр по точному совпадению полей
repo.group_by('autor', mode=GroupByMode.LAST)   # dict {значение_ключа: obj}; режимы STRICT/FIRST/LAST/LIST

# --- Запись ---
obj = repo[5]
obj.quest = 'новое значение'      # обычное присвоение — само пометит поле dirty
repo.save_dirty()                 # -> int, сколько объектов сохранено.
                                   # ОДНА транзакция на всю "грязную" пачку (через pg_session):
                                   # либо ВСЕ сохраняются, либо (при сбое) НИ ОДИН.
                                   # PermissionError, если READONLY=True.

new_obj = Naryad(autor='test')
repo.insert(new_obj)              # validate() -> insert_values() -> INSERT RETURNING * -> refresh_from_row()
                                   # PK (в т.ч. составной, как tuple) сразу доступен: repo[new_obj.s_num] is new_obj

repo.invalidate()                 # сбросить кэш — следующее обращение снова пойдёт в БД
"""