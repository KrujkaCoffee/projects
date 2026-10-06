from __future__ import annotations

import copy
import datetime
import enum
import math
import numbers
from collections.abc import Mapping

from project_cust_38 import Cust_Qt as CQT
from project_cust_38 import Cust_SQLite as CSQ
from project_cust_38 import Cust_orm as ORM


__all__ = ['SqlPageManager', 'OrmPageManager']


class SqlPageManager(CQT.PageManager):
    """
    pm = SqlPageManager(
        bd="SRV:DB_nomenklatura_erp.db",
        query='SELECT "Пномер", "Код", "Наименование" FROM "nomen"',
        columns=("Пномер", "Код", "Наименование"),
        key_column="Пномер",
        order_by=("Наименование", "Пномер"),
        column_types={"Пномер": int, "Код": str, "Наименование": str},
        page_size=100,
    )
    selected = CQT.msgboxg_get_table(
        window, "Номенклатура", None, page_manager=pm,
        decorate_dialog=pm.bind_dialog, selectRows=True, ExtendedSelection=False,
    )
    """

    def __init__(self, bd, query, columns, key_column, params=(), order_by=(),
                 page_size=100, column_types=None, attach_dbs=(), executor=None):
        page_size = self._positive_int(page_size)
        super().__init__(page_size=page_size)
        if isinstance(columns, str):
            raise TypeError("columns должен быть последовательностью имён колонок")
        self.columns = tuple(columns)
        if not self.columns or any(not isinstance(c, str) or not c or '\x00' in c for c in self.columns):
            raise ValueError("Нужны непустые имена колонок")
        if len(set(self.columns)) != len(self.columns):
            raise ValueError("Имена выходных колонок должны быть уникальны")
        if key_column not in self.columns:
            raise ValueError("Уникальный ключ должен входить в columns")
        if isinstance(params, (str, bytes, Mapping)):
            raise TypeError("params должен быть последовательностью значений")
        self.bd = bd
        self.key_column = key_column
        self.params = tuple(copy.deepcopy(tuple(params)))
        self.query = self._normalize_query(query)
        self.attach_dbs = (attach_dbs,) if isinstance(attach_dbs, str) else tuple(attach_dbs or ())
        self.executor = executor
        self.column_types = dict(column_types or {})
        if set(self.column_types) - set(self.columns):
            raise ValueError("column_types содержит неизвестные колонки")
        if any(t not in (str, int, float, bool, bytes, datetime.date, datetime.datetime, None)
               for t in self.column_types.values()):
            raise TypeError("Неподдерживаемый тип колонки")
        self._filters = {}
        self._order = self._normalize_order(order_by)
        self._rows = []
        self._loaded = False
        self._committed = None
        self._dialog_ref = None
        self.last_error = None

    @staticmethod
    def _positive_int(value):
        if isinstance(value, bool) or not isinstance(value, numbers.Integral) or value <= 0:
            raise ValueError("Размер страницы должен быть положительным целым числом")
        return int(value)

    @staticmethod
    def _quote(name):
        return '"' + name.replace('"', '""') + '"'

    @staticmethod
    def _normalize_sql(sql):
        if not isinstance(sql, str) or not sql.strip():
            raise TypeError("Источник должен быть SQL-строкой SELECT/WITH")
        pieces = []
        tokens = []
        top = []
        depth = 0
        index = 0
        ended = False
        while index < len(sql):
            char = sql[index]
            if char.isspace():
                pieces.append(char)
                index += 1
                continue
            if sql.startswith('--', index):
                end = sql.find('\n', index + 2)
                index = len(sql) if end < 0 else end
                pieces.append(' ')
                continue
            if sql.startswith('/*', index):
                end = sql.find('*/', index + 2)
                if end < 0:
                    raise ValueError("Незакрытый SQL-комментарий")
                pieces.append(' ')
                index = end + 2
                continue
            if ended:
                raise ValueError("Допускается только один SQL-запрос")
            if char in "'\"`[":
                closing = ']' if char == '[' else char
                start = index
                index += 1
                while index < len(sql):
                    if sql[index] == closing:
                        if index + 1 < len(sql) and sql[index + 1] == closing:
                            index += 2
                            continue
                        index += 1
                        break
                    index += 1
                else:
                    raise ValueError("Незакрытая SQL-строка или имя")
                pieces.append(sql[start:index])
                continue
            if char == ';':
                if depth:
                    raise ValueError("Разделитель SQL внутри источника не поддержан")
                ended = True
                index += 1
                continue
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth < 0:
                    raise ValueError("Некорректные скобки SQL")
            if char.isalpha() or char == '_':
                start = index
                while index < len(sql) and (sql[index].isalnum() or sql[index] in '_$'):
                    index += 1
                word = sql[start:index]
                if word.upper() != 'REPLACE' or not sql[index:].lstrip().startswith('('):
                    tokens.append(word.upper())
                if depth == 0:
                    top.append(word.upper())
                pieces.append(word)
                continue
            pieces.append(char)
            index += 1
        if depth or not top or top[0] not in ('SELECT', 'WITH') or 'SELECT' not in top:
            raise ValueError("Нужен один запрос SELECT/WITH с корректными скобками")
        if set(tokens) & {'INSERT', 'UPDATE', 'DELETE', 'REPLACE', 'CREATE', 'DROP', 'ALTER',
                          'ATTACH', 'DETACH', 'PRAGMA', 'VACUUM', 'INTO', 'RETURNING'}:
            raise ValueError("Менеджер принимает только запрос чтения")
        if set(top) & {'LIMIT', 'OFFSET', 'FETCH'} or any(
                top[i:i + 2] == ['ORDER', 'BY'] for i in range(len(top) - 1)):
            raise ValueError("Верхнеуровневые ORDER BY/LIMIT/OFFSET задаются менеджером")
        return ''.join(pieces).strip()

    @classmethod
    def _normalize_query(cls, query):
        query_type = getattr(CSQ, 'SqlQuery', None)
        if query_type is not None and isinstance(query, query_type):
            return query_type(sqlite=cls._normalize_sql(query.sqlite),
                              postgres=cls._normalize_sql(query.postgres),
                              canBranch=query.canBranch)
        return cls._normalize_sql(query)

    def _normalize_order(self, fields):
        if isinstance(fields, str):
            raise TypeError("Порядок задаётся последовательностью имён полей")
        result = []
        seen = set()
        for item in fields:
            if not isinstance(item, str):
                raise TypeError("Поле сортировки должно быть строкой")
            field = item[1:] if item.startswith('-') else item
            if field not in self.columns:
                raise ValueError(f"Неизвестная колонка сортировки: {field}")
            if field in seen:
                raise ValueError(f"Колонка сортировки указана дважды: {field}")
            seen.add(field)
            result.append(item)
        if self.key_column not in seen:
            result.append(self.key_column)
        return tuple(result)

    def _split_filter(self, key):
        if key in self.columns:
            return key, 'exact'
        if not isinstance(key, str) or '__' not in key:
            raise ValueError(f"Неизвестное поле фильтра: {key}")
        field, lookup = key.rsplit('__', 1)
        if field not in self.columns:
            raise ValueError(f"Неизвестное поле фильтра: {field}")
        if lookup not in ('exact', 'ne', 'contains', 'in', 'isnull', 'gt', 'gte', 'lt', 'lte'):
            raise ValueError(f"Неподдерживаемое условие: {lookup}")
        return field, lookup

    def __convert_value(self, column, value):
        if value is None:
            return None
        kind = self.column_types.get(column)
        if kind is None:
            return value
        try:
            if kind is bool:
                if isinstance(value, bool):
                    return value
                text = str(value).casefold()
                if text in ('1', 'да'):
                    return True
                if text in ('0', 'нет'):
                    return False
                raise ValueError()
            if kind is int:
                if isinstance(value, bool) or isinstance(value, float) and not value.is_integer():
                    raise ValueError()
                return int(value)
            if kind is float:
                converted = float(value)
                if not math.isfinite(converted):
                    raise ValueError()
                return converted
            if kind in (datetime.datetime, datetime.date):
                if isinstance(value, kind):
                    return value
                return kind.fromisoformat(str(value))
            if kind is bytes:
                if not isinstance(value, (bytes, bytearray, memoryview)):
                    raise ValueError()
                return bytes(value)
            return kind(value)
        except (TypeError, ValueError, OverflowError) as exc:
            return str(value)

    def _normalize_filters(self, conditions):
        result = {}
        seen = set()
        for key, value in conditions.items():
            column, lookup = self._split_filter(key)
            if (column, lookup) in seen:
                raise ValueError(f"Условие {column} / {lookup} задано дважды")
            seen.add((column, lookup))
            if lookup == 'isnull':
                if type(value) is not bool:
                    raise TypeError("isnull принимает True или False")
            elif lookup == 'in':
                if not isinstance(value, (list, tuple, set, frozenset)):
                    raise TypeError("in принимает список, кортеж или множество")
                value = tuple(self.__convert_value(column, item) for item in value)
                if any(item is None for item in value):
                    raise ValueError("NULL проверяется отдельным условием isnull")
            elif lookup == 'contains':
                if value is None or self.column_types.get(column) not in (None, str):
                    raise ValueError("Поиск подстроки доступен только для текстовых колонок")
                value = str(value)
            else:
                value = self.__convert_value(column, value)
                if value is None and lookup not in ('exact', 'ne'):
                    raise ValueError("NULL проверяется через exact/ne/isnull")
            result[key] = copy.deepcopy(value)
        return result

    def __prepare_filter_value(self, column, value):
        if isinstance(value, datetime.datetime):
            return value.isoformat(sep=' ')
        if isinstance(value, datetime.date):
            return value.isoformat()
        return value

    def _where_clause(self, column_sql):
        clauses = []
        parameters = []
        operators = {'exact': '=', 'ne': '<>', 'gt': '>', 'gte': '>=', 'lt': '<', 'lte': '<='}
        for key, value in self._filters.items():
            field, lookup = self._split_filter(key)
            column = column_sql(field)
            if lookup == 'isnull' or value is None:
                is_null = value if lookup == 'isnull' else lookup == 'exact'
                clauses.append(f"({column} {'IN' if is_null else 'NOT IN'} ('', 0) {f' OR {column} IS NULL' if is_null else ''})")
            elif lookup == 'in':
                if value:
                    clauses.append(f"{column} IN ({', '.join('?' for _ in value)})")
                    parameters.extend(self.__prepare_filter_value(field, item) for item in value)
                else:
                    clauses.append('1 = 0')
            elif lookup == 'contains':
                pattern = value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
                clauses.append(f"{column} LIKE ? ESCAPE '\\'")
                parameters.append('%' + pattern + '%')
            else:
                clauses.append(f"{column} {operators[lookup]} ?")
                parameters.append(self.__prepare_filter_value(field, value))
        return ' AND '.join(clauses), parameters

    def _order_clause(self, column_sql):
        return ', '.join(column_sql(item[1:] if item.startswith('-') else item)
                         + (' DESC' if item.startswith('-') else ' ASC') for item in self._order)

    def __build_query(self, count=False, offset=0):
        where, filter_params = self._where_clause(self._quote)
        projection = 'COUNT(*) AS "__page_count"' if count else ', '.join(map(self._quote, self.columns))
        def wrap(base):
            sql = f'SELECT {projection} FROM ({base}) AS page_source'
            if where:
                sql += ' WHERE ' + where
            if not count:
                sql += ' ORDER BY ' + self._order_clause(self._quote) + ' LIMIT ? OFFSET ?'
            return sql
        query_type = getattr(CSQ, 'SqlQuery', None)
        if query_type is not None and isinstance(self.query, query_type):
            sql = query_type(sqlite=wrap(self.query.sqlite), postgres=wrap(self.query.postgres),
                             canBranch=self.query.canBranch)
        else:
            sql = wrap(self.query)
        parameters = [*self.params, *filter_params]
        if not count:
            parameters.extend((self.page_size, offset))
        return sql, parameters

    def _execute(self, sql, parameters, one=False):
        if self.executor is not None:
            return self.executor.execute(self.bd, sql, params=parameters, rez_dict=True,
                                         one=one, attach_dbs=self.attach_dbs)
        return CSQ.custom_request_c(self.bd, sql, list_of_lists_c=[parameters],
                                    rez_dict=True, hat_c=False, one=one,
                                    attach_dbs=self.attach_dbs, lazy_method_hours=0)

    def _read_count(self):
        sql, parameters = self.__build_query(count=True)
        result = self._execute(sql, parameters, one=True)
        if not isinstance(result, Mapping) or '__page_count' not in result:
            raise RuntimeError("Не удалось получить количество строк")
        count = result['__page_count']
        if isinstance(count, bool) or not isinstance(count, numbers.Integral) or count < 0:
            raise RuntimeError("Источник вернул некорректное количество строк")
        return int(count)

    def _read_rows(self, page):
        sql, parameters = self.__build_query(offset=(page - 1) * self.page_size)
        result = self._execute(sql, parameters)
        if not isinstance(result, (list, tuple)):
            raise RuntimeError("Не удалось загрузить страницу: ожидался список строк")
        if len(result) > self.page_size:
            raise RuntimeError("Источник не соблюдает ограничение размера страницы")
        rows = []
        keys = set()
        for row in result:
            if not isinstance(row, Mapping) or any(column not in row for column in self.columns):
                raise RuntimeError("Колонки результата не соответствуют конфигурации страницы")
            identity = row[self.key_column]
            if identity is None or identity in keys:
                raise RuntimeError("Ключ строки пуст или не уникален в странице")
            keys.add(identity)
            rows.append({column: row[column] for column in self.columns})
        return rows

    def _state(self):
        return (copy.deepcopy(self._filters), self._order, self.page_size,
                self.current_page, self.total_count)

    def _restore(self):
        if self._committed is not None:
            filters, order, size, page, count = self._committed
            self._filters = copy.deepcopy(filters)
            self._order = order
            self.page_size = size
            self.current_page = page
            self.total_count = count

    def _load(self, recount=False):
        try:
            count = self._read_count() if recount or not self._loaded else self.total_count
            pages = (count + self.page_size - 1) // self.page_size
            page = max(1, min(self.current_page, pages))
            rows = self._read_rows(page) if count else []
            if count and not rows:
                count = self._read_count()
                pages = (count + self.page_size - 1) // self.page_size
                page = max(1, min(page, pages))
                rows = self._read_rows(page) if count else []
                if count and not rows:
                    raise RuntimeError("Данные изменились во время чтения; повторите обновление")
        except Exception as exc:
            self._restore()
            self.last_error = exc
            raise
        self.total_count = count
        self.current_page = page
        self._rows = rows
        self._loaded = True
        self._committed = self._state()
        self.last_error = None

    def set_data(self, data, user_data=None):
        if data is not None or user_data is not None:
            raise TypeError("Источник задан конструктором; передайте в диалог None")
        self.current_page = 1
        self._load(recount=True)

    def page_data(self):
        if not self._loaded or self._state() != self._committed:
            recount = not self._loaded or self._state()[:2] != self._committed[:2]
            self._load(recount=recount)
        return [list(self.columns), *[[row[column] for column in self.columns] for row in self._rows]], None

    @property
    def page_rows(self):
        self.page_data()
        return tuple(dict(row) for row in self._rows)

    def set_filter(self, **conditions):
        filters = self._normalize_filters(conditions)
        if filters == self._filters:
            return False
        self._filters = filters
        self.current_page = 1
        if self._loaded:
            self._load(recount=True)
            self.__refresh_dialog()
        return True

    def set_order(self, *fields):
        order = self._normalize_order(fields)
        if order == self._order:
            return False
        self._order = order
        self.current_page = 1
        if self._loaded:
            self._load()
            self.__refresh_dialog()
        return True

    def set_page_size(self, value):
        value = self._positive_int(value)
        if value == self.page_size:
            return False
        self.page_size = value
        self.current_page = 1
        if self._loaded:
            self._load()
            self.__refresh_dialog()
        return True

    def reload(self):
        self._load(recount=True)
        self.__refresh_dialog()

    def _dialog(self):
        ref = self._dialog_ref
        dialog = ref() if ref is not None else None
        if dialog is not None:
            try:
                dialog.objectName()
            except RuntimeError:
                return None
        return dialog

    def __parse_filter_cell(self, column, text):
        literal = str(text).lstrip()
        text = literal.strip()
        if not text:
            return None
        if text.upper() == '!*': # todo заменить на !* для однородности
            return column + '__isnull', True
        if text.upper() == '*':
            return column + '__isnull', False
        if text.startswith('~'):
            if (self.column_types.get(column) or str) is not str:
                raise ValueError(f'{column}: поиск подстроки доступен только для текстовых колонок')
            return column + '__contains', literal[1:]
        for prefix, lookup in (('!=', 'ne'), ('>=', 'gte'), ('<=', 'lte'),
                               ('=', 'exact'), ('>', 'gt'), ('<', 'lt')):
            if text.startswith(prefix):
                value = literal[len(prefix):]
                if not value and lookup != 'exact':
                    raise ValueError(f'{column}: после {prefix} требуется значение')
                return column + '__' + lookup, self.__convert_value(column, value)
        if (self.column_types.get(column) or str) is str:
            return column + '__contains', text
        return column + '__exact', self.__convert_value(column, text)

    def __filter_cell_text(self, column):
        conditions = [(key, value) for key, value in self._filters.items()
                      if self._split_filter(key)[0] == column]
        if not conditions:
            return ''
        if len(conditions) != 1:
            return None
        key, value = conditions[0]
        lookup = self._split_filter(key)[1]
        if lookup == 'isnull':
            return '!*' if value else '*'
        if value is None:
            if lookup == 'exact':
                return '!*'
            if lookup == 'ne':
                return '*'
            return None
        if lookup == 'contains':
            if (self.column_types.get(column) or str) is not str:
                return None
            return '~' + str(value)
        if isinstance(value, (dict, list, tuple, set, frozenset, bytes, bytearray, memoryview)):
            return None
        prefixes = {'exact': '=', 'ne': '!=', 'gt': '>', 'gte': '>=', 'lt': '<', 'lte': '<='}
        if lookup not in prefixes:
            return None
        text = ('1' if value else '0') if isinstance(value, bool) else str(value)
        return prefixes[lookup] + text

    def __sync_filter_cells(self):
        dialog = self._dialog()
        if dialog is None:
            return
        table = dialog.ui.tbl_filtr
        if table.rowCount() != 1 or table.columnCount() != len(self.columns):
            return
        self._locked_filter_columns = set()
        blocker = CQT.QtCore.QSignalBlocker(table)
        for index, column in enumerate(self.columns):
            text = self.__filter_cell_text(column)
            item = table.item(0, index)
            if item is None:
                item = CQT.QtWidgets.QTableWidgetItem()
                table.setItem(0, index, item)
            flags = item.flags()
            if text is None:
                self._locked_filter_columns.add(column)
                item.setFlags(flags & ~CQT.QtCore.Qt.ItemIsEditable)
                item.setText('-')
                conditions = {key: value for key, value in self._filters.items()
                              if self._split_filter(key)[0] == column}
                item.setToolTip('Условие сохраняется при фильтрации и очистке строки: ' + repr(conditions))
            else:
                item.setFlags(flags | CQT.QtCore.Qt.ItemIsEditable)
                item.setText(text)
                item.setToolTip(table.toolTip())
        del blocker

    def __filters_from_table(self, table):
        if table.rowCount() != 1 or table.columnCount() != len(self.columns):
            raise ValueError('Серверный фильтр требует одну строку и исходный порядок колонок')
        locked = self._locked_filter_columns
        filters = {key: value for key, value in self._filters.items()
                   if self._split_filter(key)[0] in locked}
        for index, column in enumerate(self.columns):
            if column in locked:
                continue
            if table.cellWidget(0, index) is not None:
                raise ValueError('Серверный фильтр поддерживает только текстовые ячейки')
            item = table.item(0, index)
            condition = self.__parse_filter_cell(column, item.text() if item else '')
            if condition is not None:
                filters[condition[0]] = condition[1]
        return filters

    def __show_dialog_error(self, error):
        self.last_error = error
        dialog = self._dialog()
        if dialog is None:
            return
        if self._dialog_error_handler is not None:
            self._dialog_error_handler(dialog, error)
        else:
            print(error)
            CQT.msgbox('Не удалось обновить таблицу')

    def __refresh_dialog(self):
        dialog = self._dialog()
        if dialog is not None:
            self.__sync_filter_cells()
            dialog.fill_current_page()

    def __apply_dialog_filter(self):
        dialog = self._dialog()
        if dialog is None:
            return
        mode = self._filter_apply_mode
        self._filter_apply_mode = None
        table = dialog.ui.tbl_filtr
        try:
            if mode == 'clear':
                blocker = CQT.QtCore.QSignalBlocker(table)
                for index, column in enumerate(self.columns):
                    item = table.item(0, index)
                    if item is not None and column not in self._locked_filter_columns:
                        item.setText('')
                del blocker
            conditions = self.__filters_from_table(table)
        except Exception as error:
            self.__show_dialog_error(error)
            return
        try:
            self.set_filter(**conditions)
        except Exception as error:
            self.__sync_filter_cells()
            self.__show_dialog_error(error)

    def bind_dialog(self, dialog, after_page=None, on_error=None):
        import weakref

        if getattr(dialog, 'page_manager', None) is not self:
            raise ValueError('Диалог должен использовать этот page_manager')
        current = self._dialog()
        if current is dialog:
            return
        if current is not None:
            raise ValueError('Менеджер уже подключён к открытому диалогу')
        table = dialog.ui.tbl_filtr
        if table.rowCount() not in (0, 1):
            raise ValueError('Серверный фильтр поддерживает только одну строку')
        if table.rowCount() and table.columnCount() != len(self.columns):
            raise ValueError('Колонки строки фильтра не совпадают с колонками менеджера')
        if any(table.cellWidget(row, column) is not None
               or (table.item(row, column) is not None
                   and table.item(row, column).data(CQT.QtCore.Qt.CheckStateRole) is not None)
               for row in range(table.rowCount()) for column in range(table.columnCount())):
            raise ValueError('Серверный фильтр не поддерживает комбобоксы и чеклисты')
        self._dialog_ref = weakref.ref(dialog)
        self._dialog_error_handler = on_error
        self._locked_filter_columns = set()
        self._filter_apply_mode = None
        self._filter_enter_pending = False
        original_fill = dialog.fill_current_page

        def fill_current_page():
            if self._dialog() is not dialog:
                return False
            try:
                original_fill()
            except Exception as error:
                dialog.set_page()
                self.__show_dialog_error(error)
                return False
            self.last_error = None
            try:
                if not dialog.ui.tbl_summ.isHidden():
                    CQT.fill_summ_tbl(dialog, dialog.ui.tbl_summ, dialog.ui.tbl, hidden_scroll=True)
                if after_page is not None:
                    after_page(dialog, self)
            except Exception as error:
                self.__show_dialog_error(error)
            return True

        dialog.fill_current_page = fill_current_page
        tooltip = ('Фильтр по всем строкам: Enter - применить; Shift+Delete — очистить. '
                   '* любое значение '
                   '!* пустое значение '
                   '=, !=, >, >=, <, <= сравнение; '
                   '~  подстрока; '
                   '= точное значение. ')
        table.setToolTip(tooltip)
        self.__sync_filter_cells()
        timer = CQT.QtCore.QTimer(dialog)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self.__apply_dialog_filter() if self._dialog() is dialog else None)
        self._filter_timer = timer
        guard = CQT.QtCore.QObject(dialog)

        def queue_filter(mode):
            if self._dialog() is not dialog:
                return
            self._filter_apply_mode = mode
            self._filter_enter_pending = False
            timer.start(0)

        def editor_closed(editor, hint):
            if self._dialog() is dialog and self._filter_enter_pending:
                queue_filter('apply')

        def filter_event(watched, event):
            if self._dialog() is not dialog:
                return False
            event_type = event.type()
            if event_type == CQT.QtCore.QEvent.ChildAdded:
                event.child().installEventFilter(guard)
            if event_type not in (CQT.QtCore.QEvent.KeyPress, CQT.QtCore.QEvent.KeyRelease):
                return False
            key = event.key()
            clear = key == CQT.QtCore.Qt.Key_Delete and event.modifiers() == CQT.QtCore.Qt.ShiftModifier
            enter = key in (CQT.QtCore.Qt.Key_Return, CQT.QtCore.Qt.Key_Enter)
            if not clear and not enter:
                return False
            if event_type == CQT.QtCore.QEvent.KeyRelease:
                return True
            if clear:
                table.setFocus()
                queue_filter('clear')
                return True
            if table.state() == CQT.QtWidgets.QAbstractItemView.EditingState:
                self._filter_enter_pending = True
                return False
            queue_filter('apply')
            return True

        guard.eventFilter = filter_event
        table.installEventFilter(guard)
        for child in table.findChildren(CQT.QtCore.QObject):
            child.installEventFilter(guard)
        table.itemDelegate().closeEditor.connect(editor_closed)
        dialog._sql_page_filter_guard = guard
        dialog._sql_page_filter_editor_closed = editor_closed
        dialog_ref = self._dialog_ref

        def dialog_finished(result):
            timer.stop()
            if self._dialog_ref is dialog_ref:
                self._dialog_ref = None
                self._filter_enter_pending = False
                self._filter_apply_mode = None

        dialog.finished.connect(dialog_finished)
        if after_page is not None:
            try:
                after_page(dialog, self)
            except Exception as error:
                self.__show_dialog_error(error)


