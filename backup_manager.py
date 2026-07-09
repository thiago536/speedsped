# =============================================================================
# backup_manager.py — Gerenciamento de backups via pg_dump remoto
#
# Features:
#   - Resolve nome correto do banco via bancos_nomes.json (case-sensitive PG)
#   - Limpa nome_base sujo ("3F V. 569" → "3F")
#   - pg_dump PARALELO com ThreadPoolExecutor (configuravel)
#   - Progresso em tempo real para painel.py
#   - Timeout 30 min por banco
#
# Uso standalone:
#   python backup_manager.py --listar
#   python backup_manager.py --banco Angicos
#   python backup_manager.py --todos
#   python backup_manager.py --todos --paralelo 4
# =============================================================================

import argparse
import json
import os
import re
import sys
import logging
import logging.handlers
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from threading import Lock, get_ident

from config import BACKUP_DIR, PG_BIN_DIR, SPED_EXPORT_DIR, PG_DUMP_PARALLEL as _CFG_PARALLEL, PG_DUMP_TIMEOUT as _CFG_TIMEOUT

logger = logging.getLogger(__name__)

# =============================================================================
# Arquivos de configuracao
# =============================================================================

SERVIDORES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "servidores.json")
BANCOS_NOMES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bancos_nomes.json")
PROGRESSO_BACKUP_FILE = os.path.join(SPED_EXPORT_DIR, "progresso_backup.json")

# Lock para escrita thread-safe no progresso
_progresso_lock = Lock()

# Default de workers paralelos (usa config.py)
PG_DUMP_PARALLEL = _CFG_PARALLEL
PG_DUMP_TIMEOUT = _CFG_TIMEOUT


# =============================================================================
# Limpeza de nome_base (Supabase pode ter lixo)
# =============================================================================

def limpar_nome_base(nome_base: str) -> str:
    """
    Remove versao/info extra do nome_base.
    Ex: '3F V. 569' -> '3F', 'redeserrabranca - V. 591' -> 'redeserrabranca'
    """
    if not nome_base:
        return nome_base
    # Remove padroes como " V. 569", " - V. 591", " v. 123"
    limpo = re.sub(r'\s*-?\s*[Vv]\.\s*\d+', '', nome_base).strip()
    return limpo or nome_base


# =============================================================================
# Resolucao de nome de banco (case correto para PostgreSQL)
# =============================================================================

_bancos_cache = None
_bancos_cache_mtime = None


def _carregar_bancos_nomes() -> dict:
    """Carrega mapeamento lowercase -> info do banco. Recarrega automaticamente se o arquivo mudar."""
    global _bancos_cache, _bancos_cache_mtime

    if not os.path.exists(BANCOS_NOMES_FILE):
        _bancos_cache = {}
        return _bancos_cache

    try:
        mtime_atual = os.path.getmtime(BANCOS_NOMES_FILE)
    except OSError:
        return _bancos_cache or {}

    if _bancos_cache is not None and mtime_atual == _bancos_cache_mtime:
        return _bancos_cache

    try:
        with open(BANCOS_NOMES_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)
        _bancos_cache = dados.get("bancos", {})
        _bancos_cache_mtime = mtime_atual
        logger.debug(f"bancos_nomes.json carregado: {len(_bancos_cache)} entradas")
    except Exception as e:
        logger.warning(f"Erro ao ler bancos_nomes.json: {e}")
        if _bancos_cache is None:
            _bancos_cache = {}
    return _bancos_cache


def resolver_nome_pg(nome_base: str) -> str:
    """
    Retorna nome case-correto do banco PostgreSQL.
    Consulta bancos_nomes.json, fallback pro nome_base original.
    """
    bancos = _carregar_bancos_nomes()
    chave = nome_base.lower()
    if chave in bancos:
        return bancos[chave]["dbname"]
    # Fallback: bancos remotos sao capitalizados (Saojosecuite, Saobenedito...).
    # O literal minusculo quase nunca existe no servidor (FATAL: ... does not exist),
    # entao capitaliza pela convencao (1a maiuscula). Siglas que fogem disso
    # (RDL, 3RB, DV...) ja estao mapeadas no bancos_nomes.json.
    return nome_base[:1].upper() + nome_base[1:].lower()


