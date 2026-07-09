# =============================================================================
# monitor_web.py — Dashboard web de monitoramento do SpedGenerator
#
# Servidor HTTP somente leitura (stdlib, sem dependencias novas) que agrega o
# estado do sistema e serve um dashboard HTML acessivel na rede local:
#
#   http://localhost:8777          (ou http://IP-DA-MAQUINA:8777)
#
# Fontes (apenas leitura — NAO altera nada nem envia comandos):
#   C:\ACS_Exporta\daemon_state.json      — status do daemon, ciclo, proximo ciclo
#   C:\ACS_Exporta\progresso.json         — pipeline por empresa (etapas)
#   C:\ACS_Exporta\progresso_backup.json  — pg_dump em andamento / fila
#   C:\ACS_Exporta\gerados.json           — tracking de sucesso/erro
#   C:\ACS_Exporta\empresas_fila.json     — empresas Supabase (exportado pelo daemon)
#   C:\ACS_Exporta\daemon.log             — log ao vivo
#   psutil                                — CPU, RAM, disco, processos (ACS, pg_dump...)
#
# Uso:  python monitor_web.py            (ou iniciar_monitor.bat)
# =============================================================================

import json
import os
import re
import socket
import threading
import time
import uuid
from datetime import datetime, date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import psutil

from config import SPED_EXPORT_DIR, BACKUP_DIR

PORT = 8777

DAEMON_STATE_FILE = os.path.join(SPED_EXPORT_DIR, "daemon_state.json")
PROGRESSO_FILE = os.path.join(SPED_EXPORT_DIR, "progresso.json")
PROGRESSO_BACKUP_FILE = os.path.join(SPED_EXPORT_DIR, "progresso_backup.json")
GERADOS_FILE = os.path.join(SPED_EXPORT_DIR, "gerados.json")
EMPRESAS_FILA_FILE = os.path.join(SPED_EXPORT_DIR, "empresas_fila.json")
LOCK_FILE = os.path.join(SPED_EXPORT_DIR, "spedgenerator.lock")
DUMP_LOCK_FILE = os.path.join(BACKUP_DIR, "pg_dump.lock")
COMANDOS_DIR = os.path.join(SPED_EXPORT_DIR, "comandos")

# Unicas acoes que o monitor pode enfileirar (executadas pelo command_processor
# dentro do daemon — o monitor em si nao mexe em nada)
ACOES_PERMITIDAS = {"reprocessar", "reprocessar_erros", "restaurar", "pipeline_completo",
                    "gerar_parcial", "fechamento_executar", "pausar", "retomar", "parar"}
LOG_FILES = [
    os.path.join(SPED_EXPORT_DIR, "daemon.log"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "spedgenerator.log"),
]


# -----------------------------------------------------------------------------
# Coleta de dados
# -----------------------------------------------------------------------------

def _ler_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _ler_pid(path) -> int:
    try:
        with open(path, "r") as f:
            return int(f.read().strip() or 0)
    except (OSError, ValueError):
        return 0


def _tail_log(max_linhas=120) -> list[str]:
    """Le as ultimas linhas do log mais recente (seek no fim, sem carregar tudo)."""
    candidatos = [p for p in LOG_FILES if os.path.exists(p)]
    if not candidatos:
        return []
    path = max(candidatos, key=os.path.getmtime)
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            tam = f.tell()
            f.seek(max(0, tam - 96 * 1024))
            dados = f.read().decode("utf-8", errors="replace")
        linhas = dados.splitlines()
        # Filtra ruido de polling HTTP do supabase
        linhas = [l for l in linhas if "HTTP Request: GET https://" not in l]
        return linhas[-max_linhas:]
    except OSError:
        return []


def _info_processo(pid: int) -> dict | None:
    try:
        p = psutil.Process(pid)
        with p.oneshot():
            return {
                "pid": pid,
                "vivo": True,
                "cpu": p.cpu_percent(interval=0.05),
                "ram_mb": round(p.memory_info().rss / (1024 * 1024)),
                "inicio": datetime.fromtimestamp(p.create_time()).isoformat(),
            }
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def _scan_processos() -> dict:
    """Uma passada por todos os processos: ACS, pg_dump, pg_restore, postgres."""
    res = {"acs": [], "pg_dump": 0, "pg_restore": 0, "postgres": False}
    for p in psutil.process_iter(["name", "pid"]):
        try:
            nome = (p.info["name"] or "").lower()
            if nome == "gerente.exe":
                res["acs"].append(p.info["pid"])
            elif nome == "pg_dump.exe":
                res["pg_dump"] += 1
            elif nome == "pg_restore.exe":
                res["pg_restore"] += 1
            elif nome == "postgres.exe":
                res["postgres"] = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return res


def _resumo_tracking() -> dict:
    dados = _ler_json(GERADOS_FILE) or {}
    # Mapa id -> nome_base (para o botao "Restaurar banco")
    fila = _ler_json(EMPRESAS_FILA_FILE) or {}
    bases = {str(e.get("id")): (e.get("nome_base") or "").strip()
             for e in fila.get("empresas", [])}

    hoje = date.today().isoformat()
    ok_hoje = erro_hoje = 0
    itens = []
    for emp_id, reg in dados.items():
        if not isinstance(reg, dict):
            continue
        quando = reg.get("data_geracao", "")
        status = "erro" if reg.get("status") == "erro" else "ok"
        if quando.startswith(hoje):
            if status == "erro":
                erro_hoje += 1
            else:
                ok_hoje += 1
        itens.append({
            "id": emp_id,
            "nome": reg.get("nome", f"id={emp_id}"),
            "nome_base": bases.get(str(emp_id), ""),
            "status": status,
            "quando": quando,
            "motivo": reg.get("motivo", ""),
            "tentativas": reg.get("tentativas", 0),
            "arquivos": len(reg.get("arquivos") or []),
        })
    itens.sort(key=lambda x: x["quando"], reverse=True)
    return {"hoje_ok": ok_hoje, "hoje_erro": erro_hoje, "ultimos": itens[:12]}


# -----------------------------------------------------------------------------
# Comandos (escreve arquivo em C:\ACS_Exporta\comandos\ — quem executa e o
# command_processor DENTRO do daemon, com todas as verificacoes de sempre)
# -----------------------------------------------------------------------------

