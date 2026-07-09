@echo off
REM =============================================================================
REM configurar_horario_noturno.bat — Configura o agendamento noturno do SpedGenerator
REM =============================================================================

echo =======================================================
echo     CONFIGURADOR DE AGENDAMENTO NOTURNO SPEDGENERATOR
echo =======================================================
echo.

REM 1. Remove a tarefa antiga do Daemon (que iniciava no logon) para nao conflitar
echo [-] Removendo tarefa antiga 'SpedGenerator_Daemon' (se existir)...
schtasks /delete /tn "SpedGenerator_Daemon" /f 2>nul

REM 2. Remove agendamentos antigos deste script para garantir uma instalacao limpa
echo [-] Limpando agendamentos noturnos anteriores...
schtasks /delete /tn "SpedGenerator_Noturno_Start" /f 2>nul
schtasks /delete /tn "SpedGenerator_Noturno_Stop" /f 2>nul
schtasks /delete /tn "SpedGenerator_Backup" /f 2>nul

echo.
echo [+] Criando tarefa para INICIAR o daemon diariamente as 19:00...
schtasks /create /tn "SpedGenerator_Noturno_Start" /tr "\"C:\SpedGenerator\iniciar_daemon.bat\"" /sc daily /st 19:00 /f

echo.
echo [+] Criando tarefa para REALIZAR BACKUPS diariamente as 19:15 (fora do horario comercial)...
schtasks /create /tn "SpedGenerator_Backup" /tr "\"C:\SpedGenerator\atualizar_backups.bat\"" /sc daily /st 19:15 /f

echo.
echo [+] Criando tarefa para PARAR o daemon e limpar processos diariamente as 07:00...
schtasks /create /tn "SpedGenerator_Noturno_Stop" /tr "\"C:\SpedGenerator\finalizar_sistema.bat\"" /sc daily /st 07:00 /f

echo.
echo =======================================================
echo   Tarefas agendadas com sucesso! Verificando agendamento:
echo =======================================================
echo.
schtasks /query /tn "SpedGenerator_Noturno_Start" /fo LIST
echo.
schtasks /query /tn "SpedGenerator_Backup" /fo LIST
echo.
schtasks /query /tn "SpedGenerator_Noturno_Stop" /fo LIST
echo.

pause
