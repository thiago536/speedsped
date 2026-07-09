import os
from supabase import create_client

env_path = r"C:\SpedGenerator\.env"
print(f"=== Analisando arquivo: {env_path} ===")
if not os.path.exists(env_path):
    print("ERRO: O arquivo C:\\SpedGenerator\\.env NAO EXISTE no servidor!")
else:
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        lines = content.splitlines()
        url = ""
        key = ""
        for line in lines:
            if not line.strip() or line.startswith("#"):
                continue
            if "=" in line:
                parts = line.split("=", 1)
                k = parts[0].strip()
                v = parts[1].strip() if len(parts) > 1 else ""
                if k == "SUPABASE_URL":
                    url = v
                    print(f"SUPABASE_URL = {url}")
                elif k == "SUPABASE_KEY":
                    key = v
                    masked = v[:15] + "..." + v[-15:] if len(v) > 30 else "muito curta/invalida"
                    print(f"SUPABASE_KEY = {masked} (tamanho: {len(v)})")
                elif k == "PG_PASSWORD":
                    print(f"PG_PASSWORD = {v}")
                elif k == "LOCAL_BACKUP_DIR":
                    print(f"LOCAL_BACKUP_DIR = {v}")
                else:
                    print(f"{k} = {v}")
        
        print("\n=== Testando conexao com Supabase ===")
        if not url or not key:
            print("ERRO: URL ou KEY nao foram encontradas no .env!")
        else:
            supabase = create_client(url, key)
            res = supabase.table("empresas").select("id, nome").eq("status", "liberada").execute()
            print(f"Sucesso! Retornou {len(res.data)} empresas.")
            for emp in res.data[:3]:
                print(f" - ID: {emp['id']} | Nome: {emp['nome']}")
    except Exception as e:
        print(f"ERRO durante o teste: {e}")
