import project_cust_38.Cust_tree_widget as CTREE
import project_cust_38.api_erp_commands as APIERP
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_emoji as CEMOJ
import project_cust_38.Cust_config as CFG
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_docs as CDCS
import copy
CFGo = CFG.Config
class AddMode:
    """Режимы добавления строки относительно текущей."""
    SIBLING = "sibling"   # сестра после выбранной (тот же уровень)
    CHILD   = "child"     # дочерняя в конец выбранной (уровень +1)

class CardRevDocs(CMS._ImportDb):
    def __init__(self,item:dict):
        self.uuid_card:str = None
        self.id_card:int = None
        self.rev_file:int = None
        self.date:str = None
        self.ref_user:str = None
        self.user:str = None
        self.comment:str = None

        self.parce_row_dict(item,  False, True)


    def template(self)->dict:
        return F.get_all_attrs(self)

    def __repr__(self):
        return f"CardRevDocs(rev_file={self.rev_file}, date='{self.date}', ref_user='{self.ref_user}', comment='{self.comment}')"

class StuctRowInfo():
    def __init__(self,uuid_card:str,count:int=0):
        self.uuid_card = uuid_card
        self.count = count

    def to_ui(self)->str:
        LIMIT = 5
        count_limited = min(self.count,LIMIT)
        fl_over = self.count > LIMIT
        return  f"""{CEMOJ.ПерсоналРоли.star.symbol*count_limited}{CEMOJ.ДокументыДанные.plus.symbol if fl_over else ''}"""

class CardDocs():
    _db = CFGo.project.db_dse
    def __init__(self,
                 шифрИзделия_card:str,
                 iD_card:str,
                 датаСоздания_card:str,
                 наименование_card:str,
                 номерПозиции_card:str,
                 названиеВарианта_card:str,
                 ссылкаДокс_card:str,
                 uuiD_card:str
                 ):
        self.шифрИзделия_card:str = шифрИзделия_card
        self.iD_card:str = iD_card
        self.датаСоздания_card:str = датаСоздания_card
        self.наименование_card:str = наименование_card
        self.номерПозиции_card:str = номерПозиции_card
        self.названиеВарианта_card:str = названиеВарианта_card
        self.ссылкаДокс_card:str = ссылкаДокс_card
        self.uuiD_card:str = uuiD_card
        self._current_rev:CardRevDocs = None
        self._dict_revs:dict[int,CardRevDocs] = None

    def set_current_rev(self,id_rev:int):
        self._current_rev  = self._dict_revs[id_rev]

    def get_template_versions(self)->tuple[list[str],dict]:
        DICT_ALIASES = {
            'uuid_card':'_uuid_card',
            'id_card':'_№ Карточки',
            'rev_file':'№ рев.',
            'data':'_data',
            'date':'Дата',
            'ref_user':'_ref_user',
            'user':'ФИO',
            'comment':'Примечание',
        }

        return [_.template() for _ in self._dict_revs.values()], DICT_ALIASES

    def get_list_versions(self):
        list_files = CSQ.custom_request_c(self._db, f"""SELECT 
                uuid_card,
                id_card,
                 rev_file, 
                    date, 
                    ref_user, 
                    ФизическиеЛица.Наименование as user,
                    comment 
                 FROM rkd_cards_constr_rs
                  INNER JOIN ФизическиеЛица ON ФизическиеЛица.ФизическоеЛицо_Key = rkd_cards_constr_rs.ref_user
                  WHERE 
                            uuid_card = '{self.uuiD_card}';""", rez_dict=True,attach_dbs=CFGo.project.db_users)
        self._dict_revs = dict()
        for it in list_files:
            rev_o = CardRevDocs(it)
            self._dict_revs[rev_o.rev_file] = rev_o

    def new_rev_id(self):
        if self._dict_revs is None:
            raise ValueError(f"Не загружены ревизии")
        max_id = max(self._dict_revs.keys()) if self._dict_revs else -1
        return max_id + 1

    def save_structure(self, data: dict, ref_user: str, comment: str = "") -> bool:
        uuid_card = self.uuiD_card

        new_id_rev = self.new_rev_id()
        tmp_data = [uuid_card, self.iD_card, new_id_rev, F.to_binary_pickle(data), F.now(), ref_user, comment]
        rez = CSQ.custom_request_c(self._db, f"""INSERT INTO rkd_cards_constr_rs 
         (uuid_card,id_card,rev_file,data,date,ref_user,comment) VALUES ({CSQ.questions_for_mask(tmp_data)});""",
                                   list_of_lists_c=[tmp_data])
        if rez:
            self.get_list_versions()
            self.set_current_rev(new_id_rev)
        return rez

    def get_structure(self) -> dict():
        uuid_card = self.uuiD_card
        if self._current_rev is None:
            raise Exception("Не задан номер ревизии")
        rez = CSQ.custom_request_c(self._db, f"""SELECT data FROM rkd_cards_constr_rs 
          WHERE  uuid_card = ? and rev_file = ?;""", list_of_lists_c=[[uuid_card, self._current_rev.rev_file]], rez_dict=True, one=True)
        if not rez:
            return rez
        return F.from_binary_pickle(rez['data'])




    def __repr__(self):
        return (f"CardDocs(шифр='{self.шифрИзделия_card}', "
                f"ID='{self.iD_card}', "
                f"наименование='{self.наименование_card}', "
                f"позиция='{self.номерПозиции_card}', "
                f"вариант='{self.названиеВарианта_card}')")

    def __str__(self):
        rev_str = ''
        if self._current_rev:
            rev_str = f"- рев. {self._current_rev.rev_file}"
        return (f"№{self.iD_card} {self.наименование_card} поз. {self.номерПозиции_card}{rev_str}")

