@echo off
echo =======================================================
echo   Desativando Agendamento Noturno SpedGenerator
echo =======================================================
echo.
schtasks /change /tn "SpedGenerator_Noturno_Start" /disable 2>nul
schtasks /change /tn "SpedGenerator_Backup" /disable 2>nul
schtasks /change /tn "SpedGenerator_Noturno_Stop" /disable 2>nul
echo.
echo [OK] Agendamentos automaticos desativados com sucesso! 
echo O sistema NAO iniciara mais automaticamente as 19:00.
echo.
echo Se o sistema ainda estiver rodando agora, execute o 'finalizar_sistema.bat' para fecha-lo.
echo.
pause
