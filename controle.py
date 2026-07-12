# =============================================================================
# controle.py — Sinais de controle operacional do pipeline (ADD7)
#
# Estado compartilhado em C:\ACS_Exporta\controle.json:
#   "normal"  — pipeline roda normalmente
#   "pausado" — pipeline SEGURA no proximo checkpoint e espera retomar
#   "parar"   — pipeline ABORTA no proximo checkpoint; daemon fica ocioso
#               (continua vivo, mas nao processa) ate o operador retomar
#
# Quem escreve: command_processor (botoes Pausar/Retomar/Parar do monitor web).
# Quem le: main._run_pipeline (foreground e workers de preparacao),
#          acs_runner (loop de tentativas), run_daemon (inicio de ciclo).
#
# Os checkpoints ficam ENTRE etapas atomicas (nunca no meio de pg_dump,
# pg_restore ou de uma exportacao do ACS) — parar nunca corrompe dados.
# O handler de "parar" tambem mata o gerente.exe para derrubar automacao
# em andamento; arquivos incompletos sao descartados pela validacao 0000/9999.
# =============================================================================

import json
import os
import time
import logging
from datetime import datetime

from config import SPED_EXPORT_DIR

logger = logging.getLogger(__name__)

CONTROLE_FILE = os.path.join(SPED_EXPORT_DIR, "controle.json")

ESTADOS_VALIDOS = {"normal", "pausado", "parar"}

# Cache curto para nao bater no disco a cada iteracao de loop apertado
_cache = {"estado": "normal", "lido_em": 0.0}
_CACHE_TTL = 2.0


def obter_estado(ignorar_cache: bool = False) -> str:
    """Estado atual do controle ('normal' se arquivo ausente/corrompido)."""
    agora = time.time()
    if not ignorar_cache and agora - _cache["lido_em"] < _CACHE_TTL:
        return _cache["estado"]
    estado = "normal"
    try:
        with open(CONTROLE_FILE, "r", encoding="utf-8") as f:
            dado = json.load(f)
        if dado.get("estado") in ESTADOS_VALIDOS:
            estado = dado["estado"]
    except Exception:
        pass
    _cache["estado"] = estado
    _cache["lido_em"] = agora
    return estado


def definir_estado(estado: str, origem: str = "") -> bool:
    """Grava novo estado de controle (escrita atomica)."""
    if estado not in ESTADOS_VALIDOS:
        return False
    os.makedirs(SPED_EXPORT_DIR, exist_ok=True)
    tmp = CONTROLE_FILE + ".tmp"
    dado = {"estado": estado, "origem": origem,
            "alterado_em": datetime.now().isoformat()}
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(dado, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CONTROLE_FILE)
    except Exception as e:
        logger.error(f"Falha ao gravar controle.json: {e}")
        return False
    _cache["estado"] = estado
    _cache["lido_em"] = time.time()
    logger.warning(f"CONTROLE: estado -> '{estado}'" + (f" (origem: {origem})" if origem else ""))
    return True


def deve_parar() -> bool:
    return obter_estado() == "parar"


def aguardar_se_pausado(checkpoint: str = "") -> bool:
    """
    Bloqueia enquanto o estado for 'pausado'. Retorna:
      True  — pode continuar (normal, ou retomado apos pausa)
      False — deve abortar (estado virou 'parar')
    """
    import sys
    if "--daemon" not in sys.argv:
        return True
    estado = obter_estado()
    if estado == "parar":
        return False
    if estado != "pausado":
        return True

    logger.warning(f"CONTROLE: PAUSADO em '{checkpoint or 'checkpoint'}' — aguardando retomar...")
    while True:
        time.sleep(2)
        estado = obter_estado()
        if estado == "pausado":
            continue
        if estado == "parar":
            logger.warning(f"CONTROLE: PARAR recebido durante pausa em '{checkpoint}'")
            return False
        logger.info(f"CONTROLE: retomado em '{checkpoint or 'checkpoint'}'")
        return True
