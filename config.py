# =============================================================================
# config.py — Configurações centrais do SpedGenerator
#
# Tudo configurável via .env — sem paths hardcoded de usuário.
# No servidor, basta editar .env e não precisa mexer neste arquivo.
# =============================================================================

import os
from dotenv import load_dotenv

load_dotenv()

# --- Supabase ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# --- Pasta de backups (rede ou local) ---
BACKUP_DIR = os.environ.get("BACKUP_DIR", r"C:\Backups_Novo")
DISABLE_REMOTE_BACKUP = os.environ.get("DISABLE_REMOTE_BACKUP", "False").lower() in ("true", "1", "yes")

# --- PostgreSQL local ---
PG_HOST     = os.environ.get("PG_HOST", "localhost")
PG_PORT     = int(os.environ.get("PG_PORT", "5432"))
PG_USER     = os.environ.get("PG_USER", "postgres")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "123")
PG_BIN_DIR  = os.environ.get("PG_BIN_DIR", r"C:\Program Files\PostgreSQL\15\bin")

# --- ACS Gerente (Gerente SPED) ---
ACS_EXE_PATH = os.environ.get("ACS_EXE_PATH", r"C:\ACSSoft\Sintese\Gerente SPED\gerente.exe")
ACS_INI_PATH = os.environ.get("ACS_INI_PATH", r"C:\ACSSoft\Sintese\Gerente SPED\acsgerente.ini")

# --- Pasta local para copiar backups antes de restaurar ---
LOCAL_BACKUP_DIR = os.environ.get("LOCAL_BACKUP_DIR", r"C:\SpedGenerator\Bancos")

# --- Pasta de exportação dos SPEDs ---
SPED_EXPORT_DIR = os.environ.get("SPED_EXPORT_DIR", r"C:\ACS_Exporta")

# --- Timeouts ---
SPED_TIMEOUT_SECONDS    = int(os.environ.get("SPED_TIMEOUT_SECONDS", "300"))
DELAY_BETWEEN_EMPRESAS  = int(os.environ.get("DELAY_BETWEEN_EMPRESAS", "10"))

# --- Daemon ---
DAEMON_INTERVAL_MINUTES = int(os.environ.get("DAEMON_INTERVAL_MINUTES", "5"))

# --- Backup remoto (pg_dump) ---
PG_DUMP_PARALLEL = int(os.environ.get("PG_DUMP_PARALLEL", "1"))
PG_DUMP_TIMEOUT  = int(os.environ.get("PG_DUMP_TIMEOUT", "5400"))  # 90 min

# --- Pipeline (ADD6) ---
# Workers de PREPARACAO (backup+restore+fix) rodando em paralelo no pipeline.
# O download (pg_dump) continua serial independente deste valor — ha trava
# global em backup_manager. Este valor paraleliza apenas restore/fixes.
# Manter baixo (2): restore pesa em disco e o ACS gera ao mesmo tempo.
PREP_WORKERS = int(os.environ.get("PREP_WORKERS", "2"))

# --- Abertura do ACS Gerente ---
# Timeout base para a janela de login aparecer. Bancos _local grandes
# (ex.: remigio 6 GB) deixam o Gerente legitimamente mais lento logo apos o
# restore; acs_automation escala este valor pelo tamanho do banco do ini
# (>=1.5 GB -> 90s, >=4 GB -> 150s) para nao matar sessao saudavel aos 45s.
ACS_ABRIR_TIMEOUT_S = int(os.environ.get("ACS_ABRIR_TIMEOUT_S", "45"))

# --- Compatibilidade NAT do ACS Gerente ---
# NAT que o gerente.exe instalado aceita (dialog "NAT compativel: N").
# Bancos vindos de clientes com Gerente mais novo tem linhas extras em
# 'atualizacoes' (NAT do banco = count dessa tabela) e o ACS recusa abrir.
# fix_nat_compatibilidade remove o excedente no banco _local.
# Ao ATUALIZAR o gerente.exe deste servidor, ajustar este valor no .env.
ACS_NAT_COMPATIVEL = int(os.environ.get("ACS_NAT_COMPATIVEL", "279"))

# --- Status Supabase ---
STATUS_LIBERADA    = "liberada"
STATUS_EM_PROCESSO = "em_processo"
STATUS_GERADA      = "gerada"
STATUS_ERRO        = "erro"

# --- Versoes ACS Gerente ---
import json as _json

ACS_VERSOES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "acs_versoes.json")


def carregar_versoes_acs() -> dict:
    """Carrega mapeamento de versoes ACS do JSON."""
    if not os.path.exists(ACS_VERSOES_FILE):
        return {"padrao": os.path.dirname(ACS_EXE_PATH)}
    try:
        with open(ACS_VERSOES_FILE, "r", encoding="utf-8") as f:
            dados = _json.load(f)
        dados.pop("_comentario", None)
        return dados
    except Exception:
        return {"padrao": os.path.dirname(ACS_EXE_PATH)}


def resolver_versao_acs(informacoes_sped: str | None) -> tuple[str, str, str]:
    """
    Detecta versao ACS a partir do campo informacoes_sped.
    Retorna (versao_nome, exe_path, ini_path).
    """
    versoes = carregar_versoes_acs()
    info = (informacoes_sped or "").lower()

    # Procura keyword de versao no campo informacoes_sped
    for chave, pasta in versoes.items():
        if chave == "padrao":
            continue
        if chave.lower() in info:
            exe = os.path.join(pasta, "gerente.exe")
            ini = os.path.join(pasta, "acsgerente.ini")
            if os.path.exists(exe):
                return (chave, exe, ini)

    # Fallback: versao padrao
    pasta_padrao = versoes.get("padrao", os.path.dirname(ACS_EXE_PATH))
    return ("padrao", os.path.join(pasta_padrao, "gerente.exe"),
            os.path.join(pasta_padrao, "acsgerente.ini"))
