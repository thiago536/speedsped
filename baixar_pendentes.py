"""
baixar_pendentes.py — Baixa do servidor remoto os bancos com backup desatualizado.

Compara a data de liberacao de cada cliente no Supabase com a data
do arquivo .backup em disco. Se o arquivo for mais antigo, faz pg_dump.

Uso:
    python baixar_pendentes.py              # baixa apenas os atrasados
    python baixar_pendentes.py --forcar     # força todos, mesmo os atuais
    python baixar_pendentes.py --listar     # apenas lista, sem baixar
"""

import sys
import logging
import argparse
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def parse_args():
    p = argparse.ArgumentParser(description="Baixa backups pendentes do servidor remoto")
    p.add_argument("--forcar", action="store_true", help="Força download mesmo se atualizado")
    p.add_argument("--listar", action="store_true", help="Apenas lista pendentes, sem baixar")
    return p.parse_args()


def main():
    args = parse_args()

    logger.info("=" * 60)
    logger.info(f"Iniciando verificacao de backups — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    logger.info("=" * 60)

    from backup_manager import listar_desatualizados, atualizar_todos_desatualizados

    pendentes = listar_desatualizados()

    if not pendentes:
        logger.info("Todos os backups estao atualizados. Nada a fazer.")
        return 0

    logger.info(f"{len(pendentes)} banco(s) com backup desatualizado:")
    for p in pendentes:
        logger.info(f"  - {p['nome_base']} (liberado em {p['data_liberacao'][:10]})")

    if args.listar:
        logger.info("Modo --listar: nenhum download realizado.")
        return 0

    logger.info("-" * 60)
    logger.info("Iniciando downloads...")

    sucessos, falhas = atualizar_todos_desatualizados(forcar=args.forcar)

    logger.info("=" * 60)
    logger.info(f"Resultado: {sucessos} OK | {falhas} falha(s)")
    logger.info("=" * 60)

    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
