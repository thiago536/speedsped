# =============================================================================
# main.py -Orquestrador SpedGenerator
#
# Fluxo por empresa liberada:
#   1. Consulta Supabase → lista status='liberada' + armazenamento='Nuvem'
#   2. Localiza .backup na rede (valida data >= data_liberacao)
#   3. pg_restore → PostgreSQL local
#   4. Atualiza acsgerente.ini com dados do posto
#   5. Lança ACS Gerente + AHK scripts → gera arquivos SPED
#   6. Move arquivos → C:\ACS_Exporta\{nome_posto}\
#   7. Dropa banco local (limpeza)
#
# Supabase é somente leitura — status NÃO é alterado pelo sistema.
# Tracking local em C:\ACS_Exporta\gerados.json controla quais já foram gerados.
# =============================================================================

import argparse
import logging
import logging.handlers
import os
import sys
import time
from datetime import datetime, timezone

import psutil

from config import DELAY_BETWEEN_EMPRESAS, DAEMON_INTERVAL_MINUTES, SPED_EXPORT_DIR, resolver_versao_acs, PREP_WORKERS
from supabase_client import listar_empresas_liberadas
from backup_finder import encontrar_backup
from postgres_manager import (
    criar_e_restaurar, dropar_banco, fix_saldo_mes_inventario,
    fix_aberturas_medicao, consultar_cnpjs_empresa,
    fix_prestacao_update_alias, fix_controle_processos,
    fix_nat_compatibilidade
)
from banco_tracker import registrar_banco, cleanup_mensal
from ini_manager import atualizar_ini
from acs_runner import executar_acs_e_gerar_sped, detectar_modo_sped, AcsNaoAbriuError
from file_manager import organizar_sped_posto, salvar_screenshot_erro, obter_arquivos_validos_existentes
from tracking import (
    registrar_gerado, registrar_erro, ja_gerado, listar_gerados,
    _carregar, _salvar,
    adicionar_prioridade, remover_prioridade, ordenar_por_prioridade,
)
import progresso
import auditoria

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
LOG_FORMAT_DATE = "%H:%M:%S"

_file_handler = logging.handlers.RotatingFileHandler(
    "spedgenerator.log",
    maxBytes=5 * 1024 * 1024,  # 5 MB
    backupCount=3,
    encoding="utf-8",
)
_file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S"))

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_FORMAT_DATE))

logging.basicConfig(
    level=logging.INFO,
    handlers=[_console_handler, _file_handler],
)
logger = logging.getLogger("main")


# ---------------------------------------------------------------------------
# Lock de execução — impede 2 instâncias simultâneas
# ---------------------------------------------------------------------------

LOCK_FILE = os.path.join(SPED_EXPORT_DIR, "spedgenerator.lock")


def _pid_e_spedgenerator(pid: int) -> bool:
    """Verifica se PID pertence a processo Python (nosso daemon)."""
    try:
        proc = psutil.Process(pid)
        nome = proc.name().lower()
        return "python" in nome
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def adquirir_lock() -> bool:
    """Cria lock file com PID. Retorna False se outra instância roda."""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                pid_antigo = int(f.read().strip())
            if psutil.pid_exists(pid_antigo) and _pid_e_spedgenerator(pid_antigo):
                logger.error(f"Outra instância rodando (PID {pid_antigo}). Abortando.")
                return False
            else:
                logger.warning(f"Lock órfão encontrado (PID {pid_antigo} não é SpedGenerator). Removendo.")
        except (ValueError, OSError):
            logger.warning("Lock file corrompido. Removendo.")

    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
    return True


def liberar_lock():
    """Remove lock file."""
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Estado do daemon (lido pelo painel.py)
# ---------------------------------------------------------------------------

DAEMON_STATE_FILE = os.path.join(SPED_EXPORT_DIR, "daemon_state.json")


def _salvar_daemon_state(status: str, proximo_ciclo: str = "", ciclos: int = 0,
                          ultimo_resultado: str = ""):
    """Salva estado do daemon para painel.py ler (escrita atomica)."""
    import json
    estado = {
        "status": status,  # rodando | aguardando | parado
        "pid": os.getpid(),
        "proximo_ciclo": proximo_ciclo,
        "ciclos_completos": ciclos,
        "ultimo_resultado": ultimo_resultado,
        "ultima_atualizacao": datetime.now().isoformat(),
    }
    try:
        os.makedirs(os.path.dirname(DAEMON_STATE_FILE), exist_ok=True)
        tmp = DAEMON_STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(estado, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DAEMON_STATE_FILE)
    except Exception:
        pass


def ler_daemon_state() -> dict:
    """Le estado do daemon. Usado pelo painel.py."""
    import json
    if not os.path.exists(DAEMON_STATE_FILE):
        return {"status": "parado"}
    try:
        with open(DAEMON_STATE_FILE, "r", encoding="utf-8") as f:
            estado = json.load(f)
        # Verifica se PID ainda existe (daemon pode ter crashado)
        pid = estado.get("pid", 0)
        if pid and not psutil.pid_exists(pid):
            estado["status"] = "parado"
        return estado
    except Exception:
        return {"status": "parado"}


