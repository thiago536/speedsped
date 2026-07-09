import os
import sys
import time
import threading
import pyautogui
from pynput import keyboard, mouse

# Configurações globais
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILENAME = os.path.join(SCRIPT_DIR, "workflow_log.txt")

# Tentar importar win32gui para obter títulos de janelas com alta robustez no Windows
HAS_WIN32 = False
try:
    import win32gui
    import win32process
    HAS_WIN32 = True
except ImportError:
    pass

try:
    import pygetwindow as gw
except ImportError:
    gw = None


class RpaRecorder:
    def __init__(self):
        self.recording = False
        self.lock = threading.Lock()
        
        # Resolução da tela
        try:
            width, height = pyautogui.size()
            self.resolution = f"{width}x{height}"
        except Exception:
            self.resolution = "Desconhecida"
            
        # Estados de tempo e ações
        self.last_action_time = None
        self.session_actions = []
        
        # Buffer de digitação
        self.buffer_text = ""
        self.buffer_start_time = None
        self.buffer_window = ""
        
        # Cabeçalho gravado
        self.header_written = False

    def get_active_window_title(self):
        """Retorna o título da janela ativa com máxima precisão e fallback."""
        if HAS_WIN32:
            try:
                hwnd = win32gui.GetForegroundWindow()
                if hwnd:
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        return title.strip()
            except Exception:
                pass
                
        if gw:
            try:
                win = gw.getActiveWindow()
                if win and win.title:
                    return win.title.strip()
            except Exception:
                pass
                
        return "Desconhecido"

    def flush_buffer(self):
        """Descarrega o buffer de digitação de texto para a lista de ações."""
        if not self.buffer_text:
            return
            
        current_time = time.time()
        # Calcula delay do início da digitação em relação à última ação
        delay = self.buffer_start_time - self.last_action_time
        if delay < 0:
            delay = 0.0
            
        log_line = f"[Janela: {self.buffer_window}] Teclado: Texto '{self.buffer_text}' digitado | Espera anterior: {delay:.2f}s"
        self.session_actions.append(log_line)
        
        # Atualiza o último tempo de ação para o final do fluxo de digitação
        self.last_action_time = current_time
        self.buffer_text = ""
        self.buffer_start_time = None
        self.buffer_window = ""

    def on_keyboard_press(self, key):
        with self.lock:
            # Controladores de gravação globais (independem do estado recording)
            if key == keyboard.Key.f1:
                self.start_recording()
                return
            elif key == keyboard.Key.f2:
                self.stop_recording()
                return

            # Se não estiver gravando, ignorar demais teclas
            if not self.recording:
                return

            # Verificar se é caractere digitável ou espaço
            is_printable = False
            char_val = ""
            
            if hasattr(key, 'char') and key.char is not None:
                # Evita códigos de controle como Ctrl+C (\x03)
                if key.char.isprintable():
                    is_printable = True
                    char_val = key.char
            elif key == keyboard.Key.space:
                is_printable = True
                char_val = " "

            if is_printable:
                # Inicializar o buffer de digitação se estiver vazio
                if not self.buffer_text:
                    self.buffer_start_time = time.time()
                    self.buffer_window = self.get_active_window_title()
                self.buffer_text += char_val
            else:
                # É uma tecla de controle estrutural, flush no buffer primeiro
                self.flush_buffer()
                
                # Mapear tecla especial
                key_desc = self.map_special_key(key)
                if key_desc:
                    current_time = time.time()
                    delay = current_time - self.last_action_time
                    if delay < 0:
                        delay = 0.0
                        
                    window = self.get_active_window_title()
                    log_line = f"[Janela: {window}] Teclado: {key_desc} | Espera anterior: {delay:.2f}s"
                    self.session_actions.append(log_line)
                    self.last_action_time = current_time

    def map_special_key(self, key):
        """Mapeia teclas especiais para descrições legíveis solicitadas."""
        mapping = {
            keyboard.Key.enter: "Pressionou ENTER",
            keyboard.Key.tab: "Pressionou TAB",
            keyboard.Key.esc: "Pressionou ESC",
            keyboard.Key.backspace: "Pressionou BACKSPACE",
            keyboard.Key.up: "Pressionou SETA PARA CIMA",
            keyboard.Key.down: "Pressionou SETA PARA BAIXO",
            keyboard.Key.left: "Pressionou SETA PARA ESQUERDA",
            keyboard.Key.right: "Pressionou SETA PARA DIREITA",
            keyboard.Key.delete: "Pressionou DELETE",
            keyboard.Key.caps_lock: "Pressionou CAPS LOCK",
            keyboard.Key.space: "Pressionou ESPAÇO"
        }
        
        if key in mapping:
            return mapping[key]
            
        # Caso seja outra tecla especial (Shift, Ctrl, etc.), retornamos se necessário
        # Para evitar encher o log de ruído, podemos retornar None para Shift puro, Ctrl puro etc.
        # ou representá-los de forma limpa.
        key_str = str(key).replace("Key.", "").upper()
        if key_str in ["SHIFT", "CTRL", "ALT", "SHIFT_R", "CTRL_R", "ALT_R", "CMD", "CMD_R"]:
            # Ignoramos modificadores soltos no log principal para fins de clareza RPA
            return None
            
        return f"Pressionou {key_str}"

    def on_mouse_click(self, x, y, button, pressed):
        if not pressed:
            return  # Registra apenas o evento de clique (press), evitando duplicidade na soltura
            
        with self.lock:
            if not self.recording:
                return
                
            # Esvaziar buffer de texto pendente antes de registrar ação de mouse
            self.flush_buffer()
            
            current_time = time.time()
            delay = current_time - self.last_action_time
            if delay < 0:
                delay = 0.0
                
            # Mapear botão do mouse
            button_desc = "Clique"
            if button == mouse.Button.left:
                button_desc = "Clique Esquerdo"
            elif button == mouse.Button.right:
                button_desc = "Clique Direito"
            elif button == mouse.Button.middle:
                button_desc = "Clique do Meio"
            else:
                button_desc = f"Clique {str(button).replace('Button.', '').capitalize()}"
                
            window = self.get_active_window_title()
            log_line = f"[Janela: {window}] Mouse: {button_desc} em ({x}, {y}) | Espera anterior: {delay:.2f}s"
            self.session_actions.append(log_line)
            self.last_action_time = current_time

    def on_mouse_scroll(self, x, y, dx, dy):
        with self.lock:
            if not self.recording:
                return
                
            # Esvaziar buffer de texto pendente
            self.flush_buffer()
            
            current_time = time.time()
            delay = current_time - self.last_action_time
            if delay < 0:
                delay = 0.0
                
            direction = "Scroll Up" if dy > 0 else "Scroll Down"
            window = self.get_active_window_title()
            log_line = f"[Janela: {window}] Mouse: {direction} em ({x}, {y}) | Espera anterior: {delay:.2f}s"
            self.session_actions.append(log_line)
            self.last_action_time = current_time

    def start_recording(self):
        if self.recording:
            return
            
        self.recording = True
        self.last_action_time = time.time()
        print("\nGravação Iniciada (F1)...")

    def stop_recording(self):
        if not self.recording:
            print("\nA gravação já está pausada. Pressione F1 para retomar.")
            return
            
        # Descarrega qualquer buffer de texto pendente
        self.flush_buffer()
        self.recording = False
        
        if self.session_actions:
            self.save_to_log_file()
            print(f"\nGravação Encerrada e Salva (F2)... [{len(self.session_actions)} novas ações salvas em '{LOG_FILENAME}']")
            self.session_actions.clear()
        else:
            print("\nGravação Encerrada e Salva (F2)... [Nenhuma nova ação capturada]")

    def save_to_log_file(self):
        """Salva as ações da sessão atual no arquivo txt, garantindo metadados se novo."""
        try:
            file_exists = os.path.exists(LOG_FILENAME)
            file_empty = file_exists and os.path.getsize(LOG_FILENAME) == 0
            
            # Se o arquivo não existir ou estiver vazio, insere a resolução base
            write_header = not file_exists or file_empty
            
            with open(LOG_FILENAME, "a", encoding="utf-8") as f:
                if write_header:
                    f.write(f"[Resolução Base] {self.resolution}\n")
                    
                for action in self.session_actions:
                    f.write(action + "\n")
        except PermissionError as pe:
            print(f"\n[ERRO DE PERMISSÃO] Não foi possível salvar no arquivo '{LOG_FILENAME}'.")
            print("Verifique se o arquivo está aberto em outro programa ou se a pasta possui restrições de gravação.")
            print(f"Detalhes do erro: {pe}")
        except Exception as e:
            print(f"\n[ERRO] Ocorreu uma falha inesperada ao salvar o arquivo de log: {e}")


