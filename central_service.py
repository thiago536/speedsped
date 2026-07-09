# =============================================================================
# central_service.py — Camada de serviços da central operacional
#
# Consumida pelo monitor_web (HTML) e, futuramente, pelo painel Electron.
# NENHUMA regra de negócio fica na interface: aqui mora a visão consolidada
# das empresas e a resolução de gerações parciais. As AÇÕES continuam indo
# pela camada de comandos existente (C:\ACS_Exporta\comandos\ →
# command_processor dentro do daemon).
#
# Funções principais:
#   listar_empresas_completo()  — TODAS as empresas com situação calculada
#   resolver_solicitacao()      — steps solicitados → (modo ACS, steps a pular)
#   registrar_override_geracao() / consumir_override_geracao()
# =============================================================================

import json
import os
import logging
from datetime import datetime, timezone

from config import SPED_EXPORT_DIR, BACKUP_DIR

logger = logging.getLogger(__name__)

EMPRESAS_FILA_FILE = os.path.join(SPED_EXPORT_DIR, "empresas_fila.json")
BANCOS_INFO_FILE = os.path.join(SPED_EXPORT_DIR, "bancos_info.json")
GERADOS_FILE = os.path.join(SPED_EXPORT_DIR, "gerados.json")
PROGRESSO_FILE = os.path.join(SPED_EXPORT_DIR, "progresso.json")
OVERRIDE_FILE = os.path.join(SPED_EXPORT_DIR, "geracao_override.json")

# Steps que o acs_runner ja sabe gerar (ver _STEPS_POR_MODO em acs_runner.py)
STEPS_VALIDOS = {"FISCAL", "CONTRIB", "INVENTARIO", "COMITENS", "SEMITENS",
                 "FISCAL_A", "FISCAL_B"}

# Etapa do pipeline → situação exibida
_ETAPA_SITUACAO = {
    "pendente": "NA_FILA",
    "backup": "BAIXANDO_BACKUP",
    "restaurando": "RESTAURANDO",
    "corrigindo": "RESTAURANDO",
    "aguardando": "NA_FILA",
    "adiada": "ADIADO",       # ACS nao abriu (12 tentativas) — volta no fim do ciclo
    "gerando": "GERANDO",
    "concluido": "CONCLUIDO",
    "erro": "ERRO",
}


