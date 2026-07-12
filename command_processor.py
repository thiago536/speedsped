# =============================================================================
# command_processor.py — Processador de comandos do PainelSPED (Electron)
#
# Thread daemon que monitora C:\ACS_Exporta\comandos\ por arquivos de comando
# escritos pelo frontend Electron. Processa acoes de banco de dados e backup.
#
# Comandos suportados:
#   travar       — protege banco de drop automatico
#   destravar    — remove protecao
#   dropar       — drop banco PostgreSQL
#   backup       — pg_dump de banco remoto
#   restaurar    — pg_restore de backup local
#   enfileirar   — adiciona empresa na fila manual do daemon
#   pipeline     — backup + restaurar + enfileirar
#   sincronizar  — forca sync bancos_info.json + empresas_fila.json
#
# Formato do arquivo de comando (JSON):
#   { "id": "uuid", "acao": "travar", "params": {"banco": "nome_db"},
#     "timestamp": "ISO", "status": "pendente", "origem": "PC-NAME" }
# =============================================================================

import json
import os
import logging
import threading
import time
from datetime import datetime

from config import SPED_EXPORT_DIR, BACKUP_DIR

logger = logging.getLogger(__name__)

COMANDOS_DIR = os.path.join(SPED_EXPORT_DIR, "comandos")
BANCOS_INFO_FILE = os.path.join(SPED_EXPORT_DIR, "bancos_info.json")
EMPRESAS_FILA_FILE = os.path.join(SPED_EXPORT_DIR, "empresas_fila.json")
FILA_MANUAL_FILE = os.path.join(SPED_EXPORT_DIR, "fila_manual.json")

# Intervalo de polling (segundos)
POLL_INTERVAL = 3
BANCOS_INFO_INTERVAL = 30
EMPRESAS_FILA_INTERVAL = 60  # atualiza lista empresas Supabase a cada 60s


# =============================================================================
# Helpers de leitura/escrita atomica
# =============================================================================

