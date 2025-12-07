@echo off
copy /Y Z:\Setup\mini_git.py C:\Users\A.A.Fedorov\MES\KonstruktorRS\embed\mini_git.py
C:\Users\A.A.Fedorov\MES\py\python.exe mini_git.py
C:\Users\A.A.Fedorov\MES\py\python.exe constr_rc.py %*
