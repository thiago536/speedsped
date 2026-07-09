@echo off
REM =============================================================================
REM iniciar_daemon.bat — Inicia SpedGenerator em modo daemon (loop continuo)
REM
REM PC fica 24h ligado. Copiar para shell:startup (Win+R -> shell:startup)
REM
REM Logs principais vao para spedgenerator.log (com rotation automatica).
REM daemon.log e apenas fallback pra erros nao-capturados.
REM =============================================================================

cd /d "C:\SpedGenerator"

REM Descobrir executavel do Python
set "PYTHON_EXE=python"
for %%P in (
    "C:\Users\SERVIDOR SPED\AppData\Local\Python\pythoncore-3.14-64\python.exe"
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

REM Limpa daemon.log se maior que 5MB pra nao crescer infinito
for %%A in ("C:\ACS_Exporta\daemon.log") do if %%~zA GTR 5242880 (
    echo [%date% %time%] Log rotacionado > "C:\ACS_Exporta\daemon.log"
)

"%PYTHON_EXE%" main.py --daemon >> "C:\ACS_Exporta\daemon.log" 2>&1

