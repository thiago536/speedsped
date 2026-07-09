import sys
import time
from pywinauto import Desktop, Application

def main():
    print("Connecting to ACS main window...")
    desktop = Desktop(backend="win32")
    
    # Encontra a janela principal
    app_win = None
    for w in desktop.windows():
        title = w.window_text() or ""
        if "ACS Sintese" in title and "Gerente" in title:
            app_win = w
            break
            
    if app_win is None:
        print("[ERRO] Janela ACS Sintese - Gerente não encontrada. Certifique-se de que o sistema está aberto.")
        sys.exit(1)
        
    print(f"Janela encontrada: '{app_win.window_text()}'")
    
    try:
        # Tenta obter a barra de menus nativa do Win32
        menu = app_win.menu()
        if menu:
            print("\n--- Estrutura de Menus Detectada ---")
            for item in menu.items():
                print(f"Submenu: {item.text()}")
                # Tenta listar sub-itens
                try:
                    sub = item.submenu()
                    if sub:
                        for subitem in sub.items():
                            print(f"  - {subitem.text()}")
                            try:
                                subsub = subitem.submenu()
                                if subsub:
                                    for subsubitem in subsub.items():
                                        print(f"    * {subsubitem.text()}")
                            except Exception:
                                pass
                except Exception:
                    pass
        else:
            print("[Aviso] app_win.menu() retornou None.")
    except Exception as e:
        print(f"[Erro] Falha ao ler menus: {e}")

if __name__ == "__main__":
    main()