# =============================================================================
# Servidores remotos
# =============================================================================

def carregar_servidores() -> dict:
    """Carrega mapeamento de servidores remotos do JSON."""
    if not os.path.exists(SERVIDORES_FILE):
        logger.error(f"Arquivo de servidores nao encontrado: {SERVIDORES_FILE}")
        return {}
    try:
        with open(SERVIDORES_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)
        dados.pop("_comentario", None)
        return dados
    except Exception as e:
        logger.error(f"Erro ao ler servidores.json: {e}")
        return {}


def resolver_servidor(nome_base: str) -> dict:
    """
    Retorna credenciais do servidor remoto para nome_base.
    Usa bancos_nomes.json para host/password se disponivel,
    senao fallback pra servidores.json.
    """
    servidores = carregar_servidores()
    padrao_creds = servidores.get("padrao", {})

    # 1. Tenta bancos_nomes.json (extraido do bat, mais completo)
    bancos = _carregar_bancos_nomes()
    chave = nome_base.lower()

    if chave in bancos:
        info = bancos[chave]
        host = info.get("host", padrao_creds.get("host", ""))
        
        # Tenta achar password do host correspondente em servidores.json
        fallback_password = padrao_creds.get("password", "")
        for s_key, s_val in servidores.items():
            if s_val.get("host") == host and s_val.get("password"):
                fallback_password = s_val["password"]
                break
                
        password = info.get("password") or fallback_password

        return {
            "host": host,
            "port": info.get("port", 5432),
            "user": info.get("user", "postgres"),
            "password": password,
            "dbname": info["dbname"],
        }

    # 2. Fallback: servidores.json (padrao + overrides)
    if not servidores:
        raise ValueError(f"Servidor nao encontrado para '{nome_base}' em bancos_nomes.json ou servidores.json")

    creds = servidores.get(chave, padrao_creds).copy()
    if "dbname" not in creds:
        # Mesma convencao do resolver_nome_pg: capitaliza (bancos remotos sao
        # capitalizados); o literal minusculo nao existe no servidor.
        creds["dbname"] = nome_base[:1].upper() + nome_base[1:].lower()
    return creds


# =============================================================================
# Verificacao de freshness
# =============================================================================

def backup_desatualizado(nome_base: str, data_liberacao: datetime) -> bool:
    """
    Compara mtime do backup local com data_liberacao do Supabase.
    Retorna True se backup nao existe ou esta desatualizado.
    Windows e case-insensitive, entao Bomjesus.backup == bomjesus.backup.
    """
    nome_limpo = limpar_nome_base(nome_base)
    caminho = os.path.join(BACKUP_DIR, f"{nome_limpo.lower()}.backup")

    if not os.path.exists(caminho):
        return True

    # Arquivo vazio/corrompido (ex.: dump que falhou) conta como desatualizado
    if os.path.getsize(caminho) < 100:
        return True

    mtime = os.path.getmtime(caminho)
    data_backup = datetime.fromtimestamp(mtime, tz=timezone.utc)

    if data_liberacao.tzinfo is None:
        data_liberacao = data_liberacao.replace(tzinfo=timezone.utc)

    return data_backup < data_liberacao


