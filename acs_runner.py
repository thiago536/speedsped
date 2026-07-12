# =============================================================================
# acs_runner.py - Lanca ACS Gerente e executa automacao via pywinauto
# =============================================================================

import os
import time
import logging
import shutil
import subprocess
import psutil
from config import ACS_EXE_PATH, SPED_EXPORT_DIR, SPED_TIMEOUT_SECONDS
from acs_automation import (
    executar_automacao,
    iniciar_sessao_acs,
    finalizar_sessao_acs,
    reobter_janela_acs,
    gerar_fiscal,
    gerar_contribuicoes,
    trocar_perfil_sped,
)

logger = logging.getLogger(__name__)

# Retry de ABERTURA do ACS (erro NAT/versao: o app trava antes da tela de login).
# 12 tentativas de abrir com 20s de intervalo; se nao abrir, a empresa e ADIADA
# (main.py passa os outros postos na frente e volta nela no final).
ACS_ABRIR_MAX_TENTATIVAS = 12
ACS_ABRIR_INTERVALO_S = 20


class AcsNaoAbriuError(Exception):
    """ACS nao abriu / tela de login nao apareceu apos todas as tentativas."""
    pass


# ---------------------------------------------------------------------------
# Mapeamento de informacoes_sped -> modo + quantidade de arquivos esperados
# ---------------------------------------------------------------------------

def detectar_modo_sped(informacoes_sped: str | None, nome_posto: str = "") -> tuple[str, int]:
    """
    Analisa campo informacoes_sped e retorna (modo, qtd_arquivos).

    Modos:
      ""                  -> Fiscal + Contribuicoes (padrao, 2 arquivos)
      "FISCAL_ITENS"      -> Fiscal normal + Fiscal COM itens + Contribuicoes (3)
      "INVENTARIO"        -> Fiscal COM inventario + Contribuicoes (2)
      "INVENTARIO_ITENS"  -> Fiscal COM inventario + Fiscal COM itens + Contribuicoes (3)
      "FISCAL_SEM_CONTRIB"-> Fiscal normal + Fiscal COM itens, SEM contribuicoes (2)
    """
    import re
    if nome_posto:
        nome_upper = nome_posto.upper()
        if re.search(r'\bDM\b', nome_upper):
            logger.info(f"Deteccao: Posto '{nome_posto}' identificado como grupo DM. Forcando modo 'FISCAL_SEM_CONTRIB'.")
            return ("FISCAL_SEM_CONTRIB", 2)

    if not informacoes_sped:
        return ("", 2)

    info = informacoes_sped.lower()

    # Anotacoes que nao afetam geracao — tratar como padrao
    if any(x in info for x in ["caipira", "versão", "versao", "2 meses", "thiago", "base -", "pedroramos"]):
        return ("", 2)

    # "3 arquivos e inventário" → inventario + itens + contribuicoes
    if "3 arquivos" in info and "invent" in info:
        return ("INVENTARIO_ITENS", 3)

    # "3 Arquivos" / "3 arquivos" / "Com Itens - 3 Arquivos" / "3 Arquivos / Perfil A"
    # → Fiscal normal + Fiscal COM itens + Contribuicoes
    if "3 arquivos" in info or ("com itens" in info and "3" in info):
        return ("FISCAL_ITENS", 3)

    # "Fiscal com e sem itens" → Fiscal normal + Fiscal COM itens (SEM contribuicoes)
    if "com e sem itens" in info or ("com" in info and "sem" in info and "itens" in info):
        return ("FISCAL_SEM_CONTRIB", 2)

    # "Com Inventário" → Fiscal COM inventario + Contribuicoes
    if "invent" in info:
        return ("INVENTARIO", 2)

    # "Perfil A" / "Fiscal A e B" → Fiscal B + Contrib + Fiscal A (3 arquivos)
    if "perfil" in info or "a e b" in info:
        return ("PERFIL_AB", 3)

    return ("", 2)


# ---------------------------------------------------------------------------
# Utilidades de processo
# ---------------------------------------------------------------------------

def matar_acs():
    """Fecha ACS Gerente: tenta fechar via close+ENTER, senao mata processo."""
    import time as _time
    from pywinauto import Desktop, keyboard

    # Tenta fechar graciosamente via .close() + ENTER (confirmacao)
    try:
        desktop = Desktop(backend="win32")
        for w in desktop.windows():
            t = w.window_text() or ""
            if "Gerente" in t and ("ACS" in t or "SPED" in t or "Sintese" in t):
                w.set_focus()
                _time.sleep(0.3)
                w.close()
                _time.sleep(0.5)
                keyboard.send_keys("{ENTER}")
                logger.info(f"ACS fechado via close+ENTER: '{t}'")
                _time.sleep(1)
                return
    except Exception:
        pass

    # Fallback: mata processo
    for proc in psutil.process_iter(["name", "pid"]):
        if proc.info["name"] and "gerente" in proc.info["name"].lower():
            try:
                proc.kill()
                logger.info(f"ACS Gerente encerrado (PID {proc.info['pid']})")
            except Exception:
                pass
    time.sleep(1)


# ---------------------------------------------------------------------------
# Monitoramento de arquivos
# ---------------------------------------------------------------------------

def _sanitizar(nome: str) -> str:
    for c in r'\/:*?"<>|':
        nome = nome.replace(c, "_")
    return nome.strip()


