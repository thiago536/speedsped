# =============================================================================
# progresso.py — Estado compartilhado entre main.py e painel.py
#
# main.py escreve progresso em C:\ACS_Exporta\progresso.json
# painel.py lê e exibe em tempo real
# =============================================================================

import json
import os
import logging
from datetime import datetime
from config import SPED_EXPORT_DIR

logger = logging.getLogger(__name__)

PROGRESSO_FILE = os.path.join(SPED_EXPORT_DIR, "progresso.json")


def _estado_vazio() -> dict:
    return {
        "ativo": False,
        "empresa_atual": "",
        "etapa": "",
        "indice_atual": 0,
        "total_empresas": 0,
        "inicio": "",
        "proxima": "",
        "concluidos": [],
        "erros": [],
        "ultima_atualizacao": "",
    }


def ler() -> dict:
    """Le estado atual do progresso. Retorna dict vazio se nao existe."""
    if not os.path.exists(PROGRESSO_FILE):
        return _estado_vazio()
    import time
    for tentativa in range(5):
        try:
            with open(PROGRESSO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (PermissionError, json.JSONDecodeError):
            time.sleep(0.05)
        except Exception:
            break
    return _estado_vazio()


def _salvar(estado: dict):
    """Salva estado do progresso (escrita atomica: tmp + rename com retries)."""
    estado["ultima_atualizacao"] = datetime.now().isoformat()
    os.makedirs(os.path.dirname(PROGRESSO_FILE), exist_ok=True)
    tmp = PROGRESSO_FILE + ".tmp"
    import time
    for tentativa in range(5):
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(estado, f, ensure_ascii=False, indent=2)
            os.replace(tmp, PROGRESSO_FILE)
            return
        except PermissionError:
            time.sleep(0.05)
    try:
        with open(PROGRESSO_FILE, "w", encoding="utf-8") as f:
            json.dump(estado, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Nao foi possivel salvar progresso.json apos retries: {e}")


def iniciar(total_empresas: int, nomes: list[str]):
    """Marca inicio de processamento."""
    estado = _estado_vazio()
    estado["ativo"] = True
    estado["total_empresas"] = total_empresas
    estado["inicio"] = datetime.now().isoformat()
    estado["proxima"] = nomes[0] if nomes else ""
    _salvar(estado)
    logger.debug(f"Progresso: iniciado com {total_empresas} empresa(s)")


def atualizar(indice: int, nome_empresa: str, etapa: str, proxima: str = ""):
    """Atualiza progresso atual."""
    estado = ler()
    estado["ativo"] = True
    estado["indice_atual"] = indice
    estado["empresa_atual"] = nome_empresa
    estado["etapa"] = etapa
    estado["proxima"] = proxima
    _salvar(estado)


def concluir_empresa(nome: str):
    """Marca empresa como concluida."""
    estado = ler()
    if nome not in estado.get("concluidos", []):
        estado.setdefault("concluidos", []).append(nome)
    _salvar(estado)


def erro_empresa(nome: str, motivo: str):
    """Marca empresa com erro."""
    estado = ler()
    estado.setdefault("erros", []).append(f"{nome}: {motivo}")
    _salvar(estado)


def finalizar(sucessos: int, falhas: int):
    """Marca fim de processamento."""
    estado = ler()
    estado["ativo"] = False
    estado["etapa"] = f"Finalizado: {sucessos} OK, {falhas} erros"
    estado["empresa_atual"] = ""
    estado["proxima"] = ""
    estado["pipeline"] = {}
    _salvar(estado)


def atualizar_pipeline(pipeline: dict):
    """
    Atualiza estado do pipeline per-empresa.
    pipeline = {emp_id: {"nome": str, "etapa": str}, ...}
    Etapas: backup, restaurando, corrigindo, aguardando, gerando, concluido, erro
    """
    estado = ler()
    estado["pipeline"] = pipeline
    _salvar(estado)
