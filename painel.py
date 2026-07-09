# =============================================================================
# painel.py — Painel de Controle SpedGenerator
#
# Frontend desktop (CustomTkinter) para gerenciar sistema SPED:
#   - Arquivos gerados (browser, pesquisa, download)
#   - Bancos restaurados (status, tamanho, trava, drop)
#   - Fila SPED (progresso tempo real, fila, historico)
#   - Logs (visualizador tempo real)
#   - Acesso Remoto (gerador INI com pesquisa)
#
# Compilar exe: pyinstaller --onefile --windowed --name PainelSPED painel.py
# =============================================================================

import os
import sys
import re
import json
import csv
import socket
import shutil
import threading
import time
import subprocess
from datetime import datetime

# Setup paths
if getattr(sys, "frozen", False):
    _base_dir = os.path.dirname(sys.executable)
else:
    _base_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, _base_dir)
os.chdir(_base_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(_base_dir, ".env"))

import customtkinter as ctk
from tkinter import messagebox, filedialog

import config
from banco_tracker import (
    info_completa_bancos, dropar_banco_controlado, marcar_protegido,
    sincronizar_com_pg, listar_bancos_ativos,
)
from tracking import listar_gerados
from supabase_client import get_client
import progresso
from backup_manager import ler_progresso_backup

# =============================================================================
# Theme
# =============================================================================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

FONT_TITLE = ("Segoe UI", 18, "bold")
FONT_HEADER = ("Segoe UI", 13, "bold")
FONT_BODY = ("Segoe UI", 12)
FONT_MONO = ("Consolas", 11)
FONT_SMALL = ("Segoe UI", 10)
FONT_TINY = ("Segoe UI", 9)

COR_SUCESSO = "#2ecc71"
COR_ERRO = "#e74c3c"
COR_AVISO = "#f39c12"
COR_INFO = "#3498db"
COR_TRAVA = "#9b59b6"
COR_BG_CARD = ("gray90", "gray17")
COR_BG_CARD_ALT = ("gray85", "gray20")


def _get_ip_local() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _formatar_data(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return iso_str or "-"


def _tamanho_humano(bytes_val: int) -> str:
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.0f} KB"
    else:
        return f"{bytes_val / (1024 * 1024):.1f} MB"


def _espaco_disco(path: str) -> tuple[float, float]:
    """Retorna (usado_gb, total_gb) do disco onde path esta."""
    try:
        usage = shutil.disk_usage(os.path.splitdrive(path)[0] or path)
        return usage.used / (1024**3), usage.total / (1024**3)
    except Exception:
        return 0, 0


def _ler_daemon_state() -> dict:
    """Le estado do daemon de daemon_state.json."""
    import psutil as _psutil
    daemon_file = os.path.join(config.SPED_EXPORT_DIR, "daemon_state.json")
    if not os.path.exists(daemon_file):
        return {"status": "parado"}
    try:
        with open(daemon_file, "r", encoding="utf-8") as f:
            estado = json.load(f)
        pid = estado.get("pid", 0)
        if pid and not _psutil.pid_exists(pid):
            estado["status"] = "parado"
        return estado
    except Exception:
        return {"status": "parado"}


# =============================================================================
# App Principal
# =============================================================================

class PainelApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SpedGenerator — Painel de Controle")
        self.geometry("1150x800")
        self.minsize(950, 650)

        self.ip_servidor = _get_ip_local()
        self._bancos_cache = []
        self._empresas_cache = []

        self._build_ui()
        self.after(500, self._refresh_all)

    def _build_ui(self):
        # === Header ===
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            header, text="SpedGenerator", font=FONT_TITLE,
            text_color=COR_INFO
        ).pack(side="left")

        # Progresso global no header
        self.header_prog_frame = ctk.CTkFrame(header, fg_color="transparent")
        self.header_prog_frame.pack(side="left", padx=30)
        self.lbl_prog_global = ctk.CTkLabel(
            self.header_prog_frame, text="", font=FONT_SMALL, text_color=COR_AVISO
        )
        self.lbl_prog_global.pack(side="left")
        self.progress_bar_global = ctk.CTkProgressBar(self.header_prog_frame, width=200, height=12)
        self.progress_bar_global.pack(side="left", padx=8)
        self.progress_bar_global.set(0)
        self.header_prog_frame.pack_forget()  # esconde ate ter progresso

        self.lbl_ip = ctk.CTkLabel(
            header, text=f"IP: {self.ip_servidor}",
            font=FONT_SMALL, text_color="gray"
        )
        self.lbl_ip.pack(side="right")

        self.lbl_daemon = ctk.CTkLabel(
            header, text="", font=FONT_SMALL, text_color="gray"
        )
        self.lbl_daemon.pack(side="right", padx=10)

        self.lbl_status = ctk.CTkLabel(
            header, text="", font=FONT_SMALL, text_color=COR_SUCESSO
        )
        self.lbl_status.pack(side="right", padx=20)

        # === Tabview ===
        self.tabs = ctk.CTkTabview(self, anchor="nw")
        self.tabs.pack(fill="both", expand=True, padx=15, pady=(5, 0))

        self.tab_arquivos = self.tabs.add("  Arquivos  ")
        self.tab_bancos = self.tabs.add("  Bancos  ")
        self.tab_fila = self.tabs.add("  Fila SPED  ")
        self.tab_logs = self.tabs.add("  Logs  ")
        self.tab_remoto = self.tabs.add("  Acesso Remoto  ")

        self._build_tab_arquivos()
        self._build_tab_bancos()
        self._build_tab_fila()
        self._build_tab_logs()
        self._build_tab_remoto()

        # === Footer ===
        footer = ctk.CTkFrame(self, height=32, fg_color=("gray85", "gray20"))
        footer.pack(fill="x", side="bottom")
        self.lbl_footer = ctk.CTkLabel(footer, text="", font=FONT_SMALL, text_color="gray")
        self.lbl_footer.pack(side="left", padx=15)
        self.lbl_disco = ctk.CTkLabel(footer, text="", font=FONT_SMALL, text_color="gray")
        self.lbl_disco.pack(side="right", padx=15)

    # =========================================================================
    # TAB: Arquivos Gerados
    # =========================================================================

    def _build_tab_arquivos(self):
        tab = self.tab_arquivos

        toolbar = ctk.CTkFrame(tab, fg_color="transparent")
        toolbar.pack(fill="x", pady=(5, 10))

        ctk.CTkLabel(toolbar, text="Arquivos SPED Gerados", font=FONT_HEADER).pack(side="left")

        # Botoes direita
        ctk.CTkButton(toolbar, text="Atualizar", width=90, height=30,
                       command=self._refresh_arquivos).pack(side="right")
        ctk.CTkButton(toolbar, text="Abrir Pasta", width=90, height=30,
                       command=lambda: os.startfile(config.SPED_EXPORT_DIR)).pack(side="right", padx=5)
        ctk.CTkButton(toolbar, text="Baixar Todos", width=100, height=30,
                       fg_color="#27ae60", hover_color="#1e8449",
                       command=self._baixar_todos).pack(side="right", padx=5)
        ctk.CTkButton(toolbar, text="Exportar CSV", width=100, height=30,
                       fg_color="gray40",
                       command=self._exportar_csv).pack(side="right", padx=5)

        # Pesquisa
        search_frame = ctk.CTkFrame(tab, fg_color="transparent")
        search_frame.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(search_frame, text="Pesquisar:", font=FONT_BODY).pack(side="left")
        self.arq_pesquisa = ctk.CTkEntry(search_frame, width=300,
                                          placeholder_text="Filtrar por nome do posto...")
        self.arq_pesquisa.pack(side="left", padx=8)
        self.arq_pesquisa.bind("<KeyRelease>", lambda e: self._refresh_arquivos())

        self.arq_scroll = ctk.CTkScrollableFrame(tab)
        self.arq_scroll.pack(fill="both", expand=True)

    def _refresh_arquivos(self):
        for w in self.arq_scroll.winfo_children():
            w.destroy()

        export_dir = config.SPED_EXPORT_DIR
        if not os.path.exists(export_dir):
            ctk.CTkLabel(self.arq_scroll, text="Pasta de exportacao nao encontrada",
                          text_color=COR_ERRO).pack(pady=20)
            return

        filtro = self.arq_pesquisa.get().strip().lower()

        pastas = sorted([
            d for d in os.listdir(export_dir)
            if os.path.isdir(os.path.join(export_dir, d)) and d not in ("erros",)
        ])

        if filtro:
            pastas = [p for p in pastas if filtro in p.lower()]

        if not pastas:
            msg = "Nenhum posto encontrado" if filtro else "Nenhum arquivo gerado ainda"
            ctk.CTkLabel(self.arq_scroll, text=msg,
                          text_color="gray", font=FONT_BODY).pack(pady=20)
            return

        total_arquivos = 0
        total_bytes = 0

        for idx, pasta in enumerate(pastas):
            caminho = os.path.join(export_dir, pasta)
            arquivos = [f for f in os.listdir(caminho) if os.path.isfile(os.path.join(caminho, f))]

            bg = COR_BG_CARD if idx % 2 == 0 else COR_BG_CARD_ALT
            card = ctk.CTkFrame(self.arq_scroll, fg_color=bg)
            card.pack(fill="x", pady=2, padx=5)

            # Header do posto
            header_row = ctk.CTkFrame(card, fg_color="transparent")
            header_row.pack(fill="x", padx=10, pady=(8, 2))

            ctk.CTkLabel(header_row, text=pasta, font=FONT_HEADER,
                          text_color=COR_INFO).pack(side="left")

            # Botoes
            ctk.CTkButton(header_row, text="Baixar", width=60, height=24,
                           fg_color="#27ae60", hover_color="#1e8449",
                           command=lambda p=caminho, n=pasta: self._baixar_pasta(p, n)
                           ).pack(side="right", padx=3)
            ctk.CTkButton(header_row, text="Abrir", width=50, height=24,
                           fg_color="gray40",
                           command=lambda p=caminho: os.startfile(p)).pack(side="right", padx=3)

            # Tamanho total da pasta
            pasta_bytes = sum(
                os.path.getsize(os.path.join(caminho, f)) for f in arquivos
            )
            total_bytes += pasta_bytes
            ctk.CTkLabel(header_row, text=f"{len(arquivos)} arq. | {_tamanho_humano(pasta_bytes)}",
                          font=FONT_SMALL, text_color="gray").pack(side="right", padx=10)

            total_arquivos += len(arquivos)

            # Lista de arquivos
            for arq in sorted(arquivos):
                arq_path = os.path.join(caminho, arq)
                arq_row = ctk.CTkFrame(card, fg_color="transparent")
                arq_row.pack(fill="x", padx=20, pady=1)

                tamanho = os.path.getsize(arq_path)

                ctk.CTkLabel(arq_row, text=f"  {arq}", font=FONT_MONO,
                              anchor="w").pack(side="left")
                ctk.CTkLabel(arq_row, text=_tamanho_humano(tamanho), font=FONT_SMALL,
                              text_color="gray").pack(side="right")

            ctk.CTkFrame(card, height=4, fg_color="transparent").pack()

        # Resumo
        ctk.CTkLabel(self.arq_scroll,
                      text=f"Total: {len(pastas)} posto(s) | {total_arquivos} arquivo(s) | {_tamanho_humano(total_bytes)}",
                      font=FONT_SMALL, text_color="gray").pack(anchor="w", padx=5, pady=(10, 5))

    def _baixar_pasta(self, caminho_origem: str, nome_posto: str):
        """Copia pasta do posto pra destino escolhido pelo usuario."""
        destino = filedialog.askdirectory(title=f"Escolha onde salvar '{nome_posto}'")
        if not destino:
            return

        destino_final = os.path.join(destino, nome_posto)

        def _copiar():
            try:
                if os.path.exists(destino_final):
                    shutil.rmtree(destino_final)
                shutil.copytree(caminho_origem, destino_final)
                self.after(0, lambda: self._set_status(f"Baixado: {nome_posto} -> {destino}"))
                self.after(0, lambda: messagebox.showinfo("Download",
                    f"Arquivos copiados com sucesso!\n\n{destino_final}"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Erro", f"Falha ao copiar:\n{e}"))

        threading.Thread(target=_copiar, daemon=True).start()
        self._set_status(f"Copiando {nome_posto}...")

    def _baixar_todos(self):
        """Copia todas pastas de postos pro destino."""
        destino = filedialog.askdirectory(title="Escolha onde salvar TODOS os postos")
        if not destino:
            return

        export_dir = config.SPED_EXPORT_DIR
        pastas = [
            d for d in os.listdir(export_dir)
            if os.path.isdir(os.path.join(export_dir, d)) and d not in ("erros",)
        ]

        if not pastas:
            messagebox.showinfo("Aviso", "Nenhuma pasta para baixar.")
            return

        def _copiar():
            copiadas = 0
            for pasta in pastas:
                try:
                    origem = os.path.join(export_dir, pasta)
                    dest = os.path.join(destino, pasta)
                    if os.path.exists(dest):
                        shutil.rmtree(dest)
                    shutil.copytree(origem, dest)
                    copiadas += 1
                except Exception:
                    pass
            self.after(0, lambda: self._set_status(f"Baixados {copiadas}/{len(pastas)} postos"))
            self.after(0, lambda: messagebox.showinfo("Download",
                f"{copiadas} pasta(s) copiada(s) para:\n{destino}"))

        threading.Thread(target=_copiar, daemon=True).start()
        self._set_status(f"Copiando {len(pastas)} pastas...")

    def _exportar_csv(self):
        """Exporta relatorio CSV de todos SPEDs gerados."""
        gerados = listar_gerados()
        if not gerados:
            messagebox.showinfo("Aviso", "Nenhum registro de geracao.")
            return

        path = filedialog.asksaveasfilename(
            title="Salvar Relatorio CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"relatorio_sped_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["ID", "Nome", "Data Geracao", "Status", "Arquivos"])
            for eid, info in sorted(gerados.items()):
                writer.writerow([
                    eid,
                    info.get("nome", ""),
                    info.get("data_geracao", ""),
                    info.get("status", "ok"),
                    ", ".join(info.get("arquivos", [])),
                ])
        self._set_status(f"CSV salvo: {path}")

    # =========================================================================
    # TAB: Bancos Restaurados
    # =========================================================================

    def _build_tab_bancos(self):
        tab = self.tab_bancos

        toolbar = ctk.CTkFrame(tab, fg_color="transparent")
        toolbar.pack(fill="x", pady=(5, 10))

        ctk.CTkLabel(toolbar, text="Bancos PostgreSQL Ativos", font=FONT_HEADER).pack(side="left")
        ctk.CTkButton(toolbar, text="Atualizar", width=90, height=30,
                       command=self._refresh_bancos).pack(side="right")

        # Card status backup/pg_dump
        self.backup_card = ctk.CTkFrame(tab, fg_color=("gray88", "gray22"))
        self.backup_card.pack(fill="x", padx=5, pady=(0, 5))
        backup_inner = ctk.CTkFrame(self.backup_card, fg_color="transparent")
        backup_inner.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(backup_inner, text="Backup Remoto:", font=FONT_SMALL).pack(side="left")
        self.lbl_backup_status = ctk.CTkLabel(backup_inner, text="Verificando...",
                                                font=FONT_SMALL, text_color="gray")
        self.lbl_backup_status.pack(side="left", padx=10)
        self.lbl_backup_fila = ctk.CTkLabel(backup_inner, text="",
                                              font=FONT_TINY, text_color="gray")
        self.lbl_backup_fila.pack(side="right")

        # Explicacao trava
        info_frame = ctk.CTkFrame(tab, fg_color=("gray88", "gray22"))
        info_frame.pack(fill="x", padx=5, pady=(0, 8))
        ctk.CTkLabel(info_frame,
                      text="Travar = banco NAO sera apagado na limpeza automatica do fim do mes. "
                           "Bancos sem trava sao removidos automaticamente no ultimo dia do mes.",
                      font=FONT_TINY, text_color="gray", wraplength=900).pack(padx=10, pady=5)

        # Pesquisa
        search_frame = ctk.CTkFrame(tab, fg_color="transparent")
        search_frame.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(search_frame, text="Pesquisar:", font=FONT_BODY).pack(side="left")
        self.banco_pesquisa = ctk.CTkEntry(search_frame, width=300,
                                            placeholder_text="Filtrar por nome do banco...")
        self.banco_pesquisa.pack(side="left", padx=8)
        self.banco_pesquisa.bind("<KeyRelease>", lambda e: self._render_bancos(self._bancos_cache))

        self.bancos_scroll = ctk.CTkScrollableFrame(tab)
        self.bancos_scroll.pack(fill="both", expand=True)

    def _refresh_bancos(self):
        for w in self.bancos_scroll.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.bancos_scroll, text="Carregando...",
                      text_color="gray", font=FONT_BODY).pack(pady=20)

        def _load():
            bancos = info_completa_bancos()
            self._bancos_cache = bancos
            self.after(0, lambda: self._render_bancos(bancos))

        threading.Thread(target=_load, daemon=True).start()

    def _render_bancos(self, bancos):
        for w in self.bancos_scroll.winfo_children():
            w.destroy()

        if not bancos:
            ctk.CTkLabel(self.bancos_scroll, text="Nenhum banco restaurado",
                          text_color="gray", font=FONT_BODY).pack(pady=20)
            return

        # Filtro pesquisa
        filtro = self.banco_pesquisa.get().strip().lower() if hasattr(self, 'banco_pesquisa') else ""
        if filtro:
            bancos = [b for b in bancos if filtro in b["nome_db"].lower() or filtro in b["nome_base"].lower()]

        if not bancos:
            ctk.CTkLabel(self.bancos_scroll, text="Nenhum banco encontrado",
                          text_color="gray", font=FONT_BODY).pack(pady=20)
            return

        # Header
        hdr = ctk.CTkFrame(self.bancos_scroll, fg_color="transparent")
        hdr.pack(fill="x", padx=5, pady=(0, 5))

        cols = [("Banco", 200), ("Tamanho", 80), ("Restaurado", 130), ("Status", 90)]
        for texto, largura in cols:
            ctk.CTkLabel(hdr, text=texto, font=FONT_SMALL, width=largura,
                          text_color="gray", anchor="w").pack(side="left", padx=2)

        total_mb = 0
        travados = 0

        for idx, b in enumerate(bancos):
            total_mb += b["tamanho_mb"]
            if b["protegido"]:
                travados += 1

            bg = COR_BG_CARD if idx % 2 == 0 else COR_BG_CARD_ALT
            row = ctk.CTkFrame(self.bancos_scroll, fg_color=bg)
            row.pack(fill="x", padx=5, pady=1)

            cor_status = COR_TRAVA if b["protegido"] else COR_SUCESSO
            status_txt = "Travado" if b["protegido"] else "Ativo"

            ctk.CTkLabel(row, text=b["nome_db"], font=FONT_MONO, width=200,
                          anchor="w").pack(side="left", padx=(8, 2))
            ctk.CTkLabel(row, text=f"{b['tamanho_mb']:.0f} MB", font=FONT_BODY,
                          width=80, anchor="w").pack(side="left", padx=2)
            ctk.CTkLabel(row, text=_formatar_data(b["data_restauracao"]),
                          font=FONT_SMALL, width=130, anchor="w").pack(side="left", padx=2)
            ctk.CTkLabel(row, text=status_txt, font=FONT_SMALL, width=90,
                          text_color=cor_status, anchor="w").pack(side="left", padx=2)

            # Botao travar/destravar
            nome_db = b["nome_db"]
            prot_val = not b["protegido"]

            if b["protegido"]:
                ctk.CTkButton(
                    row, text="Destravar", width=85, height=28,
                    fg_color="gray50", hover_color="gray40",
                    command=lambda db=nome_db, v=prot_val: self._toggle_protecao(db, v)
                ).pack(side="right", padx=(2, 5))
            else:
                ctk.CTkButton(
                    row, text="Travar", width=85, height=28,
                    fg_color=COR_TRAVA, hover_color="#8e44ad",
                    command=lambda db=nome_db, v=prot_val: self._toggle_protecao(db, v)
                ).pack(side="right", padx=(2, 5))

            # Botao dropar
            ctk.CTkButton(
                row, text="Dropar", width=70, height=28,
                fg_color=COR_ERRO, hover_color="#c0392b",
                command=lambda db=nome_db: self._dropar_banco(db)
            ).pack(side="right", padx=2)

        # Resumo
        resumo = ctk.CTkFrame(self.bancos_scroll, fg_color="transparent")
        resumo.pack(fill="x", padx=5, pady=(10, 5))
        ctk.CTkLabel(resumo,
                      text=f"Total: {len(bancos)} banco(s) | {total_mb:.0f} MB | {travados} travado(s)",
                      font=FONT_BODY, text_color="gray").pack(side="left")

    def _toggle_protecao(self, nome_db, protegido):
        marcar_protegido(nome_db, protegido)
        self._refresh_bancos()
        acao = "travado" if protegido else "destravado"
        self._set_status(f"Banco '{nome_db}' {acao}")

    def _dropar_banco(self, nome_db):
        if not messagebox.askyesno("Confirmar Drop",
                f"Dropar banco '{nome_db}'?\n\nEsta acao e irreversivel.\n"
                f"O banco sera permanentemente removido do PostgreSQL."):
            return

        def _drop():
            ok = dropar_banco_controlado(nome_db, force=True)
            if ok:
                self.after(0, lambda: self._set_status(f"Banco '{nome_db}' dropado"))
            else:
                self.after(0, lambda: self._set_status(f"Falha ao dropar '{nome_db}'"))
            self.after(0, self._refresh_bancos)

        threading.Thread(target=_drop, daemon=True).start()

    # =========================================================================
    # TAB: Fila SPED
    # =========================================================================

    def _build_tab_fila(self):
        tab = self.tab_fila

        # === Card progresso atual ===
        self.prog_card = ctk.CTkFrame(tab, fg_color=("gray88", "gray22"))
        self.prog_card.pack(fill="x", padx=5, pady=(5, 10))

        prog_header = ctk.CTkFrame(self.prog_card, fg_color="transparent")
        prog_header.pack(fill="x", padx=15, pady=(10, 5))

        self.lbl_prog_titulo = ctk.CTkLabel(prog_header, text="Sistema Parado",
                                              font=FONT_HEADER, text_color="gray")
        self.lbl_prog_titulo.pack(side="left")
        self.lbl_prog_etapa = ctk.CTkLabel(prog_header, text="",
                                             font=FONT_SMALL, text_color="gray")
        self.lbl_prog_etapa.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(self.prog_card, height=16)
        self.progress_bar.pack(fill="x", padx=15, pady=5)
        self.progress_bar.set(0)

        prog_detail = ctk.CTkFrame(self.prog_card, fg_color="transparent")
        prog_detail.pack(fill="x", padx=15, pady=(0, 10))

        self.lbl_prog_empresa = ctk.CTkLabel(prog_detail, text="",
                                               font=FONT_BODY, text_color=COR_INFO)
        self.lbl_prog_empresa.pack(side="left")
        self.lbl_prog_proximo = ctk.CTkLabel(prog_detail, text="",
                                               font=FONT_SMALL, text_color="gray")
        self.lbl_prog_proximo.pack(side="right")

        # === Pipeline visual ===
        self.pipeline_frame = ctk.CTkFrame(tab, fg_color=("gray88", "gray22"))
        # Nao pack aqui — so aparece quando pipeline ativo

        # === Contadores ===
        counter_frame = ctk.CTkFrame(tab, fg_color="transparent")
        counter_frame.pack(fill="x", padx=5, pady=(0, 8))

        self.lbl_counter_ok = ctk.CTkLabel(counter_frame, text="OK: 0",
                                             font=FONT_BODY, text_color=COR_SUCESSO)
        self.lbl_counter_ok.pack(side="left", padx=10)
        self.lbl_counter_erro = ctk.CTkLabel(counter_frame, text="Erros: 0",
                                               font=FONT_BODY, text_color=COR_ERRO)
        self.lbl_counter_erro.pack(side="left", padx=10)
        self.lbl_counter_restante = ctk.CTkLabel(counter_frame, text="Restantes: 0",
                                                    font=FONT_BODY, text_color=COR_AVISO)
        self.lbl_counter_restante.pack(side="left", padx=10)

        ctk.CTkButton(counter_frame, text="Atualizar", width=90, height=28,
                       command=self._refresh_fila).pack(side="right")

        # Filtro
        toolbar = ctk.CTkFrame(tab, fg_color="transparent")
        toolbar.pack(fill="x", padx=5, pady=(0, 5))

        self.fila_filtro = ctk.CTkSegmentedButton(
            toolbar, values=["Todos", "Liberada", "Gerada", "Erro", "Pendente"],
            command=lambda v: self._render_fila(self._empresas_cache)
        )
        self.fila_filtro.set("Todos")
        self.fila_filtro.pack(side="left")

        # Pesquisa
        ctk.CTkLabel(toolbar, text="Pesquisar:", font=FONT_BODY).pack(side="left", padx=(15, 5))
        self.fila_pesquisa = ctk.CTkEntry(toolbar, width=250,
                                           placeholder_text="Nome do posto...")
        self.fila_pesquisa.pack(side="left", padx=5)
        self.fila_pesquisa.bind("<KeyRelease>", lambda e: self._render_fila(self._empresas_cache))

        self.fila_scroll = ctk.CTkScrollableFrame(tab)
        self.fila_scroll.pack(fill="both", expand=True)

    def _refresh_fila(self, filtro=None):
        for w in self.fila_scroll.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.fila_scroll, text="Carregando...",
                      text_color="gray", font=FONT_BODY).pack(pady=20)

        def _load():
            try:
                resp = get_client().table("empresas").select(
                    "id, nome, nome_base, status, informacoes_sped, data_liberacao"
                ).order("nome").execute()
                empresas = resp.data or []
            except Exception as e:
                self.after(0, lambda: self._render_fila_erro(str(e)))
                return
            self._empresas_cache = empresas
            self.after(0, lambda: self._render_fila(empresas))

        threading.Thread(target=_load, daemon=True).start()

    def _render_fila_erro(self, msg):
        for w in self.fila_scroll.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.fila_scroll, text=f"Erro Supabase: {msg}",
                      text_color=COR_ERRO, font=FONT_BODY).pack(pady=20)

    def _render_fila(self, empresas):
        for w in self.fila_scroll.winfo_children():
            w.destroy()

        if not empresas:
            ctk.CTkLabel(self.fila_scroll, text="Nenhuma empresa encontrada",
                          text_color="gray", font=FONT_BODY).pack(pady=20)
            return

        filtro_status = self.fila_filtro.get()
        filtro_texto = self.fila_pesquisa.get().strip().lower() if hasattr(self, 'fila_pesquisa') else ""
        gerados_local = listar_gerados()

        # Filtro por status
        if filtro_status == "Pendente":
            empresas = [e for e in empresas
                        if e.get("status", "").lower() == "liberada"
                        and str(e["id"]) not in gerados_local]
        elif filtro_status != "Todos":
            empresas = [e for e in empresas
                        if e.get("status", "").lower() == filtro_status.lower()]

        # Filtro por texto
        if filtro_texto:
            empresas = [e for e in empresas if filtro_texto in e.get("nome", "").lower()]

        cores_status = {
            "liberada": COR_AVISO,
            "gerada": COR_SUCESSO,
            "erro": COR_ERRO,
            "em_processo": COR_INFO,
        }

        if not empresas:
            ctk.CTkLabel(self.fila_scroll, text="Nenhuma empresa encontrada com esse filtro",
                          text_color="gray", font=FONT_BODY).pack(pady=20)
            return

        for idx, e in enumerate(empresas):
            bg = COR_BG_CARD if idx % 2 == 0 else COR_BG_CARD_ALT
            row = ctk.CTkFrame(self.fila_scroll, fg_color=bg)
            row.pack(fill="x", padx=5, pady=1)

            status = e.get("status", "?")
            cor = cores_status.get(status, "gray")
            eid = str(e["id"])
            reg = gerados_local.get(eid)

            ctk.CTkLabel(row, text=e["nome"], font=FONT_BODY, width=280,
                          anchor="w").pack(side="left", padx=(8, 2))
            ctk.CTkLabel(row, text=e.get("nome_base", "-"), font=FONT_SMALL,
                          width=100, anchor="w", text_color="gray").pack(side="left", padx=2)
            ctk.CTkLabel(row, text=status.upper(), font=FONT_SMALL, width=90,
                          text_color=cor, anchor="w").pack(side="left", padx=2)
            ctk.CTkLabel(row, text=e.get("informacoes_sped") or "padrao", font=FONT_TINY,
                          width=120, anchor="w", text_color="gray").pack(side="left", padx=2)

            # Status local
            if reg and reg.get("status") == "erro":
                ctk.CTkLabel(row, text="ERRO LOCAL", font=FONT_SMALL, width=80,
                              text_color=COR_ERRO).pack(side="right", padx=5)
            elif reg:
                data_ger = _formatar_data(reg.get("data_geracao", ""))
                ctk.CTkLabel(row, text=f"Gerado {data_ger}", font=FONT_TINY, width=140,
                              text_color=COR_SUCESSO).pack(side="right", padx=5)

    # Mapeamento etapa -> (label, cor)
    _ETAPA_DISPLAY = {
        "backup":      ("Baixando",    COR_AVISO),
        "restaurando": ("Restaurando", COR_AVISO),
        "corrigindo":  ("Corrigindo",  COR_INFO),
        "aguardando":  ("Pronto",      "gray"),
        "gerando":     ("Gerando SPED", COR_SUCESSO),
        "concluido":   ("Concluido",   COR_SUCESSO),
        "erro":        ("Erro",        COR_ERRO),
    }

    def _refresh_progresso(self):
        """Le progresso.json e atualiza cards + pipeline."""
        estado = progresso.ler()
        pipeline = estado.get("pipeline", {})

        if estado.get("ativo"):
            self.header_prog_frame.pack(side="left", padx=30)

            idx = estado.get("indice_atual", 0)
            total = estado.get("total_empresas", 1) or 1

            # Progresso baseado no pipeline (mais preciso)
            if pipeline:
                n_concluidos = sum(1 for v in pipeline.values() if v.get("etapa") == "concluido")
                n_erros = sum(1 for v in pipeline.values() if v.get("etapa") == "erro")
                n_gerando = sum(1 for v in pipeline.values() if v.get("etapa") == "gerando")
                n_prep = sum(1 for v in pipeline.values()
                             if v.get("etapa") in ("backup", "restaurando", "corrigindo"))
                n_aguardando = sum(1 for v in pipeline.values() if v.get("etapa") == "aguardando")
                pct = (n_concluidos + n_erros) / total if total else 0

                titulo = f"Pipeline ({n_concluidos}/{total})"
                if n_gerando:
                    nomes_ger = [v["nome"] for v in pipeline.values() if v.get("etapa") == "gerando"]
                    titulo += f" — SPED: {nomes_ger[0]}"
                if n_prep:
                    titulo += f" | {n_prep} preparando"

                self.lbl_prog_titulo.configure(text=titulo, text_color=COR_INFO)
                self.lbl_prog_etapa.configure(
                    text=f"{n_prep} prep | {n_aguardando} prontos | {n_gerando} gerando"
                )
            else:
                pct = idx / total
                self.lbl_prog_titulo.configure(
                    text=f"Gerando SPED ({idx}/{total})", text_color=COR_INFO
                )
                self.lbl_prog_etapa.configure(text=estado.get("etapa", ""))
                n_concluidos = len(estado.get("concluidos", []))
                n_erros = len(estado.get("erros", []))

            self.lbl_prog_empresa.configure(text=estado.get("empresa_atual", ""))
            self.progress_bar.set(pct)
            self.progress_bar_global.set(pct)
            self.lbl_prog_global.configure(text=f"{n_concluidos}/{total}" if pipeline else f"{idx}/{total}")

            proxima = estado.get("proxima", "")
            self.lbl_prog_proximo.configure(text=f"Proximo: {proxima}" if proxima else "")

            restantes = total - n_concluidos - n_erros if pipeline else total - idx
            self.lbl_counter_ok.configure(text=f"OK: {n_concluidos}")
            self.lbl_counter_erro.configure(text=f"Erros: {n_erros}")
            self.lbl_counter_restante.configure(text=f"Restantes: {restantes}")
        else:
            self.header_prog_frame.pack_forget()

            etapa = estado.get("etapa", "")
            if etapa and "Finalizado" in etapa:
                self.lbl_prog_titulo.configure(text=etapa, text_color=COR_SUCESSO)
            else:
                self.lbl_prog_titulo.configure(text="Sistema parado", text_color="gray")

            self.lbl_prog_etapa.configure(text="")
            self.lbl_prog_empresa.configure(text="")
            self.lbl_prog_proximo.configure(text="")
            self.progress_bar.set(0)

            concluidos = len(estado.get("concluidos", []))
            erros = len(estado.get("erros", []))
            self.lbl_counter_ok.configure(text=f"OK: {concluidos}")
            self.lbl_counter_erro.configure(text=f"Erros: {erros}")
            self.lbl_counter_restante.configure(text="Restantes: 0")

        # --- Pipeline visual (lista de empresas com etapa) ---
        self._render_pipeline(pipeline)

    def _render_pipeline(self, pipeline: dict):
        """Renderiza lista de empresas no pipeline com etapa atual."""
        # Limpa widgets anteriores
        for w in self.pipeline_frame.winfo_children():
            w.destroy()

        if not pipeline:
            self.pipeline_frame.pack_forget()
            return

        self.pipeline_frame.pack(fill="x", padx=5, pady=(0, 8), after=self.prog_card)

        ctk.CTkLabel(self.pipeline_frame, text="Pipeline de Processamento",
                      font=FONT_HEADER).pack(anchor="w", padx=10, pady=(8, 4))

        # Ordena: gerando primeiro, depois preparando, aguardando, concluido, erro
        ordem_etapa = {
            "gerando": 0, "backup": 1, "restaurando": 2, "corrigindo": 3,
            "aguardando": 4, "concluido": 5, "erro": 6,
        }
        items = sorted(pipeline.items(),
                       key=lambda x: ordem_etapa.get(x[1].get("etapa", ""), 9))

        for idx, (emp_id, info) in enumerate(items):
            nome = info.get("nome", f"ID {emp_id}")
            etapa = info.get("etapa", "?")
            label, cor = self._ETAPA_DISPLAY.get(etapa, (etapa, "gray"))

            bg = COR_BG_CARD if idx % 2 == 0 else COR_BG_CARD_ALT
            row = ctk.CTkFrame(self.pipeline_frame, fg_color=bg, height=28)
            row.pack(fill="x", padx=5, pady=1)

            # Icone de etapa
            icone = {"backup": ">>", "restaurando": ">>", "corrigindo": "..",
                     "aguardando": "--", "gerando": "**", "concluido": "OK",
                     "erro": "XX"}.get(etapa, "??")

            ctk.CTkLabel(row, text=icone, font=FONT_MONO, width=30,
                          text_color=cor).pack(side="left", padx=(8, 2))
            ctk.CTkLabel(row, text=nome[:35], font=FONT_BODY, width=250,
                          anchor="w").pack(side="left", padx=2)
            ctk.CTkLabel(row, text=label, font=FONT_SMALL, width=120,
                          text_color=cor, anchor="w").pack(side="left", padx=2)

        ctk.CTkLabel(self.pipeline_frame, text="", height=4).pack()  # spacer

    # =========================================================================
    # TAB: Logs
    # =========================================================================

    def _build_tab_logs(self):
        tab = self.tab_logs

        toolbar = ctk.CTkFrame(tab, fg_color="transparent")
        toolbar.pack(fill="x", pady=(5, 10))

        ctk.CTkLabel(toolbar, text="Logs do Sistema", font=FONT_HEADER).pack(side="left")
        ctk.CTkButton(toolbar, text="Atualizar", width=90, height=30,
                       command=self._refresh_logs).pack(side="right")
        ctk.CTkButton(toolbar, text="Limpar", width=70, height=30,
                       fg_color="gray40",
                       command=self._limpar_logs_view).pack(side="right", padx=5)

        # Pesquisa logs
        ctk.CTkLabel(toolbar, text="Filtrar:", font=FONT_BODY).pack(side="left", padx=(15, 5))
        self.log_filtro = ctk.CTkEntry(toolbar, width=250,
                                        placeholder_text="Texto para filtrar nos logs...")
        self.log_filtro.pack(side="left", padx=5)
        self.log_filtro.bind("<Return>", lambda e: self._refresh_logs())

        self.log_linhas = ctk.CTkTextbox(tab, font=FONT_MONO, state="disabled",
                                          wrap="word")
        self.log_linhas.pack(fill="both", expand=True)

        self.log_linhas.tag_config("ERROR", foreground=COR_ERRO)
        self.log_linhas.tag_config("WARNING", foreground=COR_AVISO)
        self.log_linhas.tag_config("INFO", foreground="#aaaaaa")
        self.log_linhas.tag_config("SUCCESS", foreground=COR_SUCESSO)

    def _refresh_logs(self):
        log_files = [
            os.path.join(_base_dir, "spedgenerator.log"),
            os.path.join(_base_dir, "teste_dm_gui.log"),
        ]

        filtro = self.log_filtro.get().strip().lower() if hasattr(self, 'log_filtro') else ""

        self.log_linhas.configure(state="normal")
        self.log_linhas.delete("1.0", "end")

        for log_path in log_files:
            if not os.path.exists(log_path):
                continue
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                for line in lines[-300:]:
                    if filtro and filtro not in line.lower():
                        continue
                    if "[ERROR]" in line:
                        tag = "ERROR"
                    elif "[WARNING]" in line:
                        tag = "WARNING"
                    elif "[OK]" in line or "concluido" in line.lower():
                        tag = "SUCCESS"
                    else:
                        tag = "INFO"
                    self.log_linhas.insert("end", line, tag)
                self.log_linhas.insert("end", "\n")
            except Exception:
                pass

        self.log_linhas.configure(state="disabled")
        self.log_linhas.see("end")

    def _limpar_logs_view(self):
        self.log_linhas.configure(state="normal")
        self.log_linhas.delete("1.0", "end")
        self.log_linhas.configure(state="disabled")

    # =========================================================================
    # TAB: Acesso Remoto
    # =========================================================================

    def _build_tab_remoto(self):
        tab = self.tab_remoto

        ctk.CTkLabel(tab, text="Gerador de INI — Acesso Remoto",
                      font=FONT_HEADER).pack(anchor="w", pady=(10, 15), padx=10)

        info_frame = ctk.CTkFrame(tab, fg_color=("gray88", "gray22"))
        info_frame.pack(fill="x", padx=10, pady=(0, 15))

        ctk.CTkLabel(info_frame, text=f"IP Servidor: {self.ip_servidor}",
                      font=FONT_BODY, text_color=COR_INFO).pack(anchor="w", padx=15, pady=5)
        ctk.CTkLabel(info_frame,
                      text="Gera acsgerente.ini apontando pro banco remoto.\n"
                           "Copie o INI gerado pro computador que vai acessar os dados.",
                      font=FONT_SMALL, text_color="gray").pack(anchor="w", padx=15, pady=(0, 10))

        # Selecao de banco com pesquisa
        sel_frame = ctk.CTkFrame(tab, fg_color="transparent")
        sel_frame.pack(fill="x", padx=10, pady=(0, 5))

        ctk.CTkLabel(sel_frame, text="Pesquisar banco:", font=FONT_BODY).pack(side="left")
        self.remoto_pesquisa = ctk.CTkEntry(sel_frame, width=250,
                                             placeholder_text="Digite pra filtrar...")
        self.remoto_pesquisa.pack(side="left", padx=8)
        self.remoto_pesquisa.bind("<KeyRelease>", lambda e: self._filtrar_bancos_combo())

        ctk.CTkButton(sel_frame, text="Atualizar Lista", width=120, height=30,
                       command=self._refresh_bancos_combo).pack(side="right")

        # Lista de bancos (ao inves de combo, usa listbox estilizado)
        banco_sel_frame = ctk.CTkFrame(tab, fg_color="transparent")
        banco_sel_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(banco_sel_frame, text="Banco:", font=FONT_BODY).pack(side="left")
        self.combo_banco = ctk.CTkComboBox(banco_sel_frame, width=350,
                                            command=self._preview_ini)
        self.combo_banco.pack(side="left", padx=10)

        # IP customizavel
        ctk.CTkLabel(banco_sel_frame, text="IP:", font=FONT_BODY).pack(side="left", padx=(20, 5))
        self.remoto_ip = ctk.CTkEntry(banco_sel_frame, width=150)
        self.remoto_ip.pack(side="left")
        self.remoto_ip.insert(0, self.ip_servidor)
        self.remoto_ip.bind("<KeyRelease>", lambda e: self._preview_ini())

        # Preview INI
        ctk.CTkLabel(tab, text="Preview do INI:", font=FONT_BODY).pack(anchor="w", padx=10)
        self.ini_preview = ctk.CTkTextbox(tab, font=FONT_MONO, height=180)
        self.ini_preview.pack(fill="x", padx=10, pady=5)

        # Botoes
        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(btn_frame, text="Copiar INI", width=150,
                       fg_color=COR_INFO,
                       command=self._copiar_ini).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Salvar INI como...", width=150,
                       command=self._salvar_ini).pack(side="left", padx=5)

    def _refresh_bancos_combo(self):
        bancos = listar_bancos_ativos()
        self._bancos_combo_lista = list(bancos.keys()) if bancos else []
        nomes = self._bancos_combo_lista or ["(nenhum banco ativo)"]
        self.combo_banco.configure(values=nomes)
        if nomes:
            self.combo_banco.set(nomes[0])
            self._preview_ini(nomes[0])

    def _filtrar_bancos_combo(self):
        """Filtra lista de bancos no combo conforme digitacao."""
        filtro = self.remoto_pesquisa.get().strip().lower()
        todos = getattr(self, '_bancos_combo_lista', [])
        if filtro:
            filtrados = [b for b in todos if filtro in b.lower()]
        else:
            filtrados = todos

        nomes = filtrados or ["(nenhum resultado)"]
        self.combo_banco.configure(values=nomes)
        if filtrados:
            self.combo_banco.set(filtrados[0])
            self._preview_ini(filtrados[0])

    def _gerar_ini_conteudo(self, nome_db: str) -> str:
        """Gera conteudo do INI apontando pro servidor remoto."""
        ip = self.remoto_ip.get().strip() or self.ip_servidor

        template_path = os.path.join(os.path.dirname(config.ACS_INI_PATH), "acsgerenteNV.ini")
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8-sig") as f:
                conteudo = f.read()
        else:
            conteudo = (
                "[Banco de Dados]\n"
                "NomeServidor=localhost\n"
                "Caminho=banco\n"
                "Driver=PostgreSQL\n"
                "Porta=5432\n"
                "Usuario=postgres\n"
                "Senha=JAwd\n"
            )

        conteudo = re.sub(r"(?m)^NomeServidor=.*$", f"NomeServidor={ip}", conteudo)
        conteudo = re.sub(r"(?m)^Caminho=.*$", f"Caminho={nome_db}", conteudo)
        conteudo = re.sub(r"(?m)^Porta=.*$", f"Porta={config.PG_PORT}", conteudo)
        return conteudo

    def _preview_ini(self, nome_db=None):
        if not nome_db:
            nome_db = self.combo_banco.get()
        if not nome_db or nome_db.startswith("("):
            return

        conteudo = self._gerar_ini_conteudo(nome_db)
        self.ini_preview.delete("1.0", "end")
        self.ini_preview.insert("1.0", conteudo)

    def _copiar_ini(self):
        conteudo = self.ini_preview.get("1.0", "end").strip()
        if conteudo:
            self.clipboard_clear()
            self.clipboard_append(conteudo)
            self._set_status("INI copiado para clipboard")

    def _salvar_ini(self):
        conteudo = self.ini_preview.get("1.0", "end").strip()
        if not conteudo:
            return

        path = filedialog.asksaveasfilename(
            title="Salvar INI",
            defaultextension=".ini",
            filetypes=[("INI files", "*.ini"), ("All files", "*.*")],
            initialfile="acsgerente.ini"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(conteudo)
            self._set_status(f"INI salvo: {path}")

    # =========================================================================
    # Backup status refresh
    # =========================================================================

    def _refresh_backup_status(self):
        """Atualiza card de status do backup na tab Bancos."""
        try:
            prog = ler_progresso_backup()
        except Exception:
            prog = {"status": "ocioso"}

        status = prog.get("status", "ocioso")
        total = prog.get("total", 0)
        concluidos = prog.get("concluidos", 0)
        erros = prog.get("erros", 0)
        resultado = prog.get("resultado", "")
        bancos = prog.get("bancos", {})

        # Bancos atualmente executando
        executando = [n for n, info in bancos.items() if info.get("status") == "executando"]

        if status == "executando" and executando:
            nomes = ", ".join(executando[:3])
            extras = f" +{len(executando)-3}" if len(executando) > 3 else ""
            self.lbl_backup_status.configure(
                text=f"pg_dump: {nomes}{extras} ({concluidos}/{total} OK, {erros} erros)",
                text_color=COR_AVISO
            )
            fila = prog.get("fila", [])
            pendentes = [n for n in fila if n not in executando and n not in
                         [b for b, i in bancos.items() if i.get("status") in ("concluido", "erro")]]
            if pendentes:
                self.lbl_backup_fila.configure(
                    text=f"Fila: {', '.join(pendentes[:5])}"
                )
            else:
                self.lbl_backup_fila.configure(text="")
        elif status == "executando":
            self.lbl_backup_status.configure(
                text=f"Backup: {concluidos}/{total} OK, {erros} erros",
                text_color=COR_AVISO
            )
            self.lbl_backup_fila.configure(text="")
        else:
            if resultado:
                self.lbl_backup_status.configure(
                    text=f"Backup ocioso ({resultado})",
                    text_color="gray"
                )
            else:
                self.lbl_backup_status.configure(
                    text="Backup ocioso",
                    text_color="gray"
                )
            self.lbl_backup_fila.configure(text="")

    # =========================================================================
    # Daemon status refresh
    # =========================================================================

    def _refresh_daemon_status(self):
        """Atualiza indicador de daemon no header."""
        estado = _ler_daemon_state()
        status = estado.get("status", "parado")

        if status == "rodando":
            ciclos = estado.get("ciclos_completos", 0)
            self.lbl_daemon.configure(
                text=f"DAEMON ativo (ciclo #{ciclos})",
                text_color=COR_SUCESSO
            )
        elif status == "aguardando":
            proximo = estado.get("proximo_ciclo", "")
            self.lbl_daemon.configure(
                text=f"DAEMON aguardando (prox: {proximo})",
                text_color=COR_INFO
            )
        else:
            self.lbl_daemon.configure(
                text="DAEMON parado",
                text_color="gray50"
            )

    # =========================================================================
    # Helpers
    # =========================================================================

    def _set_status(self, msg: str):
        self.lbl_status.configure(text=msg)
        self.after(5000, lambda: self.lbl_status.configure(text=""))

    def _refresh_all(self):
        self._refresh_arquivos()
        self._refresh_bancos()
        self._refresh_fila()
        self._refresh_logs()
        self._refresh_bancos_combo()
        self._refresh_progresso()
        self._refresh_backup_status()
        self._refresh_daemon_status()
        self._update_footer()
        self.after(5000, self._auto_refresh)

    def _auto_refresh(self):
        """Refresh periodico: progresso rapido, logs moderado."""
        self._refresh_progresso()
        self._refresh_backup_status()
        self._refresh_daemon_status()
        self._update_footer()

        # Logs a cada 30s (6 ciclos de 5s)
        if not hasattr(self, '_log_counter'):
            self._log_counter = 0
        self._log_counter += 1
        if self._log_counter >= 6:
            self._refresh_logs()
            self._log_counter = 0

        self.after(5000, self._auto_refresh)

    def _update_footer(self):
        gerados = listar_gerados()
        bancos = listar_bancos_ativos()
        agora = datetime.now().strftime("%H:%M:%S")
        self.lbl_footer.configure(
            text=f"Gerados: {len(gerados)} | Bancos ativos: {len(bancos)} | Atualizado: {agora}"
        )

        usado_gb, total_gb = _espaco_disco(config.SPED_EXPORT_DIR)
        livre_gb = total_gb - usado_gb
        cor_disco = COR_ERRO if livre_gb < 10 else COR_AVISO if livre_gb < 30 else "gray"
        self.lbl_disco.configure(
            text=f"Disco: {livre_gb:.0f} GB livre / {total_gb:.0f} GB",
            text_color=cor_disco
        )


# =============================================================================
# Main
# =============================================================================

def main():
    app = PainelApp()
    app.mainloop()


if __name__ == "__main__":
    main()
