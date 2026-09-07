from __future__ import annotations

import csv
import json
import pathlib
import traceback
from typing import Iterable

import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_client_socket as CSQS
import project_cust_38.srv_sql_cache as SQLCACHE
from project_cust_38 import Cust_config as CFG


SQL_EVENTS_TABLE = "SqlEvents"
OUTPUT_CSV = pathlib.Path(r"C:\Users\A.A.Fedorov\MES\ideal_context\arm_ww\sql_table_extraction_audit.csv")
OUTPUT_JSON = pathlib.Path(r"C:\Users\A.A.Fedorov\MES\ideal_context\arm_ww\sql_table_extraction_audit.json")


COMMON_ATTACH_DBS = (
    "SRV:Naryad.db",
    "SRV:BD_dse.db",
    "SRV:BD_resxml.db",
    "SRV:BD_files.db",
    "SRV:DB_kplan.db",
    "SRV:BD_users.db",
    "SRV:DB_nomenklatura_erp.db",
    "SRV:DB_invest.db",
    "SRV:DB_xl_formulas.db",
    "SRV:db_flet.db",
)


def _normalize_text_list(values: Iterable[str] | None) -> list[str]:
    result: list[str] = []
    seen = set()
    for value in values or ():
        text = str(value or "").strip()
        if not text:
            continue
        if text not in seen:
            seen.add(text)
            result.append(text)
    return result