def _limpar_sped_antigos():
    """Remove arquivos SPED antigos de C:\\ACS_Exporta antes de gerar novos.
    Necessario porque ACS nao sobrescreve arquivo existente do mesmo periodo.
    PRESERVA arquivos intermediarios coletados com sufixos."""
    os.makedirs(SPED_EXPORT_DIR, exist_ok=True)
    removidos = 0
    sufixos_preservar = ["_FISCAL_B", "_CONTRIB", "_FISCAL_A", "_INVENTARIO", "_COMITENS", "_SEMITENS", "_FISCAL"]
    for f in os.listdir(SPED_EXPORT_DIR):
        fl = f.lower()
        if fl.endswith(".txt") and any(p in fl for p in ["sped", "contribui", "spedefd"]):
            # Preserva se tiver algum dos sufixos de coleta intermediaria
            if any(s.lower() in fl for s in sufixos_preservar):
                continue
            caminho = os.path.join(SPED_EXPORT_DIR, f)
            if os.path.isfile(caminho):
                try:
                    os.remove(caminho)
                    removidos += 1
                except Exception:
                    pass
    if removidos:
        logger.info(f"Limpeza: {removidos} arquivo(s) SPED antigo(s) removidos de '{SPED_EXPORT_DIR}'")


def _snapshot_pasta() -> float:
    """Retorna timestamp atual (referencia pra detectar arquivos novos/modificados)."""
    os.makedirs(SPED_EXPORT_DIR, exist_ok=True)
    return time.time()


def aguardar_arquivos_sped(timestamp_antes: float, qtd_esperada: int) -> list[str]:
    """
    Monitora pasta C:\\ACS_Exporta por arquivos modificados apos timestamp_antes.
    Detecta tanto arquivos novos quanto sobrescritos (mesmo nome).
    Retorna caminhos completos ou [] se timeout.
    """
    inicio = time.time()
    logger.info(f"Aguardando {qtd_esperada} arquivo(s) SPED em '{SPED_EXPORT_DIR}'...")

    while time.time() - inicio < SPED_TIMEOUT_SECONDS:
        try:
            arquivos_recentes = []
            for f in os.listdir(SPED_EXPORT_DIR):
                caminho = os.path.join(SPED_EXPORT_DIR, f)
                if os.path.isfile(caminho):
                    mtime = os.path.getmtime(caminho)
                    if mtime > timestamp_antes:
                        arquivos_recentes.append(caminho)
            if len(arquivos_recentes) >= qtd_esperada:
                logger.info(f"Arquivos SPED gerados: {sorted(arquivos_recentes)}")
                return arquivos_recentes
        except Exception:
            pass

        time.sleep(3)

    # Timeout — retorna parcial
    parcial = []
    try:
        for f in os.listdir(SPED_EXPORT_DIR):
            caminho = os.path.join(SPED_EXPORT_DIR, f)
            if os.path.isfile(caminho) and os.path.getmtime(caminho) > timestamp_antes:
                parcial.append(caminho)
    except Exception:
        pass
    logger.error(f"TIMEOUT ({SPED_TIMEOUT_SECONDS}s): {len(parcial)} de {qtd_esperada} arquivo(s)")
    return parcial


# ---------------------------------------------------------------------------
# Coleta intermediaria — pega arquivo(s) gerados e renomeia com sufixo
# ---------------------------------------------------------------------------

