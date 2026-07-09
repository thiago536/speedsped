@echo off
REM =============================================================================
REM baixar_pendentes.bat — Baixa backups desatualizados do servidor remoto
REM
REM Compara data de liberacao no Supabase com data do .backup em disco.
REM Baixa apenas os bancos que estao atrasados (pg_dump individual).
REM
REM Log salvo em: C:\Backups_Novo\baixar_pendentes.log
REM =============================================================================

cd /d "C:\SpedGenerator"

REM --- Encontra o Python instalado ---
set "PYTHON_EXE=C:\Users\SERVIDOR SPED\AppData\Local\Programs\Python\Python313\python.exe"

if not exist "%PYTHON_EXE%" set "PYTHON_EXE=C:\Users\SERVIDOR SPED\AppData\Local\Programs\Python\Python312\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=C:\Users\User 2\AppData\Local\Programs\Python\Python313\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=C:\Users\User 2\AppData\Local\Programs\Python\Python312\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=C:\Program Files\Python313\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=C:\Program Files\Python312\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [%DATE% %TIME%] ERRO: Python nao encontrado. Instale o Python ou ajuste o caminho neste bat.
    exit /b 1
)

REM --- Executa e salva log ---
echo [%DATE% %TIME%] ========================================
echo [%DATE% %TIME%] Iniciando baixar_pendentes.bat
echo [%DATE% %TIME%] Python: %PYTHON_EXE%
echo [%DATE% %TIME%] ========================================

"%PYTHON_EXE%" baixar_pendentes.py

set "CODIGO=%ERRORLEVEL%"
echo [%DATE% %TIME%] Finalizado. Codigo de saida: %CODIGO%

exit /b %CODIGO%