class OrmPageManager(SqlPageManager):
    """
    from project_cust_38.dynamic_db_models.orm_models import Nomen

    qs = Nomen.query().filter(На_удаление=0).order_by("Наименование", "Пномер")
    pm = OrmPageManager(qs, fields=("Пномер", "Код", "Наименование"), page_size=100)
    selected = CQT.msgboxg_get_table(
        window, "Номенклатура", None, page_manager=pm,
        decorate_dialog=pm.bind_dialog, selectRows=True, ExtendedSelection=False,
    )
    """

    def __init__(self, source, fields=None, page_size=100, order_by=None, column_types=None):
        if isinstance(source, type) and issubclass(source, ORM.BaseModel):
            source = source.query()
        self._base_queryset = source.clone()
        self._base_queryset._conditions = copy.deepcopy(self._base_queryset._conditions)
        self.model_cls = source.model_cls
        if isinstance(fields, str):
            fields = fields.split(',')
        columns = tuple(self.model_cls.__fields__) if fields is None else tuple(fields)
        if not columns:
            raise ValueError("Нужен хотя бы один столбец ORM.Field")
        for name in columns:
            if name not in self.model_cls.__fields__:
                raise ValueError(f"Используйте имя поля модели: {name}")
        key = self.model_cls.pk_name()
        if key not in columns:
            columns += (key,)
        original_order = source._orderings if order_by is None else order_by
        if isinstance(original_order, str):
            raise TypeError("order_by должен быть последовательностью полей")
        order = []
        for item in original_order:
            descending = item.startswith('-')
            name = item[1:] if descending else item
            if name == 'pk':
                name = key
            order.append(('-' if descending else '') + name)
        types = {name: self.model_cls.get_field(name).python_type for name in columns}
        types.update(column_types or {})
        self._base_queryset._orderings = []
        projection = ', '.join(self._quote(self.model_cls.get_field(name).db_column)
                               + ' AS ' + self._quote(name) for name in columns)
        query, params = self._base_queryset._build_select_sql(columns=projection)
        super().__init__(bd=source.db, query=query, columns=columns, key_column=key,
                         params=params, order_by=order, page_size=page_size,
                         column_types=types, attach_dbs=source.attach_dbs,
                         executor=source.executor)

    def __convert_value(self, column, value):
        field = self.model_cls.get_field(column)
        if isinstance(field, (ORM.JsonTextField, ORM.ListTextField)):
            return value
        serializer = getattr(self.model_cls, 'serialize_' + column, None)
        if callable(serializer) and not isinstance(value, str):
            return value
        return super().__convert_value(column, value)

    def __prepare_filter_value(self, column, value):
        return self.model_cls.prepare_db_value(column, value)

    def __build_query(self, count=False, offset=0):
        qs = self._base_queryset.clone()
        column_sql = lambda name: self._quote(self.model_cls.get_field(name).db_column)
        where, parameters = self._where_clause(column_sql)
        if where:
            qs = qs.where(where, parameters)
        projection = 'COUNT(*) AS "__page_count"' if count else ', '.join(
            column_sql(name) + ' AS ' + self._quote(name) for name in self.columns)
        sql, parameters = qs._build_select_sql(columns=projection, for_count=count)
        sql = sql.rstrip().removesuffix(';')
        if not count:
            sql += ' ORDER BY ' + self._order_clause(column_sql) + ' LIMIT ? OFFSET ?'
            parameters.extend((self.page_size, offset))
        return sql, parameters