def listar_desatualizados() -> list[dict]:
    """
    Consulta Supabase por todas empresas com nome_base preenchido.
    Retorna lista de dicts com nome_base limpo, deduplicado,
    para as que tem backup desatualizado ou inexistente.
    """
    from supabase_client import get_client

    try:
        resp = get_client().table("empresas").select(
            "nome, nome_base, data_liberacao"
        ).not_.is_("nome_base", "null").not_.is_("data_liberacao", "null").execute()
        todas = resp.data or []
    except Exception as e:
        logger.error(f"Erro ao consultar Supabase: {e}")
        return []

    # Deduplicar por nome_base limpo — pega data_liberacao mais recente
    por_base = {}
    for e in todas:
        nb_raw = (e.get("nome_base") or "").strip()
        dl = e.get("data_liberacao")
        if not nb_raw or not dl:
            continue

        nb = limpar_nome_base(nb_raw)

        if isinstance(dl, str):
            try:
                dl_dt = datetime.fromisoformat(dl)
                if dl_dt.tzinfo is None:
                    dl_dt = dl_dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        else:
            dl_dt = dl

        key = nb.lower()
        if key not in por_base or dl_dt > por_base[key]["data_lib_dt"]:
            por_base[key] = {
                "nome": e["nome"],
                "nome_base": nb,
                "nome_base_original": nb_raw,
                "data_liberacao": dl,
                "data_lib_dt": dl_dt,
            }

    # Filtrar desatualizados
    desatualizados = []
    for info in por_base.values():
        if backup_desatualizado(info["nome_base"], info["data_lib_dt"]):
            desatualizados.append(info)

    desatualizados.sort(key=lambda x: x["nome_base"].lower())
    return desatualizados


# =============================================================================
# Serializacao global de pg_dump — REGRA: um dump por vez contra o servidor.
# O servidor remoto recusa dumps concorrentes (resultado: backups de 0 byte).
# Dois niveis de trava:
#   - _dump_serial_lock: threads do MESMO processo (pipeline + command_processor)
#   - pg_dump.lock em BACKUP_DIR: PROCESSOS diferentes (daemon vs baixar_pendentes/CLI)
# =============================================================================

_dump_serial_lock = Lock()
DUMP_LOCK_FILE = os.path.join(BACKUP_DIR, "pg_dump.lock")
DUMP_LOCK_WAIT_TIMEOUT = PG_DUMP_TIMEOUT + 600  # espera no maximo a duracao de 1 dump


def _lock_dump_orfao(pid: int) -> bool:
    """Lock e orfao se o PID gravado nele nao existe mais."""
    if not pid:
        return True
    try:
        import psutil
        return not psutil.pid_exists(pid)
    except Exception:
        return False


