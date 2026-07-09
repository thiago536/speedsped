@echo off
REM =============================================================================
REM atualizar_e_reiniciar.bat — Sincroniza e reinicia o SpedGenerator no Servidor
REM =============================================================================

echo =======================================================
echo   SpedGenerator - Iniciando Atualizacao e Reinicio
echo =======================================================
echo.

cd /d "C:\SpedGeneretor"

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

echo [1/3] Sincronizando novos arquivos para C:\SpedGenerator...
"%PYTHON_EXE%" sync_production.py

echo.
echo [2/3] Entrando na pasta de producao C:\SpedGenerator...
cd /d "C:\SpedGenerator"

echo.
echo [3/3] Executando script de inicializacao (que limpa e reinicia o daemon)...
call iniciar_sistema.bat

echo.
echo =======================================================
echo   Processo concluido! O sistema foi atualizado e reiniciado.
echo =======================================================
echo.
pause
