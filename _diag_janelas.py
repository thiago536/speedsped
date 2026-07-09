"""Diagnostico: lanca o ACS Gerente e lista TODAS as janelas visiveis (titulo/classe)
para descobrir o titulo real da janela de login/principal e dos popups de startup."""
import subprocess, time
from pywinauto import Desktop

EXE = r"C:\ACSSoft\Sintese\Gerente SPED\gerente.exe"
proc = subprocess.Popen([EXE])
print(f"gerente.exe lancado: pid={proc.pid}", flush=True)

for espera in (8, 16, 24):
    time.sleep(8)
    print(f"\n===== ESTADO APOS ~{espera}s =====", flush=True)
    try:
        d = Desktop(backend="win32")
        for w in d.windows():
            try:
                t = w.window_text(); c = w.class_name()
                v = w.is_visible(); pid = w.process_id()
            except Exception:
                continue
            if v and (t.strip() or pid == proc.pid):
                mark = "  <== GERENTE" if pid == proc.pid else ""
                print(f"pid={pid} | class={c!r} | title={t!r}{mark}", flush=True)
    except Exception as e:
        print("erro enum:", e, flush=True)
