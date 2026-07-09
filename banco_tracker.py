# =============================================================================
# banco_tracker.py — Controle de bancos PostgreSQL restaurados
#
# Tracking local em C:\ACS_Exporta\bancos_ativos.json
# Bancos NÃO são dropados automaticamente após geração SPED.
# Drop automático só no último dia do mês, ou manual pelo painel.
# =============================================================================

import json
import os
import logging
import subprocess
from datetime import datetime, date
from calendar import monthrange
from config import SPED_EXPORT_DIR, PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_BIN_DIR

logger = logging.getLogger(__name__)

TRACKER_FILE = os.path.join(SPED_EXPORT_DIR, "bancos_ativos.json")

_pg_env = {**os.environ, "PGPASSWORD": PG_PASSWORD}


# =============================================================================
# Tracking JSON
# =============================================================================

def _carregar() -> dict:
    """Carrega tracking de bancos ativos. Retorna dict vazio se não existe."""
    if not os.path.exists(TRACKER_FILE):
        return {}
    try:
        with open(TRACKER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"JSON corrompido em {TRACKER_FILE}: {e} — resetando")
        return {}
    except Exception as e:
        logger.warning(f"Erro ao ler banco tracker: {e}")
        return {}


def _salvar(dados: dict):
    """Salva tracking de bancos ativos (escrita atomica: tmp + rename)."""
    os.makedirs(os.path.dirname(TRACKER_FILE), exist_ok=True)
    tmp = TRACKER_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    os.replace(tmp, TRACKER_FILE)


def registrar_banco(nome_db: str, nome_base: str, empresas: list[str] = None):
    """Registra banco como restaurado e ativo."""
    dados = _carregar()
    dados[nome_db] = {
        "nome_base": nome_base,
        "data_restauracao": datetime.now().isoformat(),
        "empresas": empresas or [],
        "status": "ativo",
        "protegido": False,
    }
    _salvar(dados)
    logger.info(f"Banco '{nome_db}' registrado como ativo")


def marcar_protegido(nome_db: str, protegido: bool = True):
    """Marca banco como protegido (não dropar no cleanup automático)."""
    dados = _carregar()
    if nome_db in dados:
        dados[nome_db]["protegido"] = protegido
        _salvar(dados)
        logger.info(f"Banco '{nome_db}' protegido={protegido}")


def remover_registro(nome_db: str):
    """Remove banco do tracking (após drop)."""
    dados = _carregar()
    if nome_db in dados:
        del dados[nome_db]
        _salvar(dados)
        logger.info(f"Banco '{nome_db}' removido do tracking")


def listar_bancos_ativos() -> dict:
    """Retorna todos bancos registrados como ativos."""
    return _carregar()


def banco_existe_no_pg(nome_db: str) -> bool:
    """Verifica se banco existe de fato no PostgreSQL."""
    psql = os.path.join(PG_BIN_DIR, "psql.exe")
    cmd = [
        psql, "-h", PG_HOST, "-p", str(PG_PORT), "-U", PG_USER,
        "-tAc", f"SELECT 1 FROM pg_database WHERE datname='{nome_db}'"
    ]
    try:
        result = subprocess.run(cmd, env=_pg_env, capture_output=True, text=True, timeout=10)
        return result.stdout.strip() == "1"
    except Exception:
        return False


