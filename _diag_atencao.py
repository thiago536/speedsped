"""Lanca o ACS e dump do conteudo (texto + botoes) do popup 'Atencao' que trava o startup."""
import subprocess, time
from pywinauto import Desktop

def safe(s):
    try:
        return s.encode("ascii", "replace").decode("ascii")
    except Exception:
        return "?"

EXE = r"C:\ACSSoft\Sintese\Gerente SPED\gerente.exe"
proc = subprocess.Popen([EXE])
print(f"gerente.exe pid={proc.pid}", flush=True)
time.sleep(10)

d = Desktop(backend="win32")
for w in d.windows():
    try:
        if w.process_id() != proc.pid:
            continue
        cls = w.class_name()
        ttl = safe(w.window_text())
    except Exception:
        continue
    print(f"\n=== JANELA class={cls!r} title={ttl!r} ===", flush=True)
    try:
        for c in w.descendants():
            try:
                cc = c.class_name()
                ct = safe(c.window_text())
                if ct.strip() or "Button" in cc or "Edit" in cc:
                    print(f"   [{cc}] {ct!r}", flush=True)
            except Exception:
                pass
    except Exception as e:
        print("   (erro descendants:", e, ")", flush=True)
