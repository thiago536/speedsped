# =============================================================================
# acs_automation.py - Automacao GUI do ACS Gerente via pywinauto
# Substitui LoginAutomatico.ahk, SpedPreencher.ahk e MenuNavegar.ahk
# =============================================================================

import os
import re
import logging
import threading
import time
from datetime import datetime, timedelta
from pywinauto import Desktop, Application, timings
from pywinauto.findwindows import ElementNotFoundError
import psutil
import win32gui

logger = logging.getLogger(__name__)


def _focar_janela(win_wrapper):
    """Traz janela pro foreground e garante foco absoluto de teclado e mouse usando táticas robustas."""
    try:
        import win32gui
        import win32process
        import win32con
        import win32com.client
        hwnd = win_wrapper.handle
        
        # 1. Se estiver minimizada, restaura
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            
        # 2. Tentar focar diretamente
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass

        # 3. Aplicar contornos avançados de restrição de foco do Windows
        # Tática A: Anexar thread de entrada
        try:
            fore_hwnd = win32gui.GetForegroundWindow()
            if fore_hwnd:
                fore_thread, _ = win32process.GetWindowThreadProcessId(fore_hwnd)
                target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)
                
                if fore_thread != target_thread:
                    win32process.AttachThreadInput(fore_thread, target_thread, True)
                    win32gui.SetForegroundWindow(hwnd)
                    win32process.AttachThreadInput(fore_thread, target_thread, False)
        except Exception:
            pass

        # Tática B: Simular pressionamento da tecla ALT para ceder foco
        try:
            shell = win32com.client.Dispatch("WScript.Shell")
            shell.SendKeys("%")  # Envia Alt
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass

        # 4. Força foco do pywinauto
        win_wrapper.set_focus()
    except Exception as e:
        logger.warning(f"Erro ao focar janela: {e}")

# Titulos das janelas ACS
TITULO_ACS      = "ACS Sintese"
TITULO_LOGIN    = "ACS Sintese - Acesso ao Sistema"
TITULO_FISCAL   = "ACS Sintese - Exportação para o SPED"
TITULO_MEIO     = "ACS Sintese - Dados do SPED"
TITULO_CONTRIB  = "ACS Sintese - Exportação para o SPED Contribuições"
TITULO_ATENCAO  = "Confirmação"

# Titulos de dialogs inesperados que devem ser fechados
DIALOGS_FECHAR = [
    "Erro",
    "Error",
    "Warning",
    "Information",
]

# Dimensões da janela ACS de referência (onde coordenadas foram calibradas)
REF_WIDTH = 1038
REF_HEIGHT = 538


def _coord_rel(app_win, x: int, y: int) -> tuple[int, int]:
    """Escala coordenadas proporcionalmente ao tamanho real da janela ACS."""
    try:
        rect = app_win.rectangle()
        w_atual = rect.right - rect.left
        h_atual = rect.bottom - rect.top
        if w_atual > 0 and h_atual > 0:
            x_scaled = int(x * w_atual / REF_WIDTH)
            y_scaled = int(y * h_atual / REF_HEIGHT)
            return x_scaled, y_scaled
    except Exception:
        pass
    return x, y


# =============================================================================
# Utilidades
# =============================================================================

def _calcular_senha_acs() -> str:
    """Calcula senha ACS: (dia*100+mes) / 8369, pega 4 casas decimais."""
    now = datetime.now()
    dia_numerico = (now.day * 100) + now.month
    resultado = dia_numerico / 8369
    resultado_texto = str(resultado)
    match = re.search(r'\.(\d{4})', resultado_texto)
    if match:
        return str(int(match.group(1)))
    return "0000"


def _datas_mes_anterior() -> tuple[str, str, str]:
    """Retorna (mes_ano, data_ini, data_fim) do mes anterior formatados."""
    hoje = datetime.now()
    primeiro_mes_atual = hoje.replace(day=1)
    ultimo_mes_passado = primeiro_mes_atual - timedelta(days=1)
    primeiro_mes_passado = ultimo_mes_passado.replace(day=1)

    mes_ano = ultimo_mes_passado.strftime("%m%Y")
    data_ini = primeiro_mes_passado.strftime("%d%m%Y")
    data_fim = ultimo_mes_passado.strftime("%d%m%Y")
    return mes_ano, data_ini, data_fim


def _find_window(title, timeout=30, regex=False):
    """Encontra janela por titulo com timeout. Retorna wrapper ou None."""
    desktop = Desktop(backend="win32")
    start = time.time()
    while time.time() - start < timeout:
        try:
            if regex:
                wins = desktop.windows(title_re=title)
            else:
                wins = desktop.windows(title=title)
            if wins:
                return wins[0]
        except Exception as e:
            logger.warning(f"Erro em _find_window para '{title}': {e}")
        time.sleep(0.5)
    return None


def _find_window_partial(title_part, timeout=30):
    """Encontra janela cujo titulo contem title_part. Ignora telas SPED internas e login."""
    desktop = Desktop(backend="win32")
    start = time.time()
    while time.time() - start < timeout:
        try:
            for w in desktop.windows():
                titulo = w.window_text() or ""
                if title_part in titulo:
                    # Ignora sub-janelas SPED (Fiscal, Contribuicoes, Dados)
                    if "Exporta" in titulo or "Dados" in titulo:
                        continue
                    # Ignora tela de login (Acesso ao Sistema)
                    if "Acesso" in titulo:
                        continue
                    return w
        except Exception:
            pass
        time.sleep(0.5)
    return None


def _wait_window_close(title, timeout=180):
    """Aguarda janela fechar. Retorna True se fechou, False se timeout."""
    start = time.time()
    while time.time() - start < timeout:
        win = _find_window(title, timeout=1)
        if win is None:
            return True
        time.sleep(1)
    return False


def _get_control_by_class(dialog, class_name, index):
    """
    Pega controle por classe e indice (equivalente ClassNN do AHK).
    AHK ClassNN e 1-based, aqui usamos 1-based tambem.
    Ex: TComboBox6 -> class_name="TComboBox", index=6
    """
    try:
        controls = dialog.children(class_name=class_name)
        if index <= len(controls):
            return controls[index - 1]
        
        # Fallback para descendants caso nao seja filho direto (ex: botoes dentro de paineis)
        descendants = dialog.descendants(class_name=class_name)
        if index <= len(descendants):
            return descendants[index - 1]
    except Exception as e:
        logger.warning(f"Controle {class_name}{index} nao encontrado: {e}")
    return None


def _safe_click(control, desc="botao"):
    """Click seguro com retry."""
    if control is None:
        logger.warning(f"Controle '{desc}' nao encontrado, skip click")
        return False
    try:
        control.click()
        logger.info(f"Click: {desc}")
        return True
    except Exception as e:
        logger.warning(f"Erro ao clicar '{desc}': {e}")
        return False


def _safe_select_combo(control, option, desc="combo"):
    """Seleciona opcao em ComboBox com retry."""
    if control is None:
        logger.warning(f"Controle '{desc}' nao encontrado, skip select")
        return False
    try:
        control.select(option)
        logger.info(f"Combo '{desc}' -> '{option}'")
        return True
    except Exception as e:
        logger.warning(f"Erro combo '{desc}': {e}")
        return False


def _safe_set_text(control, text, desc="campo"):
    """Define texto em controle."""
    if control is None:
        logger.warning(f"Controle '{desc}' nao encontrado, skip set_text")
        return False
    try:
        control.set_focus()
        control.set_edit_text(text)
        logger.info(f"Texto '{desc}' -> '{text}'")
        return True
    except Exception as e:
        logger.warning(f"Erro set_text '{desc}': {e}")
        return False


def _safe_type_keys(control, text, desc="campo"):
    """
    Digita texto via teclado (type_keys) — necessario pra TMaskEdit e DatePicker.
    Seleciona tudo antes de digitar pra substituir conteudo existente.
    """
    if control is None:
        logger.warning(f"Controle '{desc}' nao encontrado, skip type_keys")
        return False
    try:
        control.set_focus()
        time.sleep(0.2)
        control.type_keys("^a", set_foreground=False)  # Ctrl+A seleciona tudo
        time.sleep(0.1)
        control.type_keys(text, with_spaces=True, set_foreground=False)
        logger.info(f"Digitado '{desc}' -> '{text}'")
        return True
    except Exception as e:
        logger.warning(f"Erro type_keys '{desc}': {e}")
        return False


# =============================================================================
# Dialog handler - fecha dialogs inesperados em background
# =============================================================================

class DialogHandler:
    """Thread que monitora e fecha dialogs inesperados."""

    def __init__(self):
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("DialogHandler iniciado")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        logger.info("DialogHandler parado")

    def _loop(self):
        desktop = Desktop(backend="win32")
        while self._running:
            try:
                for win in desktop.windows():
                    titulo = win.window_text() or ""
                    for dialog_title in DIALOGS_FECHAR:
                        if dialog_title.lower() == titulo.lower():
                            logger.warning(f"Dialog inesperado detectado: '{titulo}' - fechando")
                            try:
                                # Tenta clicar OK/Sim/Yes/Close
                                for btn_text in ["OK", "Sim", "Yes", "&OK", "&Sim"]:
                                    try:
                                        btn = win.child_window(title=btn_text, class_name="TButton")
                                        if btn.exists():
                                            btn.click()
                                            break
                                    except Exception:
                                        continue
                                    try:
                                        btn = win.child_window(title=btn_text, class_name="Button")
                                        if btn.exists():
                                            btn.click()
                                            break
                                    except Exception:
                                        continue
                                else:
                                    win.close()
                            except Exception as e:
                                logger.warning(f"Nao conseguiu fechar dialog '{titulo}': {e}")
            except Exception:
                pass
            time.sleep(1)


# =============================================================================
# Login
# =============================================================================

