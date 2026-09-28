"""Differential harness for the real list_per_month_new_c and mes_registers.

Only function ASTs from Cust_* are loaded. Application imports and norm repair
are never executed. Native mes_registers.py runs unchanged, with its real SQL.
"""
from __future__ import annotations

import ast
import copy
import datetime as dt
import hashlib
import importlib.util
import json
import math
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path
from types import ModuleType, SimpleNamespace as NS


HERE = Path(__file__).resolve().parent


class UnsafeRepair(RuntimeError):
    pass


class MappingProblem(RuntimeError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                      separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def extract(path, names, namespace):
    tree = ast.parse(Path(path).read_text(encoding="utf-8-sig"))
    nodes = [copy.deepcopy(n) for n in tree.body
             if isinstance(n, ast.FunctionDef) and n.name in names]
    if {n.name for n in nodes} != set(names):
        raise RuntimeError(f"Source contract changed in {path}: {names}")
    for node in nodes:
        node.decorator_list = []
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)


class Sources:
    def __init__(self, root=None):
        self.root = Path(root) if root else HERE / "reference"
        self.hashes = {n: hashlib.sha256((self.root / n).read_bytes()).hexdigest()
                       for n in ("Cust_virbotka.py", "Cust_Functions.py",
                                 "Cust_SQLite.py", "mes_registers.py")}
        space = {"DT": dt.datetime}
        helpers = ["strtodate", "datetostr", "boolm", "valm", "is_numeric"]
        extract(self.root / "Cust_Functions.py", helpers, space)
        self.F = NS(**{n: space[n] for n in helpers})
        extract(self.root / "Cust_SQLite.py", ["prepare_list_to_tuple"], space)
        self.prepare_list_to_tuple = space["prepare_list_to_tuple"]
        path = self.root / "mes_registers.py"
        name = "_checked_mes_registers_" + self.hashes["mes_registers.py"][:12]
        if name not in sys.modules:
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module  # dataclasses resolve the module during import
            spec.loader.exec_module(module)
        self.native = sys.modules[name]
        tree = ast.parse((self.root / "Cust_virbotka.py").read_text(encoding="utf-8-sig"))
        self.original = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                             and n.name == "list_per_month_new_c")
        self.compiled = {candidate: self._compile(candidate) for candidate in (False, True)}

    def _compile(self, candidate):
        node = copy.deepcopy(self.original)
        inner = [n for n in node.body if isinstance(n, ast.FunctionDef)
                 and n.name == "get_filtr_dolgn"]
        if len(inner) != 1:
            raise RuntimeError("Expected exactly one nested get_filtr_dolgn")
        if candidate:
            inner[0].body = ast.parse("return _candidate(podrazdelenie, organization)").body
        # Observation points; original SQL and all calculations remain intact.
        watched = {"filtr_dolgn": "positions", "dict_employee": "employee_current",
                   "spis_jur": "raw_rows"}
        body, seen = [], set()
        for statement in node.body:
            body.append(statement)
            if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                target = statement.targets[0]
                if isinstance(target, ast.Name) and target.id in watched:
                    seen.add(target.id)
                    body.extend(ast.parse(f"_capture({watched[target.id]!r}, {target.id})").body)
        if seen != set(watched):
            raise RuntimeError(f"Source observation points changed: {seen}")
        node.body = body
        node.decorator_list = []
        return compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
                       str(self.root / "Cust_virbotka.py"), "exec")

    def run(self, request, gateway, employee_loader, api, candidate=None, tabel_m=None):
        audit = gateway.audit
        audit.setdefault("source", "unqueried")
        audit.setdefault("selected_fios", None)
        def capture(key, value):
            audit[key] = copy.deepcopy(value)
        def deny_repair(*args, **kwargs):
            raise UnsafeRepair("Non-numeric Подытог_нормы: original would write through Jurnal_nar")
        place = NS(Имя=request["company"], poki=request["poki"],
                   КодыНарядов=NS(НеподтвержденныйВнеплан=request["unconfirmed"]))
        namespace = {"F": self.F, "CSQ": gateway, "APIERP": api,
                     "CMS": NS(dict_emploee_full=employee_loader, Jurnal_nar=deny_repair),
                     "CQT": NS(msgbox=deny_repair), "USRCNF": NS(Config=NS(place=place)),
                     "_capture": capture, "_candidate": candidate}
        exec(self.compiled[candidate is not None], namespace)
        started = time.perf_counter()
        try:
            value = namespace["list_per_month_new_c"](
                gateway.db, request["nach"], request["konec"], gateway.db_kplan,
                gateway.db_users, request["podrazdelenie"], request["organization"], tabel_m)
            if not isinstance(value, tuple) or len(value) != 2:
                raise RuntimeError(f"Unexpected function return type: {type(value).__name__}")
            rows, norms = value
            if any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in norms.values()):
                raise ValueError("Non-finite or non-numeric norm; cannot certify equality")
            canonical(rows)
            audit.update(rows=copy.deepcopy(rows), norms=copy.deepcopy(norms), error=None)
        except Exception as exc:
            audit["error"] = {"type": type(exc).__name__, "message": str(exc)}
        audit["elapsed_seconds"] = time.perf_counter() - started
        return audit


