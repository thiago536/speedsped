import os
from supabase import create_client

env_path = r"C:\SpedGenerator\.env"
print(f"=== Corrigindo encoding do arquivo: {env_path} ===")

if not os.path.exists(env_path):
    print("ERRO: O arquivo C:\\SpedGenerator\\.env nao foi encontrado.")
else:
    try:
        # Ler o arquivo como bytes para identificar e remover o BOM
        with open(env_path, "rb") as f:
            raw_data = f.read()
        
        # UTF-8 BOM is b'\xef\xbb\xbf'
        if raw_data.startswith(b'\xef\xbb\xbf'):
            print("-> Detectado assinatura UTF-8 BOM. Removendo...")
            clean_data = raw_data[3:]
        else:
            print("-> Nenhuma assinatura BOM encontrada na leitura binaria, mas vamos limpar via string.")
            clean_data = raw_data
            
        # Decodificar e limpar espacos ou caracteres invisiveis no inicio/fim
        content_str = clean_data.decode("utf-8", errors="ignore")
        # Remove character u'\ufeff' se ainda persistir
        content_str = content_str.lstrip('\ufeff')
        
        # Salvar de volta em UTF-8 puro (sem BOM)
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content_str)
            
        print("-> Arquivo salvo com sucesso em UTF-8 puro (sem BOM)!")
        
        # Testar a conexao novamente apos a correcao
        print("\n=== Testando conexao apos a correcao ===")
        url = ""
        key = ""
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() == "SUPABASE_URL":
                        url = v.strip()
                    elif k.strip() == "SUPABASE_KEY":
                        key = v.strip()
        
        if url and key:
            supabase = create_client(url, key)
            res = supabase.table("empresas").select("id, nome").eq("status", "liberada").execute()
            print(f"Sucesso! Retornou {len(res.data)} empresas.")
            for emp in res.data[:3]:
                print(f" - ID: {emp['id']} | Nome: {emp['nome']}")
        else:
            print("ERRO: Nao foi possivel ler a URL ou a KEY apos a limpeza.")
            
    except Exception as e:
        print(f"ERRO ao corrigir: {e}")