def fazer_login(empresa_nome: str = "", timeout=40) -> bool:
    """
    Aguarda tela de login, preenche usuario/senha, seleciona empresa no combo
    por nome (via combo.select) e valida selecao antes de clicar OK.
    """
    logger.info(f"Aguardando tela de login (empresa='{empresa_nome or 'default'}')...")
    login_win = _find_window(TITULO_LOGIN, timeout=timeout)
    if login_win is None:
        logger.warning("Tela de login nao apareceu")
        return False

    try:
        login_win.set_focus()
        time.sleep(0.5)

        senha = _calcular_senha_acs()
        logger.info(f"Senha ACS calculada: {senha}")

        # TEdit2 = usuario, TEdit1 = senha (Delphi ordem inversa)
        campo_usuario = _get_control_by_class(login_win, "TEdit", 2)
        campo_senha = _get_control_by_class(login_win, "TEdit", 1)

        _safe_set_text(campo_usuario, "ACS_SUPPORTE", "usuario")
        time.sleep(0.2)
        _safe_set_text(campo_senha, senha, "senha")
        time.sleep(0.3)

        # === Seleciona empresa no combo ===
        if empresa_nome:
            combo_emp = _get_control_by_class(login_win, "TComboBox", 1)
            if combo_emp is None:
                logger.error("Combo Empresa (TComboBox1) nao encontrado na tela login")
                return False

            try:
                combo_emp.select(empresa_nome)
                time.sleep(0.3)
            except Exception as e:
                logger.error(f"Falha ao selecionar '{empresa_nome}' no combo: {e}")
                return False

            # Validacao
            atual = (combo_emp.window_text() or "").strip().upper()
            esperado = empresa_nome.strip().upper()
            if esperado not in atual:
                logger.error(f"Empresa errada no combo: atual='{atual}' esperado conter='{esperado}' — ABORTANDO LOGIN")
                return False
            logger.info(f"Combo Empresa = '{atual}' OK")

        # Clica OK (TBitBtn2)
        btn_ok = _get_control_by_class(login_win, "TBitBtn", 2)
        _safe_click(btn_ok, "OK (Login)")
        logger.info("Login enviado")

        # Aguarda login fechar
        if _wait_window_close(TITULO_LOGIN, timeout=20):
            logger.info("Login concluido")
            return True
        else:
            logger.error("Login nao fechou - senha incorreta ou empresa invalida?")
            return False

    except Exception as e:
        logger.error(f"Erro no login: {e}")
        return False


# =============================================================================
# Preencher campos SPED Fiscal
# =============================================================================

def preencher_fiscal(dialog) -> bool:
    """Preenche campos padrao na tela SPED Fiscal."""
    mes_ano, data_ini, data_fim = _datas_mes_anterior()
    logger.info(f"Preenchendo Fiscal: periodo {data_ini} a {data_fim}")

    try:
        dialog.set_focus()
        time.sleep(0.5)

        # TEdit2 = Cod Receita ICMS
        cod_receita = _get_control_by_class(dialog, "TEdit", 2)
        _safe_set_text(cod_receita, "1101", "CodReceita")

        # TMaskEdit1 = Mes/Ano (campo mascarado — digitar via teclado)
        mes_ano_ctrl = _get_control_by_class(dialog, "TMaskEdit", 1)
        _safe_type_keys(mes_ano_ctrl, mes_ano, "MesAno")

        # TAdvSmoothDatePicker2 = Data Inicial (digitar via teclado)
        data_ini_ctrl = _get_control_by_class(dialog, "TAdvSmoothDatePicker", 2)
        _safe_type_keys(data_ini_ctrl, data_ini, "DataInicial")

        # TAdvSmoothDatePicker1 = Data Final (digitar via teclado)
        data_fim_ctrl = _get_control_by_class(dialog, "TAdvSmoothDatePicker", 1)
        _safe_type_keys(data_fim_ctrl, data_fim, "DataFinal")

        # Combos
        combo5 = _get_control_by_class(dialog, "TComboBox", 5)
        _safe_select_combo(combo5, "Sim", "TComboBox5")

        combo4 = _get_control_by_class(dialog, "TComboBox", 4)
        _safe_select_combo(combo4, "Não", "TComboBox4")

        combo3 = _get_control_by_class(dialog, "TComboBox", 3)
        _safe_select_combo(combo3, "Sim", "TComboBox3")

        combo2 = _get_control_by_class(dialog, "TComboBox", 2)
        _safe_select_combo(combo2, "Entradas e Saídas", "TComboBox2")

        time.sleep(0.3)
        return True

    except Exception as e:
        logger.error(f"Erro ao preencher Fiscal: {e}")
        return False


# =============================================================================
# Preencher campos SPED Contribuicoes
# =============================================================================

def preencher_contribuicoes(dialog) -> bool:
    """Preenche campos padrao na tela SPED Contribuicoes."""
    logger.info("Preenchendo Contribuicoes")

    try:
        dialog.set_focus()
        time.sleep(0.5)

        # TMaskEdit2 e TMaskEdit1 - valores fixos (campos mascarados)
        mask2 = _get_control_by_class(dialog, "TMaskEdit", 2)
        _safe_type_keys(mask2, "810902", "TMaskEdit2")

        mask1 = _get_control_by_class(dialog, "TMaskEdit", 1)
        _safe_type_keys(mask1, "217201", "TMaskEdit1")

        # Combos
        combo5 = _get_control_by_class(dialog, "TComboBox", 5)
        _safe_select_combo(combo5, "Sim", "TComboBox5")

        combo4 = _get_control_by_class(dialog, "TComboBox", 4)
        _safe_select_combo(combo4, "Não", "TComboBox4")

        combo3 = _get_control_by_class(dialog, "TComboBox", 3)
        _safe_select_combo(combo3, "Sim", "TComboBox3")

        time.sleep(0.3)
        return True

    except Exception as e:
        logger.error(f"Erro ao preencher Contribuicoes: {e}")
        return False


# =============================================================================
# Ajustar combos por modo (inventario, itens, etc)
# =============================================================================

def ajustar_combos_fiscal(dialog, opcao: str):
    """Ajusta TComboBox6 (inventario) e TComboBox4 (itens NFC-e) conforme modo."""
    combo6 = _get_control_by_class(dialog, "TComboBox", 6)  # Exporta inventario
    combo4 = _get_control_by_class(dialog, "TComboBox", 4)  # Itens NFC-e

    if opcao == "INVENTARIO":
        _safe_select_combo(combo6, "Sim", "Inventario")
        _safe_select_combo(combo4, "Não", "ItensNFCe")
    elif opcao == "COM_ITENS":
        _safe_select_combo(combo6, "Não", "Inventario")
        _safe_select_combo(combo4, "Sim", "ItensNFCe")
    elif opcao == "SEM_ITENS":
        _safe_select_combo(combo6, "Não", "Inventario")
        _safe_select_combo(combo4, "Não", "ItensNFCe")
    else:
        # Padrao: sem inventario, sem itens
        _safe_select_combo(combo6, "Não", "Inventario")
        _safe_select_combo(combo4, "Não", "ItensNFCe")


# =============================================================================
# Confirmar dialogs pos-OK (Atencao + Dados do SPED)
# =============================================================================

_acs_io_anterior = {}  # pid -> (read_bytes, write_bytes)
_acs_processos_cache = {}


def _acs_esta_ativo() -> bool:
    """Checa se processo ACS Gerente está consumindo CPU ou I/O (ativo) de forma não-bloqueante."""
    global _acs_io_anterior, _acs_processos_cache
    
    # Limpa cache de processos que nao estao mais rodando
    try:
        pids_ativos = set(psutil.pids())
        for pid in list(_acs_processos_cache.keys()):
            if pid not in pids_ativos:
                _acs_processos_cache.pop(pid, None)
                _acs_io_anterior.pop(pid, None)
    except Exception:
        pass

    for proc in psutil.process_iter(["name", "pid"]):
        try:
            nome = proc.info["name"] or ""
            if "gerente" in nome.lower():
                pid = proc.info["pid"]
                if pid not in _acs_processos_cache:
                    _acs_processos_cache[pid] = psutil.Process(pid)
                    # Primeiro call para inicializar o contador
                    _acs_processos_cache[pid].cpu_percent()
                    
                p = _acs_processos_cache[pid]
                cpu = p.cpu_percent()
                if cpu > 2.0:
                    return True
                # Checa delta I/O — ACS pode estar escrevendo arquivo sem CPU alta
                try:
                    io = p.io_counters()
                    io_atual = (io.read_bytes, io.write_bytes)
                    io_ant = _acs_io_anterior.get(pid, (0, 0))
                    _acs_io_anterior[pid] = io_atual
                    if io_atual != io_ant:
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False


