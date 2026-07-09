# Teste rapido ADD3: timeline + auditoria txt
import os, shutil, tempfile
import auditoria

NOME = "_TESTE_ADD3"

# 1. evento + ler_timeline
auditoria.evento(NOME, "BACKUP", "Backup validado: teste.backup (165 MB)")
auditoria.evento(NOME, "GERACAO", "Fiscal B nao gerado apos 2 tentativas", nivel="erro")
evs = auditoria.ler_timeline(NOME)
assert len(evs) == 2, evs
assert evs[1]["nivel"] == "erro" and evs[1]["categoria"] == "GERACAO", evs
print("timeline OK:", evs)

# 2. restore marker
auditoria.marcar_restore("teste_local")
assert auditoria.obter_restore("TESTE_LOCAL")
print("restore marker OK")

# 3. auditoria txt com alerta (backup ANTERIOR a liberacao)
tmp = tempfile.mkdtemp()
auditoria.gravar_auditoria(tmp, {
    "empresa": "POSTO TESTE", "base": "teste", "cnpjs": ["12345678000199"],
    "data_liberacao": "2026-06-10T08:31:12+00:00",
    "backup_data": "2026-06-09T07:00:00", "backup_arquivo": "teste.backup",
    "backup_mb": 165.0, "restore": "2026-06-10T08:33:10",
    "geracao": "2026-06-10T08:34:25", "banco_local": "teste_local",
    "arquivos": ["SPED_FISCAL_A.txt", "Contribuicoes.txt"], "resultado": "SUCESSO",
})
txt = open(os.path.join(tmp, "AUDITORIA_GERACAO.txt"), encoding="utf-8").read()
assert "DADOS_POTENCIALMENTE_ANTIGOS" in txt, txt
assert "POSTO TESTE" in txt and "165.0 MB" in txt
print("auditoria txt + alerta OK")

# 4. auditoria sem alerta (backup mais novo)
auditoria.gravar_auditoria(tmp, {
    "empresa": "POSTO TESTE", "base": "teste", "cnpjs": [],
    "data_liberacao": "2026-06-10T08:31:12+00:00",
    "backup_data": "2026-06-10T11:32:05",
    "arquivos": ["a.txt"], "resultado": "SUCESSO",
})
txt = open(os.path.join(tmp, "AUDITORIA_GERACAO.txt"), encoding="utf-8").read()
assert "DADOS_POTENCIALMENTE_ANTIGOS" not in txt
print("auditoria txt sem alerta OK")

# 5. central_service.ler_timeline_empresa
from central_service import ler_timeline_empresa
d = ler_timeline_empresa(NOME)
assert d["eventos"] and d["empresa"] == NOME
print("central_service OK")

# limpeza
shutil.rmtree(tmp, ignore_errors=True)
shutil.rmtree(os.path.join(auditoria.LOGS_EMPRESAS_DIR, NOME), ignore_errors=True)
print("TODOS TESTES OK")
