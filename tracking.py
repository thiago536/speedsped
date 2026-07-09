# =============================================================================
# tracking.py — Registro local de SPEDs gerados (sem alterar Supabase)
#
# Salva em C:\ACS_Exporta\gerados.json
# Formato: { "215": { "nome": "POSTO X", "data_geracao": "...", "arquivos": [...] }, ... }
# =============================================================================

import json
import os
import logging
import shutil
from datetime import datetime
from config import SPED_EXPORT_DIR

logger = logging.getLogger(__name__)

TRACKING_FILE = os.path.join(SPED_EXPORT_DIR, "gerados.json")


def _carregar() -> dict:
    """Carrega JSON de tracking. Retorna dict vazio se não existe."""
    if not os.path.exists(TRACKING_FILE):
        return {}
    try:
        with open(TRACKING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"JSON corrompido em {TRACKING_FILE}: {e} — salvando backup e resetando")
        try:
            shutil.copy2(TRACKING_FILE, TRACKING_FILE + ".bak")
        except OSError:
            pass
        return {}
    except Exception as e:
        logger.warning(f"Erro ao ler tracking: {e}")
        return {}


def _salvar(dados: dict):
    """Salva JSON de tracking (escrita atomica: tmp + rename)."""
    os.makedirs(os.path.dirname(TRACKING_FILE), exist_ok=True)
    tmp = TRACKING_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    os.replace(tmp, TRACKING_FILE)


def registrar_gerado(empresa_id: int, nome: str, arquivos: list[str]):
    """Registra empresa como gerada com sucesso."""
    dados = _carregar()
    dados[str(empresa_id)] = {
        "nome": nome,
        "data_geracao": datetime.now().isoformat(),
        "arquivos": arquivos,
    }
    _salvar(dados)
    logger.info(f"Tracking: '{nome}' (id={empresa_id}) registrado como gerado")


def normalizar_texto(texto: str) -> str:
    import unicodedata
    texto = unicodedata.normalize('NFKD', texto)
    texto_ascii = texto.encode('ascii', 'ignore').decode('ascii')
    return "".join(c for c in texto_ascii if c.isalnum()).lower()


def nomes_parecidos(s1: str, s2: str) -> bool:
    if s1 == s2:
        return True
    def lev(a, b):
        if not a: return len(b)
        if not b: return len(a)
        dp = list(range(len(b) + 1))
        for i in range(1, len(a) + 1):
            prev = dp[0]
            dp[0] = i
            for j in range(1, len(b) + 1):
                temp = dp[j]
                if a[i-1] == b[j-1]:
                    dp[j] = prev
                else:
                    dp[j] = min(dp[j-1], dp[j], prev) + 1
                prev = temp
        return dp[len(b)]
    limiar = max(2, int(len(s1) * 0.2))
    return lev(s1, s2) <= limiar


def obter_caminho_real_tolerante(caminho: str) -> str | None:
    if os.path.exists(caminho):
        return caminho
        
    try:
        caminho = os.path.abspath(caminho)
        dir_nome = os.path.dirname(caminho)
        base_nome = os.path.basename(caminho)
        
        if not os.path.exists(dir_nome):
            dir_pai = os.path.dirname(dir_nome)
            if not os.path.exists(dir_pai):
                return None
                
            target_dir_clean = normalizar_texto(os.path.basename(dir_nome))
            pasta_real = None
            for d in os.listdir(dir_pai):
                d_clean = normalizar_texto(d)
                if nomes_parecidos(target_dir_clean, d_clean):
                    pasta_real = os.path.join(dir_pai, d)
                    break
            if not pasta_real:
                return None
            dir_nome = pasta_real
            
        from acs_runner import _extrair_sufixo
        sufixo_target = _extrair_sufixo(base_nome)
        
        target_file_clean = normalizar_texto(base_nome)
        for f in os.listdir(dir_nome):
            f_clean = normalizar_texto(f)
            if f_clean == target_file_clean:
                return os.path.join(dir_nome, f)
                
            if sufixo_target:
                sufixo_candidate = _extrair_sufixo(f)
                if sufixo_candidate == sufixo_target:
                    digits_target = "".join(c for c in base_nome if c.isdigit())[:12]
                    digits_candidate = "".join(c for c in f if c.isdigit())[:12]
                    if digits_target == digits_candidate:
                        return os.path.join(dir_nome, f)
    except Exception as e:
        logger.warning(f"Erro no helper de caminho tolerante para '{caminho}': {e}")
    return None