def _table_name_only(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if "." in text:
        return text.split(".")[-1].strip()
    return text



def _split_logged_used_tables(raw: str | None) -> list[str]:
    if raw in (None, ""):
        return []
    return _normalize_text_list([item for item in str(raw).split(";") if str(item).strip()])



def _resolved_main_db_name(db_name: str) -> str:
    text = str(db_name or "").strip()
    if not text:
        return text
    # В SqlEvents обычно хранится путь/алиас из аргумента bd
    # Если это уже SRV:..., оставляем.
    if text.startswith("SRV:"):
        return text
    # Если это просто имя файла БД.
    if text.endswith(".db"):
        return f"SRV:{pathlib.Path(text).name}"
    return text



def _build_attached_alias_paths(attach_dbs: Iterable[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in attach_dbs:
        try:
            db_path, _ = CSQS.db_path(item)
            alias = pathlib.Path(db_path).stem
            mapping[alias] = db_path
        except Exception:
            continue
    return mapping



def _attach_list_for_db(main_db: str) -> tuple[str, ...]:
    main_text = str(main_db or "")
    result = []
    for item in COMMON_ATTACH_DBS:
        if main_text.endswith(item.split("SRV:")[-1]):
            continue
        result.append(item)
    return tuple(result)



def get_distinct_queries(limit: int | None = None) -> list[dict]:
    db_files = CFG.Config.project.db_files
    limit_sql = f" LIMIT {int(limit)}" if limit else ""
    query = f"""
        SELECT DISTINCT query, db_name, used_tables
        FROM {SQL_EVENTS_TABLE}
        WHERE query IS NOT NULL AND TRIM(query) != ''
        ORDER BY LENGTH(query) DESC{limit_sql}
    """
    rows = CSQ.custom_request_c(db_files, query, rez_dict=True) or []
    return rows



def explain_used_tables(main_db: str, sql_text: str, attach_dbs: Iterable[str]) -> tuple[list[str], str | None]:
    try:
        explain_sql = f"EXPLAIN QUERY PLAN {sql_text}"
        rows = CSQ.custom_request_c(
            main_db,
            explain_sql,
            attach_dbs=tuple(attach_dbs),
        )
        if not isinstance(rows, (list, tuple, set)):
            return [], f"unexpected explain result type: {type(rows).__name__}"
        return _normalize_text_list(rows), None
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"



def regex_used_tables(main_db: str, sql_text: str, attach_dbs: Iterable[str]) -> list[str]:
    attached_alias_paths = _build_attached_alias_paths(attach_dbs)
    main_db_path = main_db
    if isinstance(main_db, str) and main_db.startswith("SRV:"):
        try:
            main_db_path, _ = CSQS.db_path(main_db)
        except Exception:
            main_db_path = main_db
    records = SQLCACHE.extract_query_table_records(
        sql_text=sql_text,
        main_db_path=main_db_path,
        attached_alias_paths=attached_alias_paths,
    )
    names = [_table_name_only(item.get("table_name") or item.get("table_key") or "") for item in records]
    return _normalize_text_list(names)



def audit_queries(limit: int | None = None) -> list[dict]:
    rows = get_distinct_queries(limit=limit)
    report: list[dict] = []

    for idx, row in enumerate(rows, start=1):
        sql_text = str(row.get("query") or "").strip()
        db_name = _resolved_main_db_name(str(row.get("db_name") or "").strip())
        attach_dbs = _attach_list_for_db(db_name)

        logged_used = [_table_name_only(x) for x in _split_logged_used_tables(row.get("used_tables"))]
        logged_used = _normalize_text_list(logged_used)

        explain_tables, explain_error = explain_used_tables(db_name, sql_text, attach_dbs)
        explain_tables = _normalize_text_list([_table_name_only(x) for x in explain_tables])

        regex_tables = regex_used_tables(db_name, sql_text, attach_dbs)

        explain_set = set(explain_tables)
        regex_set = set(regex_tables)
        logged_set = set(logged_used)

        item = {
            "idx": idx,
            "db_name": db_name,
            "query": sql_text,
            "logged_used_tables": logged_used,
            "explain_tables": explain_tables,
            "regex_tables": regex_tables,
            "missing_in_regex_vs_explain": sorted(explain_set - regex_set),
            "extra_in_regex_vs_explain": sorted(regex_set - explain_set),
            "missing_in_regex_vs_logged": sorted(logged_set - regex_set),
            "extra_in_regex_vs_logged": sorted(regex_set - logged_set),
            "explain_error": explain_error,
            "attach_dbs": list(attach_dbs),
        }
        report.append(item)

    return report



def save_report(report: list[dict]) -> None:
    OUTPUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as desc:
        writer = csv.DictWriter(
            desc,
            fieldnames=[
                "idx",
                "db_name",
                "explain_error",
                "logged_used_tables",
                "explain_tables",
                "regex_tables",
                "missing_in_regex_vs_explain",
                "extra_in_regex_vs_explain",
                "missing_in_regex_vs_logged",
                "extra_in_regex_vs_logged",
                "query",
            ],
            delimiter=";",
        )
        writer.writeheader()
        for item in report:
            writer.writerow(
                {
                    "idx": item["idx"],
                    "db_name": item["db_name"],
                    "explain_error": item["explain_error"] or "",
                    "logged_used_tables": ", ".join(item["logged_used_tables"]),
                    "explain_tables": ", ".join(item["explain_tables"]),
                    "regex_tables": ", ".join(item["regex_tables"]),
                    "missing_in_regex_vs_explain": ", ".join(item["missing_in_regex_vs_explain"]),
                    "extra_in_regex_vs_explain": ", ".join(item["extra_in_regex_vs_explain"]),
                    "missing_in_regex_vs_logged": ", ".join(item["missing_in_regex_vs_logged"]),
                    "extra_in_regex_vs_logged": ", ".join(item["extra_in_regex_vs_logged"]),
                    "query": item["query"],
                }
            )



def print_summary(report: list[dict]) -> None:
    total = len(report)
    explain_failed = sum(1 for item in report if item["explain_error"])
    exact_explain = sum(1 for item in report if not item["explain_error"] and not item["missing_in_regex_vs_explain"] and not item["extra_in_regex_vs_explain"])
    exact_logged = sum(1 for item in report if not item["missing_in_regex_vs_logged"] and not item["extra_in_regex_vs_logged"])
    mismatch = [
        item for item in report
        if item["missing_in_regex_vs_explain"] or item["extra_in_regex_vs_explain"]
    ]

    print(f"Всего distinct query: {total}")
    print(f"EXPLAIN не выполнился: {explain_failed}")
    print(f"Совпали regex vs EXPLAIN: {exact_explain}")
    print(f"Совпали regex vs logged used_tables: {exact_logged}")
    print(f"Расхождения regex vs EXPLAIN: {len(mismatch)}")

    if mismatch:
        print("\nПервые 10 расхождений:")
        for item in mismatch[:10]:
            print("=" * 80)
            print(f"idx={item['idx']} db={item['db_name']}")
            print(f"missing_in_regex_vs_explain={item['missing_in_regex_vs_explain']}")
            print(f"extra_in_regex_vs_explain={item['extra_in_regex_vs_explain']}")
            print(item['query'])



def main(limit: int | None = None) -> int:
    try:
        report = audit_queries(limit=limit)
        save_report(report)
        print_summary(report)
        print(f"\nCSV:  {OUTPUT_CSV}")
        print(f"JSON: {OUTPUT_JSON}")
        return 0
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main(limit=None))
