@echo off
rem Reinicio diagnostico — gera log em C:\SpedGenerator\restart_diag.txt
set "LOG=C:\SpedGenerator\restart_diag.txt"
echo ===== %date% %time% ELEVADO: whoami ===== > "%LOG%"
whoami >> "%LOG%" 2>&1
net session >nul 2>&1 && (echo ADMIN: SIM >> "%LOG%") || (echo ADMIN: NAO >> "%LOG%")

echo ----- processos python antes ----- >> "%LOG%"
tasklist /fi "imagename eq python.exe" >> "%LOG%" 2>&1
tasklist /fi "imagename eq pythonw.exe" >> "%LOG%" 2>&1

echo ----- matando tudo ----- >> "%LOG%"
taskkill /f /t /im python.exe >> "%LOG%" 2>&1
taskkill /f /t /im pythonw.exe >> "%LOG%" 2>&1
taskkill /f /t /im gerente.exe >> "%LOG%" 2>&1

echo ----- removendo lock ----- >> "%LOG%"
del /f /q "C:\ACS_Exporta\spedgenerator.lock" >> "%LOG%" 2>&1
if exist "C:\ACS_Exporta\spedgenerator.lock" (echo LOCK AINDA EXISTE >> "%LOG%") else (echo lock removido >> "%LOG%")

ping -n 3 127.0.0.1 >nul

echo ----- subindo daemon ----- >> "%LOG%"
cd /d C:\SpedGenerator
set "PY=C:\Users\SERVIDOR SPED\AppData\Local\Python\pythoncore-3.14-64\python.exe"
set "PYW=C:\Users\SERVIDOR SPED\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe"
start "SpedGenerator_Daemon" /min cmd /c ""%PY%" main.py --daemon >> C:\ACS_Exporta\daemon.log 2>&1"
start "" "%PYW%" overlay_status.py
start "" "%PYW%" monitor_web.py

ping -n 6 127.0.0.1 >nul
echo ----- processos python depois ----- >> "%LOG%"
tasklist /fi "imagename eq python.exe" >> "%LOG%" 2>&1
tasklist /fi "imagename eq pythonw.exe" >> "%LOG%" 2>&1
echo ----- lock depois ----- >> "%LOG%"
type "C:\ACS_Exporta\spedgenerator.lock" >> "%LOG%" 2>&1
echo ===== FIM %time% ===== >> "%LOG%"
