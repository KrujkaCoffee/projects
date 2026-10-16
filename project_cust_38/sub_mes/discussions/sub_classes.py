from project_cust_38 import Cust_config
from project_cust_38 import Cust_SQLite as CSQ
from project_cust_38 import Cust_mes as CMS
from project_cust_38 import Cust_Qt as CQT
from project_cust_38 import Cust_Functions as F
import project_cust_38.Cust_b24 as CB24
from datetime import datetime as DT, timezone
from project_cust_38.user_cache import UserCache as USR_CACHE
from project_cust_38.Cust_tree_widget import ExtTreeWidgetItem, BaseTreeWidget
CFG = Cust_config.Config

class _ImportDb():

    def parce_row_dict(self, item: dict, silent: bool = False,declared_only:bool = False):
        attrs = F.get_all_attrs_with_properties(self, include_private=True)
        for key, val in item.items():
            fix_key = str(key).replace(".", "_")
            if fix_key not in attrs:
                if declared_only:
                    continue
                if not silent:
                    print(f'class {self.__class__.__name__} ImportDbRow attr not declared :{fix_key}')

            exec(f'self.{fix_key} = val')

    def __repr__(self):
        return (f"{', '.join([f'"{k}" : {v if F.is_numeric(v) else f'"{v}"'}' for k, v in self.__dict__.items()])}")


class DiscussionMessage(_ImportDb):
    def __init__(self, row:dict):
        self.id: int|None = None
        self.thread_id: int|None = None
        self.parent_id: int|None = None
        self.author: str|None = None
        self.body: str|None = None
        self.created_at: datetime|None = None
        self.edited_at: NoneType|None = None
        self.is_deleted: bool|None = None

        self.parce_row_dict(row)

class UserTreadsCache(USR_CACHE):
    def __init__(self):
        super().__init__()
        self.discussion_threads_cache:dict = dict()
        self.load()

    def _get_tread_date(self,id:int)->None|str:
        if self.discussion_threads_cache:
            if id in self.discussion_threads_cache:
                return self.discussion_threads_cache[id]

    def is_unread(self,id:int,last_msg_date:DT):
        date_user_cahce = self._get_tread_date(id)
        if date_user_cahce is None:
            date_user_cahce = "0001-01-01 00:00:00"
        if F.strtodate(date_user_cahce) < self.as_naive_utc(last_msg_date):
            return True
        return False

    @staticmethod
    def as_naive_utc(dt):
        if dt is None: return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=MSK)
        return dt.astimezone(timezone.utc).replace(tzinfo=None)

    def set_read(self,id_tread):
        self.discussion_threads_cache[id_tread] = F.now()
        self.save()



