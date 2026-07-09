@echo off
REM =============================================================================
REM atualizar_backups.bat — Atualiza backups desatualizados via pg_dump
REM
REM Agendar no Task Scheduler:
REM   schtasks /create /tn "SpedGenerator_Backup" /tr "C:\Users\User 2\Documents\Claude\Projects\SpedGeneretor\atualizar_backups.bat" /sc daily /st 08:00
REM =============================================================================

cd /d "C:\SpedGenerator"

REM Descobrir executavel do Python
set "PYTHON_EXE=python"
for %%P in (
    "%USERPROFILE%\AppData\Local\Programs\Python\Python313\python.exe"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python310\python.exe"
    "C:\Users\SERVIDOR SPED\AppData\Local\Programs\Python\Python313\python.exe"
    "C:\Users\SERVIDOR SPED\AppData\Local\Programs\Python\Python312\python.exe"
    "C:\Users\SERVIDOR SPED\AppData\Local\Programs\Python\Python311\python.exe"
    "C:\Users\SERVIDOR SPED\AppData\Local\Programs\Python\Python310\python.exe"
    "C:\Users\User 2\AppData\Local\Programs\Python\Python313\python.exe"
    "C:\Users\User 2\AppData\Local\Programs\Python\Python312\python.exe"
    "C:\Users\User 2\AppData\Local\Programs\Python\Python311\python.exe"
    "C:\Users\User 2\AppData\Local\Programs\Python\Python310\python.exe"
    "C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe"
    "C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe"
    "C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe"
    "C:\Users\Administrator\AppData\Local\Programs\Python\Python310\python.exe"
    "C:\Users\Administrador\AppData\Local\Programs\Python\Python313\python.exe"
    "C:\Users\Administrador\AppData\Local\Programs\Python\Python312\python.exe"
    "C:\Users\Administrador\AppData\Local\Programs\Python\Python311\python.exe"
    "C:\Users\Administrador\AppData\Local\Programs\Python\Python310\python.exe"
    "C:\Program Files\Python313\python.exe"
    "C:\Program Files\Python312\python.exe"
    "C:\Program Files\Python311\python.exe"
    "C:\Program Files\Python310\python.exe"
    "C:\Program Files\Python39\python.exe"
) do (
    if exist "%%~P" (
        set "PYTHON_EXE=%%~P"
        goto :python_found
    )
)
:python_found

"%PYTHON_EXE%" backup_manager.py --todos >> "C:\Backups_Novo\backup_refresh.log" 2>&1

