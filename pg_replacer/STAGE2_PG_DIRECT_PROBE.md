# MES → PostgreSQL: запуск Stage 2 direct-connection probe

Дата решения: 2026-08-18  
Артефакт runtime: `Cust_postgresql_executor.py`

## 1. Строгое решение

Прямое PostgreSQL-соединение со стороны клиента допускается к контролируемому
Stage 2, но ещё не к полному cutover.

Новый модуль уже является production-фундаментом будущего исполнителя:

- один ленивый `psycopg_pool.ConnectionPool` на процесс;
- `min_size=0`, `max_size=1`, освобождение простаивающего backend;
- process/fork guard, явное закрытие и защитные таймауты;
- прежняя сигнатура `custom_request_c(...)` и основные формы результата;
- явные многошаговые транзакции на одном соединении;
- единственный автоповтор только очевидного чтения после потери связи;
- записи и `COMMIT` автоматически не повторяются;
- ошибка `PostgresCommitOutcomeUnknown` вынуждает сверить результат, а не
  создать дубль;
- безопасное quoting схем через `psycopg.sql.Identifier`;
- отдельный неблокирующий Stage 2 probe с bounded queue, circuit breaker и
  локальной/опциональной центральной статистикой.

Однако модуль пока нельзя объявлять полной drop-in заменой `Cust_SQLite.py`.
Отложенные гейты — SQLite→PG SQL-совместимость, редкие legacy-комбинации
результатов и контрактные тесты реальных запросов. Stage 2 их не проверяет:
`SELECT 123` измеряет соединения, частоту, RTT и отказоустойчивость, но не CPU,
I/O, блокировки и план исполнения бизнес-SQL.

## 2. Почему кэш во время этого теста отключать не надо

Отключение клиентского/серверного кэша меняет production-нагрузку и повышает
риск для пользователя. Нужную частоту можно получить без этого:

1. существующий `lazy_method_hours` сначала имеет право вернуть локальный
   результат;
2. сразу после него вызывается `stage2_observe_request(...)`;
3. затем работает прежний путь `Cust_client_socket` и его кэш;
4. SQLite остаётся единственным источником пользовательского результата.

Так probe видит каждый логический запрос, дошедший до транспортного слоя, в том
числе будущие client/server cache hits. При этом пользовательский трафик и
ответы не меняются. Отключённый кэш дал бы другой эксперимент — стресс-тест
SQLite/transport, а не оценку direct PG connections.

## 3. Подготовка PostgreSQL

### 3.1. Сначала зафиксировать фактические пределы

Выполнить от административной роли:

```sql
SELECT version();
SHOW max_connections;
SHOW superuser_reserved_connections;
SHOW shared_buffers;
SHOW work_mem;
SHOW idle_session_timeout;
SHOW idle_in_transaction_session_timeout;
SHOW statement_timeout;

SELECT count(*) AS current_sessions
FROM pg_stat_activity;
```

Нельзя принимать решение только по Xeon E5-2698 v4 и 32 ГБ RAM. Для
`SELECT 123` CPU практически не является ограничителем. Реальные гейты:
`max_connections`, память backend-процессов, сетевой handshake, TLS/SSPI,
Hyper-V storage и будущая конкурентность тяжёлых запросов. `work_mem` может
расходоваться несколькими операциями одного запроса, поэтому простое повышение
`max_connections` не является бесплатным.

### 3.2. Отдельная минимально привилегированная роль

Для Stage 2 роль не должна читать бизнес-таблицы. Ей нужны `CONNECT`, выполнение
константного `SELECT` и, если включена центральная телеметрия, права только на
одну таблицу статистики.

Пример DDL; пароль/SSPI и `CONNECTION LIMIT` выбрать по политике организации:

