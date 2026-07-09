import json
from supabase_client import listar_empresas_liberadas
from acs_runner import detectar_modo_sped

emps = listar_empresas_liberadas()
with open(r"C:\ACS_Exporta\gerados.json", encoding="utf-8") as f:
    ger = json.load(f)

print(f"{len(emps)} liberadas:")
for e in emps:
    modo, qtd = detectar_modo_sped(e.get("informacoes_sped") or "", e["nome"])
    t = ger.get(str(e["id"])) or {}
    status = t.get("status", "gerado" if t.get("nome") else "-sem registro-")
    print(f"- id={e['id']} {e['nome']}")
    print(f"    modo={modo} ({qtd} arquivos) | info_sped={e.get('informacoes_sped')!r}")
    print(f"    tracking: status={status} tentativas={t.get('tentativas', 0)} "
          f"ultima={t.get('data_geracao', '-')}")
    if t.get("motivo"):
        print(f"    motivo: {t['motivo'][:90]}")
