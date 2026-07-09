@echo off
echo =======================================================
echo   Ativando Agendamento Noturno SpedGenerator
echo =======================================================
echo.
schtasks /change /tn "SpedGenerator_Noturno_Start" /enable 2>nul
schtasks /change /tn "SpedGenerator_Backup" /enable 2>nul
schtasks /change /tn "SpedGenerator_Noturno_Stop" /enable 2>nul
echo.
echo [OK] Agendamentos automaticos reativados com sucesso!
echo O sistema voltara a iniciar automaticamente as 19:00 e parar as 07:00.
echo.
pause