def criar_comando(acao: str, params: dict) -> dict:
    if acao not in ACOES_PERMITIDAS:
        return {"erro": f"Acao nao permitida: '{acao}'"}
    cmd_id = uuid.uuid4().hex[:12]
    cmd = {
        "id": cmd_id,
        "acao": acao,
        "params": params,
        "timestamp": datetime.now().isoformat(),
        "status": "pendente",
        "origem": "monitor_web",
    }
    os.makedirs(COMANDOS_DIR, exist_ok=True)
    path = os.path.join(COMANDOS_DIR, f"web_{cmd_id}.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cmd, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return {"id": cmd_id, "status": "pendente"}


def consultar_comando(cmd_id: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{12}", cmd_id or ""):
        return {"erro": "id invalido"}
    cmd = _ler_json(os.path.join(COMANDOS_DIR, f"web_{cmd_id}.json"))
    if not cmd:
        return {"erro": "comando nao encontrado"}
    return {"id": cmd_id, "status": cmd.get("status"), "resultado": cmd.get("resultado", "")}


def _resumo_empresas() -> dict:
    dados = _ler_json(EMPRESAS_FILA_FILE) or {}
    empresas = dados.get("empresas", [])
    liberadas = [e for e in empresas if e.get("status") == "liberada"]
    pendentes = [e["nome"] for e in liberadas if not e.get("gerado_local")]
    com_erro = [e["nome"] for e in liberadas if e.get("erro_local")]
    return {
        "total_liberadas": len(liberadas),
        "pendentes": pendentes[:15],
        "com_erro": com_erro[:15],
        "atualizado": dados.get("ultima_atualizacao", ""),
    }


def coletar_status() -> dict:
    # Daemon
    daemon = _ler_json(DAEMON_STATE_FILE) or {"status": "parado"}
    pid_lock = _ler_pid(LOCK_FILE)
    pid = daemon.get("pid") or pid_lock
    proc = _info_processo(pid) if pid else None
    if not proc:
        daemon["status"] = "parado"
    daemon["processo"] = proc

    # Sistema
    ram = psutil.virtual_memory()
    disco = psutil.disk_usage("C:\\")
    sistema = {
        "cpu": psutil.cpu_percent(interval=0.1),
        "ram_pct": ram.percent,
        "ram_usada_gb": round(ram.used / 1024**3, 1),
        "ram_total_gb": round(ram.total / 1024**3, 1),
        "disco_livre_gb": round(disco.free / 1024**3, 1),
        "disco_pct": disco.percent,
    }

    # Processos relevantes
    procs = _scan_processos()

    # Backup (pg_dump) + lock de serializacao
    backup = _ler_json(PROGRESSO_BACKUP_FILE) or {"status": "ocioso", "bancos": {}}
    # Normaliza nomes de banco para minusculas (o arquivo pode acumular chaves
    # duplicadas tipo 'Alianca'/'alianca', o que quebra parsers estritos)
    backup["bancos"] = {k.lower(): v for k, v in (backup.get("bancos") or {}).items()}
    pid_dump = _ler_pid(DUMP_LOCK_FILE)
    backup["lock"] = {
        "pid": pid_dump,
        "vivo": bool(pid_dump and psutil.pid_exists(pid_dump)),
    } if pid_dump else None

    # Controle operacional (ADD7): normal | pausado | parar
    try:
        from controle import obter_estado
        controle_estado = obter_estado(ignorar_cache=True)
    except Exception:
        controle_estado = "?"

    return {
        "agora": datetime.now().isoformat(),
        "controle": controle_estado,
        "daemon": daemon,
        "sistema": sistema,
        "processos": {
            "acs_rodando": bool(procs["acs"]),
            "acs_pids": procs["acs"],
            "pg_dump_qtd": procs["pg_dump"],
            "pg_restore_qtd": procs["pg_restore"],
            "postgres_rodando": procs["postgres"],
        },
        "backup": backup,
        "pipeline": _ler_json(PROGRESSO_FILE) or {},
        "tracking": _resumo_tracking(),
        "empresas": _resumo_empresas(),
        "log": _tail_log(),
    }


# -----------------------------------------------------------------------------
# Dashboard HTML (embutido — pagina unica, atualiza via fetch a cada 4s)
# -----------------------------------------------------------------------------

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SpedGenerator — Monitor</title>
<style>
  :root {
    --bg:#0f1419; --card:#1a2129; --card2:#212a35; --txt:#d8dee6; --mut:#7d8a99;
    --ok:#3ddc84; --warn:#ffb340; --err:#ff5c5c; --info:#4aa3ff; --bord:#2c3743;
  }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:var(--txt); font:14px/1.45 'Segoe UI',system-ui,sans-serif; padding:16px; }
  h1 { font-size:18px; display:flex; align-items:center; gap:10px; margin-bottom:14px; }
  h1 small { color:var(--mut); font-weight:normal; font-size:12px; }
  h2 { font-size:13px; text-transform:uppercase; letter-spacing:.06em; color:var(--mut); margin-bottom:10px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(330px,1fr)); gap:14px; }
  .card { background:var(--card); border:1px solid var(--bord); border-radius:10px; padding:14px; }
  .wide { grid-column:1 / -1; }
  .dot { width:11px; height:11px; border-radius:50%; display:inline-block; }
  .dot.ok{background:var(--ok);box-shadow:0 0 8px var(--ok)} .dot.warn{background:var(--warn)}
  .dot.err{background:var(--err);box-shadow:0 0 8px var(--err)} .dot.off{background:var(--mut)}
  .kv { display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px solid var(--bord); }
  .kv:last-child { border-bottom:none; }
  .kv b { font-weight:600; }
  .mut { color:var(--mut); }
  .ok  { color:var(--ok); } .warn { color:var(--warn); } .err { color:var(--err); } .info { color:var(--info); }
  .bar { background:var(--card2); border-radius:6px; height:8px; overflow:hidden; margin-top:4px; }
  .bar i { display:block; height:100%; background:var(--info); border-radius:6px; transition:width .6s; }
  .bar i.warn { background:var(--warn); } .bar i.err { background:var(--err); }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th { text-align:left; color:var(--mut); font-weight:600; padding:4px 8px; border-bottom:1px solid var(--bord); }
  td { padding:5px 8px; border-bottom:1px solid var(--bord); }
  tr:last-child td { border-bottom:none; }
  .badge { display:inline-block; padding:1px 9px; border-radius:10px; font-size:11.5px; font-weight:600; }
  .b-ok{background:rgba(61,220,132,.15);color:var(--ok)} .b-err{background:rgba(255,92,92,.15);color:var(--err)}
  .b-warn{background:rgba(255,179,64,.16);color:var(--warn)} .b-info{background:rgba(74,163,255,.15);color:var(--info)}
  .b-mut{background:rgba(125,138,153,.15);color:var(--mut)}
  #log { background:#0a0e12; border:1px solid var(--bord); border-radius:8px; padding:10px;
         font:12px/1.5 Consolas,monospace; height:330px; overflow-y:auto; white-space:pre-wrap; word-break:break-all; }
  #log .err { color:var(--err); } #log .warn { color:var(--warn); }
  .stale { opacity:.45; }
  #erro-conexao { display:none; background:rgba(255,92,92,.12); border:1px solid var(--err); color:var(--err);
                  padding:8px 14px; border-radius:8px; margin-bottom:12px; font-weight:600; }
  button.acao { background:var(--card2); border:1px solid var(--bord); color:var(--txt); cursor:pointer;
                border-radius:6px; padding:2px 9px; font-size:11.5px; margin-right:4px; }
  button.acao:hover { border-color:var(--info); color:var(--info); }
  button.acao:disabled { opacity:.4; cursor:wait; }
  #modal-bg { display:none; position:fixed; inset:0; background:rgba(0,0,0,.65); z-index:20;
              align-items:center; justify-content:center; }
  #modal { background:var(--card); border:1px solid var(--bord); border-radius:12px; padding:18px;
           width:min(560px, 92vw); max-height:80vh; display:flex; flex-direction:column;
           box-shadow:0 10px 40px rgba(0,0,0,.6); }
  #modal h3 { font-size:15px; margin-bottom:4px; }
  #modal-sub { color:var(--mut); font-size:12.5px; margin-bottom:10px; }
  #modal-corpo { overflow-y:auto; flex:1; margin-bottom:12px; }
  .modal-emp { border:1px solid var(--bord); border-radius:8px; padding:8px 12px; margin-bottom:6px;
               background:var(--card2); }
  .modal-emp .badge { margin:3px 4px 0 0; }
  #modal-rodape { display:flex; gap:10px; justify-content:flex-end; }
  #modal-rodape button { border-radius:7px; padding:7px 18px; font-size:13px; cursor:pointer; border:1px solid var(--bord); }
  #btn-confirmar { background:var(--info); color:#fff; border:none; font-weight:600; }
  #btn-cancelar { background:var(--card2); color:var(--txt); }
  #toast { position:fixed; bottom:18px; right:18px; max-width:420px; display:none; z-index:30;
           background:var(--card2); border:1px solid var(--bord); border-left:4px solid var(--info);
           border-radius:8px; padding:10px 14px; box-shadow:0 4px 18px rgba(0,0,0,.5); font-size:13px; }
  #toast.ok { border-left-color:var(--ok); } #toast.err { border-left-color:var(--err); }