# ---------------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------------
# (a antiga processar_empresa() foi REMOVIDA em 2026-07: estava morta — sem
#  chamadores — e reutilizava banco _local existente, violando a regra de
#  restore sempre fresco. O fluxo real e o pipeline paralelo abaixo.)

def run(args=None):
    logger.info("SpedGenerator iniciado.")

    if not adquirir_lock():
        return

    if args is None:
        args = parse_args()

    try:
        _run_interno(args)
    finally:
        liberar_lock()


def _run_interno(args):
    # Cleanup mensal: dropa bancos não-protegidos no último dia do mês
    cleanup_mensal()

    status_filtro = "liberada"
    if args.posto:
        status_filtro = None
    empresas = listar_empresas_liberadas(status_filtro=status_filtro)
    if empresas is None:
        raise ConnectionError("Supabase inacessivel apos retries — ciclo abortado")

    # Solicitacoes MANUAIS (Reprocessar/Pipeline no painel): empresas na fila de
    # prioridade entram no ciclo MESMO que o status no Supabase nao seja
    # 'liberada' (ex.: em_processo). Pedido explicito do operador nao e ignorado.
    if status_filtro and not args.reprocessar:
        from tracking import _carregar_prioridade
        ids_prio = set(_carregar_prioridade())
        ids_atuais = {e["id"] for e in empresas}
        faltantes = ids_prio - ids_atuais
        if faltantes:
            todas = listar_empresas_liberadas(status_filtro=None) or []
            for e in todas:
                if e["id"] in faltantes:
                    if not e.get("data_liberacao"):
                        # Sem data de liberacao: exige backup fresco de agora (regra 1)
                        e["data_liberacao"] = datetime.now(timezone.utc).isoformat()
                    st = e.get("status", "?")
                    logger.info(f"Solicitacao MANUAL: '{e['nome']}' (status={st}) incluida no ciclo")
                    auditoria.evento(e["nome"], "INFO",
                                     f"Solicitacao manual via painel — processando apesar do status '{st}'")
                    empresas.append(e)

    if not empresas:
        logger.info("Nenhuma empresa liberada para processar.")
        return

    # --posto: filtrar por nome
    if args.posto:
        filtro = args.posto.lower()
        empresas = [e for e in empresas if filtro in e["nome"].lower()]
        if not empresas:
            logger.error(f"Nenhuma empresa encontrada com '{args.posto}'")
            return
        logger.info(f"Filtrado por '{args.posto}': {len(empresas)} empresa(s)")

    # --reprocessar: ignorar tracking, forçar reprocessamento por ID
    if args.reprocessar:
        empresas = [e for e in empresas if e["id"] == args.reprocessar]
        if not empresas:
            logger.error(f"Empresa id={args.reprocessar} não encontrada entre liberadas")
            return
        logger.info(f"Reprocessando id={args.reprocessar} (ignorando tracking)")
    else:
        # Filtra empresas já geradas (tracking local).
        # data_liberacao mais nova que o último registro = re-liberação → reprocessa.
        pendentes = [e for e in empresas
                     if not ja_gerado(e["id"], e.get("informacoes_sped"), e.get("data_liberacao"))]
        puladas = len(empresas) - len(pendentes)
        if puladas:
            logger.info(f"Pulando {puladas} empresa(s) já gerada(s) (tracking local)")
        if not pendentes:
            logger.info("Todas empresas liberadas já foram geradas.")
            return
        empresas = pendentes

    # Ordena por prioridade (fila local)
    empresas = ordenar_por_prioridade(empresas)

    logger.info(f"Total: {len(empresas)} empresa(s) pendente(s)")

    # --dry-run: mostra plano sem executar
    if args.dry_run:
        from backup_manager import backup_desatualizado as _backup_desatualizado, limpar_nome_base
        from mapping_config import deve_ignorar_base, obter_base_mapeada
        logger.info("=== DRY RUN — nenhuma ação será executada ===")
        for i, e in enumerate(empresas, 1):
            info = e.get("informacoes_sped") or "padrão"
            nb_orig = (e.get("nome_base") or "").strip()
            nb = limpar_nome_base(obter_base_mapeada(nb_orig))
            dl = e.get("data_liberacao")
            
            if deve_ignorar_base(nb_orig):
                dump_tag = " [IGNORADA LOCALMENTE]"
            else:
                precisa = False
                if nb and dl:
                    dl_dt = datetime.fromisoformat(dl) if isinstance(dl, str) else dl
                    if dl_dt.tzinfo is None:
                        dl_dt = dl_dt.replace(tzinfo=timezone.utc)
                    precisa = _backup_desatualizado(nb, dl_dt)
                dump_tag = " [PRECISA PG_DUMP]" if precisa else ""
                
            logger.info(f"  {i}. {e['nome']} | base={nb} (original={nb_orig}) | info={info}{dump_tag}")
        return

    _run_pipeline(empresas)


# ---------------------------------------------------------------------------
# Pipeline paralelo: prepara em background, gera SPED em foreground
# ---------------------------------------------------------------------------

