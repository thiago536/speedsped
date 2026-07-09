@echo off
rem ===========================================================================
rem pausar_pipeline.bat — PAUSA o pipeline no proximo checkpoint (entre etapas)
rem Escreve direto em C:\ACS_Exporta\controle.json (mesmo sinal do monitor web).
rem O daemon continua vivo; a etapa atomica em andamento termina antes de parar.
rem Para voltar: retomar_pipeline.bat ou botao Retomar no monitor.
rem ===========================================================================
cd /d C:\SpedGenerator
"C:\Users\SERVIDOR SPED\AppData\Local\Python\pythoncore-3.14-64\python.exe" -c "from controle import definir_estado; ok = definir_estado('pausado', 'atalho desktop'); print('PIPELINE PAUSADO - segura no proximo checkpoint.' if ok else 'FALHOU ao gravar estado!')"
echo.
echo O indicador na tela e o monitor (http://localhost:8777) mostram PAUSADO.
echo Para voltar a processar: atalho "Retomar Pipeline" ou botao Retomar no monitor.
echo.
pause