def _aguardar_geracao_e_fechar(titulo_sped: str, timeout=180) -> bool:
    """
    Aguarda SPED ser gerado e fecha dialogs pos-geracao.

    Estrategia:
    0. Early-exit: se ACS idle desde inicio E tela config ja fechou
       → geracao aconteceu durante espera do "Dados do SPED" (bancos rapidos/medios)
    1. Aguarda dialog "Aviso" aparecer
    2. Aguarda ACS parar de trabalhar (CPU/IO idle)
    3. Fecha Aviso com ENTER
    4. Fecha config se ainda aberta
    """
    from pywinauto import keyboard

    TIMEOUT_INATIVO = 120  # timeout se sem atividade por 120s
    TETO_GERACAO_S = 3000  # teto absoluto de 50min para geracao ATIVA (bancos grandes)
    EARLY_EXIT_CHECK = 15  # apos 15s idle desde inicio, verifica se ja concluiu

    logger.info(f"Aguardando geracao SPED (timeout base={timeout}s, dinamico ativo)...")
    start = time.time()
    ultimo_ativo = time.time()
    desktop = Desktop(backend="win32")
    ja_foi_ativo = False  # rastreia se ACS foi ativo pelo menos 1x

    # Fase 1: aguarda "Aviso" aparecer (ou early-exit se geracao ja concluiu)
    aviso_encontrado = False
    geracao_ja_concluiu = False

    # Resolve a pasta do gerente.exe
    pasta_gerente = None
    try:
        for proc in psutil.process_iter(["name", "exe", "cmdline"]):
            try:
                if proc.info["name"] and "gerente" in proc.info["name"].lower():
                    exe_path = proc.info.get("exe")
                    if not exe_path:
                        cmd = proc.info.get("cmdline")
                        if cmd and len(cmd) > 0:
                            exe_path = cmd[0]
                    if exe_path:
                        pasta_gerente = os.path.dirname(exe_path)
                        break
            except Exception as ex:
                logger.warning(f"Erro ao obter info do processo: {ex}")
    except Exception as ex:
        logger.warning(f"Erro ao iterar processos: {ex}")

    if not pasta_gerente:
        try:
            from config import ACS_EXE_PATH
            pasta_gerente = os.path.dirname(ACS_EXE_PATH)
            logger.info(f"pasta_gerente resolvida via config fallback: '{pasta_gerente}'")
        except Exception:
            pasta_gerente = r"C:\ACSSoft\Sintese\Gerente SPED"
            logger.info(f"pasta_gerente resolvida via hardcoded fallback: '{pasta_gerente}'")
    else:
        logger.info(f"pasta_gerente resolvida via psutil: '{pasta_gerente}'")

    consecutive_not_running = 0
    ultimo_log_carregamento = 0

    while True:
        elapsed = time.time() - start
        inativo_por = time.time() - ultimo_ativo

        # === Detecta se apareceu algum arquivo txt de erro na pasta do gerente ===
        erro_detectado = None
        if pasta_gerente:
            try:
                for f in os.listdir(pasta_gerente):
                    if f.lower().endswith(".txt") and ("invalido" in f.lower() or "ncm" in f.lower()):
                        caminho_txt = os.path.join(pasta_gerente, f)
                        if os.path.isfile(caminho_txt):
                            # Lê o conteúdo do arquivo
                            linhas = []
                            with open(caminho_txt, "r", encoding="utf-8", errors="replace") as f_err:
                                for line in f_err:
                                    line_clean = line.strip()
                                    if line_clean:
                                        linhas.append(line_clean)
                            
                            if linhas:
                                desc_erro = linhas[0]
                                codigos = [l for l in linhas[1:] if l.strip()]
                                if codigos:
                                    msg_completa = f"{desc_erro}: {', '.join(codigos[:5])}"
                                else:
                                    msg_completa = desc_erro
                            else:
                                msg_completa = f"Erro de NCM invalido reportado no arquivo {f}"

                            logger.error(f"Erro de produto detectado: {msg_completa}")
                            erro_detectado = msg_completa

                            # Departamento sem CFOP e' corrigivel automaticamente:
                            # levanta excecao tipada com os pares (depto, cfop) para
                            # o acs_runner cadastrar no banco _local e re-tentar.
                            try:
                                from cfop_fixer import extrair_pares, DepartamentoSemCfopError
                                pares_cfop = extrair_pares("\n".join(linhas))
                                if pares_cfop:
                                    logger.warning(f"Departamentos sem CFOP detectados: {pares_cfop}")
                                    erro_detectado = DepartamentoSemCfopError(msg_completa, pares_cfop)
                            except ImportError:
                                pass
                            
                            # Remove o arquivo para não re-detectar em runs futuros
                            try:
                                os.remove(caminho_txt)
                                logger.info(f"Arquivo de erro removido: {caminho_txt}")
                            except Exception as e_del:
                                logger.warning(f"Erro ao remover {caminho_txt}: {e_del}")
                            
                            # Fecha processo do notepad.exe para limpar a tela
                            for p in psutil.process_iter(["name"]):
                                if p.info["name"] and "notepad" in p.info["name"].lower():
                                    try:
                                        p.kill()
                                        logger.info("Processo do Notepad encerrado para limpar a tela.")
                                    except Exception:
                                        pass
                            break
            except Exception as e:
                logger.warning(f"Erro ao verificar arquivos de erro na pasta do gerente: {e}")

        if erro_detectado:
            if isinstance(erro_detectado, Exception):
                raise erro_detectado
            raise Exception(erro_detectado)

        # === Detecta se o ACS está carregando/gerando ===
        esta_carregando = False
        titulo_carregamento = ""
        try:
            for w in desktop.windows():
                if w.is_visible():
                    t = (w.window_text() or "").lower()
                    cls = (w.class_name() or "").lower()
                    palavras_carregamento = [
                        "carregando", "gerando", "geração", "geracao", "processando", 
                        "aguarde", "exportando", "exportação", "exportacao", "calculando", 
                        "recalculando", "progresso", "criando", "lendo", "gravando", 
                        "escrevendo", "aguardando", "preparando"
                    ]
                    if any(p in t for p in palavras_carregamento):
                        # Verifica se a janela tem ligação com o ACS
                        if "acs" in t or "sintese" in t or "gerente" in t or "delphi" in cls or cls.startswith("t"):
                            esta_carregando = True
                            titulo_carregamento = w.window_text()
                            break
        except Exception:
            pass

        if esta_carregando:
            ultimo_ativo = time.time()  # Evita timeout de inatividade
            ja_foi_ativo = True
            if time.time() - ultimo_log_carregamento > 30:
                logger.info(f"Identificado carregamento/geração ativa: '{titulo_carregamento}'. Impedindo interrupção do sistema.")
                ultimo_log_carregamento = time.time()
        elif _acs_esta_ativo():
            ultimo_ativo = time.time()
            ja_foi_ativo = True

        # Checa se o processo gerente.exe ainda esta rodando no SO (detecta crash durante a geracao)
        proc_running = False
        try:
            for proc in psutil.process_iter(["name"]):
                try:
                    if proc.info["name"] and "gerente" in proc.info["name"].lower():
                        proc_running = True
                        break
                except Exception:
                    pass
        except Exception:
            pass

        # Se a janela de carregamento está visível, o processo com certeza está rodando!
        if esta_carregando:
            proc_running = True

        if not proc_running:
            consecutive_not_running += 1
            if consecutive_not_running >= 8:  # 8 iterações (~16 segundos) sem sinal do processo
                logger.warning("Processo gerente.exe nao existe mais no SO por 16s — crash verificado durante a geracao!")
                break
        else:
            consecutive_not_running = 0

        # === Early-exit: geracao ja aconteceu (durante Dados do SPED wait) ===
        # Se ACS nunca ficou ativo E tela config SPED ja fechou → arquivo ja gerado
        # PULA early-exit para EFD Contribuições pois sua tela fecha ao iniciar a geracao
        if titulo_sped != TITULO_CONTRIB and not ja_foi_ativo and elapsed > EARLY_EXIT_CHECK:
            config_aberta = _find_window(titulo_sped, timeout=1)
            if not config_aberta:
                # Confirma: checa se ACS principal ainda existe (nao crashou)
                acs_main = _find_window_partial(TITULO_ACS, timeout=3)
                
                # Checa se o processo gerente.exe ainda esta rodando no SO
                proc_running = False
                for proc in psutil.process_iter(["name"]):
                    try:
                        if proc.info["name"] and "gerente" in proc.info["name"].lower():
                            proc_running = True
                            break
                    except Exception:
                        pass

                if acs_main:
                    logger.info(f"Early-exit: geracao ja concluiu (ACS idle desde inicio, config '{titulo_sped}' fechada, ACS principal OK). Elapsed={elapsed:.0f}s")
                    geracao_ja_concluiu = True
                    break
                elif not proc_running:
                    logger.warning("ACS principal nao encontrada e processo gerente nao existe no SO — crash verificado")
                    break
                else:
                    logger.info("Janela principal ocupada/oculta, mas processo gerente ainda ativo — continuando espera pelo Aviso")

        # === Detecta arquivo gerado na pasta de exportação ===
        # Se um novo arquivo de SPED/Contribuições aparecer, assumimos que a geração concluiu.
        try:
            from config import SPED_EXPORT_DIR
            for f in os.listdir(SPED_EXPORT_DIR):
                caminho = os.path.join(SPED_EXPORT_DIR, f)
                if os.path.isfile(caminho):
                    mtime = os.path.getmtime(caminho)
                    if mtime >= start:
                        fl = f.lower()
                        if fl.endswith(".txt") and any(p in fl for p in ["sped", "contribui", "spedefd"]):
                            logger.info(f"Detecção por arquivo: Novo arquivo SPED encontrado: '{f}'")
                            time.sleep(2.0)  # Garantia para o ACS terminar de escrever
                            geracao_ja_concluiu = True
                            break
            if geracao_ja_concluiu:
                break
        except Exception as e:
            logger.warning(f"Erro ao verificar arquivos em C:\\ACS_Exporta: {e}")

        # === Detecta "Aviso" ===
        if elapsed > timeout and inativo_por > TIMEOUT_INATIVO:
            break

        # Teto absoluto: bancos grandes podem gerar por 30-40+ min legitimamente
        # (caso POSTO SANTO ANTONIO). Enquanto o ACS mostrar atividade (CPU/IO/
        # janela de progresso) a espera continua; travamento real cai antes na
        # regra de inatividade acima (timeout base + 120s sem atividade).
        if elapsed > TETO_GERACAO_S:
            logger.warning(f"Teto absoluto {TETO_GERACAO_S/60:.0f}min atingido")
            break

        try:
            for w in desktop.windows():
                titulo = w.window_text() or ""
                if titulo == "Aviso" and elapsed > 5:
                    try:
                        children = w.children()
                        tem_botao = any("Button" in (c.class_name() or "") or "TBitBtn" in (c.class_name() or "") for c in children)
                        if tem_botao:
                            try:
                                win32gui.SetForegroundWindow(w.handle)
                            except Exception:
                                pass
                            aviso_encontrado = True
                            textos = []
                            for c in children:
                                cls = c.class_name() or ""
                                txt = c.window_text() or ""
                                if txt.strip():
                                    textos.append(f"[{cls}]{txt.strip()}")
                            conteudo = " | ".join(textos) if textos else "(sem texto visivel)"
                            logger.info(f"Dialog 'Aviso' encontrado ({elapsed:.0f}s). Conteudo: {conteudo}")
                            break
                    except Exception:
                        pass
            if aviso_encontrado:
                break
        except Exception:
            pass
        time.sleep(2)

    # === Se early-exit: pula direto pra cleanup ===
    if geracao_ja_concluiu:
        # Apenas garante que nao ficou nenhum dialog residual
        _fechar_dialog_final(timeout=3)
        acs_win = _find_window_partial(TITULO_ACS, timeout=5)
        if acs_win:
            _focar_janela(acs_win)
            _limpar_subtelas_acs(acs_win)
        logger.info("Pos-geracao concluido (early-exit)")
        return True

    if not aviso_encontrado:
        inativo_por = time.time() - ultimo_ativo
        # Ultima chance: verifica se config ja fechou mesmo sem Aviso
        config_aberta = _find_window(titulo_sped, timeout=1)
        if not config_aberta:
            acs_main = _find_window_partial(TITULO_ACS, timeout=3)
            if acs_main:
                logger.info(f"Aviso nao apareceu mas config fechou e ACS OK — assumindo geracao concluiu. Elapsed={time.time()-start:.0f}s")
                _focar_janela(acs_main)
                _limpar_subtelas_acs(acs_main)
                logger.info("Pos-geracao concluido (sem Aviso)")
                return True
        logger.error(f"Timeout aguardando geracao (Aviso nao apareceu). Elapsed={time.time()-start:.0f}s, inativo={inativo_por:.0f}s")
        return False

    # Fase 2: Aguarda ACS parar de trabalhar ANTES de fechar Aviso
    logger.info("Aviso detectado — aguardando ACS finalizar escrita...")
    espera_pos = 0
    while espera_pos < 30:
        if not _acs_esta_ativo():
            time.sleep(2)
            if not _acs_esta_ativo():
                logger.info(f"ACS idle apos {espera_pos + 2}s pos-Aviso")
                break
        time.sleep(2)
        espera_pos += 2

    # Fase 3: ENTER fecha Aviso (re-foca primeiro)
    try:
        for w in desktop.windows():
            if (w.window_text() or "") == "Aviso":
                try:
                    win32gui.SetForegroundWindow(w.handle)
                except Exception:
                    pass
                break
    except Exception:
        pass
    time.sleep(0.5)
    keyboard.send_keys("{ENTER}")
    logger.info("ENTER enviado (fechar Aviso)")
    time.sleep(2)

    # Fase 4: Fecha tela config SPED — SÓ se ainda aberta
    config_titulo = titulo_sped
    config_win = _find_window(config_titulo, timeout=3)
    if config_win:
        fechou_via_btn = False
        try:
            for btn_class in ["TBitBtn", "TButton", "Button"]:
                controls = config_win.children(class_name=btn_class)
                for ctrl in controls:
                    txt = (ctrl.window_text() or "").lower()
                    if txt in ["sair", "&sair", "fechar", "cancelar", "cancel"]:
                        _safe_click(ctrl, f"Botao '{txt}' da tela config")
                        fechou_via_btn = True
                        break
                if fechou_via_btn:
                    break
        except Exception:
            pass

        if not fechou_via_btn:
            try:
                config_win.set_focus()
                time.sleep(0.3)
                keyboard.send_keys("{ESC}")
                logger.info("ESC enviado (fechar tela config SPED)")
            except Exception:
                pass
        time.sleep(1.5)

        confirm_win = _find_window(TITULO_ATENCAO, timeout=5)
        if confirm_win:
            try:
                confirm_win.set_focus()
            except Exception:
                pass
            time.sleep(0.3)
            keyboard.send_keys("{ESC}")
            logger.info("ESC enviado (cancelar saida — ficar no sistema)")
            time.sleep(0.5)
    else:
        logger.info("Tela config SPED ja fechou automaticamente — ESC nao necessario")
        confirm_win = _find_window(TITULO_ATENCAO, timeout=5)
        if confirm_win:
            try:
                confirm_win.set_focus()
            except Exception:
                pass
            time.sleep(0.3)
            keyboard.send_keys("{ESC}")
            logger.info("ESC enviado (cancelar saida pos-auto-close)")
            time.sleep(0.5)

    # Verificação final: garante ACS principal ainda existe
    time.sleep(1)
    acs_win = _find_window_partial(TITULO_ACS, timeout=10)
    if acs_win is None:
        logger.warning("Janela ACS desapareceu apos pos-geracao — possivel crash/exit inesperado")
    else:
        _focar_janela(acs_win)
        _limpar_subtelas_acs(acs_win)

    logger.info("Pos-geracao concluido")
    return True