# Classificacao de erro (ADD 2026-07):
#  - TRANSITORIO: pode se resolver sozinho (ACS nao abriu, NAT, backup indisponivel)
#      → continua re-tentando com cooldown (comportamento atual).
#  - DEFINITIVO: o Gerente retornou erro de DADOS (NCM invalido, produto, etc.)
#      ou a geracao falhou MAX_TENTATIVAS_GERACAO vezes no dia com o mesmo tipo
#      de erro → o sistema PARA de tentar, sai da fila de prioridade e o monitor
#      exibe FALHA_DEFINITIVA com o motivo. Destrava com: Reprocessar (web),
#      --limpar-tracking, ou nova liberacao do contador (data_liberacao mais nova).
MAX_TENTATIVAS_GERACAO = 3

# Palavras que indicam erro de dados retornado pelo Gerente (nunca se resolve
# re-tentando). "invalido" so conta se nao for "janela invalida" (erro de GUI,
# transitorio — ACS travou/fechou).
_KEYWORDS_ERRO_DADOS = ("ncm", "produto", "invalido")


def _classificar_definitivo(motivo: str, tentativas: int) -> tuple[bool, str]:
    """Retorna (definitivo, motivo possivelmente anotado)."""
    m = motivo.lower()
    if "janela" not in m and any(k in m for k in _KEYWORDS_ERRO_DADOS):
        return True, f"{motivo} | Erro de dados retornado pelo Gerente — corrija no banco e use Reprocessar"
    if motivo.startswith("[GERACAO]") and tentativas >= MAX_TENTATIVAS_GERACAO:
        return True, (f"{motivo} | {tentativas} tentativas sem sucesso — o Gerente nao gera este arquivo; "
                      f"verifique no ACS e use Reprocessar")
    return False, motivo


def registrar_erro(empresa_id: int, nome: str, motivo: str, arquivos: list[str] = None,
                   definitivo: bool = False):
    """Registra erro para empresa (pra saber que tentou e falhou) com contador de tentativas.

    definitivo=True (explicito ou auto-classificado): para de re-tentar e sai da
    fila de prioridade — o monitor mostra FALHA_DEFINITIVA com o motivo."""
    dados = _carregar()
    registro_anterior = dados.get(str(empresa_id)) or {}

    # Se o erro anterior foi de um dia diferente, resetamos as tentativas!
    data_geracao_antiga = registro_anterior.get("data_geracao")
    tentativas = registro_anterior.get("tentativas", 0)
    if data_geracao_antiga:
        try:
            dt_antigo = datetime.fromisoformat(data_geracao_antiga)
            if dt_antigo.date() < datetime.now().date():
                tentativas = 0  # Novo dia, resetamos
        except Exception:
            tentativas = 0

    tentativas += 1
    if not definitivo:
        definitivo, motivo = _classificar_definitivo(motivo, tentativas)
    dados[str(empresa_id)] = {
        "nome": nome,
        "data_geracao": datetime.now().isoformat(),
        "status": "erro",
        "motivo": motivo,
        "tentativas": tentativas,
        "definitivo": definitivo,
        "arquivos": arquivos or registro_anterior.get("arquivos") or [],
    }
    _salvar(dados)
    if definitivo:
        remover_prioridade(empresa_id)
        logger.error(f"Tracking: '{nome}' (id={empresa_id}) FALHA DEFINITIVA — parou de re-tentar. "
                     f"Motivo: {motivo}")
    else:
        logger.info(f"Tracking: '{nome}' (id={empresa_id}) registrado como erro. Tentativas hoje: {tentativas}")



