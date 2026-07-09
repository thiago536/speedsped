@echo off
REM =============================================================================
REM iniciar_sistema.bat — Ponto unico de entrada DEFINITIVO do SpedGenerator
REM =============================================================================

echo ============================================
echo   SpedGenerator - Iniciando sistema...
echo ============================================
echo.

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

REM 1. Roda o script de parada primeiro para limpar qualquer execucao anterior travada
echo [INFO] Limpando processos and locks anteriores...
call finalizar_sistema.bat

echo.
echo [INFO] Iniciando daemon em background (modo oculto/minimizado)...
start "SpedGenerator_Daemon" /min cmd /c ""%PYTHON_EXE%" main.py --daemon >> C:\ACS_Exporta\daemon.log 2>&1"

echo [INFO] Aguardando inicializacao do daemon...
REM Usa ping como fallback robusto para o comando timeout em ambientes com redirecionamento de entrada
ping -n 4 127.0.0.1 >nul

echo [INFO] Abrindo painel de controle...
start "" "%PYTHON_EXE%" painel.py

echo [INFO] Abrindo indicador de status na tela...
set "PYTHONW_EXE=%PYTHON_EXE:python.exe=pythonw.exe%"
if exist "%PYTHONW_EXE%" (
    start "" "%PYTHONW_EXE%" overlay_status.py
) else (
    start "SpedGenerator_Overlay" /min "%PYTHON_EXE%" overlay_status.py
)

echo.
echo [OK] Sistema iniciado com sucesso!
echo [OK] O daemon detectara automaticamente quais postos faltam ser gerados.
echo.
REM Usa ping como fallback robusto para o comando timeout em ambientes com redirecionamento de entrada
ping -n 6 127.0.0.1 >nul