def _coletar_intermediario(timestamp_antes: float, sufixo: str) -> list[str]:
    """
    Aguarda 1 arquivo novo em SPED_EXPORT_DIR (por mtime > timestamp_antes).
    Renomeia com sufixo pra evitar sobrescrita pela proxima geracao.
    Retorna lista com caminho renomeado, ou [] se timeout.
    """
    inicio = time.time()
    timeout = SPED_TIMEOUT_SECONDS
    logger.info(f"Coletando arquivo intermediario (sufixo='{sufixo}')...")

    while time.time() - inicio < timeout:
        try:
            for f in os.listdir(SPED_EXPORT_DIR):
                caminho = os.path.join(SPED_EXPORT_DIR, f)
                if os.path.isfile(caminho) and os.path.getmtime(caminho) > timestamp_antes:
                    fl = f.lower()
                    # Apenas processa se for arquivo SPED/Contribuicoes .txt valido
                    if fl.endswith(".txt") and any(p in fl for p in ["sped", "contribui", "spedefd"]):
                        # Encontrou arquivo novo — renomeia com sufixo
                        nome_base, ext = os.path.splitext(f)
                        novo_nome = f"{nome_base}_{sufixo}{ext}"
                        novo_caminho = os.path.join(SPED_EXPORT_DIR, novo_nome)
                        shutil.move(caminho, novo_caminho)
                        logger.info(f"Coletado: '{f}' -> '{novo_nome}'")
                        return [novo_caminho]
        except Exception:
            pass
        time.sleep(3)

    logger.error(f"TIMEOUT coletando arquivo intermediario (sufixo='{sufixo}')")
    return []


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def _executar_acs_tentativa(modo: str, qtd_esperada: int, empresa_nome: str = "",
                            exe_path: str = None,
                            steps_concluidos: set[str] = None,
                            nome_posto: str = "") -> list[str]:
    """Uma tentativa de gerar SPED. Retorna lista de arquivos ou [].
    Levanta AcsNaoAbriuError se o ACS nao abrir apos ACS_ABRIR_MAX_TENTATIVAS."""
    import auditoria
    exe = exe_path or ACS_EXE_PATH

    # 1. Fecha ACS anterior
    matar_acs()

    # Limpa arquivos de erros de produtos antigos no diretorio do ACS antes do lancamento
    try:
        acs_dir = os.path.dirname(exe)
        for f in os.listdir(acs_dir):
            if f.lower().endswith(".txt") and ("invalido" in f.lower() or "ncm" in f.lower()):
                caminho_txt = os.path.join(acs_dir, f)
                if os.path.isfile(caminho_txt):
                    os.remove(caminho_txt)
                    logger.info(f"Limpo arquivo de erro residual antes de lancar o ACS: {caminho_txt}")
    except Exception as e:
        logger.warning(f"Erro ao limpar arquivos de erro residuais no ACS: {e}")

    # 2. Limpa arquivos SPED antigos (ACS nao sobrescreve existentes)
    _limpar_sped_antigos()

    # 3. Lanca ACS Gerente — com RETRY de abertura (erro NAT: trava antes do login)
    app_win, handler = None, None
    for i in range(1, ACS_ABRIR_MAX_TENTATIVAS + 1):
        try:
            # Desconecta sessoes intrusas do banco alvo (lido do .ini — esta
            # funcao nao recebe nome_base) para o upgrade de estrutura do
            # Gerente nao abortar com "outras conexoes ativas". Best-effort:
            # falha aqui NAO pode impedir o lancamento do ACS.
            try:
                from postgres_manager import _desconectar_sessoes
                from acs_automation import _dbname_do_ini
                nome_db = _dbname_do_ini()
                if nome_db:
                    _desconectar_sessoes(nome_db)
            except Exception as e:
                logger.warning(f"Desconexao pre-lancamento falhou (seguindo mesmo assim): {e}")
            subprocess.Popen([exe])
            if i == 1:
                logger.info(f"ACS Gerente lancado: {exe}")
        except Exception as e:
            logger.error(f"Erro ao lancar ACS Gerente: {e}")
            return None  # None = fatal, sem retry

        app_win, handler = iniciar_sessao_acs(empresa_nome)
        if app_win is not None:
            if i > 1:
                logger.info(f"ACS abriu na tentativa {i}/{ACS_ABRIR_MAX_TENTATIVAS}")
                auditoria.evento(nome_posto, "RECUPERACAO",
                                 f"ACS abriu na tentativa {i}/{ACS_ABRIR_MAX_TENTATIVAS}")
            break

        logger.warning(f"ACS nao abriu/login nao apareceu (tentativa {i}/{ACS_ABRIR_MAX_TENTATIVAS})")
        auditoria.evento(nome_posto, "ACS",
                         f"ACS nao abriu / tela de login nao apareceu (tentativa {i}/{ACS_ABRIR_MAX_TENTATIVAS})",
                         nivel="erro")
        matar_acs()
        if i < ACS_ABRIR_MAX_TENTATIVAS:
            time.sleep(ACS_ABRIR_INTERVALO_S)

    if app_win is None:
        raise AcsNaoAbriuError(
            f"ACS nao abriu apos {ACS_ABRIR_MAX_TENTATIVAS} tentativas "
            f"(intervalo {ACS_ABRIR_INTERVALO_S}s)")

    # 3.5. Verificacoes pre-geracao (Tipo da Contribuicao e Contas do Caixa)
    # OBRIGATORIAS antes de TODO sped, porem NAO-FATAIS: se a navegacao GUI do
    # cadastro falhar (MDI nao achado, menu desalinhado, etc.), apenas logamos e
    # auditamos e SEGUIMOS para a geracao. O dado fresco ja esta no banco; nao
    # vale a pena perder o sped por causa de um hiccup de tela no cadastro.
    try:
        from acs_automation import executar_verificacoes_pre_geracao
        if executar_verificacoes_pre_geracao(app_win, empresa_nome):
            logger.info(f"Verificacoes pre-geracao OK para '{empresa_nome}'")
        else:
            logger.warning(
                f"Verificacoes pre-geracao NAO concluidas para '{empresa_nome}' "
                f"— seguindo para a geracao mesmo assim (nao-fatal)")
            auditoria.evento(nome_posto, "VERIFICACAO",
                             "Verificacoes pre-geracao incompletas — geracao prosseguiu",
                             nivel="aviso")
    except Exception as e_verify:
        logger.warning(f"Erro nas verificacoes pre-geracao (nao-fatal): {e_verify} "
                       f"— seguindo para a geracao")
        auditoria.evento(nome_posto, "VERIFICACAO",
                         f"Erro nas verificacoes pre-geracao (nao-fatal): {e_verify}",
                         nivel="aviso")

    # 4. TODOS modos via pipeline unificado (coleta imediata apos cada geracao)
    # Pipeline faz login uma vez, gera cada arquivo e coleta na hora.
    # Mais robusto que executar_automacao() — se ACS crashar, arquivos parciais salvos.
    try:
        arquivos = _pipeline_multi_fiscal(modo, empresa_nome, steps_concluidos,
                                          app_win=app_win, handler=handler)
    finally:
        matar_acs()
    return arquivos


# ---------------------------------------------------------------------------
# Mapeamento de steps por modo (sufixos esperados)
# ---------------------------------------------------------------------------

_STEPS_POR_MODO = {
    "":                 ["FISCAL", "CONTRIB"],
    "FISCAL":           ["FISCAL"],
    "CONTRIBUICOES":    ["CONTRIB"],
    "INVENTARIO":       ["INVENTARIO", "CONTRIB"],
    "FISCAL_ITENS":     ["COMITENS", "SEMITENS", "CONTRIB"],
    "INVENTARIO_ITENS": ["INVENTARIO", "COMITENS", "CONTRIB"],
    "FISCAL_SEM_CONTRIB": ["SEMITENS", "COMITENS"],
    "PERFIL_AB":        ["FISCAL_B", "CONTRIB", "FISCAL_A"],
    "FISCAL_A_ONLY":    ["FISCAL_A"],
}