def _fechar_dialog_final(timeout=10):
    """Fecha TODOS dialogs do ACS que ficam na frente apos geracao."""
    desktop = Desktop(backend="win32")
    start = time.time()
    titulos_popups = ["aviso", "atenção", "confirmação", "erro", "error", "warning", "information"]
    while time.time() - start < timeout:
        encontrou = False
        try:
            for w in desktop.windows():
                titulo = w.window_text() or ""
                # Ignora a janela oculta do Delphi TApplication
                if titulo == "ACS Gerente":
                    continue
                # Fecha dialogs do ACS (exceto janela principal 'ACS Sintese - Gerente')
                if ("ACS" in titulo or titulo.lower() in titulos_popups) and "Sintese - Gerente" not in titulo and "Sintese - Acesso" not in titulo:
                    for btn_class in ["Button", "TButton", "TBitBtn"]:
                        try:
                            controls = w.children(class_name=btn_class)
                            for ctrl in controls:
                                txt = (ctrl.window_text() or "").lower()
                                if txt in ["ok", "&ok", "sim", "&sim", "yes", ""] or not txt:
                                    ctrl.click()
                                    logger.info(f"Dialog ACS fechado: '{titulo}'")
                                    encontrou = True
                                    time.sleep(0.5)
                                    break
                            if encontrou:
                                break
                        except Exception:
                            continue
        except Exception:
            pass
        if not encontrou:
            break
        time.sleep(0.5)
    logger.info("Dialogs ACS limpos")


def _limpar_subtelas_acs(app_win) -> bool:
    """
    Verifica e fecha qualquer subtela ACS aberta (exceto janela principal).
    Retorna True se tela principal limpa e pronta pro proximo passo.
    """
    desktop = Desktop(backend="win32")
    titulo_principal = app_win.window_text() or ""

    for tentativa in range(5):
        encontrou_subtela = False
        try:
            for w in desktop.windows():
                titulo = w.window_text() or ""
                if not titulo:
                    continue
                # Ignora a janela oculta do Delphi TApplication
                if titulo == "ACS Gerente":
                    continue
                # Nunca tenta fechar a janela principal do Gerente ou a tela de login
                if "Gerente" in titulo or "Acesso" in titulo:
                    continue
                # Ignora janela principal e janelas nao-ACS
                if titulo == titulo_principal:
                    continue
                if "ACS" not in titulo and "Sintese" not in titulo:
                    continue
                # Subtela ACS detectada — tenta fechar
                logger.info(f"Subtela ACS aberta: '{titulo}' — fechando")
                encontrou_subtela = True
                try:
                    # Tenta botao primeiro
                    fechou = False
                    for btn_class in ["Button", "TButton", "TBitBtn"]:
                        controls = w.children(class_name=btn_class)
                        for ctrl in controls:
                            txt = (ctrl.window_text() or "").lower()
                            if txt in ["ok", "&ok", "sim", "&sim", "fechar", "cancelar", "cancel", "sair", "&sair"]:
                                ctrl.click()
                                fechou = True
                                break
                        if fechou:
                            break
                    if not fechou:
                        w.close()
                except Exception as e:
                    logger.warning(f"Nao fechou subtela '{titulo}': {e}")
                # Fechar a tela de exportacao dispara o dialog 'Confirmacao'
                # ("deseja sair do SPED?"), cujo titulo nao contem ACS/Sintese e
                # escapa deste loop. Sem responder 'Sim', a subtela nunca fecha
                # e bloqueia o menu da proxima exportacao (Fiscal/Contrib da
                # mesma sessao falha com "Tela SPED nao abriu de nenhuma forma").
                if "Exporta" in titulo:
                    try:
                        _confirmar_saida_sped(timeout=3)
                    except Exception:
                        pass
        except Exception:
            pass

        if not encontrou_subtela:
            logger.info("Tela principal limpa — pronta")
            return True
        time.sleep(0.5)

    logger.warning("Ainda ha subtelas ACS abertas apos 5 tentativas")
    return False