class OrdersDocs:
    def __init__(self,):
        self.DICT_ALIASES = {
            "structures": "Структуры",
            "шифрИзделия_card": "Шифр\nкарточки",
            "iD_card": "№\nкарточки",
            "датаСоздания_card": "Дата создания\nкарточки",
            "наименование_card": "Наименование\nкарточки",
            "номерПозиции_card": "Позиция\nкарточки",
            "названиеВарианта_card": "Вариант\nкарточки",
            "ссылкаДокс_card": "Ссылка\nкарточки",


            "наименование_папки_proc": "Папка\nпроцесса",
            "iD_proc": "№\nпроцесса",
            "статус_proc": "Статус\nпроцесса",
            "схема_proc": "Схема\nпроцесса",
            "датаЗапуска_proc": "Дата запуска\nпроцесса",
            "ответственный_proc": "Ответственный\nпроцесса",
            "желаемаяДата_proc": "Желаемая дата\nпроцесса",
            "кодРС_proc": "Код РС\nпроцесса",
            "комментарий_proc": "Комментарий\nпроцесса",
            "наименование_proc": "Наименование\nпроцесса",
            "ссылкаДокс_proc": "Ссылка\nпроцесса",
            "этап_proc": "Этап\nпроцесса",

            "uuiD_card": "_UUID_card",
            "uuiD_proc": "_UUID_proc",
        }
        self.list_orders_docs = []
        self._dict_cards:dict[str,CardDocs] = dict()
        self._list_uuids_folders = ['84c4813d-7c97-4ed9-9216-1e4239ccb4c1','96351661-6c79-40ef-bd98-507458e974ae','b2c7c577-e22d-4ce4-a557-95d6e79c19aa']
        self._db = CFG.Config.project.db_dse
        self.LIMIT_SECS = 300

    def update(self):
        data_cache = CMS.load_tmp_stukt("orders_tatkuz_for_molding", False)
        fl_load_from_srv = True
        if data_cache:
            delta = (F.now('') - F.strtodate(data_cache['date'])).seconds
            if delta < self.LIMIT_SECS:
                fl_load_from_srv = False
        if fl_load_from_srv:  # fl_load_from_srv=True
            with CDCS.TFlexTkpProcessClient() as client:
                # client.get_tkp_folders(CDCS.TFlexHttpClient._GET_ALL_PROCESS_RKD_FOLDERS)
                key, data_process = client.get_process_rkd(
                    folder_uuid_lst=self._list_uuids_folders)  # client.get_tkp_folders()
            if not key == 200:
                CQT.msgbox(f'Ошибка получения данных из DOCs код {key}')
                data_process = data_cache['data']
            else:
                CMS.save_tmp_stukt({"data": data_process, "date": F.now()}, "orders_tatkuz_for_molding")
        else:
            data_process = data_cache['data']
        self.list_orders_docs = []
        #====================data_structures====================
        data_structures = F.deploy_dict_c(CSQ.custom_request_c(self._db, f"""
            SELECT uuid_card, COUNT(uuid_card) as count FROM rkd_cards_constr_rs GROUP BY uuid_card """,rez_dict=True),
                                          'uuid_card',keep_key=True)



        #====================data_structures====================


        for i, item in enumerate(data_process):
            new_item = dict()
            for name, alias in self.DICT_ALIASES.items():
                if name in item._asdict():
                    v = item._asdict()[name]
                    if 'дата' in name.lower():
                        if v:
                            v = F.dateStrToStr(v,"%Y-%m-%dT%H:%M:%S",'%d.%m.%Y %H:%M',v)
                    new_item[name] = v
                else:
                    if name == 'structures':
                        v = item._asdict()['uuiD_card']
                        raw_data = data_structures.get(v, {'count': 0, 'uuid_card': v})
                        stuct_info_o = StuctRowInfo(raw_data['uuid_card'], raw_data['count'])
                        new_item[name] = stuct_info_o.to_ui()

            self.list_orders_docs.append(new_item)
            if new_item['uuiD_card'] not in self._dict_cards:
                card_o = CardDocs(
                    new_item['шифрИзделия_card'],
                    new_item['iD_card'],
                    new_item['датаСоздания_card'],
                    new_item['наименование_card'],
                    new_item['номерПозиции_card'],
                    new_item['названиеВарианта_card'],
                    new_item['ссылкаДокс_card'],
                    new_item['uuiD_card']
                )
                self._dict_cards[card_o.uuiD_card] = card_o
        return

    def get_card(self,uuid_card)->CardDocs:
        card_o = self._dict_cards[uuid_card]
        card_o.get_list_versions()
        return card_o




