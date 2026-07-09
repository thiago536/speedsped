# =============================================================================
# watcher.py — Loop contínuo que monitora Supabase por novos postos liberados
#
# Uso:
#   python watcher.py                  (intervalo padrão 30min)
#   python watcher.py --intervalo 60   (checa a cada 60 min)
#   python watcher.py --intervalo 5    (checa a cada 5 min, debug)
#
# Executa main.run() quando encontra pendentes.
# Respeita tracking local — não reprocessa já gerados.
# =============================================================================

import argparse
import logging
import sys
import time
from datetime import datetime

# Importa setup de logging do main (RotatingFileHandler etc)
import main

logger = logging.getLogger("watcher")


def watcher_loop(intervalo_min: int):
    """Loop infinito: checa Supabase → processa pendentes → dorme."""
    logger.info(f"Watcher iniciado — intervalo: {intervalo_min} min")

    while True:
        logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] Checando Supabase...")

        try:
            args = argparse.Namespace(
                posto=None,
                reprocessar=None,
                dry_run=False,
                limpar_tracking=None,
                status=False,
            )
            main.run(args)
        except Exception as e:
            logger.exception(f"Erro no ciclo do watcher: {e}")

        logger.info(f"Próxima checagem em {intervalo_min} min...")
        time.sleep(intervalo_min * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Watcher — monitora Supabase por novos liberados")
    parser.add_argument(
        "--intervalo", type=int, default=30,
        help="Intervalo entre checagens em minutos (padrão: 30)",
    )
    args = parser.parse_args()
    watcher_loop(args.intervalo)
