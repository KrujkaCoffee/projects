@echo off
chcp 65001
SET "PYTHON_PATH=C:\srv_mes\srv_mes_2\python"
SET "MES_DB_LOGS=C:\srv_mes\srv_mes\db_logs"

REM
echo %PATH% | findstr /I /C:"%PYTHON_PATH%" >nul
IF %ERRORLEVEL% NEQ 0 (
    REM
    setx PATH "%PATH%;%PYTHON_PATH%"
    echo Путь к Python добавлен в переменную PATH.
) ELSE (
    echo Путь к Python уже существует в переменной PATH.
)
