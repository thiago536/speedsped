@echo off
REM =============================================================================
REM finalizar_sistema.bat — Encerra DEFINITIVAMENTE o SpedGenerator
REM =============================================================================

echo ============================================
echo   SpedGenerator - Finalizando sistema...
echo ============================================
echo.

set "LOCK_FILE=C:\ACS_Exporta\spedgenerator.lock"

echo ========================================= >> "C:\ACS_Exporta\daemon.log"
echo [%date% %time%] FINALIZANDO SISTEMA DEFINITIVAMENTE... >> "C:\ACS_Exporta\daemon.log"

REM 1. Encerra processos Python específicos do SpedGenerator via PowerShell (seguro e limpo)
echo [1/5] Encerrando processos Python (daemon e painel)...
powershell -Command "Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*main.py*' -or $_.CommandLine -like '*painel.py*' -or $_.CommandLine -like '*command_processor*' } | Stop-Process -Force" >> "C:\ACS_Exporta\daemon.log" 2>&1
taskkill /f /t /im python.exe >> "C:\ACS_Exporta\daemon.log" 2>&1
taskkill /f /t /im pythonw.exe >> "C:\ACS_Exporta\daemon.log" 2>&1

REM 2. Encerra o ACS Gerente, AutoHotkey e scripts AHK com a árvore inteira de processos (/t)
echo [2/5] Encerrando ACS Gerente e automacoes...
taskkill /f /t /im gerente.exe >> "C:\ACS_Exporta\daemon.log" 2>&1
taskkill /f /t /im AutoHotkey.exe >> "C:\ACS_Exporta\daemon.log" 2>&1

REM 3. Encerra processos remanescentes de banco de dados (pg_dump, pg_restore, psql) para liberar CPU/HD
echo [3/5] Encerrando downloads e restauracoes de bancos (pg_dump/pg_restore)...
taskkill /f /t /im pg_dump.exe >> "C:\ACS_Exporta\daemon.log" 2>&1
taskkill /f /t /im pg_restore.exe >> "C:\ACS_Exporta\daemon.log" 2>&1
taskkill /f /t /im psql.exe >> "C:\ACS_Exporta\daemon.log" 2>&1

REM 4. Remove o arquivo de lock para liberar execucoes futuras
echo [4/5] Liberando arquivos de lock...
if exist "%LOCK_FILE%" (
    del /f /q "%LOCK_FILE%" >> "C:\ACS_Exporta\daemon.log" 2>&1
)

REM 5. Encerra janelas CMD orfãs do daemon
echo [5/5] Finalizando janelas de console...
powershell -Command "Get-Process -Name cmd -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -eq 'SpedGenerator_Daemon' } | Stop-Process -Force" >> "C:\ACS_Exporta\daemon.log" 2>&1

echo [%date% %time%] SISTEMA ENCERRADO DEFINITIVAMENTE. >> "C:\ACS_Exporta\daemon.log"
echo ========================================= >> "C:\ACS_Exporta\daemon.log"

echo.
echo [OK] Sistema finalizado com sucesso!
echo [OK] Todos os downloads e automacoes foram parados e os locks liberados.
echo.
REM Usa ping como fallback robusto para o comando timeout em ambientes com redirecionamento de entrada
ping -n 4 127.0.0.1 >nul
