# =============================================================================
# overlay_status.py — Indicador visual flutuante do SpedGenerator
#
# Janela sempre-no-topo, sem borda, "click-through" (cliques atravessam),
# que mostra em tempo real o que o daemon esta fazendo, lendo:
#   - C:\ACS_Exporta\progresso.json   (estado do pipeline)
#   - C:\ACS_Exporta\spedgenerator.lock (PID do daemon)
#
# Estados exibidos:
#   CINZA    Daemon parado
#   VERDE    Daemon ativo, aguardando proximo ciclo (pulso suave)
#   AZUL     Preparando dados (backup/restore) — pode usar o PC normalmente
#   LARANJA  Automacao prestes a iniciar — feche o que estiver usando
#   VERMELHO Automacao em andamento — NAO use mouse/teclado (pisca)
#
# Nao interfere na automacao: WS_EX_NOACTIVATE (nunca rouba foco) +
# WS_EX_TRANSPARENT (mouse atravessa a janela).
# =============================================================================

import ctypes
import json
import os
import tkinter as tk

PROGRESSO_FILE = r"C:\ACS_Exporta\progresso.json"
LOCK_FILE = r"C:\ACS_Exporta\spedgenerator.lock"

POLL_MS = 1500      # releitura do estado
ANIM_MS = 400       # passo da animacao

CORES = {
    "parado":     {"bg": "#3a3a3a", "fg": "#bbbbbb", "dot": "#888888"},
    "ocioso":     {"bg": "#1e3a23", "fg": "#a8e6b0", "dot": "#3ddc5a"},
    "preparando": {"bg": "#16324f", "fg": "#a9d2ff", "dot": "#3aa0ff"},
    "prestes":    {"bg": "#4f3a10", "fg": "#ffd98a", "dot": "#ffb020"},
    "gerando":    {"bg": "#5a1515", "fg": "#ffffff", "dot": "#ff3030"},
}

SPINNER = ["|", "/", "-", "\\"]


def _pid_vivo(pid: int) -> bool:
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return False
    try:
        code = ctypes.c_ulong()
        if ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code)):
            return code.value == STILL_ACTIVE
        return False
    finally:
        ctypes.windll.kernel32.CloseHandle(h)


def daemon_rodando() -> bool:
    try:
        with open(LOCK_FILE, "r", encoding="utf-8", errors="ignore") as f:
            pid = int(f.read().strip().split()[0])
        return _pid_vivo(pid)
    except Exception:
        return False


def ler_progresso() -> dict:
    try:
        with open(PROGRESSO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def ler_controle() -> str:
    try:
        with open(r"C:\ACS_Exporta\controle.json", "r", encoding="utf-8") as f:
            return json.load(f).get("estado", "normal")
    except Exception:
        return "normal"


def detectar_estado() -> tuple[str, str]:
    """Retorna (estado, texto)."""
    if not daemon_rodando():
        return "parado", "Daemon parado"

    ctl = ler_controle()
    if ctl == "pausado":
        return "prestes", "PIPELINE PAUSADO pelo operador\n(retome pelo monitor web)"
    if ctl == "parar":
        return "parado", "PARADO pelo operador\n(retome pelo monitor web)"

    p = ler_progresso()
    etapa = (p.get("etapa") or "").lower()
    empresa = p.get("empresa_atual") or ""
    pipeline = p.get("pipeline") or {}

    if p.get("ativo"):
        if "gerando" in etapa:
            return "gerando", f"AUTOMACAO EM ANDAMENTO ({empresa})\nNAO USE MOUSE / TECLADO"
        # alguma empresa ja preparada esperando a vez de gerar?
        if any((v.get("etapa") == "aguardando") for v in pipeline.values()):
            return "prestes", "Automacao prestes a iniciar\nEvite usar o computador"
        if any(palavra in etapa for palavra in ("backup", "restaurando", "localizando", "corrigindo")):
            return "preparando", f"Preparando dados: {empresa or '...'}\n({p.get('etapa')})"
        return "preparando", f"Processando: {empresa or p.get('etapa') or '...'}"

    return "ocioso", "Daemon ativo - aguardando proximo ciclo"


class Overlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.92)

        self.frame = tk.Frame(self.root, padx=14, pady=10)
        self.frame.pack(fill="both", expand=True)
        self.dot = tk.Label(self.frame, text="●", font=("Segoe UI", 16))
        self.dot.pack(side="left", padx=(0, 10))
        self.label = tk.Label(self.frame, font=("Segoe UI", 11, "bold"), justify="left")
        self.label.pack(side="left")

        self.estado = ""
        self.tick = 0
        self.root.update_idletasks()
        self._aplicar_estilos_win32()
        self._posicionar()
        self._poll()
        self._animar()

    def _aplicar_estilos_win32(self):
        """Janela nunca rouba foco e deixa cliques atravessarem."""
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        WS_EX_NOACTIVATE = 0x08000000
        WS_EX_TOOLWINDOW = 0x00000080  # nao aparece no Alt-Tab
        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

    def _posicionar(self):
        """Canto inferior direito, acima da barra de tarefas."""
        self.root.update_idletasks()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"+{sw - w - 16}+{sh - h - 64}")

    def _aplicar(self, estado: str, texto: str):
        cor = CORES[estado]
        for wdg in (self.frame, self.dot, self.label):
            wdg.configure(bg=cor["bg"])
        self.root.configure(bg=cor["bg"])
        self.dot.configure(fg=cor["dot"])
        self.label.configure(fg=cor["fg"], text=texto)
        self.estado = estado
        self._posicionar()

    def _poll(self):
        estado, texto = detectar_estado()
        self._aplicar(estado, texto)
        self.root.after(POLL_MS, self._poll)

    def _animar(self):
        self.tick += 1
        if self.estado == "gerando":
            # pisca forte: alterna o fundo entre vermelho escuro e vivo
            bg = "#b01010" if self.tick % 2 else "#5a1515"
            for wdg in (self.frame, self.dot, self.label):
                wdg.configure(bg=bg)
            self.root.configure(bg=bg)
        elif self.estado == "prestes":
            self.dot.configure(fg="#ffb020" if self.tick % 2 else "#4f3a10")
        elif self.estado == "preparando":
            self.dot.configure(text=SPINNER[self.tick % 4], font=("Consolas", 16, "bold"))
        elif self.estado == "ocioso":
            # pulso suave do ponto verde
            self.dot.configure(fg="#3ddc5a" if self.tick % 4 < 2 else "#1f7a33")
        if self.estado != "preparando":
            self.dot.configure(text="●", font=("Segoe UI", 16))
        self.root.after(ANIM_MS, self._animar)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    Overlay().run()
