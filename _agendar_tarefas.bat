@echo off
echo ========================================================
echo     AGENDANDO TAREFAS SPEDGENERATOR (24 HORAS INFINITO)
echo ========================================================
echo.

powershell -Command "$action = New-ScheduledTaskAction -Execute 'C:\SpedGenerator\iniciar_daemon.bat' -WorkingDirectory 'C:\SpedGenerator'; $trigger = New-ScheduledTaskTrigger -AtLogOn; $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 0); Register-ScheduledTask -TaskName 'SpedGenerator_Daemon' -Action $action -Trigger $trigger -Settings $settings -Force"

powershell -Command "$action_bkp = New-ScheduledTaskAction -Execute 'C:\SpedGenerator\atualizar_backups.bat' -WorkingDirectory 'C:\SpedGenerator'; $trigger_bkp = New-ScheduledTaskTrigger -Daily -At '08:00'; $settings_bkp = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 0); Register-ScheduledTask -TaskName 'SpedGenerator_Backup' -Action $action_bkp -Trigger $trigger_bkp -Settings $settings_bkp -Force"

echo.
echo [OK] Tarefas agendadas com sucesso no Windows!
echo [OK] SpedGenerator_Daemon iniciara no logon do usuario e rodara 24h sem limite de tempo.
echo.
pause
