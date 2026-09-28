"""Deterministic synthetic data; no names or records from production snapshots."""
import copy
import datetime as dt
import random

A = "Иванов Иван Иванович"
B = "Петров Петр Петрович"


def history(identifier, person, job, *, department="d1", organization="o1",
            period="2025-01-01 00:00:00", event="Прием", employee=None):
    return {"id": identifier, "ФизическоеЛицо_Key": person, "Должность_Key": job,
            "Подразделение_Key": department, "Период": period,
            "Организация_Key": organization, "Событие": event,
            "Сотрудник_Key": employee or "contract-" + person}


def fragment(identifier, fio, order, norm, *, status="Начат", date="2026-01-15 12:00:00"):
    return {"Пномер": identifier, "Дата": date, "ФИО": fio, "Подытог": 60,
            "Номер_наряда": order, "Статус": status, "Подытог_нормы": norm}


def base():
    return {
        "name": "01_base", "expected": "MATCH",
        "purpose": "Две должности; одна строка Начат и одна Завершен у каждого сотрудника.",
        "golden": {"row_ids": [1, 2, 3, 4], "norms": {A: 120, B: 60}},
        "request": {"nach": "2026-01-01 05:00:00", "konec": "2026-02-01 04:59:59",
                    "as_of": "2026-06-30 12:00:00", "organization": "Завод А",
                    "podrazdelenie": "Цех 1", "company": "Завод А", "poki": 0, "unconfirmed": 1},
        "dimensions": {"positions": {"j1": "Сварщик", "j2": "Слесарь", "j3": "Оператор лазера"},
                       "departments": {"d1": "Цех 1", "d2": "Цех 2"}},
        "organization_refs": {"Завод А": ["o1"]},
        "history": [history(1, "p1", "j1"), history(2, "p2", "j2")],
        "erp": {"status": 200, "data": [{"Должность": "Сварщик", "Подразделение": "Цех 1"},
                                        {"Должность": "Слесарь", "Подразделение": "Цех 1"}]},
        "employee_current": {A: {"Компания": "Завод А", "Подразделение": "Цех 1"},
                             B: {"Компания": "Завод А", "Подразделение": "Цех 1"}},
        "tabel": [A + " Сварщик", B + " Слесарь"],
        "tables": {
            "dolgn_etap": [{"Должность": s, "Подразделение": "Цех 1", "Производство": "Завод А"}
                           for s in ("Сварщик", "Слесарь")],
            "jurnal": [fragment(1, A, 1, 120), fragment(2, A, 1, None, status="Завершен"),
                       fragment(3, B, 2, 60), fragment(4, B, 2, 0, status="Завершен")],
            "naryad": [{"Пномер": i, "Номер_мк": i, "Твремя": 120, "Норма_времени": 100,
                        "Коэфф_сложности": 1.2, "Внеплан": 0, "Подтвержд_вып": 1} for i in (1, 2)],
            "mk": [{"Пномер": i, "Номер_проекта": "PROJECT-" + str(i), "НомКплан": i} for i in (1, 2)],
            "plan": [{"Пномер": 1}, {"Пномер": 2}],
            "пл_оуп": [{"НомПл": 1, "Пномер_ЗП": 1}],
            "знпр": [{"s_num": 1, "№проекта": "OVERRIDE-1"}],
            "коды_веплана_для_наряда": [{"code": 0, "poki": 0}, {"code": 1, "poki": 0},
                                     {"code": 10, "poki": 1}],
        },
    }