def _ler_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _salvar_json_atomico(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# =============================================================================
# Visão consolidada das empresas (Parte 1 do ADD2)
# =============================================================================

def listar_empresas_completo() -> dict:
    """
    Retorna TODAS as empresas conhecidas com dados operacionais:
    backup em disco (data/tamanho), banco local, tracking, situação calculada.
    Fontes: arquivos JSON exportados pelo daemon (sem tocar Supabase direto).
    """
    from backup_manager import limpar_nome_base
    from mapping_config import obter_base_mapeada, deve_ignorar_base
    from acs_runner import detectar_modo_sped, _STEPS_POR_MODO

    fila = _ler_json(EMPRESAS_FILA_FILE) or {}
    empresas = fila.get("empresas", [])
    gerados = _ler_json(GERADOS_FILE) or {}
    bancos_info = (_ler_json(BANCOS_INFO_FILE) or {}).get("bancos", {})
    progresso = _ler_json(PROGRESSO_FILE) or {}
    pipeline = progresso.get("pipeline", {}) if progresso.get("ativo") else {}
    overrides = _ler_json(OVERRIDE_FILE) or {}
    agora = datetime.now(timezone.utc)

    resultado = []
    for e in empresas:
        emp_id = e.get("id")
        nome = e.get("nome", "")
        nb_orig = (e.get("nome_base") or "").strip()
        status_supabase = e.get("status", "")
        data_lib = e.get("data_liberacao") or ""
        reg = gerados.get(str(emp_id)) or {}

        # Backup em disco
        backup_data = ""
        backup_mb = 0.0
        backup_desatualizado = None
        nb_limpo = ""
        if nb_orig:
            nb_limpo = limpar_nome_base(obter_base_mapeada(nb_orig))
            caminho = os.path.join(BACKUP_DIR, f"{nb_limpo.lower()}.backup")
            if os.path.exists(caminho):
                try:
                    mtime = os.path.getmtime(caminho)
                    backup_data = datetime.fromtimestamp(mtime).isoformat(timespec="minutes")
                    backup_mb = round(os.path.getsize(caminho) / (1024 * 1024), 1)
                    if data_lib:
                        dt_bk = datetime.fromtimestamp(mtime, tz=timezone.utc)
                        dt_lib = datetime.fromisoformat(data_lib)
                        if dt_lib.tzinfo is None:
                            dt_lib = dt_lib.replace(tzinfo=timezone.utc)
                        backup_desatualizado = dt_bk < dt_lib
                except OSError:
                    pass

        # Banco local restaurado
        nome_db = f"{nb_limpo.lower()}_local" if nb_limpo else ""
        banco_local = nome_db if nome_db and nome_db in bancos_info else ""

        # Situação calculada (prioridade: pipeline ativo > regras estáticas)
        etapa_pipeline = (pipeline.get(str(emp_id)) or {}).get("etapa", "")
        if nb_orig and deve_ignorar_base(nb_orig):
            situacao = "IGNORADO"
        elif etapa_pipeline and etapa_pipeline in _ETAPA_SITUACAO:
            situacao = _ETAPA_SITUACAO[etapa_pipeline]
        elif status_supabase != "liberada":
            situacao = "AGUARDANDO_LIBERACAO"
        elif not nb_orig or not data_lib:
            situacao = "BLOQUEADO"  # dados faltando no Supabase
        elif reg.get("status") == "erro":
            # FALHA_DEFINITIVA: o Gerente retornou erro de dados ou as tentativas
            # esgotaram — o sistema PAROU de tentar (destrave com Reprocessar).
            # ERRO transitorio: continua tentando (cooldown crescente no tracking).
            situacao = "FALHA_DEFINITIVA" if reg.get("definitivo") else "ERRO"
        elif reg and reg.get("arquivos"):
            situacao = "CONCLUIDO"
        elif not backup_data:
            situacao = "AGUARDANDO_BACKUP"
        elif backup_desatualizado:
            situacao = "BACKUP_DESATUALIZADO"
        else:
            situacao = "PENDENTE"

        resultado.append({
            "id": emp_id,
            "nome": nome,
            "nome_base": nb_orig,
            "nome_base_limpo": nb_limpo,
            "status_supabase": status_supabase,
            "informacoes_sped": e.get("informacoes_sped") or "",
            "data_liberacao": data_lib,
            "backup_data": backup_data,
            "backup_mb": backup_mb,
            "backup_desatualizado": backup_desatualizado,
            "banco_local": banco_local,
            "ultima_geracao": reg.get("data_geracao", "") if reg.get("status") != "erro" else "",
            "ultimo_erro": reg.get("motivo", "") if reg.get("status") == "erro" else "",
            "definitivo": bool(reg.get("definitivo")) if reg.get("status") == "erro" else False,
            "tentativas": reg.get("tentativas", 0),
            "arquivos_gerados": len(reg.get("arquivos") or []),
            "parcial_pendente": str(emp_id) in overrides,
            "situacao": situacao,
            # Arquivos que o fluxo completo geraria (mesma regra do acs_runner)
            "steps_previstos": _STEPS_POR_MODO.get(
                detectar_modo_sped(e.get("informacoes_sped"), nome)[0],
                ["FISCAL", "CONTRIB"]),
        })

    return {
        "empresas": resultado,
        "total": len(resultado),
        "atualizado": fila.get("ultima_atualizacao", ""),
    }


# =============================================================================
# Geração parcial (Parte 5 do ADD2)
# =============================================================================

def resolver_solicitacao(steps_solicitados: set[str], informacoes_sped: str | None,
                         nome_posto: str = "") -> tuple[str, set[str]] | None:
    """
    Traduz steps solicitados pela interface para um modo que o acs_runner JA
    conhece + steps a marcar como "ja gerados" (para o runner pular).

    Retorna (modo, steps_a_pular) ou None se a combinação não é suportada
    pelos fluxos existentes (não criamos automação nova).
    """
    from acs_runner import _STEPS_POR_MODO, detectar_modo_sped

    solicitados = {s.upper() for s in steps_solicitados} & STEPS_VALIDOS
    if not solicitados:
        return None

    modo_natural, _ = detectar_modo_sped(informacoes_sped, nome_posto)

    # Candidatos: modos cujos steps cobrem todos os solicitados
    candidatos = []
    for modo, steps in _STEPS_POR_MODO.items():
        steps_set = set(steps)
        if solicitados <= steps_set:
            extra = len(steps_set - solicitados)
            # Prefere o modo com MENOS steps extras (match exato vence);
            # empate decidido pelo modo natural da empresa
            prioridade = (extra, 0 if modo == modo_natural else 1, len(steps_set))
            candidatos.append((prioridade, modo, steps_set))

    if not candidatos:
        return None

    candidatos.sort(key=lambda c: c[0])
    _, modo, steps_set = candidatos[0]
    return (modo, steps_set - solicitados)


def registrar_override_geracao(empresa_id, steps: list[str], nome: str = "") -> bool:
    """Grava solicitação de geração parcial. Consumida pelo main na geração."""
    steps_norm = sorted({s.upper() for s in steps} & STEPS_VALIDOS)
    if not steps_norm:
        return False
    overrides = _ler_json(OVERRIDE_FILE) or {}
    overrides[str(empresa_id)] = {
        "steps": steps_norm,
        "nome": nome,
        "criado": datetime.now().isoformat(),
    }
    _salvar_json_atomico(OVERRIDE_FILE, overrides)
    logger.info(f"Override de geracao registrado: '{nome}' (id={empresa_id}) steps={steps_norm}")
    return True


def ler_timeline_empresa(nome: str, max_eventos: int = 150) -> dict:
    """Timeline de eventos da empresa (ADD3) — consumida pelo monitor web."""
    import auditoria
    return {"empresa": nome, "eventos": auditoria.ler_timeline(nome, max_eventos)}


def consumir_override_geracao(empresa_id) -> dict | None:
    """Lê e REMOVE a solicitação de geração parcial da empresa (one-shot)."""
    overrides = _ler_json(OVERRIDE_FILE) or {}
    ov = overrides.pop(str(empresa_id), None)
    if ov:
        _salvar_json_atomico(OVERRIDE_FILE, overrides)
    return ov