def _run_pipeline(empresas: list[dict]):
    """
    Pipeline de processamento paralelo (ADD6):
      Background (PREP_WORKERS threads): download backup → copy local → pg_restore → fix banco
        (download serial via trava global; createdb/dropdb serial via _ddl_lock;
         apenas pg_restore/fixes de bancos DIFERENTES rodam em paralelo)
      Foreground (1 thread):  INI → ACS SPED → organizar → registrar

    Enquanto SPED A gera, backups B/C/D estao baixando e restaurando.
    """
    from concurrent.futures import ThreadPoolExecutor
    from threading import Lock
    import queue

    from backup_manager import limpar_nome_base
    from postgres_manager import db_existe

    total = len(empresas)
    nomes = [e["nome"] for e in empresas]
    progresso.iniciar(total, nomes)

    # --- Pipeline state ---
    _pipeline = {}           # emp_id -> {"nome": str, "etapa": str}
    _pipeline_lock = Lock()
    _db_locks = {}           # nome_db -> Lock (evita 2 restores do mesmo banco)
    _db_locks_lock = Lock()
    _restaurados_ciclo = set()  # nome_db ja restaurados do backup atual NESTE ciclo
    _restaurados_lock = Lock()
    _prep_errors = set()     # emp_ids que falharam na preparacao (nao chegaram na fila)
    _backup_meta = {}        # emp_id -> {arquivo, data, mb} (auditoria de origem)
    fila_prontas = queue.Queue()

    # Inicializa todas empresas como "pendente" no pipeline
    for e in empresas:
        _pipeline[str(e["id"])] = {"nome": e["nome"], "etapa": "pendente"}
    progresso.atualizar_pipeline(dict(_pipeline))

    def _set_etapa(emp_id, nome, etapa):
        with _pipeline_lock:
            _pipeline[str(emp_id)] = {"nome": nome, "etapa": etapa}
            progresso.atualizar_pipeline(dict(_pipeline))

    def _get_db_lock(nome_db):
        with _db_locks_lock:
            if nome_db not in _db_locks:
                _db_locks[nome_db] = Lock()
            return _db_locks[nome_db]

    # --- Background: preparar empresa (download + restore + fix) ---
    def _prep_error(emp_id, nome, motivo, categoria="SISTEMA"):
        """Registra erro de preparacao (backup/restore) — nao entrou na fila."""
        _prep_errors.add(str(emp_id))
        _set_etapa(emp_id, nome, "erro")
        auditoria.evento(nome, categoria, motivo, nivel="erro")
        registrar_erro(emp_id, nome, f"[{categoria}] {motivo}")

    def _preparar(empresa):
        emp_id = empresa["id"]
        nome = empresa["nome"]
        try:
            # CONTROLE (ADD7): checkpoint antes de iniciar a preparacao
            from controle import aguardar_se_pausado
            if not aguardar_se_pausado(f"preparacao de {nome}"):
                _set_etapa(emp_id, nome, "cancelado")
                logger.warning(f"Preparacao de '{nome}' CANCELADA pelo operador")
                _prep_errors.add(str(emp_id))  # contabiliza p/ o foreground encerrar
                return False

            nome_base = (empresa.get("nome_base") or "").strip()
            data_lib = empresa.get("data_liberacao")
            info_sped = empresa.get("informacoes_sped") or ""

            from mapping_config import deve_ignorar_base
            if deve_ignorar_base(nome_base):
                logger.warning(f"Base '{nome_base}' está configurada para ser IGNORADA localmente (Web/Sem backup). Pulando.")
                _prep_error(emp_id, nome, "Base ignorada localmente (Web/Sem backup)")
                return False

            if not nome_base or not data_lib:
                _prep_error(emp_id, nome, "nome_base ou data_liberacao vazio")
                return False

            nome_base = limpar_nome_base(nome_base)
            data_lib_dt = datetime.fromisoformat(data_lib) if isinstance(data_lib, str) else data_lib
            if data_lib_dt.tzinfo is None:
                data_lib_dt = data_lib_dt.replace(tzinfo=timezone.utc)

            # 0. Backup FORCADO (comando 'reprocessar' da web): baixa dump NOVO
            #    antes de tudo — reprocessar = dado atual da nuvem, nunca o mesmo
            #    .backup antigo em disco. Marca so e consumida se o dump der certo.
            from tracking import backup_forcado, desmarcar_backup_forcado
            if backup_forcado(emp_id):
                from mapping_config import obter_base_mapeada
                from backup_manager import executar_pg_dump
                base_dl = limpar_nome_base(obter_base_mapeada(nome_base))
                _set_etapa(emp_id, nome, "backup")
                logger.info(f"'{nome}': reprocessamento — baixando backup NOVO de '{base_dl}' (forcado)")
                auditoria.evento(nome, "BACKUP", "Reprocessamento: download de backup novo forcado")
                if executar_pg_dump(base_dl, forcar=True):
                    desmarcar_backup_forcado(emp_id)
                else:
                    _prep_error(emp_id, nome,
                                "Download forcado do backup falhou (reprocessamento exige dado novo)",
                                categoria="BACKUP")
                    return False

            # 1. Backup (download se necessario — pode demorar)
            _set_etapa(emp_id, nome, "backup")
            try:
                backup_path = encontrar_backup(nome_base, data_lib_dt)
            except Exception as e:
                logger.error(f"Erro backup '{nome}': {e}")
                _prep_error(emp_id, nome, f"Backup: {e}", categoria="BACKUP")
                return False

            if not backup_path:
                _prep_error(emp_id, nome, "Backup nao encontrado/desatualizado", categoria="BACKUP")
                return False

            # Auditoria de origem: registra qual backup vai originar este SPED
            try:
                _backup_meta[str(emp_id)] = {
                    "arquivo": os.path.basename(backup_path),
                    "data": datetime.fromtimestamp(os.path.getmtime(backup_path)).isoformat(timespec="seconds"),
                    "mb": round(os.path.getsize(backup_path) / 1048576, 1),
                }
                auditoria.evento(nome, "BACKUP",
                                 f"Backup validado: {os.path.basename(backup_path)} "
                                 f"({_backup_meta[str(emp_id)]['mb']} MB, {_backup_meta[str(emp_id)]['data']})")
            except OSError:
                pass

            # CONTROLE (ADD7): checkpoint entre backup e restore
            if not aguardar_se_pausado(f"restore de {nome}"):
                _set_etapa(emp_id, nome, "cancelado")
                logger.warning(f"Restore de '{nome}' CANCELADO pelo operador (backup ja baixado fica salvo)")
                _prep_errors.add(str(emp_id))
                return False

            # 2. Restore — SEMPRE restaura do backup atual para garantir dados frescos.
            #    So reutiliza se o MESMO banco ja foi restaurado NESTE ciclo (ex.: dois
            #    postos que compartilham a mesma base). criar_e_restaurar dropa e recria
            #    com seguranca quando o banco ja existe (evita reaproveitar dado velho).
            nome_db_local = f"{nome_base.lower()}_local"
            db_lock = _get_db_lock(nome_db_local)
            with db_lock:
                if nome_db_local in _restaurados_ciclo:
                    logger.info(f"Banco '{nome_db_local}' ja restaurado neste ciclo — reutilizando")
                else:
                    _set_etapa(emp_id, nome, "restaurando")
                    try:
                        if not criar_e_restaurar(nome_base, backup_path):
                            _prep_error(emp_id, nome, "Falha no pg_restore", categoria="RESTORE")
                            return False
                        registrar_banco(nome_db_local, nome_base)
                        auditoria.marcar_restore(nome_db_local)
                        auditoria.evento(nome, "RESTORE", f"Banco '{nome_db_local}' restaurado com sucesso")
                        with _restaurados_lock:
                            _restaurados_ciclo.add(nome_db_local)
                    except Exception as e:
                        logger.error(f"Erro restore '{nome}': {e}")
                        _prep_error(emp_id, nome, f"Restore: {e}", categoria="RESTORE")
                        return False

            # 3. Fixes no banco
            _set_etapa(emp_id, nome, "corrigindo")
            try:
                fix_nat_compatibilidade(nome_db_local)
                fix_saldo_mes_inventario(nome_db_local)
                fix_controle_processos(nome_db_local)
                fix_prestacao_update_alias(nome_db_local)
                modo, _ = detectar_modo_sped(info_sped, nome)
                if modo != "CONTRIBUICOES":
                    fix_aberturas_medicao(nome_db_local)
            except Exception as e:
                logger.warning(f"Fix banco '{nome}': {e} (continuando)")

            # Pronto pra SPED
            _set_etapa(emp_id, nome, "aguardando")
            fila_prontas.put(empresa)
            return True

        except Exception as e:
            logger.exception(f"Erro inesperado preparando '{nome}': {e}")
            _prep_error(emp_id, nome, f"Inesperado: {str(e)[:80]}")
            return False

    # --- Inicia background threads ---
    # PREP_WORKERS paraleliza restore/fixes; o download continua serial
    # (trava global no backup_manager) e createdb/dropdb tambem (_ddl_lock).
    workers = min(PREP_WORKERS, total)
    logger.info(f"Pipeline: {total} empresa(s) — preparando em background ({workers} threads)")
    executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="prep")
    futures = [executor.submit(_preparar, e) for e in empresas]

    # --- Foreground: gera SPED pra empresas prontas ---
    sucessos, falhas = 0, 0
    processadas = 0
    adiadas = []  # postos onde o ACS nao abriu (12 tentativas) — voltam DEPOIS dos demais

    while processadas < total:
        # CONTROLE (ADD7): checkpoint entre empresas — pausa segura aqui;
        # PARAR aborta o restante do ciclo (empresas ficam pendentes p/ depois)
        from controle import aguardar_se_pausado
        if not aguardar_se_pausado("fila de geracao"):
            logger.warning("PIPELINE ABORTADO pelo operador (PARAR) — "
                           "empresas restantes ficam pendentes ate 'retomar'")
            break

        # Conta erros de preparacao (backup/restore — nunca entraram na fila)
        n_prep_errors = len(_prep_errors)

        # Se todos terminaram (processadas no foreground + erros de prep), sai
        if processadas + n_prep_errors >= total:
            break

        # Pega proxima empresa pronta; adiadas so entram quando a fila esvaziou
        try:
            empresa = fila_prontas.get(timeout=5)
        except queue.Empty:
            # Checa se todos futures ja acabaram
            if all(f.done() for f in futures) and fila_prontas.empty():
                if adiadas:
                    empresa = adiadas.pop(0)
                    logger.info(f"Retornando ao posto ADIADO (ACS nao abriu antes): {empresa['nome']}")
                else:
                    break
            else:
                continue

        emp_id = empresa["id"]
        nome = empresa["nome"]
        nome_base = limpar_nome_base((empresa.get("nome_base") or "").strip())
        info_sped = empresa.get("informacoes_sped") or ""
        processadas += 1

        logger.info(f"\n[SPED {processadas}/{total}] {nome}")
        _set_etapa(emp_id, nome, "gerando")
        progresso.atualizar(processadas, nome, "Gerando SPED")

        try:
            # AUTO-RECUPERACAO (ADD3): banco local ausente NAO e erro fatal —
            # se sumiu entre a preparacao e a geracao, restaura de novo do backup.
            nome_db_local = f"{nome_base.lower()}_local"
            dl = empresa.get("data_liberacao")
            dl_dt = datetime.fromisoformat(dl) if isinstance(dl, str) else dl
            if dl_dt is not None and dl_dt.tzinfo is None:
                dl_dt = dl_dt.replace(tzinfo=timezone.utc)
            if not db_existe(nome_db_local):
                logger.warning(f"Banco '{nome_db_local}' nao encontrado — restore automatico")
                auditoria.evento(nome, "RECUPERACAO",
                                 f"Banco local '{nome_db_local}' nao encontrado. Restore automatico iniciado.")
                _set_etapa(emp_id, nome, "restaurando")
                bp = encontrar_backup(nome_base, dl_dt)
                if not bp or not criar_e_restaurar(nome_base, bp):
                    raise Exception("[RESTORE] Banco local ausente e o restore automatico falhou")
                registrar_banco(nome_db_local, nome_base)
                auditoria.marcar_restore(nome_db_local)
                auditoria.evento(nome, "RECUPERACAO", f"Banco '{nome_db_local}' restaurado com sucesso")
                _set_etapa(emp_id, nome, "gerando")

            # INI
            versao_nome, exe_path, ini_path = resolver_versao_acs(info_sped)
            if versao_nome != "padrao":
                logger.info(f"Versao ACS: '{versao_nome}' -> {exe_path}")

            if not atualizar_ini(nome_base, nome, ini_path=ini_path):
                raise Exception("[SISTEMA] Falha ao atualizar .ini")

            # CNPJs pra validação
            cnpjs = consultar_cnpjs_empresa(nome_db_local)

            # Obter arquivos validos ja existentes — mas NUNCA reaproveitar
            # arquivo mais ANTIGO que a liberacao vigente (re-liberacao/reprocesso:
            # arquivo velho geraria "sucesso" sem abrir o ACS — falso sucesso)
            existentes_validos = obter_arquivos_validos_existentes(nome, cnpjs_esperados=cnpjs)
            if dl_dt is not None and existentes_validos:
                frescos = {}
                for s, c in existentes_validos.items():
                    try:
                        mt = datetime.fromtimestamp(os.path.getmtime(c), tz=timezone.utc)
                    except OSError:
                        continue
                    if mt >= dl_dt:
                        frescos[s] = c
                    else:
                        logger.info(f"Arquivo existente IGNORADO (anterior a liberacao): {os.path.basename(c)}")
                existentes_validos = frescos
            steps_ja_gerados = set(existentes_validos.keys())
            if existentes_validos:
                logger.info(f"Arquivos validos ja existentes na pasta: {list(existentes_validos.values())} (passos: {steps_ja_gerados})")

            # Geracao PARCIAL solicitada pela central operacional (one-shot):
            # traduz steps solicitados para um modo ja existente + steps a pular.
            modo_override = None
            qtd_esperada_override = None
            from central_service import consumir_override_geracao, resolver_solicitacao
            ov = consumir_override_geracao(emp_id)
            if ov:
                res = resolver_solicitacao(set(ov.get("steps", [])), info_sped, nome)
                if res:
                    modo_override, steps_pular = res
                    solicitados = set(ov["steps"])
                    # steps solicitados SEMPRE geram de novo (mesmo se arquivo existe)
                    steps_ja_gerados = (steps_ja_gerados - solicitados) | (steps_pular - solicitados)
                    existentes_validos = {s: c for s, c in existentes_validos.items()
                                          if s not in solicitados}
                    qtd_esperada_override = len(solicitados | set(existentes_validos.keys()))
                    logger.info(f"Geracao PARCIAL: steps={sorted(solicitados)} -> modo='{modo_override or 'padrao'}' (pulando: {sorted(steps_pular)})")
                else:
                    logger.warning(f"Geracao parcial solicitada com combinacao nao suportada: {ov.get('steps')} — gerando fluxo completo")

            # SPED (com retry inteligente — salva parciais automaticamente)
            arquivos = []
            try:
                arquivos = executar_acs_e_gerar_sped(nome, nome_base=nome_base,
                                                      informacoes_sped=info_sped, exe_path=exe_path,
                                                      steps_ja_gerados=steps_ja_gerados,
                                                      modo_override=modo_override)
            except AcsNaoAbriuError:
                raise  # tratado abaixo: adia o posto (ou erro real no retorno final)
            except Exception as e:
                logger.error(f"Erro durante geracao SPED para '{nome}': {e}")
                if any(k in str(e).lower() for k in ["ncm", "invalido", "produto"]):
                    raise e
                # Prossegue para resgatar e salvar qualquer arquivo gerado ate o momento do erro!

            # Organizar (valida CNPJ + contagem + perfil + move pra pasta do posto)
            finais = organizar_sped_posto(nome, arquivos, cnpjs_esperados=cnpjs)

            # Merge com os arquivos ja existentes
            todos_finais = list(existentes_validos.values())
            for f in finais:
                if f not in todos_finais:
                    todos_finais.append(f)

            if not todos_finais:
                raise Exception("[GERACAO] Nenhum arquivo SPED valido gerado")

            # Checar completude (geracao parcial: conta so os steps solicitados)
            if qtd_esperada_override is not None:
                qtd_esperada = qtd_esperada_override
            else:
                _, qtd_esperada = detectar_modo_sped(info_sped, nome)
            parcial = len(todos_finais) < qtd_esperada

            # ADD3: esperados vs encontrados — nomeia exatamente o que faltou
            from acs_runner import _STEPS_POR_MODO, _extrair_sufixo
            if modo_override is not None:
                steps_esperados = set(ov.get("steps", [])) | set(existentes_validos.keys())
            else:
                _m, _ = detectar_modo_sped(info_sped, nome)
                steps_esperados = set(_STEPS_POR_MODO.get(_m, ["FISCAL", "CONTRIB"]))
            steps_obtidos = {s for s in (_extrair_sufixo(f) for f in todos_finais) if s}
            faltantes = steps_esperados - steps_obtidos
            nomes_faltantes = [auditoria.STEP_NOME.get(s, s) for s in sorted(faltantes)]

            # Registrar
            logger.info(f"Banco '{nome_db_local}' mantido ativo")

            if parcial:
                # Sucesso parcial com arquivos salvos — erro NOMEADO (qual arquivo faltou)
                if nomes_faltantes:
                    msg = f"[GERACAO] {', '.join(nomes_faltantes)} nao gerado(s) apos as tentativas ({len(todos_finais)}/{qtd_esperada} salvos)"
                else:
                    msg = f"[GERACAO] Sucesso parcial: {len(todos_finais)}/{qtd_esperada} arquivo(s) salvos"
                logger.warning(f"[OK PARCIAL] {nome} — {msg}")
                auditoria.evento(nome, "GERACAO", msg, nivel="erro")
                # Registra como erro parcial pra permitir reprocessamento ate gerar todos os arquivos esperados!
                registrar_erro(emp_id, nome, msg, todos_finais)
                falhas += 1
                _set_etapa(emp_id, nome, "erro")
                progresso.erro_empresa(nome, msg)
            else:
                # Sempre registra como gerado com sucesso se tiver gerado todos os arquivos esperados
                registrar_gerado(emp_id, nome, todos_finais)
                remover_prioridade(emp_id)
                sucessos += 1
                _set_etapa(emp_id, nome, "concluido")
                progresso.concluir_empresa(nome)
                logger.info(f"[OK] {nome} — {len(todos_finais)} arquivo(s) salvos com status OK")
                # AUDITORIA DE ORIGEM (ADD3): evidencia permanente junto dos SPEDs
                meta = _backup_meta.get(str(emp_id), {})
                auditoria.gravar_auditoria(os.path.dirname(todos_finais[0]), {
                    "empresa": nome,
                    "base": nome_base,
                    "cnpjs": cnpjs,
                    "data_liberacao": empresa.get("data_liberacao") or "",
                    "backup_arquivo": meta.get("arquivo", ""),
                    "backup_data": meta.get("data", ""),
                    "backup_mb": meta.get("mb", ""),
                    "restore": auditoria.obter_restore(nome_db_local),
                    "geracao": datetime.now().isoformat(timespec="seconds"),
                    "banco_local": nome_db_local,
                    "arquivos": [os.path.basename(f) for f in todos_finais],
                    "resultado": "SUCESSO",
                })
                auditoria.evento(nome, "INFO",
                                 f"Processamento concluido — {len(todos_finais)} arquivo(s), auditoria gravada")

        except AcsNaoAbriuError as e:
            if not empresa.get("_acs_adiada"):
                # 1a vez: ADIA o posto — os outros passam na frente; volta nele no final
                empresa["_acs_adiada"] = True
                adiadas.append(empresa)
                processadas -= 1  # nao conta como processada (vai voltar)
                _set_etapa(emp_id, nome, "adiada")
                msg = (f"ACS nao abriu apos 12 tentativas — posto ADIADO; "
                       f"o sistema processa os demais e volta neste no final do ciclo")
                logger.warning(f"[ADIADO] {nome}: {msg}")
                auditoria.evento(nome, "RECUPERACAO", msg)
                progresso.atualizar(processadas, nome, "Adiado (ACS nao abriu)")
            else:
                # Retorno final tambem nao abriu: agora sim e erro de verdade
                falhas += 1
                _set_etapa(emp_id, nome, "erro")
                msg = f"[ACS] {e} — mesmo no retorno final do ciclo"
                logger.error(f"Erro SPED '{nome}': {msg}")
                salvar_screenshot_erro(nome)
                auditoria.evento(nome, "ACS", msg, nivel="erro")
                registrar_erro(emp_id, nome, msg[:100])
                progresso.erro_empresa(nome, msg[:100])

        except Exception as e:
            falhas += 1
            _set_etapa(emp_id, nome, "erro")
            logger.exception(f"Erro SPED '{nome}': {e}")
            salvar_screenshot_erro(nome)
            msg_e = str(e)
            categoria = "SISTEMA"
            for cat in ("BACKUP", "RESTORE", "ACS", "GERACAO", "ARQUIVOS"):
                if f"[{cat}]" in msg_e:
                    categoria = cat
                    break
            auditoria.evento(nome, categoria, msg_e[:200], nivel="erro")
            registrar_erro(emp_id, nome, msg_e[:100])
            progresso.erro_empresa(nome, msg_e[:100])

        if processadas < total:
            time.sleep(DELAY_BETWEEN_EMPRESAS)

    # Espera background terminar
    executor.shutdown(wait=True)

    # Contagem final
    total_falhas = len(_prep_errors) + falhas  # prep errors + SPED errors
    total_ok = sucessos

    progresso.finalizar(total_ok, total_falhas)

    logger.info("=" * 60)
    logger.info(f"Pipeline: {total_ok} sucesso(s) | {total_falhas} falha(s)")
    logger.info(f"Arquivos em: C:\\ACS_Exporta\\")


