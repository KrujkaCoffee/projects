@echo off
cd "%~dp0"
TITLE mesinfo.powerz.ru
call ".\venv\Scripts\activate"
rem python ".\General.py"
rem set FLASK_APP=General
rem flask run --host=0.0.0.0 --port=20000
python .\General.py
pause
