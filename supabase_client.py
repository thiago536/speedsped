# =============================================================================
# supabase_client.py — Consulta empresas liberadas no Supabase (somente leitura)
#
# Retry automatico com backoff exponencial pra resiliencia de rede.
# =============================================================================

import logging
import os
import time
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

_client: Client = None

# Sentinel: distingue "Supabase falhou" de "sem empresas"
_SUPABASE_FALHOU = None


def get_client() -> Client:
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL e SUPABASE_KEY devem estar configurados no .env")
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def _retry(fn, max_tentativas: int = 3, desc: str = "Supabase"):
    """Executa fn() com retry e backoff exponencial."""
    for tentativa in range(max_tentativas):
        try:
            return fn()
        except Exception as e:
            wait = (2 ** tentativa) * 10  # 10s, 20s, 40s
            if tentativa < max_tentativas - 1:
                logger.warning(f"{desc} falhou (tentativa {tentativa+1}/{max_tentativas}): {e} — retry em {wait}s")
                time.sleep(wait)
            else:
                logger.error(f"{desc} falhou apos {max_tentativas} tentativas: {e}")
                raise


def atualizar_status(empresa_id: int, novo_status: str) -> bool:
    """Atualiza status da empresa no Supabase (em_processo, gerada, erro)."""
    try:
        def _update():
            get_client().table("empresas").update(
                {"status": novo_status}
            ).eq("id", empresa_id).execute()
        _retry(_update, desc=f"atualizar_status({empresa_id})")
        logger.info(f"Status empresa {empresa_id} -> '{novo_status}'")
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar status empresa {empresa_id}: {e}")
        return False


def combinar_info_sped(informacoes_sped: str | None, anotacoes: str | None) -> str:
    """Junta informacoes_sped com as anotacoes do contador — o modo de geracao
    (ex.: 'Inventario', '3 Arquivos') as vezes so esta escrito nas anotacoes."""
    info = (informacoes_sped or "").strip()
    anot = " ".join((anotacoes or "").split())  # normaliza quebras de linha
    if not anot or anot.lower() in info.lower():
        return info
    if not info:
        return anot
    return f"{info} | {anot}"


def limpar_nome_para_busca(nome: str) -> str:
    import unicodedata
    import re
    if not nome:
        return ""
    nome = unicodedata.normalize("NFD", nome)
    nome = "".join(c for c in nome if unicodedata.category(c) != "Mn")
    nome = nome.lower()
    nome = re.sub(r"^(posto|auto\s+posto|conveniencia|transportadora|comercio|e\.leite\s+&\s+cia)\s+", "", nome)
    nome = re.sub(r"[^a-z0-9]", "", nome)
    return nome


def listar_empresas_liberadas(status_filtro: str | None = "liberada") -> list[dict] | None:
    """
    Retorna empresas com status=status_filtro que sao Nuvem.
    Se status_filtro for None, retorna de qualquer status.
    Nuvem = armazenamento='Nuvem' OU nome_base preenchido.
    Ordena por data_liberacao ASC (mais antigas primeiro).

    Retorna None se Supabase falhou (distinto de lista vazia = sem empresas).
    """
    try:
        def _query():
            q = (
                get_client()
                .table("empresas")
                .select("id, nome, nome_base, armazenamento, data_liberacao, informacoes_sped, anotacoes, status, cnpj")
            )
            if status_filtro:
                q = q.eq("status", status_filtro)
            return q.order("data_liberacao", desc=False).execute()
        response = _retry(_query, desc="listar_empresas_liberadas")
        todas = response.data or []

        # Tenta resolver nome_base faltante via bancos_nomes.json (fallback automatico)
        bancos_map = {}
        try:
            import json
            map_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bancos_nomes.json")
            if os.path.exists(map_path):
                with open(map_path, "r", encoding="utf-8") as f:
                    map_data = json.load(f)
                bancos_map = map_data.get("bancos", {})
        except Exception as e:
            logger.error(f"Erro ao carregar bancos_nomes.json para auto-resolucao: {e}")

        for e in todas:
            if not (e.get("nome_base") or "").strip():
                nome_alvo = limpar_nome_para_busca(e["nome"])
                # 1. Match exato
                if nome_alvo in bancos_map:
                    e["nome_base"] = bancos_map[nome_alvo].get("dbname")
                    logger.info(f"Auto-resolvido base para '{e['nome']}' -> '{e['nome_base']}' via match exato")
                else:
                    # 2. Match aproximado
                    sugerido = None
                    for bkey in bancos_map:
                        if nome_alvo in bkey or bkey in nome_alvo:
                            sugerido = bancos_map[bkey].get("dbname")
                            break
                        # Tenta remover 'boa'
                        nome_sem_boa = nome_alvo.replace("boa", "")
                        if nome_sem_boa in bkey or bkey in nome_sem_boa:
                            sugerido = bancos_map[bkey].get("dbname")
                            break
                    if sugerido:
                        e["nome_base"] = sugerido
                        logger.info(f"Auto-resolvido base aproximado para '{e['nome']}' -> '{e['nome_base']}'")

        # Nuvem: armazenamento diz 'nuvem' OU nome_base preenchido
        empresas = [
            e for e in todas
            if (e.get("armazenamento") or "").lower() == "nuvem"
            or (e.get("nome_base") or "").strip()
        ]
        # As anotacoes do contador valem como informacoes_sped (ex.: 'Inventario')
        for e in empresas:
            e["informacoes_sped"] = combinar_info_sped(e.get("informacoes_sped"), e.get("anotacoes"))
        logger.info(f"Empresas liberadas (Nuvem, status={status_filtro}): {len(empresas)}")
        for e in empresas:
            logger.info(f"  - {e['nome']} | base={e['nome_base']} | lib={e.get('data_liberacao','?')}")
        return empresas
    except Exception as e:
        logger.error(f"Supabase INACESSIVEL apos retries: {e}")
        return None
