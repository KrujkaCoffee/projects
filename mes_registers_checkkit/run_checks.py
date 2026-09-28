#!/usr/bin/env python3
"""Run offline regression tests. Exit 0 means expectations held, NOT migration approval."""
import argparse
import copy
import json
import platform
import sqlite3
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

from cases import A, B, base, targeted_cases, volume_case
from engine import (Sources, canonical, compare, create_fixture, digest,
                    run_case, test_models)


def comparator_checks():
    original = {"positions": ["A"], "selected_fios": ["P", "Q"],
                "raw_rows": [{"id": 1}, {"id": 2}], "rows": [{"id": 1}, {"id": 2}],
                "norms": {"P": 10, "Q": 20}, "source": "erp", "error": None}
    new = copy.deepcopy(original); new["source"] = "register"
    checks = []
    def verify(name, changed, expected):
        actual = compare(original, changed)["verdict"]
        if actual != expected: raise AssertionError((name, actual, expected))
        checks.append(name)
    verify("exact_outputs", new, "MATCH")
    c = copy.deepcopy(new); c["norms"] = {"P": 20, "Q": 10}
    verify("same_total_different_people", c, "DIFFERENT")
    c = copy.deepcopy(new); c["rows"].reverse()
    verify("same_rows_different_order", c, "DIFFERENT")
    c = copy.deepcopy(new); c["rows"].append(c["rows"][0])
    verify("row_multiplicity", c, "DIFFERENT")
    c = copy.deepcopy(new); c["rows"][0]["payload"] = "changed"
    verify("same_id_different_payload", c, "DIFFERENT")
    c = copy.deepcopy(new); c["selected_fios"].append("R")
    verify("new_employee_without_journal", c, "DIFFERENT")
    c = copy.deepcopy(new); c["positions"].append("B")
    verify("new_position_without_employees", c, "DIFFERENT")
    c = copy.deepcopy(new); c["source"] = "sql_fallback"
    verify("fallback_is_not_evidence", c, "INCONCLUSIVE")
    c = copy.deepcopy(new); c["error"] = {"type": "TestError"}
    verify("new_error_is_blocked", c, "BLOCKED")
    c = copy.deepcopy(new); c["positions"] *= 2
    verify("position_duplicates_are_diagnostic", c, "MATCH")
    c = copy.deepcopy(new); c["selected_fios"] = None
    verify("none_is_not_a_list", c, "DIFFERENT")
    c = copy.deepcopy(new); c["raw_rows"].append({"id": 3})
    verify("raw_unconfirmed_row_detected", c, "DIFFERENT")
    return checks


def native_checks(sources):
    checks = []
    with tempfile.TemporaryDirectory(prefix="mes_native_") as directory:
        paths = create_fixture(base(), directory)
        trace = []
        catalog = sources.native.get_mes_registers(models_module=test_models(),
            executor=sources.native.SqliteExecutor(paths, trace=trace), clock=lambda: "2026-06-30 12:00:00")
        assert [r["id"] for r in catalog.employee.all_current()] == [1, 2]
        checks.append("all_current_uses_frozen_clock")
        assert len(trace) == 2
        checks.append("one_date_guard_and_one_snapshot_query")
        assert catalog.employee.at("p1", "2024-12-31 23:59:59") is None
        checks.append("at_before_first_event")
        assert catalog.employee.at("p1", "2025-01-01 00:00:00")["id"] == 1
        checks.append("at_includes_exact_timestamp")
        assert len(catalog.employee.history("p1", from_="2025-01-01", to="2025-01-01")) == 1
        checks.append("history_inclusive_bounds")
        before = {k: Path(p).read_bytes() for k, p in paths.items()}
        catalog.employee.all_at("2026-06-30 12:00:00")
        assert all(Path(paths[k]).read_bytes() == data for k, data in before.items())
        checks.append("native_does_not_modify_sqlite_files")
        executor = sources.native.SqliteExecutor(paths)
        try:
            executor.fetch_all("BD_users", 'DELETE FROM "КадроваяИстория"')
        except sources.native.RegisterError:
            pass
        else:
            raise AssertionError("Native executor accepted mutation")
        checks.append("native_rejects_mutation")
        try:
            sources.native.SqliteExecutor({"BD_users": Path(directory)/"absent.db"}).fetch_all("BD_users", "SELECT 1")
        except sources.native.RegisterSourceUnavailable:
            pass
        else:
            raise AssertionError("Native executor accepted missing source")
        assert not (Path(directory)/"absent.db").exists()
        checks.append("missing_file_not_created")
        trace.clear()
        # Recommendation: one snapshot for a report run, reused for every month.
        frozen = catalog.employee.all_at("2026-06-30 12:00:00")
        for _ in range(12): assert len(frozen) == 2
        assert len(trace) == 2
        checks.append("reuse_snapshot_across_12_months")
    return checks