def _adquirir_lock_dump(nome_banco: str) -> bool:
    """
    Trava inter-processos de pg_dump (arquivo com PID em BACKUP_DIR).
    Espera ate DUMP_LOCK_WAIT_TIMEOUT se outro processo estiver baixando.
    """
    inicio = time.time()
    avisou = False
    while True:
        try:
            fd = os.open(DUMP_LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        except FileExistsError:
            pass
        except OSError as e:
            logger.warning(f"Lock de pg_dump indisponivel ({e}) — prosseguindo sem trava inter-processos")
            return True

        pid = 0
        try:
            with open(DUMP_LOCK_FILE, "r") as f:
                pid = int(f.read().strip() or 0)
        except (OSError, ValueError):
            pid = 0

        if _lock_dump_orfao(pid):
            logger.warning(f"Lock de pg_dump orfao (PID {pid}) — removendo")
            try:
                os.remove(DUMP_LOCK_FILE)
            except OSError:
                pass
            continue

        if time.time() - inicio > DUMP_LOCK_WAIT_TIMEOUT:
            logger.error(
                f"Timeout esperando outro pg_dump (PID {pid}) terminar — "
                f"download de '{nome_banco}' adiado para o proximo ciclo"
            )
            return False

        if not avisou:
            logger.info(f"Outro pg_dump em andamento (PID {pid}) — '{nome_banco}' aguardando na fila")
            _atualizar_progresso_banco(nome_banco, "aguardando", 0)
            avisou = True
        time.sleep(10)


def _liberar_lock_dump():
    try:
        if os.path.exists(DUMP_LOCK_FILE):
            os.remove(DUMP_LOCK_FILE)
    except OSError:
        pass


# =============================================================================
# pg_dump (single)
# =============================================================================

def executar_pg_dump(nome_base: str, forcar: bool = False) -> bool:
    """
    Executa pg_dump do servidor remoto para C:\\Backups_Novo\\{nome_base}.backup.
    Resolve nome correto do banco via bancos_nomes.json.

    SERIALIZADO globalmente: um unico pg_dump por vez, mesmo com chamadas
    simultaneas do pipeline, do command_processor (painel) ou de outro processo.

    Timeout inteligente: se arquivo parou de crescer por 5 min, mata.
    Timeout absoluto: PG_DUMP_TIMEOUT (default 90 min).
    """
    nome_limpo = limpar_nome_base(nome_base)

    # Skip rapido se ja existe e nao forcar (nao precisa de trava)
    backup_file = os.path.join(BACKUP_DIR, f"{nome_limpo.lower()}.backup")
    if not forcar and os.path.exists(backup_file):
        tamanho = os.path.getsize(backup_file) / (1024 * 1024)
        if tamanho > 0.01:
            logger.info(f"Backup '{nome_limpo}' ja existe ({tamanho:.1f} MB) — pulando")
            return True

    # Trava de threads do mesmo processo
    if not _dump_serial_lock.acquire(blocking=False):
        logger.info(f"Outro pg_dump em andamento neste processo — '{nome_limpo}' aguardando na fila")
        _atualizar_progresso_banco(nome_limpo, "aguardando", 0)
        _dump_serial_lock.acquire()
    try:
        # Trava entre processos (daemon vs baixar_pendentes/CLI)
        if not _adquirir_lock_dump(nome_limpo):
            _atualizar_progresso_banco(nome_limpo, "erro", 0, "timeout aguardando outro pg_dump")
            return False
        try:
            return _executar_pg_dump_impl(nome_limpo, backup_file)
        finally:
            _liberar_lock_dump()
    finally:
        _dump_serial_lock.release()


def _executar_pg_dump_impl(nome_limpo: str, backup_file: str) -> bool:
    """Corpo do pg_dump. So roda com as travas de serializacao adquiridas."""
    creds = resolver_servidor(nome_limpo)

    # Temp UNICO por execucao: evita que dois dumps simultaneos do mesmo banco
    # escrevam/limpem o mesmo .tmp (corrida que gerava backups de 0 byte).
    backup_temp = backup_file + f".{os.getpid()}_{get_ident()}.tmp"

    os.makedirs(BACKUP_DIR, exist_ok=True)

    pg_dump = os.path.join(PG_BIN_DIR, "pg_dump.exe")
    if not os.path.exists(pg_dump):
        logger.error(f"pg_dump nao encontrado: {pg_dump}")
        return False

    cmd = [
        pg_dump,
        "-h", creds["host"],
        "-p", str(creds.get("port", 5432)),
        "-U", creds.get("user", "postgres"),
        "-F", "c",
        "-Z", "0",              # Sem compressão: muito mais rápido e leve no servidor remoto
        "-b",
        "-f", backup_temp,
        creds["dbname"],
    ]

    env = {**os.environ, "PGPASSWORD": creds["password"]}

    MAX_RETRIES = 2
    for tentativa in range(1, MAX_RETRIES + 1):
        if tentativa > 1:
            logger.warning(f"=== [RETRY BACKUP] Tentativa {tentativa}/{MAX_RETRIES} para '{nome_limpo}' ===")
            time.sleep(15)

        # Limpa .tmp orfao de execucao anterior
        _limpar_temp(backup_temp)

        # Verifica espaco em disco (minimo 500MB livre)
        if not _verificar_espaco_disco(BACKUP_DIR, 500):
            _atualizar_progresso_banco(nome_limpo, "erro", 0, "disco insuficiente")
            return False

        logger.info(f"pg_dump '{nome_limpo}' (Tentativa {tentativa}) de {creds['host']}:{creds.get('port', 5432)}/{creds['dbname']}...")
        _atualizar_progresso_banco(nome_limpo, f"executando (T.{tentativa})", 0)

        try:
            proc = subprocess.Popen(
                cmd, env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except Exception as e:
            logger.error(f"Erro ao iniciar pg_dump (tentativa {tentativa}): {e}")
            if tentativa == MAX_RETRIES:
                _atualizar_progresso_banco(nome_limpo, "erro", 0, str(e))
                return False
            continue

        inicio = time.time()
        ultimo_log = inicio
        ultimo_tamanho = 0
        ultimo_cresceu = inicio  # ultima vez que arquivo cresceu

        STALL_TIMEOUT = 300  # 5 min sem crescer = travou
        sucesso_tentativa = True

        while proc.poll() is None:
            time.sleep(10)
            agora = time.time()
            elapsed = int(agora - inicio)

            # Checa tamanho atual do .tmp
            try:
                tamanho_atual = os.path.getsize(backup_temp) if os.path.exists(backup_temp) else 0
            except OSError:
                tamanho_atual = 0
            tamanho_mb = tamanho_atual / (1024 * 1024)

            # Detecta crescimento
            if tamanho_atual > ultimo_tamanho:
                ultimo_cresceu = agora
                ultimo_tamanho = tamanho_atual

            # Timeout absoluto
            if elapsed > PG_DUMP_TIMEOUT:
                logger.error(f"pg_dump '{nome_limpo}' TIMEOUT ABSOLUTO na tentativa {tentativa} apos {elapsed}s ({tamanho_mb:.1f} MB)")
                proc.kill()
                proc.wait()
                sucesso_tentativa = False
                break

            # Timeout por inatividade (arquivo parou de crescer)
            tempo_parado = agora - ultimo_cresceu
            if tempo_parado > STALL_TIMEOUT and tamanho_atual > 0:
                logger.error(
                    f"pg_dump '{nome_limpo}' TRAVOU na tentativa {tentativa} — sem crescer por {int(tempo_parado)}s "
                    f"({tamanho_mb:.1f} MB). Matando."
                )
                proc.kill()
                proc.wait()
                sucesso_tentativa = False
                break

            # Log a cada 30s com tamanho
            if agora - ultimo_log >= 30:
                vel = tamanho_mb / (elapsed / 60) if elapsed > 10 else 0
                logger.info(
                    f"pg_dump '{nome_limpo}' (T.{tentativa}): {tamanho_mb:.1f} MB "
                    f"({elapsed}s, {vel:.1f} MB/min)"
                )
                _atualizar_progresso_banco(nome_limpo, f"executando (T.{tentativa})", elapsed,
                                            tamanho_mb=round(tamanho_mb, 1))
                ultimo_log = agora

        if not sucesso_tentativa:
            _limpar_temp(backup_temp)
            if tentativa == MAX_RETRIES:
                _atualizar_progresso_banco(nome_limpo, "erro", int(time.time() - inicio), "timeout/travou")
                return False
            continue

        elapsed = int(time.time() - inicio)
        _, stderr_bytes = proc.communicate()
        stderr_text = stderr_bytes.decode("utf-8", errors="replace")

        if proc.returncode != 0:
            logger.error(f"pg_dump '{nome_limpo}' FALHOU na tentativa {tentativa} ({elapsed}s, code={proc.returncode})")
            for line in stderr_text.strip().split("\n")[-5:]:
                logger.error(f"  stderr: {line}")
            _limpar_temp(backup_temp)
            if tentativa == MAX_RETRIES:
                _atualizar_progresso_banco(nome_limpo, "erro", elapsed, f"code={proc.returncode}")
                return False
            continue

        if not os.path.exists(backup_temp) or os.path.getsize(backup_temp) < 100:
            logger.error(f"pg_dump '{nome_limpo}' (tentativa {tentativa}): arquivo vazio")
            _limpar_temp(backup_temp)
            if tentativa == MAX_RETRIES:
                _atualizar_progresso_banco(nome_limpo, "erro", elapsed, "arquivo vazio")
                return False
            continue

        # Sucesso: substitui atomicamente. os.replace troca o arquivo de uma vez,
        # preservando o backup antigo ate o ultimo instante — um dump que falha
        # NUNCA destroi o backup bom existente.
        try:
            os.replace(backup_temp, backup_file)
        except OSError as e:
            logger.error(f"Erro ao substituir backup: {e}")
            _limpar_temp(backup_temp)
            if tentativa == MAX_RETRIES:
                _atualizar_progresso_banco(nome_limpo, "erro", elapsed, str(e))
                return False
            continue

        tamanho_mb = os.path.getsize(backup_file) / (1024 * 1024)
        vel = tamanho_mb / (elapsed / 60) if elapsed > 30 else 0
        logger.info(f"pg_dump '{nome_limpo}' OK ({elapsed}s, {tamanho_mb:.1f} MB, {vel:.1f} MB/min)")
        _atualizar_progresso_banco(nome_limpo, "concluido", elapsed)
        return True

    return False


def _limpar_temp(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def _verificar_espaco_disco(caminho: str, min_mb: int = 500) -> bool:
    """Verifica se disco tem espaco minimo livre (em MB)."""
    try:
        import shutil
        usage = shutil.disk_usage(caminho)
        livre_mb = usage.free / (1024 * 1024)
        if livre_mb < min_mb:
            logger.error(f"Disco insuficiente em {caminho}: {livre_mb:.0f}MB livre (minimo {min_mb}MB)")
            return False
        return True
    except Exception as e:
        logger.warning(f"Nao foi possivel verificar disco: {e}")
        return True  # Na duvida, continua


# =============================================================================
# pg_dump PARALELO
# =============================================================================

def atualizar_todos_desatualizados(forcar: bool = False,
                                    max_workers: int = None) -> tuple[int, int]:
    """
    Atualiza todos backups desatualizados em PARALELO.
    max_workers: quantos pg_dump simultaneos (default PG_DUMP_PARALLEL).
    Retorna (sucessos, falhas).
    """
    desatualizados = listar_desatualizados()

    if not desatualizados:
        logger.info("Todos backups estao atualizados")
        _atualizar_progresso_geral("ocioso")
        return (0, 0)

    workers = max_workers or PG_DUMP_PARALLEL
    total = len(desatualizados)
    logger.info(f"{total} backup(s) desatualizado(s) — {workers} paralelo(s)")

    nomes = [d["nome_base"] for d in desatualizados]
    _atualizar_progresso_geral("executando", executando=[], fila=nomes, total=total)

    sucessos = 0
    falhas = 0
    _counter_lock = Lock()

    def _dump_worker(info):
        nb = info["nome_base"]
        # Sempre força: listar_desatualizados() já confirmou que o arquivo está desatualizado
        return (nb, executar_pg_dump(nb, forcar=True))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_dump_worker, d): d for d in desatualizados}

        for future in as_completed(futures):
            nb, ok = future.result()
            with _counter_lock:
                if ok:
                    sucessos += 1
                else:
                    falhas += 1
                restantes = total - sucessos - falhas
                logger.info(f"Backup progress: {sucessos} OK | {falhas} erros | {restantes} restantes")
                _atualizar_progresso_geral(
                    "executando",
                    concluidos=sucessos,
                    erros=falhas,
                    total=total,
                )

    resultado = f"{sucessos} OK, {falhas} erros"
    _atualizar_progresso_geral("ocioso", resultado=resultado,
                                concluidos=sucessos, erros=falhas, total=total)
    logger.info(f"Backup refresh: {resultado}")
    return (sucessos, falhas)


# =============================================================================
# Progresso (lido pelo painel.py)
# =============================================================================

def _atualizar_progresso_banco(banco: str, status: str, elapsed: int, erro: str = "", tamanho_mb: float = 0):
    """Atualiza status de um banco especifico no progresso."""
    with _progresso_lock:
        estado = _ler_progresso_raw()
        bancos_status = estado.get("bancos", {})
        bancos_status[banco] = {
            "status": status,
            "elapsed": elapsed,
            "erro": erro,
            "tamanho_mb": tamanho_mb,
        }
        estado["bancos"] = bancos_status
        estado["ultima_atualizacao"] = datetime.now().isoformat()
        _salvar_progresso(estado)


def _atualizar_progresso_geral(status: str, executando: list = None,
                                fila: list = None, total: int = 0,
                                concluidos: int = 0, erros: int = 0,
                                resultado: str = ""):
    """Atualiza estado geral do backup manager."""
    with _progresso_lock:
        estado = _ler_progresso_raw()
        estado.update({
            "status": status,
            "total": total,
            "concluidos": concluidos,
            "erros": erros,
            "resultado": resultado,
            "ultima_atualizacao": datetime.now().isoformat(),
        })
        if fila is not None:
            estado["fila"] = fila
        if executando is not None:
            estado["executando"] = executando
        _salvar_progresso(estado)


def _ler_progresso_raw() -> dict:
    try:
        if os.path.exists(PROGRESSO_BACKUP_FILE):
            with open(PROGRESSO_BACKUP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"status": "ocioso", "bancos": {}}


def _salvar_progresso(estado: dict):
    try:
        os.makedirs(os.path.dirname(PROGRESSO_BACKUP_FILE), exist_ok=True)
        tmp = PROGRESSO_BACKUP_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(estado, f, ensure_ascii=False, indent=2)
        os.replace(tmp, PROGRESSO_BACKUP_FILE)
    except Exception:
        pass


def ler_progresso_backup() -> dict:
    """Le estado atual do progresso de backup. Usado pelo painel.py."""
    return _ler_progresso_raw()


# =============================================================================
# CLI
# =============================================================================

def _setup_logging():
    fmt = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.handlers.RotatingFileHandler(
                os.path.join(BACKUP_DIR, "backup_refresh.log"),
                maxBytes=5 * 1024 * 1024,
                backupCount=2,
                encoding="utf-8",
            ),
        ],
    )


