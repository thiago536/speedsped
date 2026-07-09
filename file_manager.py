# =============================================================================
# file_manager.py — Move e organiza arquivos SPED gerados
# =============================================================================

import os
import shutil
import logging
from datetime import datetime
from config import SPED_EXPORT_DIR

import pyautogui

logger = logging.getLogger(__name__)


def salvar_screenshot_erro(nome_posto: str) -> str | None:
    """Captura screenshot da tela e salva em C:\\ACS_Exporta\\erros\\."""
    try:
        pasta_erros = os.path.join(SPED_EXPORT_DIR, "erros")
        os.makedirs(pasta_erros, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_limpo = _sanitizar_nome_pasta(nome_posto)
        caminho = os.path.join(pasta_erros, f"{nome_limpo}_{ts}.png")
        pyautogui.screenshot(caminho)
        logger.info(f"Screenshot salvo: {caminho}")
        return caminho
    except Exception as e:
        logger.warning(f"Falha ao salvar screenshot: {e}")
        return None


def _sanitizar_nome_pasta(nome: str) -> str:
    """Remove caracteres inválidos para nome de pasta Windows."""
    invalidos = r'\/:*?"<>|'
    for c in invalidos:
        nome = nome.replace(c, "_")
    return nome.strip()


def extrair_perfil_sped(caminho: str) -> str | None:
    """
    Extrai letra do perfil (A, B, C...) da linha |0000| do arquivo SPED.
    Formato: |0000|...|PERFIL|1|  — perfil é o campo 14 (0-indexed campos[14] se split por |).
    Retorna None se não encontrar.
    """
    try:
        with open(caminho, "r", encoding="latin-1") as f:
            primeira_linha = f.readline().strip()
        if "|0000|" not in primeira_linha:
            return None
        campos = primeira_linha.split("|")
        # Registro 0000 tem o campo IND_PERFIL na 14ª posição (1-based), que é campos[14] (campos[0] é '')
        if len(campos) > 14:
            perfil = campos[14].strip()
            if len(perfil) == 1 and perfil.isalpha():
                return perfil.upper()
        
        # Fallback para o comportamento anterior de campos_limpos caso o layout varie
        campos_limpos = [c for c in campos if c != ""]
        if len(campos_limpos) >= 3:
            perfil = campos_limpos[-2]  # penúltimo campo (último é '1')
            if len(perfil) == 1 and perfil.isalpha():
                return perfil.upper()
        return None
    except Exception:
        return None


def obter_arquivos_validos_existentes(nome_posto: str, cnpjs_esperados: list[str] | None = None) -> dict[str, str]:
    """
    Varre a pasta final do posto em C:\\ACS_Exporta\\{nome_posto}\\ e retorna
    um dicionario {sufixo: caminho_completo} de todos os arquivos SPED que ja existem
    e sao validos.
    """
    nome_limpo = _sanitizar_nome_pasta(nome_posto)
    pasta = os.path.join(SPED_EXPORT_DIR, nome_limpo)
    if not os.path.exists(pasta):
        return {}
        
    validos = {}
    from acs_runner import _extrair_sufixo
    for f in os.listdir(pasta):
        caminho = os.path.join(pasta, f)
        if os.path.isfile(caminho) and f.lower().endswith(".txt"):
            sufixo = _extrair_sufixo(f)
            if sufixo:
                perfil_esp = _detectar_perfil_esperado(f)
                if validar_arquivo_sped(caminho, perfil_esperado=perfil_esp, cnpjs_esperados=cnpjs_esperados):
                    validos[sufixo] = caminho
    return validos



def arquivar_speds_antigos(nome_posto: str, steps: set[str] | None = None) -> int:
    """
    Move os arquivos SPED ja existentes na pasta final do posto para a subpasta
    'anteriores\\YYYYMMDD_HHMMSS\\' (NUNCA apaga). Usado pelo reprocessamento
    manual: sem isso, os arquivos antigos seriam reaproveitados e o sistema
    marcaria sucesso SEM abrir o ACS (falso sucesso).

    steps=None  -> arquiva todos os SPED + AUDITORIA_GERACAO.txt (regeracao total)
    steps={...} -> arquiva apenas os arquivos desses steps (geracao parcial)
    Retorna a quantidade de arquivos movidos.
    """
    if not (nome_posto or "").strip():
        return 0  # nunca operar na raiz de C:\ACS_Exporta
    from acs_runner import _extrair_sufixo
    pasta = os.path.join(SPED_EXPORT_DIR, _sanitizar_nome_pasta(nome_posto))
    if not os.path.isdir(pasta):
        return 0

    destino = None
    movidos = 0
    for f in list(os.listdir(pasta)):
        caminho = os.path.join(pasta, f)
        if not os.path.isfile(caminho) or not f.lower().endswith(".txt"):
            continue
        sufixo = _extrair_sufixo(f)
        eh_auditoria = f.upper().startswith("AUDITORIA")
        if steps is None:
            if sufixo is None and not eh_auditoria:
                continue  # .txt desconhecido: nao mexe
        else:
            if eh_auditoria or sufixo not in steps:
                continue
        if destino is None:
            destino = os.path.join(pasta, "anteriores", datetime.now().strftime("%Y%m%d_%H%M%S"))
            os.makedirs(destino, exist_ok=True)
        try:
            shutil.move(caminho, os.path.join(destino, f))
            movidos += 1
        except Exception as e:
            logger.warning(f"Falha ao arquivar '{f}': {e}")

    if movidos:
        logger.info(f"'{nome_posto}': {movidos} arquivo(s) antigos arquivados em '{destino}'")
    return movidos


def arquivar_speds_antigos(nome_posto: str, steps: set[str] | None = None) -> int:
    """
    Move os arquivos SPED ja existentes na pasta final do posto para a subpasta
    'anteriores\\YYYYMMDD_HHMMSS\\' (NUNCA apaga). Usado pelo reprocessamento
    manual: sem isso, os arquivos antigos seriam reaproveitados e o sistema
    marcaria sucesso SEM abrir o ACS (falso sucesso).

    steps=None  -> arquiva todos os SPED + AUDITORIA_GERACAO.txt (regeracao total)
    steps={...} -> arquiva apenas os arquivos desses steps (geracao parcial)
    Retorna a quantidade de arquivos movidos.
    """
    if not (nome_posto or "").strip():
        return 0  # nunca operar na raiz de C:\ACS_Exporta
    from acs_runner import _extrair_sufixo
    pasta = os.path.join(SPED_EXPORT_DIR, _sanitizar_nome_pasta(nome_posto))
    if not os.path.isdir(pasta):
        return 0

    destino = None
    movidos = 0
    for f in list(os.listdir(pasta)):
        caminho = os.path.join(pasta, f)
        if not os.path.isfile(caminho) or not f.lower().endswith(".txt"):
            continue
        sufixo = _extrair_sufixo(f)
        eh_auditoria = f.upper().startswith("AUDITORIA")
        if steps is None:
            if sufixo is None and not eh_auditoria:
                continue  # .txt desconhecido: nao mexe
        else:
            if eh_auditoria or sufixo not in steps:
                continue
        if destino is None:
            destino = os.path.join(pasta, "anteriores", datetime.now().strftime("%Y%m%d_%H%M%S"))
            os.makedirs(destino, exist_ok=True)
        try:
            shutil.move(caminho, os.path.join(destino, f))
            movidos += 1
        except Exception as e:
            logger.warning(f"Falha ao arquivar '{f}': {e}")

    if movidos:
        logger.info(f"'{nome_posto}': {movidos} arquivo(s) antigos arquivados em '{destino}'")
    return movidos


def extrair_cnpj_sped(caminho: str) -> str | None:
    """
    Extrai CNPJ (14 dígitos) da linha |0000| do arquivo SPED.
    Busca primeiro campo com exatamente 14 dígitos numéricos.
    Funciona pra Fiscal e Contribuições (posições diferentes).
    """
    try:
        with open(caminho, "r", encoding="latin-1") as f:
            primeira_linha = f.readline().strip()
        if "|0000|" not in primeira_linha:
            return None
        for campo in primeira_linha.split("|"):
            campo = campo.strip()
            if len(campo) == 14 and campo.isdigit():
                return campo
        return None
    except Exception:
        return None


def extrair_periodo_sped(caminho: str) -> tuple[str, str] | None:
    """
    Extrai período (DT_INI, DT_FIM) da linha |0000| no formato DDMMYYYY.
    Retorna tupla (dt_ini, dt_fim) ou None.
    """
    try:
        with open(caminho, "r", encoding="latin-1") as f:
            primeira_linha = f.readline().strip()
        if "|0000|" not in primeira_linha:
            return None
        datas = []
        for campo in primeira_linha.split("|"):
            campo = campo.strip()
            if len(campo) == 8 and campo.isdigit():
                dd, mm = int(campo[:2]), int(campo[2:4])
                if 1 <= dd <= 31 and 1 <= mm <= 12:
                    datas.append(campo)
        if len(datas) >= 2:
            return (datas[0], datas[1])
        return None
    except Exception:
        return None


def validar_arquivo_sped(caminho: str, perfil_esperado: str | None = None,
                          cnpjs_esperados: list[str] | None = None) -> bool:
    """
    Valida arquivo SPED com checagens:
      1. Header |0000| presente
      2. Footer |9999| presente
      3. Contagem de registros (|9999| QTD_LIN vs linhas reais)
      4. Tamanho mínimo (1024 bytes)
      5. Perfil (A/B/C) se esperado
      6. CNPJ bate com banco local (se cnpjs_esperados informado)
      7. Log período para auditoria
    """
    nome_arq = os.path.basename(caminho)
    try:
        # --- Leitura única: header, footer, contagem ---
        with open(caminho, "r", encoding="latin-1") as f:
            primeira_linha = f.readline()
            if "|0000|" not in primeira_linha:
                logger.error(f"[VALIDAÇÃO] Header |0000| ausente: {nome_arq}")
                return False

            num_linhas = 1
            ultima_linha = ""
            for linha in f:
                num_linhas += 1
                if linha.strip():
                    ultima_linha = linha.strip()

            # Footer |9999|
            campos = ultima_linha.split("|")
            campos_limpos = [c for c in campos if c != ""]
            if not campos_limpos or campos_limpos[0] != "9999":
                logger.error(f"[VALIDAÇÃO] Registro |9999| ausente no final: {nome_arq}")
                return False

            # Contagem de registros: |9999|QTD_LIN| → campos_limpos[1]
            if len(campos_limpos) >= 2 and campos_limpos[1].isdigit():
                qtd_declarada = int(campos_limpos[1])
                diferenca = abs(qtd_declarada - num_linhas)
                if diferenca == 0:
                    logger.info(f"[VALIDAÇÃO] Contagem OK: {num_linhas} registros em {nome_arq}")
                elif diferenca <= 2:
                    # Tolerância pra trailing newlines
                    logger.warning(f"[VALIDAÇÃO] Contagem quase: declarado={qtd_declarada}, contado={num_linhas} em {nome_arq}")
                else:
                    logger.error(f"[VALIDAÇÃO] Contagem DIVERGE: declarado={qtd_declarada}, contado={num_linhas} em {nome_arq}")
                    return False

        # --- Tamanho mínimo ---
        tamanho = os.path.getsize(caminho)
        if tamanho < 1024:
            logger.error(f"[VALIDAÇÃO] Muito pequeno ({tamanho} bytes): {nome_arq}")
            return False

        # --- Perfil ---
        if perfil_esperado:
            perfil_real = extrair_perfil_sped(caminho)
            if perfil_real and perfil_real != perfil_esperado.upper():
                logger.error(f"[VALIDAÇÃO] Perfil errado: esperado='{perfil_esperado}', encontrado='{perfil_real}' em {nome_arq}")
                return False
            if perfil_real:
                logger.info(f"[VALIDAÇÃO] Perfil OK: '{perfil_real}' em {nome_arq}")

        # --- CNPJ ---
        cnpj_arquivo = extrair_cnpj_sped(caminho)
        if cnpj_arquivo:
            if cnpjs_esperados:
                if cnpj_arquivo in cnpjs_esperados:
                    logger.info(f"[VALIDAÇÃO] CNPJ OK: {cnpj_arquivo} em {nome_arq}")
                else:
                    logger.error(f"[VALIDAÇÃO] CNPJ DIVERGE: arquivo={cnpj_arquivo}, esperados={cnpjs_esperados} em {nome_arq}")
                    return False
            else:
                logger.info(f"[VALIDAÇÃO] CNPJ extraído: {cnpj_arquivo} em {nome_arq} (sem lista pra comparar)")

        # --- Período (log pra auditoria) ---
        periodo = extrair_periodo_sped(caminho)
        if periodo:
            dt_ini, dt_fim = periodo
            logger.info(f"[VALIDAÇÃO] Período: {dt_ini[:2]}/{dt_ini[2:4]}/{dt_ini[4:]} a {dt_fim[:2]}/{dt_fim[2:4]}/{dt_fim[4:]} em {nome_arq}")

        logger.info(f"[VALIDAÇÃO] APROVADO: {nome_arq} ({tamanho:,} bytes, {num_linhas} registros)")
        return True
    except Exception as e:
        logger.error(f"[VALIDAÇÃO] Erro ao validar: {nome_arq} — {e}")
        return False


def preparar_pasta_posto(nome_posto: str) -> str:
    """
    Cria pasta C:\\ACS_Exporta\\{nome_posto} se não existir.
    Retorna caminho da pasta.
    """
    nome_limpo = _sanitizar_nome_pasta(nome_posto)
    pasta = os.path.join(SPED_EXPORT_DIR, nome_limpo)
    os.makedirs(pasta, exist_ok=True)
    logger.info(f"Pasta do posto: '{pasta}'")
    return pasta


def mover_arquivos_sped(arquivos: list[str], pasta_destino: str) -> list[str]:
    """
    Move lista de arquivos para pasta_destino.
    Adiciona timestamp ao nome para evitar sobrescrever arquivos anteriores.
    Retorna lista de caminhos finais.
    """
    movidos = []
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    for arquivo in arquivos:
        if not os.path.exists(arquivo):
            logger.warning(f"Arquivo não existe para mover: {arquivo}")
            continue

        nome_original = os.path.basename(arquivo)
        nome_base, ext = os.path.splitext(nome_original)
        novo_nome = f"{nome_base}_{ts}{ext}"
        destino = os.path.join(pasta_destino, novo_nome)

        try:
            shutil.move(arquivo, destino)
            logger.info(f"Movido: '{nome_original}' -> '{destino}'")
            movidos.append(destino)
        except Exception as e:
            logger.error(f"Erro ao mover '{arquivo}': {e}")

    return movidos


def _detectar_perfil_esperado(nome_arquivo: str) -> str | None:
    """Detecta perfil esperado pelo sufixo do arquivo intermediário."""
    nome = nome_arquivo.upper()
    if "_FISCAL_A" in nome:
        return "A"
    elif "_FISCAL_B" in nome:
        return "B"
    # Contribuições e outros não têm perfil a validar
    return None


def organizar_sped_posto(nome_posto: str, arquivos_gerados: list[str],
                          cnpjs_esperados: list[str] | None = None) -> list[str]:
    """
    Pipeline: valida arquivos (incluindo perfil e CNPJ), cria pasta, move só válidos.
    Além disso, escaneia C:\\ACS_Exporta para resgatar qualquer arquivo SPED gerado
    recentemente (últimos 30 minutos) que possa ter ficado solto devido a um crash.
    Realiza de-duplicação inteligente para evitar mover cópias redundantes do mesmo arquivo.
    Retorna lista de arquivos na pasta final.
    """
    import time

    # 1. Normaliza caminhos absolutos
    arquivos_set = {os.path.abspath(a) for a in arquivos_gerados if a}

    # 2. Resgata arquivos soltos em SPED_EXPORT_DIR
    try:
        limite_tempo = time.time() - 1800  # Últimos 30 minutos
        for f in os.listdir(SPED_EXPORT_DIR):
            caminho = os.path.join(SPED_EXPORT_DIR, f)
            caminho_abs = os.path.abspath(caminho)
            if os.path.isfile(caminho_abs) and caminho_abs not in arquivos_set:
                fl = f.lower()
                # Verifica se é um arquivo SPED ou Contribuições
                if fl.endswith(".txt") and any(p in fl for p in ["sped", "contribui", "spedefd"]):
                    # Verifica se o arquivo foi criado/modificado recentemente
                    if os.path.getmtime(caminho_abs) > limite_tempo:
                        logger.info(f"Resgatando arquivo solto detectado em '{SPED_EXPORT_DIR}': '{f}'")
                        arquivos_set.add(caminho_abs)
    except Exception as e:
        logger.warning(f"Erro ao tentar resgatar arquivos soltos de '{SPED_EXPORT_DIR}': {e}")

    # 3. Valida estrutura básica de cada arquivo
    validos = []
    for arq in arquivos_set:
        perfil_esp = _detectar_perfil_esperado(os.path.basename(arq))
        if validar_arquivo_sped(arq, perfil_esperado=perfil_esp, cnpjs_esperados=cnpjs_esperados):
            validos.append(arq)
        else:
            logger.warning(f"Arquivo SPED descartado (inválido): {arq}")

    # 4. De-duplicação inteligente baseada em assinatura (Tamanho + Header + Footer)
    # Ordena por prioridade de sufixo para garantir que o mais específico permaneça
    def obter_peso_nome(caminho):
        nome = os.path.basename(caminho).upper()
        if "_FISCAL_B" in nome: return 1
        if "_FISCAL_A" in nome: return 1
        if "_CONTRIB" in nome: return 1
        if "_INVENTARIO" in nome: return 1
        if "_COMITENS" in nome: return 1
        if "_SEMITENS" in nome: return 1
        if "_FISCAL" in nome: return 2
        return 3  # sem sufixo

    validos.sort(key=obter_peso_nome)

    deduplicados = []
    assinaturas_conteudos = {}  # (tamanho, primeira_linha, ultima_linha) -> caminho

    for arq in validos:
        try:
            tamanho = os.path.getsize(arq)
            with open(arq, "r", encoding="latin-1") as f:
                primeira = f.readline().strip()
                ultima = ""
                for linha in f:
                    if linha.strip():
                        ultima = linha.strip()

            assinatura = (tamanho, primeira, ultima)
            if assinatura in assinaturas_conteudos:
                logger.info(f"Removendo duplicata redundante: '{os.path.basename(arq)}' "
                            f"(ja representado por '{os.path.basename(assinaturas_conteudos[assinatura])}')")
                try:
                    os.remove(arq)
                except Exception:
                    pass
            else:
                assinaturas_conteudos[assinatura] = arq
                deduplicados.append(arq)
        except Exception as e:
            # Em caso de erro de leitura, mantém por segurança
            deduplicados.append(arq)

    if not deduplicados:
        logger.error(f"Nenhum arquivo SPED válido localizado para '{nome_posto}'.")
        return []

    pasta = preparar_pasta_posto(nome_posto)
    return mover_arquivos_sped(deduplicados, pasta)


