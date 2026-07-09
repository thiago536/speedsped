@echo off
rem Reinicio rapido do daemon (elevado) — log em C:\SpedGenerator\restart_diag.txt
set "LOG=C:\SpedGenerator\restart_diag.txt"
echo ===== %date% %time% reinicio ===== > "%LOG%"
taskkill /f /t /im python.exe >> "%LOG%" 2>&1
taskkill /f /t /im pythonw.exe >> "%LOG%" 2>&1
taskkill /f /t /im gerente.exe >> "%LOG%" 2>&1
del /f /q "C:\ACS_Exporta\spedgenerator.lock" >> "%LOG%" 2>&1
ping -n 3 127.0.0.1 >nul
cd /d C:\SpedGenerator
set "PY=C:\Users\SERVIDOR SPED\AppData\Local\Python\pythoncore-3.14-64\python.exe"
set "PYW=C:\Users\SERVIDOR SPED\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe"
start "SpedGenerator_Daemon" /min cmd /c ""%PY%" main.py --daemon >> C:\ACS_Exporta\daemon.log 2>&1"
start "" "%PYW%" overlay_status.py
start "" "%PYW%" monitor_web.py
ping -n 6 127.0.0.1 >nul
echo ----- processos depois ----- >> "%LOG%"
tasklist /fi "imagename eq python.exe" >> "%LOG%" 2>&1
type "C:\ACS_Exporta\spedgenerator.lock" >> "%LOG%" 2>&1
echo ===== FIM %time% ===== >> "%LOG%"
