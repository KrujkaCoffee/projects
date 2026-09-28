from __future__ import annotations
"""Автогенерированный manifest схем project_cust_38."""

MANIFEST = {
    "admin_schema_hash": "a37c1e55ac90b17bf458f5f6769b72a970be76d26911afd214e75d4bf780855a",
    "artifact_version": "a37c1e55ac90",
    "generated_at_utc": "2026-06-16 14:46:46",
    "generator_version": "1.0.4",
    "hint_names": [
        "KroCausesHint",
        "JurnalHint",
        "MkHint",
        "NaryadHint"
    ],
    "model_names": [
        "KroCauses",
        "Jurnal",
        "Mk",
        "Naryad"
    ],
    "notes": "generated into C:\\srv_mes\\srv_mes\\project_cust_38\\dynamic_db_models",
    "table_fields_hash": "2c2d53337f12f88e920600dc4d25774a164f7d14e2aac48bed29cbb8ce42c350",
    "table_signatures": {
        "Naryad.jurnal": {
            "api_hash": "4ff30727e1b2616bf776b28bba18746e090be3855ece30568aa98cd82fd3b613",
            "cache_hash": "fe62fadffc0680a9399391b58e361a456c3b412f0c7f060b1c9a7f30487ebc21",
            "db_key": "Naryad",
            "table_name": "jurnal",
            "ui_hash": "70337576df0d8cfd53b0d9d28e1b936120662868c707a4121de15a883a8270ad"
        },
        "Naryad.mk": {
            "api_hash": "bfcbae04f0aa7c0e42870d7b428839c9d9d6dc2b906aab9d804ca76306b167f6",
            "cache_hash": "3edbbb727d77e067671f5d8f4d48c52c755ccf9617ed815b077c4a027e146868",
            "db_key": "Naryad",
            "table_name": "mk",
            "ui_hash": "c1c82a5dfba1277741238310d8e28b5d9ebf08b9a054bc8320bbc838580a46b5"
        },
        "Naryad.naryad": {
            "api_hash": "051dc44b73396e04891efccd9cb1d1f7a9b993bf96b23d8adef5001d40bb6305",
            "cache_hash": "52b8d7572b694369c1f027c5727035a7db43696640221e53b06cdda323e5b11d",
            "db_key": "Naryad",
            "table_name": "naryad",
            "ui_hash": "4e782baaee07c0cf0df729cba43baefde7c0b40e2295096c416e8ec25991bc9b"
        },
        "db_naryad.kro_causes": {
            "api_hash": "de134b335ca1b11e23c57bc5e96638ce4333db42c6e1dd7a194f695e1838d272",
            "cache_hash": "bde4b4ed1bdb67d7323b744066b5a7d5d0163d99516e1d237261def75adbcec1",
            "db_key": "db_naryad",
            "table_name": "kro_causes",
            "ui_hash": "205f10ae025c8864095ac6a4fe1e0df6797c44bd3b4ef2150b0cbd72e5400d9d"
        }
    }
}
ARTIFACT_VERSION = 'a37c1e55ac90'
GENERATED_AT_UTC = '2026-06-16 14:46:46'


from typing import Any
from typing_extensions import TypedDict

class KroCausesHint(TypedDict, total=False):
    id: int
    name: str | None
    text: str | None
    descr: str | None

class JurnalHint(TypedDict, total=False):
    Пномер: int
    Дата: str | None
    Штамп: float | None
    Номер_наряда: int | None
    ФИО: str | None
    Подытог: float | None
    Подытог_нормы: float | None
    Статус: str | None
    Примечание: str | None
    Ном_заверш: int | None
    Дата_выгрузки_ЕРП: str | None
    ФИО_выгрузки_ЕРП: str | None
    Файл_выгрузки_ЕРП: bytes | None
    Минут_выгружено_ЕРП: float | None
    base_ERP: int | None

class MkHint(TypedDict, total=False):
    Пномер: int
    Дата: str | None
    Статус: str | None
    Номенклатура: str | None
    Номер_заказа: str | None
    Номер_проекта: str | None
    Вид: str | None
    Примечание: str | None
    Основание: str | None
    Прогресс: str | None
    Приоритет: int | None
    Направление: str | None
    Вес: float | None
    xml: float | None
    Количество: int | None
    Статус_ЧПУ: str | None
    Ресурсная: bytes | None
    Дата_завершения: str | None
    Коэф_парал: int | None
    Обеспечение: bytes | None
    Место: int
    Искл_план_рм: str | None
    Тип: int
    Ресурсная_дата: str
    ФИО: str | None
    НомКплан: int | None
    check_execute_opers: int | None
    Тип_доработки: int | None
    На_удал: int | None
    ТипВыгрузкиТрЗт: int | None
    xml_with_pki: float | None

class NaryadHint(TypedDict, total=False):
    Пномер: int
    Дата: str | None
    Автор: str | None
    Номер_мк: int | None
    Внеплан: int | None
    Задание: str | None
    Компл_ФИО: str | None
    Компл_Дата: str | None
    Компл_номер_тара: str | None
    Компл_адрес: str | None
    Распред_ФИО: str | None
    ФИО: str | None
    Фвремя: float | None
    ФИО2: str | None
    Фвремя2: float | None
    Твремя: float | None
    Норма_времени: float | None
    ДСЕ: str | None
    ДСЕ_ID: str | None
    Операции: str | None
    Опер_время: str | None
    Опер_колво: str | None
    Примечание: str | None
    Коэфф_сложности: float | None
    Подтвержд_вып: int | None
    Категория_внепл: int | None
    Виды_работ: str | None
    Номер_замечания_журнал: str | None
    Подтвержд_вып_дата: str | None
    Подтвержд_вып_фио: str | None
    Профессии: str | None
    РЦ_наряд: str | None
    ФИО_для_ОТК: str | None
    ФИО_для_ОТК_от_мастера: str | None
    Коэф_норм_созд: float | None
    Аутсорсинг: int | None
    Обособленная_расценка: int | None
    Заводской_комплект: str | None
    Кол_повт_приемок: int
    Распред_дата: str | None
    month_closing_block: str | None
    АвтоПодтвержд: int | None

__all__ = [
    "KroCausesHint",
    "JurnalHint",
    "MkHint",
    "NaryadHint"
]
