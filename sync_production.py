import os
import shutil

src_dir = r"C:\SpedGeneretor"
dest_dir = r"C:\SpedGenerator"

print(f"=== Sincronizando Arquivos para {dest_dir} ===")

if not os.path.exists(dest_dir):
    os.makedirs(dest_dir)

files_copied = 0
for item in os.listdir(src_dir):
    src_path = os.path.join(src_dir, item)
    dest_path = os.path.join(dest_dir, item)
    
    if item in (".git", ".idea", ".vscode", "__pycache__", "setup.ps1", ".env", "sync_production.py", "check_daemon.py", "debug_env.py", "fix_env.py"):
        continue
        
    if os.path.isfile(src_path):
        shutil.copy2(src_path, dest_path)
        print(f"-> Copiado: {item}")
        files_copied += 1
    elif os.path.isdir(src_path):
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path)
        shutil.copytree(src_path, dest_path)
        print(f"-> Copiada pasta: {item}")
        files_copied += 1

print(f"Total de {files_copied} itens sincronizados.")

env_path = os.path.join(dest_dir, ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        env_content = f.read()
    
    if "DISABLE_REMOTE_BACKUP" not in env_content:
        separator = "" if env_content.endswith("\n") else "\n"
        with open(env_path, "a", encoding="utf-8") as f:
            f.write(f"{separator}DISABLE_REMOTE_BACKUP=True\n")
        print("-> Inserido DISABLE_REMOTE_BACKUP=True no arquivo .env!")
    else:
        lines = env_content.splitlines()
        new_lines = []
        for line in lines:
            if line.startswith("DISABLE_REMOTE_BACKUP"):
                new_lines.append("DISABLE_REMOTE_BACKUP=True")
            else:
                new_lines.append(line)
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines) + "\n")
        print("-> DISABLE_REMOTE_BACKUP ja existia e foi garantido como True no arquivo .env!")
else:
    print("ERRO: O arquivo .env oficial em C:\\SpedGenerator\\.env nao foi encontrado!")

print("\n=== CONCLUIDO COM SUCESSO ===")
