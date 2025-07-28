@echo off
setlocal enabledelayedexpansion

rem
for /f "delims=" %%i in ('git describe --tags --abbrev=0') do set TAG=%%i

rem
echo !TAG! > ver.txt