def _confirmar_saida_sped(timeout=10):
    """Clica Sim (Button1) no dialog 'Confirmacao' que pergunta se quer sair do SPED."""
    TITULOS = [TITULO_ATENCAO, "Atenção", "Confirmação", "Confirma"]
    win = None
    for titulo in TITULOS:
        win = _find_window(titulo, timeout=max(2, timeout // len(TITULOS)))
        if win:
            break
    if win:
        try:
            _focar_janela(win)
        except Exception:
            pass
        time.sleep(0.3)
        btn = _get_control_by_class(win, "Button", 1)
        if btn is None:
            btn = _get_control_by_class(win, "TButton", 1)
        _safe_click(btn, "Sim (Sair do SPED)")
        logger.info("Confirmacao saida SPED clicada")
        time.sleep(0.5)
    else:
        logger.warning("Dialog 'Confirmacao' saida nao apareceu")


def _confirmar_atencao(timeout=20):
    """Clica Sim no dialog de Confirmacao/Atencao e envia ENTER para garantir o fechamento.
    Re-encontra janela a cada tentativa pra evitar WinError 1400 (handle stale).
    Procura por multiplos titulos possiveis."""
    from pywinauto import keyboard
    import win32gui

    TITULOS_CONFIRMACAO = ["Confirmação", "Atenção", "Confirma", "Confirm", "Aviso"]

    def _achar_dialog():
        """Procura dialog de confirmacao por multiplos titulos possiveis de forma super rapida."""
        desktop = Desktop(backend="win32")
        try:
            for w in desktop.windows():
                try:
                    titulo = w.window_text() or ""
                    hwnd = w.handle
                    if win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd):
                        # Verifica se o titulo do dialog bate com os esperados
                        if any(t.lower() in titulo.lower() for t in TITULOS_CONFIRMACAO):
                            # Evita pegar a janela principal do ACS
                            if "gerente" in titulo.lower() or "sintese" in titulo.lower() and len(titulo) > 15:
                                continue
                            return w
                except Exception:
                    pass
        except Exception:
            pass
        return None

    # Aguarda dialog aparecer (timeout total)
    start = time.time()
    win = None
    while time.time() - start < timeout:
        win = _achar_dialog()
        if win:
            logger.info(f"Dialog de confirmacao encontrado: '{win.window_text()}' (HWND: {win.handle})")
            break
        time.sleep(0.2)

    if not win:
        logger.warning("Dialog 'Confirmacao/Atencao' nao apareceu")
        return False

    for tentativa in range(3):
        try:
            # Re-encontra janela a cada tentativa (evita handle stale / WinError 1400)
            if tentativa > 0:
                win = _achar_dialog()
                if not win:
                    logger.info("Dialog confirmacao ja fechou entre tentativas")
                    return True
                logger.info(f"Dialog de confirmacao ainda presente/novo: '{win.window_text()}' (HWND: {win.handle})")

            _focar_janela(win)
            time.sleep(0.3)
            btn = _get_control_by_class(win, "Button", 1)
            if btn is None:
                btn = _get_control_by_class(win, "TButton", 1)
            if btn is None:
                btn = _get_control_by_class(win, "TBitBtn", 1)

            # Clica e em seguida envia ENTER via teclado para robustez absoluta
            if btn:
                _safe_click(btn, "Sim (Confirmacao)")
            else:
                logger.warning("Botao nao encontrado no dialog, tentando fechar via ENTER/ESC")
            time.sleep(0.2)

            # ENTER via keyboard global (mais robusto que type_keys no handle)
            try:
                if win32gui.IsWindow(win.handle):
                    win32gui.SetForegroundWindow(win.handle)
            except Exception:
                pass
            keyboard.send_keys("{ENTER}")
            time.sleep(0.8)

            check = _achar_dialog()
            if not check:
                return True
            logger.warning(f"Confirmacao ainda aberto (tentativa {tentativa + 1}/3)")
        except Exception as e:
            logger.warning(f"Erro confirmar atencao (tentativa {tentativa + 1}): {e}")

    logger.error("Confirmacao nao fechou apos 3 tentativas")
    return False


def _confirmar_dados_sped(timeout=120):
    """Clica OK no dialog Dados do SPED.

    Espera dinamica: apos clicar Sim na confirmacao, ACS processa banco antes
    de mostrar 'Dados do SPED'. Bancos grandes demoram mais. Usa deteccao de
    atividade ACS (CPU/IO) pra estender timeout automaticamente — nao depende
    de valor fixo.
    """
    from pywinauto import keyboard

    TIMEOUT_INATIVO = 60   # desiste se ACS idle por 60s sem tela aparecer
    TETO_ABSOLUTO = 300    # maximo 5 min de espera

    logger.info("Aguardando tela 'Dados do SPED' (espera dinamica por atividade ACS)...")
    start = time.time()
    ultimo_ativo = time.time()
    win = None

    # Fase 1: espera tela aparecer (dinamico — enquanto ACS estiver trabalhando, espera)
    while True:
        elapsed = time.time() - start
        inativo_por = time.time() - ultimo_ativo

        if _acs_esta_ativo():
            ultimo_ativo = time.time()

        # Tenta achar tela
        win = _find_window(TITULO_MEIO, timeout=2)
        if win:
            logger.info(f"Tela 'Dados do SPED' apareceu apos {elapsed:.0f}s")
            break

        # Timeout: ACS parou de trabalhar E tela nao apareceu
        if inativo_por > TIMEOUT_INATIVO and elapsed > timeout:
            logger.warning(f"Dados do SPED nao apareceu (elapsed={elapsed:.0f}s, inativo={inativo_por:.0f}s) — tentando continuar")
            return False

        # Teto absoluto
        if elapsed > TETO_ABSOLUTO:
            logger.warning(f"Teto absoluto {TETO_ABSOLUTO}s — Dados do SPED nao apareceu")
            return False

        time.sleep(2)

    # Fase 2: clica OK com retry
    for tentativa in range(3):
        try:
            if tentativa > 0:
                win = _find_window(TITULO_MEIO, timeout=3)
                if not win:
                    logger.info("Dados do SPED ja fechou entre tentativas")
                    return True

            _focar_janela(win)
            time.sleep(0.5)
            btn = _get_control_by_class(win, "TBitBtn", 2)

            _safe_click(btn, "OK (Dados do SPED)")
            time.sleep(0.2)

            try:
                win32gui.SetForegroundWindow(win.handle)
            except Exception:
                pass
            keyboard.send_keys("{ENTER}")
            time.sleep(1.0)

            check = _find_window(TITULO_MEIO, timeout=2)
            if not check:
                logger.info("Dados do SPED fechado com sucesso")
                return True
            logger.warning(f"Dados do SPED ainda aberto (tentativa {tentativa + 1}/3)")
        except Exception as e:
            logger.warning(f"Erro confirmar Dados do SPED (tentativa {tentativa + 1}): {e}")

    logger.error("Dados do SPED nao fechou apos 3 tentativas")
    return False


# =============================================================================
# Trocar Perfil SPED (A/B)
# =============================================================================

def _encontrar_cadastro_mdi(app_win, timeout=10):
    """Encontra MDI child 'Cadastro de Empresas' via Application wrapper."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            app = Application(backend="win32").connect(handle=app_win.handle)
            main = app.window(handle=app_win.handle)
            cad = main.child_window(title_re=".*Cadastro de Empresas.*")
            if cad.exists():
                logger.info(f"Cadastro MDI child encontrado: '{cad.window_text()}'")
                return cad
        except Exception:
            pass
        time.sleep(0.5)
    logger.error("Cadastro MDI child nao encontrado")
    return None


def _encontrar_caixa_mdi(app_win, timeout=10):
    """Encontra MDI child 'Cadastro de Contas do Caixa' via Application wrapper."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            app = Application(backend="win32").connect(handle=app_win.handle)
            main = app.window(handle=app_win.handle)
            cad = main.child_window(title_re=".*Contas do Caixa.*")
            if cad.exists():
                logger.info(f"Cadastro Contas do Caixa MDI child encontrado: '{cad.window_text()}'")
                return cad
        except Exception:
            pass
        time.sleep(0.5)
    logger.error("Cadastro Contas do Caixa MDI child nao encontrado")
    return None



def trocar_perfil_sped(app_win, perfil: str = "A") -> bool:
    """
    Troca perfil SPED da empresa no ACS.
    Menu via teclado (F10) → Cadastro → Empresa → MDI child.
    Fiscal tab → Editar → combo TwwDBComboBox → Salvar → ESC.
    """
    from pywinauto import keyboard

    logger.info(f"Trocando perfil SPED para '{perfil}'...")

    try:
        # 1. Foco sem click (set_focus clica no icon e minimiza)
        _focar_janela(app_win)
        time.sleep(0.5)
        keyboard.send_keys("{ESC}")       # fecha qualquer menu/dialog residual
        time.sleep(0.5)

        # 2. Menu Cadastro > Empresa via teclado (resolução-independente com delays de segurança)
        keyboard.send_keys("{F10}")       # ativa barra de menus
        time.sleep(0.8)
        keyboard.send_keys("{ENTER}")     # abre Cadastro (1o menu)
        time.sleep(0.8)
        keyboard.send_keys("{DOWN}")      # item 2
        time.sleep(0.3)
        keyboard.send_keys("{DOWN}")      # item 3
        time.sleep(0.3)
        keyboard.send_keys("{DOWN}")      # item 4 (Empresa)
        time.sleep(0.3)
        keyboard.send_keys("{RIGHT}")     # abre submenu
        time.sleep(0.5)
        keyboard.send_keys("{ENTER}")     # seleciona Empresa (1o item submenu)
        time.sleep(2.0)

        # 3. Encontra MDI child Cadastro de Empresas
        cad = _encontrar_cadastro_mdi(app_win)
        if cad is None:
            return False

        # 4. Aba Fiscal (tab header na parte inferior do form)
        cad.click_input(coords=(169, 503))
        time.sleep(0.5)

        # 5. Editar (CmdModificar — toolbar)
        cad.click_input(coords=(138, 58))
        time.sleep(0.5)

        # 6. Encontra combo Perfil SPED por posicao relativa (211,193) na aba Fiscal
        combo_encontrado = False
        cad_rect = cad.rectangle()
        for ctrl in cad.descendants():
            try:
                if ctrl.class_name() == "TwwDBComboBox":
                    r = ctrl.rectangle()
                    rel_x = r.left - cad_rect.left
                    rel_y = r.top - cad_rect.top
                    if abs(rel_x - 211) <= 10 and abs(rel_y - 193) <= 10:
                        valor_antes = ctrl.window_text()
                        if valor_antes == perfil:
                            logger.info(f"Perfil SPED ja esta em '{perfil}', nada a fazer")
                            combo_encontrado = True
                            break
                        ctrl.set_focus()
                        time.sleep(0.3)
                        ctrl.type_keys(perfil, set_foreground=False)
                        time.sleep(0.3)
                        novo = ctrl.window_text()
                        logger.info(f"Perfil SPED: '{valor_antes}' -> '{novo}'")
                        combo_encontrado = True
                        break
            except Exception:
                continue

        if not combo_encontrado:
            logger.error("Combo Perfil SPED nao encontrado na posicao esperada (211,193)")
            keyboard.send_keys("{ESC}")
            time.sleep(0.5)
            return False

        # 6. Salvar (CmdSalvar — toolbar)
        cad.click_input(coords=(170, 63))
        time.sleep(1.0)

        # 7. ESC fecha Cadastro
        keyboard.send_keys("{ESC}")
        time.sleep(0.5)

        # Confirmação se aparecer
        confirm = _find_window(TITULO_ATENCAO, timeout=3)
        if confirm:
            try:
                confirm.set_focus()
            except Exception:
                pass
            keyboard.send_keys("{ENTER}")
            time.sleep(0.5)

        logger.info(f"Perfil SPED trocado para '{perfil}'")
        return True

    except Exception as e:
        logger.error(f"Erro ao trocar perfil: {e}")
        try:
            from pywinauto import keyboard as kb
            for _ in range(3):
                kb.send_keys("{ESC}")
                time.sleep(0.3)
        except Exception:
            pass
        return False


# =============================================================================
# Gerar SPED Fiscal
# =============================================================================

def _abrir_menu_opcoes_e_selecionar(app_win, item_tipo: str) -> bool:
    """Abre o menu Opcoes -> Exportacao de arquivos e seleciona Fiscal ou Contribuicoes via teclado (robusto)."""
    from pywinauto import keyboard
    logger.info(f"Navegando ate o menu {item_tipo} via setas de teclado...")

    try:
        _focar_janela(app_win)
        time.sleep(0.5)
        keyboard.send_keys("{ESC}")  # fecha menus residuais
        time.sleep(0.5)

        # 1. Abre o menu "Opções" usando a tecla de atalho de sistema Alt+O (%o)
        keyboard.send_keys("%o")
        time.sleep(0.8)

        # 2. Desce 3 vezes para "Exportação de arquivos" e abre o submenu (Seta Direita)
        keyboard.send_keys("{DOWN}{DOWN}{DOWN}{RIGHT}")
        time.sleep(0.8)

        # 3. Navega dentro do submenu para o item desejado
        num_downs = 11 if item_tipo == "FISCAL" else 13
        for i in range(num_downs):
            keyboard.send_keys("{DOWN}")
            time.sleep(0.1)
        time.sleep(0.2)
        keyboard.send_keys("{ENTER}")
        logger.info(f"Sequencia de setas enviada para {item_tipo} ({num_downs} setas)")
        time.sleep(2.0)
        return True
    except Exception as e:
        logger.error(f"Erro na navegacao de menu por teclado: {e}")
        return False


def _abrir_menu_opcoes(app_win):
    """Clica em Opcoes -> Exportacao de arquivos (coords fixas — menus nao escalam)."""
    try:
        _focar_janela(app_win)
    except Exception:
        pass
    time.sleep(0.8)

    # Log tamanho da janela pra debug
    try:
        rect = app_win.rectangle()
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        logger.info(f"Menu: janela '{app_win.window_text()}' ativa ({w}x{h} em {rect.left},{rect.top})")
    except Exception:
        logger.info(f"Menu: janela '{app_win.window_text()}' ativa")

    # Menus sao posicao fixa, nao usar _coord_rel
    c1 = (302, 33)   # Opcoes (conforme opções fiscal.txt)
    c2 = (349, 112)  # Exportacao de arquivos (conforme opções fiscal.txt)

    try:
        _focar_janela(app_win)
        time.sleep(0.3)
        app_win.click_input(coords=c1)
        logger.info(f"Click menu Opcoes {c1}")
    except Exception as e:
        logger.warning(f"click_input falhou, tentando via pywinauto mouse: {e}")
        from pywinauto import mouse
        rect = app_win.rectangle()
        mouse.click(coords=(rect.left + c1[0], rect.top + c1[1]))
    time.sleep(1.5)
    try:
        app_win.click_input(coords=c2)
        logger.info(f"Click Exportacao {c2}")
    except Exception:
        from pywinauto import mouse
        rect = app_win.rectangle()
        mouse.click(coords=(rect.left + c2[0], rect.top + c2[1]))
    time.sleep(1.5)


def gerar_fiscal(app_win, opcao: str = "") -> bool:
    """Abre menu SPED Fiscal, preenche, confirma e aguarda geracao."""
    logger.info(f"Gerando SPED Fiscal (opcao='{opcao or 'padrao'}')")

    try:
        # Tentar abrir menu de forma robusta via teclado
        _abrir_menu_opcoes_e_selecionar(app_win, "FISCAL")
        fiscal_win = _find_window(TITULO_FISCAL, timeout=3)
        if fiscal_win is None:
            logger.warning("Tela SPED Fiscal nao abriu via teclado, fechando menus e tentando via cliques de mouse...")
            from pywinauto import keyboard
            keyboard.send_keys("{ESC}{ESC}")  # Garante fechar menus
            time.sleep(0.5)
            _abrir_menu_opcoes(app_win)
            time.sleep(0.5)
            try:
                app_win.click_input(coords=(636, 370))
            except Exception as e:
                logger.warning(f"click_input fiscal falhou: {e}")
                from pywinauto import mouse
                rect = app_win.rectangle()
                mouse.click(coords=(rect.left + 636, rect.top + 370))
            time.sleep(1.5)
            fiscal_win = _find_window(TITULO_FISCAL, timeout=10)

        if fiscal_win is None:
            logger.error("Tela SPED Fiscal nao abriu de nenhuma forma")
            return False

        # Preenche campos padrao
        preencher_fiscal(fiscal_win)
        time.sleep(0.5)

        # Ajusta combos conforme modo
        ajustar_combos_fiscal(fiscal_win, opcao)
        time.sleep(0.4)

        fiscal_win.set_focus()

        # Clica OK (TBitBtn3) — verifica que tela fiscal fechou
        btn_ok = _get_control_by_class(fiscal_win, "TBitBtn", 3)
        if not _safe_click(btn_ok, "OK (Fiscal)"):
            logger.error("Nao conseguiu clicar OK na tela Fiscal")
            return False
        time.sleep(1.0)

        # Confirmacao ("Concorda com os termos?") -> Sim
        if not _confirmar_atencao():
            logger.error("Falha na confirmacao (termos)")
            return False

        # Dados do SPED -> OK (verifica com retry, mas nao-fatal se ausente)
        _confirmar_dados_sped()

        # Aguarda geracao + fecha via ENTER/ESC
        if not _aguardar_geracao_e_fechar(TITULO_FISCAL, timeout=600):
            logger.error("Timeout geracao SPED Fiscal")
            return False

        logger.info("SPED Fiscal gerado e fechado com sucesso")
        return True

    except Exception as e:
        logger.error(f"Erro ao gerar Fiscal: {e}")
        if any(k in str(e).lower() for k in ["ncm", "invalido", "produto"]):
            raise e
        return False


# =============================================================================
# Gerar SPED Contribuicoes
# =============================================================================

def gerar_contribuicoes(app_win) -> bool:
    """Abre menu SPED Contribuicoes, preenche, confirma e aguarda geracao."""
    logger.info("Gerando SPED Contribuicoes")

    try:
        # Tentar abrir menu de forma robusta via teclado
        _abrir_menu_opcoes_e_selecionar(app_win, "CONTRIB")
        contrib_win = _find_window(TITULO_CONTRIB, timeout=3)
        if contrib_win is None:
            logger.warning("Tela SPED Contribuicoes nao abriu via teclado, fechando menus e tentando via cliques de mouse...")
            from pywinauto import keyboard
            keyboard.send_keys("{ESC}{ESC}")  # Garante fechar menus
            time.sleep(0.5)
            _abrir_menu_opcoes(app_win)
            time.sleep(0.5)
            c_contrib = (741, 416)
            logger.info(f"Clicando Contribuicoes {c_contrib}")
            try:
                app_win.click_input(coords=c_contrib)
            except Exception as e:
                logger.warning(f"click_input contrib falhou: {e}")
                from pywinauto import mouse
                rect = app_win.rectangle()
                mouse.click(coords=(rect.left + c_contrib[0], rect.top + c_contrib[1]))
            time.sleep(1.5)
            contrib_win = _find_window(TITULO_CONTRIB, timeout=10)

        if contrib_win is None:
            logger.error("Tela SPED Contribuicoes nao abriu de nenhuma forma")
            return False

        # Preenche campos
        preencher_contribuicoes(contrib_win)
        time.sleep(0.5)

        contrib_win.set_focus()

        # Clica OK (TBitBtn2) — verifica
        btn_ok = _get_control_by_class(contrib_win, "TBitBtn", 2)
        if not _safe_click(btn_ok, "OK (Contribuicoes)"):
            logger.error("Nao conseguiu clicar OK na tela Contribuicoes")
            return False
        time.sleep(1.0)

        # Confirmacao ("Concorda com os termos?") -> Sim
        if not _confirmar_atencao():
            logger.error("Falha na confirmacao (termos) Contribuicoes")
            return False

        # Dados do SPED -> OK (opcional — nem todos modos mostram)
        _confirmar_dados_sped(timeout=5)

        # Aguarda geracao + fecha via ENTER/ESC
        if not _aguardar_geracao_e_fechar(TITULO_CONTRIB, timeout=600):
            logger.error("Timeout geracao SPED Contribuicoes")
            return False

        logger.info("SPED Contribuicoes gerado e fechado com sucesso")
        return True

    except Exception as e:
        logger.error(f"Erro ao gerar Contribuicoes: {e}")
        if any(k in str(e).lower() for k in ["ncm", "invalido", "produto"]):
            raise e
        return False


# =============================================================================
# Pipeline completo
# =============================================================================

# =============================================================================
# Sessao ACS — login separado pra permitir coleta intermediaria entre geracoes
# =============================================================================

def _fechar_avisos_startup(timeout=15):
    """Fecha dialogs 'Aviso' e outros popups de erro/atenção que aparecem ao iniciar ACS (antes do login)."""
    desktop = Desktop(backend="win32")
    start = time.time()
    fechou = 0
    TITULOS_POPUP = ["Aviso", "Atenção", "Confirmação", "ACS Sintese", "Erro", "Error", "Warning", "Information", "gerente"]
    
    while time.time() - start < timeout:
        encontrou = False
        try:
            for w in desktop.windows():
                titulo = w.window_text() or ""
                cls = w.class_name() or ""
                # Ignora a janela principal do gerente ou de login
                if "Sintese - Gerente" in titulo or "Acesso ao Sistema" in titulo:
                    continue
                # Ignora a janela oculta wrapper TApplication
                if cls == "TApplication":
                    continue
                    
                if any(t.lower() == titulo.lower() for t in TITULOS_POPUP) or (titulo == "ACS Sintese" and len(titulo) < 15):
                    encontrou = True
                    try:
                        children = w.children()
                        for c in children:
                            cls = c.class_name() or ""
                            if "Button" in cls or "TBitBtn" in cls or "TButton" in cls:
                                c.click()
                                fechou += 1
                                logger.info(f"Popup de startup '{titulo}' fechado via click ({fechou})")
                                break
                        else:
                            from pywinauto import keyboard
                            w.set_focus()
                            keyboard.send_keys("{ENTER}")
                            fechou += 1
                            logger.info(f"Popup de startup '{titulo}' fechado via ENTER ({fechou})")
                    except Exception:
                        pass
                    time.sleep(0.5)
        except Exception:
            pass
        if not encontrou:
            break
        time.sleep(0.5)
    return fechou


def _timeout_abertura_acs() -> int:
    """
    Timeout para o ACS abrir, escalado pelo tamanho do banco _local do ini.
    Bancos grandes (ex.: remigio 6.3 GB) deixam CPU/disco lentos logo apos o
    restore e o Gerente demora legitimamente mais que 45s para mostrar o login
    — matar aos 45s gera falso "ACS nao abriu", retry e horas de atraso.
    <1.5 GB: base (45s) | >=1.5 GB: 90s | >=4 GB: 150s.
    """
    from config import (ACS_ABRIR_TIMEOUT_S, ACS_NAT_COMPATIVEL, ACS_INI_PATH,
                        PG_HOST, PG_PORT, PG_USER, PG_PASSWORD)
    timeout = ACS_ABRIR_TIMEOUT_S
    try:
        caminho = ""
        with open(ACS_INI_PATH, encoding="latin-1") as f:
            for linha in f:
                if linha.strip().lower().startswith("caminho="):
                    caminho = linha.split("=", 1)[1].strip()
                    break
        if caminho:
            import psycopg2
            conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, user=PG_USER,
                                    password=PG_PASSWORD, dbname="postgres",
                                    connect_timeout=5)
            cur = conn.cursor()
            cur.execute("SELECT pg_database_size(%s)", (caminho,))
            gb = cur.fetchone()[0] / 1_000_000_000
            cur.close()
            conn.close()
            if gb >= 4:
                timeout = max(timeout, 150)
            elif gb >= 1.5:
                timeout = max(timeout, 90)

            # Banco com NAT antigo (count(atualizacoes) < NAT do exe): o Gerente
            # roda o UPGRADE DE ESTRUTURA no primeiro startup, numa transacao
            # unica — matar no meio da rollback e o banco volta a estaca zero
            # (caso alianca 6.1 GB: 150s nunca bastavam e count seguia 259).
            # Comprovado em je_local (259->279 as 06:50, gerou 07:03) e
            # saomarcos_local (259->279 as 22:49, gerou 3/3 as 23:28).
            try:
                conn2 = psycopg2.connect(host=PG_HOST, port=PG_PORT, user=PG_USER,
                                         password=PG_PASSWORD, dbname=caminho,
                                         connect_timeout=5)
                cur2 = conn2.cursor()
                cur2.execute("SELECT count(*) FROM atualizacoes")
                nat_banco = cur2.fetchone()[0]
                cur2.close()
                conn2.close()
                if nat_banco < ACS_NAT_COMPATIVEL:
                    timeout_upgrade = min(900, 240 + int(60 * gb))
                    timeout = max(timeout, timeout_upgrade)
                    logger.info(
                        f"Banco '{caminho}' precisa de upgrade de estrutura "
                        f"(NAT {nat_banco} -> {ACS_NAT_COMPATIVEL}) — aguardando ate {timeout}s "
                        f"para o Gerente migrar sem ser interrompido")
            except Exception:
                pass

            if timeout != ACS_ABRIR_TIMEOUT_S:
                logger.info(f"Banco '{caminho}' tem {gb:.1f} GB — timeout de abertura do ACS ajustado para {timeout}s")
    except Exception as e:
        logger.debug(f"_timeout_abertura_acs: usando base {timeout}s ({e})")
    return timeout


