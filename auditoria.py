# =============================================================================
# auditoria.py — Timeline por empresa + arquivo de auditoria da origem dos dados
#
# ADD3: toda geração precisa de rastreabilidade (qual backup originou o SPED)
# e o diagnóstico precisa ser por empresa, não num log gigante.
#
#   evento(nome, categoria, msg)   → logs/empresas/{NOME}/timeline.jsonl
#   gravar_auditoria(pasta, dados) → AUDITORIA_GERACAO.txt junto dos SPEDs
#   ler_timeline(nome)             → consumido pelo monitor web
#
# REGRA: nenhuma função daqui pode quebrar o pipeline — tudo é best-effort.
# =============================================================================

import json
import os
import logging
from datetime import datetime, timezone

from config import SPED_EXPORT_DIR

logger = logging.getLogger(__name__)

LOGS_EMPRESAS_DIR = os.path.join(SPED_EXPORT_DIR, "logs", "empresas")
ARQUIVO_AUDITORIA = "AUDITORIA_GERACAO.txt"

# Nome amigável de cada step (mesmos rótulos do monitor web)
STEP_NOME = {
    "FISCAL": "Fiscal", "CONTRIB": "Contribuicoes",
    "INVENTARIO": "Fiscal com Inventario", "COMITENS": "Fiscal com Itens",
    "SEMITENS": "Fiscal sem Itens", "FISCAL_A": "Fiscal A", "FISCAL_B": "Fiscal B",
}

# Categorias de erro/evento (ADD3 — classificação)
# BACKUP | RESTORE | ACS | GERACAO | ARQUIVOS | SISTEMA | RECUPERACAO | INFO


def _sanitizar(nome: str) -> str:
    for c in r'\/:*?"<>|':
        nome = nome.replace(c, "_")
    return nome.strip() or "_sem_nome"


def _arquivo_timeline(nome_empresa: str) -> str:
    pasta = os.path.join(LOGS_EMPRESAS_DIR, _sanitizar(nome_empresa))
    os.makedirs(pasta, exist_ok=True)
    return os.path.join(pasta, "timeline.jsonl")


def evento(nome_empresa: str, categoria: str, msg: str, nivel: str = "info"):
    """Registra um evento na timeline da empresa. Nunca levanta exceção."""
    try:
        caminho = _arquivo_timeline(nome_empresa)
        linha = json.dumps({
            "ts": datetime.now().isoformat(timespec="seconds"),
            "categoria": categoria,
            "nivel": nivel,
            "msg": str(msg)[:300],
        }, ensure_ascii=False)
        with open(caminho, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
        # Rotação simples: mantém as últimas 600 linhas quando passa de 512 KB
        if os.path.getsize(caminho) > 512 * 1024:
            with open(caminho, "r", encoding="utf-8") as f:
                linhas = f.readlines()[-600:]
            with open(caminho, "w", encoding="utf-8") as f:
                f.writelines(linhas)
    except Exception:
        pass  # timeline jamais derruba o pipeline


def ler_timeline(nome_empresa: str, max_eventos: int = 150) -> list[dict]:
    """Últimos eventos da empresa (mais recentes por último)."""
    try:
        caminho = os.path.join(LOGS_EMPRESAS_DIR, _sanitizar(nome_empresa), "timeline.jsonl")
        if not os.path.exists(caminho):
            return []
        with open(caminho, "r", encoding="utf-8") as f:
            linhas = f.readlines()[-max_eventos:]
        eventos = []
        for ln in linhas:
            try:
                eventos.append(json.loads(ln))
            except Exception:
                continue
        return eventos
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Horário de restore por banco (preenchido pelo pipeline no mesmo processo)
# ---------------------------------------------------------------------------

_restores: dict[str, str] = {}


def marcar_restore(nome_db: str):
    _restores[nome_db.lower()] = datetime.now().isoformat(timespec="seconds")


def obter_restore(nome_db: str) -> str:
    return _restores.get(nome_db.lower(), "")


# ---------------------------------------------------------------------------
# Arquivo de auditoria (origem dos dados) — acompanha os SPEDs gerados
# ---------------------------------------------------------------------------

def gravar_auditoria(pasta_destino: str, dados: dict):
    """
    Grava AUDITORIA_GERACAO.txt na pasta final do posto.
    dados: empresa, base, cnpjs, data_liberacao, backup_arquivo, backup_data,
           backup_mb, restore, geracao, banco_local, arquivos, resultado.
    Nunca levanta exceção.
    """
    try:
        alerta = ""
        try:
            d_bk = dados.get("backup_data") or ""
            d_lib = dados.get("data_liberacao") or ""
            if d_bk and d_lib:
                dt_bk = datetime.fromisoformat(d_bk)
                dt_lib = datetime.fromisoformat(d_lib)
                # normaliza tz pra comparar (liberação vem do Supabase com tz)
                if dt_lib.tzinfo is not None:
                    dt_lib = dt_lib.astimezone().replace(tzinfo=None)
                if dt_bk.tzinfo is not None:
                    dt_bk = dt_bk.astimezone().replace(tzinfo=None)
                if dt_bk < dt_lib:
                    alerta = "DADOS_POTENCIALMENTE_ANTIGOS: backup ANTERIOR a data de liberacao!"
        except Exception:
            pass

        cnpjs = dados.get("cnpjs") or []
        arquivos = dados.get("arquivos") or []
        linhas = [
            "=" * 60,
            "AUDITORIA DE GERACAO — ORIGEM DOS DADOS",
            "=" * 60,
            f"Empresa:                {dados.get('empresa', '')}",
            f"Base:                   {dados.get('base', '')}",
            f"CNPJ(s):                {', '.join(str(c) for c in cnpjs) or '?'}",
            "",
            f"Data/Hora da Liberacao: {dados.get('data_liberacao', '') or '?'}",
            f"Backup Utilizado em:    {dados.get('backup_data', '') or '?'}",
            f"Arquivo Backup:         {dados.get('backup_arquivo', '') or '?'}",
            f"Tamanho do Backup:      {dados.get('backup_mb', '') or '?'} MB",
            f"Data/Hora do Restore:   {dados.get('restore', '') or '?'}",
            f"Data/Hora da Geracao:   {dados.get('geracao', '') or '?'}",
            f"Banco Local Utilizado:  {dados.get('banco_local', '') or '?'}",
            "",
            "Arquivos Gerados:",
        ]
        linhas += [f"  * {a}" for a in arquivos] or ["  (nenhum)"]
        linhas += ["", f"Resultado Final: {dados.get('resultado', 'SUCESSO')}"]
        if alerta:
            linhas += ["", "!" * 60, alerta, "!" * 60]
        linhas += ["", f"Gerado automaticamente pelo SpedGenerator em {datetime.now().isoformat(timespec='seconds')}"]

        os.makedirs(pasta_destino, exist_ok=True)
        caminho = os.path.join(pasta_destino, ARQUIVO_AUDITORIA)
        tmp = caminho + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("\n".join(linhas) + "\n")
        os.replace(tmp, caminho)
        logger.info(f"Auditoria gravada: {caminho}")
        if alerta:
            logger.warning(f"AUDITORIA: {alerta} ({dados.get('empresa')})")
    except Exception as e:
        logger.warning(f"Falha ao gravar auditoria (nao-fatal): {e}")
