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

def capturar_menu(down_count, filename):
    print(f"[DEBUG] Testando {down_count} DOWNs...")
    # Traz foco
    matar_acs()
    time.sleep(1.0)
    subprocess.Popen([EXE_PATH])
    app_win, handler = iniciar_sessao_acs("POSTO ADEMIR")
    if not app_win:
        print("[ERRO] Falha no login")
        return
    time.sleep(2.0)
    _focar_janela(app_win)
    time.sleep(0.5)
    
    # Abre Opções -> Exportação de arquivos
    keyboard.send_keys("%o")
    time.sleep(0.8)
    keyboard.send_keys("{DOWN}{DOWN}{DOWN}{RIGHT}")
    time.sleep(0.8)
    
    # Desce N vezes
    if down_count > 0:
        keyboard.send_keys(f"{{DOWN {down_count}}}")
    time.sleep(0.8)
    
    # Captura
    pyautogui.screenshot(filename)
    print(f"[DEBUG] Screenshot salvo em: {filename}")
    
    matar_acs()
    finalizar_sessao_acs(handler)
    time.sleep(1.0)

def main():
    print("============================================================")
    print("      VISUAL DIAGNOSTICS: COMPARANDO QUANTIDADE DE SETAS    ")
    print("============================================================")
    
    atualizar_ini("Ademir", "POSTO ADEMIR")
    
    # Testar 10 down
    capturar_menu(10, "shot_10_down.png")
    
    # Testar 11 down
    capturar_menu(11, "shot_11_down.png")
    
    # Testar 12 down
    capturar_menu(12, "shot_12_down.png")
    
    # Testar 13 down
    capturar_menu(13, "shot_13_down.png")

if __name__ == "__main__":
    main()