class SpecSchema:
    """Схема полей спецификации."""
    SCHEMA_VERSION = 1
    AUTOCALC_FIELDS = ['mass_total', 'mass_item']
    USER_EDITABLE_FIELDS = ('designation', 'name', 'mass_one', 'qty', 'area_one', 'area_total', 'weld_std', 'weld_len',
                       'edge_prep', 'material', 'comment')
    REWRITE_FIELDS = ('designation', 'name', 'mass_one', 'qty', 'area_one', 'area_total', 'weld_std', 'weld_len',
                       'edge_prep', 'material', 'comment','_pki','_nomenclature_ref','nomenclature','code_erp')
    AUTOCALC_EMO = CEMOJ.ОперацииПроизводства.calculated.symbol
    base_DICT_ALIASES: dict[str, str] = {
        "pos": "№ п.п",
        "designation": "Обозначение",
        "name": "Наименование",
        "mass_one": "масса\n1 шт",
        "qty": "кол-во",
        "mass_total": f"масса\nобщ.",
        "_qty_on_item": f"_Кол-во\nна вхождение",
        "_qty_on_struct":  "_Кол-во\nна изделие",
        "mass_item": f"Итого на\nизделие, кг",
        "area_one": "S 1 шт,м2",
        "area_total": "S общ,м2",
        "weld_std": "Стандарт,\nтип шва",
        "weld_len": "Длина сварных\n швов, мм",
        "edge_prep": "Разделка\nкромок, мм",
        "material": "Материал\nпо чертежу",
        "nomenclature": "Номенклатура\nпо 1С",
        "code_erp": "Код\nпо 1С",
        "_pki": "_pki",
        "pki_ui": "ПКИ",
        "comment": "Комментарии",
        "_nomenclature_ref": "_nomenclature_ref",
    }
    DICT_ALIASES: dict[str, str] = {}
    for _k, _v in base_DICT_ALIASES.items():
        DICT_ALIASES[_k] = (
            f"{AUTOCALC_EMO} {_v}" if _k in AUTOCALC_FIELDS else _v
        )

    # Обратный индекс: user_text -> pep_name
    USER_TO_PEP: dict[str, str] = {v: k for k, v in DICT_ALIASES.items()}

    # Служебное поле уровня (уйдёт в system_data через префикс "__")
    LEVEL_KEY = "_level"
    UUID_KEY = "_uuid"

    PEP_NAMES: list[str] = list(DICT_ALIASES.keys())
    USER_HEADERS: list[str] = list(DICT_ALIASES.values())

    def __init__(self,tree:CTREE.ExtTreeWidget):
        self.tree:CTREE.ExtTreeWidget = tree
        self._new:bool = True

    @property
    def is_new(self)->bool:
        return self._new

    @classmethod
    def pep_names(cls) -> list[str]:
        return list(cls.DICT_ALIASES.keys())

    @classmethod
    def user_headers(cls) -> list[str]:
        return list(cls.DICT_ALIASES.values())

    @classmethod
    def user_text(cls, pep_name: str) -> str:
        return cls.DICT_ALIASES[pep_name]

    @classmethod
    def pep_name(cls, user_text: str) -> str | None:
        for k, v in cls.DICT_ALIASES.items():
            if v == user_text:
                return k
        return None

    @classmethod
    def empty_row(cls) -> dict[str, object]:
        """Пустая строка-заготовка со всеми pep-ключами."""
        return {p: "" for p in cls.pep_names()}


    def to_tree_rows(self,rows: list[dict]) -> list[dict]:
        """
        pep-строки -> строки для ExtTreeWidget.fill_table:
            * ключи переименованы pep_name -> user_text
            * "pos" выкидываем (нумерация генерируется на лету)
            * "_level" уходит в system_data через префикс "__"
        """
        out = []
        for r in rows:
            new_r = {}
            for k, v in r.items():
                if k == "pos":
                    # колонка есть, значение генерируется на лету
                    new_r[self.DICT_ALIASES["pos"]] = ""
                    continue
                if k == self.LEVEL_KEY:
                    new_r["__level"] = v  # system_fields_prefix="__"
                    continue
                if k == self.UUID_KEY:
                    new_r["__uuid"] = v
                    continue
                new_r[self.DICT_ALIASES.get(k, k)] = v
            out.append(new_r)
        return out

    @classmethod
    def signature(cls) -> dict:
        """
        Сигнатура схемы — идентификатор набора полей.
        Кладём в файл/БД, чтобы при загрузке отсеять чужие/устаревшие данные.
        """
        return {
            "version": cls.SCHEMA_VERSION,
            "keys": list(cls.DICT_ALIASES.keys()),
            "level_key": cls.LEVEL_KEY,
        }
    @staticmethod
    def migrate_1(sig,data):
        sig['keys'].append( '_nomenclature_ref')
        for i, it in enumerate(data):
            data[i]['_nomenclature_ref'] = ''
        return sig, data

    @staticmethod
    def migrate_2(sig,data):
        sig['keys'].append( '_nomenclature_ref')
        rez = []
        for i, it in enumerate(data):
            if '_pki' not in it:
                it['_pki'] = 0
                it['pki_ui'] = ''
            if '_qty_on_item' not in it:
                it['_qty_on_item'] = 0
            if '_qty_on_struct' not in it:
                it['_qty_on_struct'] = 0
            if 'code_erp' not in it:
                it['code_erp'] = ''
            if SpecSchema.UUID_KEY not in it:
                it[SpecSchema.UUID_KEY] = F.get_time_shtamp_c()
            it = F.sort_dict_by_sample(it, SpecSchema.DICT_ALIASES)
            rez.append(it)
        sig = SpecSchema.signature()
        return sig, rez

    @classmethod
    def check_signature(cls, sig: dict) -> tuple[bool, list[str]]:
        """Проверить, что сохранённая сигнатура совпадает с текущей."""
        errors: list[str] = []
        if not isinstance(sig, dict):
            return False, ["Сигнатура не является словарём"]
        if sig.get("version") != cls.SCHEMA_VERSION:
            errors.append(
                f"Версия схемы не совпадает: файл={sig.get('version')!r}, "
                f"приложение={cls.SCHEMA_VERSION}"
            )
        if list(sig.get("keys", [])) != list(cls.DICT_ALIASES.keys()):
            errors.append("Набор/порядок полей не совпадает с текущей схемой")
        if sig.get("level_key") != cls.LEVEL_KEY:
            errors.append(
                f"Ключ уровня не совпадает: файл={sig.get('level_key')!r}, "
                f"приложение={cls.LEVEL_KEY!r}"
            )
        return (len(errors) == 0), errors


    def _validate_rows(self, rows) -> tuple[bool, list[str]]:
        """
        Проверить список словарей перед загрузкой.
        Возвращает (ok, errors). errors — человекочитаемые сообщения.
        """
        errors: list[str] = []

        if not isinstance(rows, list):
            return False, ["Данные не являются списком"]

        if not rows:
            return True, []

        known_keys   = set(self.DICT_ALIASES.keys())
        service_keys = {self.LEVEL_KEY, self.UUID_KEY}
        allowed_keys = known_keys | service_keys

        prev_lvl: int | None = None

        for i, r in enumerate(rows):
            if not isinstance(r, dict):
                errors.append(f"[{i}] элемент не словарь")
                continue

            keys = set(r.keys())

            unknown = keys - allowed_keys
            if unknown:
                errors.append(f"[{i}] неизвестные поля: {sorted(unknown)}")

            missing_service = service_keys - keys
            if missing_service:
                errors.append(f"[{i}] нет служебного поля: {sorted(missing_service)}")

            # отсутствующие пользовательские поля не критичны (подставим ""),
            # но сообщим — чтобы отловить битые строки
            missing_user = known_keys - keys
            if missing_user:
                errors.append(f"[{i}] нет полей: {sorted(missing_user)}")

            lvl = r.get(self.LEVEL_KEY)
            if not isinstance(lvl, int) or isinstance(lvl, bool) or lvl < 0:
                errors.append(
                    f"[{i}] {self.LEVEL_KEY!r} должен быть int >= 0, "
                    f"получено {lvl!r}"
                )
                continue

            if prev_lvl is None:
                if lvl != 0:
                    errors.append(
                        f"[{i}] первая строка должна иметь "
                        f"{self.LEVEL_KEY}=0, получено {lvl}"
                    )
            else:
                if lvl > prev_lvl + 1:
                    errors.append(
                        f"[{i}] уровень {lvl} после {prev_lvl} — пропуск уровня"
                    )
            prev_lvl = lvl

        return (len(errors) == 0), errors

    # ---------------- DUMP / LOAD ----------------

    def save_tree(self) -> dict:
        sig = self.signature()
        return {'sig':sig, 'data':self.dump_tree()}


    def dump_tree(self) -> list[dict]:
        """
        Обход дерева (preorder) -> list[dict] в pep-нотации.
        Сохраняет pos и _level.
        """
        tree = self.tree
        out: list[dict] = []

        def walk(item):
            dse = Dse_row(item)
            row = {p: dse.get(p) for p in self.PEP_NAMES}
            row[self.LEVEL_KEY] = dse.level
            row[self.UUID_KEY] = dse.uuid
            out.append(row)
            for i in range(item.childCount()):
                walk(item.child(i))

        for i in range(tree.topLevelItemCount()):
            walk(tree.topLevelItem(i))
        return out

    def hide_columns_by_prefix(self, prefix: str = "_") -> list[str]:
        """
        Скрыть колонки, чьи заголовки начинаются с prefix.
        Возвращает список имён скрытых колонок.
        """
        tree = self.tree
        header = tree.header()
        hidden: list[str] = []
        for col in range(tree.columnCount()):
            name = tree.headerItem().text(col)
            if name.startswith(prefix):
                if CFG.Config.user_config.is_developer:
                    print(f'Hide column {name}')
                    with CQT.QSignalBlocker(tree):
                        for item in tree.iter_items_preorder():
                            item.setForeground(col, CQT.QtGui.QColor(188, 188, 188))

                    with CQT.QSignalBlocker(header):
                        tree.headerItem().setForeground(col, CQT.QtGui.QColor(188, 188, 188))

                else:
                    header.hideSection(col)
                hidden.append(name)
        return hidden

    def load_tree(self, data:dict, **fill_kwargs) -> tuple[bool, list[str]]:
        """
        Проверить data и загрузить в дерево.
        Возвращает (ok, errors). При ok=False дерево не трогается.
        """
        sig = data['sig']
        rows = data['data']
        tree = self.tree
        #sig, rows = SpecSchema.migrate_1(sig, rows)
        sig, rows = SpecSchema.migrate_2(sig, rows)
        ok, errors = SpecSchema.check_signature(sig)
        if not ok:
            return False, errors
        ok, errors = self._validate_rows(rows)
        if not ok:
            return False, errors
        # очищаем всегда — чтобы старые данные не смешивались с новыми
        self.clear_table()

        if not rows:
            # чистое дерево — сразу выходим
            self._new = True
            # пустое дерево, но колонки обязательно нужны — иначе items «нулевой ширины»
            tree.setColumnCount(len(self.USER_HEADERS))
            tree.setHeaderLabels(self.USER_HEADERS)
            self.hide_columns_by_prefix()
            return True, []

        self._new = False

        tree.fill_table(
            self.to_tree_rows(rows),
            nick_name_level="__level",
            nick_name_uuid=None,
            system_fields_prefix="__",
            on_drop_access = tree.on_drop_access,
            odd_item_color = (203,213,203),
            even_item_color = (253,253,253),

            **fill_kwargs,
        )
        self.hide_columns_by_prefix()

        return True, []


    def add_row_silent(self, mode: str = AddMode.SIBLING)-> CTREE.ExtTreeWidgetItem:
        """
        Тихая вставка пустой строки относительно текущей.
        Возвращает созданный ExtTreeWidgetItem или None.
        """

        cur = self.tree.currentItem()

        if cur is None:
            parent = None
            new_level = 0
            insert_idx = self.tree.topLevelItemCount()
        else:
            cur_level = int(cur.data(0, cur.LEVEL_ROLE) or 0)

            if mode == AddMode.CHILD:
                parent = cur
                new_level = cur_level + 1
                insert_idx = cur.childCount()
            else:  # SIBLING
                parent = cur.parent()
                new_level = cur_level
                if parent is None:
                    insert_idx = self.tree.indexOfTopLevelItem(cur) + 1
                else:
                    insert_idx = parent.indexOfChild(cur) + 1

        header = self.tree.headerItem()
        texts = ["" for _ in range(self.tree.columnCount())]
        item = CTREE.ExtTreeWidgetItem(texts, new_level)

        if parent is None:
            self.tree.insertTopLevelItem(insert_idx, item)
        else:
            parent.insertChild(insert_idx, item)
            parent.setExpanded(True)

        return item


    def remove_cur_row_silent(self) -> bool:
        """Тихое удаление текущей строки вместе с потомками. True если удалили."""

        cur = self.tree.currentItem()
        if cur is None:
            return False

        parent = cur.parent()
        if parent is None:
            self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(cur))
        else:
            parent.removeChild(cur)
        return True

    def _clone_item(self, src):
        """
        Рекурсивный клон ExtTreeWidgetItem.
        Все значения и служебные поля копируются, uuid генерится заново.
        """
        texts = [src.text(c) for c in range(src.columnCount())]
        lvl = int(src.data(0, src.LEVEL_ROLE) or 0)

        sys_src = src.data(0, src.SYSTEM_FIELDS_ROLE)
        temp_src = src.data(0, src.TEMP_FIELDS_ROLE)

        clone = CTREE.ExtTreeWidgetItem(
            texts,
            lvl,
            object_uuid=None,  # новый uuid
            system_data=copy.deepcopy(sys_src) if sys_src else {},
            temp_data=copy.deepcopy(temp_src) if temp_src is not None else None,
        )
        for i in range(src.childCount()):
            clone.addChild(self._clone_item(src.child(i)))
        return clone

    def duplicate_row_silent(self):
        """Тихий дубль текущей строки (со всеми потомками) сразу под оригиналом."""
        tree = self.tree
        cur = tree.currentItem()
        if cur is None:
            return None

        clone = self._clone_item(cur)
        parent = cur.parent()
        if parent is None:
            idx = tree.indexOfTopLevelItem(cur) + 1
            tree.insertTopLevelItem(idx, clone)
        else:
            idx = parent.indexOfChild(cur) + 1
            parent.insertChild(idx, clone)
            parent.setExpanded(True)
        return clone

    def oform_tree(self,fnc_oform):
        lvl = 0
        tree = self.tree
        def oform_row(item,lvl_parent=0) -> None:
            lvl = lvl_parent + 1
            for i in range(item.childCount()):
                oform_row(item.child(i),lvl)
            fnc_oform(item,lvl)

        for i in range(tree.topLevelItemCount()):
            oform_row(tree.topLevelItem(i))

    def expand_all(self) -> None:
        """Раскрыть все узлы, не дёргая тяжёлые обработчики на каждый узел."""
        tree = self.tree
        tree.blockSignals(True)
        try:
            tree.expandAll()
        finally:
            tree.blockSignals(False)
        # один раз перерисовываем и пересчитываем чередование
        tree.apply_alternate_colors()
        tree.viewport().update()

    def clear_table(self):
        self.tree.setCurrentItem(None)
        self.tree.clearSelection()
        self.tree._clear_table()

