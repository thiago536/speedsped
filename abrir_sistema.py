import os
import sys
import time
import argparse
import subprocess

# Tentar importar dependências do Windows para manipulação de janelas
HAS_WIN32 = False
try:
    import win32gui
    import win32process
    import win32con
    import win32com.client
    HAS_WIN32 = True
except ImportError:
    pass

# Caminho configurável padrão no topo do código, conforme solicitado
DEFAULT_SPED_PATH = r"C:\ACSSoft\Sintese\Gerente SPED\gerente.exe"


def get_hwnds_for_pid(pid):
    """Retorna todos os manipuladores de janela (hwnds) pertencentes a um PID."""
    hwnds = []
    if not HAS_WIN32:
        return hwnds

    def enum_window_callback(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
            if found_pid == pid:
                # Filtrar janelas que possuem título (evitar janelas de controle em background)
                title = win32gui.GetWindowText(hwnd)
                if title:
                    hwnds.append(hwnd)
        return True

    try:
        win32gui.EnumWindows(enum_window_callback, None)
    except Exception as e:
        print(f"[Erro] Falha ao enumerar janelas para o PID {pid}: {e}")
    return hwnds


def find_window_by_keywords(keywords):
    """Busca janelas visíveis que contenham palavras-chave no título."""
    hwnds_found = []
    if not HAS_WIN32:
        return hwnds_found

    def enum_window_callback(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd).upper()
            for keyword in keywords:
                if keyword.upper() in title:
                    hwnds_found.append((hwnd, win32gui.GetWindowText(hwnd)))
                    break
        return True

    try:
        win32gui.EnumWindows(enum_window_callback, None)
    except Exception:
        pass
    return hwnds_found


def robust_focus_window(hwnd):
    """Traz a janela para o primeiro plano usando múltiplas táticas avançadas do Windows."""
    if not HAS_WIN32:
        print("[Erro] Biblioteca win32 não instalada. Impossível focar a janela via código.")
        return False

    try:
        # 1. Verificar se a janela está minimizada e restaurá-la
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

        # 2. Tentar focar diretamente
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception:
        # Se falhar, aplicar contornos avançados de restrição de foco do Windows
        pass

    # Tática A: Anexar thread de entrada
    try:
        fore_hwnd = win32gui.GetForegroundWindow()
        if fore_hwnd:
            fore_thread, _ = win32process.GetWindowThreadProcessId(fore_hwnd)
            target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)
            
            if fore_thread != target_thread:
                win32process.AttachThreadInput(fore_thread, target_thread, True)
                win32gui.SetForegroundWindow(hwnd)
                win32process.AttachThreadInput(fore_thread, target_thread, False)
                return True
    except Exception:
        pass

    # Tática B: Simular pressionamento da tecla ALT para ceder foco (WScript Shell)
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.SendKeys("%")  # Envia Alt
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception as e:
        print(f"[Aviso] Não foi possível trazer a janela para o primeiro plano via APIs nativas: {e}")
        
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Inicializador do Sistema Alvo (SPED) com foco robusto de janela."
    )
    parser.add_argument(
        "--path",
        default=DEFAULT_SPED_PATH,
        help=f"Caminho do executável a ser aberto. Padrão: {DEFAULT_SPED_PATH}"
    )
    parser.add_argument(
        "--wait",
        type=float,
        default=5.0,
        help="Tempo máximo (em segundos) para esperar a janela do sistema aparecer. Padrão: 5.0"
    )
    args = parser.parse_args()

    target_path = args.path

    print("============================================================")
    print("                INICIALIZADOR DO SISTEMA RPA                ")
    print("============================================================")
    print(f"Caminho configurado: {target_path}")

    # Validação do arquivo
    if not os.path.exists(target_path):
        print(f"\n[ATENÇÃO] O caminho '{target_path}' não foi encontrado na máquina.")
        print("Verifique o caminho do seu validador SPED no topo do script ou passe via argumento.")
        print("\nExemplo para testar com Bloco de Notas:")
        print("  python abrir_sistema.py --path C:\\Windows\\notepad.exe\n")
        sys.exit(1)

    print("\n[RPA] Iniciando o processo...")
    try:
        # Iniciar o processo
        process = subprocess.Popen(target_path)
        pid = process.pid
        print(f"[RPA] Processo iniciado com sucesso! PID: {pid}")
    except Exception as e:
        print(f"[Erro] Falha catastrófica ao tentar executar o arquivo: {e}")
        sys.exit(1)

    print(f"[RPA] Monitorando abertura da janela (Timeout: {args.wait}s)...")
    
    start_time = time.time()
    focused = False
    
    # Palavras-chave para busca secundária por título
    sped_keywords = []
    exe_name = os.path.splitext(os.path.basename(target_path))[0]
    sped_keywords.append(exe_name)
    
    # Adicionar palavras-chave adicionais apenas se o executável for relacionado ao SPED/Validador
    if "sped" in exe_name.lower() or "validador" in exe_name.lower():
        sped_keywords.extend(["SPED", "Validador", "EFD", "Contábil", "Fiscal", "Receita Federal", "Guia Prático"])

    while time.time() - start_time < args.wait:
        # Tática 1: Buscar janelas pertencentes ao PID lançado
        hwnds = get_hwnds_for_pid(pid)
        if hwnds:
            hwnd = hwnds[0]
            title = win32gui.GetWindowText(hwnd)
            print(f"[RPA] Janela detectada via PID! Título: '{title}'")
            if robust_focus_window(hwnd):
                print("[RPA] Sucesso: Janela do sistema trazida para o primeiro plano (Foco obtido).")
                focused = True
                break

        # Tática 2: Fallback para busca por palavras-chave (caso o PID tenha mudado via wrapper/launcher)
        keyword_windows = find_window_by_keywords(sped_keywords)
        if keyword_windows:
            # Seleciona o primeiro que bater com palavras-chave
            hwnd, title = keyword_windows[0]
            print(f"[RPA] Janela detectada via título! Título: '{title}'")
            if robust_focus_window(hwnd):
                print("[RPA] Sucesso: Janela do sistema trazida para o primeiro plano (Foco obtido via título).")
                focused = True
                break
                
        time.sleep(0.5)

    if not focused:
        print("\n[Aviso] O processo foi iniciado, mas sua janela principal não pôde ser focada.")
        print("Razões comuns: O sistema demora mais para carregar (aumente o tempo limite usando --wait)")
        print("ou roda em modo silencioso / segundo plano.")
        print("Tente aumentar o timeout. Exemplo:")
        print(f"  python abrir_sistema.py --path \"{target_path}\" --wait 10")
    else:
        print("\n============================================================")
        print("               PROCESSO CONCLUÍDO COM SUCESSO               ")
        print("============================================================")


if __name__ == "__main__":
    main()