def _ler_json_safe(path: str) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _salvar_json_atomico(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # Retry no replace: leitores (monitor web/painel) abrem esses arquivos a cada
    # poucos segundos e podem bloquear o replace transitoriamente (WinError 5/32)
    for tentativa in range(5):
        try:
            os.replace(tmp, path)
            return
        except (PermissionError, OSError):
            time.sleep(0.1)
    os.replace(tmp, path)  # ultima tentativa: se falhar, propaga o erro real


# =============================================================================
# Exportar bancos_info.json para Electron
# =============================================================================

def exportar_bancos_info():
    try:
        from banco_tracker import sincronizar_com_pg, tamanho_banco_mb
        dados = sincronizar_com_pg()
        info = {}
        for nome_db, banco in dados.items():
            try:
                tam = tamanho_banco_mb(nome_db)
            except Exception:
                tam = 0.0
            info[nome_db] = {
                "nome_base": banco.get("nome_base", ""),
                "tamanho_mb": tam,
                "data_restauracao": banco.get("data_restauracao", ""),
                "protegido": banco.get("protegido", False),
                "status": banco.get("status", "ativo"),
                "empresas": banco.get("empresas", []),
            }
        _salvar_json_atomico(BANCOS_INFO_FILE, {
            "bancos": info,
            "total": len(info),
            "ultima_atualizacao": datetime.now().isoformat(),
        })
        return True
    except Exception as e:
        logger.error(f"Erro ao exportar bancos_info: {e}")
        return False


# =============================================================================
# Exportar empresas_fila.json (dados Supabase para Electron)
# =============================================================================

def exportar_empresas_fila():
    """Exporta lista de empresas do Supabase para Electron."""
    try:
        from supabase_client import get_client, combinar_info_sped
        from tracking import listar_gerados

        resp = get_client().table("empresas").select(
            "id, nome, nome_base, status, informacoes_sped, anotacoes, data_liberacao, "
            "responsavel_atual, cnpj, armazenamento, enviada, progresso, data_envio, "
            "data_conclusao, email_contador, updated_at, created_at"
        ).order("nome").execute()
        empresas = resp.data or []
        gerados = listar_gerados()

        # Enriquecer com info local
        resultado = []
        for e in empresas:
            eid = str(e["id"])
            reg = gerados.get(eid)
            resultado.append({
                "id": e["id"],
                "nome": e.get("nome", ""),
                "nome_base": e.get("nome_base", ""),
                "status": e.get("status", ""),
                "informacoes_sped": combinar_info_sped(e.get("informacoes_sped"), e.get("anotacoes")),
                "data_liberacao": e.get("data_liberacao", ""),
                "responsavel_atual": e.get("responsavel_atual") or "",
                "responsavel": e.get("responsavel_atual") or "",
                "cnpj": e.get("cnpj") or "",
                "armazenamento": e.get("armazenamento") or "",
                "enviada": bool(e.get("enviada")),
                "progresso": e.get("progresso") or "",
                "data_envio": e.get("data_envio") or "",
                "data_conclusao": e.get("data_conclusao") or "",
                "email_contador": e.get("email_contador") or "",
                "updated_at": e.get("updated_at") or "",
                "gerado_local": bool(reg),
                "data_geracao": reg.get("data_geracao", "") if reg else "",
                "erro_local": reg.get("status") == "erro" if reg else False,
            })

        # Ler fila manual pendente
        fila_manual = []
        if os.path.exists(FILA_MANUAL_FILE):
            try:
                fila_manual = json.loads(open(FILA_MANUAL_FILE, "r", encoding="utf-8").read())
            except Exception:
                fila_manual = []

        _salvar_json_atomico(EMPRESAS_FILA_FILE, {
            "empresas": resultado,
            "total": len(resultado),
            "fila_manual": fila_manual,
            "ultima_atualizacao": datetime.now().isoformat(),
        })
        return True
    except Exception as e:
        logger.error(f"Erro ao exportar empresas_fila: {e}")
        return False


# =============================================================================
# Handlers de comandos
# =============================================================================

def _handle_travar(params: dict) -> tuple[bool, str]:
    banco = params.get("banco", "")
    if not banco:
        return False, "Parametro 'banco' obrigatorio"
    from banco_tracker import marcar_protegido, listar_bancos_ativos
    if banco not in listar_bancos_ativos():
        return False, f"Banco '{banco}' nao encontrado"
    marcar_protegido(banco, True)
    logger.info(f"[CMD] Banco '{banco}' TRAVADO")
    return True, f"Banco '{banco}' travado"


def _handle_destravar(params: dict) -> tuple[bool, str]:
    banco = params.get("banco", "")
    if not banco:
        return False, "Parametro 'banco' obrigatorio"
    from banco_tracker import marcar_protegido, listar_bancos_ativos
    if banco not in listar_bancos_ativos():
        return False, f"Banco '{banco}' nao encontrado"
    marcar_protegido(banco, False)
    logger.info(f"[CMD] Banco '{banco}' DESTRAVADO")
    return True, f"Banco '{banco}' destravado"


def _handle_dropar(params: dict) -> tuple[bool, str]:
    banco = params.get("banco", "")
    if not banco:
        return False, "Parametro 'banco' obrigatorio"
    from banco_tracker import dropar_banco_controlado
    ok = dropar_banco_controlado(banco, force=True)
    if ok:
        logger.info(f"[CMD] Banco '{banco}' DROPADO")
        return True, f"Banco '{banco}' dropado"
    return False, f"Falha ao dropar '{banco}'"


def _handle_backup(params: dict) -> tuple[bool, str]:
    banco = params.get("banco", "")
    if not banco:
        return False, "Parametro 'banco' obrigatorio"
    forcar = params.get("forcar", False)
    try:
        from backup_manager import executar_pg_dump
        ok = executar_pg_dump(banco, forcar=forcar)
        if ok:
            logger.info(f"[CMD] Backup '{banco}' concluido")
            return True, f"Backup '{banco}' concluido"
        return False, f"Falha backup '{banco}'"
    except Exception as e:
        return False, f"Erro backup: {e}"


def _handle_restaurar(params: dict) -> tuple[bool, str]:
    """Restaura banco a partir de backup local em C:\\Backups_Novo."""
    banco = params.get("banco", "")
    if not banco:
        return False, "Parametro 'banco' obrigatorio"

    from backup_manager import limpar_nome_base
    nome_limpo = limpar_nome_base(banco).lower()
    backup_path = os.path.join(BACKUP_DIR, f"{nome_limpo}.backup")

    if not os.path.exists(backup_path):
        return False, f"Backup nao encontrado: {backup_path}"

    nome_db = f"{nome_limpo}_local"
    try:
        from postgres_manager import criar_banco, restaurar_backup
        from banco_tracker import registrar_banco

        logger.info(f"[CMD] Restaurando '{nome_db}' de {backup_path}")
        if not criar_banco(nome_db):
            return False, f"Falha ao criar banco '{nome_db}'"

        ok = restaurar_backup(nome_db, backup_path)
        if ok:
            registrar_banco(nome_db, nome_limpo)
            logger.info(f"[CMD] Banco '{nome_db}' restaurado com sucesso")
            return True, f"Banco '{nome_db}' restaurado"
        return False, f"Falha pg_restore '{nome_db}'"
    except Exception as e:
        logger.error(f"[CMD] Erro restaurar '{banco}': {e}")
        return False, f"Erro restaurar: {e}"


def _handle_enfileirar(params: dict) -> tuple[bool, str]:
    """Adiciona empresa na fila manual do daemon."""
    empresa_id = params.get("empresa_id")
    nome = params.get("nome", "")
    if not empresa_id:
        return False, "Parametro 'empresa_id' obrigatorio"

    # Le fila manual existente
    fila = []
    if os.path.exists(FILA_MANUAL_FILE):
        try:
            fila = json.loads(open(FILA_MANUAL_FILE, "r", encoding="utf-8").read())
        except Exception:
            fila = []

    # Verifica duplicata
    if any(item.get("empresa_id") == empresa_id for item in fila):
        return False, f"Empresa '{nome}' ja esta na fila manual"

    fila.append({
        "empresa_id": empresa_id,
        "nome": nome,
        "solicitado_em": datetime.now().isoformat(),
        "status": "pendente",
    })

    _salvar_json_atomico(FILA_MANUAL_FILE, fila)
    logger.info(f"[CMD] Empresa '{nome}' (id={empresa_id}) adicionada na fila manual")
    return True, f"'{nome}' adicionada na fila"


def _recolocar_na_fila(empresa_id, nome: str):
    """Limpa tracking (zera tentativas) e adiciona prioridade — o proximo ciclo
    do daemon refaz TODAS as verificacoes (backup >= liberacao, restore, geracao)."""
    from tracking import _carregar, _salvar, adicionar_prioridade
    dados = _carregar()
    chave = str(empresa_id)
    if chave in dados:
        del dados[chave]
        _salvar(dados)
    adicionar_prioridade(int(empresa_id))


def _handle_reprocessar(params: dict) -> tuple[bool, str]:
    """Recoloca empresa na fila do daemon (mesmo ja marcada como processada).
    Marca backup FORCADO: a preparacao baixa um dump NOVO antes de restaurar —
    reprocessar significa refazer com dado atual da nuvem, nao com o mesmo
    .backup antigo em disco."""
    empresa_id = params.get("empresa_id")
    nome = params.get("nome", "")
    if not empresa_id:
        return False, "Parametro 'empresa_id' obrigatorio"

    # Arquiva os SPED antigos da pasta (senao seriam reaproveitados e o sistema
    # marcaria sucesso SEM gerar nada novo — falso sucesso)
    from file_manager import arquivar_speds_antigos
    from tracking import marcar_backup_forcado
    n_arq = arquivar_speds_antigos(nome)
    marcar_backup_forcado(empresa_id)
    _recolocar_na_fila(empresa_id, nome)
    logger.info(f"[CMD] Reprocessamento: '{nome}' (id={empresa_id}) — tracking limpo + backup NOVO forcado + "
                f"{n_arq} arquivo(s) antigos arquivados + prioridade na fila")
    extra = f" ({n_arq} arquivo(s) antigos movidos para 'anteriores\\')" if n_arq else ""
    return True, f"'{nome}' voltou para a fila — backup NOVO + restore NOVO + geracao NOVA garantidos{extra}"


def _handle_reprocessar_erros(params: dict) -> tuple[bool, str]:
    """Refaz TODAS as empresas com status de erro no tracking (inclusive falhas
    definitivas): limpa tracking, arquiva SPEDs antigos e recoloca na fila.
    NAO forca download novo em lote (o backup em disco ja e validado contra a
    data_liberacao; se estiver velho o pipeline baixa sozinho) — para dado novo
    de UMA empresa especifica, use 'reprocessar' ou 'pipeline_completo'."""
    from tracking import listar_gerados
    from file_manager import arquivar_speds_antigos

    com_erro = [(emp_id, reg.get("nome", ""))
                for emp_id, reg in listar_gerados().items()
                if reg.get("status") == "erro"]
    if not com_erro:
        return True, "Nenhuma empresa com erro no tracking — nada a refazer"

    for emp_id, nome in com_erro:
        arquivar_speds_antigos(nome)
        _recolocar_na_fila(emp_id, nome)

    nomes = ", ".join(n for _, n in com_erro)
    logger.info(f"[CMD] Reprocessar erros: {len(com_erro)} empresa(s) de volta a fila: {nomes}")
    return True, f"{len(com_erro)} empresa(s) com erro voltaram para a fila: {nomes}"


def _handle_pipeline_completo(params: dict) -> tuple[bool, str]:
    """
    Pipeline completo manual: forca download de backup NOVO (em thread, na fila
    serializada de pg_dump) e recoloca a empresa na fila do daemon. O restore,
    INI, geracao, organizacao e tracking acontecem pelo pipeline normal —
    nenhuma regra duplicada.
    """
    empresa_id = params.get("empresa_id")
    nome = params.get("nome", "")
    banco = (params.get("banco") or "").strip()
    forcar_backup = params.get("forcar_backup", True)
    if not empresa_id or not banco:
        return False, "Parametros 'empresa_id' e 'banco' obrigatorios"

    from file_manager import arquivar_speds_antigos

    if not forcar_backup:
        arquivar_speds_antigos(nome)
        _recolocar_na_fila(empresa_id, nome)
        logger.info(f"[CMD] Pipeline completo (sem forcar backup): '{nome}' (id={empresa_id})")
        return True, f"'{nome}' na fila — backup sera baixado so se estiver desatualizado"

    def _baixar_e_enfileirar():
        try:
            from backup_manager import executar_pg_dump
            ok = executar_pg_dump(banco, forcar=True)  # serializado: 1 dump por vez
            if not ok:
                logger.error(f"[CMD] Pipeline completo '{nome}': pg_dump falhou — empresa NAO enfileirada")
                return
        except Exception as e:
            logger.error(f"[CMD] Pipeline completo '{nome}': erro no download: {e}")
            return
        arquivar_speds_antigos(nome)
        _recolocar_na_fila(empresa_id, nome)
        logger.info(f"[CMD] Pipeline completo '{nome}': backup novo baixado, empresa na fila")

    threading.Thread(target=_baixar_e_enfileirar, daemon=True,
                     name=f"PipelineCompleto-{banco}").start()
    return True, (f"Pipeline de '{nome}' agendado: baixando backup novo de '{banco}' "
                  f"(fila de 1 dump por vez) — depois entra na fila de geracao")


def _handle_gerar_parcial(params: dict) -> tuple[bool, str]:
    """
    Geracao parcial: registra quais steps gerar (FISCAL, CONTRIB, INVENTARIO,
    COMITENS, SEMITENS, FISCAL_A, FISCAL_B) e recoloca a empresa na fila.
    O main consome o override e o acs_runner gera APENAS o solicitado,
    reutilizando os modos ja existentes (sem automacao nova).
    """
    empresa_id = params.get("empresa_id")
    nome = params.get("nome", "")
    steps = params.get("steps") or []
    info_sped = params.get("informacoes_sped") or ""
    if not empresa_id or not steps:
        return False, "Parametros 'empresa_id' e 'steps' obrigatorios"

    from central_service import resolver_solicitacao, registrar_override_geracao
    res = resolver_solicitacao(set(steps), info_sped, nome)
    if res is None:
        return False, (f"Combinacao de steps nao suportada pelos fluxos existentes: {steps}. "
                       f"Combine como os modos do ACS (ex.: FISCAL+CONTRIB, INVENTARIO+CONTRIB, "
                       f"COMITENS+SEMITENS, FISCAL_A, CONTRIB)")

    modo, pular = res
    if not registrar_override_geracao(empresa_id, steps, nome):
        return False, f"Steps invalidos: {steps}"
    # Arquiva os antigos APENAS dos steps solicitados — serao gerados de novo;
    # os demais continuam na pasta e sao reaproveitados normalmente
    from file_manager import arquivar_speds_antigos
    arquivar_speds_antigos(nome, {s.upper() for s in steps})
    _recolocar_na_fila(empresa_id, nome)
    logger.info(f"[CMD] Geracao parcial: '{nome}' (id={empresa_id}) steps={steps} (modo='{modo or 'padrao'}')")
    return True, f"'{nome}' na fila para gerar apenas: {', '.join(sorted({s.upper() for s in steps}))}"


def _handle_pipeline(params: dict) -> tuple[bool, str]:
    """Pipeline completo: backup + restaurar + enfileirar."""
    banco = params.get("banco", "")
    empresa_id = params.get("empresa_id")
    nome = params.get("nome", "")

    if not banco:
        return False, "Parametro 'banco' obrigatorio"

    # 1. Backup
    ok_backup, msg_backup = _handle_backup({"banco": banco, "forcar": True})
    if not ok_backup:
        return False, f"Pipeline falhou no backup: {msg_backup}"

    # 2. Restaurar
    ok_restore, msg_restore = _handle_restaurar({"banco": banco})
    if not ok_restore:
        return False, f"Pipeline falhou na restauracao: {msg_restore}"

    # 3. Enfileirar (se empresa_id fornecido)
    if empresa_id:
        ok_fila, msg_fila = _handle_enfileirar({
            "empresa_id": empresa_id, "nome": nome
        })
        if not ok_fila:
            return True, f"Backup+Restauracao OK, mas fila falhou: {msg_fila}"

    logger.info(f"[CMD] Pipeline completo '{banco}' OK")
    return True, f"Pipeline '{banco}' completo (backup + restauracao + fila)"


def exportar_log_recente():
    """Copia ultimas 500 linhas do log para pasta compartilhada."""
    try:
        log_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spedgenerator.log")
        log_dst = os.path.join(SPED_EXPORT_DIR, "spedgenerator.log")
        if not os.path.exists(log_src):
            return False
        with open(log_src, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        recent = lines[-500:] if len(lines) > 500 else lines
        tmp = log_dst + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.writelines(recent)
        os.replace(tmp, log_dst)
        return True
    except Exception as e:
        logger.error(f"Erro ao exportar log: {e}")
        return False


def _handle_pausar(params: dict) -> tuple[bool, str]:
    """Pausa o pipeline no proximo checkpoint (entre etapas — nada e corrompido)."""
    from controle import definir_estado
    if definir_estado("pausado", origem=params.get("origem", "monitor")):
        return True, ("Pipeline PAUSADO: segura no proximo checkpoint (entre etapas). "
                      "A etapa atomica em andamento (download/restore/exportacao) termina antes.")
    return False, "Falha ao gravar estado de pausa"


def _handle_retomar(params: dict) -> tuple[bool, str]:
    """Retoma o pipeline pausado/parado."""
    from controle import definir_estado
    if definir_estado("normal", origem=params.get("origem", "monitor")):
        return True, "Pipeline RETOMADO — processamento volta ao normal"
    return False, "Falha ao gravar estado"


def _handle_parar(params: dict) -> tuple[bool, str]:
    """
    Para o pipeline: aborta no proximo checkpoint, mata o ACS Gerente
    (derruba automacao em andamento) e o daemon fica ocioso ate 'retomar'.
    Downloads/restores em andamento terminam (sao seguros e bounded);
    arquivos de exportacao incompletos sao descartados pela validacao.
    """
    from controle import definir_estado
    if not definir_estado("parar", origem=params.get("origem", "monitor")):
        return False, "Falha ao gravar estado de parada"
    try:
        from acs_runner import matar_acs
        matar_acs()
    except Exception as e:
        logger.warning(f"[CMD] parar: nao foi possivel matar ACS: {e}")
    return True, ("Pipeline PARANDO: ACS encerrado, etapas restantes abortadas no checkpoint. "
                  "O daemon fica ocioso ate voce clicar RETOMAR.")


def _handle_sincronizar(params: dict) -> tuple[bool, str]:
    ok1 = exportar_bancos_info()
    ok2 = exportar_empresas_fila()
    if ok1 and ok2:
        return True, "Bancos e empresas sincronizados"
    return False, f"Sincronizacao parcial: bancos={'OK' if ok1 else 'ERRO'}, empresas={'OK' if ok2 else 'ERRO'}"


def _handle_fechamento_simular(params: dict) -> tuple[bool, str]:
    """Simula o fechamento mensal — nao altera nada."""
    from fechamento import simular_fechamento
    sim = simular_fechamento()
    r = sim["resumo"]
    aviso = f" | ATENCAO: {sim['ocupado']}" if sim.get("ocupado") else ""
    return True, (f"SIMULACAO {sim['mes']}: {r['empresas_arquivadas']} empresa(s) p/ arquivar, "
                  f"{r['speds_arquivados']} SPEDs, {r['bancos_candidatos']} banco(s) p/ remover, "
                  f"~{r['espaco_total_gb']} GB a recuperar{aviso}")


def _handle_fechamento_executar(params: dict) -> tuple[bool, str]:
    """Executa o fechamento mensal em thread (zip pode demorar)."""
    from fechamento import sistema_ocupado
    ocupado = sistema_ocupado()
    if ocupado:
        return False, f"Fechamento abortado: {ocupado} — tente quando o sistema estiver ocioso"

    def _executar():
        try:
            from fechamento import executar_fechamento
            executar_fechamento(automatico=False)
        except Exception as e:
            logger.error(f"[CMD] Fechamento mensal falhou: {e}")

    threading.Thread(target=_executar, daemon=True, name="FechamentoMensal").start()
    return True, "Fechamento mensal iniciado — acompanhe no log; relatorio em C:\\ACS_Exporta\\Historico"


# Mapeamento acao -> handler
_HANDLERS = {
    "travar": _handle_travar,
    "destravar": _handle_destravar,
    "dropar": _handle_dropar,
    "backup": _handle_backup,
    "restaurar": _handle_restaurar,
    "enfileirar": _handle_enfileirar,
    "reprocessar": _handle_reprocessar,
    "reprocessar_erros": _handle_reprocessar_erros,
    "pipeline_completo": _handle_pipeline_completo,
    "gerar_parcial": _handle_gerar_parcial,
    "fechamento_simular": _handle_fechamento_simular,
    "fechamento_executar": _handle_fechamento_executar,
    "pipeline": _handle_pipeline,
    "sincronizar": _handle_sincronizar,
    "pausar": _handle_pausar,
    "retomar": _handle_retomar,
    "parar": _handle_parar,
}


# =============================================================================
# Processamento de comandos
# =============================================================================

def _processar_comando(cmd_path: str):
    cmd = _ler_json_safe(cmd_path)
    if not cmd:
        return

    cmd_id = cmd.get("id", "?")
    acao = cmd.get("acao", "")
    params = cmd.get("params", {})

    if cmd.get("status") != "pendente":
        return

    handler = _HANDLERS.get(acao)
    if not handler:
        cmd["status"] = "erro"
        cmd["resultado"] = f"Acao desconhecida: '{acao}'"
        cmd["processado_em"] = datetime.now().isoformat()
        _salvar_json_atomico(cmd_path, cmd)
        return

    cmd["status"] = "executando"
    _salvar_json_atomico(cmd_path, cmd)
    logger.info(f"[CMD] Executando: {acao} (id={cmd_id}) params={params}")

    try:
        ok, msg = handler(params)
        cmd["status"] = "concluido" if ok else "erro"
        cmd["resultado"] = msg
    except Exception as e:
        cmd["status"] = "erro"
        cmd["resultado"] = f"Excecao: {e}"
        logger.error(f"[CMD] Excecao em {acao}: {e}")

    cmd["processado_em"] = datetime.now().isoformat()
    _salvar_json_atomico(cmd_path, cmd)

    # Atualiza bancos_info apos operacoes de banco
    if acao in ("travar", "destravar", "dropar", "restaurar", "sincronizar", "pipeline"):
        exportar_bancos_info()


def _limpar_comandos_antigos():
    if not os.path.exists(COMANDOS_DIR):
        return
    agora = time.time()
    for fname in os.listdir(COMANDOS_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(COMANDOS_DIR, fname)
        try:
            mtime = os.path.getmtime(fpath)
            if agora - mtime > 86400:
                cmd = _ler_json_safe(fpath)
                if cmd and cmd.get("status") in ("concluido", "erro"):
                    os.remove(fpath)
        except Exception:
            pass


# =============================================================================
# Thread principal
# =============================================================================

def _loop_comandos():
    logger.info("[CMD] Command processor iniciado")
    os.makedirs(COMANDOS_DIR, exist_ok=True)

    exportar_bancos_info()
    exportar_empresas_fila()

    ultimo_bancos = time.time()
    ultimo_empresas = time.time()
    ultimo_cleanup = time.time()

    while True:
        try:
            if os.path.exists(COMANDOS_DIR):
                for fname in sorted(os.listdir(COMANDOS_DIR)):
                    if not fname.endswith(".json"):
                        continue
                    fpath = os.path.join(COMANDOS_DIR, fname)
                    cmd = _ler_json_safe(fpath)
                    if cmd and cmd.get("status") == "pendente":
                        _processar_comando(fpath)

            agora = time.time()
            if agora - ultimo_bancos >= BANCOS_INFO_INTERVAL:
                exportar_bancos_info()
                exportar_log_recente()
                ultimo_bancos = agora

            if agora - ultimo_empresas >= EMPRESAS_FILA_INTERVAL:
                exportar_empresas_fila()
                ultimo_empresas = agora

            if agora - ultimo_cleanup >= 3600:
                _limpar_comandos_antigos()
                ultimo_cleanup = agora

        except Exception as e:
            logger.error(f"[CMD] Erro no loop: {e}")

        time.sleep(POLL_INTERVAL)


_thread = None


def iniciar():
    global _thread
    if _thread and _thread.is_alive():
        return
    _thread = threading.Thread(target=_loop_comandos, daemon=True, name="CommandProcessor")
    _thread.start()
    logger.info("[CMD] Command processor thread iniciada")
