@echo off
rem ===========================================================================
rem iniciar_monitor.bat — Sobe o dashboard web de monitoramento (porta 8777)
rem Acesso: http://localhost:8777  ou  http://IP-DESTA-MAQUINA:8777
rem Somente leitura — nao interfere no daemon.
rem Se ja estiver rodando, apenas abre o navegador.
rem ===========================================================================
cd /d C:\SpedGenerator

set "PYTHON_EXE=C:\Users\SERVIDOR SPED\AppData\Local\Python\pythoncore-3.14-64\python.exe"
set "PYTHONW_EXE=C:\Users\SERVIDOR SPED\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe"

rem Porta 8777 ja em uso? Entao o monitor ja esta no ar — so abre o navegador.
netstat -ano | findstr ":8777" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo [OK] Monitor ja esta rodando. Abrindo navegador...
    goto :abrir
)

echo [INFO] Iniciando Monitor Web em background...
if exist "%PYTHONW_EXE%" (
    start "" "%PYTHONW_EXE%" monitor_web.py
) else (
    start "SpedGenerator_Monitor" /min cmd /c ""%PYTHON_EXE%" monitor_web.py"
)

rem Aguarda o servidor subir
ping -n 3 127.0.0.1 >nul

:abrir
rem Descobre o IP desta maquina na rede local
set "IP_LOCAL=?"
for /f "delims=" %%I in ('powershell -noprofile -command "$s=New-Object Net.Sockets.UdpClient;$s.Connect('8.8.8.8',53);$s.Client.LocalEndPoint.Address.ToString()"') do set "IP_LOCAL=%%I"

start "" "http://localhost:8777"
echo.
echo ============================================================
echo   Monitor disponivel!
echo.
echo   Neste PC:           http://localhost:8777
echo   Outros PCs da rede: http://%IP_LOCAL%:8777
echo.
echo   (o endereco de rede tambem aparece no topo do dashboard;
echo    clique nele para copiar)
echo ============================================================
echo.
pause