def summarize_case(sources, case, full, elapsed):
    errors = []
    actual, expected = full["comparison"]["verdict"], case["expected"]
    if actual != expected: errors.append(f"verdict: expected {expected}, got {actual}")
    if "expected_native_ids" in case and full["new"].get("register_ids") != case["expected_native_ids"]:
        errors.append("Native latest state IDs differ from independent expectation")
    golden = case.get("golden")
    if golden:
        old = full["old"]
        if old.get("error"):
            errors.append("Golden reference could not run")
        else:
            if sorted(r["Пномер"] for r in old["rows"]) != sorted(golden["row_ids"]):
                errors.append("Legacy row IDs differ from independent golden list")
            if canonical(old["norms"]) != canonical(golden["norms"]):
                errors.append("Legacy norms differ from independent golden values")
    if case["name"] == "01_base" and not full["old"].get("error"):
        by_id = {r["Пномер"]: r for r in full["old"]["rows"]}
        if by_id[1]["Номер_проекта"] != "OVERRIDE-1" or by_id[3]["Номер_проекта"] != "PROJECT-2":
            errors.append("Project CASE expression changed")
        if "ДАТАВРЕМЯ(" in full["old"].get("erp_query", ""):
            errors.append("ERP query acquired a date predicate; baseline semantics changed")
    compact = {"name": case["name"], "purpose": case["purpose"], "expected": expected,
               "expectation_passed": not errors, "errors": errors,
               "comparison": full["comparison"], "native_query_count": full["native_query_count"],
               "fixture_counts": {"people": len({r["ФизическоеЛицо_Key"] for r in case["history"]}),
                                  "history": len(case["history"]), "jurnal": len(case["tables"]["jurnal"])},
               "timing_seconds": {"fixture_and_comparison": elapsed,
                                  "old_function": full["old"]["elapsed_seconds"],
                                  "new_function": full["new"]["elapsed_seconds"],
                                  "new_positions": full["new"].get("positions_seconds")}}
    for side in ("old", "new"):
        compact[side + "_error"] = full[side].get("error")
    return compact


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", help="Directory with the four real project modules; otherwise bundled reference")
    parser.add_argument("--random-cases", type=int, default=100)
    parser.add_argument("--seed", type=int, default=73021)
    parser.add_argument("--stress-employees", type=int, default=5000, help="0 disables the large case")
    parser.add_argument("--stress-events", type=int, default=6)
    parser.add_argument("--stress-fragments", type=int, default=20)
    parser.add_argument("--out", default="check_results.json")
    parser.add_argument("--fixtures-dir", help="Optional: materialize all generated JSON fixtures")
    args = parser.parse_args()
    if args.random_cases < 0 or args.stress_employees < 0 or args.stress_events < 1 or args.stress_fragments < 1:
        parser.error("Counts must be nonnegative; events/fragments must be positive")
    sources = Sources(args.project)
    result = {"schema_version": 1, "suite_passed": False,
              "meaning": "Passing the suite confirms expected behavior, including intentional differences. It is not migration approval.",
              "environment": {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version},
              "source_hashes": sources.hashes, "cases": []}
    started = time.perf_counter()
    try:
        result["comparator_checks"] = comparator_checks()
        result["native_checks"] = native_checks(sources)
    except Exception as exc:
        result["infrastructure_error"] = {"type": type(exc).__name__, "message": str(exc)}
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise
    cases = targeted_cases()
    cases.extend(volume_case(seed=args.seed+i, employees=35+i%31, events=2+i%7,
                             fragments=4+i%17) for i in range(args.random_cases))
    if args.stress_employees:
        cases.append(volume_case(args.seed, args.stress_employees, args.stress_events,
                                 args.stress_fragments, name="stress_large"))
    fixtures_dir = Path(args.fixtures_dir) if args.fixtures_dir else None
    if fixtures_dir: fixtures_dir.mkdir(parents=True, exist_ok=True)
    for number, case in enumerate(cases, 1):
        t0 = time.perf_counter()
        if fixtures_dir:
            (fixtures_dir / (case["name"] + ".json")).write_text(json.dumps(case, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        with tempfile.TemporaryDirectory(prefix="mes_reg_") as directory:
            full = run_case(sources, case, directory)
        item = summarize_case(sources, case, full, time.perf_counter() - t0)
        result["cases"].append(item)
        print(f"{number:03}/{len(cases)} {'OK' if item['expectation_passed'] else 'FAIL'} "
              f"{case['name']}: {item['comparison']['verdict']}", flush=True)
        if item["errors"]:
            print("  " + "; ".join(item["errors"]), flush=True)
    result["elapsed_seconds"] = time.perf_counter() - started
    result["verdict_counts"] = dict(Counter(c["comparison"]["verdict"] for c in result["cases"]))
    result["expectation_failures"] = sum(not c["expectation_passed"] for c in result["cases"])
    result["suite_passed"] = not result["expectation_failures"]
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("suite_passed", "verdict_counts", "expectation_failures", "elapsed_seconds")}, ensure_ascii=False))
    return 0 if result["suite_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