class Dse_row:
    """
    Обёртка над ExtTreeWidgetItem — представляет строку дерева как «деталь».

    В __init__ собирает:
        cols  : dict[pep_name, column_index]  — где какое поле в дереве
        values: dict[pep_name, str]           — снапшот значений на момент создания
    Это ускоряет обход дерева: не нужно каждый раз искать колонку по header
    и дёргать item.text() повторно для расчётов.
    """

    PARAM_KEY = "Параметр"
    VALUE_KEY = "Значение"
    NAME_KEY  = "_name"

    def __init__(self, item, with_values: bool = True):
        # item: ExtTreeWidgetItem
        self.item = item
        self.tree = item.treeWidget()

        # --- кеш колонок: pep_name -> index ---
        self.cols: dict[str, int] = self._build_cols()

        # --- снапшот значений (опционально) ---
        self.values: dict[str, str] = {}
        if with_values:
            self._load_values()

    # ---------------- служебное ----------------
    def apply_template(self, tpl: list[dict]) -> list[str]:
        """
        Применить вертикальную структуру [{"_name":pep, "Значение":val}, ...]
        к item'у. Возвращает список pep_name, которые были изменены.
        Пишет только те, что реально отличаются — чтобы не плодить setText.
        """
        changed: list[str] = []
        for row in tpl:
            pep = row.get(self.NAME_KEY)
            if pep not in SpecSchema.REWRITE_FIELDS:
                continue
            if not pep or pep == "pos":
                continue  # pos — вычисляемое
            if pep not in self.cols:
                continue  # нет такой колонки
            new_val = row.get(self.VALUE_KEY, "")
            new_val = "" if new_val is None else str(new_val)
            old_val = self.values.get(pep, "")
            if new_val != old_val:
                self.set(pep, new_val)
                changed.append(pep)
        return changed


    def _build_cols(self) -> dict[str, int]:
        """Один проход по header: user_text -> pep_name -> column."""
        header = self.tree.headerItem()
        user_to_pep = SpecSchema.USER_TO_PEP
        cols: dict[str, int] = {}
        for col in range(self.tree.columnCount()):
            pep = user_to_pep.get(header.text(col))
            if pep is not None:
                cols[pep] = col
        return cols

    def _load_values(self) -> None:
        """Снапшот всех колонок (кроме pos — он вычисляемый)."""
        for pep, col in self.cols.items():
            self.values[pep] = self.item.text(col) or ""

    def refresh(self, with_values: bool = True) -> None:
        """Пересобрать кеши (если структура дерева изменилась)."""
        self.cols = self._build_cols()
        if with_values:
            self._load_values()

    # ---------------- чтение/запись ----------------

    def _column_by_pep(self, pep_name: str) -> int | None:
        return self.cols.get(pep_name)

    def _get_value(self, pep_name: str) -> str:
        col = self.cols.get(pep_name)
        if col is None:
            return ""
        return self.item.text(col) or ""

    def _set_value(self, pep_name: str, value: object) -> bool:
        col = self.cols.get(pep_name)
        if col is None:
            return False
        val = "" if value is None else str(value)
        self.item.setText(col, val)
        self.values[pep_name] = val   # поддерживаем снапшот актуальным
        return True

    def _calc_pos(self) -> str:
        """№ п.п — генерируется на лету из позиции в дереве (1, 1.1, 1.1.1)."""
        parts: list[str] = []
        node = self.item
        while node is not None:
            parent = node.parent()
            if parent is None:
                idx = self.tree.indexOfTopLevelItem(node)
            else:
                idx = parent.indexOfChild(node)
            parts.append(str(idx + 1))
            node = parent
        return ".".join(reversed(parts))

    # ---------------- публичное ----------------

    @property
    def level(self) -> int:
        v = self.item.data(0, self.item.LEVEL_ROLE)
        return int(v) if v is not None else 0

    @property
    def uuid(self):
        return self.item.uuid

    def get(self, pep_name: str, default: object = "") -> object:
        if pep_name == "pos":
            return self._calc_pos()
        val = self.values.get(pep_name, None)
        if val is None or val == "":
            return default
        return val

    def set(self, pep_name: str, value: object) -> bool:
        return self._set_value(pep_name, value)

    def template(self) -> list[dict]:
        """
        Вертикальное представление строки:
            [
                {"_name": pep_name, "Параметр": user_text, "Значение": val},
                ...
            ]
        Порядок и набор — по SpecSchema.DICT_ALIASES.
        """
        out: list[dict] = []
        for pep_name, user_text in SpecSchema.DICT_ALIASES.items():
            out.append({
                self.NAME_KEY:  pep_name,
                self.PARAM_KEY: user_text,
                self.VALUE_KEY: self.get(pep_name),
            })
        return out