def targeted_cases():
    cases = [base()]
    def add(name, purpose, expected="MATCH", keep_golden=False):
        case = base()
        case.update(name=name, purpose=purpose, expected=expected)
        if not keep_golden:
            case.pop("golden", None)
        cases.append(case)
        return case

    c = add("02_timesheet_from_db", "Ветка tabel_m=None с чтением mtdz.", keep_golden=True)
    c["tabel_mode"] = "db"
    c = add("03_duplicate_timesheet", "Повтор ФИО в табеле не умножает строки IN.", keep_golden=True)
    c["tabel"] *= 3
    c = add("04_duplicate_erp_positions", "Дубли должностей и порядок не влияют на membership.", keep_golden=True)
    c["erp"]["data"] = c["erp"]["data"][::-1] * 3
    c = add("05_same_title_different_guid", "Два GUID с одинаковым названием должности.", keep_golden=True)
    c["dimensions"]["positions"]["j4"] = "Сварщик"
    c["history"].append(history(3, "p3", "j4"))
    c = add("06_other_department", "Состояние другого подразделения не добавляет должность.", keep_golden=True)
    c["history"].append(history(3, "p3", "j3", department="d2"))
    c = add("07_other_organization", "Состояние другой организации не добавляет должность.", keep_golden=True)
    c["history"].append(history(3, "p3", "j3", organization="o2"))
    c = add("08_future_event", "Событие после зафиксированного as_of не попадает в срез.", keep_golden=True)
    c["history"].append(history(3, "p1", "j3", period="2027-01-01 00:00:00"))
    c = add("09_tie_breaker_id", "При одинаковом Период выбирается больший id.", keep_golden=True)
    c["history"][0]["Должность_Key"] = "j3"
    c["history"].append(history(3, "p1", "j1"))
    c["expected_native_ids"] = [3, 2]
    c = add("10_iso_separator", "Смешанные T и пробел в датах одного календарного дня.", keep_golden=True)
    c["history"][0]["Период"] = "2025-01-01T00:00:00"
    c = add("11_dismissed_removed_by_current_dict", "dict_emploee_full уже исключил уволенного; регистр оставляет событие.")
    c["history"].append(history(3, "p1", "j1", event="Увольнение", period="2026-02-01 00:00:00"))
    c["employee_current"].pop(A)
    c["golden"] = {"row_ids": [3, 4], "norms": {B: 60}}
    c = add("12_rehire", "Увольнение и повторный прием; последнее состояние доступно.", keep_golden=True)
    c["history"] += [history(3, "p1", "j1", event="Увольнение", period="2025-06-01 00:00:00"),
                     history(4, "p1", "j1", event="Прием", period="2026-01-01 00:00:00")]
    c = add("13_current_position_changed", "Оба текущих источника видят новую должность; старый табель исключает ФИО.")
    c["history"].append(history(3, "p1", "j3", period="2026-03-01 00:00:00"))
    c["erp"]["data"][0]["Должность"] = "Оператор лазера"
    c["golden"] = {"row_ids": [3, 4], "norms": {B: 60}}
    c = add("14_month_end_is_not_current", "Замена текущего источника на срез конца месяца меняет набор должностей.", "DIFFERENT")
    c["history"].append(history(3, "p1", "j3", period="2026-03-01 00:00:00"))
    c["erp"]["data"][0]["Должность"] = "Оператор лазера"
    c["request"]["as_of"] = "2026-01-31 23:59:59"
    c = add("15_two_contracts_one_person", "Два Сотрудник_Key одного физлица; employee.all_at сворачивает их.", "DIFFERENT")
    c["history"].append(history(3, "p1", "j2", employee="second-contract", period="2026-01-01 00:00:00"))
    c = add("16_never_in_erp_timesheet", "Новый человек есть в КадроваяИстория, но его еще нет ни в одном табеле 1С.", "DIFFERENT")
    c["history"].append(history(3, "p3", "j3"))
    c = add("17_mes_sync_lag", "В 1С новая должность, MES еще содержит прежнюю.", "DIFFERENT")
    c["erp"]["data"][0]["Должность"] = "Оператор лазера"
    c = add("18_department_transfer_lag", "Перевод в другой цех отражен только в MES.", "DIFFERENT")
    c["history"].append(history(3, "p1", "j1", department="d2", period="2026-01-01 00:00:00"))
    c = add("19_excluding_dismissal_changes_positions", "Дополнительный фильтр Событие=Увольнение меняет старую семантику.", "DIFFERENT")
    c["history"].append(history(3, "p1", "j1", event="Увольнение", period="2026-02-01 00:00:00"))
    c["employee_current"].pop(A)
    c["policy"] = {"exclude_events": ["Увольнение"]}
    c = add("20_missing_position_mapping", "Неизвестный GUID должности должен быть ошибкой, а не молчаливым пропуском.", "BLOCKED")
    del c["dimensions"]["positions"]["j1"]
    c = add("21_missing_department_mapping", "Неизвестный GUID подразделения.", "BLOCKED")
    del c["dimensions"]["departments"]["d1"]
    c = add("22_filial_mapping_unverified", "Нет явного соответствия Филиал.Наименование и Организация_Key.", "BLOCKED")
    c["organization_refs"] = {}
    c = add("23_wrong_org_guid", "Неверный GUID дает пустой регистр и совпавший SQL fallback; это не доказательство.", "INCONCLUSIVE")
    c["organization_refs"] = {"Завод А": ["wrong-guid"]}
    c = add("24_corrupt_history_date", "Некорректный Период блокирует strict_dates даже у другого сотрудника.", "BLOCKED")
    c["history"].append(history(3, "p3", "j3", department="d2", period="not-a-date"))
    c = add("25_aware_as_of", "Timezone-aware as_of не принимается данным API регистра.", "BLOCKED")
    c["request"]["as_of"] += "+03:00"
    c = add("26_erp_empty", "HTTP 200 и data=[] ведут в dolgn_etap; совпадение не аттестует замену.", "INCONCLUSIVE")
    c["erp"]["data"] = []
    c = add("27_erp_http_error", "HTTP 500 с совпадающим SQL fallback.", "INCONCLUSIVE")
    c["erp"]["status"] = 500
    c = add("28_erp_transport_exception", "Исключение API старым кодом не перехватывается.", "BLOCKED")
    c["erp"]["raise"] = "synthetic connection timeout"
    c = add("29_erp_missing_data", "HTTP 200 без ключа data вызывает KeyError в исходнике.", "BLOCKED")
    c["erp"]["body"] = {}
    c = add("30_register_empty_fallback", "Пустая КадроваяИстория и совпавший dolgn_etap.", "INCONCLUSIVE")
    c["history"] = []
    c = add("31_register_empty_strict", "Пустой регистр без fallback показывает потерю выборки.", "DIFFERENT")
    c["history"] = []; c["policy"] = {"empty_fallback": False}
    c = add("32_register_error_fallback", "Даже одинаковые результаты при подавленной ошибке регистра не дают MATCH.", "INCONCLUSIVE")
    c["history"][0]["Период"] = "bad"
    c["policy"] = {"error_fallback": True}
    c = add("33_no_organization_guard", "Возврат None оставляет SQL без фильтра ФИО; это старое поведение.", "INCONCLUSIVE")
    c["request"]["organization"] = None
    c = add("34_empty_fallback_lists", "[] в обоих источниках: SQLite IN () пуст; источник не подтвержден.", "INCONCLUSIVE")
    c["erp"]["data"] = []; c["history"] = []; c["tables"]["dolgn_etap"] = []
    c["golden"] = {"row_ids": [], "norms": {}}
    c = add("35_no_current_employee", "Отсутствующий в текущем словаре сотрудник исключается.")
    c["employee_current"].pop(A)
    c["golden"] = {"row_ids": [3, 4], "norms": {B: 60}}
    c = add("36_company_comes_from_config", "company из Config.place.Имя, отдельно от аргумента organization.")
    c["request"]["company"] = "Другой завод"
    c["golden"] = {"row_ids": [], "norms": {}}
    c = add("37_whitespace_in_timesheet", "split() сворачивает повторные пробелы табеля.", keep_golden=True)
    c["tabel"] = ["  " + s.replace(" ", "   ") + "  " for s in c["tabel"]]
    c = add("38_case_sensitive_title", "Сварщик и сварщик не равны; регистр не должен менять правило.")
    c["tabel"][0] = A + " сварщик"
    c["golden"] = {"row_ids": [3, 4], "norms": {B: 60}}
    c = add("39_two_word_fio", "Парсер первых трех слов теряет должность при ФИО без отчества.")
    c["tabel"][0] = "Иванов Иван Сварщик"
    c["golden"] = {"row_ids": [3, 4], "norms": {B: 60}}
    c = add("40_position_trailing_space", "Название справочника с пробелом нельзя незаметно strip().", "DIFFERENT")
    c["dimensions"]["positions"]["j1"] += " "
    c = add("41_unconfirmed_order", "Неподтвержденный наряд исключен из spis_jur_full, но норма Начат остается.")
    c["tables"]["naryad"][0]["Подтвержд_вып"] = 0
    c["golden"] = {"row_ids": [3, 4], "norms": {A: 120, B: 60}}
    c = add("42_unconfirmed_unplanned_code", "Код НеподтвержденныйВнеплан удаляет строки, но не норму Начат.")
    c["tables"]["naryad"][0]["Внеплан"] = 1
    c["golden"] = {"row_ids": [3, 4], "norms": {A: 120, B: 60}}
    c = add("43_unknown_unplanned_code", "Нет кода в справочнике: WHERE по LEFT JOIN исключает строки.")
    c["tables"]["naryad"][0]["Внеплан"] = 99
    c["golden"] = {"row_ids": [3, 4], "norms": {B: 60}}
    c = add("44_other_poki", "Код существует, но относится к другому poki.")
    c["tables"]["naryad"][0]["Внеплан"] = 10
    c["golden"] = {"row_ids": [3, 4], "norms": {B: 60}}
    c = add("45_missing_inner_join", "Отсутствующий mk исключает строки INNER JOIN.")
    c["tables"]["mk"] = c["tables"]["mk"][1:]
    c["golden"] = {"row_ids": [3, 4], "norms": {B: 60}}
    c = add("46_left_join_multiplies_rows", "Дубли пл_оуп умножают строки и норму; нельзя сравнивать только set(id).")
    c["tables"]["пл_оуп"] *= 2
    c["golden"] = {"row_ids": [1, 1, 2, 2, 3, 4], "norms": {A: 240, B: 60}}
    c = add("47_time_boundaries", "05:00 включено; 04:59:00 следующего месяца включено; 04:59:01 исключено.")
    for i, date in enumerate(("2026-01-01 04:59:59", "2026-01-01 05:00:00",
                              "2026-02-01 04:59:00", "2026-02-01 04:59:01"), 5):
        c["tables"]["jurnal"].append(fragment(i, A, 1, 10, date=date))
    c["golden"] = {"row_ids": [1, 2, 3, 4, 6, 7], "norms": {A: 140, B: 60}}
    c = add("48_comma_and_exponent", "F.valm обрабатывает десятичную запятую и экспоненту.")
    c["tables"]["jurnal"][0]["Подытог_нормы"] = "12,5"
    c["tables"]["jurnal"][2]["Подытог_нормы"] = "1e2"
    c["golden"] = {"row_ids": [1, 2, 3, 4], "norms": {A: 12.5, B: 100.0}}
    c = add("49_negative_norm", "Отрицательные числовые нормы суммируются исходником.")
    c["tables"]["jurnal"][0]["Подытог_нормы"] = -120
    c["golden"] = {"row_ids": [1, 2, 3, 4], "norms": {A: -120, B: 60}}
    c = add("50_non_numeric_start", "Пустая норма Начат требует записи через Jurnal_nar; стенд блокирует ее.", "BLOCKED")
    c["tables"]["jurnal"][0]["Подытог_нормы"] = None
    c = add("51_non_numeric_finish", "Пустая норма Завершен не запускает ветку ремонта.", keep_golden=True)
    c["tables"]["jurnal"][3]["Подытог_нормы"] = "not numeric"
    c = add("52_nan_string_converts_to_zero", "is_numeric('NaN') истинно, но текущий F.valm('NaN') возвращает 0.")
    c["tables"]["jurnal"][0]["Подытог_нормы"] = "NaN"
    c["golden"] = {"row_ids": [1, 2, 3, 4], "norms": {A: 0, B: 60}}
    c = add("53_no_started_rows", "Сотрудники в журнале получают ноль, если нет Начат.")
    for row in c["tables"]["jurnal"]:
        row["Статус"] = "Завершен"
    c["golden"] = {"row_ids": [1, 2, 3, 4], "norms": {A: 0, B: 0}}
    c = add("54_same_department_name_two_guids", "Старый WHERE отбирает по имени; новый сохраняет это правило.", keep_golden=True)
    c["dimensions"]["departments"]["d3"] = "Цех 1"
    c["history"][0]["Подразделение_Key"] = "d3"
    c = add("55_leap_february", "Полный февраль високосного года, граница 29 февраля.", keep_golden=True)
    c["request"].update(nach="2024-02-01 05:00:00", konec="2024-03-01 04:59:59")
    for r in c["tables"]["jurnal"]: r["Дата"] = "2024-02-29 23:59:59"
    c = add("56_year_boundary", "Переход декабрь-январь.", keep_golden=True)
    c["request"].update(nach="2025-12-01 05:00:00", konec="2026-01-01 04:59:59")
    for r in c["tables"]["jurnal"]: r["Дата"] = "2025-12-31 23:59:59"
    c = add("57_missing_norm_unconfirmed", "Неподтвержденная строка Начат с плохой нормой все равно запускает ремонт.", "BLOCKED")
    c["tables"]["naryad"][0]["Подтвержд_вып"] = 0
    c["tables"]["jurnal"][0]["Подытог_нормы"] = ""
    c = add("58_absent_month_timesheet", "Пустой переданный табель дает пустую выборку при непустых должностях.")
    c["tabel"] = []
    c["golden"] = {"row_ids": [], "norms": {}}
    c = add("59_infinite_norm_is_blocked", "F.valm('1e999') дает бесконечность; совпадение не аттестуется.", "BLOCKED")
    c["tables"]["jurnal"][0]["Подытог_нормы"] = "1e999"
    return cases