```sql
CREATE SCHEMA IF NOT EXISTS mes_probe;

CREATE TABLE IF NOT EXISTS mes_probe.client_sessions (
    session_id   text PRIMARY KEY,
    client_id    text NOT NULL,
    app_name     text NOT NULL,
    app_version  text NOT NULL DEFAULT '',
    process_id   integer NOT NULL,
    started_at   timestamptz NOT NULL,
    last_seen_at timestamptz NOT NULL,
    snapshot     jsonb NOT NULL,
    received_at  timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS ix_mes_probe_client_sessions_last_seen
    ON mes_probe.client_sessions (last_seen_at DESC);

-- Выполнить в соответствии с локальной политикой создания LOGIN/SSPI-role.
-- ALTER ROLE mes_probe_client CONNECTION LIMIT 140;
ALTER ROLE mes_probe_client SET statement_timeout = '2s';
ALTER ROLE mes_probe_client SET lock_timeout = '1s';
ALTER ROLE mes_probe_client SET idle_in_transaction_session_timeout = '10s';

GRANT CONNECT ON DATABASE mes TO mes_probe_client;
GRANT USAGE ON SCHEMA mes_probe TO mes_probe_client;
GRANT INSERT (session_id, client_id, app_name, app_version, process_id,
              started_at, last_seen_at, snapshot)
    ON mes_probe.client_sessions TO mes_probe_client;
GRANT UPDATE (last_seen_at, snapshot, received_at)
    ON mes_probe.client_sessions TO mes_probe_client;
GRANT SELECT (session_id) ON mes_probe.client_sessions TO mes_probe_client;
```

Число `140` выше — только иллюстрация синтаксиса, не рекомендация. Лимит роли
должен быть меньше доступного общего бюджета с сохранением административного и
аварийного резерва. Если доступно доменное SSPI, предпочтительно не раздавать
общий пароль. При password auth использовать SCRAM и TLS
(`sslmode=verify-full`), а DSN хранить вне исходников и логов.