class Nomenclature:
    EMO_PKI = CEMOJ.ОперацииПроизводства.purchased.symbol
    def __init__(self,refs_types_nomen:set[str]):
        dict_types_nomens = {f'&nomen_{i}': ref for i, ref in enumerate(refs_types_nomen)}
        types_nomens_str = ', '.join(list(dict_types_nomens.keys()))

        wet_req_text = f"""
                                ВЫБРАТЬ
                                Номенклатура.Ссылка КАК Номенклатура,
                                
                                МАКСИМУМ(ВЫБОР
                                        КОГДА СхемыОбеспечения.Склад ЕСТЬ NULL
                                            ТОГДА 0
                                        ИНАЧЕ 1
                                    КОНЕЦ) КАК ЭтоПКИ
                            ПОМЕСТИТЬ ВТ_с_ПКИ
                            ИЗ
                                Справочник.Номенклатура КАК Номенклатура
                                    ЛЕВОЕ СОЕДИНЕНИЕ РегистрСведений.СхемыОбеспечения КАК СхемыОбеспечения
                                    ПО (Номенклатура.СхемаОбеспечения.Ссылка = СхемыОбеспечения.СхемаОбеспечения)
                                        И (СхемыОбеспечения.Склад.Ссылка В
                                            (ВЫБРАТЬ
                                                Склады.Ссылка
                                            ИЗ
                                                Справочник.Склады КАК Склады
                                            ГДЕ
                                                Склады.Наименование ПОДОБНО "Склад комплектующих%"))
                            ГДЕ
                                Номенклатура.ВидНоменклатуры В ({types_nomens_str})
                            
                            СГРУППИРОВАТЬ ПО
                            
                                Номенклатура.Ссылка
                            ;
                            
                            ////////////////////////////////////////////////////////////////////////////////
                            ВЫБРАТЬ
                                ВТ_с_ПКИ.Номенклатура.ПометкаУдаления КАК _ПометкаУдаления,
                                "" КАК X,
                                ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВТ_с_ПКИ.Номенклатура.Ссылка)) _ref,
                                ВТ_с_ПКИ.Номенклатура.Код КАК Код,
                                ВТ_с_ПКИ.Номенклатура.Наименование КАК Наименование,
                                ВТ_с_ПКИ.Номенклатура.Артикул КАК Артикул,
                                ВТ_с_ПКИ.Номенклатура.ВидНоменклатуры.Наименование КАК Вид,
                                ВТ_с_ПКИ.ЭтоПКИ КАК ПКИ
                            ИЗ
                                ВТ_с_ПКИ КАК ВТ_с_ПКИ
                            УПОРЯДОЧИТЬ ПО
                                                            Артикул,
                                                            Наименование,
                                                            Вид

                    """
        refs = APIERP.Refs_wet(wet_req_text)
        for name, ref in dict_types_nomens.items():
            ref_res = APIERP.Ref_wet(name.replace('&', ''), 'Справочники.ВидыНоменклатуры', ref)
            refs.add_ref(ref_res)

        key, data_rez = APIERP.get_wet_request(wet_req_text, refs=refs)

        if key != 200:
            print(f'find_erp_res Ошибка получения данных код ({key}) из ERP')

        data = data_rez['data']
        emo_del = CEMOJ.СтатусыПроизводства.error.symbol

        for it in data:
            if it['_ПометкаУдаления']:
                it['X'] = emo_del
            it['ПКИ'] = self.EMO_PKI if it['ПКИ'] else ''



        self.data:list[dict] = data

