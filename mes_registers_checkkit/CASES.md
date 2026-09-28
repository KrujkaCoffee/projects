Целевые сценарии сравнения `get_filtr_dolgn` и `mes_registers.employee`.

Статус — ожидаемый результат сравнения, а не статус прохождения теста. `DIFFERENT`, `BLOCKED` и `INCONCLUSIVE` должны быть обнаружены; они не разрешают внедрение.

| Сценарий | Что проверяет | Ожидание |
|---|---|---|
| `01_base` | Две должности; одна строка Начат и одна Завершен у каждого сотрудника. | `MATCH` |
| `02_timesheet_from_db` | Ветка tabel_m=None с чтением mtdz. | `MATCH` |
| `03_duplicate_timesheet` | Повтор ФИО в табеле не умножает строки IN. | `MATCH` |
| `04_duplicate_erp_positions` | Дубли должностей и порядок не влияют на membership. | `MATCH` |
| `05_same_title_different_guid` | Два GUID с одинаковым названием должности. | `MATCH` |
| `06_other_department` | Состояние другого подразделения не добавляет должность. | `MATCH` |
| `07_other_organization` | Состояние другой организации не добавляет должность. | `MATCH` |
| `08_future_event` | Событие после зафиксированного as_of не попадает в срез. | `MATCH` |
| `09_tie_breaker_id` | При одинаковом Период выбирается больший id. | `MATCH` |
| `10_iso_separator` | Смешанные T и пробел в датах одного календарного дня. | `MATCH` |
| `11_dismissed_removed_by_current_dict` | dict_emploee_full уже исключил уволенного; регистр оставляет событие. | `MATCH` |
| `12_rehire` | Увольнение и повторный прием; последнее состояние доступно. | `MATCH` |
| `13_current_position_changed` | Оба текущих источника видят новую должность; старый табель исключает ФИО. | `MATCH` |
| `14_month_end_is_not_current` | Замена текущего источника на срез конца месяца меняет набор должностей. | `DIFFERENT` |
| `15_two_contracts_one_person` | Два Сотрудник_Key одного физлица; employee.all_at сворачивает их. | `DIFFERENT` |
| `16_never_in_erp_timesheet` | Новый человек есть в КадроваяИстория, но его еще нет ни в одном табеле 1С. | `DIFFERENT` |
| `17_mes_sync_lag` | В 1С новая должность, MES еще содержит прежнюю. | `DIFFERENT` |
| `18_department_transfer_lag` | Перевод в другой цех отражен только в MES. | `DIFFERENT` |
| `19_excluding_dismissal_changes_positions` | Дополнительный фильтр Событие=Увольнение меняет старую семантику. | `DIFFERENT` |
| `20_missing_position_mapping` | Неизвестный GUID должности должен быть ошибкой, а не молчаливым пропуском. | `BLOCKED` |
| `21_missing_department_mapping` | Неизвестный GUID подразделения. | `BLOCKED` |
| `22_filial_mapping_unverified` | Нет явного соответствия Филиал.Наименование и Организация_Key. | `BLOCKED` |
| `23_wrong_org_guid` | Неверный GUID дает пустой регистр и совпавший SQL fallback; это не доказательство. | `INCONCLUSIVE` |
| `24_corrupt_history_date` | Некорректный Период блокирует strict_dates даже у другого сотрудника. | `BLOCKED` |
| `25_aware_as_of` | Timezone-aware as_of не принимается данным API регистра. | `BLOCKED` |
| `26_erp_empty` | HTTP 200 и data=[] ведут в dolgn_etap; совпадение не аттестует замену. | `INCONCLUSIVE` |
| `27_erp_http_error` | HTTP 500 с совпадающим SQL fallback. | `INCONCLUSIVE` |
| `28_erp_transport_exception` | Исключение API старым кодом не перехватывается. | `BLOCKED` |
| `29_erp_missing_data` | HTTP 200 без ключа data вызывает KeyError в исходнике. | `BLOCKED` |
| `30_register_empty_fallback` | Пустая КадроваяИстория и совпавший dolgn_etap. | `INCONCLUSIVE` |
| `31_register_empty_strict` | Пустой регистр без fallback показывает потерю выборки. | `DIFFERENT` |
| `32_register_error_fallback` | Даже одинаковые результаты при подавленной ошибке регистра не дают MATCH. | `INCONCLUSIVE` |
| `33_no_organization_guard` | Возврат None оставляет SQL без фильтра ФИО; это старое поведение. | `INCONCLUSIVE` |
| `34_empty_fallback_lists` | [] в обоих источниках: SQLite IN () пуст; источник не подтвержден. | `INCONCLUSIVE` |
| `35_no_current_employee` | Отсутствующий в текущем словаре сотрудник исключается. | `MATCH` |
| `36_company_comes_from_config` | company из Config.place.Имя, отдельно от аргумента organization. | `MATCH` |
| `37_whitespace_in_timesheet` | split() сворачивает повторные пробелы табеля. | `MATCH` |
| `38_case_sensitive_title` | Сварщик и сварщик не равны; регистр не должен менять правило. | `MATCH` |
| `39_two_word_fio` | Парсер первых трех слов теряет должность при ФИО без отчества. | `MATCH` |
| `40_position_trailing_space` | Название справочника с пробелом нельзя незаметно strip(). | `DIFFERENT` |
| `41_unconfirmed_order` | Неподтвержденный наряд исключен из spis_jur_full, но норма Начат остается. | `MATCH` |
| `42_unconfirmed_unplanned_code` | Код НеподтвержденныйВнеплан удаляет строки, но не норму Начат. | `MATCH` |
| `43_unknown_unplanned_code` | Нет кода в справочнике: WHERE по LEFT JOIN исключает строки. | `MATCH` |
| `44_other_poki` | Код существует, но относится к другому poki. | `MATCH` |
| `45_missing_inner_join` | Отсутствующий mk исключает строки INNER JOIN. | `MATCH` |
| `46_left_join_multiplies_rows` | Дубли пл_оуп умножают строки и норму; нельзя сравнивать только set(id). | `MATCH` |
| `47_time_boundaries` | 05:00 включено; 04:59:00 следующего месяца включено; 04:59:01 исключено. | `MATCH` |
| `48_comma_and_exponent` | F.valm обрабатывает десятичную запятую и экспоненту. | `MATCH` |
| `49_negative_norm` | Отрицательные числовые нормы суммируются исходником. | `MATCH` |
| `50_non_numeric_start` | Пустая норма Начат требует записи через Jurnal_nar; стенд блокирует ее. | `BLOCKED` |
| `51_non_numeric_finish` | Пустая норма Завершен не запускает ветку ремонта. | `MATCH` |
| `52_nan_string_converts_to_zero` | is_numeric('NaN') истинно, но текущий F.valm('NaN') возвращает 0. | `MATCH` |
| `53_no_started_rows` | Сотрудники в журнале получают ноль, если нет Начат. | `MATCH` |
| `54_same_department_name_two_guids` | Старый WHERE отбирает по имени; новый сохраняет это правило. | `MATCH` |
| `55_leap_february` | Полный февраль високосного года, граница 29 февраля. | `MATCH` |
| `56_year_boundary` | Переход декабрь-январь. | `MATCH` |
| `57_missing_norm_unconfirmed` | Неподтвержденная строка Начат с плохой нормой все равно запускает ремонт. | `BLOCKED` |
| `58_absent_month_timesheet` | Пустой переданный табель дает пустую выборку при непустых должностях. | `MATCH` |
| `59_infinite_norm_is_blocked` | F.valm('1e999') дает бесконечность; совпадение не аттестуется. | `BLOCKED` |

Дополнительно `volume_case` генерирует случайные истории со стабильным seed и независимыми ожидаемыми ID/нормами, а `test_capture.py` проверяет четыре последовательных чтения и обнаружение нестабильности.