def _extrair_sufixo(caminho: str) -> str | None:
    """Extrai tipo do arquivo SPED pelo nome.
    Reconhece tanto sufixos intermediarios (_FISCAL) quanto nomes originais do ACS (SPED_*, Contribuicoes_*)."""
    nome = os.path.basename(caminho).upper()
    # 1. Sufixos de coleta intermediaria (mais especificos primeiro)
    for sufixo in ["INVENTARIO", "COMITENS", "SEMITENS", "FISCAL_B", "FISCAL_A", "FISCAL", "CONTRIB"]:
        if f"_{sufixo}" in nome:
            return sufixo
    # 2. Nomes originais do ACS
    if nome.startswith("CONTRIBUI"):
        return "CONTRIB"
    if nome.startswith("SPED") or nome.startswith("SPEDEFD"):
        return "FISCAL"
    return None


def _modo_retry(modo_original: str, steps_esperados: list[str], steps_ok: set) -> str:
    """Determina modo de retry baseado nos steps que faltam."""
    faltam = set(steps_esperados) - steps_ok

    # Caso mais comum: só falta contribuições
    if faltam == {"CONTRIB"}:
        return "CONTRIBUICOES"

    # Só falta fiscal simples
    if faltam == {"FISCAL"}:
        return "FISCAL"

    # Só falta Fiscal A (PERFIL_AB com B e Contrib já gerados)
    if faltam == {"FISCAL_A"}:
        return "FISCAL_A_ONLY"

    # Só falta Fiscal B (PERFIL_AB com A e Contrib já gerados)
    if faltam == {"FISCAL_B"}:
        return "FISCAL"

    # Complexo demais: retry completo do modo original
    return modo_original


