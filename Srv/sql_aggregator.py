"""
Примеры:
  python sqlevents_rollup_monthly.py --db C:\DB_srv\BD_files.db --keep-months 2 --chunk 50000
  python sqlevents_rollup_monthly.py --db C:\DB_srv\BD_files.db --keep-months 2 --archive-dir .\SqlEventsArchive

Ожидание лока:
  --busy-ms 600000         (busy_timeout SQLite, мс)
  --lock-wait-s 0          (0 = ждать бесконечно на уровне retry-loop)
  --lock-sleep 0.25        (стартовая пауза)
  --lock-sleep-max 5.0     (макс пауза)
"""

from __future__ import annotations

import argparse
import sqlite3
import time
from pathlib import Path
from datetime import datetime, date


DT_CANDIDATES = ("dt", "event_dt", "created_at", "created", "ts", "timestamp", "time", "date")



def _is_lock_error(e: Exception) -> bool:
    if not isinstance(e, sqlite3.OperationalError):
        return False
    msg = str(e).lower()
    return ("database is locked" in msg) or ("database is busy" in msg) or ("locked" in msg)


def run_with_lock_wait(
    fn,
    *,
    wait_s: int,
    sleep0: float,
    sleep_max: float,
):
    """
    wait_s = 0 -> ждать бесконечно
    """
    start = time.time()
    delay = max(0.01, float(sleep0))

    while True:
        try:
            return fn()
        except Exception as e:
            if not _is_lock_error(e):
                raise
            if wait_s and (time.time() - start) >= wait_s:
                raise
            time.sleep(delay)
            delay = min(float(sleep_max), delay * 1.5)



def detect_dt_column(conn: sqlite3.Connection, table: str) -> str | None:
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    low = {c.lower(): c for c in cols}
    for k in DT_CANDIDATES:
        if k in low:
            return low[k]
    for c in cols:
        cl = c.lower()
        if any(x in cl for x in ("dt", "date", "time", "ts")):
            return c
    return None


def detect_dt_mode(conn: sqlite3.Connection, table: str, dt_col: str) -> str:
    """
      - iso_text: текстовые ISO-строки (YYYY-MM-DD....) => сравниваем строками по префиксу
      - unix_epoch: integer/real epoch seconds => сравниваем числами
      - text: другой текст (всё равно попробуем iso_text-стратегию по префиксу)
    """
    row = conn.execute(
        f"SELECT typeof({dt_col}) AS t, {dt_col} AS v "
        f"FROM {table} WHERE {dt_col} IS NOT NULL LIMIT 1"
    ).fetchone()
    if not row:
        return "iso_text"
    t = str(row[0]).lower()
    v = row[1]
    if t in ("integer", "real"):
        return "unix_epoch"
    if isinstance(v, str) and len(v) >= 10 and v[4] == "-" and v[7] == "-":
        return "iso_text"
    return "text"


