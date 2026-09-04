

# Трэйс при запуске mes_pg_migrate_2.py
```
Traceback (most recent call last):
  File "C:\DB_srv_test\mes_pg_migrate_2.py", line 916, in <module>
    raise SystemExit(main())
                     ~~~~^^
  File "C:\DB_srv_test\mes_pg_migrate_2.py", line 864, in main
    pg_conn = connect_pg(args.pg_dsn)
  File "C:\DB_srv_test\mes_pg_migrate_2.py", line 551, in connect_pg
    return psycopg.connect(**dsn)
           ~~~~~~~~~~~~~~~^^^^^^^
  File "C:\srv_mes\srv_mes\python\Lib\site-packages\psycopg\connection.py", line 122, in connect
    raise last_ex.with_traceback(None)
psycopg.OperationalError: connection failed: connection to server at "127.0.0.1", port 5432 failed: FATAL:  sorry, too many clients already

```
# ~ 25.08.2026 14:17 перезагрузка службы postgres


# ~ 26.08.2026 замечен вышеупомянутый трейс у юзера - были заменены логин и пароль dsn проблема ушла
```
WARNING:psycopg.pool:error connecting in 'mes-pg-client-10376': connection failed: connection to server at "192.168.100.135", port 5432 failed: server closed the connection unexpectedly
    This probably means the server terminated abnormally
    before or while processing the request.
WARNING:psycopg.pool:error connecting in 'mes-pg-client-10376': connection failed: connection to server at "192.168.100.135", port 5432 failed: FATAL: password authentication failed for user "postgres"
```
# 31.08.2026 лимит коннектов у второго разработчика (возможно что причина та же при дебаге или разработке мы открываем много соединений)
```
Backend QtAgg is interactive backend. Turning interactive mode on.
WARNING:psycopg.pool:error connecting in 'mes-pg-client-15888': connection failed: connection to server at "192.168.100.135", port 5432 failed: FATAL: sorry, too many clients already
WARNING:psycopg.pool:error connecting in 'mes-pg-client-15888': connection failed: connection to server at "192.168.100.135", port 5432 failed: FATAL: sorry, too many clients already
WARNING:psycopg.pool:error connecting in 'mes-pg-client-15888': connection failed: connection to server at "192.168.100.135", port 5432 failed: FATAL: sorry, too many clients already
```

# 01.09.2026 держалось недолго 3-5 минут (осуществлялся дебаг приложения)
```
WARNING:psycopg.pool:error connecting in 'mes-pg-client-15888': connection failed: connection to server at "192.168.100.135", port 5432 failed: FATAL: sorry, too many clients already
```