def volume_case(seed=73021, employees=40, events=6, fragments=20, name=None):
    """Seeded histories, two legal employers, three departments and job changes.

    ERP fixture is an independent current-position response. This establishes
    synthetic agreement only; actual ERP validation is done by capture_live.py.
    """
    rng = random.Random(seed)
    c = base()
    c.pop("golden")
    c.update(name=name or f"random_{seed}", purpose=f"seed={seed}; {employees} физлиц × {events} кадровых событий × {fragments} фрагментов.")
    c["history"], c["tabel"], c["employee_current"] = [], [], {}
    c["tables"]["jurnal"], c["tables"]["naryad"] = [], []
    c["tables"]["mk"], c["tables"]["plan"] = [], []
    c["tables"]["пл_оуп"], c["tables"]["знпр"] = [], []
    erp_jobs = set()
    expected_rows, expected_norms = [], {}
    for i in range(employees):
        person, fio, order = f"person-{i:07}", f"Работник{i:07} Имя Отчество", i + 1
        org = "o1" if i % 7 else "o2"
        dep = "d1" if i % 5 else "d2"
        job = rng.choice(list(c["dimensions"]["positions"]))
        final_name = c["dimensions"]["positions"][job]
        for event in range(events):
            event_job = job if event == events - 1 else rng.choice(list(c["dimensions"]["positions"]))
            period = (dt.datetime(2025, 1, 1) + dt.timedelta(days=event * 20)).strftime("%Y-%m-%d %H:%M:%S")
            c["history"].append(history(i * events + event + 1, person, event_job,
                                      department=dep, organization=org, period=period))
        if org == "o1" and dep == "d1": erp_jobs.add(final_name)
        active = i % 11 != 0
        if active:
            c["employee_current"][fio] = {"Компания": "Завод А" if org == "o1" else "Завод Б",
                                          "Подразделение": c["dimensions"]["departments"][dep]}
        c["tabel"].append(fio + " " + final_name)
        if i % 9 == 0: c["tabel"].append(fio + " " + final_name)
        confirmed = 0 if i % 13 == 0 else 1
        c["tables"]["naryad"].append({"Пномер": order, "Номер_мк": order, "Твремя": 480,
            "Норма_времени": 400, "Коэфф_сложности": 1.1, "Внеплан": 0, "Подтвержд_вып": confirmed})
        c["tables"]["mk"].append({"Пномер": order, "Номер_проекта": f"PROJECT-{order}", "НомКплан": order})
        c["tables"]["plan"].append({"Пномер": order})
        selected = active and org == "o1" and dep == "d1"
        total = 0
        for j in range(fragments):
            number = i * fragments + j + 1
            norm = rng.randint(0, 7200) / 10
            started = j % 2 == 0
            c["tables"]["jurnal"].append(fragment(number, fio, order, norm,
                status="Начат" if started else "Завершен", date=f"2026-01-{1+j%28:02} 12:00:00"))
            if selected:
                if confirmed: expected_rows.append(number)
                if started: total += norm
        if selected: expected_norms[fio] = total
    c["erp"]["data"] = [{"Должность": s, "Подразделение": "Цех 1"} for s in sorted(erp_jobs)]
    c["golden"] = {"row_ids": expected_rows, "norms": expected_norms}
    return c
