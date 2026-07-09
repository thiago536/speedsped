import os
import sys
import time
import logging
import subprocess
import pyautogui
from pywinauto import keyboard

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

from acs_runner import matar_acs
from acs_automation import iniciar_sessao_acs, finalizar_sessao_acs, _focar_janela
from ini_manager import atualizar_ini

EXE_PATH = r"C:\ACSSoft\Sintese\Gerente SPED\gerente.exe"

def main():
    print("============================================================")
    print("             DEBUG NAVEGAÇÃO DE MENU POR IMAGENS            ")
    print("============================================================")
    
    # 1. Limpar e atualizar ini
    matar_acs()
    time.sleep(1.0)
    
    atualizar_ini("Ademir", "POSTO ADEMIR")
    
    # 2. Lançar o processo
    try:
        subprocess.Popen([EXE_PATH])
    except Exception as e:
        print(f"[ERRO] Falha ao executar: {e}")
        sys.exit(1)
        
    # 3. Login
    app_win, handler = iniciar_sessao_acs("POSTO ADEMIR")
    if not app_win:
        print("[ERRO] Falha no login")
        matar_acs()
        sys.exit(1)
        
    time.sleep(3.0)
    _focar_janela(app_win)
    time.sleep(0.5)
    
    # --- PASSO A: Testar Alt+O ---
    print("[DEBUG] Enviando Alt+O para abrir o menu Opções...")
    keyboard.send_keys("%o") # Alt+O (% é Alt no pywinauto)
    time.sleep(1.5)
    pyautogui.screenshot("shot_A_alt_o.png")
    print("[DEBUG] Screenshot A salvo")
    
    # --- PASSO B: Navegar no dropdown ---
    print("[DEBUG] Enviando DOWN 3 vezes e RIGHT para abrir Exportação...")
    keyboard.send_keys("{DOWN}{DOWN}{DOWN}{RIGHT}")
    time.sleep(1.5)
    pyautogui.screenshot("shot_B_submenu.png")
    print("[DEBUG] Screenshot B salvo")
    
    # --- PASSO C: Tentar abrir SPED Fiscal ---
    print("[DEBUG] Enviando ENTER para abrir SPED Fiscal...")
    keyboard.send_keys("{ENTER}")
    time.sleep(3.0)
    pyautogui.screenshot("shot_C_fiscal.png")
    print("[DEBUG] Screenshot C salvo")
    
    # 4. Encerrar
    matar_acs()
    finalizar_sessao_acs(handler)
    print("[DEBUG] Fim do script de debug!")

if __name__ == "__main__":
    main()
