# =============================================================================
# fechamento.py — Fechamento mensal automático (ADD5)
#
# Arquiva o histórico operacional do mês encerrado em
#   C:\ACS_Exporta\Historico\{ano}\{MM_MES}.zip
# remove da área operacional o que foi arquivado, dropa bancos _local
# não-protegidos (via banco_tracker) e gera FECHAMENTO_MENSAL_{ano}_{MM}.txt.
#
# REGRAS:
#   - C:\Backups_Novo NUNCA é tocado (backups originais intactos).
#   - Originais só são removidos DEPOIS do zip validado (testzip + contagem).
#   - Nada roda com o pipeline ativo ou pg_dump/pg_restore/gerente rodando.
#   - simular=True mostra tudo sem alterar nada.
# =============================================================================

import json
import os
import logging
import zipfile
from datetime import datetime, date, timedelta

from config import SPED_EXPORT_DIR

logger = logging.getLogger(__name__)

HISTORICO_DIR = os.path.join(SPED_EXPORT_DIR, "Historico")
HISTORICO_JSON = os.path.join(HISTORICO_DIR, "fechamento_historico.json")

# Pastas de 1º nivel em C:\ACS_Exporta que NUNCA sao arquivadas/removidas
PASTAS_RESERVADAS = {"historico", "comandos", "logs", "erros", "bancos", "anteriores"}