</style>
</head>
<body>
<h1><span class="dot off" id="dot-daemon"></span> SpedGenerator — Monitor
  <small id="hdr-rede" title="Clique para copiar — endereco para outros PCs da rede"
         style="cursor:pointer" onclick="navigator.clipboard.writeText(this.textContent.replace('Rede: ',''));this.textContent='copiado!';setTimeout(()=>this.textContent='Rede: {{URL_REDE}}',1200)">Rede: {{URL_REDE}}</small>
  <small id="hdr-info"></small>
  <small style="margin-left:auto" id="hdr-hora"></small>
</h1>
<div id="erro-conexao">Sem conexao com o monitor — verificando...</div>
<div id="toast"></div>
<div id="modal-bg">
  <div id="modal">
    <h3 id="modal-titulo"></h3>
    <div id="modal-sub"></div>
    <div id="modal-corpo"></div>
    <div id="modal-rodape">
      <button id="btn-cancelar" onclick="fecharModal()">Cancelar</button>
      <button id="btn-confirmar" onclick="confirmarLote()">Confirmar e executar</button>
    </div>
  </div>
</div>

<div class="grid">
  <div class="card">
    <h2>Daemon</h2>
    <div id="card-daemon"></div>
  </div>
  <div class="card">
    <h2>Maquina</h2>
    <div id="card-sistema"></div>
  </div>
  <div class="card">
    <h2>Processos / Automacao <span id="ctl-estado" style="font-size:12px;margin-left:8px"></span></h2>
    <div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap">
      <button class="acao" onclick="comandoControle('pausar')"
              title="Segura o pipeline no proximo checkpoint (entre etapas) — a etapa em andamento termina, nada e corrompido">&#10074;&#10074; Pausar</button>
      <button class="acao" onclick="comandoControle('retomar')"
              title="Volta a processar (apos Pausar ou Parar)">&#9654; Retomar</button>
      <button class="acao" onclick="comandoControle('parar')"
              title="Encerra o ACS imediatamente, aborta o restante do ciclo e deixa o daemon ocioso ate Retomar">&#9632; Parar</button>
    </div>
    <div id="card-procs"></div>
  </div>
  <div class="card">
    <h2>Backup remoto (pg_dump)</h2>
    <div id="card-backup"></div>
  </div>
  <div class="card wide">
    <h2>Pipeline do ciclo atual</h2>
    <div id="card-pipeline"></div>
  </div>
  <div class="card wide">
    <h2>Central de empresas</h2>
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:8px">
      <input id="busca" placeholder="Buscar empresa, base ou ID..." style="flex:1;min-width:220px;background:var(--card2);
             border:1px solid var(--bord);color:var(--txt);border-radius:6px;padding:5px 10px">
      <select id="filtro-sit" style="background:var(--card2);border:1px solid var(--bord);color:var(--txt);border-radius:6px;padding:5px">
        <option value="">Todas situacoes</option>
        <option>PENDENTE</option><option>ERRO</option><option>FALHA_DEFINITIVA</option><option>BLOQUEADO</option>
        <option>CONCLUIDO</option><option>AGUARDANDO_LIBERACAO</option>
        <option>AGUARDANDO_BACKUP</option><option>BACKUP_DESATUALIZADO</option>
        <option>BAIXANDO_BACKUP</option><option>RESTAURANDO</option><option>NA_FILA</option>
        <option>GERANDO</option><option>ADIADO</option><option>IGNORADO</option>
      </select>
      <label class="mut"><input type="checkbox" id="f-liberadas"> so liberadas</label>
      <label class="mut"><input type="checkbox" id="f-erro"> com erro</label>
      <span class="mut" id="central-info"></span>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:8px;
                background:var(--card2);border-radius:8px;padding:7px 10px">
      <b id="sel-info">0 selecionada(s)</b>
      <button class="acao" onclick="acaoLote('reprocessar')" title="Limpa o tracking, FORCA backup novo da nuvem e recoloca na fila — restore e geracao refeitos do zero">&#8635; Reprocessar</button>
      <button class="acao" onclick="acaoLote('pipeline_completo')" title="Forca download de backup NOVO (1 por vez) e depois roda o pipeline inteiro">&#9654; Pipeline completo</button>
      <button class="acao" onclick="reprocessarErros()" title="Recoloca na fila TODAS as empresas com erro no tracking (inclusive falhas definitivas) — sem precisar selecionar uma a uma">&#8635;&#8635; Refazer todos com erro</button>
      <span style="border-left:1px solid var(--bord);padding-left:10px">
        Parcial:
        <label><input type="checkbox" class="step" value="FISCAL"> Fiscal</label>
        <label><input type="checkbox" class="step" value="FISCAL_A"> Fiscal A</label>
        <label><input type="checkbox" class="step" value="FISCAL_B"> Fiscal B</label>
        <label><input type="checkbox" class="step" value="INVENTARIO"> Inventario</label>
        <label><input type="checkbox" class="step" value="COMITENS"> Com itens</label>
        <label><input type="checkbox" class="step" value="SEMITENS"> Sem itens</label>
        <label><input type="checkbox" class="step" value="CONTRIB"> Contribuicoes</label>
        <button class="acao" onclick="acaoLote('gerar_parcial')" title="Gera APENAS os steps marcados, reutilizando os fluxos existentes do ACS">Gerar parcial</button>
      </span>
    </div>
    <div style="max-height:420px;overflow:auto" id="central-tabela"></div>
  </div>
  <div class="card">
    <h2>Empresas liberadas</h2>
    <div id="card-empresas"></div>
  </div>
  <div class="card">
    <h2>Ultimos resultados (tracking)</h2>
    <div id="card-tracking"></div>
  </div>
  <div class="card">
    <h2>Fechamento mensal</h2>
    <div class="mut" style="margin-bottom:8px;font-size:12.5px">
      Arquiva o mes encerrado em Historico\\{ano}\\{mes}.zip, limpa a area operacional e
      remove bancos _local nao-protegidos. Roda sozinho todo dia 1&ordm;.
      Backups em C:\\Backups_Novo NUNCA sao tocados.
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button class="acao" onclick="fechamentoSimular()" title="Mostra o que seria arquivado/removido — nao altera nada">&#128269; Simular</button>
      <button class="acao" onclick="fechamentoExecutar()" title="Executa o fechamento de verdade (pede confirmacao)">&#128230; Executar fechamento</button>
      <button class="acao" onclick="fechamentoHistorico()" title="Zips e relatorios ja gerados">&#128194; Historico</button>
    </div>
    <div id="card-fechamento" class="mut" style="margin-top:8px"></div>
  </div>
  <div class="card wide">
    <h2>Log ao vivo</h2>
    <div id="log"></div>
  </div>