def executar_acs_e_gerar_sped(nome_posto: str, nome_base: str = "",
                              informacoes_sped: str | None = None,
                              exe_path: str = None,
                              steps_ja_gerados: set[str] = None,
                              modo_override: str = None,
                              cnpj_supabase: str = "") -> list[str]:
    """
    Pipeline completo com retry inteligente e sucesso parcial:
    - Descobre nome_fantasia real da empresa no banco local.
    - Gera SPED com coleta intermediaria (cada arquivo validado na hora).
    - Se parte falha, salva o que deu certo e retenta apenas o que faltou.
    - Valida cada arquivo com 0000/9999 antes de aceitar.

    modo_override: forca um modo de _STEPS_POR_MODO em vez do detectado por
    informacoes_sped (usado pela geracao parcial da central operacional;
    combinado com steps_ja_gerados gera apenas os steps solicitados).
    """
    from postgres_manager import descobrir_nome_empresa
    from file_manager import validar_arquivo_sped
    import auditoria

    if modo_override is not None and modo_override in _STEPS_POR_MODO:
        modo = modo_override
        qtd_esperada = len(_STEPS_POR_MODO[modo])
    else:
        modo, qtd_esperada = detectar_modo_sped(informacoes_sped, nome_posto)

    # Descobrir nome real da empresa pra selecionar no combo login
    empresa_nome = ""
    if nome_base:
        nome_db = f"{nome_base.lower()}_local"
        empresa_nome = descobrir_nome_empresa(nome_db, nome_posto, cnpj_supabase=cnpj_supabase)
        if empresa_nome is None:
            logger.error(f"Abortando: empresa '{nome_posto}' nao localizada em '{nome_db}'")
            return []

    steps_esperados = _STEPS_POR_MODO.get(modo, ["FISCAL", "CONTRIB"])
    logger.info(f"Modo SPED: '{modo or 'padrao'}' | empresa='{empresa_nome}' | Steps: {steps_esperados}")

    # Retry guiado por PROGRESSO: enquanto cada sessao do ACS validar ao menos
    # um step novo, continua abrindo sessao apenas para os steps faltantes
    # (cliente com 3 arquivos pode precisar de 3+ sessoes se o ACS travar entre
    # geracoes). So desiste apos MAX_SEM_PROGRESSO sessoes seguidas sem validar
    # nada. MAX_TENTATIVAS_ABS e um teto duro de seguranca contra loop.
    MAX_SEM_PROGRESSO = 2
    MAX_TENTATIVAS_ABS = 10
    todos_arquivos = []    # acumula arquivos validos entre tentativas
    steps_concluidos = set(steps_ja_gerados) if steps_ja_gerados else set()
    tentativa = 0
    sem_progresso = 0
    cfop_fix_tentado = False   # correcao automatica de CFOP: no maximo 1x por execucao
    ncm_fix_tentado = False    # correcao automatica de NCM: no maximo 1x por execucao
    saldo_fix_tentado = False  # correcao automatica de saldo_mes: no maximo 1x por execucao

    while tentativa < MAX_TENTATIVAS_ABS:
        # CONTROLE (ADD7): entre sessoes do ACS — PARAR aborta mantendo os
        # arquivos ja validados; pausa segura aqui tambem.
        from controle import aguardar_se_pausado
        if not aguardar_se_pausado(f"geracao de {nome_posto}"):
            logger.warning(f"Geracao de '{nome_posto}' INTERROMPIDA pelo operador — "
                           f"{len(todos_arquivos)} arquivo(s) ja validados serao salvos")
            break

        steps_faltando = [s for s in steps_esperados if s not in steps_concluidos]
        if not steps_faltando:
            break
        if sem_progresso >= MAX_SEM_PROGRESSO:
            break
        tentativa += 1
        n_steps_antes = len(steps_concluidos)

        if tentativa > 1:
            modo_tentativa = _modo_retry(modo, steps_esperados, steps_concluidos)
            logger.info(f"=== RETRY {tentativa} para '{nome_posto}' — modo='{modo_tentativa}' faltam={steps_faltando} ===")
            nomes = [auditoria.STEP_NOME.get(s, s) for s in steps_faltando]
            auditoria.evento(nome_posto, "GERACAO",
                             f"Nova tentativa ({tentativa}) apenas para: {', '.join(nomes)}")
            time.sleep(5)
        else:
            modo_tentativa = modo

        try:
            resultado = _executar_acs_tentativa(modo_tentativa, len(steps_faltando),
                                                empresa_nome, exe_path=exe_path,
                                                steps_concluidos=steps_concluidos,
                                                nome_posto=nome_posto)
        except AcsNaoAbriuError:
            if todos_arquivos:
                # ja colhemos parte dos arquivos nesta execucao — salva os parciais
                logger.warning("ACS parou de abrir no meio da execucao — mantendo parciais")
                break
            raise  # nada gerado: main.py ADIA o posto e volta nele depois dos outros
        except Exception as e_gen:
            # Departamento sem CFOP: corrigivel automaticamente no banco _local.
            # Cadastra o CFOP faltante (clone de template + cabecalho) e repete
            # a geracao. So 1 tentativa de correcao por execucao; se nao houver
            # nada corrigivel, propaga (vira erro definitivo de dados no tracking).
            from cfop_fixer import DepartamentoSemCfopError, corrigir_cfops_banco
            if not isinstance(e_gen, DepartamentoSemCfopError):
                # NCM invalido: corrigivel automaticamente no banco _local
                # (troca pelo NCM dos produtos irmaos — ncm_fixer). O _local e'
                # re-restaurado a cada ciclo, entao a correcao roda de novo
                # sempre que o erro reaparecer. 1 tentativa por execucao.
                # Saldo de fim de mes ausente: dialog 'Atenção' "Os saldos dos
                # diversos do final do mês ainda não foram registrados!" —
                # roda fix_saldo_mes_inventario (insere o registro de fim do
                # mes anterior, FK-safe) e repete. Caso DA SERRA 2026-07-11.
                msg_low = str(e_gen).lower()
                if ("saldo" in msg_low and "registrad" in msg_low
                        and not saldo_fix_tentado and nome_base):
                    saldo_fix_tentado = True
                    nome_db = f"{nome_base.lower()}_local"
                    logger.warning(f"Saldo de fim de mes ausente em '{nome_posto}' — "
                                   f"rodando fix_saldo_mes_inventario em '{nome_db}'")
                    auditoria.evento(nome_posto, "CORRECAO",
                                     "ACS acusou saldos do fim do mes nao registrados — "
                                     "inserindo registro em saldo_mes e repetindo a geracao",
                                     nivel="aviso")
                    from postgres_manager import fix_saldo_mes_inventario
                    if fix_saldo_mes_inventario(nome_db):
                        sem_progresso = 0
                        continue
                    auditoria.evento(nome_posto, "CORRECAO",
                                     "fix_saldo_mes_inventario falhou — erro segue",
                                     nivel="erro")
                    raise

                from ncm_fixer import extrair_barras_ncm, corrigir_ncms_banco
                barras = extrair_barras_ncm(str(e_gen))
                if not barras or ncm_fix_tentado or not nome_base:
                    raise
                ncm_fix_tentado = True
                nome_db = f"{nome_base.lower()}_local"
                logger.warning(f"NCM invalido em '{nome_posto}': barras {barras} — "
                               f"corrigindo automaticamente em '{nome_db}'")
                auditoria.evento(nome_posto, "CORRECAO",
                                 f"NCM invalido detectado (barras {barras}) — "
                                 f"corrigindo pelo NCM dos produtos irmaos no banco local",
                                 nivel="aviso")
                try:
                    corrigiu_ncm, resumo_ncm = corrigir_ncms_banco(nome_db, barras)
                except Exception as e_fix:
                    logger.error(f"Correcao automatica de NCM falhou: {e_fix}")
                    auditoria.evento(nome_posto, "CORRECAO",
                                     f"Correcao automatica de NCM falhou: {e_fix}", nivel="erro")
                    raise e_gen from e_fix
                for linha in resumo_ncm:
                    logger.info(f"[ncm_fixer] {linha}")
                if not corrigiu_ncm:
                    auditoria.evento(nome_posto, "CORRECAO",
                                     f"Nada corrigivel para barras {barras} em {nome_db} — "
                                     f"precisa de correcao manual", nivel="erro")
                    raise
                auditoria.evento(nome_posto, "CORRECAO",
                                 f"NCM(s) corrigido(s) no banco local (barras {barras}) — "
                                 f"repetindo a geracao")
                sem_progresso = 0
                continue
            if cfop_fix_tentado or not nome_base:
                raise
            cfop_fix_tentado = True
            nome_db = f"{nome_base.lower()}_local"
            logger.warning(f"Departamento sem CFOP em '{nome_posto}': {e_gen.pares} — "
                           f"corrigindo automaticamente em '{nome_db}'")
            auditoria.evento(nome_posto, "CORRECAO",
                             f"Departamento sem CFOP detectado ({e_gen.pares}) — "
                             f"cadastrando CFOP automaticamente no banco local",
                             nivel="aviso")
            try:
                corrigiu, resumo = corrigir_cfops_banco(nome_db, e_gen.pares)
            except Exception as e_fix:
                logger.error(f"Correcao automatica de CFOP falhou: {e_fix}")
                auditoria.evento(nome_posto, "CORRECAO",
                                 f"Correcao automatica de CFOP falhou: {e_fix}", nivel="erro")
                raise e_gen from e_fix
            for linha in resumo:
                logger.info(f"[cfop_fixer] {linha}")
            if not corrigiu:
                auditoria.evento(nome_posto, "CORRECAO",
                                 f"Nada corrigivel para {e_gen.pares} em {nome_db} — "
                                 f"precisa de correcao manual", nivel="erro")
                raise
            auditoria.evento(nome_posto, "CORRECAO",
                             f"CFOP(s) cadastrado(s) no banco local ({e_gen.pares}) — "
                             f"repetindo a geracao")
            sem_progresso = 0
            continue

        # None = erro fatal (ACS não lançou), sem retry
        if resultado is None:
            auditoria.evento(nome_posto, "ACS", "ACS Gerente nao pode ser lancado", nivel="erro")
            break

        if not resultado and not steps_concluidos:
            auditoria.evento(nome_posto, "ACS",
                             f"Tentativa {tentativa}: ACS abriu mas nenhum arquivo foi coletado (login/menu/geracao falhou)",
                             nivel="erro")

        # Valida cada arquivo coletado com 0000/9999
        for arq in resultado:
            sufixo = _extrair_sufixo(arq)
            if validar_arquivo_sped(arq):
                todos_arquivos.append(arq)
                if sufixo:
                    steps_concluidos.add(sufixo)
                    logger.info(f"Step '{sufixo}' validado (0000/9999 OK)")
                    auditoria.evento(nome_posto, "GERACAO",
                                     f"{auditoria.STEP_NOME.get(sufixo, sufixo)} gerado e validado (0000/9999 OK)")
                else:
                    logger.info(f"Arquivo validado (sem sufixo): {arq}")
            else:
                logger.warning(f"Arquivo descartado (validacao 0000/9999 falhou): {arq}")

        # Contabiliza progresso desta sessao: validou step novo → zera contador
        if len(steps_concluidos) > n_steps_antes:
            sem_progresso = 0
        else:
            sem_progresso += 1

        # Todos steps OK?
        if steps_concluidos >= set(steps_esperados):
            if tentativa > 1:
                logger.info(f"Retry completou steps faltantes na tentativa {tentativa}")
            break

        faltando = [s for s in steps_esperados if s not in steps_concluidos]
        logger.warning(f"Tentativa {tentativa}: {len(steps_concluidos)}/{len(steps_esperados)} steps OK. "
                       f"Faltam: {faltando} (sessoes sem progresso: {sem_progresso}/{MAX_SEM_PROGRESSO})")

    # Resultado final
    if not todos_arquivos:
        logger.error(f"Todas {tentativa} tentativas falharam para '{nome_posto}'")
    elif steps_concluidos < set(steps_esperados):
        faltando = [s for s in steps_esperados if s not in steps_concluidos]
        nomes = [auditoria.STEP_NOME.get(s, s) for s in faltando]
        logger.warning(f"Sucesso parcial '{nome_posto}': {len(todos_arquivos)} arquivo(s) validos, faltam: {faltando}")
        auditoria.evento(nome_posto, "GERACAO",
                         f"{', '.join(nomes)} nao gerado(s) apos {tentativa} tentativas nesta execucao",
                         nivel="erro")

    return todos_arquivos


