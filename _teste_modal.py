import json
import urllib.request

d = json.load(urllib.request.urlopen("http://localhost:8777/api/empresas"))
assert d["total"] > 0

# Todas empresas devem trazer steps_previstos coerentes
exemplos = {}
for e in d["empresas"]:
    sp = e.get("steps_previstos")
    assert isinstance(sp, list) and sp, f"steps_previstos invalido: {e['nome']}"
    chave = e.get("informacoes_sped") or "(padrao)"
    if chave not in exemplos:
        exemplos[chave] = (e["nome"], sp)

print("steps_previstos por tipo de informacoes_sped:")
for info, (nome, sp) in sorted(exemplos.items())[:12]:
    print(f"  {info[:38]:<40} -> {sp}   ({nome[:30]})")

# HTML contem o modal de verificacao
html = urllib.request.urlopen("http://localhost:8777/").read().decode("utf-8")
for trecho in ("modal-bg", "confirmarLote", "STEP_LABEL", "Confirmar e executar"):
    assert trecho in html, f"faltando no HTML: {trecho}"
print("modal presente no HTML OK")
print("TESTE OK")