HISTORY_FIELDS = ["id", "ФизическоеЛицо_Key", "Должность_Key", "Подразделение_Key",
                  "Период", "Организация_Key", "Событие", "Сотрудник_Key"]
WORK_FIELDS = ["Пномер", "Дата", "Штамп", "Номер_наряда", "ФИО", "Подытог",
               "Подытог_нормы", "Статус", "Примечание", "Ном_заверш", "Дата_выгрузки_ЕРП",
               "ФИО_выгрузки_ЕРП", "Минут_выгружено_ЕРП", "base_ERP"]


def test_models():
    """Bound field metadata for the actual catalog, not a register mock."""
    module = ModuleType("checkkit_models")
    definitions = [("EmployeeHistory", "BD_users", "КадроваяИстория", "id", HISTORY_FIELDS),
                   ("Competence", "BD_users", "competence_vals", "s_num",
                    ["s_num", "id_comp", "id_user", "value", "created_at"]),
                   ("WorkLog", "Naryad", "jurnal", "Пномер", WORK_FIELDS)]
    for name, db, table, pk, fields in definitions:
        model = type(name, (), {"__table__": table, "__db_key__": db,
                               "__table_key__": f"{db}.{table}", "__pk__": pk})
        for field in fields:
            setattr(model, field, NS(model=model, name=field, db_column=field))
        setattr(module, name, model)
    return module


def register_positions(rows, *, department, organization, dimensions, organization_refs,
                       exclude_events=()):
    """Explicit migration candidate, not a claim of equivalence to the ERP query.

    Keep dismissal events by default: the legacy positions query has no such
    predicate. Legacy dict_emploee_full still controls employee membership.
    """
    if organization not in organization_refs or not organization_refs[organization]:
        raise MappingProblem(f"No verified филиал -> Организация_Key mapping: {organization!r}")
    scope = set(organization_refs[organization])
    result = set()
    for row in rows:
        if row["Организация_Key"] not in scope:
            continue
        ref = row["Подразделение_Key"]
        if ref not in dimensions["departments"]:
            raise MappingProblem(f"Unknown Подразделение_Key: {ref!r}")
        if dimensions["departments"][ref] != department:
            continue
        if row["Событие"] in exclude_events:
            continue
        ref = row["Должность_Key"]
        if ref not in dimensions["positions"]:
            raise MappingProblem(f"Unknown Должность_Key: {ref!r}")
        value = dimensions["positions"][ref]
        if not isinstance(value, str):
            raise MappingProblem(f"Position has no string name: {ref!r}")
        result.add(value)
    return sorted(result)


class Candidate:
    def __init__(self, state_loader, request, dimensions, organization_refs, gateway,
                 *, empty_fallback=True, error_fallback=False, exclude_events=()):
        self.state_loader, self.request = state_loader, request
        self.dimensions, self.organization_refs, self.gateway = dimensions, organization_refs, gateway
        self.empty_fallback, self.error_fallback = empty_fallback, error_fallback
        self.exclude_events = exclude_events

    def __call__(self, department, organization):
        audit = self.gateway.audit
        if department is not None and organization is None:
            audit["source"] = "legacy_guard"
            return None  # preserves the existing no-FIO-filter behavior
        started = time.perf_counter()
        try:
            rows = self.state_loader(self.request["as_of"])
            audit["register_rows_count"] = len(rows)
            audit["register_snapshot_hash"] = digest(rows)
            audit["register_ids"] = [r["id"] for r in rows]
            positions = register_positions(rows, department=department, organization=organization,
                                           dimensions=self.dimensions, organization_refs=self.organization_refs,
                                           exclude_events=self.exclude_events)
            audit["source"] = "register"
        except Exception as exc:
            audit["register_error"] = {"type": type(exc).__name__, "message": str(exc)}
            if not self.error_fallback:
                raise
            positions = []
            audit["fallback_reason"] = "register_error"
        finally:
            audit["positions_seconds"] = time.perf_counter() - started
        if not positions and (self.empty_fallback or audit.get("fallback_reason")):
            audit.setdefault("fallback_reason", "empty_register")
            return self.gateway.custom_request_c(
                self.gateway.db,
                f'''SELECT "Должность" FROM dolgn_etap WHERE "Подразделение" = '{department}'
                    AND "Производство" = '{organization}';''', hat_c=False, one_column=True)
        return positions