</div>

<script>
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmtHora = iso => iso ? iso.replace('T',' ').slice(0,19) : '—';

function barra(pct, limWarn=75, limErr=90) {
  const cls = pct >= limErr ? 'err' : pct >= limWarn ? 'warn' : '';
  return `<div class="bar"><i class="${cls}" style="width:${Math.min(pct,100)}%"></i></div>`;
}
function kv(rotulo, valor) { return `<div class="kv"><span class="mut">${rotulo}</span><b>${valor}</b></div>`; }

const ETAPAS = {
  pendente:    ['b-mut',  'Pendente'],
  backup:      ['b-warn', 'Baixando backup'],
  restaurando: ['b-warn', 'Restaurando'],
  corrigindo:  ['b-info', 'Corrigindo banco'],
  aguardando:  ['b-info', 'Pronta p/ gerar'],
  gerando:     ['b-info', 'Gerando SPED'],
  concluido:   ['b-ok',   'Concluido'],
  erro:        ['b-err',  'Erro'],
};

function render(d) {
  $('hdr-hora').textContent = fmtHora(d.agora);

  // --- Daemon ---
  const dm = d.daemon, proc = dm.processo;
  const stMap = { rodando:['ok','RODANDO'], aguardando:['ok','AGUARDANDO'], parado:['err','PARADO'], erro_fatal:['err','ERRO FATAL'] };
  const [stCls, stTxt] = stMap[dm.status] || ['warn', (dm.status||'?').toUpperCase()];
  $('dot-daemon').className = 'dot ' + (stCls === 'ok' ? 'ok' : stCls === 'err' ? 'err' : 'warn');
  $('hdr-info').textContent = stTxt + (dm.status==='aguardando' && dm.proximo_ciclo ? ` · proximo ciclo ${dm.proximo_ciclo}` : '');
  $('card-daemon').innerHTML =
    kv('Status', `<span class="${stCls}">${stTxt}</span>`) +
    kv('Ciclos completos', dm.ciclos_completos ?? '—') +
    kv('Proximo ciclo', dm.proximo_ciclo || '—') +
    kv('Ultimo resultado', esc(dm.ultimo_resultado || '—')) +
    (proc ? kv('PID / RAM / CPU', `${proc.pid} · ${proc.ram_mb} MB · ${proc.cpu}%`) +
            kv('Iniciado em', fmtHora(proc.inicio)) : kv('Processo', '<span class="err">nao encontrado</span>')) +
    kv('Ultima atualizacao', fmtHora(dm.ultima_atualizacao));

  // --- Sistema ---
  const s = d.sistema;
  $('card-sistema').innerHTML =
    kv('CPU', s.cpu + '%') + barra(s.cpu) +
    kv('RAM', `${s.ram_usada_gb} / ${s.ram_total_gb} GB (${s.ram_pct}%)`) + barra(s.ram_pct) +
    kv('Disco C: livre', `${s.disco_livre_gb} GB (${s.disco_pct}% usado)`) + barra(s.disco_pct, 80, 92);

  // --- Processos ---
  const p = d.processos;
  $('card-procs').innerHTML =
    kv('ACS Gerente', p.acs_rodando ? `<span class="ok">ABERTO</span> (PID ${p.acs_pids.join(', ')})` : '<span class="mut">fechado</span>') +
    kv('pg_dump ativos', p.pg_dump_qtd > 1 ? `<span class="err">${p.pg_dump_qtd} (CONCORRENTES!)</span>`
                          : p.pg_dump_qtd === 1 ? '<span class="warn">1 (baixando)</span>' : '<span class="mut">0</span>') +
    kv('pg_restore ativos', p.pg_restore_qtd || '0') +
    kv('PostgreSQL local', p.postgres_rodando ? '<span class="ok">rodando</span>' : '<span class="err">PARADO</span>');

  // --- Backup ---
  const bk = d.backup, bancos = bk.bancos || {};
  const executando = Object.entries(bancos).filter(([,i]) => String(i.status||'').startsWith('executando'));
  const fila = Object.entries(bancos).filter(([,i]) => i.status === 'aguardando');
  let bkHtml = '';
  if (executando.length) {
    for (const [nome, i] of executando) {
      const min = Math.floor((i.elapsed||0)/60);
      bkHtml += kv(`<span class="warn">&#9660;</span> ${esc(nome)}`, `${i.tamanho_mb||0} MB · ${min} min`);
    }
  } else {
    bkHtml += kv('Download', '<span class="mut">nenhum em andamento</span>');
  }
  if (fila.length) bkHtml += kv('Na fila (1 por vez)', fila.map(([n]) => esc(n)).join(', '));
  if (bk.lock) bkHtml += kv('Trava pg_dump', bk.lock.vivo ? `PID ${bk.lock.pid}` : `<span class="warn">orfa (PID ${bk.lock.pid})</span>`);
  const errosBk = Object.entries(bancos).filter(([,i]) => i.status === 'erro').slice(0,4);
  for (const [nome, i] of errosBk) bkHtml += kv(`<span class="err">x</span> ${esc(nome)}`, `<span class="err">${esc(i.erro||'erro')}</span>`);
  $('card-backup').innerHTML = bkHtml;

  // --- Pipeline ---
  const pl = d.pipeline || {}, etapas = pl.pipeline || {};
  let plHtml = '';
  if (pl.ativo) {
    let tempo = '';
    if (pl.inicio) {
      const min = Math.max(0, Math.round((Date.now() - new Date(pl.inicio)) / 60000));
      tempo = ` <span class="mut">· inicio ${fmtHora(pl.inicio).slice(11,16)} · ${min} min decorridos</span>`;
    }
    plHtml += `<div style="margin-bottom:8px">Processando <b>${esc(pl.empresa_atual||'—')}</b>` +
              (pl.etapa ? ` — <span class="info">${esc(pl.etapa)}</span>` : '') +
              ` <span class="mut">(${pl.indice_atual||0}/${pl.total_empresas||0})</span>${tempo}</div>`;
  } else {
    plHtml += `<div style="margin-bottom:8px" class="mut">Ciclo inativo. ${esc(pl.etapa||'')}</div>`;
  }
  const linhas = Object.values(etapas);
  if (linhas.length) {
    plHtml += '<table><tr><th>Empresa</th><th>Etapa</th></tr>' + linhas.map(e => {
      const [cls, txt] = ETAPAS[e.etapa] || ['b-mut', esc(e.etapa)];
      return `<tr><td>${esc(e.nome)}</td><td><span class="badge ${cls}">${txt}</span></td></tr>`;
    }).join('') + '</table>';
  }
  $('card-pipeline').innerHTML = plHtml;

  // --- Empresas ---
  const em = d.empresas;
  $('card-empresas').innerHTML =
    kv('Liberadas no Supabase', em.total_liberadas) +
    kv('Pendentes de gerar', em.pendentes.length ? `<span class="warn">${em.pendentes.length}</span>` : '<span class="ok">0</span>') +
    (em.pendentes.length ? `<div style="margin:6px 0" class="mut">${em.pendentes.map(esc).join(', ')}</div>` : '') +
    (em.com_erro.length ? kv('Com erro local', `<span class="err">${em.com_erro.map(esc).join(', ')}</span>`) : '') +
    kv('Lista atualizada', fmtHora(em.atualizado));

  // --- Tracking (com acoes) ---
  const tk = d.tracking;
  $('card-tracking').innerHTML =
    `<div style="margin-bottom:8px">Hoje: <span class="badge b-ok">${tk.hoje_ok} OK</span> <span class="badge b-err">${tk.hoje_erro} erros</span></div>` +
    '<table><tr><th>Empresa</th><th>Status</th><th>Quando</th><th>Acoes</th></tr>' +
    tk.ultimos.map(t =>
      `<tr><td title="${esc(t.motivo)}">${esc(t.nome)}</td>` +
      `<td>${t.status==='ok' ? `<span class="badge b-ok">OK (${t.arquivos} arq)</span>`
                             : `<span class="badge b-err" title="${esc(t.motivo)}">ERRO ${t.tentativas}x</span>`}</td>` +
      `<td class="mut">${fmtHora(t.quando).slice(5,16)}</td>` +
      `<td><button class="acao" title="Limpa o tracking e recoloca na fila: o daemon refaz a checagem de data, baixa backup se preciso, restaura e gera"
            onclick="enviarComando(this,'reprocessar',{empresa_id:${JSON.stringify(t.id)},nome:'${esc(t.nome)}'})">&#8635; Fila</button>` +
      (t.nome_base ? `<button class="acao" title="Apenas pg_restore do backup local de '${esc(t.nome_base)}' (sem gerar SPED)"
            onclick="enviarComando(this,'restaurar',{banco:'${esc(t.nome_base)}'})">Restaurar</button>` : '') +
      `</td></tr>`
    ).join('') + '</table>';

  // --- Log ---
  const logEl = $('log');
  const noFim = logEl.scrollTop + logEl.clientHeight >= logEl.scrollHeight - 30;
  logEl.innerHTML = d.log.map(l => {
    const cls = /\[ERROR\]|\[CRITICAL\]/.test(l) ? 'err' : /\[WARNING\]/.test(l) ? 'warn' : '';
    return `<span class="${cls}">${esc(l)}</span>`;
  }).join('\n');
  if (noFim) logEl.scrollTop = logEl.scrollHeight;
}