MESES = ["", "JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO",
         "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]


def _mes_anterior(hoje: date = None) -> tuple[int, int]:
    hoje = hoje or date.today()
    primeiro = hoje.replace(day=1)
    ant = primeiro - timedelta(days=1)
    return ant.year, ant.month


def _corte_mes_atual() -> float:
    """Timestamp do 1º dia do mês corrente — tudo anterior é 'mês encerrado'."""
    hoje = date.today()
    return datetime(hoje.year, hoje.month, 1).timestamp()


def _mtime_mais_recente(pasta: str) -> float:
    mais = 0.0
    for raiz, _, arquivos in os.walk(pasta):
        for f in arquivos:
            try:
                mt = os.path.getmtime(os.path.join(raiz, f))
                if mt > mais:
                    mais = mt
            except OSError:
                pass
    return mais


def _tamanho_e_arquivos(pasta: str) -> tuple[int, int]:
    total, n = 0, 0
    for raiz, _, arquivos in os.walk(pasta):
        for f in arquivos:
            try:
                total += os.path.getsize(os.path.join(raiz, f))
                n += 1
            except OSError:
                pass
    return total, n


def sistema_ocupado() -> str:
    """Retorna motivo se o sistema estiver ocupado (fechamento deve esperar)."""
    try:
        with open(os.path.join(SPED_EXPORT_DIR, "progresso.json"), "r", encoding="utf-8") as f:
            if json.load(f).get("ativo"):
                return "pipeline de geracao ativo"
    except Exception:
        pass
    try:
        import psutil
        for p in psutil.process_iter(["name"]):
            n = (p.info["name"] or "").lower()
            if n in ("pg_dump.exe", "pg_restore.exe", "gerente.exe"):
                return f"processo '{n}' em execucao"
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# Coleta (compartilhada entre simulacao e execucao)
# ---------------------------------------------------------------------------

def _coletar() -> dict:
    corte = _corte_mes_atual()

    # 1. Pastas de postos sem atividade no mes corrente
    pastas = []
    for d in sorted(os.listdir(SPED_EXPORT_DIR)):
        caminho = os.path.join(SPED_EXPORT_DIR, d)
        if not os.path.isdir(caminho) or d.lower() in PASTAS_RESERVADAS:
            continue
        if _mtime_mais_recente(caminho) >= corte:
            continue  # teve atividade neste mes — continua operacional
        tam, n = _tamanho_e_arquivos(caminho)
        pastas.append({"nome": d, "caminho": caminho, "bytes": tam, "arquivos": n})

    # 2. Screenshots de erro antigos
    screenshots = []
    pasta_erros = os.path.join(SPED_EXPORT_DIR, "erros")
    if os.path.isdir(pasta_erros):
        for f in sorted(os.listdir(pasta_erros)):
            c = os.path.join(pasta_erros, f)
            try:
                if os.path.isfile(c) and os.path.getmtime(c) < corte:
                    screenshots.append({"nome": f, "caminho": c, "bytes": os.path.getsize(c)})
            except OSError:
                pass

    # 3. Timelines (logs/empresas) sem atividade no mes corrente
    timelines = []
    pasta_logs = os.path.join(SPED_EXPORT_DIR, "logs", "empresas")
    if os.path.isdir(pasta_logs):
        for d in sorted(os.listdir(pasta_logs)):
            c = os.path.join(pasta_logs, d)
            if os.path.isdir(c) and _mtime_mais_recente(c) < corte:
                tam, n = _tamanho_e_arquivos(c)
                timelines.append({"nome": d, "caminho": c, "bytes": tam, "arquivos": n})

    # 4. Bancos _local nao-protegidos (candidatos a drop)
    bancos = []
    try:
        from banco_tracker import sincronizar_com_pg, tamanho_banco_mb
        for nome_db, info in sincronizar_com_pg().items():
            if info.get("protegido"):
                continue
            bancos.append({"nome_db": nome_db, "mb": tamanho_banco_mb(nome_db)})
    except Exception as e:
        logger.warning(f"Fechamento: erro ao listar bancos: {e}")

    return {"pastas": pastas, "screenshots": screenshots,
            "timelines": timelines, "bancos": bancos}


def _resumo(c: dict) -> dict:
    bytes_disco = (sum(p["bytes"] for p in c["pastas"]) +
                   sum(s["bytes"] for s in c["screenshots"]) +
                   sum(t["bytes"] for t in c["timelines"]))
    mb_bancos = sum(b["mb"] for b in c["bancos"])
    speds = auditorias = 0
    for p in c["pastas"]:
        for raiz, _, arquivos in os.walk(p["caminho"]):
            for f in arquivos:
                fu = f.upper()
                if fu.startswith("AUDITORIA"):
                    auditorias += 1
                elif fu.endswith(".TXT") and ("SPED" in fu or "CONTRIBUI" in fu):
                    speds += 1
    return {
        "empresas_arquivadas": len(c["pastas"]),
        "speds_arquivados": speds,
        "auditorias_arquivadas": auditorias,
        "logs_arquivados": len(c["timelines"]),
        "screenshots_arquivados": len(c["screenshots"]),
        "bancos_candidatos": len(c["bancos"]),
        "espaco_disco_gb": round(bytes_disco / (1024 ** 3), 2),
        "espaco_bancos_gb": round(mb_bancos / 1024, 2),
        "espaco_total_gb": round(bytes_disco / (1024 ** 3) + mb_bancos / 1024, 2),
    }


def simular_fechamento() -> dict:
    """Mostra o que o fechamento faria — sem alterar NADA."""
    c = _coletar()
    ano, mes = _mes_anterior()
    return {
        "simulacao": True,
        "mes": f"{MESES[mes].capitalize()}/{ano}",
        "zip_destino": os.path.join(HISTORICO_DIR, str(ano), f"{mes:02d}_{MESES[mes]}.zip"),
        "resumo": _resumo(c),
        "pastas": [{"nome": p["nome"], "arquivos": p["arquivos"],
                    "mb": round(p["bytes"] / 1048576, 1)} for p in c["pastas"]],
        "bancos": c["bancos"],
        "ocupado": sistema_ocupado(),
    }


# ---------------------------------------------------------------------------
# Execucao
# ---------------------------------------------------------------------------

def _zip_validado(zip_path: str, itens: list[tuple[str, str]]) -> bool:
    """Cria o zip em .tmp, valida e renomeia. itens = [(caminho_abs, arcname)]."""
    tmp = zip_path + ".tmp"
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            for caminho, arcname in itens:
                z.write(caminho, arcname)
        with zipfile.ZipFile(tmp, "r") as z:
            if z.testzip() is not None:
                raise IOError("testzip falhou (entrada corrompida)")
            if len(z.namelist()) != len(itens):
                raise IOError(f"zip incompleto: {len(z.namelist())}/{len(itens)} entradas")
        # Se o zip do mes ja existe (re-execucao), mescla com nome -2.zip
        destino = zip_path
        i = 2
        while os.path.exists(destino):
            destino = zip_path[:-4] + f"-{i}.zip"
            i += 1
        os.replace(tmp, destino)
        logger.info(f"Fechamento: zip validado: {destino} ({len(itens)} arquivos)")
        return True
    except Exception as e:
        logger.error(f"Fechamento: falha ao criar zip: {e} — NADA sera removido")
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        return False


def executar_fechamento(automatico: bool = False) -> dict:
    """Executa o fechamento mensal. Retorna o relatório (dict)."""
    ocupado = sistema_ocupado()
    if ocupado:
        msg = f"Fechamento abortado: {ocupado}"
        logger.warning(msg)
        return {"erro": msg}

    ano, mes = _mes_anterior()
    marker = os.path.join(HISTORICO_DIR, f".fechado_{ano}_{mes:02d}")
    if automatico and os.path.exists(marker):
        return {"erro": f"Fechamento {mes:02d}/{ano} ja executado (automatico)"}

    c = _coletar()
    resumo = _resumo(c)
    zip_path = os.path.join(HISTORICO_DIR, str(ano), f"{mes:02d}_{MESES[mes]}.zip")

    # 1. Monta lista de itens do zip
    itens = []
    for p in c["pastas"]:
        for raiz, _, arquivos in os.walk(p["caminho"]):
            for f in arquivos:
                abs_ = os.path.join(raiz, f)
                itens.append((abs_, os.path.join(p["nome"], os.path.relpath(abs_, p["caminho"]))))
    for s in c["screenshots"]:
        itens.append((s["caminho"], os.path.join("_screenshots", s["nome"])))
    for t in c["timelines"]:
        for raiz, _, arquivos in os.walk(t["caminho"]):
            for f in arquivos:
                abs_ = os.path.join(raiz, f)
                itens.append((abs_, os.path.join("_timelines", t["nome"],
                                                 os.path.relpath(abs_, t["caminho"]))))

    # 2. Zip (so remove originais se o zip validar)
    removidos_ok = False
    if itens:
        if not _zip_validado(zip_path, itens):
            return {"erro": "Zip falhou na validacao — nenhum arquivo foi removido"}
        # 3. Remove originais arquivados
        import shutil
        for p in c["pastas"]:
            try:
                shutil.rmtree(p["caminho"])
            except Exception as e:
                logger.warning(f"Fechamento: falha ao remover '{p['nome']}': {e}")
        for s in c["screenshots"]:
            try:
                os.remove(s["caminho"])
            except OSError:
                pass
        for t in c["timelines"]:
            try:
                shutil.rmtree(t["caminho"])
            except Exception:
                pass
        removidos_ok = True
        logger.info(f"Fechamento: {len(itens)} arquivo(s) arquivados e removidos da area operacional")
    else:
        logger.info("Fechamento: nada para arquivar este mes")

    # 4. Bancos locais nao-protegidos
    bancos_dropados = []
    mb_dropados = 0.0
    try:
        from banco_tracker import dropar_banco_controlado
        for b in c["bancos"]:
            if dropar_banco_controlado(b["nome_db"], force=True):
                bancos_dropados.append(b["nome_db"])
                mb_dropados += b["mb"]
    except Exception as e:
        logger.warning(f"Fechamento: erro no drop de bancos: {e}")

    # 5. Relatorio
    agora = datetime.now()
    relatorio = {
        "mes": f"{MESES[mes].capitalize()}/{ano}",
        "executado_em": agora.isoformat(timespec="minutes"),
        "automatico": automatico,
        "zip": zip_path if itens else "",
        "empresas_arquivadas": resumo["empresas_arquivadas"],
        "speds_arquivados": resumo["speds_arquivados"],
        "auditorias_arquivadas": resumo["auditorias_arquivadas"],
        "logs_arquivados": resumo["logs_arquivados"],
        "screenshots_arquivados": resumo["screenshots_arquivados"],
        "bancos_removidos": len(bancos_dropados),
        "espaco_recuperado_gb": round(
            (resumo["espaco_disco_gb"] if removidos_ok else 0) + mb_dropados / 1024, 2),
    }

    os.makedirs(HISTORICO_DIR, exist_ok=True)
    txt = os.path.join(HISTORICO_DIR, f"FECHAMENTO_MENSAL_{ano}_{mes:02d}.txt")
    try:
        with open(txt, "w", encoding="utf-8") as f:
            f.write("\n".join([
                "=" * 50,
                f"FECHAMENTO MENSAL — {relatorio['mes']}",
                "=" * 50,
                f"Empresas Arquivadas:    {relatorio['empresas_arquivadas']}",
                f"SPEDs Arquivados:       {relatorio['speds_arquivados']}",
                f"Auditorias Arquivadas:  {relatorio['auditorias_arquivadas']}",
                f"Logs Arquivados:        {relatorio['logs_arquivados']}",
                f"Screenshots Arquivados: {relatorio['screenshots_arquivados']}",
                f"Bancos Locais Removidos:{relatorio['bancos_removidos']:>5}",
                f"  ({', '.join(bancos_dropados) or 'nenhum'})",
                f"Espaco Recuperado:      {relatorio['espaco_recuperado_gb']} GB",
                f"Arquivo Historico:      {relatorio['zip'] or '(nada arquivado)'}",
                f"Data da Operacao:       {agora.strftime('%Y-%m-%d %H:%M')}",
                f"Execucao:               {'automatica' if automatico else 'manual (painel)'}",
            ]) + "\n")
    except Exception as e:
        logger.warning(f"Fechamento: falha ao gravar relatorio txt: {e}")

    # 6. Historico json (painel) + marker
    try:
        hist = []
        if os.path.exists(HISTORICO_JSON):
            with open(HISTORICO_JSON, "r", encoding="utf-8") as f:
                hist = json.load(f)
        hist.append(relatorio)
        tmp = HISTORICO_JSON + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(hist, f, ensure_ascii=False, indent=2)
        os.replace(tmp, HISTORICO_JSON)
        with open(marker, "w") as f:
            f.write(agora.isoformat())
    except Exception as e:
        logger.warning(f"Fechamento: falha ao gravar historico: {e}")

    logger.info(f"Fechamento {relatorio['mes']} concluido: "
                f"{relatorio['empresas_arquivadas']} empresas, "
                f"{relatorio['bancos_removidos']} bancos, "
                f"{relatorio['espaco_recuperado_gb']} GB recuperados")
    return relatorio


def fechamento_automatico():
    """Chamado pelo daemon a cada ciclo: executa no dia 1º (uma vez por mês)."""
    if date.today().day != 1:
        return
    ano, mes = _mes_anterior()
    marker = os.path.join(HISTORICO_DIR, f".fechado_{ano}_{mes:02d}")
    if os.path.exists(marker):
        return
    logger.info(f"Fechamento AUTOMATICO do mes {mes:02d}/{ano} iniciando...")
    executar_fechamento(automatico=True)


def listar_historico() -> dict:
    """Zips + relatorios existentes (consumido pelo monitor web)."""
    zips = []
    relatorios = []
    if os.path.isdir(HISTORICO_DIR):
        for raiz, _, arquivos in os.walk(HISTORICO_DIR):
            for f in sorted(arquivos):
                c = os.path.join(raiz, f)
                if f.lower().endswith(".zip"):
                    zips.append({"nome": os.path.relpath(c, HISTORICO_DIR),
                                 "mb": round(os.path.getsize(c) / 1048576, 1)})
                elif f.startswith("FECHAMENTO_MENSAL"):
                    relatorios.append(f)
    execucoes = []
    try:
        with open(HISTORICO_JSON, "r", encoding="utf-8") as f:
            execucoes = json.load(f)
    except Exception:
        pass
    return {"zips": zips, "relatorios": relatorios, "execucoes": execucoes[-12:]}
