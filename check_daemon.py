import os

paths = {
    "env": r"C:\SpedGenerator\.env",
    "export_dir": r"C:\ACS_Exporta",
    "lock_file": r"C:\ACS_Exporta\spedgenerator.lock",
    "daemon_log": r"C:\ACS_Exporta\daemon.log",
    "sped_log": r"C:\SpedGenerator\spedgenerator.log"
}

print("=== DIAGNOSTICO DO DAEMON ===")

# 1. Verificar pastas e arquivos essenciais
for name, path in paths.items():
    status = "Existe" if os.path.exists(path) else "NAO ENCONTRADO"
    print(f"[{name.upper()}]: {path} -> {status}")

# 2. Verificar o lock file (pode estar impedindo de iniciar)
if os.path.exists(paths["lock_file"]):
    try:
        with open(paths["lock_file"], "r") as f:
            pid = f.read().strip()
        print(f"-> AVISO: Lock file ativo com PID {pid}. Outra instancia pode estar rodando ou travada.")
    except Exception as e:
        print(f"-> Erro ao ler lock file: {e}")

# 3. Ler o final de daemon.log
print("\n=== ULTIMAS LINHAS DE daemon.log ===")
if os.path.exists(paths["daemon_log"]):
    try:
        with open(paths["daemon_log"], "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        for line in lines[-25:]:
            print(line, end="")
    except Exception as e:
        print(f"Erro ao ler daemon.log: {e}")
else:
    print("Nenhum arquivo daemon.log encontrado.")

# 4. Ler o final de spedgenerator.log
print("\n=== ULTIMAS LINHAS DE spedgenerator.log ===")
if os.path.exists(paths["sped_log"]):
    try:
        with open(paths["sped_log"], "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        for line in lines[-25:]:
            print(line, end="")
    except Exception as e:
        print(f"Erro ao ler spedgenerator.log: {e}")
else:
    print("Nenhum arquivo spedgenerator.log encontrado.")
