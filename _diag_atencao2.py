"""Captura o conteudo do popup 'Atencao' (#32770) que trava o startup do ACS."""
import subprocess, time
from pywinauto import Desktop

def safe(s):
    try:
        return s.encode("ascii", "replace").decode("ascii")
    except Exception:
        return "?"

EXE = r"C:\ACSSoft\Sintese\Gerente SPED\gerente.exe"

for tentativa in range(1, 4):  # ate 3 lancamentos para pegar o popup intermitente
    proc = subprocess.Popen([EXE])
    print(f"\n########## LANCAMENTO {tentativa} (pid={proc.pid}) ##########", flush=True)
    achou_dialog = False
    for i in range(30):  # ~15s
        time.sleep(0.5)
        try:
            d = Desktop(backend="win32")
            for w in d.windows():
                try:
                    if w.process_id() != proc.pid:
                        continue
                    cls = w.class_name(); ttl = safe(w.window_text())
                except Exception:
                    continue
                if cls == "#32770":
                    print(f"[{i*0.5:.1f}s] >>> POPUP class={cls!r} title={ttl!r}", flush=True)
                    try:
                        for c in w.descendants():
                            try:
                                cc = c.class_name(); ct = safe(c.window_text())
                                if ct.strip() or "Button" in cc:
                                    print(f"      [{cc}] {ct!r}", flush=True)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    achou_dialog = True
        except Exception:
            pass
        if achou_dialog:
            break
    try:
        proc.terminate()
    except Exception:
        pass
    time.sleep(2)
    if achou_dialog:
        print("CAPTURADO — parando.", flush=True)
        break