def iniciar_sessao_acs(empresa_nome: str = "") -> tuple:
    """
    Abre ACS, faz login (selecionando empresa no combo) e retorna (app_win, handler).
    Retorna (None, None) se falhar.
    """
    handler = DialogHandler()
    handler.start()

    # Aguarda ACS abrir — espera janela de login OU janela principal aparecer
    timeout_abrir = _timeout_abertura_acs()
    logger.info(f"Aguardando ACS Gerente abrir (ate {timeout_abrir}s)...")
    acs_abriu = False
    start = time.time()
    while time.time() - start < timeout_abrir:
        # Fecha dialogs "Aviso" de startup de forma proativa dentro do loop para evitar deadlock
        _fechar_avisos_startup(timeout=2)
        
        # Checa login
        login_win = _find_window(TITULO_LOGIN, timeout=1)
        if login_win:
            logger.info("Janela de login ACS detectada")
            acs_abriu = True
            break
        # Checa janela principal (caso login seja automatico)
        main_win = _find_window_partial(TITULO_ACS, timeout=1)
        if main_win:
            logger.info("Janela principal ACS detectada (sem login)")
            acs_abriu = True
            break
        time.sleep(0.5)

    if not acs_abriu:
        logger.error(f"ACS Gerente nao abriu em {timeout_abrir}s (popups de startup podem ter travado a execucao)")
        handler.stop()
        return None, None

    if not fazer_login(empresa_nome, timeout=40):
        logger.error("Login falhou")
        handler.stop()
        return None, None

    time.sleep(2.5)

    app_win = _find_window_partial(TITULO_ACS, timeout=10)
    if app_win is None:
        logger.error("ACS fechou apos login")
        handler.stop()
        return None, None

    _focar_janela(app_win)
    return app_win, handler


