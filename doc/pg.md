#

```sql
SHOW max_identifier_length;
```


# src/include/pg_config_manual.h

# #define NAMEDATALEN 64
# #define NAMEDATALEN 256


```shell
meson setup build --prefix=C:\PostgreSQL-custom
meson compile -C build
meson install -C build
```

```
SELECT
  COUNT(*) AS total_connections,
  SUM(CASE WHEN state <> 'idle' THEN 1 ELSE 0 END) AS non_idle_connections,
  SUM(CASE WHEN state = 'active' THEN 1 ELSE 0 END) AS active_connections
FROM pg_stat_activity;
```


```sql
SELECT
  pid,
  usename,
  application_name,
  client_addr,
  state,
  now() - backend_start AS connection_age,
  now() - xact_start AS transaction_age,
  now() - query_start AS query_age,
  wait_event_type,
  wait_event,
  query
FROM pg_stat_activity
ORDER BY
  COALESCE(query_start, xact_start, backend_start) NULLS LAST;
```


```sql
SET search_path = ...
```