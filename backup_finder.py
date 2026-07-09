# =============================================================================
# backup_finder.py — Localiza arquivo .backup e atualiza via pg_dump se preciso
#
# Se backup nao existe ou esta desatualizado (mtime < data_liberacao),
# auto_refresh=True faz pg_dump automatico do servidor remoto.
# =============================================================================

import os
import logging
from datetime import datetime, timezone
from config import BACKUP_DIR, DISABLE_REMOTE_BACKUP

logger = logging.getLogger(__name__)


def encontrar_backup(nome_base: str, data_liberacao: datetime,
                     auto_refresh: bool = True) -> str | None:
    """
    Procura '{nome_base}.backup' na pasta de backups.
    Valida que data de modificacao do arquivo >= data_liberacao.

    Se auto_refresh=True e backup desatualizado/inexistente,
    executa pg_dump automatico do servidor remoto.

    Retorna caminho completo se encontrado e valido, None caso contrario.
    """
    from mapping_config import obter_base_mapeada
    nome_base_real = obter_base_mapeada(nome_base)
    from backup_manager import limpar_nome_base
    nome_base_limpo = limpar_nome_base(nome_base_real)
    nome_base_lower = nome_base_limpo.lower()
    nome_arquivo = f"{nome_base_lower}.backup"
    caminho_backup = os.path.join(BACKUP_DIR, nome_arquivo)

    # Garante data_liberacao tem timezone
    if data_liberacao.tzinfo is None:
        data_liberacao = data_liberacao.replace(tzinfo=timezone.utc)

    # Verifica se backup existe e esta atualizado
    precisa_atualizar = False

    if not os.path.exists(caminho_backup):
        logger.warning(f"Backup nao encontrado: {caminho_backup}")
        precisa_atualizar = True
    else:
        tamanho = os.path.getsize(caminho_backup)
        if tamanho < 100:
            # Arquivo vazio/corrompido (ex.: dump que falhou) — NUNCA restaurar isso.
            logger.warning(
                f"Backup '{nome_arquivo}' invalido/vazio ({tamanho} bytes) — rebaixando do servidor"
            )
            precisa_atualizar = True
        else:
            mtime = os.path.getmtime(caminho_backup)
            data_backup = datetime.fromtimestamp(mtime, tz=timezone.utc)

            if data_backup < data_liberacao:
                logger.warning(
                    f"Backup '{nome_arquivo}' desatualizado: "
                    f"backup={data_backup.astimezone().strftime('%d/%m/%Y %H:%M')} < "
                    f"liberacao={data_liberacao.astimezone().strftime('%d/%m/%Y %H:%M')}"
                )
                precisa_atualizar = True
            else:
                logger.info(
                    f"Backup OK: '{caminho_backup}' "
                    f"(gerado {data_backup.astimezone().strftime('%d/%m/%Y %H:%M')} "
                    f">= liberacao {data_liberacao.astimezone().strftime('%d/%m/%Y %H:%M')})"
                )
                return caminho_backup

    # Auto-refresh via pg_dump
    if precisa_atualizar and auto_refresh:
        if DISABLE_REMOTE_BACKUP:
            logger.info(f"DISABLE_REMOTE_BACKUP ativo. Usando backup local existente: {caminho_backup}")
            if os.path.exists(caminho_backup):
                return caminho_backup
            else:
                logger.error(f"Backup nao encontrado localmente e download remoto desativado para '{nome_base}'")
                return None

        logger.info(f"Auto-refresh: baixando backup NOVO (forcado) do servidor para '{nome_base_limpo}'")
        try:
            from backup_manager import executar_pg_dump
            # forcar=True: SEMPRE rebaixa, mesmo que exista arquivo no disco.
            # O pg_dump so retorna True apos baixar com sucesso (codigo 0 + arquivo
            # valido + rename atomico), entao o arquivo resultante e sempre fresco.
            ok = executar_pg_dump(nome_base_limpo, forcar=True)
            if ok and os.path.exists(caminho_backup):
                mtime_novo = os.path.getmtime(caminho_backup)
                data_novo = datetime.fromtimestamp(mtime_novo, tz=timezone.utc)
                logger.info(
                    f"Backup NOVO baixado do servidor: {caminho_backup} "
                    f"(gerado agora: {data_novo.astimezone().strftime('%d/%m/%Y %H:%M')})"
                )
                return caminho_backup
            logger.error(
                f"pg_dump FALHOU para '{nome_base}' — SPED BLOQUEADO. "
                f"O sistema NAO gera com backup desatualizado."
            )
            return None
        except Exception as e:
            logger.error(
                f"Erro ao baixar backup de '{nome_base}': {e} — SPED BLOQUEADO. "
                f"O sistema NAO gera com backup desatualizado."
            )
            return None

    if precisa_atualizar:
        _listar_disponiveis()
        return None

    return caminho_backup


def _listar_disponiveis():
    """Loga backups disponiveis na pasta (ajuda debug)."""
    try:
        arquivos = [f for f in os.listdir(BACKUP_DIR) if f.endswith(".backup")]
        logger.info(f"Backups disponiveis em '{BACKUP_DIR}': {arquivos[:20]}")
    except Exception as e:
        logger.warning(f"Nao foi possivel listar pasta de backup: {e}")


def listar_todos_backups() -> list[str]:
    """Retorna lista de todos os nomes de backup disponiveis (sem extensao)."""
    try:
        return [
            os.path.splitext(f)[0]
            for f in os.listdir(BACKUP_DIR)
            if f.endswith(".backup")
        ]
    except Exception as e:
        logger.error(f"Erro ao listar backups: {e}")
        return []