def _cmd_listar():
    desatualizados = listar_desatualizados()
    if not desatualizados:
        print("\nTodos backups estao atualizados.")
        return

    print(f"\n{len(desatualizados)} backup(s) desatualizado(s):\n")
    print(f"{'NOME_BASE':<25} {'PG_NAME':<20} {'NOME':<30} {'BACKUP':<12}")
    print("-" * 90)

    for d in desatualizados:
        nb = d["nome_base"]
        pg_name = resolver_nome_pg(nb)
        nome = d["nome"][:28]

        caminho = os.path.join(BACKUP_DIR, f"{nb.lower()}.backup")
        if os.path.exists(caminho):
            mtime = datetime.fromtimestamp(os.path.getmtime(caminho), tz=timezone.utc)
            backup_data = mtime.strftime("%d/%m/%Y")
        else:
            backup_data = "NAO EXISTE"

        flag = " *" if nb != pg_name else ""
        print(f"{nb:<25} {pg_name:<20} {nome:<30} {backup_data:<12}{flag}")
    print()
    if any(d["nome_base"] != resolver_nome_pg(d["nome_base"]) for d in desatualizados):
        print("  * = nome corrigido por bancos_nomes.json\n")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Backup Manager — pg_dump paralelo de servidores remotos",
    )
    parser.add_argument("--listar", action="store_true",
                        help="Lista bancos com backup desatualizado")
    parser.add_argument("--banco", type=str, default=None,
                        help="Atualiza backup de banco especifico")
    parser.add_argument("--todos", action="store_true",
                        help="Atualiza todos desatualizados")
    parser.add_argument("--paralelo", type=int, default=None,
                        help=f"Numero de pg_dumps simultaneos (default {PG_DUMP_PARALLEL})")
    parser.add_argument("--forcar", action="store_true",
                        help="Forca atualizacao mesmo se atual")
    return parser.parse_args()


if __name__ == "__main__":
    os.makedirs(BACKUP_DIR, exist_ok=True)
    _setup_logging()

    args = parse_args()

    if args.listar:
        _cmd_listar()
    elif args.banco:
        ok = executar_pg_dump(args.banco, forcar=args.forcar)
        sys.exit(0 if ok else 1)
    elif args.todos:
        ok, falhas = atualizar_todos_desatualizados(
            forcar=args.forcar,
            max_workers=args.paralelo,
        )
        sys.exit(0 if falhas == 0 else 1)
    else:
        parse_args()
        print("\nUse --listar, --banco NOME ou --todos")
