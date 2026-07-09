# Teste do fechamento: simulacao real (somente leitura) + execucao em sandbox
import json, os, shutil, zipfile
from datetime import datetime, timedelta

# 1. SIMULACAO REAL — nao altera nada
from fechamento import simular_fechamento, listar_historico, PASTAS_RESERVADAS
sim = simular_fechamento()
r = sim["resumo"]
print(f"SIMULACAO {sim['mes']}: {r['empresas_arquivadas']} empresas, {r['speds_arquivados']} SPEDs, "
      f"{r['bancos_candidatos']} bancos, {r['espaco_total_gb']} GB | ocupado='{sim['ocupado']}'")
assert "Historico" in sim["zip_destino"]

# 2. EXECUCAO EM SANDBOX: redireciona SPED_EXPORT_DIR para pasta de teste
import fechamento
SANDBOX = r"C:\SpedGenerator\_sandbox_fech"
shutil.rmtree(SANDBOX, ignore_errors=True)
os.makedirs(os.path.join(SANDBOX, "POSTO VELHO"))
os.makedirs(os.path.join(SANDBOX, "POSTO ATIVO"))
os.makedirs(os.path.join(SANDBOX, "comandos"))
velho = (datetime.now() - timedelta(days=40)).timestamp()
# posto velho: arquivos do mes passado
for n in ["SPED_x_FISCAL.TXT", "AUDITORIA_GERACAO.txt"]:
    p = os.path.join(SANDBOX, "POSTO VELHO", n)
    open(p, "w").write("conteudo")
    os.utime(p, (velho, velho))
# posto ativo: arquivo de hoje (NAO pode ser arquivado)
open(os.path.join(SANDBOX, "POSTO ATIVO", "SPED_y_FISCAL.TXT"), "w").write("novo")
# arquivo em comandos (reservada — intocavel)
open(os.path.join(SANDBOX, "comandos", "cmd.json"), "w").write("{}")

fechamento.SPED_EXPORT_DIR = SANDBOX
fechamento.HISTORICO_DIR = os.path.join(SANDBOX, "Historico")
fechamento.HISTORICO_JSON = os.path.join(fechamento.HISTORICO_DIR, "fechamento_historico.json")

# bloqueia drop de bancos no teste (mock do banco_tracker via coleta)
_orig = fechamento._coletar
def _coletar_sem_bancos():
    c = _orig()
    c["bancos"] = []
    return c
fechamento._coletar = _coletar_sem_bancos
fechamento.sistema_ocupado = lambda: ""  # sandbox: ignora ocupacao real da maquina

rel = fechamento.executar_fechamento()
assert "erro" not in rel, rel
assert rel["empresas_arquivadas"] == 1, rel
assert not os.path.exists(os.path.join(SANDBOX, "POSTO VELHO")), "posto velho deveria ter sido removido"
assert os.path.exists(os.path.join(SANDBOX, "POSTO ATIVO", "SPED_y_FISCAL.TXT")), "posto ativo intocavel!"
assert os.path.exists(os.path.join(SANDBOX, "comandos", "cmd.json")), "pasta reservada intocavel!"
zips = [f for _, _, fs in os.walk(fechamento.HISTORICO_DIR) for f in fs if f.endswith(".zip")]
assert len(zips) == 1, zips
# zip contem os 2 arquivos do posto velho
zpath = [os.path.join(r2, f) for r2, _, fs in os.walk(fechamento.HISTORICO_DIR) for f in fs if f.endswith(".zip")][0]
with zipfile.ZipFile(zpath) as z:
    assert len(z.namelist()) == 2, z.namelist()
txts = [f for f in os.listdir(fechamento.HISTORICO_DIR) if f.startswith("FECHAMENTO_MENSAL")]
assert txts, "relatorio txt nao gerado"
print(f"EXECUCAO SANDBOX OK: zip={os.path.basename(zpath)}, relatorio={txts[0]}, "
      f"recuperado={rel['espaco_recuperado_gb']} GB")

# 3. marker impede re-execucao automatica
rel2 = fechamento.executar_fechamento(automatico=True)
assert "erro" in rel2 and "ja executado" in rel2["erro"], rel2
print("MARKER anti-repeticao OK")

shutil.rmtree(SANDBOX, ignore_errors=True)
print("TODOS TESTES OK")
