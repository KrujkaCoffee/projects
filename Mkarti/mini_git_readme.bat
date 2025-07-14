@echo off
chcp 1251
setlocal

for /f "delims=" %%i in ('python mini_git.py --help') do (
    set "help_text=%%i"
    echo %%i
)

start powershell -WindowStyle Hidden -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('%help_text%', 'Справка')"

endlocal