# ---------------------------------------------------------------------------
# Modo daemon — loop contínuo 24h
# ---------------------------------------------------------------------------

MAX_ERROS_CONSECUTIVOS = 5


def run_daemon(args):
    """Loop infinito: consulta Supabase a cada N minutos, processa pendentes."""
    logger.info("=" * 60)
    logger.info(f"SpedGenerator DAEMON iniciado (intervalo={DAEMON_INTERVAL_MINUTES}min)")
    logger.info("=" * 60)

    if not adquirir_lock():
        return

    # Inicia command processor (thread daemon para comandos do PainelSPED Electron)
    try:
        import command_processor
        command_processor.iniciar()
        logger.info("Command processor iniciado (PainelSPED remoto)")
    except Exception as e:
        logger.warning(f"Falha ao iniciar command processor: {e} — continuando sem ele")

    # Inicia watcher de backups: baixa automaticamente quando um cliente é liberado
    # com data_liberacao mais nova que o arquivo .backup em disco.
    import threading

    def _backup_watcher():
        from backup_manager import atualizar_todos_desatualizados
        while True:
            try:
                atualizar_todos_desatualizados()
            except Exception as e:
                logger.warning(f"[BackupWatcher] Erro: {e}")
            time.sleep(900)  # verifica a cada 15 minutos

    # BackupWatcher DESATIVADO: rodava dumps em paralelo com o pipeline; dumps
    # concorrentes no mesmo servidor falhavam (0 bytes) e o resultado vazio
    # sobrescrevia backups bons. O pipeline ja baixa o backup fresco sob demanda
    # (encontrar_backup com forcar=True) ao processar cada empresa liberada — serial,
    # 1 dump por vez, sem corrida.
    _ = _backup_watcher  # mantido para referencia; nao iniciado
    logger.info("BackupWatcher DESATIVADO — download sob demanda pelo pipeline (1 por vez, sem concorrencia)")

    ciclos = 0
    erros_consecutivos = 0

    try:
        while True:
            ciclos += 1

            # CONTROLE (ADD7): operador clicou PARAR — daemon fica ocioso
            # (vivo, respondendo comandos) ate o operador RETOMAR no monitor.
            from controle import obter_estado
            if obter_estado(ignorar_cache=True) == "parar":
                logger.warning(f"--- Ciclo #{ciclos}: PARADO pelo operador — aguardando 'retomar' ---")
                _salvar_daemon_state("parado_operador", ciclos=ciclos,
                                      ultimo_resultado="PARADO pelo operador (clique Retomar no monitor)")
                time.sleep(15)
                continue

            logger.info(f"\n--- Ciclo #{ciclos} ---")
            _salvar_daemon_state("rodando", ciclos=ciclos)

            # Fechamento mensal automatico (ADD5): dia 1º, uma vez por mes,
            # antes do pipeline (sistema ocioso). Nunca derruba o daemon.
            try:
                from fechamento import fechamento_automatico
                fechamento_automatico()
            except Exception as e:
                logger.warning(f"Fechamento automatico falhou (nao-fatal): {e}")

            resultado = ""
            try:
                _run_interno(args)
                resultado = "OK"
                erros_consecutivos = 0
            except Exception as e:
                erros_consecutivos += 1
                logger.exception(f"Erro no ciclo #{ciclos} ({erros_consecutivos}/{MAX_ERROS_CONSECUTIVOS}): {e}")
                resultado = f"Erro: {str(e)[:80]}"

                if erros_consecutivos >= MAX_ERROS_CONSECUTIVOS:
                    logger.critical(
                        f"DAEMON ENCERRADO: {MAX_ERROS_CONSECUTIVOS} erros consecutivos. "
                        f"Ultimo: {e}. Verifique conexao e configuracao."
                    )
                    _salvar_daemon_state("erro_fatal", ciclos=ciclos,
                                          ultimo_resultado=f"FATAL: {erros_consecutivos} erros consecutivos")
                    return
            # Decide o tempo de espera para o próximo ciclo
            tempo_espera_segundos = DAEMON_INTERVAL_MINUTES * 60
            
            try:
                empresas = listar_empresas_liberadas()
                if empresas:
                    # Filtra os postos pelo argumento se houver filtro
                    if args.posto:
                        filtro = args.posto.lower()
                        empresas = [e for e in empresas if filtro in e["nome"].lower()]
                    
                    tem_pendentes_ou_erros = False
                    for e in empresas:
                        if not ja_gerado(e["id"], e.get("informacoes_sped"), e.get("data_liberacao")):
                            tem_pendentes_ou_erros = True
                            break
                    
                    if tem_pendentes_ou_erros:
                        tempo_espera_segundos = 30  # Retry rápido em 30 segundos se houver pendências/erros!
                        logger.info("Existem empresas pendentes ou com erros. Próximo ciclo agendado para RETRY rápido em 30 segundos!")
            except Exception as e:
                logger.warning(f"Erro ao verificar se há empresas pendentes: {e}")

            # Calcula e exibe horário do próximo ciclo
            from datetime import datetime as dt, timedelta
            proximo = dt.now() + timedelta(seconds=tempo_espera_segundos)
            proximo_str = proximo.strftime("%H:%M:%S")

            logger.info(f"Ciclo #{ciclos} concluído. Próximo: {proximo_str}")
            _salvar_daemon_state("aguardando", proximo_ciclo=proximo_str,
                                  ciclos=ciclos, ultimo_resultado=resultado)

            time.sleep(tempo_espera_segundos)
    except KeyboardInterrupt:
        logger.info("Daemon interrompido por Ctrl+C")
    finally:
        _salvar_daemon_state("parado", ciclos=ciclos)
        liberar_lock()
        logger.info("Daemon encerrado.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cmd_limpar_tracking(args):
    """Remove empresa do tracking local (permite reprocessar)."""
    dados = _carregar()
    if args.limpar_tracking == "todos":
        dados.clear()
        _salvar(dados)
        logger.info("Tracking limpo completamente.")
    else:
        chave = args.limpar_tracking
        if chave in dados:
            nome = dados[chave].get("nome", "?")
            del dados[chave]
            _salvar(dados)
            logger.info(f"Removido do tracking: id={chave} ({nome})")
        else:
            logger.error(f"ID {chave} não encontrado no tracking.")


def _cmd_status(args):
    """Mostra status atual: liberadas no Supabase vs geradas localmente."""
    empresas = listar_empresas_liberadas()
    gerados = listar_gerados()

    print(f"\n{'ID':<6} {'NOME':<35} {'BASE':<15} {'STATUS LOCAL':<15}")
    print("-" * 75)
    for e in empresas:
        eid = str(e["id"])
        reg = gerados.get(eid)
        if reg and reg.get("status") == "erro":
            status = f"ERRO: {reg.get('motivo', '?')[:20]}"
        elif reg:
            status = f"GERADO {reg['data_geracao'][:10]}"
        else:
            status = "PENDENTE"
        print(f"{e['id']:<6} {e['nome']:<35} {e.get('nome_base',''):<15} {status}")
    print()


def parse_args():
    parser = argparse.ArgumentParser(
        description="SpedGenerator — Gerador automático de arquivos SPED",
    )
    parser.add_argument(
        "--posto", type=str, default=None,
        help="Processa apenas postos cujo nome contenha este texto",
    )
    parser.add_argument(
        "--reprocessar", type=int, default=None,
        help="Força reprocessamento de empresa por ID (ignora tracking)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Mostra plano de execução sem processar",
    )
    parser.add_argument(
        "--limpar-tracking", type=str, default=None, metavar="ID|todos",
        help="Remove empresa do tracking local (ID numérico ou 'todos')",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Mostra status de todas empresas liberadas",
    )
    parser.add_argument(
        "--priorizar", type=int, default=None, metavar="ID",
        help="Adiciona empresa ao topo da fila de prioridade",
    )
    parser.add_argument(
        "--daemon", action="store_true",
        help="Modo daemon: loop contínuo consultando Supabase a cada N minutos",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.status:
        _cmd_status(args)
    elif args.limpar_tracking:
        _cmd_limpar_tracking(args)
    elif args.priorizar:
        adicionar_prioridade(args.priorizar)
    elif args.daemon:
        run_daemon(args)
    else:
        run(args)
