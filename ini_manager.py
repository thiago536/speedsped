# =============================================================================
# ini_manager.py - Copia acsgerenteNV.ini como acsgerente.ini trocando Caminho
#
# Suporta multiplas versoes do ACS Gerente (padrao, DM, 659, etc).
# Cada versao tem sua pasta com gerente.exe + acsgerenteNV.ini template.
# =============================================================================

import re
import logging
import os
import shutil
from config import ACS_INI_PATH

logger = logging.getLogger(__name__)

# Template Nuvem (fonte) e destino (nome padrao que gerente.exe le)
INI_TEMPLATE = os.path.join(os.path.dirname(ACS_INI_PATH), "acsgerenteNV.ini")


def atualizar_ini(nome_base: str, razao_social: str, ini_path: str = None) -> bool:
    """
    Copia acsgerenteNV.ini como acsgerente.ini, trocando apenas Caminho=
    pelo nome do banco restaurado. Resto do arquivo fica intacto.

    ini_path: caminho do acsgerente.ini destino (se None, usa padrao config).
    """
    destino = ini_path or ACS_INI_PATH
    template = os.path.join(os.path.dirname(destino), "acsgerenteNV.ini")

    if not os.path.exists(template):
        logger.error(f"Template INI nao encontrado: {template}")
        return False

    try:
        with open(template, "r", encoding="utf-8-sig") as f:
            conteudo = f.read()

        nome_db = f"{nome_base.lower()}_local"
        conteudo = re.sub(r"(?m)^Caminho=.*$", f"Caminho={nome_db}", conteudo)

        with open(destino, "w", encoding="utf-8") as f:
            f.write(conteudo)

        logger.info(f".ini criado: {destino} -> Caminho={nome_db}")
        return True

    except Exception as e:
        logger.error(f"Erro ao criar .ini: {e}")
        return False


def restaurar_ini_original(ini_path: str = None):
    """Remove acsgerente.ini gerado (limpeza)."""
    destino = ini_path or ACS_INI_PATH
    if os.path.exists(destino):
        try:
            os.remove(destino)
            logger.info(f".ini removido: {destino}")
        except Exception as e:
            logger.warning(f"Erro ao remover .ini: {e}")
