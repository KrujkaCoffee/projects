@echo off
cd "%~dp0"
TITLE mesinfo.powerz.ru
echo "%~dp0"
rem call ".\venv\Scripts\activate"
rem python ".\General.py"
rem set FLASK_APP=General
rem flask run --host=0.0.0.0 --port=20000 
rem python .\General.py
start "mesinfo.powerz.ru" powershell.exe -command "Get-Content ..\db_logs\flask_site.log -Wait -Tail 80 -Encoding UTF8"