def ja_gerado(empresa_id: int, informacoes_sped: str | None = None,
              data_liberacao=None) -> bool:
    """
    Checa se empresa já foi gerada com sucesso (pular no próximo run).
    Verifica se o registro local existe, se não tem status de erro (respeitando limite de retries e cooldown),
    se a quantidade de arquivos físicos gerados coincide com a esperada,
    e se os arquivos existem e não estão vazios.

    data_liberacao: se fornecida e for MAIS NOVA que o último registro (sucesso
    ou erro), a empresa foi RE-LIBERADA pelo contador → reprocessar do zero
    (zera o bloqueio de 3 tentativas/dia).
    """
    dados = _carregar()
    registro = dados.get(str(empresa_id))
    if not registro:
        return False

    # Re-liberação: contador liberou DEPOIS do último resultado registrado
    if data_liberacao:
        try:
            dt_lib = (datetime.fromisoformat(data_liberacao)
                      if isinstance(data_liberacao, str) else data_liberacao)
            if dt_lib.tzinfo is not None:
                # data_geracao é horário local naive — converte para comparar
                dt_lib = dt_lib.astimezone().replace(tzinfo=None)
            dt_reg = datetime.fromisoformat(registro.get("data_geracao", ""))
            if dt_lib > dt_reg:
                logger.info(
                    f"Empresa ID {empresa_id} RE-LIBERADA "
                    f"(liberacao {dt_lib:%d/%m %H:%M} > ultimo registro {dt_reg:%d/%m %H:%M}) "
                    f"— reprocessando (tentativas zeradas)"
                )
                del dados[str(empresa_id)]
                _salvar(dados)
                return False
        except (ValueError, TypeError):
            pass

    if registro.get("status") == "erro":
        # FALHA DEFINITIVA: erro de dados do Gerente ou tentativas esgotadas —
        # re-tentar nao resolve. Fica bloqueada (mesmo em dias seguintes) ate
        # Reprocessar / --limpar-tracking / nova liberacao do contador.
        if registro.get("definitivo"):
            return True

        # Se tem status de erro, vamos ver se atingiu o máximo de tentativas ou se está em cooldown
        tentativas = registro.get("tentativas", 0)
        
        # Verifica se o erro foi registrado hoje
        data_geracao_str = registro.get("data_geracao")
        hoje = datetime.now().date()
        dia_diferente = False
        if data_geracao_str:
            try:
                dt_erro = datetime.fromisoformat(data_geracao_str)
                if dt_erro.date() < hoje:
                    dia_diferente = True
            except Exception:
                dia_diferente = True

        if dia_diferente:
            # É de outro dia, resetamos a lógica de erro para tentar hoje
            return False

        # NAO desiste mais apos 3 tentativas (erros tipo "ACS nao abriu / NAT"
        # podem se resolver sozinhos): o sistema fica tentando o dia inteiro,
        # apenas espacando mais os retries para nao martelar (15 min nas 3
        # primeiras tentativas, 60 min a partir da 4a).
        minutos_cooldown = 60 if tentativas >= 3 else 15
        if data_geracao_str:
            try:
                dt_erro = datetime.fromisoformat(data_geracao_str)
                segundos_passados = (datetime.now() - dt_erro).total_seconds()
                if segundos_passados < minutos_cooldown * 60:
                    # Ainda em cooldown, pula por enquanto (retorna True) para evitar loop rápido!
                    return True
            except Exception:
                pass

        return False

    # Se não temos a lista de arquivos registrados, considera não gerado
    arquivos = registro.get("arquivos", [])
    if not arquivos:
        return False

    # Detecta a quantidade esperada de arquivos com base no informacoes_sped
    from acs_runner import detectar_modo_sped
    _, qtd_esperada = detectar_modo_sped(informacoes_sped, registro.get("nome", ""))

    # Se a quantidade de arquivos registrados for menor que a esperada, precisa reprocessar
    if len(arquivos) < qtd_esperada:
        logger.warning(f"Empresa ID {empresa_id} registrada com apenas {len(arquivos)}/{qtd_esperada} arquivos. Reprocessando.")
        return False

    # Verifica se todos os arquivos registrados existem fisicamente e têm tamanho > 1KB (1024 bytes)
    arquivos_reais = []
    need_update = False
    for arq in arquivos:
        caminho_real = obter_caminho_real_tolerante(arq)
        if not caminho_real:
            logger.warning(f"Arquivo registrado '{arq}' não existe fisicamente. Reprocessando empresa ID {empresa_id}.")
            return False
        if caminho_real != arq:
            need_update = True
        arquivos_reais.append(caminho_real)
        
        try:
            if os.path.getsize(caminho_real) <= 1024:
                logger.warning(f"Arquivo registrado '{caminho_real}' está vazio ou muito pequeno (<1KB). Reprocessando empresa ID {empresa_id}.")
                return False
        except OSError:
            logger.warning(f"Não foi possível ler tamanho do arquivo '{caminho_real}'. Reprocessando empresa ID {empresa_id}.")
            return False

    if need_update:
        logger.info(f"Atualizando caminhos corrigidos de encoding para ID {empresa_id} em gerados.json")
        registro["arquivos"] = arquivos_reais
        _salvar(dados)

    return True