class Api:
    def __init__(self, response, audit):
        self.response, self.audit = response, audit

    def get_wet_request(self, *, text):
        self.audit["erp_query"] = text
        self.audit["erp_calls"] = self.audit.get("erp_calls", 0) + 1
        if self.response.get("raise"):
            raise RuntimeError(self.response["raise"])
        status = self.response["status"]
        self.audit["source"] = "erp" if status == 200 and self.response.get("data") else "erp_empty_or_error"
        body = copy.deepcopy(self.response.get("body", {"data": self.response.get("data")}))
        return status, body


class Gateway:
    def __init__(self, sources, connections):
        self.sources, self.connections = sources, connections
        self.db, self.db_users, self.db_kplan = "Naryad", "BD_users", "DB_kplan"
        self.audit = {"queries": []}

    def prepare_list_to_tuple(self, values):
        self.audit["selected_fios"] = copy.deepcopy(values)
        return self.sources.prepare_list_to_tuple(values)

    def custom_request_c(self, db, query, **kwargs):
        if not isinstance(query, str) or not query.lstrip().upper().startswith("SELECT"):
            raise UnsafeRepair("Only original SELECT queries are allowed")
        self.audit["queries"].append(query)
        if "FROM dolgn_etap" in query:
            self.audit["source"] = "sql_fallback"
        rows = [dict(r) for r in self.connections[db].execute(query)]
        if kwargs.get("one_column"):
            return [next(iter(row.values())) for row in rows]
        if kwargs.get("rez_dict"):
            return rows
        raise RuntimeError("Unexpected CSQ result shape")


SCHEMAS = {
    "Naryad": {
        "jurnal": '"Пномер" INTEGER PRIMARY KEY, "Дата" TEXT, "ФИО" TEXT, "Подытог", "Номер_наряда" INTEGER, "Статус" TEXT, "Подытог_нормы"',
        "naryad": '"Пномер" INTEGER PRIMARY KEY, "Номер_мк" INTEGER, "Твремя", "Норма_времени", "Коэфф_сложности", "Внеплан" INTEGER, "Подтвержд_вып" INTEGER',
        "dolgn_etap": '"Должность" TEXT, "Подразделение" TEXT, "Производство" TEXT',
        "коды_веплана_для_наряда": '"code" INTEGER, "poki" INTEGER',
    },
    "DB_kplan": {
        "mk": '"Пномер" INTEGER PRIMARY KEY, "Номер_проекта" TEXT, "НомКплан" INTEGER',
        "plan": '"Пномер" INTEGER PRIMARY KEY',
        "пл_оуп": '"НомПл" INTEGER, "Пномер_ЗП" INTEGER',
        "знпр": '"s_num" INTEGER, "№проекта" TEXT',
    },
    "BD_users": {"КадроваяИстория": ', '.join('"'+f+'"'+(' INTEGER PRIMARY KEY' if f == 'id' else ' TEXT') for f in HISTORY_FIELDS)}
}


def quote_ident(value):
    return '"' + value.replace('"', '""') + '"'


def create_fixture(case, directory):
    paths = {db: Path(directory) / (db + ".db") for db in SCHEMAS}
    for db, tables in SCHEMAS.items():
        with sqlite3.connect(paths[db]) as conn:
            for table, definition in tables.items():
                conn.execute(f"CREATE TABLE {quote_ident(table)} ({definition})")
                rows = case["history"] if table == "КадроваяИстория" else case["tables"].get(table, [])
                if rows:
                    columns = list(rows[0])
                    sql = f"INSERT INTO {quote_ident(table)} ({','.join(map(quote_ident, columns))}) VALUES ({','.join('?' for _ in columns)})"
                    conn.executemany(sql, ([r.get(c) for c in columns] for r in rows))
            if db == "BD_users":
                name = dt.datetime.strptime(case["request"]["nach"], "%Y-%m-%d %H:%M:%S").strftime("mtdz_%Y_%m_%d")
                conn.execute(f'CREATE TABLE {quote_ident(name)} ("ФИО" TEXT)')
                conn.executemany(f'INSERT INTO {quote_ident(name)} VALUES (?)', [(s,) for s in case["tabel"]])
    return paths


