from project_cust_38 import Cust_config
from project_cust_38 import Cust_SQLite as CSQ
from project_cust_38 import Cust_mes as CMS
from project_cust_38 import Cust_Qt as CQT
from project_cust_38 import Cust_Functions as F
from project_cust_38.Cust_tree_widget import ExtTreeWidgetItem, BaseTreeWidget
CFG = Cust_config.Config

class _ImportDb():

    def parce_row_dict(self, item: dict):
        attrs = F.get_all_attrs_with_properties(self, include_private=True)
        for key, val in item.items():
            fix_key = str(key).replace(".", "_")
            if fix_key not in attrs:
                print(f'class {self.__class__.__name__} ImportDbRow attr not declared :{fix_key}')
            exec(f'self.{fix_key} = val')

    def __repr__(self):
        return (f"{', '.join([f'"{k}" : {v if F.is_numeric(v) else f'"{v}"'}' for k, v in self.__dict__.items()])}")



class Discussion(_ImportDb):
    SCHEMA = 'discusess'
    DB_THREADS = 'discussion_threads'
    DB_MSGS = 'discussion_messages'
    def __init__(self,
                app_name:str,
                tbl_name:str,
                id_row:str,

                 ):

        self.app_name:str =app_name
        self.tbl_name:str =tbl_name
        self.id_row:str =id_row

        self.id: int | None = None
        self.title: str | None = None
        self.created_at = None
        self.created_by: str | None = None
        self.is_resolved: bool | None = None
        self.is_locked: bool | None = None
        self.messages_count: int | None = None
        self.last_message_at = None
        self.unread_count: int | None = None

        self.data_msgs:list[dict] = []


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
        return self

    def _load_msgs(self):
        self.data_msgs = CSQ.custom_request_pg(
            f"""SELECT * FROM {self.db_msgs}
                        WHERE thread_id = %s
                        ORDER BY created_at, id""",
            list_of_lists_c=[self.id],
        ) or []

    def create_if_missing(self, created_by: str | None = None) -> int | None:
        """Создать тред, если его ещё нет. Вернуть id треда."""
        if self.id is not None:
            return self.id

        row = CSQ.custom_request_pg(
            f"""INSERT INTO {self.db_threads} (app_name, tbl_name, id_row, created_by)
                VALUES (%s, %s, %s, %s)
                RETURNING *""",
            list_of_lists_c=[self.app_name, self.tbl_name, self.id_row,
                             created_by or self.created_by],
            one=True,
        )
        if row:
            self.parce_row_dict(row)
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
    def has_discussion(cls, app_name: str, tbl_name: str, id_row) -> bool:
        """Быстрая проверка: есть ли в треде хоть одно живое сообщение.
        Не создаёт тред, не грузит сообщения."""
        row = CSQ.custom_request_pg(
            f"""
            SELECT 1
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
        return bool(row)

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



