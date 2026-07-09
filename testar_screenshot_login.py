import os
import sys
import time
import logging
import subprocess
import pyautogui

# Configurar logging para exibir no console em tempo real
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

from acs_runner import matar_acs
from acs_automation import iniciar_sessao_acs, finalizar_sessao_acs
from ini_manager import atualizar_ini

EXE_PATH = r"C:\ACSSoft\Sintese\Gerente SPED\gerente.exe"

def main():
    print("============================================================")
    print("      TESTAR LOGIN E CAPTURAR SCREENSHOT DA TELA INICIAL    ")
    print("============================================================")
    
    # 1. Limpar instâncias antigas
    matar_acs()
    time.sleep(1.0)
    
    # 2. Iniciar o .ini e lançar o processo
    print("[RPA] Atualizando acsgerente.ini para apontar para ademir_local...")
    if not atualizar_ini("Ademir", "POSTO ADEMIR"):
        print("[ERRO] Falha ao atualizar acsgerente.ini")
        sys.exit(1)
        
    print(f"[RPA] Lançando o executável: {EXE_PATH}")
    try:
        subprocess.Popen([EXE_PATH])
        print("[RPA] Processo iniciado!")
    except Exception as e:
        print(f"[ERRO] Falha ao executar: {e}")
        sys.exit(1)
        
    # 3. Executar o login
    print("[RPA] Aguardando janela e realizando login...")
    app_win, handler = iniciar_sessao_acs("POSTO ADEMIR")
    
    if app_win:
        print("[RPA] Login concluído com sucesso!")
        print("[RPA] Aguardando 3 segundos para a janela carregar completamente...")
        time.sleep(3.0)
        
        # Tirar screenshot
        caminho_shot = "screenshot_pos_login.png"
        print(f"[RPA] Capturando screenshot da tela pós-login em: {caminho_shot}")
        pyautogui.screenshot(caminho_shot)
        print("[RPA] Screenshot capturado com sucesso!")
        
        print("[RPA] Mantendo o sistema aberto por mais 5 segundos para verificação visual...")
        time.sleep(5.0)
    else:
        print("[ERRO] Falha no login")
        # Captura screenshot mesmo se falhar o login
        pyautogui.screenshot("screenshot_falha_login.png")
        
    # 4. Limpar
    matar_acs()
    finalizar_sessao_acs(handler)

if __name__ == "__main__":
    main()