class Discussion(_ImportDb):
    SCHEMA = 'discusess'
    DB_THREADS = 'discussion_threads'
    DB_MSGS = 'discussion_messages'

    def __init__(self,
                app_name:str,
                tbl_name:str,
                id_row:str,
                title:str,
                ui_row:str
                 ):

        self.app_name:str =app_name
        self.tbl_name:str =tbl_name
        self.id_row:str =id_row
        self.title: str | None = title
        self.ui_row: str | None = ui_row

        self.id: int | None = None
        self.fl_new:bool = False
        self.created_at = None
        self.created_by: str | None = None
        self.is_resolved: bool | None = None
        self.is_locked: bool | None = None
        self.messages_count: int | None = None
        self.last_message_at = None
        self.unread_count: int | None = None

        self.data_msgs:list[dict] = []
        self.dict_messages:dict[DiscussionMessage]=dict()

    @property
    def ui_title(self):
        app_name = ''
        try:
            parent_app = CFG.window_manager.active.parent.window
            app_name = 'Приложение: ' + getattr(parent_app, 'NAME_MODULE_BASE','') + ' -> '
        except:
            print('Ошибка получения имени родительского окна приложения')

        return f'{app_name} {self.title} <<объект(строка) {self.ui_row}>>'

    @property
    def db_threads(self) -> str:
        return f'{self.SCHEMA}.{self.DB_THREADS}'

    @property
    def db_msgs(self) -> str:
        return f'{self.SCHEMA}.{self.DB_MSGS}'

    def load(self) -> "Discussion":
        """Загрузить тред и его сообщения. Если треда нет — id остаётся None."""
        data = CSQ.custom_request_pg(
            f"""SELECT * FROM {self.db_threads}
                 WHERE app_name = %s AND tbl_name = %s AND id_row = %s""",
            list_of_lists_c=[self.app_name, self.tbl_name, self.id_row],
            one=True,
        )
        if data:
            self.parce_row_dict(data)
        if self.id is not None:
            self._load_msgs()

        user_treads_cashe = UserTreadsCache()
        user_treads_cashe.set_read(self.id)

        return self

    def _load_msgs(self):
        self.data_msgs = CSQ.custom_request_pg(
            f"""SELECT * FROM {self.db_msgs}
                        WHERE thread_id = %s
                        ORDER BY created_at, id""",
            list_of_lists_c=[self.id],
        ) or []
        self.dict_messages = {}
        for msg in self.data_msgs:
            msg_o = DiscussionMessage(msg)
            self.dict_messages[msg_o.id] = msg_o

    def get_message_o(self,id:int)->DiscussionMessage|None:
        if id in self.dict_messages:
            return self.dict_messages[id]


    def create_if_missing(self, created_by: str | None = None) -> int | None:
        """Создать тред, если его ещё нет. Вернуть id треда."""
        if self.id is not None:
            return self.id

        row = CSQ.custom_request_pg(
            f"""INSERT INTO {self.db_threads} (app_name, tbl_name, id_row, created_by, title, ui_row)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *""",
            list_of_lists_c=[self.app_name, self.tbl_name, self.id_row,
                             created_by or self.created_by, self.title, self.ui_row],
            one=True,
        )
        if row:
            self.parce_row_dict(row)
            self.fl_new = True
        return self.id

    def refresh(self) -> "Discussion":
        """Перечитать и тред, и сообщения."""
        return self.load()

    def add_message(self,
                    body: str,
                    author: str,
                    parent_id: int | None = None) -> int | None:
        if self.id is None:
            self.create_if_missing(created_by=author)

        if self.id is None:
            return None

        row = CSQ.custom_request_pg(
            f"""INSERT INTO {self.db_msgs} (thread_id, parent_id, author, body)
                VALUES (%s, %s, %s, %s)
                RETURNING *""",
            list_of_lists_c=[self.id, parent_id, author, body],
            one=True,
        )
        if not row:
            return None

        # обновляем счётчики треда
        CSQ.custom_request_pg(
            f"""UPDATE {self.db_threads}
                      SET messages_count  = messages_count + 1,
                          last_message_at = %s
                    WHERE id = %s""",
            list_of_lists_c=[row['created_at'], self.id],
        )


        self.data_msgs.append(row)
        return row['id']

    # --- связка с деревом ----------------------------------------------
    @staticmethod
    def parent_id_from_tree(tree) -> int | None:
        """id выделенного сообщения как родителя.
        Синтетический корень / пусто / мусор -> None (создаём корневое сообщение)."""
        item = tree.currentItem()
        if item is None:
            return None

        sys_fields = item.system_fields or {}
        if sys_fields.get('is_synthetic_root'):
            return None

        val = item.uuid
        if not val or val == DiscussionTreeFiller.SYNTHETIC_UUID:
            return None
        try:
            return int(val)
        except (TypeError, ValueError):
            return None


    def reply_to_selected(self, tree, body: str, author: str,
                          select_new: bool = True) -> int | None:
        """Ответить на выделенное сообщение.
        Если ничего не выделено — создастся корневое.
        После вставки перечитывает и перерисовывает дерево."""

        parent_id = self.parent_id_from_tree(tree)
        new_id = self.add_message(body=body, author=author, parent_id=parent_id)
        self.refresh()
        self.fill_tree(tree)

        if select_new and new_id is not None:
            item = self._find_item_by_uuid(tree, str(new_id))
            if item is not None:
                self._expand_to_item(tree, item)

        return new_id

    # --- отрисовка ------------------------------------------------------
    def fill_tree(self, tree, focus_last: bool = True):
        DiscussionTreeFiller(tree=tree).fill(self.data_msgs)
        if focus_last and self.data_msgs:
            self._focus_last_message(tree)

    def _focus_last_message(self, tree):
        """Найти самое свежее сообщение и раскрыть путь до него."""
        # если в data_msgs есть ключ created_at — сортируем по нему,
        # иначе по id (id автоинкрементный, что то же самое по смыслу)
        last = max(
            self.data_msgs,
            key=lambda m: (m.get('created_at') or '', m.get('id') or 0)
        )
        item = self._find_item_by_uuid(tree, str(last['id']))
        if item is not None:
            self._expand_to_item(tree, item)

    @staticmethod
    def _find_item_by_uuid(tree, uuid_str: str):
        """Найти ExtTreeWidgetItem по uuid. Возвращает item или None."""

        def walk(item):
            if item.uuid == uuid_str:
                return item
            for i in range(item.childCount()):
                found = walk(item.child(i))
                if found is not None:
                    return found
            return None

        for i in range(tree.topLevelItemCount()):
            found = walk(tree.topLevelItem(i))
            if found is not None:
                return found
        return None

    @staticmethod
    def _expand_to_item(tree, item):
        """Раскрыть всех предков item, проскроллить и выделить."""
        parent = item.parent()
        while parent is not None:
            parent.setExpanded(True)
            parent = parent.parent()
        tree.scrollToItem(item)
        tree.setCurrentItem(item)
        item.setSelected(True)


    @classmethod
    def is_unread_msges(cls,id_tread:int, last_msg_date: DT) -> bool:
        user_treads_cashe =  UserTreadsCache()
        return user_treads_cashe.is_unread(id_tread,last_msg_date)


    @classmethod
    def has_discussion(cls, app_name: str, tbl_name: str, id_row) -> dict|DT:
        """Быстрая проверка: есть ли в треде хоть одно живое сообщение.
        Не создаёт тред, не грузит сообщения."""
        row = CSQ.custom_request_pg(
            f"""
            SELECT id, last_message_at 
              FROM {cls.SCHEMA}.{cls.DB_THREADS} t
             WHERE t.app_name = %s
               AND t.tbl_name = %s
               AND t.id_row   = %s
               AND t.messages_count > 0
             LIMIT 1
            """,
            list_of_lists_c=[app_name, tbl_name, str(id_row)],
            one=True,
        )
        return row if row else False

