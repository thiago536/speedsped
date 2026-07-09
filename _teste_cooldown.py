# Teste: 3+ tentativas NAO bloqueia mais o dia — vira cooldown de 60 min
from datetime import datetime, timedelta
import tracking

dados = tracking._carregar()
backup_orig = dict(dados)
try:
    # 5 tentativas, erro de 2h atras → cooldown 60min ja passou → deve TENTAR (False)
    dados["999991"] = {"nome": "_T1", "status": "erro", "tentativas": 5,
                       "data_geracao": (datetime.now() - timedelta(hours=2)).isoformat()}
    # 5 tentativas, erro de 10min atras → em cooldown → pula (True)
    dados["999992"] = {"nome": "_T2", "status": "erro", "tentativas": 5,
                       "data_geracao": (datetime.now() - timedelta(minutes=10)).isoformat()}
    # 2 tentativas, erro de 20min atras → cooldown 15min passou → tenta (False)
    dados["999993"] = {"nome": "_T3", "status": "erro", "tentativas": 2,
                       "data_geracao": (datetime.now() - timedelta(minutes=20)).isoformat()}
    tracking._salvar(dados)

    assert tracking.ja_gerado(999991) is False, "5 tent + 2h: deveria tentar de novo"
    assert tracking.ja_gerado(999992) is True,  "5 tent + 10min: deveria estar em cooldown"
    assert tracking.ja_gerado(999993) is False, "2 tent + 20min: deveria tentar de novo"
    print("COOLDOWN OK — sistema fica tentando o dia todo (15min ate 3 tent, 60min depois)")
finally:
    tracking._salvar(backup_orig)
    print("tracking restaurado")
