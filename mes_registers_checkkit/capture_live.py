"""Run from an ALREADY INITIALIZED MES Python console; no application imports here.

Reads the legacy ERP endpoint, MES SELECTs and employee.all_at. Norm-repair
calls are blocked by engine.Sources. Results are files; no business writes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import inspect
import json
import math
import time
from pathlib import Path

from engine import (Candidate, Gateway, MappingProblem, Sources, compare, digest,
                    stability_view)


class LiveGateway(Gateway):
    def __init__(self, sources, csq, db, db_users, db_kplan):
        super().__init__(sources, {})
        self.csq, self.db, self.db_users, self.db_kplan = csq, db, db_users, db_kplan

    def custom_request_c(self, db, query, **kwargs):
        if not isinstance(query, str) or not query.lstrip().upper().startswith("SELECT"):
            raise RuntimeError("Capture only accepts SELECT")
        self.audit["queries"].append(query)
        if "FROM dolgn_etap" in query: self.audit["source"] = "sql_fallback"
        return self.csq.custom_request_c(db, query, **kwargs)


class LiveApi:
    def __init__(self, api, audit):
        self.api, self.audit = api, audit

    def get_wet_request(self, *, text):
        self.audit["erp_query"] = text
        self.audit["erp_calls"] = self.audit.get("erp_calls", 0) + 1
        started = time.perf_counter()
        try:
            result = self.api.get_wet_request(text=text)
            status, body = result
            self.audit["erp_status"] = status
            self.audit["source"] = "erp" if status == 200 and isinstance(body, dict) and body.get("data") else "erp_empty_or_error"
            return result
        finally:
            self.audit["positions_seconds"] = time.perf_counter() - started


def checked_map(rows, key, value):
    if not isinstance(rows, list):
        raise MappingProblem(f"Expected list of dictionaries for {key}; got {type(rows).__name__}")
    mapping = {}
    for row in rows:
        ref, title = row[key], row[value]
        if ref in mapping and mapping[ref] != title:
            raise MappingProblem(f"Conflicting dimension names for {key}={ref!r}")
        mapping[ref] = title
    return mapping


def read_dimensions(csq, db_users):
    positions = csq.custom_request_c(db_users, 'SELECT "Ref_Key", "Наименование" FROM "Должности";', rez_dict=True)
    departments = csq.custom_request_c(db_users, 'SELECT "Подразделение_Key", "Наименование" FROM "Подразделения";', rez_dict=True)
    return {"positions": checked_map(positions, "Ref_Key", "Наименование"),
            "departments": checked_map(departments, "Подразделение_Key", "Наименование")}


def json_safe(value):
    """Keep invalid values visible in blocked outcomes instead of emitting JSON NaN."""
    if isinstance(value, float) and not math.isfinite(value):
        return {"__nonfinite_float__": str(value)}
    if isinstance(value, dict): return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)): return [json_safe(v) for v in value]
    if isinstance(value, (dt.datetime, dt.date)): return {"__datetime__": value.isoformat()}
    if value is None or isinstance(value, (str, int, float, bool)): return value
    return {"__unsupported_type__": type(value).__name__, "repr": repr(value)}


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(value), ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def capture_one(*, vir, registers, db, db_users, db_kplan, podrazdelenie,
                organization, organization_refs, nach, konec, out_file,
                as_of=None, sources=None):
    """Four reads: OLD -> NEW -> OLD -> NEW; final verdict checks repeat stability.

    organization_refs is an explicit verified list of Организация_Key values
    corresponding to the legacy Филиал.Наименование, not an inferred mapping.
    Current Config.place supplies company/poki/unconfirmed exactly as before.
    """
    if not isinstance(organization_refs, (list, tuple)) or not organization_refs:
        raise ValueError("organization_refs must be a nonempty verified list")
    sources = sources or Sources(Path(inspect.getsourcefile(vir)).parent)
    place = vir.USRCNF.Config.place
    request = {"nach": nach, "konec": konec, "as_of": as_of or dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
               "organization": organization, "podrazdelenie": podrazdelenie,
               "company": place.Имя, "poki": place.poki,
               "unconfirmed": place.КодыНарядов.НеподтвержденныйВнеплан}
    output = {"schema_version": 1, "mode": "live_differential_capture", "request": request,
              "source_hashes": sources.hashes, "organization_refs": list(organization_refs),
              "started_at": dt.datetime.now().isoformat(), "runs": []}
    for side in ("old", "new", "old", "new"):
        gateway = LiveGateway(sources, vir.CSQ, db, db_users, db_kplan)
        candidate = None
        if side == "new":
            try:
                dimensions = read_dimensions(vir.CSQ, db_users)
                gateway.audit["dimensions_hash"] = digest(dimensions)
                candidate = Candidate(registers.employee.all_at, request, dimensions,
                                      {organization: organization_refs}, gateway)
            except Exception as exc:
                output["runs"].append({"side": side, "source": "register", "error": {
                    "type": type(exc).__name__, "message": str(exc)}})
                continue
        run = sources.run(request, gateway, vir.CMS.dict_emploee_full,
                          LiveApi(vir.APIERP, gateway.audit), candidate=candidate)
        run["side"] = side
        output["runs"].append(run)
    output["comparison"] = assess_capture(output)
    output["finished_at"] = dt.datetime.now().isoformat()
    write_json(out_file, output)
    return output


def assess_capture(output):
    runs = output["runs"]
    if len(runs) != 4 or [r["side"] for r in runs] != ["old", "new", "old", "new"]:
        raise ValueError("Expected OLD -> NEW -> OLD -> NEW capture")
    if any(r.get("error") for r in runs):
        return {"verdict": "BLOCKED", "errors": [{"run": i, "side": r["side"], "error": r["error"]}
                                                  for i, r in enumerate(runs) if r.get("error")]}
    stable_old = digest(stability_view(runs[0])) == digest(stability_view(runs[2]))
    stable_new = (digest(stability_view(runs[1])) == digest(stability_view(runs[3])) and
                  runs[1].get("dimensions_hash") == runs[3].get("dimensions_hash"))
    first, second = compare(runs[0], runs[1]), compare(runs[2], runs[3])
    verdict = first["verdict"]
    if not stable_old or not stable_new or first["verdict"] != second["verdict"]:
        verdict = "UNSTABLE"
    return {"verdict": verdict, "stable_old": stable_old, "stable_new": stable_new,
            "first_comparison": first, "second_comparison": second,
            "meaning": "Stable equality is evidence for these calls and data, not a distributed transactional snapshot or a universal proof."}


def month_bounds(month):
    begin = dt.datetime.strptime(month, "%Y-%m").replace(hour=5)
    end_month = begin.replace(year=begin.year+1, month=1) if begin.month == 12 else begin.replace(month=begin.month+1)
    return begin.strftime("%Y-%m-%d %H:%M:%S"), (end_month-dt.timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")


def capture_matrix(*, vir, registers, db, db_users, db_kplan, podrazdeleniya,
                   organization, organization_refs, months, out_dir, as_of=None):
    """Read all (department, month) pairs for the current Config.place.

    Repeated live reads are deliberately uncached for stability diagnosis.
    They are not a performance benchmark for a cached production implementation.
    """
    folder = Path(out_dir)
    folder.mkdir(parents=True, exist_ok=True)
    sources = Sources(Path(inspect.getsourcefile(vir)).parent)
    as_of = as_of or dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    index = {"schema_version": 1, "as_of": as_of, "cases": []}
    for dep_i, department in enumerate(podrazdeleniya, 1):
        for month in months:
            path = folder / f"dep_{dep_i:03}_{month}.json"
            nach, konec = month_bounds(month)
            out = capture_one(vir=vir, registers=registers, db=db, db_users=db_users, db_kplan=db_kplan,
                podrazdelenie=department, organization=organization, organization_refs=organization_refs,
                nach=nach, konec=konec, out_file=path, as_of=as_of, sources=sources)
            index["cases"].append({"department": department, "month": month,
                                   "file": path.name, "verdict": out["comparison"]["verdict"]})
            write_json(folder / "index.json", index)
            print(month, department, out["comparison"]["verdict"], flush=True)
    index["all_cases_matched"] = bool(index["cases"]) and all(c["verdict"] == "MATCH" for c in index["cases"])
    write_json(folder / "index.json", index)
    return index


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-assess a saved capture without ERP/MES access")
    parser.add_argument("capture", help="One dep_XXX_YYYY-MM.json, not index.json")
    args = parser.parse_args()
    data = json.loads(Path(args.capture).read_text(encoding="utf-8"))
    result = assess_capture(data)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["verdict"] == "MATCH" else 2)
