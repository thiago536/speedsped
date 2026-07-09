@echo off
rem ===========================================================================
rem retomar_pipeline.bat — RETOMA o pipeline (apos Pausar ou Parar)
rem ===========================================================================
cd /d C:\SpedGenerator
"C:\Users\SERVIDOR SPED\AppData\Local\Python\pythoncore-3.14-64\python.exe" -c "from controle import definir_estado; ok = definir_estado('normal', 'atalho desktop'); print('PIPELINE RETOMADO - processamento volta ao normal.' if ok else 'FALHOU ao gravar estado!')"
echo.
pause