def main():
    print("============================================================")
    print("        GRAVADOR DE AÇÕES RPA EXTREMAMENTE PRECISO        ")
    print("============================================================")
    print("[Atalhos]")
    print("  F1 : Iniciar / Retomar gravação das ações")
    print("  F2 : Pausar gravação e salvar imediatamente os dados")
    print("  Ctrl+C : Finalizar o script completamente")
    print("------------------------------------------------------------")
    
    recorder = RpaRecorder()
    print(f"Resolução da tela identificada: {recorder.resolution}")
    print("Status: OCIOSO. Aguardando comando F1 para gravar...")
    print("============================================================\n")

    # Inicializar os ouvintes pynput em threads separadas (assíncronos)
    keyboard_listener = keyboard.Listener(on_press=recorder.on_keyboard_press)
    mouse_listener = mouse.Listener(
        on_click=recorder.on_mouse_click, 
        on_scroll=recorder.on_mouse_scroll
    )

    keyboard_listener.start()
    mouse_listener.start()

    # Loop para manter a linha de comando ativa
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n[Encerrando] O script do gravador foi finalizado pelo usuário no terminal.")
        # Se por acaso fechar repentinamente e houver dados na sessão, salva antes de sair
        if recorder.recording:
            with recorder.lock:
                recorder.flush_buffer()
                if recorder.session_actions:
                    recorder.save_to_log_file()
                    print(f"Dados residuais salvos com sucesso em '{LOG_FILENAME}'.")
    finally:
        keyboard_listener.stop()
        mouse_listener.stop()


if __name__ == "__main__":
    main()
