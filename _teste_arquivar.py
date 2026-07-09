# Teste arquivar_speds_antigos com pasta de posto fake
import os, shutil
from config import SPED_EXPORT_DIR
from file_manager import arquivar_speds_antigos

POSTO = "_TESTE_ARQ"
pasta = os.path.join(SPED_EXPORT_DIR, POSTO)
os.makedirs(pasta, exist_ok=True)
try:
    for n in ["SPED_010526_310526_COMITENS_x.TXT", "SPED_010526_310526_SEMITENS_x.TXT",
              "Contribuicoes_010126_CONTRIB_x.TXT", "AUDITORIA_GERACAO.txt", "leia-me.txt"]:
        open(os.path.join(pasta, n), "w").write("x")

    # 1. parcial: arquiva so CONTRIB
    n = arquivar_speds_antigos(POSTO, {"CONTRIB"})
    assert n == 1, n
    restantes = [f for f in os.listdir(pasta) if f.lower().endswith(".txt")]
    assert not any("CONTRIB" in f.upper() and "AUDITORIA" not in f.upper() for f in restantes), restantes
    print("1. parcial (so CONTRIB) OK")

    # 2. total: arquiva COMITENS, SEMITENS e AUDITORIA; preserva leia-me.txt
    n = arquivar_speds_antigos(POSTO)
    assert n == 3, n
    restantes = [f for f in os.listdir(pasta) if os.path.isfile(os.path.join(pasta, f))]
    assert restantes == ["leia-me.txt"], restantes
    sub = os.path.join(pasta, "anteriores")
    total_arquivados = sum(len(fs) for _, _, fs in os.walk(sub))
    assert total_arquivados == 4, total_arquivados
    print("2. total OK (4 arquivados em 'anteriores', leia-me preservado)")

    # 3. nome vazio: nao faz nada (protecao da raiz)
    assert arquivar_speds_antigos("") == 0
    assert arquivar_speds_antigos("  ") == 0
    print("3. protecao nome vazio OK")

    print("TODOS TESTES OK")
finally:
    shutil.rmtree(pasta, ignore_errors=True)