def sincronizar_com_pg():
    """
    Sincroniza tracking com estado real do PostgreSQL.
    Remove do tracking bancos que já foram dropados externamente.
    Adiciona bancos *_local que existem no PG mas não no tracking.
    """
    dados = _carregar()
    alterado = False

    # Remove fantasmas (tracking diz ativo, PG não tem)
    for nome_db in list(dados.keys()):
        if not banco_existe_no_pg(nome_db):
            logger.warning(f"Banco '{nome_db}' não existe no PG — removendo do tracking")
            del dados[nome_db]
            alterado = True

    # Descobre bancos *_local no PG que não estão no tracking
    psql = os.path.join(PG_BIN_DIR, "psql.exe")
    cmd = [
        psql, "-h", PG_HOST, "-p", str(PG_PORT), "-U", PG_USER,
        "-tAc", "SELECT datname FROM pg_database WHERE datname LIKE '%_local' ORDER BY datname"
    ]
    try:
        result = subprocess.run(cmd, env=_pg_env, capture_output=True, text=True, timeout=10)
        bancos_pg = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
        for nome_db in bancos_pg:
            if nome_db not in dados:
                nome_base = nome_db.replace("_local", "")
                dados[nome_db] = {
                    "nome_base": nome_base,
                    "data_restauracao": datetime.now().isoformat(),
                    "empresas": [],
                    "status": "ativo",
                    "protegido": False,
                    "descoberto": True,
                }
                logger.info(f"Banco '{nome_db}' descoberto no PG — adicionado ao tracking")
                alterado = True
    except Exception as e:
        logger.warning(f"Erro ao listar bancos PG: {e}")

    if alterado:
        _salvar(dados)

    return dados


def tamanho_banco_mb(nome_db: str) -> float:
    """Retorna tamanho do banco em MB."""
    psql = os.path.join(PG_BIN_DIR, "psql.exe")
    cmd = [
        psql, "-h", PG_HOST, "-p", str(PG_PORT), "-U", PG_USER,
        "-tAc", f"SELECT pg_database_size('{nome_db}') / (1024*1024.0)"
    ]
    try:
        result = subprocess.run(cmd, env=_pg_env, capture_output=True, text=True, timeout=10)
        return round(float(result.stdout.strip()), 1)
    except Exception:
        return 0.0


# =============================================================================
# Drop controlado
# =============================================================================

def dropar_banco_controlado(nome_db: str, force: bool = False) -> bool:
    """
    Dropa banco e remove do tracking.
    Se protegido e force=False, recusa.
    """
    dados = _carregar()
    info = dados.get(nome_db, {})

    if info.get("protegido") and not force:
        logger.warning(f"Banco '{nome_db}' protegido — drop recusado (use force=True)")
        return False

    from postgres_manager import dropar_banco
    ok = dropar_banco(nome_db)
    if ok:
        remover_registro(nome_db)
    return ok


def eh_ultimo_dia_do_mes() -> bool:
    """Verifica se hoje é último dia do mês."""
    hoje = date.today()
    _, ultimo = monthrange(hoje.year, hoje.month)
    return hoje.day == ultimo


def cleanup_mensal() -> list[str]:
    """
    Drop automático de bancos não-protegidos.
    Só executa no último dia do mês.
    Retorna lista de bancos dropados.
    """
    if not eh_ultimo_dia_do_mes():
        logger.info("Cleanup mensal: não é último dia do mês — pulando")
        return []

    logger.info("Cleanup mensal: último dia do mês — iniciando limpeza")
    dados = sincronizar_com_pg()
    dropados = []

    for nome_db, info in list(dados.items()):
        if info.get("protegido"):
            logger.info(f"  PROTEGIDO: '{nome_db}' — mantido")
            continue

        if dropar_banco_controlado(nome_db, force=True):
            dropados.append(nome_db)
            logger.info(f"  DROPADO: '{nome_db}'")
        else:
            logger.warning(f"  FALHA ao dropar: '{nome_db}'")

    logger.info(f"Cleanup mensal: {len(dropados)} banco(s) dropado(s)")
    return dropados


# =============================================================================
# Info detalhada pra frontend
# =============================================================================

def info_completa_bancos() -> list[dict]:
    """
    Retorna lista detalhada de bancos pra exibir no frontend.
    Inclui tamanho, empresas, status, proteção.
    """
    dados = sincronizar_com_pg()
    resultado = []

    for nome_db, info in dados.items():
        tamanho = tamanho_banco_mb(nome_db)
        resultado.append({
            "nome_db": nome_db,
            "nome_base": info.get("nome_base", ""),
            "data_restauracao": info.get("data_restauracao", ""),
            "empresas": info.get("empresas", []),
            "status": info.get("status", "ativo"),
            "protegido": info.get("protegido", False),
            "tamanho_mb": tamanho,
        })

    resultado.sort(key=lambda x: x["nome_db"])
    return resultado