def month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def add_month(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    return date(y, m, 1)


def iso_day(d: date) -> str:
    return d.isoformat()


def epoch_day(d: date) -> int:
    return int(datetime(d.year, d.month, d.day, 0, 0, 0).timestamp())


def parse_any_datetime(x) -> datetime:
    if x is None:
        raise ValueError("empty datetime")
    s = str(x).strip()
    if s == "":
        raise ValueError("empty datetime")
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        try:
            return datetime.fromtimestamp(float(s))
        except Exception:
            raise ValueError(f"Не смог распарсить дату/время: {x!r}")


def compute_month_range(conn: sqlite3.Connection, table: str, dt_col: str, dt_mode: str) -> tuple[date, date] | None:
    row = conn.execute(f"SELECT MIN({dt_col}), MAX({dt_col}) FROM {table}").fetchone()
    if not row or row[0] is None or row[1] is None:
        return None

    if dt_mode == "unix_epoch":
        dmin = month_start(datetime.fromtimestamp(float(row[0])).date())
        dmax = month_start(datetime.fromtimestamp(float(row[1])).date())
        return dmin, dmax

    dmin = month_start(parse_any_datetime(row[0]).date())
    dmax = month_start(parse_any_datetime(row[1]).date())
    return dmin, dmax



def ensure_agg_tables(conn: sqlite3.Connection):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS SqlEventsAggMonth(
        ym TEXT NOT NULL,             -- 'YYYY-MM'
        app TEXT NOT NULL,
        db_name TEXT NOT NULL,
        query_kind TEXT NOT NULL,     -- SELECT/INSERT/UPDATE/DELETE/WITH/OTHER
        calls INTEGER NOT NULL,
        total_time REAL NOT NULL,     -- сумма времени
        max_time REAL NOT NULL,
        total_bytes INTEGER NOT NULL,
        PRIMARY KEY (ym, app, db_name, query_kind)
    );
    """)


def ensure_index_dt(conn: sqlite3.Connection, table: str, dt_col: str):
    idx_name = f"idx_{table.lower()}_{dt_col.lower()}"
    conn.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({dt_col});")


def ensure_archive_schema(conn_main: sqlite3.Connection, archive_path: Path):
    """
    Создаёт архивную БД и таблицу SqlEvents по исходному CREATE TABLE.
    """
    sql = conn_main.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='SqlEvents'"
    ).fetchone()
    if not sql or not sql[0]:
        raise RuntimeError("Не нашёл CREATE TABLE SqlEvents в sqlite_master.")
    create_sql = sql[0]

    conn_arch = sqlite3.connect(str(archive_path))
    try:
        conn_arch.execute("PRAGMA foreign_keys=OFF;")
        conn_arch.execute(create_sql)
        conn_arch.commit()
    finally:
        conn_arch.close()



def kind_sql_expr(query_col: str = "query") -> str:
    q = f"ltrim({query_col})"
    return f"""
    CASE
      WHEN upper({q}) LIKE 'SELECT%' THEN 'SELECT'
      WHEN upper({q}) LIKE 'INSERT%' THEN 'INSERT'
      WHEN upper({q}) LIKE 'UPDATE%' THEN 'UPDATE'
      WHEN upper({q}) LIKE 'DELETE%' THEN 'DELETE'
      WHEN upper({q}) LIKE 'WITH%'   THEN 'WITH'
      ELSE 'OTHER'
    END
    """


def ym_expr_for_mode(dt_col: str, dt_mode: str) -> str:
    if dt_mode == "unix_epoch":
        return f"strftime('%Y-%m', {dt_col}, 'unixepoch')"
    return f"strftime('%Y-%m', {dt_col})"


def rollup_one_month(conn: sqlite3.Connection, dt_col: str, dt_mode: str, ym: str, start_bound, end_bound):
    conn.execute("DELETE FROM SqlEventsAggMonth WHERE ym = ?", (ym,))
    kexpr = kind_sql_expr("query")
    ym_expr = ym_expr_for_mode(dt_col, dt_mode)

    conn.execute(f"""
    INSERT INTO SqlEventsAggMonth(ym, app, db_name, query_kind, calls, total_time, max_time, total_bytes)
    SELECT
      {ym_expr} AS ym,
      app,
      db_name,
      {kexpr} AS query_kind,
      COUNT(*) AS calls,
      COALESCE(SUM(completion_time), 0.0) AS total_time,
      COALESCE(MAX(completion_time), 0.0) AS max_time,
      COALESCE(SUM(size), 0) AS total_bytes
    FROM SqlEvents
    WHERE {dt_col} >= ? AND {dt_col} < ?
    GROUP BY ym, app, db_name, query_kind
    """, (start_bound, end_bound))


def move_or_delete_month_batched(
    conn: sqlite3.Connection,
    dt_col: str,
    start_bound,
    end_bound,
    *,
    chunk: int,
    archive_path: Path | None,
    lock_wait_s: int,
    lock_sleep: float,
    lock_sleep_max: float,
):
    run_with_lock_wait(
        lambda: conn.execute("CREATE TEMP TABLE IF NOT EXISTS _move_rids(rid INTEGER PRIMARY KEY);"),
        wait_s=lock_wait_s, sleep0=lock_sleep, sleep_max=lock_sleep_max,
    )

    if archive_path:
        ensure_archive_schema(conn, archive_path)
        run_with_lock_wait(
            lambda: conn.execute("ATTACH DATABASE ? AS arch", (str(archive_path),)),
            wait_s=lock_wait_s, sleep0=lock_sleep, sleep_max=lock_sleep_max,
        )

    moved_total = 0

    while True:
        def _one_chunk() -> int:
            conn.execute("BEGIN IMMEDIATE;")
            try:
                conn.execute("DELETE FROM _move_rids;")
                conn.execute(
                    f"INSERT INTO _move_rids(rid) "
                    f"SELECT rowid FROM SqlEvents "
                    f"WHERE {dt_col} >= ? AND {dt_col} < ? "
                    f"LIMIT ?;",
                    (start_bound, end_bound, chunk),
                )
                n = conn.execute("SELECT COUNT(*) FROM _move_rids;").fetchone()[0]
                if n == 0:
                    conn.execute("COMMIT;")
                    return 0

                if archive_path:
                    conn.execute(
                        "INSERT INTO arch.SqlEvents "
                        "SELECT * FROM main.SqlEvents "
                        "WHERE rowid IN (SELECT rid FROM _move_rids);"
                    )

                conn.execute("DELETE FROM SqlEvents WHERE rowid IN (SELECT rid FROM _move_rids);")
                conn.execute("COMMIT;")
                return int(n)
            except Exception:
                conn.execute("ROLLBACK;")
                raise

        n = run_with_lock_wait(
            _one_chunk,
            wait_s=lock_wait_s, sleep0=lock_sleep, sleep_max=lock_sleep_max,
        )
        if n == 0:
            break
        moved_total += n

    if archive_path:
        run_with_lock_wait(
            lambda: conn.execute("DETACH DATABASE arch"),
            wait_s=lock_wait_s, sleep0=lock_sleep, sleep_max=lock_sleep_max,
        )

    return moved_total


def main():
    ap = argparse.ArgumentParser(description="Monthly rollup + gentle cleanup for SqlEvents (lock-wait enabled)")
    ap.add_argument("--db", required=True, help="Path to main sqlite db (where SqlEvents lives)")
    ap.add_argument("--dt-col", default="", help="Datetime column name (auto-detect if empty)")
    ap.add_argument("--keep-months", type=int, default=2, help="How many latest months to keep in raw SqlEvents")
    ap.add_argument("--chunk", type=int, default=50000, help="Batch size for move/delete")
    ap.add_argument("--archive-dir", default="", help="If set: move old months into separate sqlite files here")

    ap.add_argument("--busy-ms", type=int, default=300000,
                    help="SQLite busy_timeout in ms (how long SQLite waits on lock internally)")
    ap.add_argument("--lock-wait-s", type=int, default=0,
                    help="How long our retry-loop waits on lock. 0 = infinite")
    ap.add_argument("--lock-sleep", type=float, default=0.25,
                    help="Initial sleep between lock retries")
    ap.add_argument("--lock-sleep-max", type=float, default=5.0,
                    help="Max sleep between lock retries")

    ap.add_argument("--no-index", action="store_true", help="Do not create index on dt column")
    ap.add_argument("--no-wal", action="store_true", help="Do not switch to WAL mode")
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    conn = sqlite3.connect(str(db_path), timeout=max(60.0, args.busy_ms / 1000.0))
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None  # будем управлять транзакциями сами через BEGIN/COMMIT
    try:
        def _init_pragmas():
            conn.execute("PRAGMA foreign_keys=OFF;")
            conn.execute(f"PRAGMA busy_timeout={int(args.busy_ms)};")
            conn.execute("PRAGMA temp_store=MEMORY;")
            if not args.no_wal:
                # WAL сильно помогает, но если окружение запрещает — можно выключить ключом --no-wal
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
            return True

        run_with_lock_wait(
            _init_pragmas,
            wait_s=args.lock_wait_s,
            sleep0=args.lock_sleep,
            sleep_max=args.lock_sleep_max,
        )

        dt_col = args.dt_col.strip() or detect_dt_column(conn, "SqlEvents")
        if not dt_col:
            raise SystemExit(
                "Не смог найти колонку времени в SqlEvents.\n"
                "Добавь столбец (например event_dt TEXT DEFAULT CURRENT_TIMESTAMP) "
                "или укажи --dt-col."
            )

        dt_mode = detect_dt_mode(conn, "SqlEvents", dt_col)

        run_with_lock_wait(
            lambda: ensure_agg_tables(conn),
            wait_s=args.lock_wait_s, sleep0=args.lock_sleep, sleep_max=args.lock_sleep_max,
        )

        if not args.no_index:
            run_with_lock_wait(
                lambda: ensure_index_dt(conn, "SqlEvents", dt_col),
                wait_s=args.lock_wait_s, sleep0=args.lock_sleep, sleep_max=args.lock_sleep_max,
            )

        rng = compute_month_range(conn, "SqlEvents", dt_col, dt_mode)
        if not rng:
            print("SqlEvents пустая — нечего делать.")
            return

        dmin, dmax = rng
        today_m = month_start(date.today())
        cutoff_m = add_month(today_m, -args.keep_months)  # всё что < cutoff_m считаем закрытым

        print(f"[info] dt_col={dt_col} dt_mode={dt_mode} range={dmin}..{dmax} cutoff(<)={cutoff_m}")

        archive_dir = Path(args.archive_dir) if args.archive_dir else None
        if archive_dir:
            archive_dir.mkdir(parents=True, exist_ok=True)

        m = dmin
        while m <= dmax:
            next_m = add_month(m, 1)
            ym = f"{m.year:04d}-{m.month:02d}"

            if dt_mode == "unix_epoch":
                start_bound = epoch_day(m)
                end_bound = epoch_day(next_m)
            else:
                start_bound = iso_day(m)         # 'YYYY-MM-01'
                end_bound = iso_day(next_m)      # 'YYYY-MM-next-01'

            def _roll():
                conn.execute("BEGIN IMMEDIATE;")
                try:
                    rollup_one_month(conn, dt_col, dt_mode, ym, start_bound, end_bound)
                    conn.execute("COMMIT;")
                except Exception:
                    conn.execute("ROLLBACK;")
                    raise

            run_with_lock_wait(
                _roll,
                wait_s=args.lock_wait_s, sleep0=args.lock_sleep, sleep_max=args.lock_sleep_max
            )
            print(f"[rollup] {ym} done")

            # 2) чистка только закрытых месяцев
            if m < cutoff_m:
                arch_path = None
                if archive_dir:
                    arch_path = archive_dir / f"SqlEvents_{ym}.sqlite"

                removed = move_or_delete_month_batched(
                    conn,
                    dt_col,
                    start_bound,
                    end_bound,
                    chunk=int(args.chunk),
                    archive_path=arch_path,
                    lock_wait_s=args.lock_wait_s,
                    lock_sleep=args.lock_sleep,
                    lock_sleep_max=args.lock_sleep_max,
                )
                print(f"[cleanup] {ym} removed={removed} archive={'yes' if arch_path else 'no'}")

            m = next_m

        if not args.no_wal:
            run_with_lock_wait(
                lambda: conn.execute("PRAGMA wal_checkpoint(TRUNCATE);"),
                wait_s=args.lock_wait_s, sleep0=args.lock_sleep, sleep_max=args.lock_sleep_max,
            )

        print("[ok] done")

    finally:
        conn.close()


if __name__ == "__main__":
    main()