class DiscussionTreeFiller:
    ID = 'id'
    PARENT_ID = 'parent_id'
    AUTHOR = 'author'
    BODY = 'body'
    CREATED = 'created_at'
    DELETED = 'is_deleted'

    SYNTHETIC_UUID = '__root__'
    ROOT_LABEL = '<<⚙️ Объект из таблицы >>'      # эмодзи + подпись

    def __init__(self, tree):
        self.tree = tree

    def _fmt_date(self, val) -> str:
        if val is None:
            return ''
        if hasattr(val, 'strftime'):
            return val.strftime('%d.%m.%Y %H:%M')
        return str(val)

    def _make_text(self, data: dict) -> str:
        if data.get(self.DELETED):
            return '[удалено]'
        author = data.get(self.AUTHOR) or '—'
        date = self._fmt_date(data.get(self.CREATED))
        body = (data.get(self.BODY) or '').strip()
        head = f'{author}  •  {date}' if date else author
        return f'{head}\n{body}' if body else head

    def fill(self, messages: list[dict]) -> None:
        self.tree.clear()

        # --- синтетический корень ---
        root_item = ExtTreeWidgetItem(
            texts=[self.ROOT_LABEL],
            level=0,
            object_uuid=self.SYNTHETIC_UUID,
            system_data={'is_synthetic_root': True, 'id': None, 'parent_id': None},
        )

        self.tree.addTopLevelItem(root_item)

        root_item.set_row_style(bold=True, foreground_color='#444444')

        if messages:
            nodes = {m[self.ID]: {'data': m, 'children': []} for m in messages}

            roots = []
            for m in messages:
                pid = m.get(self.PARENT_ID)
                if pid is None or pid not in nodes:
                    roots.append(m[self.ID])
                else:
                    nodes[pid]['children'].append(m[self.ID])

            sort_key = lambda mid: (nodes[mid]['data'].get(self.CREATED), mid)
            for node in nodes.values():
                node['children'].sort(key=sort_key)
            roots.sort(key=sort_key)

            for root_id in roots:
                # уровень 1, потому что уровень 0 теперь у синтетического корня
                self._build_item(root_id, nodes, parent=root_item, level=1)

        root_item.setExpanded(True)

        # выделяем корень по умолчанию — чтобы "просто напечатать и отправить" создало корневое
        self.tree.setCurrentItem(root_item)

    def _build_item(self, mid, nodes, parent, level):
        data = nodes[mid]['data']
        text = self._make_text(data)

        item = ExtTreeWidgetItem(
            texts=[text],
            level=level,
            object_uuid=str(mid),
            system_data={'raw': data, 'id': mid, 'parent_id': data.get(self.PARENT_ID)},
        )

        if parent is None:
            self.tree.addTopLevelItem(item)
        else:
            parent.addChild(item)

        if data.get(self.DELETED):
            item.set_row_style(foreground_color='#888888', italic=True)
        elif data.get('is_unread'):
            item.set_row_style(bold=True)

        for child_id in nodes[mid]['children']:
            self._build_item(child_id, nodes, parent=item, level=level + 1)