# ---------------------------------------------------------------------------
# Pipeline multi-fiscal — coleta intermediaria entre cada geracao
# ---------------------------------------------------------------------------

def _pipeline_multi_fiscal(modo: str, empresa_nome: str = "", steps_concluidos: set[str] = None,
                           app_win=None, handler=None) -> list[str]:
    """
    Pipeline unificado pra todos os modos SPED.
    Faz login uma vez, gera cada arquivo e coleta imediatamente apos geracao.
    Retorna lista parcial se algum step falhar (permite retry focado).
    app_win/handler: sessao ja aberta pelo retry de abertura (se None, abre aqui).
    """
    if app_win is None:
        app_win, handler = iniciar_sessao_acs(empresa_nome)
        if app_win is None:
            return []

    arquivos_coletados = []
    steps_concluidos = steps_concluidos or set()

    try:
        if modo == "INVENTARIO_ITENS":
            # Passo 1: Fiscal COM inventario
            if "INVENTARIO" in steps_concluidos:
                logger.info("Passo 'INVENTARIO' ja gerado anteriormente — pulando")
            else:
                ts = _snapshot_pasta()
                ok = gerar_fiscal(app_win, "INVENTARIO")
                if not ok:
                    logger.error("Falha gerando Fiscal com inventario")
                    return arquivos_coletados
                coletados = _coletar_intermediario(ts, "INVENTARIO")
                arquivos_coletados.extend(coletados)

            # Passo 2: Fiscal COM itens
            if "COMITENS" in steps_concluidos:
                logger.info("Passo 'COMITENS' ja gerado anteriormente — pulando")
            else:
                app_win = reobter_janela_acs(empresa_nome)
                if app_win is None:
                    return arquivos_coletados
                ts = _snapshot_pasta()
                ok = gerar_fiscal(app_win, "COM_ITENS")
                if not ok:
                    logger.error("Falha gerando Fiscal com itens")
                    return arquivos_coletados
                coletados = _coletar_intermediario(ts, "COMITENS")
                arquivos_coletados.extend(coletados)

            # Passo 3: Contribuicoes
            if "CONTRIB" in steps_concluidos:
                logger.info("Passo 'CONTRIB' ja gerado anteriormente — pulando")
            else:
                app_win = reobter_janela_acs(empresa_nome)
                if app_win is None:
                    return arquivos_coletados
                ts = _snapshot_pasta()
                ok = gerar_contribuicoes(app_win)
                if not ok:
                    logger.error("Falha gerando Contribuicoes")
                    return arquivos_coletados
                coletados = _coletar_intermediario(ts, "CONTRIB")
                arquivos_coletados.extend(coletados)

        elif modo == "FISCAL_ITENS":
            # Passo 1: Fiscal COM itens
            if "COMITENS" in steps_concluidos:
                logger.info("Passo 'COMITENS' ja gerado anteriormente — pulando")
            else:
                ts = _snapshot_pasta()
                ok = gerar_fiscal(app_win, "COM_ITENS")
                if not ok:
                    logger.error("Falha gerando Fiscal com itens")
                    return arquivos_coletados
                coletados = _coletar_intermediario(ts, "COMITENS")
                arquivos_coletados.extend(coletados)

            # Passo 2: Fiscal SEM itens
            if "SEMITENS" in steps_concluidos:
                logger.info("Passo 'SEMITENS' ja gerado anteriormente — pulando")
            else:
                app_win = reobter_janela_acs(empresa_nome)
                if app_win is None:
                    return arquivos_coletados
                ts = _snapshot_pasta()
                ok = gerar_fiscal(app_win, "SEM_ITENS")
                if not ok:
                    logger.error("Falha gerando Fiscal sem itens")
                    return arquivos_coletados
                coletados = _coletar_intermediario(ts, "SEMITENS")
                arquivos_coletados.extend(coletados)

            # Passo 3: Contribuicoes
            if "CONTRIB" in steps_concluidos:
                logger.info("Passo 'CONTRIB' ja gerado anteriormente — pulando")
            else:
                app_win = reobter_janela_acs(empresa_nome)
                if app_win is None:
                    return arquivos_coletados
                ts = _snapshot_pasta()
                ok = gerar_contribuicoes(app_win)
                if not ok:
                    logger.error("Falha gerando Contribuicoes")
                    return arquivos_coletados
                coletados = _coletar_intermediario(ts, "CONTRIB")
                arquivos_coletados.extend(coletados)

        elif modo == "FISCAL_SEM_CONTRIB":
            # Fiscal normal (SEM itens) + Fiscal COM itens, SEM contribuicoes
            # Passo 1: Fiscal normal
            if "SEMITENS" in steps_concluidos:
                logger.info("Passo 'SEMITENS' ja gerado anteriormente — pulando")
            else:
                ts = _snapshot_pasta()
                ok = gerar_fiscal(app_win, "SEM_ITENS")
                if not ok:
                    logger.error("Falha gerando Fiscal normal")
                    return arquivos_coletados
                coletados = _coletar_intermediario(ts, "SEMITENS")
                arquivos_coletados.extend(coletados)

            # Passo 2: Fiscal COM itens
            if "COMITENS" in steps_concluidos:
                logger.info("Passo 'COMITENS' ja gerado anteriormente — pulando")
            else:
                app_win = reobter_janela_acs(empresa_nome)
                if app_win is None:
                    return arquivos_coletados
                ts = _snapshot_pasta()
                ok = gerar_fiscal(app_win, "COM_ITENS")
                if not ok:
                    logger.error("Falha gerando Fiscal com itens")
                    return arquivos_coletados
                coletados = _coletar_intermediario(ts, "COMITENS")
                arquivos_coletados.extend(coletados)

        elif modo == "PERFIL_AB":
            # Garante perfil B antes de começar (pode estar em A de run anterior)
            # Depois: Fiscal B + Contribuições → troca A → Fiscal A → volta B
            if "FISCAL_B" in steps_concluidos:
                logger.info("Passo 'FISCAL_B' ja gerado anteriormente — pulando")
            else:
                trocar_perfil_sped(app_win, "B")
                app_win = reobter_janela_acs(empresa_nome)
                if app_win is None:
                    return arquivos_coletados

                # Passo 1: Fiscal B (perfil B garantido)
                ts = _snapshot_pasta()
                ok = gerar_fiscal(app_win, "")
                if not ok:
                    logger.error("Falha gerando Fiscal B")
                    return arquivos_coletados
                coletados = _coletar_intermediario(ts, "FISCAL_B")
                arquivos_coletados.extend(coletados)

            # Passo 2: Contribuições
            if "CONTRIB" in steps_concluidos:
                logger.info("Passo 'CONTRIB' ja gerado anteriormente — pulando")
            else:
                app_win = reobter_janela_acs(empresa_nome)
                if app_win is None:
                    return arquivos_coletados
                ts = _snapshot_pasta()
                ok = gerar_contribuicoes(app_win)
                if not ok:
                    logger.error("Falha gerando Contribuições")
                    return arquivos_coletados
                coletados = _coletar_intermediario(ts, "CONTRIB")
                arquivos_coletados.extend(coletados)

            # Passo 3: Trocar para Perfil A
            if "FISCAL_A" in steps_concluidos:
                logger.info("Passo 'FISCAL_A' ja gerado anteriormente — pulando")
            else:
                app_win = reobter_janela_acs(empresa_nome)
                if app_win is None:
                    return arquivos_coletados
                if not trocar_perfil_sped(app_win, "A"):
                    logger.error("Falha ao trocar para Perfil A")
                    return arquivos_coletados

                # Passo 4: Fiscal A
                app_win = reobter_janela_acs(empresa_nome)
                if app_win is None:
                    return arquivos_coletados
                ts = _snapshot_pasta()
                ok = gerar_fiscal(app_win, "")
                if not ok:
                    logger.error("Falha gerando Fiscal A")
                    # Tenta voltar pra B antes de sair
                    app_win = reobter_janela_acs(empresa_nome)
                    if app_win:
                        trocar_perfil_sped(app_win, "B")
                    return arquivos_coletados
                coletados = _coletar_intermediario(ts, "FISCAL_A")
                arquivos_coletados.extend(coletados)

                # Passo 5: Voltar para Perfil B (cleanup)
                app_win = reobter_janela_acs(empresa_nome)
                if app_win:
                    trocar_perfil_sped(app_win, "B")

        elif modo == "INVENTARIO":
            # Fiscal COM inventario + Contribuicoes
            if "INVENTARIO" in steps_concluidos:
                logger.info("Passo 'INVENTARIO' ja gerado anteriormente — pulando")
            else:
                ts = _snapshot_pasta()
                ok = gerar_fiscal(app_win, "INVENTARIO")
                if not ok:
                    logger.error("Falha gerando Fiscal com inventario")
                    return arquivos_coletados
                coletados = _coletar_intermediario(ts, "INVENTARIO")
                arquivos_coletados.extend(coletados)

            if "CONTRIB" in steps_concluidos:
                logger.info("Passo 'CONTRIB' ja gerado anteriormente — pulando")
            else:
                app_win = reobter_janela_acs(empresa_nome)
                if app_win is None:
                    return arquivos_coletados
                ts = _snapshot_pasta()
                ok = gerar_contribuicoes(app_win)
                if not ok:
                    logger.error("Falha gerando Contribuicoes")
                    return arquivos_coletados
                coletados = _coletar_intermediario(ts, "CONTRIB")
                arquivos_coletados.extend(coletados)

        elif modo == "FISCAL_A_ONLY":
            # Retry focado: só Fiscal A (troca perfil → gera → volta)
            if "FISCAL_A" in steps_concluidos:
                logger.info("Passo 'FISCAL_A' ja gerado anteriormente — pulando")
            else:
                trocar_perfil_sped(app_win, "A")
                app_win = reobter_janela_acs(empresa_nome)
                if app_win is None:
                    return arquivos_coletados
                ts = _snapshot_pasta()
                ok = gerar_fiscal(app_win, "")
                if not ok:
                    logger.error("Falha gerando Fiscal A (retry focado)")
                    app_win = reobter_janela_acs(empresa_nome)
                    if app_win:
                        trocar_perfil_sped(app_win, "B")
                    return arquivos_coletados
                coletados = _coletar_intermediario(ts, "FISCAL_A")
                arquivos_coletados.extend(coletados)
                # Volta pra B
                app_win = reobter_janela_acs(empresa_nome)
                if app_win:
                    trocar_perfil_sped(app_win, "B")

        elif modo == "CONTRIBUICOES":
            # Apenas Contribuicoes (usado em retry focado)
            if "CONTRIB" in steps_concluidos:
                logger.info("Passo 'CONTRIB' ja gerado anteriormente — pulando")
            else:
                ts = _snapshot_pasta()
                ok = gerar_contribuicoes(app_win)
                if not ok:
                    logger.error("Falha gerando Contribuicoes")
                    return arquivos_coletados
                coletados = _coletar_intermediario(ts, "CONTRIB")
                arquivos_coletados.extend(coletados)

        elif modo == "FISCAL":
            # Apenas Fiscal (usado em retry focado)
            if "FISCAL" in steps_concluidos:
                logger.info("Passo 'FISCAL' ja gerado anteriormente — pulando")
            else:
                ts = _snapshot_pasta()
                ok = gerar_fiscal(app_win, "")
                if not ok:
                    logger.error("Falha gerando Fiscal")
                    return arquivos_coletados
                coletados = _coletar_intermediario(ts, "FISCAL")
                arquivos_coletados.extend(coletados)

        else:
            # Padrao: Fiscal + Contribuicoes com coleta intermediaria
            if "FISCAL" in steps_concluidos:
                logger.info("Passo 'FISCAL' ja gerado anteriormente — pulando")
            else:
                ts = _snapshot_pasta()
                ok = gerar_fiscal(app_win, "")
                if not ok:
                    logger.error("Falha gerando Fiscal")
                    return arquivos_coletados
                coletados = _coletar_intermediario(ts, "FISCAL")
                arquivos_coletados.extend(coletados)

            if "CONTRIB" in steps_concluidos:
                logger.info("Passo 'CONTRIB' ja gerado anteriormente — pulando")
            else:
                app_win = reobter_janela_acs(empresa_nome)
                if app_win is None:
                    return arquivos_coletados
                ts = _snapshot_pasta()
                ok = gerar_contribuicoes(app_win)
                if not ok:
                    logger.error("Falha gerando Contribuicoes")
                    return arquivos_coletados
                coletados = _coletar_intermediario(ts, "CONTRIB")
                arquivos_coletados.extend(coletados)

        logger.info(f"Pipeline concluido: {len(arquivos_coletados)} arquivo(s)")
        return arquivos_coletados

    finally:
        finalizar_sessao_acs(handler)
