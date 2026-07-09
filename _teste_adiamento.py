# Teste da logica de adiamento (sem abrir o ACS de verdade):
# simula _executar_acs_tentativa levantando AcsNaoAbriuError e verifica que
# executar_acs_e_gerar_sped PROPAGA quando nada foi gerado.
from unittest.mock import patch
import acs_runner
from acs_runner import AcsNaoAbriuError, executar_acs_e_gerar_sped

# 1. ACS nunca abre, nada gerado → exceção propaga (main vai adiar)
with patch.object(acs_runner, "_executar_acs_tentativa",
                  side_effect=AcsNaoAbriuError("ACS nao abriu apos 12 tentativas")):
    try:
        executar_acs_e_gerar_sped("POSTO X")  # sem nome_base → não consulta banco
        raise SystemExit("FALHOU: deveria ter propagado AcsNaoAbriuError")
    except AcsNaoAbriuError:
        print("1. propaga AcsNaoAbriuError quando nada gerado: OK")

# 2. Constantes do retry de abertura
assert acs_runner.ACS_ABRIR_MAX_TENTATIVAS == 12
assert acs_runner.ACS_ABRIR_INTERVALO_S == 20
print("2. retry de abertura = 12x com 20s: OK")

# 3. central_service mapeia etapa 'adiada' → ADIADO
from central_service import _ETAPA_SITUACAO
assert _ETAPA_SITUACAO["adiada"] == "ADIADO"
print("3. situacao ADIADO no central_service: OK")

print("TODOS TESTES OK")
