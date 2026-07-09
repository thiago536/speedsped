import json
import os
import urllib.request
import urllib.error

# 1. POST comando valido (id fake — só prova o circuito; arquivo é removido no fim)
req = urllib.request.Request("http://localhost:8777/api/comando",
    data=json.dumps({"acao": "reprocessar", "params": {"empresa_id": 999999, "nome": "TESTE_WEB"}}).encode(),
    headers={"Content-Type": "application/json"}, method="POST")
res = json.load(urllib.request.urlopen(req))
print("POST:", res)
cmd_id = res["id"]

# 2. GET status do comando
st = json.load(urllib.request.urlopen(f"http://localhost:8777/api/comando/{cmd_id}"))
print("GET status:", st)

# 3. Acao proibida deve ser rejeitada
req2 = urllib.request.Request("http://localhost:8777/api/comando",
    data=json.dumps({"acao": "dropar", "params": {"banco": "x"}}).encode(),
    headers={"Content-Type": "application/json"}, method="POST")
try:
    urllib.request.urlopen(req2)
    print("FALHA: dropar deveria ser rejeitado")
except urllib.error.HTTPError as e:
    print("acao proibida rejeitada OK:", e.code, json.load(e))

# 4. tracking agora traz id e nome_base
j = json.load(urllib.request.urlopen("http://localhost:8777/api/status"))
t0 = j["tracking"]["ultimos"][0]
print("tracking item:", {k: t0[k] for k in ("id", "nome", "nome_base", "status")})

# 5. arquivo de comando existe na pasta que o daemon observa; remove (limpeza do teste)
path = rf"C:\ACS_Exporta\comandos\web_{cmd_id}.json"
print("arquivo de comando existe:", os.path.exists(path))
os.remove(path)
print("teste limpo")