class TypesNomenclature:
    NAME_LAST_TYPE_NOMEN = 'type_nomen_constructor_tree'
    def __init__(self):
        self.load()

    @property
    def last_type_nomen(self)->str|None:
        return CMS.load_tmp_stukt(self.NAME_LAST_TYPE_NOMEN, None)

    @last_type_nomen.setter
    def last_type_nomen(self, value:str):
        CMS.save_tmp_stukt(value,self.NAME_LAST_TYPE_NOMEN)

    def load(self):
        def sort_tree(items: list[dict]) -> list[dict]:
            """
            Рекурсивно переупорядочивает плоский список словарей так,
            чтобы он читался как дерево (без добавления новых полей).

            Правила:
              1. Первым идёт элемент, чей 'Родитель_ref' отсутствует среди 'ref' (корень).
              2. Сразу за узлом идут его потомки.
              3. Среди потомков сначала идут 'ЭтоГруппа' == True, затем остальные
                 (в исходном относительном порядке).
              4. Каждый потомок раскрывается аналогично.
            """
            refs = {it['_ref'] for it in items}

            children: dict[str, list[dict]] = {}
            roots: list[dict] = []
            for it in items:
                parent = it['_Родитель_ref']
                if parent in refs:
                    children.setdefault(parent, []).append(it)
                else:
                    roots.append(it)

            def order(lst: list[dict]) -> list[dict]:
                # группы вперёд, стабильно
                return sorted(lst, key=lambda x: not x.get('_ЭтоГруппа'))

            result: list[dict] = []

            def walk(node: dict) -> None:
                result.append(node)
                for child in order(children.get(node['_ref'], [])):
                    walk(child)

            for root in order(roots):
                walk(root)

            return result

        wet_req_text = f"""
            ВЫБРАТЬ
            ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВидыНоменклатуры.ССЫЛКА)) _ref,
            ВидыНоменклатуры.ПометкаУдаления КАК _ПометкаУдаления,
            "" КАК X,
            ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВидыНоменклатуры.Родитель.ССЫЛКА)) _Родитель_ref, 
            ВидыНоменклатуры.ЭтоГруппа КАК _ЭтоГруппа,
            ВидыНоменклатуры.Наименование КАК Наименование,
            ВидыНоменклатуры.Описание КАК Описание
        ИЗ
            Справочник.ВидыНоменклатуры КАК ВидыНоменклатуры
        ГДЕ
            ВидыНоменклатуры.Родитель В ИЕРАРХИИ
                    (ВЫБРАТЬ ПЕРВЫЕ 1
                        ВидыНоменклатуры.Ссылка КАК Ссылка
                    ИЗ
                        Справочник.ВидыНоменклатуры КАК ВидыНоменклатуры
                    ГДЕ
                        ВидыНоменклатуры.Ссылка = &ИВид
                        И ВидыНоменклатуры.ЭтоГруппа = ИСТИНА)
"""
        refs = APIERP.Refs_wet(wet_req_text)
        ref_res = APIERP.Ref_wet('ИВид', 'Справочники.ВидыНоменклатуры', '12ce209b-a327-11e9-80e4-4ccc6a67082d')
        refs.add_ref(ref_res)

        key, data_rez = APIERP.get_wet_request(wet_req_text, refs=refs)

        if key != 200:
            print(f'find_erp_res Ошибка получения данных код ({key}) из ERP')
        if data_rez['data']:
            data = data_rez['data']

        for it in data:
            emo_gr = '       '
            if it['_ЭтоГруппа']:
                emo_gr = CEMOJ.ДокументыДанные.folder.symbol
            it['Наименование'] = f'{emo_gr} {it["Наименование"]}'

            emo_del = ''
            if it['_ПометкаУдаления']:
                emo_del = CEMOJ.СтатусыПроизводства.error.symbol
            it['X'] = emo_del

        self.data = sort_tree(data)

    def get_set_child_refs(self,ref:str, with_parent:bool=True)->set[str]:
        childs = set([_['_ref'] for _ in self.data if _['_Родитель_ref'] == ref])
        if with_parent:
            childs.add(ref)
        return childs

