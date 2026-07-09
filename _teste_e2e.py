import json
import time
import urllib.request

# 1. /api/empresas responde com a visao completa
d = json.load(urllib.request.urlopen("http://localhost:8777/api/empresas"))
print("empresas:", d["total"], "| atualizado:", d["atualizado"][:19])
sits = {}
for e in d["empresas"]:
    sits[e["situacao"]] = sits.get(e["situacao"], 0) + 1
print("situacoes:", sits)

# 2. comando reprocessar de ponta a ponta (id fake, daemon NOVO deve aceitar)
req = urllib.request.Request("http://localhost:8777/api/comando",
    data=json.dumps({"acao": "reprocessar", "params": {"empresa_id": 999999, "nome": "TESTE_E2E"}}).encode(),
    headers={"Content-Type": "application/json"}, method="POST")
res = json.load(urllib.request.urlopen(req))
cmd_id = res["id"]
st = {}
for _ in range(10):
    time.sleep(2)
    st = json.load(urllib.request.urlopen(f"http://localhost:8777/api/comando/{cmd_id}"))
    if st.get("status") in ("concluido", "erro"):
        break
print("reprocessar via daemon:", st)
assert st.get("status") == "concluido", f"esperava concluido: {st}"

# 3. gerar_parcial com combo invalido deve falhar com mensagem clara
req2 = urllib.request.Request("http://localhost:8777/api/comando",
    data=json.dumps({"acao": "gerar_parcial",
                     "params": {"empresa_id": 999999, "nome": "TESTE_E2E",
                                "steps": ["FISCAL", "INVENTARIO"]}}).encode(),
    headers={"Content-Type": "application/json"}, method="POST")
res2 = json.load(urllib.request.urlopen(req2))
st2 = {}
for _ in range(10):
    time.sleep(2)
    st2 = json.load(urllib.request.urlopen(f"http://localhost:8777/api/comando/{res2['id']}"))
    if st2.get("status") in ("concluido", "erro"):
        break
print("gerar_parcial combo invalido:", st2.get("status"), "-", st2.get("resultado", "")[:80])
assert st2.get("status") == "erro"

# limpeza: tira o id fake da prioridade
from tracking import remover_prioridade
remover_prioridade(999999)
print("E2E OK — daemon novo executando comandos da central")