class SubscriptionRepo:
    SCHEMA = 'discusess'
    DB_SUBSCRIPTIONS = 'discussion_user_thread_subscriptions'
    DB_MSGS = 'discussion_messages'
    def __init__(self, thread:Discussion):
        self.thread_o: Discussion = thread
        self.phys_person_uuid = CFG.user_config.User.ID_ФизЛица
        self.send_msg_o:DiscussionMessage|None = None
    @property
    def db_msgs(self) -> str:
        return f'{self.SCHEMA}.{self.DB_MSGS}'
    # оповещение о новых сообщениях
    # ─── сюда подставь свою инфраструктуру ──────────────────────────

    def _build_notification_payload(self):
        """Сформировать данные для уведомления: заголовок треда, превью, ссылка."""
        # у тебя тут, скорее всего, SELECT по threads/messages
        self._base_msg = f'Новое сообщение МЕС, в треде "{self.thread_o.ui_title}"'
        data_msg = CSQ.custom_request_pg(
            f"""SELECT * FROM {self.db_msgs}
                        WHERE id = %s 
                        """,
            one=True,
            list_of_lists_c=[self.send_msg_o.id])
        date_str = F.datetostr(data_msg['created_at'],"%H:%M %d.%m.%Y")

        self._msg = f"""{date_str} - {data_msg['author']}:\n\n...\n{data_msg['body']}"""


    def _send_notification(self, id_chat_str):
        template = CB24.MessageBuilder(self._base_msg)  # Инициализация (базовое сообщение)
        template.add_message(self._msg)  # Добавить сообщение
        template.send_by_chat_id(id_chat_str)  # Итоговая отправка


    def _log_send_failure(self, id_chat_str):
        CMS.send_err_msg_dev_chat('Ошибка отправки сообщения threads',
                                  [
                                      {'k': 'user_uuid_b24', 'v': id_chat_str},
                                      {'k': 'base_msg', 'v': self._base_msg},
                                      {'k': 'msg', 'v': self._msg},
                                      {'k': 'ref_user', 'v': CFG.user_config.User.ID_ФизЛица},

                                  ])

    def on_new_message(self,msg_o:DiscussionMessage|int):
        """
          Точка входа при появлении нового сообщения в треде.
          Вызывается ПОСЛЕ успешного COMMIT записи сообщения.

          :param db:          соединение/сессия
          :param thread_id:   в каком треде сообщение
          :param message_id:  id сохранённого сообщения
          :param author_uuid: кто написал — ему уведомление не шлём
          """
        if isinstance(msg_o, int):
            msg_o = self.thread_o.get_message_o(msg_o)

        self.send_msg_o = msg_o
        # 1. Кто подписан на этот тред
        subscribers = self.subscribers()

        # 2. Собираем полезную нагрузку один раз (заголовок, ссылка, превью)
        self._build_notification_payload()
        subscribers_chats = self._get_subscribers_chats(subscribers)
        # 3. Рассылка
        for ref_user, id_chat_str in subscribers_chats.items():
            if ref_user == CFG.user_config.User.ID_ФизЛица:
                continue  # не спамим автора
            try:
                self._send_notification(id_chat_str)
            except Exception as e:
                # ОДИН упавший получатель не должен валить всю рассылку
                self._log_send_failure(id_chat_str)

    # ─────────────────────────── чтение ───────────────────────────

    def is_subscribed(self) -> bool:
        if self.thread_o.id is None:
            return False
        row = CSQ.custom_request_pg(
            f"""
            SELECT 1
              FROM {self.SCHEMA}.{self.DB_SUBSCRIPTIONS}
             WHERE thread_id = %s
               AND phys_person_uuid = %s
             LIMIT 1
            """,
            list_of_lists_c=[self.thread_o.id, self.phys_person_uuid],
            one=True
        )
        return len(row)

    def _get_subscribers_chats(self,subscrabers: list[str]) -> dict[str]:
        data = F.deploy_dict_c(CSQ.custom_request_c(CFG.project.db_users,
                                    f"""SELECT ФизическоеЛицо_Key,id_bitrix FROM ФизическиеЛица WHERE 
ФизическоеЛицо_Key IN ({CSQ.prepare_list_to_tuple(subscrabers)})""",rez_dict=True),'ФизическоеЛицо_Key')
        return data


    def subscribers(self) -> list[str]:
        if self.thread_o.id is None:
            return []
        """Все uuid, подписанные на тред."""
        rows = CSQ.custom_request_pg(
            f"""
            SELECT phys_person_uuid
              FROM {self.SCHEMA}.{self.DB_SUBSCRIPTIONS}
             WHERE thread_id = %s
            """,
            list_of_lists_c=[self.thread_o.id],
        )

        return [_['phys_person_uuid'] for _ in rows] if rows else []

    def count(self) -> int:
        if self.thread_o.id is None:
            return 0
        row = CSQ.custom_request_pg(
            f"""
            SELECT COUNT(*) AS cnt
              FROM {self.SCHEMA}.{self.DB_SUBSCRIPTIONS}
             WHERE thread_id = %s
            """,
            list_of_lists_c=[self.thread_o.id],
            one=True,
        )
        return int(row[0]) if row else 0

    # ─────────────────────────── запись ───────────────────────────

    def subscribe(self) -> bool:
        if self.thread_o.id is None:
            return False
        """Идемпотентно: повторный вызов не падает и не дублирует."""
        CSQ.custom_request_pg(
            f"""
            INSERT INTO {self.SCHEMA}.{self.DB_SUBSCRIPTIONS}
                        (phys_person_uuid, thread_id)
                 VALUES (%s, %s)
            ON CONFLICT (phys_person_uuid, thread_id) DO NOTHING
            """,
            list_of_lists_c=[self.phys_person_uuid, self.thread_o.id],
        )
        return True

    def unsubscribe(self) -> bool:
        if self.thread_o.id is None:
            return True
        CSQ.custom_request_pg(
            f"""
            DELETE FROM {self.SCHEMA}.{self.DB_SUBSCRIPTIONS}
             WHERE phys_person_uuid = %s
               AND thread_id = %s
            """,
            list_of_lists_c=[self.phys_person_uuid, self.thread_o.id],
        )
        return True

    def toggle(self) -> bool:
        """
        Удобно для кнопки: одна операция вместо двух.
        Возвращает новое состояние (True = подписан).
        """

        if self.is_subscribed():
            self.unsubscribe()
            return False
        self.subscribe()
        return True