if __name__ == '__main__':
    from PyQt5 import QtWidgets
    from project_cust_38.dynamic_db_models.orm_models import Nomen
    def show_sql_demo(window, search_code=""):
        pm = SqlPageManager(
            bd="SRV:DB_nomenklatura_erp.db",
            query='SELECT "Пномер", "Код", "Наименование", "П1" FROM "nomen" ',
            columns=("Пномер", "Код", "Наименование", "П1"),
            column_types={"Пномер": int, "Код": str, "Наименование": str, "П1": bool},
            key_column="Пномер",
            order_by=("Наименование", "Пномер"),
            page_size=100,
        )
        if search_code:
            pm.set_filter(Код__contains=search_code)
        return CQT.msgboxg_get_table(
            window,
            "SQL",
            None,
            WindowTitle="SQL",
            page_manager=pm,
            decorate_dialog=pm.bind_dialog,
            selectRows=True,
            ExtendedSelection=False,
            load_summ=False,
            show_filtr=True,
            sortingEnabled=False,
        )


    def show_orm_demo(window, search_code=""):
        qs = Nomen.query().filter(На_удаление=0).order_by("Наименование", "Пномер")
        pm = OrmPageManager(
            qs,
            fields=("Пномер", "Код", "Наименование", "П1"),
            page_size=100,
        )
        if search_code:
            pm.set_filter(Код__contains=search_code)
        return CQT.msgboxg_get_table(
            window,
            "ORM",
            None,
            WindowTitle="ORM",
            page_manager=pm,
            decorate_dialog=pm.bind_dialog,
            selectRows=True,
            ExtendedSelection=False,
            load_summ=False,
            show_filtr=True,
            sortingEnabled=False,
        )

    mode = 'sql'

    app = QtWidgets.QApplication([])
    window = QtWidgets.QMainWindow()
    if mode == "sql":
        show_sql_demo(window, "")
    if mode == "orm":
        show_orm_demo(window, "")
    window.show()
    app.exec()