def listar_gerados() -> dict:
    """Retorna todos registros do tracking."""
    return _carregar()


# =============================================================================
# Fila de prioridade
# =============================================================================

PRIORIDADE_FILE = os.path.join(SPED_EXPORT_DIR, "prioridade.json")


def _carregar_prioridade() -> list[int]:
    """Carrega lista de IDs prioritários."""
    if not os.path.exists(PRIORIDADE_FILE):
        return []
    try:
        with open(PRIORIDADE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"JSON corrompido em {PRIORIDADE_FILE}: {e}")
        return []
    except Exception:
        return []


def _salvar_prioridade(ids: list[int]):
    """Salva lista de IDs prioritários (escrita atomica)."""
    os.makedirs(os.path.dirname(PRIORIDADE_FILE), exist_ok=True)
    tmp = PRIORIDADE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(ids, f)
    os.replace(tmp, PRIORIDADE_FILE)


def adicionar_prioridade(empresa_id: int):
    """Adiciona empresa ao topo da fila de prioridade."""
    ids = _carregar_prioridade()
    if empresa_id not in ids:
        ids.insert(0, empresa_id)
        _salvar_prioridade(ids)
        logger.info(f"Prioridade: id={empresa_id} adicionado ao topo da fila")
    else:
        logger.info(f"Prioridade: id={empresa_id} já está na fila")


def remover_prioridade(empresa_id: int):
    """Remove empresa da fila de prioridade (após processamento)."""
    ids = _carregar_prioridade()
    if empresa_id in ids:
        ids.remove(empresa_id)
        _salvar_prioridade(ids)


# =============================================================================
# Backup forcado (Reprocessar via web = dado NOVO garantido)
#
# O comando "reprocessar" marca a empresa aqui; na preparacao do proximo ciclo
# o daemon baixa um backup NOVO (pg_dump forcado, serial) ANTES de restaurar —
# senao o restore seria refeito a partir do MESMO .backup antigo em disco
# (que ainda passa na checagem contra a data_liberacao antiga).
# =============================================================================

FORCAR_BACKUP_FILE = os.path.join(SPED_EXPORT_DIR, "forcar_backup.json")


def _carregar_forcados() -> list[int]:
    if not os.path.exists(FORCAR_BACKUP_FILE):
        return []
    try:
        with open(FORCAR_BACKUP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _salvar_forcados(ids: list[int]):
    os.makedirs(os.path.dirname(FORCAR_BACKUP_FILE), exist_ok=True)
    tmp = FORCAR_BACKUP_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(ids, f)
    os.replace(tmp, FORCAR_BACKUP_FILE)


def marcar_backup_forcado(empresa_id: int):
    ids = _carregar_forcados()
    if int(empresa_id) not in ids:
        ids.append(int(empresa_id))
        _salvar_forcados(ids)
        logger.info(f"Backup forcado: id={empresa_id} marcado (proxima preparacao baixa dump novo)")


def backup_forcado(empresa_id: int) -> bool:
    return int(empresa_id) in _carregar_forcados()


def desmarcar_backup_forcado(empresa_id: int):
    ids = _carregar_forcados()
    if int(empresa_id) in ids:
        ids.remove(int(empresa_id))
        _salvar_forcados(ids)


def ordenar_por_prioridade(empresas: list[dict]) -> list[dict]:
    """Reordena lista: prioritários primeiro (ordem da fila), depois o resto."""
    ids_prio = _carregar_prioridade()
    if not ids_prio:
        return empresas

    prio_set = set(ids_prio)
    prioritarias = []
    normais = []

    for e in empresas:
        if e["id"] in prio_set:
            prioritarias.append(e)
        else:
            normais.append(e)

    # Ordena prioritárias pela ordem da fila
    prioritarias.sort(key=lambda e: ids_prio.index(e["id"]))

    if prioritarias:
        nomes = [e["nome"] for e in prioritarias]
        logger.info(f"Prioridade: {len(prioritarias)} empresa(s) na frente: {nomes}")

    return prioritarias + normais