def open_connections(paths):
    connections = {}
    for db, path in paths.items():
        conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        if db == "Naryad":
            conn.execute("ATTACH DATABASE ? AS kplan", (paths["DB_kplan"].resolve().as_uri() + "?mode=ro",))
        connections[db] = conn
    return connections


def run_case(sources, case, directory):
    paths = create_fixture(case, directory)
    connections = open_connections(paths)
    trace = []
    catalog = sources.native.get_mes_registers(models_module=test_models(),
                  executor=sources.native.SqliteExecutor(paths, trace=trace))
    tabel_m = None if case.get("tabel_mode") == "db" else [[], [], []] + [[i, s] for i, s in enumerate(case["tabel"])]
    outputs = []
    try:
        for new in (False, True):
            gateway = Gateway(sources, connections)
            candidate = Candidate(catalog.employee.all_at, case["request"], case["dimensions"],
                                  case["organization_refs"], gateway, **case.get("policy", {})) if new else None
            outputs.append(sources.run(case["request"], gateway,
                           lambda db: copy.deepcopy(case["employee_current"]),
                           Api(case["erp"], gateway.audit), candidate=candidate, tabel_m=tabel_m))
        return {"name": case["name"], "request": case["request"], "old": outputs[0],
                "new": outputs[1], "comparison": compare(*outputs),
                "native_query_count": len(trace), "native_queries": trace}
    finally:
        for conn in connections.values():
            conn.close()


def unique(values):
    if values is None:
        return None
    return sorted({canonical(v) for v in values})


def difference(left, right, limit=20):
    a, b = Counter(map(canonical, left)), Counter(map(canonical, right))
    def sample(counter):
        return [{"value": json.loads(k), "count": v} for k, v in list(counter.items())[:limit]]
    return {"old_only_count": sum((a-b).values()), "new_only_count": sum((b-a).values()),
            "old_only": sample(a-b), "new_only": sample(b-a)}


def compare(old, new):
    if old.get("error") or new.get("error"):
        return {"verdict": "BLOCKED", "old_error": old.get("error"), "new_error": new.get("error")}
    checks = {
        "positions_set": unique(old.get("positions")) == unique(new.get("positions")),
        "selected_fios_set": unique(old.get("selected_fios")) == unique(new.get("selected_fios")),
        "raw_rows_bag": Counter(map(canonical, old["raw_rows"])) == Counter(map(canonical, new["raw_rows"])),
        "returned_rows_bag": Counter(map(canonical, old["rows"])) == Counter(map(canonical, new["rows"])),
        "returned_rows_order": canonical(old["rows"]) == canonical(new["rows"]),
        "norms_by_fio": canonical(old["norms"]) == canonical(new["norms"]),
    }
    verdict = "DIFFERENT" if not all(checks.values()) else "MATCH"
    if verdict == "MATCH" and (old.get("source") != "erp" or new.get("source") != "register"):
        verdict = "INCONCLUSIVE"  # matching fallback does not test source replacement
    result = {"verdict": verdict, "checks": checks,
              "sources": {"old": old.get("source"), "new": new.get("source")},
              "diagnostic_positions_sequence_equal": old.get("positions") == new.get("positions"),
              "counts": {side: {"positions": len(out.get("positions") or []),
                                  "selected_fios": len(unique(out.get("selected_fios")) or []),
                                  "raw_rows": len(out["raw_rows"]), "returned_rows": len(out["rows"]),
                                  "norms_fio": len(out["norms"])} for side, out in (("old", old), ("new", new))}}
    for field in ("positions", "selected_fios", "raw_rows", "rows"):
        if canonical(old.get(field)) != canonical(new.get(field)):
            result[field + "_diff"] = difference(old.get(field) or [], new.get(field) or [])
    if not checks["norms_by_fio"]:
        keys = sorted(set(old["norms"]) | set(new["norms"]))
        changed = [k for k in keys if canonical(old["norms"].get(k)) != canonical(new["norms"].get(k))]
        result["norm_diff_count"] = len(changed)
        result["norm_diff"] = [{"fio": k, "old": old["norms"].get(k), "new": new["norms"].get(k)} for k in changed[:20]]
    return result


def stability_view(outcome):
    fields = ("positions", "selected_fios", "employee_current", "raw_rows", "rows", "norms",
              "error", "source", "register_snapshot_hash")
    return {key: outcome.get(key) for key in fields}