// ===== Central de empresas =====
const SIT_BADGE = {
  CONCLUIDO:'b-ok', ERRO:'b-err', FALHA_DEFINITIVA:'b-err', BLOQUEADO:'b-err', GERANDO:'b-info',
  RESTAURANDO:'b-info', BAIXANDO_BACKUP:'b-warn', NA_FILA:'b-info',
  PENDENTE:'b-warn', AGUARDANDO_BACKUP:'b-warn', BACKUP_DESATUALIZADO:'b-warn', ADIADO:'b-warn',
  AGUARDANDO_LIBERACAO:'b-mut', IGNORADO:'b-mut',
};
let empresasCache = [];
const selecionadas = new Set();

function renderCentral() {
  const busca = ($('busca').value || '').toLowerCase();
  const sit = $('filtro-sit').value;
  const soLib = $('f-liberadas').checked;
  const comErro = $('f-erro').checked;

  const lista = empresasCache.filter(e => {
    if (busca && !(`${e.nome} ${e.nome_base} ${e.id}`.toLowerCase().includes(busca))) return false;
    if (sit && e.situacao !== sit) return false;
    if (soLib && e.status_supabase !== 'liberada') return false;
    if (comErro && !e.ultimo_erro) return false;
    return true;
  });

  $('central-info').textContent = `${lista.length} de ${empresasCache.length} empresa(s)`;
  $('central-tabela').innerHTML =
    '<table><tr><th></th><th>ID</th><th>Empresa</th><th>Base</th><th>Situacao</th>' +
    '<th>Liberacao</th><th>Backup</th><th>Banco local</th><th>Ult. geracao</th><th>Erro / tent.</th></tr>' +
    lista.map(e => {
      const sel = selecionadas.has(e.id) ? 'checked' : '';
      const bk = e.backup_data
        ? `${fmtHora(e.backup_data).slice(5,16)} (${e.backup_mb} MB)` +
          (e.backup_desatualizado ? ' <span class="err" title="backup anterior a liberacao">&#9888;</span>' : '')
        : '<span class="mut">sem backup</span>';
      const erroCol = e.ultimo_erro
        ? `${e.definitivo ? '<span class="err" title="FALHA DEFINITIVA: o sistema PAROU de tentar (o Gerente retorna erro). Corrija a causa e use Reprocessar.">&#9940;</span> ' : ''}<span class="err" title="${esc(e.ultimo_erro)}">${esc(e.ultimo_erro.slice(0,28))}</span> <span class="mut">${e.tentativas}x</span>`
        : (e.tentativas ? `<span class="mut">${e.tentativas}x</span>` : '');
      return `<tr>
        <td><input type="checkbox" ${sel} onchange="togSel(${e.id}, this.checked)"></td>
        <td class="mut">${e.id}</td>
        <td><a href="#" style="color:inherit" title="ver historico da empresa" onclick="verTimeline(${e.id});return false">${esc(e.nome)}</a>${e.parcial_pendente ? ' <span class="info" title="geracao parcial pendente">&#9678;</span>' : ''}</td>
        <td class="mut">${esc(e.nome_base)}</td>
        <td><span class="badge ${SIT_BADGE[e.situacao] || 'b-mut'}">${e.situacao}</span></td>
        <td class="mut">${e.data_liberacao ? fmtHora(e.data_liberacao).slice(5,16) : '—'}</td>
        <td>${bk}</td>
        <td>${e.banco_local ? '<span class="ok">&#10003;</span>' : '<span class="mut">—</span>'}</td>
        <td class="mut">${e.ultima_geracao ? fmtHora(e.ultima_geracao).slice(5,16) : '—'}</td>
        <td>${erroCol}</td>
      </tr>`;
    }).join('') + '</table>';
}