Официальные справки: [Psycopg connection pools](https://www.psycopg.org/psycopg3/docs/advanced/pool.html),
[PostgreSQL connection settings](https://www.postgresql.org/docs/current/runtime-config-connection.html),
[SSPI authentication](https://www.postgresql.org/docs/current/sspi-auth.html).

## 4. Установка и конфигурация клиента

### 4.1. Файлы и зависимости

1. Скопировать `Cust_postgresql_executor.py` в
   `project_cust_38/Cust_postgresql_executor.py`.
2. Зафиксировать одну проверенную версию Psycopg 3 в дистрибутиве приложений,
   например диапазон:

   ```text
   psycopg[binary,pool]>=3.2,<4
   ```

3. До интеграции выполнить безопасный self-test — он не использует сеть:

   ```bash
   python project_cust_38/Cust_postgresql_executor.py
   ```

   Ожидаемый итог:

   ```text
   SELF-TEST OK: executor helpers, formatter, queue и circuit breaker
   ```

4. На одной тестовой машине явно проверить DSN:

   ```bash
   python project_cust_38/Cust_postgresql_executor.py --live-probe --count 3
   ```

   Команда не печатает DSN или пароль.

### 4.2. Переменные окружения Stage 2

Минимальный профиль:

```text
MES_PG_DSN=host=<host> port=5432 dbname=<db> user=mes_probe_client password=<secret> sslmode=verify-full
MES_PG_APPLICATION_NAME=Mkarti-stage2
MES_PG_POOL_MIN_SIZE=0
MES_PG_POOL_MAX_SIZE=1
MES_PG_POOL_TIMEOUT_SEC=3
MES_PG_POOL_MAX_WAITING=8
MES_PG_CONNECT_TIMEOUT_SEC=3
MES_PG_MAX_IDLE_SEC=300
MES_PG_MAX_LIFETIME_SEC=1800
MES_PG_RECONNECT_TIMEOUT_SEC=5
MES_PG_TCP_USER_TIMEOUT_MS=10000
MES_PG_KEEPALIVES_IDLE_SEC=10
MES_PG_KEEPALIVES_INTERVAL_SEC=3
MES_PG_KEEPALIVES_COUNT=3
MES_PG_STATEMENT_TIMEOUT_MS=2000
MES_PG_LOCK_TIMEOUT_MS=1000
MES_PG_IDLE_IN_TRANSACTION_TIMEOUT_MS=10000

MES_PG_PROBE_ENABLED=1
MES_PG_PROBE_QUEUE_SIZE=256
MES_PG_PROBE_FAILURE_THRESHOLD=3
MES_PG_PROBE_COOLDOWN_STEPS_SEC=60,300,900
MES_PG_PROBE_CONNECTION_TIMEOUT_SEC=2
MES_PG_PROBE_STALL_TIMEOUT_SEC=15
MES_PG_PROBE_FLUSH_INTERVAL_SEC=60
MES_PG_PROBE_WORKER_IDLE_EXIT_SEC=30
MES_PG_PROBE_TELEMETRY_TABLE=mes_probe.client_sessions
MES_PG_PROBE_SPOOL_DIR=<локальный каталог с правом записи>
MES_PG_PROBE_IDENTITY_SALT=<одинаковая случайная строка для пилотной группы>
MES_APP_VERSION=<версия приложения>
```

Для каждого приложения задать отдельный `MES_PG_APPLICATION_NAME`, например
`Mkarti-stage2`, `Sozdanie-stage2`, `Vipolnenie-stage2`, `TehKarti-stage2`.
Это позволяет отделить стартовый SQL-шторм конкретной программы.

Пароль нельзя помещать в `.py`, Git, GUI exception и telemetry. Если текущий
механизм доставки не умеет безопасно передавать секрет или SSPI, это отдельный
security blocker для массового direct connection.

`MES_PG_SCHEMA_MAP_JSON` Stage 2 не нужен. Он станет обязательным при включении
настоящих запросов. Пример формы, где справа должны стоять фактические имена
перенесённых схем:

```text
MES_PG_SCHEMA_MAP_JSON={"Naryad":"naryad_stage","BD_users":"users_stage","DB_kplan":"kplan_stage"}
```

## 5. Минимальное внедрение в `Cust_SQLite.py`

Production-файл в данном комплекте намеренно не изменён. Применить следующий
малый патч после проверки пути импорта.

В секции import:

```python
try:
    from project_cust_38 import Cust_postgresql_executor as CPG
except Exception:
    CPG = None

# Читает env, но не открывает соединение и не запускает worker до первого hook.
_PG_STAGE2_READY = bool(CPG and CPG.configure_default_from_env(strict=False))
```

В `custom_request_c(...)` вставить hook строго после возможного возврата из
локального `lazy_method_hours` cache и непосредственно перед текущим блоком
`if 'SRV:' in bd:`:

```python
    # Stage 2: fire-and-forget. Результат PostgreSQL не влияет на SQLite-ответ.
    if _PG_STAGE2_READY:
        CPG.stage2_observe_request(bd, custom_request_c)

    if 'SRV:' in bd:
        # существующий код без изменений
        ...
```

Не помещать `SELECT 123` непосредственно в `custom_request_c`, не создавать
там `psycopg.connect()` и не ждать `Future.result()`. Только `put_nowait` в
bounded queue обеспечивает silence-семантику.

После 30 секунд без событий worker записывает финальный snapshot и завершается.
Поэтому минутный telemetry flush не превращается в вечный heartbeat: соединение
остаётся нетронутым и затем закрывается пулом по `MES_PG_MAX_IDLE_SEC`.
Session `statement_timeout` задаётся одним configure-запросом при открытии
соединения, а не на каждый probe; TCP user-timeout/keepalive страхуют half-open
network path. Параметры и платформенные ограничения описаны в
[libpq connection parameters](https://www.postgresql.org/docs/current/libpq-connect.html).
Если synchronous worker всё же не вернулся за 15 секунд, hook помечает stall,
открывает breaker и перестаёт добавлять новые сетевые попытки. Зависший daemon
worker не блокирует GUI; очередь остаётся ограниченной.

На штатном завершении Qt желательно вызвать:

```python
app.aboutToQuit.connect(CPG.shutdown_default_runtime)
```

`atexit` уже зарегистрирован как страховка. Повторный shutdown безопасен.

### Быстрый rollback

1. Установить `MES_PG_PROBE_ENABLED=0` и перезапустить приложение.
2. Hook останется no-op; SQLite/HTTP путь не меняется.
3. При недоступной БД автоматический circuit breaker сам прекращает попытки на
   `60 → 300 → 900` секунд с jitter и допускает только один half-open probe.

## 6. Как проверяется корректность silence-теста

### 6.1. Клиентский invariant

Каждый snapshot содержит:

```text
eligible = terminal + pending
```

Где `terminal` — сумма success, timeout, error, queue drop, breaker/disabled/
shutdown skip; `pending` — события в очереди и in-flight. Поле
`probe.accounting.valid` должно быть `true`. Стойкий `false` два flush-интервала
подряд означает дефект telemetry, а не проблему PostgreSQL.

В telemetry отсутствуют SQL-тексты, параметры, ФИО и raw computer name.
Сохраняются только тип операции (`SELECT`, `UPDATE`...), alias БД, счётчики,
RTT, pool stats и salted hash клиента.

Назначить retention: например, nightly удалять строки
`last_seen_at < now() - interval '14 days'` и так же чистить старые локальные
JSON snapshots. Модуль намеренно сам не удаляет файлы пользователя.

### 6.2. Центральная сверка

Актуальные процессы и несколько экземпляров приложения:

```sql
SELECT
    app_name,
    client_id,
    count(*) AS app_processes,
    max(last_seen_at) AS last_seen
FROM mes_probe.client_sessions
WHERE last_seen_at >= now() - interval '3 minutes'
GROUP BY app_name, client_id
ORDER BY app_name, client_id;
```

Суммарный исход:

```sql
SELECT
    sum((snapshot #>> '{probe,counters,eligible_requests}')::bigint) AS eligible,
    sum(coalesce((snapshot #>> '{probe,counters,probe_success}')::bigint, 0)) AS success,
    sum(coalesce((snapshot #>> '{probe,counters,probe_timeout}')::bigint, 0)) AS timeout,
    sum(coalesce((snapshot #>> '{probe,counters,probe_error}')::bigint, 0)) AS error,
    sum(coalesce((snapshot #>> '{probe,counters,queue_dropped}')::bigint, 0)) AS queue_dropped,
    sum(coalesce((snapshot #>> '{probe,counters,breaker_skipped}')::bigint, 0)) AS breaker_skipped
FROM mes_probe.client_sessions
WHERE last_seen_at >= now() - interval '10 minutes';
```

Текущие соединения:

```sql
SELECT
    application_name,
    state,
    count(*) AS sessions,
    max(clock_timestamp() - state_change) AS max_state_age
FROM pg_stat_activity
WHERE datname = current_database()
GROUP BY application_name, state
ORDER BY application_name, state;

SELECT count(*)
FROM pg_stat_activity
WHERE application_name LIKE '%-stage2'
  AND state = 'idle in transaction';
```

Последний запрос обязан всегда возвращать `0`. Probe работает в autocommit и
не должен оставлять `idle in transaction`.

Если `pg_stat_statements` уже включён:

```sql
SELECT calls, rows, total_exec_time, mean_exec_time
FROM pg_stat_statements
WHERE query ILIKE '%mes_connection_probe%';
```

Сумма client `probe_success` должна быть близка к приросту `calls`. Допустимая
разница — задержка flush, ручной `--live-probe`, reset статистики и незавершённые
сессии. Статистика PostgreSQL описана в
[Monitoring Database Activity](https://www.postgresql.org/docs/current/monitoring-stats.html)
и [pg_stat_statements](https://www.postgresql.org/docs/current/pgstatstatements.html).

### 6.3. Метрики хоста/Hyper-V

Снимать с интервалом 10–15 секунд:

- CPU host и VM, steal/ready time гипервизора;
- available/committed RAM и swap/page faults;
- PostgreSQL RSS/PSS в сумме, не только один backend;
- disk latency/queue, WAL bytes, temp files/temp bytes;
- network RTT, retransmits и connection handshakes;
- `numbackends`, commits/rollbacks, deadlocks, blocks read/hit;
- application startup time и число пользовательских timeout/error dialogs.

## 7. План длительности и расширения когорты

Один-два дня достаточны только для smoke-test. Для решения о direct connection
рекомендовано пять рабочих дней, потому что нужны как минимум два утренних
старта, рабочий пик и период простоя дольше `max_idle_sec`.

| Фаза | Когорта | Длительность | Цель |
|---|---:|---:|---|
| Preflight | 1–2 машины разработчиков | 30–60 минут | DSN, TLS/SSPI, DDL, self/live test |
| A | 10 процессов | 1 полный рабочий день | стартовый SQL-шторм, breaker, влияние на GUI |
| B | 35–40 процессов | 1 полный рабочий день | нелинейность connection churn/RTT |
| C | 81 отмеченный пользователь | 2 полных рабочих дня | два пика и обычный день |
| D | до 102 пользователей/все приложения | 1 рабочий день | worst observed process count |

Минимально допустимый срок — три полных рабочих дня, только если попали два
утренних старта и есть достоверная центральная telemetry. Для SQL-совместимости
этого всё равно недостаточно: Stage 3 должен идти отдельно до стабилизации
новых fingerprint/ошибок, ориентир — не менее пяти рабочих дней.

## 8. Критерии продолжения и остановки

Расширять когорту можно только при выполнении всех условий:

- пользовательский SQLite/HTTP результат и число ошибок не изменились;
- `pool_max=1`, а `pool_size` одного процесса никогда не превышает `1`;
- `idle in transaction = 0` для Stage 2 приложений;
- `queue_dropped = 0`; предупредительный предел — `0.1%` eligible;
- p95 `queue_wait_ms` ниже 250 мс вне краткого cold-start burst;
- `probe_timeout + probe_error < 0.1%` выполненных попыток на здоровой сети;
- breaker не открывается систематически;
- `probe_stall_detected = 0`;
- p95 `SELECT 123` не хуже удвоенного baseline и обычно ниже 50 мс в LAN;
- p99 ниже 200 мс либо есть документированное сетевое объяснение;
- persistent `accounting.valid = true`;
- общий connection budget сохраняет минимум 30% headroom;
- CPU, RAM, disk latency и время запуска приложений не имеют статистически
  заметной регрессии относительно baseline.

Немедленно остановить расширение когорты при любом из событий:

- Stage 2 соединения устойчиво занимают ≥70% `max_connections`; при ≥80%
  отключить probe для всей когорты;
- появился хотя бы один долгий `idle in transaction`;
- users видят новые freeze/timeout/error dialogs;
- queue drop ≥0.1%, timeout/error ≥0.5% или повторяющийся breaker open;
- появился хотя бы один повторяемый `probe_stall_detected`;
- очередь устойчиво ждёт секунды: один connection уже не успевает за cadence;
- заметен connection storm: `connections_num` приближается к числу probes
  вместо одного соединения на активный период процесса;
- Hyper-V/БД входит в memory pressure, swap или растёт disk latency.

Пороговые числа — стартовые эксплуатационные guardrails, а не SLA. После
baseline их можно ужесточить, но нельзя ослаблять только ради «зелёного» теста.

## 9. Проверка connection budget для текущей оценки

До резерва и администраторских соединений:

Это верхняя оценка одновременного активного/недавно активного контура, а не
обещание постоянно держать столько backend: `min_size=0` и `max_idle=300`
должны уменьшить наблюдаемый peak. Именно величину этого уменьшения измеряет
Stage 2.

Четыре шардированные группы в текущем `Srv_tcp.py` дают 4 × 9 = 36
процессов. Если одновременно работают и четыре оставшихся SQLite-сервиса из
известного alias contour, серверная часть достигает 40 процессов.

| Сценарий | Клиентские процессы | Server contour | Итого |
|---|---:|---:|---:|
| 81 пользователь × 1 экземпляр | 81 | 36–40 | 117–121 |
| 102 пользователя × 1 экземпляр | 102 | 36–40 | 138–142 |
| 81 пользователь × 2 экземпляра | 162 | 36–40 | 198–202 |
| 102 пользователя × 2 экземпляра | 204 | 36–40 | 240–244 |

Затем добавить monitoring/admin/migration reserve — практически ещё 15–25
соединений. Поэтому `max_connections=100` заведомо не подходит, а значение
около 150 не покрывает несколько экземпляров. Это не означает, что нужно сразу
ставить 260+: сначала Stage 2 должен показать реальный peak process count и
фактическую память backend. Если worst case близок к таблице, варианты — жёстче
закрывать idle pool, ограничивать несколько экземпляров, разделять когорты или
вводить PgBouncer с отдельно проверенной транзакционной семантикой.

## 10. Будущее включение настоящего executor

После Stage 3 и явного schema map одиночный PG-native запрос выглядит так:

```python
from project_cust_38 import Cust_postgresql_executor as CPG

CPG.configure_default_from_env(strict=True)

row = CPG.custom_request_c(
    "Naryad.db",
    "SELECT \"Пномер\", \"Статус\" FROM naryad WHERE \"Пномер\" = %s",
    list_of_lists_c=[[nom_nar]],
    rez_dict=True,
    one=True,
)
```

Атомарная бизнес-операция:

```python
with CPG.transaction("Naryad.db", isolation="READ COMMITTED") as tx:
    current = tx.execute(
        "SELECT \"Статус\" FROM naryad WHERE \"Пномер\" = %s FOR UPDATE",
        list_of_lists_c=[[nom_nar]],
        hat_c=False,
        one=True,
        one_column=True,
    )
    tx.execute(
        "UPDATE naryad SET \"Статус\" = %s WHERE \"Пномер\" = %s",
        list_of_lists_c=[[new_status, nom_nar]],
    )
    tx.execute(
        "INSERT INTO status_audit(naryad_id, old_status, new_status) VALUES (%s, %s, %s)",
        list_of_lists_c=[[nom_nar, current, new_status]],
    )
```

Транзакцию держать короткой: никаких GUI dialogs, ожидания пользователя,
HTTP/ERP вызовов или тяжёлых вычислений внутри `with`. При `max_size=1` длинная
транзакция блокирует остальные PG-вызовы данного процесса до pool timeout.

На этом этапе SQL должен быть уже PG-native (`%s`, корректные quotes и функции).
Модуль специально не делает `.replace('?', '%s')`, `.replace('==', '=')` и
другие неоднозначные подмены. Проверенный `Cust_pgsql_mutator` позже подключается
через `sql_preparer`, но только после Stage 3 статистики и строгих blocking
issues.

## 11. Итоговый gate

Stage 2 считается успешным, если пять рабочих дней показывают безопасный
connection budget, отсутствие влияния на пользователя, нулевые
`idle in transaction`, контролируемый churn и согласованную telemetry.

Успех Stage 2 разрешает перейти к Stage 3 capture/replay и контрактным тестам.
Он не разрешает массово выполнять бизнес-SQL в PostgreSQL без этих тестов.