def finalizar_sessao_acs(handler):
    """Para o DialogHandler."""
    if handler:
        handler.stop()


def reobter_janela_acs(empresa_nome: str = "") -> object:
    """
    Re-encontra janela principal ACS apos uma geracao.
    Se ACS voltou pra tela de login, re-loga automaticamente.
    """
    time.sleep(2)

    # Primeiro tenta achar janela principal (exclui login/SPED)
    app_win = _find_window_partial(TITULO_ACS, timeout=15)
    if app_win is not None:
        _focar_janela(app_win)
        time.sleep(0.5)
        return app_win

    # Janela principal nao encontrada — checa se ACS voltou pra login
    login_win = _find_window(TITULO_LOGIN, timeout=5)
    if login_win is not None:
        logger.warning("ACS voltou pra tela de login — re-logando")
        if fazer_login(empresa_nome, timeout=30):
            time.sleep(2.5)
            app_win = _find_window_partial(TITULO_ACS, timeout=15)
            if app_win is not None:
                _focar_janela(app_win)
                time.sleep(0.5)
                logger.info("Re-login OK — janela principal recuperada")
                return app_win
        logger.error("Re-login falhou")
        return None

    logger.error("Janela ACS nao encontrada apos geracao (nem login, nem principal)")
    return None


def verificar_e_corrigir_tipo_contribuicao(app_win) -> bool:
    """Verifica e corrige o tipo da contribuicao para Aliquotas Basicas."""
    from pywinauto import keyboard
    logger.info("Verificando 'Tipo da contribuicao'...")
    
    try:
        # 1. Focar janela principal e limpar menus
        _focar_janela(app_win)
        time.sleep(0.5)
        keyboard.send_keys("{ESC}")
        time.sleep(0.5)
        
        # 2. Navegar ate Cadastro -> Empresas -> Empresa via teclado
        keyboard.send_keys("{F10}")
        time.sleep(0.8)
        keyboard.send_keys("{ENTER}")
        time.sleep(0.8)
        keyboard.send_keys("{DOWN}")
        time.sleep(0.3)
        keyboard.send_keys("{DOWN}")
        time.sleep(0.3)
        keyboard.send_keys("{DOWN}")
        time.sleep(0.3)
        keyboard.send_keys("{RIGHT}")
        time.sleep(0.5)
        keyboard.send_keys("{ENTER}")
        time.sleep(2.0)
        
        # 3. Encontrar Cadastro de Empresas child
        cad = _encontrar_cadastro_mdi(app_win)
        if cad is None:
            logger.error("MDI Cadastro de Empresas nao encontrado")
            return False
            
        # 4. Clicar na aba Fiscal
        cad.click_input(coords=(169, 503))
        time.sleep(0.8)
        
        # 5. Localizar o combobox de Tipo de Contribuicao (y ~ 298, x ~ 211)
        combo_tipo = None
        cad_rect = cad.rectangle()
        for ctrl in cad.descendants():
            try:
                cls = ctrl.class_name()
                if "combo" in cls.lower() or "wwdb" in cls.lower():
                    r = ctrl.rectangle()
                    rel_x = r.left - cad_rect.left
                    rel_y = r.top - cad_rect.top
                    if abs(rel_x - 211) <= 15 and abs(rel_y - 298) <= 20:
                        combo_tipo = ctrl
                        break
            except Exception:
                pass
                
        if combo_tipo is None:
            logger.error("Combo 'Tipo da contribuicao' nao encontrado na posicao esperada (211,298)")
            keyboard.send_keys("{ESC}")
            return False
            
        valor_atual = (combo_tipo.window_text() or "").strip()
        logger.info(f"Tipo da contribuicao atual: '{valor_atual}'")
        
        # Verifica se ja esta correto (Apuração a aliquota básica)
        if "basica" in valor_atual.lower() or "básica" in valor_atual.lower():
            logger.info("Tipo da contribuicao ja esta correto (basica). Nenhuma alteracao necessaria.")
            keyboard.send_keys("{ESC}")
            time.sleep(0.5)
            return True
            
        # Caso contrario, edita e altera
        logger.info("Tipo da contribuicao incorreto. Corrigindo para 'Apuração a aliquota básica'...")
        
        # Clicar Modificar (138, 58)
        cad.click_input(coords=(138, 58))
        time.sleep(0.8)

        # Set focus no combo e altera
        combo_tipo.set_focus()
        time.sleep(0.3)

        def _eh_basica(v: str) -> bool:
            v = (v or "").strip().lower()
            return "basica" in v or "básica" in v

        # Seleciona "Apuração a aliquota básica" navegando com SETA e RE-LENDO o
        # valor a cada passo (em vez de chutar 3x UP as cegas). Para assim que o
        # combo mostra 'basica'. Pressionar UP no topo nao passa do primeiro item,
        # entao o loop converge se 'basica' for o item mais acima.
        selecionado = _eh_basica(combo_tipo.window_text())
        for _ in range(8):
            if selecionado:
                break
            keyboard.send_keys("{UP}")
            time.sleep(0.25)
            try:
                selecionado = _eh_basica(combo_tipo.window_text())
            except Exception:
                selecionado = False

        if not selecionado:
            logger.error("Nao foi possivel selecionar 'Apuração a aliquota básica' no combo "
                         "— ABORTANDO alteracao SEM salvar (evita gravar valor errado)")
            keyboard.send_keys("{ESC}")  # cancela edicao do registro
            time.sleep(0.3)
            keyboard.send_keys("{ESC}")  # fecha o cadastro
            time.sleep(0.3)
            return False

        keyboard.send_keys("{ENTER}")
        time.sleep(0.3)

        # Confirma o valor selecionado antes de salvar
        novo_val = (combo_tipo.window_text() or "").strip()
        logger.info(f"Tipo da contribuicao apos selecao: '{novo_val}'")
        if not _eh_basica(novo_val):
            logger.error(f"Valor pos-selecao inesperado ('{novo_val}') — ABORTANDO sem salvar")
            keyboard.send_keys("{ESC}")
            time.sleep(0.3)
            keyboard.send_keys("{ESC}")
            time.sleep(0.3)
            return False

        # Clicar Salvar (170, 63)
        cad.click_input(coords=(170, 63))
        time.sleep(1.0)
        
        # ESC fecha Cadastro
        keyboard.send_keys("{ESC}")
        time.sleep(0.5)
        
        # Confirmação se aparecer
        confirm = _find_window(TITULO_ATENCAO, timeout=3)
        if confirm:
            try:
                confirm.set_focus()
            except Exception:
                pass
            keyboard.send_keys("{ENTER}")
            time.sleep(0.5)
            
        logger.info("Tipo da contribuicao atualizado com sucesso!")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao verificar/corrigir tipo da contribuicao: {e}")
        try:
            keyboard.send_keys("{ESC}")
        except Exception:
            pass
        return False