class OpenedFile():
    _emo_doc = CEMOJ.ДокументыДанные.document.symbol
    _emo_card = CEMOJ.ДокументыДанные.archive.symbol

    def __init__(self,lbl_o:CQT.QtWidgets.QLabel):
        self._pathf:F.Cust_path|None = None
        self._lbl_o:CQT.QtWidgets.QLabel = lbl_o
        self._dirty:bool = False
        self._card:CardDocs = None

    def set(self, pathf:str|None|CardDocs):

        if pathf is None:
            self._pathf = None
            self._card = None

        else:
            if isinstance(pathf, CardDocs):
                self._card = pathf
                self._pathf = None
            else:
                self._pathf = F.Cust_path(pathf)
                self._card = None

        self._dirty: bool = False
        self.upd_ui()

    def upd_ui(self):
        prefix = ''
        if self._dirty:
            prefix = '*'
        if self._pathf:
            self._lbl_o.setText(f'{prefix} {self._emo_doc} {self._pathf}')
            return
        if self._card:
            self._lbl_o.setText(f'{prefix} {self._emo_card} Карточка {self._card}')
            return
        self._lbl_o.setText(f'{prefix}')

    @property
    def pathf(self)->str:
        return str(self._pathf.path)

    @property
    def is_opened(self)->bool:
        return self._pathf is not None
    @property
    def is_dirty(self)->bool:
        return self._dirty

    def set_dirty(self,val:bool=True):
        self._dirty = val
        self.upd_ui()