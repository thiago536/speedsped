import json
from datetime import datetime, timedelta, timezone

# ---- 1. resolver_solicitacao: combos mapeiam para modos existentes ----
from central_service import resolver_solicitacao

casos = [
    ({"FISCAL", "CONTRIB"}, "", "", ("", set())),
    ({"CONTRIB"}, "", "", ("CONTRIBUICOES", set())),
    ({"FISCAL"}, "", "", ("FISCAL", set())),
    ({"FISCAL_A"}, "Perfil A", "", ("FISCAL_A_ONLY", set())),
    ({"INVENTARIO", "CONTRIB"}, "Com Inventário", "", ("INVENTARIO", set())),
    ({"INVENTARIO"}, "Com Inventário", "", ("INVENTARIO", {"CONTRIB"})),
    ({"COMITENS", "SEMITENS"}, "", "", ("FISCAL_SEM_CONTRIB", set())),
    ({"COMITENS", "SEMITENS", "CONTRIB"}, "3 Arquivos", "", ("FISCAL_ITENS", set())),
    ({"FISCAL_A", "CONTRIB"}, "Perfil A", "", ("PERFIL_AB", {"FISCAL_B"})),
]
for solicitados, info, nome, esperado in casos:
    res = resolver_solicitacao(solicitados, info, nome)
    assert res is not None, f"sem resolucao para {solicitados}"
    assert res == esperado, f"{solicitados} -> {res}, esperado {esperado}"
print("1. resolver_solicitacao:", len(casos), "combos OK")

# combinacao impossivel (FISCAL simples + INVENTARIO nao coexistem em nenhum modo)
assert resolver_solicitacao({"FISCAL", "INVENTARIO"}, "", "") is None
assert resolver_solicitacao({"XYZ"}, "", "") is None
print("2. combos invalidos rejeitados OK")

# ---- 2. override registrar/consumir (one-shot) ----
from central_service import registrar_override_geracao, consumir_override_geracao
assert registrar_override_geracao(999999, ["contrib"], "TESTE")
ov = consumir_override_geracao(999999)
assert ov and ov["steps"] == ["CONTRIB"], ov
assert consumir_override_geracao(999999) is None  # ja consumido
print("3. override one-shot OK")

# ---- 3. ja_gerado: re-liberacao zera o bloqueio ----
import tracking
dados = tracking._carregar()
backup_original = dados.get("999999")
agora = datetime.now()
dados["999999"] = {
    "nome": "TESTE_RELIB", "status": "erro", "motivo": "teste",
    "tentativas": 3, "arquivos": [],
    "data_geracao": (agora - timedelta(hours=2)).isoformat(),
}
tracking._salvar(dados)
# 3 tentativas hoje, sem nova liberacao -> bloqueado (True = pular)
assert tracking.ja_gerado(999999) is True, "deveria estar bloqueado (3 tentativas)"
# liberacao ANTIGA (antes do erro) -> continua bloqueado
lib_antiga = (agora - timedelta(hours=5)).astimezone(timezone.utc).isoformat()
assert tracking.ja_gerado(999999, None, lib_antiga) is True, "liberacao antiga nao deveria destravar"
# liberacao NOVA (depois do erro) -> destrava e zera tracking
lib_nova = (agora - timedelta(minutes=10)).astimezone(timezone.utc).isoformat()
assert tracking.ja_gerado(999999, None, lib_nova) is False, "re-liberacao deveria destravar"
assert "999999" not in tracking._carregar(), "registro deveria ter sido zerado"
print("4. re-liberacao destrava e zera tentativas OK")

# ---- 4. listar_empresas_completo ----
from central_service import listar_empresas_completo
d = listar_empresas_completo()
assert d["total"] > 0
sits = {}
for e in d["empresas"]:
    sits[e["situacao"]] = sits.get(e["situacao"], 0) + 1
    for campo in ("id", "nome", "nome_base", "situacao", "backup_mb", "tentativas"):
        assert campo in e
print("5. listar_empresas_completo:", d["total"], "empresas | situacoes:", sits)

# ---- 5. acs_runner modo_override ----
from acs_runner import _STEPS_POR_MODO
import inspect, acs_runner
sig = inspect.signature(acs_runner.executar_acs_e_gerar_sped)
assert "modo_override" in sig.parameters
print("6. acs_runner aceita modo_override OK")

# ---- 6. handlers novos registrados ----
import command_processor as cp
for acao in ("reprocessar", "pipeline_completo", "gerar_parcial"):
    assert acao in cp._HANDLERS, f"handler '{acao}' ausente"
ok, msg = cp._handle_gerar_parcial({"empresa_id": 999999, "nome": "T", "steps": ["FISCAL", "INVENTARIO"]})
assert not ok and "nao suportada" in msg, msg
print("7. handlers registrados + validacao de combo OK")

# limpeza: remove override que gerar_parcial invalido nao criou, prioridade nao foi adicionada
from tracking import remover_prioridade
remover_prioridade(999999)
if backup_original is not None:
    dados = tracking._carregar(); dados["999999"] = backup_original; tracking._salvar(dados)
print("TODOS OS TESTES PASSARAM")