def verificar_e_corrigir_contas_caixa(app_win) -> bool:
    """Verifica e corrige os campos Cod. Contabil e Descricao em Contas do Caixa."""
    from pywinauto import keyboard
    logger.info("Verificando 'Contas do Caixa'...")
    
    try:
        # 1. Focar janela principal e limpar menus
        _focar_janela(app_win)
        time.sleep(0.5)
        keyboard.send_keys("{ESC}")
        time.sleep(0.5)
        
        # 2. Navegar ate Cadastro -> Contas do Caixa (26 vezes seta para baixo)
        keyboard.send_keys("{F10}")
        time.sleep(0.8)
        keyboard.send_keys("{ENTER}")
        time.sleep(0.8)
        for _ in range(26):
            keyboard.send_keys("{DOWN}")
            time.sleep(0.1)
        time.sleep(0.2)
        keyboard.send_keys("{ENTER}")
        time.sleep(2.0)
        
        # 3. Encontrar Cadastro de Contas do Caixa child
        caixa_win = _encontrar_caixa_mdi(app_win)
        if caixa_win is None:
            logger.error("Janela Cadastro de Contas do Caixa nao encontrada")
            return False
            
        # 4. Localizar os Edits (Cod. Contabil e Descricao do Cod. Contabil)
        cod_contabil_ctrl = None
        desc_contabil_ctrl = None
        caixa_rect = caixa_win.rectangle()
        
        for ctrl in caixa_win.descendants():
            try:
                cls = ctrl.class_name()
                if any(k in cls.lower() for k in ["edit", "wwdbedit", "dbedit", "tmask"]):
                    r = ctrl.rectangle()
                    rel_x = r.left - caixa_rect.left
                    rel_y = r.top - caixa_rect.top
                    # Cod. Contabil: x ~ 182, y ~ 413
                    # Descricao: x ~ 182, y ~ 439
                    if abs(rel_x - 182) <= 15:
                        if abs(rel_y - 413) <= 15:
                            cod_contabil_ctrl = ctrl
                        elif abs(rel_y - 439) <= 15:
                            desc_contabil_ctrl = ctrl
            except Exception:
                pass
                
        # Se nao encontrar com o X estrito, tenta encontrar puramente por Y
        if not cod_contabil_ctrl or not desc_contabil_ctrl:
            logger.warning("Filtro de X estrito falhou, procurando edits puramente pelo Y...")
            for ctrl in caixa_win.descendants():
                try:
                    cls = ctrl.class_name()
                    if any(k in cls.lower() for k in ["edit", "wwdbedit", "dbedit", "tmask"]):
                        r = ctrl.rectangle()
                        rel_y = r.top - caixa_rect.top
                        if abs(rel_y - 413) <= 15 and not cod_contabil_ctrl:
                            cod_contabil_ctrl = ctrl
                        elif abs(rel_y - 439) <= 15 and not desc_contabil_ctrl:
                            desc_contabil_ctrl = ctrl
                except Exception:
                    pass
                    
        if not cod_contabil_ctrl or not desc_contabil_ctrl:
            logger.error(f"Campos do Caixa nao encontrados. Cod: {cod_contabil_ctrl}, Desc: {desc_contabil_ctrl}")
            # Log de todos os edits pra ajudar em diagnostico
            for i, ctrl in enumerate(caixa_win.descendants()):
                try:
                    cls = ctrl.class_name()
                    if any(k in cls.lower() for k in ["edit", "wwdbedit", "dbedit"]):
                        r = ctrl.rectangle()
                        rx = r.left - caixa_rect.left
                        ry = r.top - caixa_rect.top
                        logger.info(f"Edit encontrado em ({rx},{ry}) classe={cls} texto='{ctrl.window_text()}'")
                except Exception:
                    pass
            keyboard.send_keys("{ESC}")
            return False
            
        cod_val = (cod_contabil_ctrl.window_text() or "").strip()
        desc_val = (desc_contabil_ctrl.window_text() or "").strip()
        logger.info(f"Valores do Caixa atuais: Cod. Contabil='{cod_val}', Descricao='{desc_val}'")
        
        # Verifica se já estão corretos (01 e COMBUSTIVEL)
        if cod_val == "01" and desc_val.upper() == "COMBUSTIVEL":
            logger.info("Campos do Caixa ja estao corretos. Nenhuma alteracao necessaria.")
            keyboard.send_keys("{ESC}")
            time.sleep(0.5)
            return True
            
        # Caso contrario, edita e altera
        logger.info("Valores do Caixa incorretos. Corrigindo...")
        
        # Clicar Modificar/Editar (138, 58)
        caixa_win.click_input(coords=(138, 58))
        time.sleep(0.8)
        
        # Preencher Cod. Contabil
        cod_contabil_ctrl.set_focus()
        time.sleep(0.2)
        cod_contabil_ctrl.type_keys("^a", set_foreground=False)
        time.sleep(0.1)
        cod_contabil_ctrl.type_keys("01", set_foreground=False)
        time.sleep(0.2)
        
        # Preencher Descricao
        desc_contabil_ctrl.set_focus()
        time.sleep(0.2)
        desc_contabil_ctrl.type_keys("^a", set_foreground=False)
        time.sleep(0.1)
        desc_contabil_ctrl.type_keys("COMBUSTIVEL", set_foreground=False)
        time.sleep(0.2)
        
        # Clicar Salvar (170, 63)
        caixa_win.click_input(coords=(170, 63))
        time.sleep(1.0)
        
        # ESC fecha janela
        keyboard.send_keys("{ESC}")
        time.sleep(0.5)
        
        # Confirmação se aparecer
        confirm = _find_window(TITULO_ATENCAO, timeout=3)
        if confirm:
            try:
                confirm.set_focus()
            except Exception:
                pass
            keyboard.send_keys("{ENTER}")
            time.sleep(0.5)
            
        logger.info("Contas do Caixa atualizado com sucesso!")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao verificar/corrigir contas do caixa: {e}")
        try:
            keyboard.send_keys("{ESC}")
        except Exception:
            pass
        return False


def executar_verificacoes_pre_geracao(app_win, empresa_nome: str = "") -> bool:
    """Executa todas as verificacoes pre-geracao no ACS.

    As duas verificacoes rodam SEMPRE (a falha de uma nao impede a outra) e, ao
    final, a tela e SEMPRE devolvida limpa na janela principal — assim, mesmo que
    um cadastro falhe, a geracao subsequente nao herda uma subtela aberta. Retorna
    True so quando ambas concluiram; o chamador decide o que fazer (hoje: nao-fatal).
    """
    logger.info(f"Iniciando verificacoes pre-geracao para a empresa '{empresa_nome}'...")

    try:
        # 1. Tipo de contribuicao
        ok_tipo = verificar_e_corrigir_tipo_contribuicao(app_win)
        if not ok_tipo:
            logger.error("Falha na verificacao/correcao do Tipo da Contribuicao")

        # 2. Contas do Caixa (roda mesmo que a anterior tenha falhado)
        ok_caixa = verificar_e_corrigir_contas_caixa(app_win)
        if not ok_caixa:
            logger.error("Falha na verificacao/correcao das Contas do Caixa")
    finally:
        # Garante que nenhuma subtela de cadastro ficou aberta antes da geracao.
        _garantir_tela_principal_pos_verificacao(app_win)

    if ok_tipo and ok_caixa:
        logger.info("Todas as verificacoes pre-geracao concluidas com SUCESSO!")
        return True

    logger.warning("Verificacoes pre-geracao concluidas com pendencias "
                   f"(tipo={'OK' if ok_tipo else 'FALHOU'}, caixa={'OK' if ok_caixa else 'FALHOU'})")
    return False


def _garantir_tela_principal_pos_verificacao(app_win):
    """Fecha qualquer cadastro MDI residual e devolve o foco a janela principal do ACS.

    As verificacoes navegam por cadastros (MDI children) e, num caminho de erro,
    podem deixar um cadastro aberto. Antes de gerar, mandamos ESC algumas vezes
    (cancela edicao/fecha o MDI child) e re-focamos a principal, para que a
    navegacao de menu da geracao parta sempre de um estado limpo.
    """
    from pywinauto import keyboard
    try:
        _focar_janela(app_win)
        time.sleep(0.3)
        for _ in range(2):
            keyboard.send_keys("{ESC}")
            time.sleep(0.3)
        # Confirmacao residual ("Deseja sair?" etc.) — cancela pra ficar no sistema
        confirm = _find_window(TITULO_ATENCAO, timeout=2)
        if confirm:
            try:
                confirm.set_focus()
            except Exception:
                pass
            keyboard.send_keys("{ESC}")
            time.sleep(0.3)
        _focar_janela(app_win)
        time.sleep(0.2)
    except Exception as e:
        logger.warning(f"Erro ao garantir tela principal pos-verificacao: {e}")


def executar_automacao(modo: str = "", empresa_nome: str = "") -> bool:
    """
    Pipeline completo de automacao (mantido pra backward compat com modos simples).

    Modos:
      ""              -> Fiscal + Contribuicoes (padrao, 2 arquivos)
      "FISCAL"        -> Apenas Fiscal (1)
      "CONTRIBUICOES" -> Apenas Contribuicoes (1)

    NOTA: Modos multi-fiscal (FISCAL_ITENS, INVENTARIO, INVENTARIO_ITENS)
    sao orquestrados diretamente por acs_runner pra coleta intermediaria.
    """
    app_win, handler = iniciar_sessao_acs(empresa_nome)
    if app_win is None:
        return False

    try:
        ok = True

        if modo == "FISCAL":
            ok = gerar_fiscal(app_win, "")

        elif modo == "CONTRIBUICOES":
            ok = gerar_contribuicoes(app_win)

        elif modo == "INVENTARIO":
            # Fiscal com inventario + Contribuicoes (sem risco de sobrescrita)
            ok = gerar_fiscal(app_win, "INVENTARIO")
            if ok:
                app_win = reobter_janela_acs(empresa_nome)
                if app_win is None:
                    return False
                ok = gerar_contribuicoes(app_win)

        else:
            # Padrao: Fiscal + Contribuicoes
            ok = gerar_fiscal(app_win, "")
            if ok:
                app_win = reobter_janela_acs(empresa_nome)
                if app_win is None:
                    return False
                ok = gerar_contribuicoes(app_win)

        return ok

    finally:
        finalizar_sessao_acs(handler)