function togSel(id, on) {
  if (on) selecionadas.add(id); else selecionadas.delete(id);
  $('sel-info').textContent = `${selecionadas.size} selecionada(s)`;
}

const STEP_LABEL = {
  FISCAL: 'Fiscal', CONTRIB: 'Contribuicoes', INVENTARIO: 'Fiscal com Inventario',
  COMITENS: 'Fiscal com Itens', SEMITENS: 'Fiscal sem Itens',
  FISCAL_A: 'Fiscal A', FISCAL_B: 'Fiscal B',
};
const ACAO_ROTULO = {
  reprocessar: 'Reprocessar (fluxo completo)',
  pipeline_completo: 'Pipeline completo (backup novo + fluxo completo)',
  gerar_parcial: 'Geracao parcial',
};
let lotePendente = null;  // {acao, alvos, steps}

function acaoLote(acao) {
  if (!selecionadas.size) { toast('Selecione ao menos uma empresa na tabela.', 'err'); return; }
  const alvos = empresasCache.filter(e => selecionadas.has(e.id));
  let steps = [];
  if (acao === 'gerar_parcial') {
    steps = [...document.querySelectorAll('.step:checked')].map(c => c.value);
    if (!steps.length) { toast('Marque ao menos um step para a geracao parcial.', 'err'); return; }
  }
  lotePendente = {acao, alvos, steps};

  // Tela de verificacao: o que vai ser gerado para CADA cliente
  $('modal-titulo').textContent = ACAO_ROTULO[acao];
  $('modal-sub').textContent = `${alvos.length} cliente(s) — confira os arquivos que serao gerados antes de confirmar:`;
  let aviso = '';
  if (acao === 'pipeline_completo')
    aviso = '<div class="warn" style="margin-top:6px">&#9888; Um backup NOVO sera baixado do servidor para cada cliente (fila de 1 download por vez) antes de gerar.</div>';
  $('modal-corpo').innerHTML = alvos.map(e => {
    const stepsGerar = acao === 'gerar_parcial' ? steps : (e.steps_previstos || ['FISCAL', 'CONTRIB']);
    const info = e.informacoes_sped ? ` <span class="mut">· ${esc(e.informacoes_sped)}</span>` : '';
    return `<div class="modal-emp">
      <b>${esc(e.nome)}</b> <span class="mut">(base: ${esc(e.nome_base) || '?'} · id ${e.id})</span>${info}<br>
      ${stepsGerar.map(s => `<span class="badge b-info">${STEP_LABEL[s] || s}</span>`).join(' ')}
      <span class="mut">= ${stepsGerar.length} arquivo(s)</span>
    </div>`;
  }).join('') + aviso;
  $('btn-confirmar').style.display = '';
  $('modal-bg').style.display = 'flex';
}

function fecharModal() {
  $('modal-bg').style.display = 'none';
  $('btn-confirmar').style.display = '';
  lotePendente = null;
}

// ===== Timeline da empresa (ADD3) =====
async function verTimeline(id) {
  const e = empresasCache.find(x => x.id === id);
  if (!e) return;
  $('modal-titulo').textContent = 'Historico — ' + e.nome;
  $('modal-sub').textContent =
    `liberacao: ${e.data_liberacao ? fmtHora(e.data_liberacao) : '—'} · ` +
    `backup: ${e.backup_data || '—'}${e.backup_desatualizado ? ' (DESATUALIZADO!)' : ''} · ` +
    `ult. geracao: ${e.ultima_geracao ? fmtHora(e.ultima_geracao) : '—'} · ` +
    `tentativas hoje: ${e.tentativas || 0}`;
  $('modal-corpo').innerHTML = '<span class="mut">carregando historico...</span>';
  $('btn-confirmar').style.display = 'none';
  $('modal-bg').style.display = 'flex';
  try {
    const r = await fetch('/api/timeline?nome=' + encodeURIComponent(e.nome), {cache:'no-store'});
    const d = await r.json();
    const evs = (d.eventos || []).slice().reverse();  // mais recente primeiro
    $('modal-corpo').innerHTML = evs.length
      ? '<table><tr><th>Quando</th><th>Categoria</th><th>Evento</th></tr>' + evs.map(ev =>
          `<tr>
            <td class="mut" style="white-space:nowrap">${esc((ev.ts || '').replace('T', ' '))}</td>
            <td><span class="badge ${ev.nivel === 'erro' ? 'b-err' : 'b-mut'}">${esc(ev.categoria || '')}</span></td>
            <td class="${ev.nivel === 'erro' ? 'err' : ''}">${esc(ev.msg || '')}</td>
          </tr>`).join('') + '</table>'
      : '<span class="mut">Sem historico registrado ainda (a timeline comeca a ser gravada a partir de agora, a cada processamento).</span>';
  } catch (err) {
    $('modal-corpo').innerHTML = '<span class="err">Erro ao carregar historico.</span>';
  }
}

async function confirmarLote() {
  if (!lotePendente) return;
  const {acao, alvos, steps} = lotePendente;
  $('modal-bg').style.display = 'none';
  lotePendente = null;
  const rotulos = {reprocessar:'Reprocessar', pipeline_completo:'Pipeline completo (backup novo)', gerar_parcial:`Gerar parcial [${steps.join('+')}]`};

  let ok = 0, falha = 0;
  for (const e of alvos) {
    const params = {empresa_id: e.id, nome: e.nome};
    if (acao === 'pipeline_completo') params.banco = e.nome_base_limpo || e.nome_base;
    if (acao === 'gerar_parcial') { params.steps = steps; params.informacoes_sped = e.informacoes_sped; }
    try {
      const r = await fetch('/api/comando', {method:'POST', headers:{'Content-Type':'application/json'},
                                             body: JSON.stringify({acao, params})});
      const res = await r.json();
      if (res.erro) { falha++; continue; }
      // espera o daemon processar (poll curto)
      let st = {};
      for (let i = 0; i < 8; i++) {
        await new Promise(f => setTimeout(f, 1500));
        st = await (await fetch('/api/comando/' + res.id)).json();
        if (st.status === 'concluido' || st.status === 'erro') break;
      }
      if (st.status === 'erro') { falha++; toast(`${e.nome}: ${st.resultado}`, 'err'); }
      else ok++;
    } catch { falha++; }
  }
  selecionadas.clear();
  $('sel-info').textContent = '0 selecionada(s)';
  toast(`${rotulos[acao]}: ${ok} OK${falha ? `, ${falha} falha(s)` : ''}. Acompanhe no pipeline/log.`, falha ? 'err' : 'ok');
}

async function atualizarEmpresas() {
  try {
    const r = await fetch('/api/empresas', {cache:'no-store'});
    const d = await r.json();
    if (d.empresas) { empresasCache = d.empresas; renderCentral(); }
  } catch (e) { /* mantem cache anterior */ }
}
for (const id of ['busca','filtro-sit','f-liberadas','f-erro'])
  $(id).addEventListener('input', renderCentral);

