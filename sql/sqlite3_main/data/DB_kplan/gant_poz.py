# /sql/sqlite3_main/data/DB_kplan/500_gant_poz.py

from __future__ import annotations
import logging

from dataclasses import dataclass
from datetime import datetime, timedelta

from project_cust_38 import Cust_mes as CMS
from project_cust_38 import Cust_Functions as F

F_NEW = CMS_NEW = None
try:
    from project_cust_38_new import Cust_mes as CMS
    from project_cust_38_new import Cust_Functions as F
except Exception as e:
    print(e)


DB_ALIAS = "DB_kplan"
TABLE = "gant_poz"
ORDER = 500

REQUIRES = [
    "plan",
    "gant_poz_val_by_day",
]


@dataclass
class EtapInfo:
    """
    Минимальная duck-typing замена Table_db_info.

    Для gant-объекта реально нужны:
    - name: имя этапной таблицы, например 'пл_сб'
    - id: идентификатор этапа/подразделения для gant_poz_val_by_day
    - alias: подпись для UI, если понадобится отрисовка
    """
    id: int
    name: str
    alias: str


def _pack_poz_gant(poz: CMS.Poz_gant) -> bytes:
    return F.pack_byte_file(
        F.to_binary_pickle(poz)
    )


def _cld_day(day: datetime) -> CMS.Month_cld_day:
    return CMS.Month_cld_day(
        is_holyday=0,
        day_week=day.weekday(),
        dt_datetime=day,
    )


def build_light_gant(
    *,
    id_poz: int,
    etaps: list[EtapInfo],
    start_date: str = "2026-05-01",
    days: int = 5,
    plan_minutes: int = 120,
    fact_minutes: int | None = None,
) -> CMS.Poz_gant:
    start = datetime.strptime(start_date, "%Y-%m-%d")

    poz = CMS.Poz_gant(id_poz)

    for offset in range(days):
        current_day = start + timedelta(days=offset)
        day_gant = poz.add_day(current_day, _cld_day(current_day))

        for etap in etaps:
            etap_gant = day_gant.add_etap(etap)
            etap_gant.add_cell(CMS.Types_day_gant.plan, plan_minutes)

            if fact_minutes is not None:
                etap_gant.add_cell(CMS.Types_day_gant.fact, fact_minutes)

    return poz


def seed(ctx):
    """
    ctx — объект сборщика фикстур.
    Он знает, куда писать локальную DB_kplan.db.
    """

    # В простейшем варианте можно зашить 2-3 этапа.
    # Главное: id должны соответствовать тестовым справочникам,
    # которые уже загружены в БД.
    etaps = [
        EtapInfo(id=1, name="пл_сб", alias="Сборка"),
        EtapInfo(id=2, name="пл_покр", alias="Покраска"),
    ]

    positions = ctx.select(
        "DB_kplan",
        """
        SELECT Пномер
        FROM plan
        ORDER BY Пномер
        LIMIT 10
        """
    )

    dict_tbls_db_info = {item.name: item for item in etaps}

    for row in positions:
        id_poz = row["Пномер"]

        poz = build_light_gant(
            id_poz=id_poz,
            etaps=etaps,
            start_date="2026-05-01",
            days=5,
            plan_minutes=120,
            fact_minutes=90,
        )

        blob = _pack_poz_gant(poz)

        ctx.execute(
            "DB_kplan",
            """
            INSERT INTO gant_poz (id_poz, data_gant, dt_upd)
            VALUES (?, ?, ?)
            ON CONFLICT(id_poz) DO UPDATE SET
                data_gant = excluded.data_gant,
                dt_upd = excluded.dt_upd
            """,
            [id_poz, blob, ctx.now()],
        )
        aggregate_rows = poz.generate_agregate(dict_tbls_db_info)
        ctx.execute(
            "DB_kplan",
            "DELETE FROM gant_poz_val_by_day WHERE id_poz = ?",
            [id_poz],
        )
        ctx.insert_many(
            "DB_kplan",
            "gant_poz_val_by_day",
            aggregate_rows,
        )
