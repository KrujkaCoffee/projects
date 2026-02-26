from __future__ import annotations

import re
from typing import Any


def normalize_material_name(name: str) -> str:
    """Нормализация для поиска: нижний регистр + схлопывание пробелов."""
    return re.sub(r"\s+", " ", (name or "").strip().lower())


MATERIALS: dict[str, dict[str, Any]] = {
  "Бобы": {
    "ds": 8.1,
    "qs_kg_m3": 1390.0,
    "qss_kg_m3": 830.0,
    "qss_range": None,
    "u0_m_s": 25.0,
    "u0_range": [
      23.0,
      27.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Активированный уголь": {
    "ds": 3,
    "qs_kg_m3": 1860.0,
    "qss_kg_m3": 340.0,
    "qss_range": None,
    "u0_m_s": 21.5,
    "u0_range": [
      20.0,
      23.0
    ],
    "lambda_s_dl_over_d": 0.06
  },
  "Бентонит": {
    "ds": 0.04,
    "qs_kg_m3": 2680.0,
    "qss_kg_m3": 720.0,
    "qss_range": None,
    "u0_m_s": 26.0,
    "u0_range": [
      25.0,
      27.0
    ],
    "lambda_s_dl_over_d": 0.1
  },
  "Горький люпин": {
    "ds": 6.1,
    "qs_kg_m3": 1340.0,
    "qss_kg_m3": 830.0,
    "qss_range": None,
    "u0_m_s": 25.0,
    "u0_range": [
      23.0,
      27.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Ячмень": {
    "ds": 4,
    "qs_kg_m3": 1420.0,
    "qss_kg_m3": 690.0,
    "qss_range": None,
    "u0_m_s": 22.5,
    "u0_range": [
      20.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Стеклянные шарики": {
    "ds": 1.14,
    "qs_kg_m3": 2990.0,
    "qss_kg_m3": 1780.0,
    "qss_range": None,
    "u0_m_s": 24.5,
    "u0_range": [
      22.0,
      27.0
    ],
    "lambda_s_dl_over_d": 0.06
  },
  "Окалаленная слюда": {
    "ds": 2,
    "qs_kg_m3": 2520.0,
    "qss_kg_m3": 100.0,
    "qss_range": None,
    "u0_m_s": 20.0,
    "u0_range": [
      18.0,
      22.0
    ],
    "lambda_s_dl_over_d": 0.03
  },
  "Сырая слюда": {
    "ds": 0.93,
    "qs_kg_m3": 2550.0,
    "qss_kg_m3": 830.0,
    "qss_range": None,
    "u0_m_s": 27.5,
    "u0_range": [
      25.0,
      30.0
    ],
    "lambda_s_dl_over_d": 0.09
  },
  "Зеленый солод": {
    "ds": 4.5,
    "qs_kg_m3": 1320.0,
    "qss_kg_m3": 400.0,
    "qss_range": None,
    "u0_m_s": 25.0,
    "u0_range": [
      23.0,
      27.0
    ],
    "lambda_s_dl_over_d": 0.06
  },
  "Овес": {
    "ds": 3.4,
    "qs_kg_m3": 1340.0,
    "qss_kg_m3": 510.0,
    "qss_range": None,
    "u0_m_s": 23.5,
    "u0_range": [
      22.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Древесная щепа": {
    "ds": "100x50x4",
    "qs_kg_m3": 720.0,
    "qss_kg_m3": 500.0,
    "qss_range": None,
    "u0_m_s": 25.0,
    "u0_range": [
      23.0,
      27.0
    ],
    "lambda_s_dl_over_d": 0.08
  },
  "Древесные опилки": {
    "ds": "50x20x1",
    "qs_kg_m3": 470.0,
    "qss_kg_m3": 275.0,
    "qss_range": [
      150.0,
      400.0
    ],
    "u0_m_s": 23.5,
    "u0_range": [
      22.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Древесные волокна": {
    "ds": "200X3X3",
    "qs_kg_m3": 470.0,
    "qss_kg_m3": 20.0,
    "qss_range": None,
    "u0_m_s": 22.5,
    "u0_range": [
      20.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Клевер рогатый": {
    "ds": 1.1,
    "qs_kg_m3": 1420.0,
    "qss_kg_m3": 830.0,
    "qss_range": None,
    "u0_m_s": 23.5,
    "u0_range": [
      22.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Картофельные хлопья": {
    "ds": "10x10x1",
    "qs_kg_m3": 1200.0,
    "qss_kg_m3": 300.0,
    "qss_range": None,
    "u0_m_s": 21.5,
    "u0_range": [
      20.0,
      23.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Концентрированный корм": {
    "ds": 0.86,
    "qs_kg_m3": 1370.0,
    "qss_kg_m3": 540.0,
    "qss_range": None,
    "u0_m_s": 23.5,
    "u0_range": [
      22.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.06
  },
  "Влажная кукуруза": {
    "ds": 8.7,
    "qs_kg_m3": 1250.0,
    "qss_kg_m3": 680.0,
    "qss_range": None,
    "u0_m_s": 24.5,
    "u0_range": [
      22.0,
      27.0
    ],
    "lambda_s_dl_over_d": 0.06
  },
  "Сухая кукуруза": {
    "ds": 7.7,
    "qs_kg_m3": 1300.0,
    "qss_kg_m3": 680.0,
    "qss_range": None,
    "u0_m_s": 23.5,
    "u0_range": [
      22.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Кукурузная мука": {
    "ds": 0.75,
    "qs_kg_m3": 1440.0,
    "qss_kg_m3": 650.0,
    "qss_range": None,
    "u0_m_s": 24.0,
    "u0_range": [
      23.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.06
  },
  "Кукурузный крахмал": {
    "ds": 0.19,
    "qs_kg_m3": 1400.0,
    "qss_kg_m3": 460.0,
    "qss_range": None,
    "u0_m_s": 24.0,
    "u0_range": [
      23.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.1
  },
  "Гранулированный макролон": {
    "ds": 3.2,
    "qs_kg_m3": 1230.0,
    "qss_kg_m3": 670.0,
    "qss_range": None,
    "u0_m_s": 23.5,
    "u0_range": [
      22.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Солод": {
    "ds": 3.7,
    "qs_kg_m3": 1370.0,
    "qss_kg_m3": 540.0,
    "qss_range": None,
    "u0_m_s": 21.0,
    "u0_range": [
      20.0,
      22.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Солодовая крупа": {
    "ds": 0.7,
    "qs_kg_m3": 1480.0,
    "qss_kg_m3": 400.0,
    "qss_range": None,
    "u0_m_s": 23.5,
    "u0_range": [
      22.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.06
  },
  "Метилцеллюлоза": {
    "ds": 0.35,
    "qs_kg_m3": 1230.0,
    "qss_kg_m3": 370.0,
    "qss_range": None,
    "u0_m_s": 23.5,
    "u0_range": [
      22.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.06
  },
  "Бикарбонат натрия": {
    "ds": 0.063,
    "qs_kg_m3": 2700.0,
    "qss_kg_m3": 1070.0,
    "qss_range": None,
    "u0_m_s": 23.5,
    "u0_range": [
      22.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.1
  },
  "Картонная шелуха": {
    "ds": "100x20",
    "qs_kg_m3": 970.0,
    "qss_kg_m3": 50.0,
    "qss_range": None,
    "u0_m_s": 19.0,
    "u0_range": [
      18.0,
      20.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Фенольная смола": {
    "ds": 0.65,
    "qs_kg_m3": 1380.0,
    "qss_kg_m3": 520.0,
    "qss_range": None,
    "u0_m_s": 22.5,
    "u0_range": [
      20.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.06
  },
  "Гранулированный полиэтилен": {
    "ds": 3.5,
    "qs_kg_m3": 1070.0,
    "qss_kg_m3": 500.0,
    "qss_range": None,
    "u0_m_s": 22.5,
    "u0_range": [
      20.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Порошок полиэтилена": {
    "ds": 0.25,
    "qs_kg_m3": 1070.0,
    "qss_kg_m3": 450.0,
    "qss_range": None,
    "u0_m_s": 22.5,
    "u0_range": [
      20.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.1
  },
  "Полиэфирная стружка": {
    "ds": "6х4х2",
    "qs_kg_m3": 1400.0,
    "qss_kg_m3": 700.0,
    "qss_range": None,
    "u0_m_s": 25.0,
    "u0_range": [
      23.0,
      27.0
    ],
    "lambda_s_dl_over_d": 0.06
  },
  "Гранулированный полипропилен": {
    "ds": 3.5,
    "qs_kg_m3": 1000.0,
    "qss_kg_m3": 500.0,
    "qss_range": None,
    "u0_m_s": 22.5,
    "u0_range": [
      20.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Порошок полипропилена": {
    "ds": 0.22,
    "qs_kg_m3": 1000.0,
    "qss_kg_m3": 570.0,
    "qss_range": None,
    "u0_m_s": 22.5,
    "u0_range": [
      20.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.1
  },
  "Гранулированный полистирол": {
    "ds": 2.7,
    "qs_kg_m3": 1070.0,
    "qss_kg_m3": 600.0,
    "qss_range": None,
    "u0_m_s": 22.5,
    "u0_range": [
      20.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "ПВХ-порошок": {
    "ds": 0.2,
    "qs_kg_m3": 1320.0,
    "qss_kg_m3": 570.0,
    "qss_range": None,
    "u0_m_s": 22.5,
    "u0_range": [
      20.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.1
  },
  "Рис": {
    "ds": 2.7,
    "qs_kg_m3": 1620.0,
    "qss_kg_m3": 800.0,
    "qss_range": None,
    "u0_m_s": 22.5,
    "u0_range": [
      20.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.06
  },
  "Рисовая шелуха": {
    "ds": 2.5,
    "qs_kg_m3": 1280.0,
    "qss_kg_m3": 105.0,
    "qss_range": None,
    "u0_m_s": 19.0,
    "u0_range": [
      18.0,
      20.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Рожь": {
    "ds": 3,
    "qs_kg_m3": 1180.0,
    "qss_kg_m3": 620.0,
    "qss_range": None,
    "u0_m_s": 23.5,
    "u0_range": [
      22.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Опилки": {
    "ds": 0.7,
    "qs_kg_m3": 470.0,
    "qss_kg_m3": 190.0,
    "qss_range": None,
    "u0_m_s": 22.5,
    "u0_range": [
      20.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Мыльная паста": {
    "ds": "20x5",
    "qs_kg_m3": 1100.0,
    "qss_kg_m3": 600.0,
    "qss_range": None,
    "u0_m_s": 25.0,
    "u0_range": [
      23.0,
      27.0
    ],
    "lambda_s_dl_over_d": 0.08
  },
  "Соевые бобы": {
    "ds": 6.3,
    "qs_kg_m3": 1270.0,
    "qss_kg_m3": 690.0,
    "qss_range": None,
    "u0_m_s": 23.5,
    "u0_range": [
      22.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Рапс": {
    "ds": 1.9,
    "qs_kg_m3": 1140.0,
    "qss_kg_m3": 680.0,
    "qss_range": None,
    "u0_m_s": 22.5,
    "u0_range": [
      20.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Стальные шарики, дробь": {
    "ds": 1.08,
    "qs_kg_m3": 7850.0,
    "qss_kg_m3": 4420.0,
    "qss_range": None,
    "u0_m_s": 30.0,
    "u0_range": [
      25.0,
      35.0
    ],
    "lambda_s_dl_over_d": 0.12
  },
  "Каменная соль": {
    "ds": 1.6,
    "qs_kg_m3": 2190.0,
    "qss_kg_m3": 1200.0,
    "qss_range": None,
    "u0_m_s": 24.5,
    "u0_range": [
      22.0,
      27.0
    ],
    "lambda_s_dl_over_d": 0.08
  },
  "Шарики из пенопласта": {
    "ds": 3.5,
    "qs_kg_m3": 84.0,
    "qss_kg_m3": 29.0,
    "qss_range": None,
    "u0_m_s": 17.5,
    "u0_range": [
      15.0,
      20.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Высушенное отработанное зерно": {
    "ds": 0.96,
    "qs_kg_m3": 680.0,
    "qss_kg_m3": 260.0,
    "qss_range": None,
    "u0_m_s": 21.0,
    "u0_range": [
      20.0,
      22.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Белая горчица": {
    "ds": 2.1,
    "qs_kg_m3": 1190.0,
    "qss_kg_m3": 700.0,
    "qss_range": None,
    "u0_m_s": 22.5,
    "u0_range": [
      20.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Пшеница": {
    "ds": 3.9,
    "qs_kg_m3": 1380.0,
    "qss_kg_m3": 730.0,
    "qss_range": None,
    "u0_m_s": 24.5,
    "u0_range": [
      22.0,
      27.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Пшеничные отруби": {
    "ds": 0.15,
    "qs_kg_m3": 1470.0,
    "qss_kg_m3": 370.0,
    "qss_range": None,
    "u0_m_s": 22.5,
    "u0_range": [
      20.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.06
  },
  "Пшеничная мука": {
    "ds": 0.09,
    "qs_kg_m3": 1470.0,
    "qss_kg_m3": 540.0,
    "qss_range": None,
    "u0_m_s": 20.5,
    "u0_range": [
      18.0,
      23.0
    ],
    "lambda_s_dl_over_d": 0.08
  },
  "Озимая пшеница": {
    "ds": 3.4,
    "qs_kg_m3": 1390.0,
    "qss_kg_m3": 820.0,
    "qss_range": None,
    "u0_m_s": 23.5,
    "u0_range": [
      22.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Целлюлозный порошок": {
    "ds": 0.04,
    "qs_kg_m3": 1380.0,
    "qss_kg_m3": 230.0,
    "qss_range": None,
    "u0_m_s": 22.5,
    "u0_range": [
      20.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.04
  },
  "Цемент": {
    "ds": 0.05,
    "qs_kg_m3": 3100.0,
    "qss_kg_m3": 1420.0,
    "qss_range": None,
    "u0_m_s": 22.5,
    "u0_range": [
      20.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.18
  },
  "Цементная мука": {
    "ds": 0.05,
    "qs_kg_m3": 3100.0,
    "qss_kg_m3": 960.0,
    "qss_range": None,
    "u0_m_s": 22.5,
    "u0_range": [
      20.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.15
  },
  "Цикорий": {
    "ds": 25,
    "qs_kg_m3": 1320.0,
    "qss_kg_m3": 300.0,
    "qss_range": None,
    "u0_m_s": 25.0,
    "u0_range": [
      23.0,
      27.0
    ],
    "lambda_s_dl_over_d": 0.06
  },
  "Оксид цинка": {
    "ds": 0.1,
    "qs_kg_m3": 4850.0,
    "qss_kg_m3": 2000.0,
    "qss_range": None,
    "u0_m_s": 27.5,
    "u0_range": [
      25.0,
      30.0
    ],
    "lambda_s_dl_over_d": 0.15
  },
  "Сахар": {
    "ds": 0.52,
    "qs_kg_m3": 1610.0,
    "qss_kg_m3": 860.0,
    "qss_range": None,
    "u0_m_s": 22.5,
    "u0_range": [
      20.0,
      25.0
    ],
    "lambda_s_dl_over_d": 0.08
  }
}

ALIASES: dict[str, str] = {}


def find_material(name: str) -> tuple[str | None, dict[str, Any] | None]:
    """Вернуть (каноническое_имя, запись) по введённому пользователем тексту."""
    key = normalize_material_name(name)
    if not key:
        return None, None

    if key in ALIASES:
        canon = ALIASES[key]
        return canon, MATERIALS.get(canon)

    for canon, rec in MATERIALS.items():
        if normalize_material_name(canon) == key:
            return canon, rec

    return None, None


def list_materials(limit: int = 50) -> list[str]:
    """Выдать отсортированный список материалов."""
    names = sorted(MATERIALS.keys())
    return names[: max(0, int(limit))]