// ===== Fechamento mensal (ADD5) =====
function abrirModalInfo(titulo, sub) {
  $('modal-titulo').textContent = titulo;
  $('modal-sub').textContent = sub || '';
  $('modal-corpo').innerHTML = '<span class="mut">carregando...</span>';
  $('btn-confirmar').style.display = 'none';
  $('modal-bg').style.display = 'flex';
}

async function fechamentoSimular() {
  abrirModalInfo('Simulacao do fechamento mensal', 'Nada sera alterado — apenas visualizacao.');
  try {
    const d = await (await fetch('/api/fechamento/simular', {cache:'no-store'})).json();
    if (d.erro) { $('modal-corpo').innerHTML = '<span class="err">' + esc(d.erro) + '</span>'; return; }
    const r = d.resumo;
    const aviso = d.ocupado ? `<div class="warn">&#9888; Sistema ocupado agora (${esc(d.ocupado)}) — execute quando ocioso.</div>` : '';
    $('modal-corpo').innerHTML =
      `<div class="modal-emp"><b>Mes a fechar: ${esc(d.mes)}</b><br>
       Zip destino: <span class="mut">${esc(d.zip_destino)}</span></div>
       <div class="modal-emp">
         Empresas a arquivar: <b>${r.empresas_arquivadas}</b> ·
         SPEDs: <b>${r.speds_arquivados}</b> ·
         Auditorias: <b>${r.auditorias_arquivadas}</b> ·
         Logs: <b>${r.logs_arquivados}</b> ·
         Screenshots: <b>${r.screenshots_arquivados}</b><br>
         Bancos _local a remover: <b>${r.bancos_candidatos}</b><br>
         Espaco a recuperar: <b>${r.espaco_total_gb} GB</b>
         <span class="mut">(${r.espaco_disco_gb} GB disco + ${r.espaco_bancos_gb} GB bancos)</span>
       </div>` +
      (d.pastas.length
        ? '<div class="modal-emp"><b>Pastas:</b><br>' + d.pastas.map(p =>
            `${esc(p.nome)} <span class="mut">(${p.arquivos} arq, ${p.mb} MB)</span>`).join('<br>') + '</div>'
        : '<div class="modal-emp mut">Nenhuma pasta para arquivar (todas tiveram atividade neste mes).</div>') +
      (d.bancos.length
        ? '<div class="modal-emp"><b>Bancos:</b><br>' + d.bancos.map(b =>
            `${esc(b.nome_db)} <span class="mut">(${b.mb} MB)</span>`).join('<br>') + '</div>'
        : '') + aviso;
  } catch (e) { $('modal-corpo').innerHTML = '<span class="err">Erro ao simular.</span>'; }
}

async function fechamentoExecutar() {
  if (!confirm('Executar o FECHAMENTO MENSAL agora?\n\nIsso vai compactar as pastas do mes encerrado, remover os originais (apos validar o zip) e dropar bancos _local nao-protegidos.\n\nDica: rode a Simulacao antes.')) return;
  try {
    const r = await fetch('/api/comando', {method:'POST', headers:{'Content-Type':'application/json'},
                                           body: JSON.stringify({acao:'fechamento_executar', params:{}})});
    const res = await r.json();
    if (res.erro) { toast('Erro: ' + res.erro, 'err'); return; }
    toast('Fechamento enviado ao daemon...', '');
    for (let i = 0; i < 10; i++) {
      await new Promise(f => setTimeout(f, 2000));
      const st = await (await fetch('/api/comando/' + res.id)).json();
      if (st.status === 'concluido') { toast(st.resultado || 'Fechamento iniciado', 'ok'); $('card-fechamento').textContent = st.resultado || ''; return; }
      if (st.status === 'erro') { toast('Falhou: ' + (st.resultado || '?'), 'err'); return; }
    }
    toast('Fechamento em andamento — acompanhe no log.', '');
  } catch (e) { toast('Erro ao enviar: ' + e, 'err'); }
}

async function fechamentoHistorico() {
  abrirModalInfo('Historico de fechamentos', 'C:\\ACS_Exporta\\Historico');
  try {
    const d = await (await fetch('/api/fechamento/historico', {cache:'no-store'})).json();
    const ex = (d.execucoes || []).slice().reverse();
    $('modal-corpo').innerHTML =
      (ex.length
        ? '<table><tr><th>Mes</th><th>Executado</th><th>Empresas</th><th>SPEDs</th><th>Bancos</th><th>GB recup.</th><th>Modo</th></tr>' +
          ex.map(e => `<tr><td>${esc(e.mes)}</td><td class="mut">${esc(e.executado_em || '').replace('T',' ')}</td>
            <td>${e.empresas_arquivadas}</td><td>${e.speds_arquivados}</td>
            <td>${e.bancos_removidos}</td><td><b>${e.espaco_recuperado_gb}</b></td>
            <td class="mut">${e.automatico ? 'auto' : 'manual'}</td></tr>`).join('') + '</table>'
        : '<div class="mut">Nenhum fechamento executado ainda.</div>') +
      (d.zips && d.zips.length
        ? '<div class="modal-emp" style="margin-top:8px"><b>Arquivos:</b><br>' +
          d.zips.map(z => `${esc(z.nome)} <span class="mut">(${z.mb} MB)</span>`).join('<br>') + '</div>'
        : '');
  } catch (e) { $('modal-corpo').innerHTML = '<span class="err">Erro ao carregar historico.</span>'; }
}

let toastTimer = null;
function toast(msg, cls) {
  const t = $('toast');
  t.textContent = msg;
  t.className = cls || '';
  t.style.display = 'block';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.style.display = 'none', 8000);
}

async function enviarComando(btn, acao, params) {
  const rotulo = acao === 'reprocessar' ? `Recolocar "${params.nome}" na fila` : `Restaurar banco "${params.banco}"`;
  if (!confirm(rotulo + '?')) return;
  btn.disabled = true;
  try {
    const r = await fetch('/api/comando', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({acao, params})
    });
    const res = await r.json();
    if (res.erro) { toast('Erro: ' + res.erro, 'err'); btn.disabled = false; return; }
    toast(rotulo + ': enviado, aguardando o daemon...', '');
    // Acompanha o resultado (restaurar pode demorar minutos — depois acompanhe no log)
    for (let i = 0; i < 20; i++) {
      await new Promise(ok => setTimeout(ok, 3000));
      const st = await (await fetch('/api/comando/' + res.id)).json();
      if (st.status === 'concluido') { toast('OK: ' + (st.resultado || rotulo), 'ok'); break; }
      if (st.status === 'erro') { toast('Falhou: ' + (st.resultado || '?'), 'err'); break; }
      if (i === 19) toast('Comando ainda executando — acompanhe no log ao vivo.', '');
    }
  } catch (e) {
    toast('Erro ao enviar comando: ' + e, 'err');
  }
  btn.disabled = false;
}

