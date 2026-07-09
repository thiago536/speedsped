# -*- coding: utf-8 -*-
"""Observa o startup do Gerente sem fechar nada: registra todas as janelas/dialogs
que aparecerem e tira screenshot a cada mudanca. Uso: python observar_startup_nat.py [segundos]"""
import sys, time, subprocess, os

EXE = r"C:\ACSSoft\Sintese\Gerente SPED\gerente.exe"
CWD = r"C:\ACSSoft\Sintese\Gerente SPED"
OUT = r"C:\SpedGenerator\observacao_nat.log"
SHOTS = r"C:\SpedGenerator"

from pywinauto import Desktop
from PIL import ImageGrab

log = open(OUT, "w", encoding="utf-8")
def w(msg):
    log.write(f"{time.strftime('%H:%M:%S')} {msg}\n"); log.flush()

dur = int(sys.argv[1]) if len(sys.argv) > 1 else 90
proc = subprocess.Popen([EXE], cwd=CWD)
w(f"gerente.exe lancado pid={proc.pid}")

vistos = set()
shot_n = 0
t0 = time.time()
while time.time() - t0 < dur:
    if proc.poll() is not None:
        w(f"PROCESSO ENCERROU sozinho, exit code={proc.returncode}")
        break
    try:
        for win in Desktop(backend="win32").windows():
            try:
                pid = win.process_id()
            except Exception:
                continue
            if pid != proc.pid:
                continue
            titulo = win.window_text()
            classe = win.class_name()
            chave = (titulo, classe)
            if chave not in vistos:
                vistos.add(chave)
                w(f"JANELA NOVA: titulo={titulo!r} classe={classe}")
                # texto dos filhos (statics = corpo do dialog)
                try:
                    for ch in win.children():
                        t = ch.window_text()
                        if t:
                            w(f"    filho[{ch.class_name()}]: {t!r}")
                except Exception as e:
                    w(f"    (erro lendo filhos: {e})")
                shot_n += 1
                try:
                    ImageGrab.grab(all_screens=True).save(
                        os.path.join(SHOTS, f"teste_nat_shot{shot_n}.png"))
                    w(f"    screenshot teste_nat_shot{shot_n}.png")
                except Exception as e:
                    w(f"    (erro screenshot: {e})")
    except Exception as e:
        w(f"erro enum: {e}")
    time.sleep(1)
else:
    w("tempo esgotado; processo ainda vivo" if proc.poll() is None else "fim")
w("FIM observacao")
log.close()
