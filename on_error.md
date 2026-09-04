

# юзнуть при максимальном пуле
```sql
SELECT name, setting
FROM pg_settings
WHERE name IN (
    'max_connections',
    'reserved_connections',
    'superuser_reserved_connections'
);

SELECT
    usename,
    application_name,
    client_addr,
    state,
    count(*) AS connections,
    min(backend_start) AS oldest_connection,
    max(now() - state_change) AS longest_state
FROM pg_stat_activity
WHERE backend_type = 'client backend'
GROUP BY usename, application_name, client_addr, state
ORDER BY connections DESC;

SELECT
    pid,
    datname,
    usename,
    application_name,
    client_addr,
    client_port,
    state,
    now() - backend_start AS connection_age,
    now() - state_change AS state_age,
    now() - xact_start AS transaction_age,
    wait_event_type,
    wait_event,
    left(query, 200) AS last_query
FROM pg_stat_activity
WHERE backend_type = 'client backend'
ORDER BY backend_start;
```

# на пк
```shell
Get-CimInstance Win32_Process |
    Where-Object { $_.Name -in @('python.exe', 'pythonw.exe') } |
    Sort-Object CreationDate |
    Select-Object ProcessId, ParentProcessId, CreationDate, CommandLine
```