async function reprocessarErros() {
  const comErro = empresasCache.filter(e => e.ultimo_erro);
  if (!comErro.length) { toast('Nenhuma empresa com erro na central.', ''); return; }
  const nomes = comErro.map(e => e.nome).slice(0, 10).join(', ');
  if (!confirm(`Refazer TODAS as ${comErro.length} empresa(s) com erro?\n\n${nomes}${comErro.length > 10 ? '...' : ''}\n\n` +
               'Elas voltam para a fila com prioridade; o daemon refaz backup/restore/geracao no proximo ciclo.')) return;
  try {
    const r = await fetch('/api/comando', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({acao:'reprocessar_erros', params:{}})});
    const res = await r.json();
    if (res.erro) { toast('Erro: ' + res.erro, 'err'); return; }
    for (let i = 0; i < 10; i++) {
      await new Promise(ok => setTimeout(ok, 2000));
      const st = await (await fetch('/api/comando/' + res.id)).json();
      if (st.status === 'concluido') { toast(st.resultado || 'Empresas com erro de volta a fila.', 'ok'); return; }
      if (st.status === 'erro') { toast('Falhou: ' + (st.resultado || '?'), 'err'); return; }
    }
    toast('Comando enviado — o daemon processa em ate 3s (precisa estar rodando).', '');
  } catch (e) { toast('Erro: ' + e, 'err'); }
}

async function comandoControle(acao) {
  if (acao === 'parar' &&
      !confirm('PARAR o pipeline? O ACS sera encerrado, o restante do ciclo abortado, e o daemon fica ocioso ate voce clicar Retomar.')) return;
  try {
    const r = await fetch('/api/comando', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({acao, params:{origem:'monitor'}})});
    const res = await r.json();
    if (res.erro) { toast('Erro: ' + res.erro, 'err'); return; }
    for (let i = 0; i < 10; i++) {
      await new Promise(ok => setTimeout(ok, 2000));
      const st = await (await fetch('/api/comando/' + res.id)).json();
      if (st.status === 'concluido') { toast(st.resultado || acao, 'ok'); return; }
      if (st.status === 'erro') { toast('Falhou: ' + (st.resultado || '?'), 'err'); return; }
    }
    toast('Comando enviado — o daemon processa em ate 3s (precisa estar rodando).', '');
  } catch (e) { toast('Erro: ' + e, 'err'); }
}

function renderControle(c) {
  const el = $('ctl-estado'); if (!el) return;
  if (c === 'pausado') { el.textContent = 'PAUSADO'; el.style.color = '#ffb020'; }
  else if (c === 'parar') { el.textContent = 'PARADO PELO OPERADOR'; el.style.color = '#ff5050'; }
  else { el.textContent = ''; }
}

async function atualizar() {
  try {
    const r = await fetch('/api/status', {cache:'no-store'});
    const dados = await r.json();
    render(dados);
    renderControle(dados.controle);
    $('erro-conexao').style.display = 'none';
    document.body.classList.remove('stale');
  } catch (e) {
    $('erro-conexao').style.display = 'block';
    document.body.classList.add('stale');
  }
}
atualizar();
atualizarEmpresas();
setInterval(atualizar, 4000);
setInterval(atualizarEmpresas, 8000);
</script>
</body>
</html>
"""


# -----------------------------------------------------------------------------
# Servidor HTTP
# -----------------------------------------------------------------------------

def ip_local() -> str:
    """IP desta maquina na rede local (interface usada para sair, sem enviar nada)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 53))
            return s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "localhost"


class MonitorHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/status"):
            try:
                corpo = json.dumps(coletar_status(), ensure_ascii=False).encode("utf-8")
                self._responder(200, "application/json; charset=utf-8", corpo)
            except Exception as e:
                erro = json.dumps({"erro": str(e)}).encode("utf-8")
                self._responder(500, "application/json; charset=utf-8", erro)
        elif self.path.startswith("/api/empresas"):
            try:
                from central_service import listar_empresas_completo
                corpo = json.dumps(listar_empresas_completo(), ensure_ascii=False).encode("utf-8")
                self._responder(200, "application/json; charset=utf-8", corpo)
            except Exception as e:
                self._responder(500, "application/json; charset=utf-8",
                                json.dumps({"erro": str(e)}).encode("utf-8"))
        elif self.path.startswith("/api/timeline"):
            try:
                from urllib.parse import urlparse, parse_qs
                qs = parse_qs(urlparse(self.path).query)
                nome = (qs.get("nome") or [""])[0]
                from central_service import ler_timeline_empresa
                corpo = json.dumps(ler_timeline_empresa(nome), ensure_ascii=False).encode("utf-8")
                self._responder(200, "application/json; charset=utf-8", corpo)
            except Exception as e:
                self._responder(500, "application/json; charset=utf-8",
                                json.dumps({"erro": str(e)}).encode("utf-8"))
        elif self.path.startswith("/api/fechamento/"):
            try:
                from fechamento import simular_fechamento, listar_historico
                if self.path.startswith("/api/fechamento/simular"):
                    corpo = json.dumps(simular_fechamento(), ensure_ascii=False).encode("utf-8")
                else:
                    corpo = json.dumps(listar_historico(), ensure_ascii=False).encode("utf-8")
                self._responder(200, "application/json; charset=utf-8", corpo)
            except Exception as e:
                self._responder(500, "application/json; charset=utf-8",
                                json.dumps({"erro": str(e)}).encode("utf-8"))
        elif self.path.startswith("/api/comando/"):
            cmd_id = self.path.rsplit("/", 1)[-1]
            corpo = json.dumps(consultar_comando(cmd_id), ensure_ascii=False).encode("utf-8")
            self._responder(200, "application/json; charset=utf-8", corpo)
        elif self.path in ("/", "/index.html"):
            html = DASHBOARD_HTML.replace("{{URL_REDE}}", f"http://{ip_local()}:{PORT}")
            self._responder(200, "text/html; charset=utf-8", html.encode("utf-8"))
        else:
            self._responder(404, "text/plain; charset=utf-8", b"404")

    def do_POST(self):
        if self.path != "/api/comando":
            self._responder(404, "text/plain; charset=utf-8", b"404")
            return
        try:
            tam = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(tam) or b"{}")
            acao = body.get("acao", "")
            params = body.get("params") or {}
            res = criar_comando(acao, params)
            codigo = 400 if res.get("erro") else 200
            self._responder(codigo, "application/json; charset=utf-8",
                            json.dumps(res, ensure_ascii=False).encode("utf-8"))
        except Exception as e:
            self._responder(500, "application/json; charset=utf-8",
                            json.dumps({"erro": str(e)}).encode("utf-8"))

    def _responder(self, codigo, ctype, corpo):
        self.send_response(codigo)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, fmt, *args):
        pass  # silencia log de acesso (polling a cada 4s poluiria o console)


def main():
    # Sem reuse de porta: impede duas instancias do monitor escutando 8777 juntas
    ThreadingHTTPServer.allow_reuse_address = False
    servidor = ThreadingHTTPServer(("0.0.0.0", PORT), MonitorHandler)
    ip = ip_local()
    print(f"SpedGenerator Monitor rodando:")
    print(f"  Local:  http://localhost:{PORT}")
    print(f"  Rede:   http://{ip}:{PORT}")
    print("Ctrl+C para encerrar.")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nMonitor encerrado.")


if __name__ == "__main__":
    main()
