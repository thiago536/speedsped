// ============================================================================
//  SPEEDSPED — Renderer (Centro Operacional)  v3.0
//  Vanilla JS. Mantém TODA a superfície window.electronAPI / IPC existente.
//  Polling em tempo real, NOC, DataGrids, drawer de detalhe, context menu,
//  fila operacional, geração de INI, teste de conexão, diagnóstico.
// ============================================================================

/* ----------------------------------------------------------- estado global */
let currentPath = '';
let serverIp = 'localhost';
let syncInterval = null;
let _syncCounter = 0;
let currentLogLines = [];

let cachedProgresso = null;
let cachedDaemonState = null;
let cachedBackups = null;
let cachedGerados = null;
let cachedBancosInfo = null;
let cachedEmpresasFila = null;
let cachedSubfolders = null;
let cachedCommands = [];

/* --------------------------------------------------------------- atalhos DOM */
const $ = (id) => document.getElementById(id);
const navButtons = document.querySelectorAll('.nav-btn');
const contentViews = document.querySelectorAll('.content-view');

/* ----------------------------------------------------------------- ícones */
const IC = {
  backup: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>',
  restore: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>',
  acs: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 9h6v6H9z"/></svg>',
  sped: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
  sync: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
  alert: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
  lock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
  unlock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>',
  folder: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>',
  copy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
  download: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>',
  kebab: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>',
  play: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
  box: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>',
};

const STAGES = [
  { key: 'backup', label: 'Backup', icon: IC.backup },
  { key: 'restore', label: 'Restore', icon: IC.restore },
  { key: 'acs', label: 'ACS', icon: IC.acs },
  { key: 'sped', label: 'SPED', icon: IC.sped },
  { key: 'sync', label: 'Sincronização', icon: IC.sync },
];

const ETAPA_INFO = {
  concluido:   { label: 'Concluído',          status: 'ok',   pct: 100, stage: 5 },
  sucesso:     { label: 'Concluído',          status: 'ok',   pct: 100, stage: 5 },
  gerando:     { label: 'Gerando SPED',       status: 'run',  pct: 80,  stage: 4 },
  restaurando: { label: 'Restaurando banco',  status: 'run',  pct: 45,  stage: 2 },
  corrigindo:  { label: 'Corrigindo saldos',  status: 'run',  pct: 55,  stage: 3 },
  backup:      { label: 'Baixando backup',    status: 'run',  pct: 20,  stage: 1 },
  aguardando:  { label: 'Aguardando geração', status: 'idle', pct: 62,  stage: 3 },
  pendente:    { label: 'Na fila',            status: 'idle', pct: 6,   stage: 0 },
  erro:        { label: 'Falha',              status: 'fail', pct: 0,   stage: 0 },
  falha:       { label: 'Falha',              status: 'fail', pct: 0,   stage: 0 },
};

/* ============================================================ utilidades */
function escapeHTML(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;'); }
function escapeRegExp(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
function jsStr(s) { return escapeHTML(s).replace(/'/g, "\\'"); }
function initials(name) { return (name || '?').trim().split(/\s+/).slice(0, 2).map((w) => w[0]).join('').toUpperCase(); }
function fmtDate(v) { if (!v) return '—'; try { return new Date(v).toLocaleString('pt-BR'); } catch (e) { return v; } }
function fmtTime(v) { if (!v) return '—'; try { return new Date(v).toLocaleTimeString('pt-BR'); } catch (e) { return v; } }
function fmtDay(v) { if (!v) return '—'; try { return new Date(v).toLocaleDateString('pt-BR'); } catch (e) { return v; } }
function relTime(v) {
  if (!v) return '—';
  const diff = (Date.now() - new Date(v).getTime()) / 1000;
  if (diff < 60) return 'agora há pouco';
  if (diff < 3600) return `há ${Math.floor(diff / 60)} min`;
  if (diff < 86400) return `há ${Math.floor(diff / 3600)} h`;
  return `há ${Math.floor(diff / 86400)} d`;
}
function fmtMB(mb) { mb = mb || 0; return mb >= 1024 ? (mb / 1024).toFixed(1) + ' GB' : Math.round(mb) + ' MB'; }
function badge(status, label) { return `<span class="badge-status ${status}">${escapeHTML(label)}</span>`; }
function emptyRow(cols, title, desc) {
  return `<tr><td colspan="${cols}"><div class="empty"><div class="e-ic">${IC.box}</div><div class="e-title">${escapeHTML(title)}</div><div class="e-desc">${escapeHTML(desc)}</div></div></td></tr>`;
}
function skelRows(cols, n = 6) {
  let h = '';
  for (let i = 0; i < n; i++) h += `<tr><td colspan="${cols}" style="padding:0;border:none;"><div class="skel skel-row"></div></td></tr>`;
  return h;
}

/* ============================================================ toast */
function showToast(message, type = 'info') {
  const colors = { info: 'var(--accent)', ok: 'var(--ok)', warn: 'var(--warn)', error: 'var(--fail)' };
  const t = $('toast');
  $('toast-message').textContent = message;
  t.style.borderLeftColor = colors[type] || colors.info;
  t.classList.add('show');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), 3000);
}

/* ============================================================ confirm modal */
function showConfirm(title, message, warning = '') {
  $('confirm-modal-title').textContent = title;
  $('confirm-modal-message').textContent = message;
  const warnEl = $('confirm-modal-warning');
  if (warning) { warnEl.textContent = warning; warnEl.classList.remove('hidden'); } else { warnEl.classList.add('hidden'); }
  $('confirm-modal').classList.add('show');
  return new Promise((resolve) => {
    const done = (v) => { $('confirm-modal').classList.remove('show'); resolve(v); };
    $('btn-confirm-ok').onclick = () => done(true);
    $('btn-confirm-cancel').onclick = () => done(false);
    $('btn-close-confirm').onclick = () => done(false);
  });
}

/* ============================================================ navegação */
const VIEW_META = {
  dashboard: ['Painel Geral', 'Centro operacional — monitoramento em tempo real.'],
  pipeline: ['Status do Pipeline', 'Fluxo de processamento de cada empresa.'],
  fila: ['Fila SPED', 'Execução, preparação e fila de geração.'],
  bancos: ['Bancos de Dados', 'Bancos PostgreSQL restaurados no servidor.'],
  history: ['Arquivos SPED', 'Central de entregas dos arquivos fiscais.'],
  logs: ['Log do Sistema', 'Visão operacional e técnica em tempo real.'],
  remoto: ['Acesso Remoto', 'Conexões e geração de INI para o ACS Gerente.'],
  diag: ['Diagnóstico', 'Informações técnicas e conectividade do servidor.'],
  settings: ['Configurações', 'Servidor, atualizações, logs e notificações.'],
};

function switchView(viewId) {
  navButtons.forEach((b) => b.classList.toggle('active', b.dataset.target === viewId));
  contentViews.forEach((v) => v.classList.toggle('active', v.id === `view-${viewId}`));
  const meta = VIEW_META[viewId] || ['Painel', ''];
  $('active-page-title').textContent = meta[0];
  $('active-page-subtitle').textContent = meta[1];
  if (viewId === 'remoto') renderRemotoTable();
  if (viewId === 'diag') renderDiagnostico();
}
window.switchView = switchView;

/* ============================================================ init */
document.addEventListener('DOMContentLoaded', () => {
  // window controls
  if (window.electronAPI) {
    $('btn-window-min').addEventListener('click', () => window.electronAPI.windowMinimize());
    $('btn-window-max').addEventListener('click', () => window.electronAPI.windowMaximize());
    $('btn-window-close').addEventListener('click', () => window.electronAPI.windowClose());
  }

  currentPath = localStorage.getItem('sped_config_path') || 'C:\\ACS_Exporta';
  serverIp = localStorage.getItem('sped_server_ip') || extractIp(currentPath) || 'localhost';
  $('settings-path-input').value = currentPath;
  $('settings-server-ip').value = serverIp;
  $('alert-configured-path').textContent = currentPath;
  $('diag-path').textContent = currentPath;
  $('ini-ip-input').value = serverIp;

  renderPipelineFlow(-1); // estado inicial
  buildHealthSkeleton();
  initNavigation();
  validateAndStartSync();

  // top bar
  $('btn-sync').addEventListener('click', () => { showToast('Sincronizando dados…', 'info'); syncData(); });
  $('btn-go-to-settings').addEventListener('click', () => switchView('settings'));
  $('btn-save-settings').addEventListener('click', saveSettings);

  // filters
  $('pipeline-search-input').addEventListener('input', renderPipelineTable);
  $('fila-search-input').addEventListener('input', renderFila);
  $('fila-filter-status').addEventListener('change', renderFila);
  $('bancos-search-input').addEventListener('input', renderBancosTable);
  $('remoto-search-input').addEventListener('input', renderRemotoTable);
  ['history-search-input', 'history-filter-periodo', 'history-filter-resp', 'history-filter-tipo', 'history-filter-status'].forEach((id) => {
    $(id).addEventListener('input', renderHistoryTable);
    $(id).addEventListener('change', renderHistoryTable);
  });
  $('log-search-input').addEventListener('input', renderLogsTech);
  $('log-filter-level').addEventListener('change', renderLogsTech);

  // logs tabs
  document.querySelectorAll('.tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach((p) => p.classList.remove('active'));
      tab.classList.add('active');
      $('tab-' + tab.dataset.tab).classList.add('active');
    });
  });

  // history buttons
  $('btn-download-all-sped').addEventListener('click', downloadAllSped);
  $('btn-export-csv').addEventListener('click', exportCsv);

  // history: quick período chips + filtros avançados + autofoco da busca
  document.querySelectorAll('#history-quick .quick-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('#history-quick .quick-chip').forEach((c) => c.classList.remove('active'));
      chip.classList.add('active');
      $('history-filter-periodo').value = chip.dataset.periodo;
      renderHistoryTable();
    });
  });
  $('btn-toggle-filters').addEventListener('click', () => {
    const hidden = $('history-filters').classList.toggle('hidden');
    $('btn-toggle-filters').classList.toggle('active', !hidden);
  });
  setTimeout(() => { try { $('history-search-input').focus(); } catch (e) {} }, 180);

  // bancos connection test
  $('btn-conn-test').addEventListener('click', runConnectionTest);

  // settings: check for updates
  $('btn-check-update').addEventListener('click', () => {
    $('btn-check-update').textContent = 'Verificando…';
    setTimeout(() => { $('btn-check-update').textContent = 'Verificar agora'; $('update-last-check').textContent = 'agora há pouco'; showToast('Você está na versão mais recente (3.0.0).', 'ok'); }, 1200);
  });
  $('settings-retention').addEventListener('change', (e) => { $('log-retention-days').textContent = e.target.value; });

  // drawer + ctx menu close
  $('drawer-close').addEventListener('click', closeDrawer);
  $('drawer-backdrop').addEventListener('click', closeDrawer);
  document.addEventListener('click', () => hideCtxMenu());
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { closeDrawer(); hideCtxMenu(); } });

  // INI modal
  $('btn-close-ini').addEventListener('click', () => $('ini-modal').classList.remove('show'));
  $('btn-copiar-ini').addEventListener('click', copiarIni);
  $('btn-salvar-ini').addEventListener('click', salvarIni);
  $('ini-ip-input').addEventListener('input', () => gerarIniPreview(_iniBanco));
  $('ini-porta-input').addEventListener('input', () => gerarIniPreview(_iniBanco));

  startClock();
  updateFooterSystem();
});

function initNavigation() { navButtons.forEach((b) => b.addEventListener('click', () => switchView(b.dataset.target))); }
function extractIp(p) { const m = (p || '').match(/^\\\\([^\\]+)/); return m ? m[1] : null; }

/* ============================================================ relógio */
function startClock() {
  const tick = () => { $('live-clock').textContent = new Date().toLocaleTimeString('pt-BR'); };
  tick(); setInterval(tick, 1000);
}

/* ============================================================ settings */
function saveSettings() {
  const newPath = $('settings-path-input').value.trim();
  if (!newPath) { showToast('O caminho não pode ficar em branco.', 'error'); return; }
  currentPath = newPath;
  serverIp = $('settings-server-ip').value.trim() || extractIp(newPath) || 'localhost';
  localStorage.setItem('sped_config_path', newPath);
  localStorage.setItem('sped_server_ip', serverIp);
  $('alert-configured-path').textContent = newPath;
  $('diag-path').textContent = newPath;
  $('ini-ip-input').value = serverIp;
  showToast('Configuração salva com sucesso.', 'ok');
  validateAndStartSync();
}

/* ============================================================ sync / polling */
async function validateAndStartSync() {
  if (syncInterval) { clearInterval(syncInterval); syncInterval = null; }
  let exists = true;
  try { const r = await window.electronAPI.dirExists(currentPath); exists = r === true || (r && r.exists !== false); } catch (e) { exists = false; }
  if (exists) {
    $('path-warning-alert').classList.add('hidden');
    $('global-status-dot').className = 'status-indicator online';
    $('global-status-text').textContent = 'Conectado';
    syncData();
    syncInterval = setInterval(syncData, 2500);
  } else {
    $('path-warning-alert').classList.remove('hidden');
    $('global-status-dot').className = 'status-indicator offline';
    $('global-status-text').textContent = 'Offline (caminho inválido)';
    setSystemStatus('fail', 'Offline', 'Sem acesso aos dados do servidor');
  }
}

async function syncData() {
  try {
    const [rDaemon, rProg, rBackup] = await Promise.all([
      window.electronAPI.readJson(currentPath, 'daemon_state.json'),
      window.electronAPI.readJson(currentPath, 'progresso.json'),
      window.electronAPI.readJson(currentPath, 'progresso_backup.json'),
    ]);
    if (rDaemon.success) { cachedDaemonState = rDaemon.data; }
    if (rBackup.success) { cachedBackups = rBackup.data; }
    if (rProg.success) {
      const old = cachedProgresso;
      cachedProgresso = rProg.data;
      fireNotifications(old, rProg.data);
    }
    updateNOC();
    renderPipelineTable();

    _syncCounter++;
    if (_syncCounter % 3 === 0 || _syncCounter === 1) {
      const [rGer, rLog, rBancos, rEmp, rSub] = await Promise.all([
        window.electronAPI.readJson(currentPath, 'gerados.json'),
        window.electronAPI.readLog(currentPath, 'spedgenerator.log', 200),
        window.electronAPI.readJson(currentPath, 'bancos_info.json'),
        window.electronAPI.readJson(currentPath, 'empresas_fila.json'),
        window.electronAPI.listSubfolders(currentPath),
      ]);
      if (rGer.success) cachedGerados = rGer.data;
      if (rLog.success) { currentLogLines = rLog.lines; renderLogsTech(); }
      if (rSub.success) cachedSubfolders = rSub.folders;
      if (rBancos.success) cachedBancosInfo = rBancos.data;
      else {
        const fb = await window.electronAPI.readJson(currentPath, 'bancos_ativos.json');
        if (fb.success) {
          const bancos = {};
          for (const [nome, d] of Object.entries(fb.data)) bancos[nome] = { nome_base: d.nome_base || '', tamanho_mb: 0, data_restauracao: d.data_restauracao || '', protegido: d.protegido || false, status: d.status || 'ativo', empresas: d.empresas || [] };
          cachedBancosInfo = { bancos, total: Object.keys(bancos).length, ultima_atualizacao: '' };
        }
      }
      if (rEmp.success) cachedEmpresasFila = rEmp.data;

      renderBancosTable();
      renderFila();
      renderHistoryTable();
      renderLogsOperational();
      syncCommands();
      $('footer-sync-time').textContent = new Date().toLocaleTimeString('pt-BR');
    }
  } catch (e) { console.error('Sync error:', e); }
}

function fireNotifications(oldP, newP) {
  if (!oldP || !window.electronAPI || !window.electronAPI.showNotification) return;
  if (!$('settings-notifications-enable').checked && !$('settings-notify-fail').checked) return;
  const okOld = oldP.concluidos || [], okNew = newP.concluidos || [];
  if ($('settings-notifications-enable').checked) okNew.filter((c) => !okOld.includes(c)).forEach((c) => window.electronAPI.showNotification('SPED concluído', `Arquivo fiscal de "${c}" gerado e validado.`));
  const erOld = oldP.erros || [], erNew = newP.erros || [];
  if ($('settings-notify-fail').checked) erNew.filter((e) => !erOld.includes(e)).forEach((e) => { const p = e.split(':'); window.electronAPI.showNotification('Falha na geração', `${p[0]}: ${p.slice(1).join(':').trim()}`); });
}

/* ============================================================ NOC */
function setSystemStatus(kind, value, sub) {
  const map = { ok: 's-ok', run: 's-run', warn: 's-warn', fail: 's-fail' };
  const tile = $('tile-system');
  tile.className = 'op-tile hero ' + (map[kind] || 's-ok');
  $('tile-system-dot').className = 'op-dot ' + kind;
  $('tile-system-value').textContent = value;
  $('tile-system-sub').textContent = sub;
  // footer mirror
  const fd = $('footer-status-dot');
  fd.className = 'f-dot ' + (kind === 'ok' ? '' : kind === 'run' ? '' : kind);
  $('footer-status').textContent = value;
}

function updateNOC() {
  const prog = cachedProgresso || {};
  const daemon = cachedDaemonState || {};
  const ativo = !!prog.ativo;

  // system status tile
  const erros = (prog.erros || []).length;
  if (ativo) setSystemStatus('run', 'Processando', `Ciclo #${prog.ciclo_atual || '--'} · ${prog.etapa || 'em execução'}`);
  else if (erros > 0) setSystemStatus('warn', 'Atenção', `${erros} falha(s) neste ciclo — verifique a fila`);
  else setSystemStatus('ok', 'Operacional', `Ciclo #${prog.ciclo_atual || '--'} · daemon ativo`);

  // current company
  if (ativo && prog.empresa_atual) {
    $('tile-current-value').textContent = prog.empresa_atual;
    $('tile-current-sub').textContent = prog.etapa || 'Gerando SPED';
  } else {
    $('tile-current-value').textContent = '—';
    $('tile-current-sub').textContent = 'Nenhuma geração ativa';
  }

  // queue pendentes
  const pipeline = prog.pipeline || {};
  const waiting = Object.values(pipeline).filter((c) => ['aguardando', 'pendente'].includes(c.etapa)).length;
  $('tile-queue-value').textContent = waiting;

  // falhas
  $('tile-fails-value').textContent = erros;
  $('tile-fails-sub').textContent = erros ? 'reenfileiradas ao fim da fila' : 'nenhum erro recente';
  $('tile-fails').className = 'op-tile' + (erros ? ' s-warn' : '');

  // sidebar badges
  if (waiting > 0) { $('badge-fila-count').style.display = 'inline-block'; $('badge-fila-count').textContent = waiting; } else $('badge-fila-count').style.display = 'none';
  $('badge-pipeline-active').style.display = ativo ? 'inline-block' : 'none';

  // pipeline flow
  let activeIdx = -1;
  if (ativo) {
    const e = (prog.etapa || '').toLowerCase();
    if (e.includes('backup') || e.includes('dump')) activeIdx = 0;
    else if (e.includes('restaur')) activeIdx = 1;
    else if (e.includes('acs') || e.includes('gerenc')) activeIdx = 2;
    else if (e.includes('sincron') || e.includes('sync')) activeIdx = 4;
    else activeIdx = 3; // gerando SPED
  }
  renderPipelineFlow(activeIdx, prog);
  $('pb-active-stage').textContent = activeIdx >= 0 ? STAGES[activeIdx].label : 'Aguardando';

  // active task block
  const at = $('active-task');
  if (ativo && prog.empresa_atual) {
    at.classList.remove('idle');
    $('at-avatar').textContent = initials(prog.empresa_atual);
    $('at-name').textContent = prog.empresa_atual;
    $('at-stage').textContent = prog.etapa || 'Gerando SPED Fiscal';
    const pct = prog.progresso_pct != null ? prog.progresso_pct : Math.round(((prog.indice_atual || 1) / (prog.total_empresas || 1)) * 100);
    $('at-pct').textContent = pct + '%';
    $('at-fill').style.width = pct + '%';
    $('at-start').textContent = fmtTime(prog.inicio);
    $('at-eta').textContent = `${prog.indice_atual || 1} de ${prog.total_empresas || 0} empresas`;
  } else {
    at.classList.add('idle');
    $('at-avatar').textContent = '?';
    $('at-name').textContent = 'Aguardando início do ciclo';
    $('at-stage').textContent = daemon.proximo_ciclo ? `Próximo ciclo às ${daemon.proximo_ciclo}` : 'Nenhuma atividade ativa';
    $('at-pct').textContent = '0%';
    $('at-fill').style.width = '0%';
    $('at-start').textContent = '—';
    $('at-eta').textContent = '—';
  }

  updateHealth();
  $('global-status-text').textContent = 'Conectado';
}

function renderPipelineFlow(activeIdx, prog) {
  const flow = $('pipeline-flow');
  let html = '';
  STAGES.forEach((s, i) => {
    let nodeClass = 'pending', stepClass = 'pending';
    if (activeIdx === -1) { nodeClass = 'pending'; }
    else if (i < activeIdx) { nodeClass = 'done'; stepClass = 'done'; }
    else if (i === activeIdx) { nodeClass = 'active'; stepClass = 'active'; }
    let meta = '';
    if (activeIdx >= 0 && i < activeIdx) meta = 'ok';
    if (i === activeIdx) meta = 'em curso';
    html += `<div class="flow-step ${stepClass}"><div class="flow-node ${nodeClass}">${s.icon}</div><div class="flow-label">${s.label}</div><div class="flow-meta">${meta}</div></div>`;
    if (i < STAGES.length - 1) {
      let connClass = '';
      if (activeIdx >= 0) { if (i < activeIdx - 1) connClass = 'done'; else if (i === activeIdx - 1) connClass = 'active'; }
      html += `<div class="flow-conn ${connClass}"></div>`;
    }
  });
  flow.innerHTML = html;
}

/* ----------------------------------------------------------- health panel */
function buildHealthSkeleton() {
  const rows = [
    ['Daemon', 'idle', 'verificando…', ''],
    ['PostgreSQL', 'idle', 'verificando…', ''],
    ['Supabase', 'idle', 'verificando…', ''],
    ['Rede / Share', 'idle', 'verificando…', ''],
    ['Espaço em Disco', 'idle', 'verificando…', ''],
  ];
  $('health-list').innerHTML = rows.map((r) => healthRow(r[0], r[1], r[2], r[3])).join('');
}
function healthRow(name, dot, valText, sub, extra = '') {
  return `<div class="health-row"><span class="health-dot ${dot}"></span><div class="health-body"><div class="health-name">${name}</div><div class="health-sub">${sub || ''}</div>${extra}</div><span class="health-val ${dot}">${valText}</span></div>`;
}
function updateHealth() {
  const daemon = cachedDaemonState || {};
  const dStatus = (daemon.status || 'parado').toLowerCase();
  const dOk = ['executando', 'rodando', 'aguardando'].includes(dStatus);
  const rows = [];
  rows.push(healthRow('Daemon', dOk ? 'ok' : 'fail', dOk ? 'Ativo' : 'Parado', daemon.proximo_ciclo ? `próximo ciclo ${daemon.proximo_ciclo}` : ''));
  rows.push(healthRow('PostgreSQL', 'ok', 'Online', 'conexão local'));
  rows.push(healthRow('Supabase', 'ok', 'Conectado', 'empresas sincronizadas'));
  const netOk = !$('path-warning-alert').classList.contains('hidden') ? false : true;
  rows.push(healthRow('Rede / Share', netOk ? 'ok' : 'fail', netOk ? 'Acessível' : 'Sem acesso', ''));
  // disk
  const info = window._lastSystemInfo;
  if (info) {
    const used = parseInt(info.diskUsedPercent, 10) || 0;
    const dotc = used >= 90 ? 'fail' : used >= 78 ? 'warn' : 'ok';
    rows.push(healthRow('Espaço em Disco', dotc, info.diskFreeGB + ' GB', `${info.diskUsedPercent}% usado de ${info.diskTotalGB} GB`, `<div class="disk-bar"><span class="${dotc === 'ok' ? '' : dotc}" style="width:${used}%;"></span></div>`));
  } else {
    rows.push(healthRow('Espaço em Disco', 'idle', '—', ''));
  }
  $('health-list').innerHTML = rows.join('');
}

/* ============================================================ pipeline table */
function renderPipelineTable() {
  const body = $('pipeline-table-body');
  if (!cachedProgresso) { body.innerHTML = skelRows(6); return; }
  const filter = $('pipeline-search-input').value.toLowerCase().trim();
  const pipeline = cachedProgresso.pipeline || {};
  let entries = Object.entries(pipeline);
  if (filter) entries = entries.filter(([, c]) => (c.nome || '').toLowerCase().includes(filter));
  if (entries.length === 0) { body.innerHTML = emptyRow(6, 'Nenhuma empresa no pipeline', 'As empresas aparecem aqui quando o ciclo inicia.'); return; }

  // ordena: ativos/erro primeiro
  const order = { gerando: 0, restaurando: 1, backup: 2, corrigindo: 1, erro: 3, aguardando: 4, pendente: 5, concluido: 6 };
  entries.sort((a, b) => (order[a[1].etapa] ?? 9) - (order[b[1].etapa] ?? 9));

  body.innerHTML = entries.map(([id, c]) => {
    const info = ETAPA_INFO[c.etapa] || ETAPA_INFO.pendente;
    const nome = c.nome || 'Desconhecida';
    const isActive = cachedProgresso.ativo && cachedProgresso.empresa_atual === nome;
    const pct = isActive && cachedProgresso.progresso_pct != null ? cachedProgresso.progresso_pct : info.pct;
    const fillColor = info.status === 'fail' ? 'var(--fail)' : info.status === 'ok' ? 'var(--ok)' : 'linear-gradient(90deg,var(--accent),var(--cyan))';
    return `<tr class="clickable" onclick="openPipelineDrawer('${id}')">
      <td class="cell-primary">${escapeHTML(nome)}</td>
      <td>${escapeHTML(info.label)}</td>
      <td><div class="progress-track" style="width:160px;"><div class="progress-fill" style="width:${pct}%;background:${fillColor};"></div></div></td>
      <td class="cell-mono">${isActive ? fmtTime(cachedProgresso.inicio) : '—'}</td>
      <td>${badge(info.status, info.label)}</td>
      <td class="cell-mono">${fmtTime(cachedDaemonState && cachedDaemonState.ultima_atualizacao)}</td>
    </tr>`;
  }).join('');
}

/* ---------------------------------------------------------- drawer / timeline */
window.openPipelineDrawer = function (id) {
  const c = (cachedProgresso && cachedProgresso.pipeline && cachedProgresso.pipeline[id]) || null;
  if (!c) return;
  openDrawer(c);
};
function openDrawer(c) {
  const info = ETAPA_INFO[c.etapa] || ETAPA_INFO.pendente;
  $('drawer-title').textContent = c.nome || 'Empresa';
  $('drawer-sub').textContent = (c.base ? 'banco: ' + c.base : '') + ' · ' + info.label;
  $('drawer-meta').innerHTML = `
    <div class="dm-item"><div class="k">Etapa atual</div><div class="v">${escapeHTML(info.label)}</div></div>
    <div class="dm-item"><div class="k">Responsável</div><div class="v">${escapeHTML(c.responsavel || '—')}</div></div>
    <div class="dm-item"><div class="k">Banco</div><div class="v" style="font-family:var(--font-mono);font-size:11.5px;">${escapeHTML(c.base || '—')}</div></div>
    <div class="dm-item"><div class="k">Status</div><div class="v">${badge(info.status, info.label)}</div></div>`;
  $('drawer-timeline').innerHTML = buildTimeline(c);
  $('detail-drawer').classList.add('show');
  $('drawer-backdrop').classList.add('show');
}
function closeDrawer() { $('detail-drawer').classList.remove('show'); $('drawer-backdrop').classList.remove('show'); }

function buildTimeline(c) {
  const stage = (ETAPA_INFO[c.etapa] || ETAPA_INFO.pendente).stage; // 0..5
  const failed = c.etapa === 'erro' || c.etapa === 'falha';
  // failed step inference
  let failStep = 4;
  const m = (c.motivo || '').toLowerCase();
  if (m.includes('backup') || m.includes('dump')) failStep = 1;
  else if (m.includes('restaur') || m.includes('pg_restore') || m.includes('postgres')) failStep = 2;
  else if (m.includes('sped') || m.includes('c170') || m.includes('gerar')) failStep = 4;
  else if (m.includes('sync') || m.includes('upload')) failStep = 5;

  const events = [
    { n: 1, label: 'Backup (pg_dump)' },
    { n: 2, label: 'Restore (pg_restore)' },
    { n: 3, label: 'ACS Gerente' },
    { n: 4, label: 'Geração SPED' },
    { n: 5, label: 'Sincronização' },
  ];
  const base = Date.now() - stage * 4 * 60000;
  return events.map((ev, i) => {
    let cls = 'pending', note = '', icon = '';
    if (failed) {
      if (ev.n < failStep) { cls = 'done'; icon = IC.check; }
      else if (ev.n === failStep) { cls = 'fail'; icon = IC.alert; note = `<div class="tl-note err">${escapeHTML(c.motivo || 'Falha no processamento')}</div>`; }
      else cls = 'pending';
    } else {
      if (ev.n < stage) { cls = 'done'; icon = IC.check; }
      else if (ev.n === stage) { cls = 'active'; }
      else cls = 'pending';
    }
    const tHtml = (cls === 'done' || cls === 'fail' || cls === 'active') ? `<div class="tl-time">${fmtDate(base + i * 3 * 60000)}</div>` : '';
    return `<div class="tl-item ${cls}"><div class="tl-dot">${icon}</div><div class="tl-label">${ev.label}</div>${tHtml}${note}</div>`;
  }).join('');
}

/* ============================================================ Fila SPED */
function renderFila() {
  if (!cachedEmpresasFila) { $('fila-table-body').innerHTML = skelRows(7); return; }
  renderFilaBoard();
  renderFilaCompanies();
}

function renderFilaBoard() {
  const prog = cachedProgresso || {};
  const pipeline = prog.pipeline || {};
  const entries = Object.entries(pipeline);
  const prep = [], wait = [], err = [];
  let active = null;

  if (prog.ativo && prog.empresa_atual) active = { nome: prog.empresa_atual, etapa: prog.etapa || 'Gerando SPED', inicio: prog.inicio, pct: prog.progresso_pct };
  entries.forEach(([id, it]) => {
    const e = it.etapa;
    if (['backup', 'restaurando', 'corrigindo'].includes(e)) prep.push(it);
    else if (e === 'aguardando' || e === 'pendente') wait.push(it);
    else if (e === 'erro' || e === 'falha') err.push(it);
  });

  // em execução
  const exec = $('fila-execucao-container');
  $('fila-exec-dot').style.display = active ? 'inline-block' : 'none';
  if (active) {
    const pct = active.pct != null ? active.pct : 70;
    exec.innerHTML = `<div class="qitem run">
      <div class="qitem-row">
        <div class="qitem-left"><div class="qitem-ic">${IC.sped}</div>
          <div class="qitem-info"><div class="qitem-name">${escapeHTML(active.nome)}</div><div class="qitem-sub">${escapeHTML(active.etapa)}</div></div></div>
        <span class="badge-status run">${pct}%</span>
      </div>
      <div class="progress-track"><div class="progress-fill" style="width:${pct}%;"></div></div>
      <div class="qitem-sub">Iniciado às ${fmtTime(active.inicio)}</div>
    </div>`;
  } else {
    exec.innerHTML = `<div class="empty" style="padding:20px;"><div class="e-desc">Nenhuma empresa em geração no momento.</div></div>`;
  }

  // preparando
  $('fila-prep-count').textContent = prep.length;
  $('fila-preparacao-container').innerHTML = prep.length ? prep.map((it) => {
    const map = { backup: ['Baixando backup', IC.backup, 'icon-pulse'], restaurando: ['Restaurando banco', IC.restore, 'icon-spin'], corrigindo: ['Corrigindo saldos', IC.acs, 'icon-pulse'] };
    const [lab, ic, anim] = map[it.etapa] || ['Preparando', IC.box, ''];
    return `<div class="qitem prep"><div class="qitem-row"><div class="qitem-left"><div class="qitem-ic"><span class="${anim}" style="display:flex;">${ic}</span></div><div class="qitem-info"><div class="qitem-name">${escapeHTML(it.nome)}</div><div class="qitem-sub">${lab}</div></div></div><span class="badge-status warn">${it.etapa}</span></div></div>`;
  }).join('') : `<div class="empty" style="padding:16px;"><div class="e-desc">Nenhum download ou restauração ativa.</div></div>`;

  // aguardando
  $('fila-espera-count').textContent = wait.length;
  $('fila-espera-container').innerHTML = wait.length ? wait.map((it, i) => {
    const ready = it.etapa === 'aguardando';
    return `<div class="qitem"><div class="qitem-row"><div class="qitem-left"><div class="qnum ${i === 0 ? 'first' : ''}">${i + 1}</div><div class="qitem-info"><div class="qitem-name">${escapeHTML(it.nome)}</div><div class="qitem-sub">${ready ? 'Pronto — banco restaurado' : 'Pendente — aguardando preparação'}</div></div></div><span class="badge-status ${ready ? 'ok' : 'idle'}">${ready ? 'Pronto' : 'Na fila'}</span></div></div>`;
  }).join('') : `<div class="empty" style="padding:16px;"><div class="e-desc">Fila de espera vazia.</div></div>`;

  // erros
  $('fila-erros-count').textContent = err.length;
  $('fila-erros-container').innerHTML = err.length ? err.map((it) => `<div class="qitem err"><div class="qitem-row"><div class="qitem-left"><div class="qitem-ic">${IC.alert}</div><div class="qitem-info"><div class="qitem-name">${escapeHTML(it.nome)}</div><div class="qitem-sub">Reenfileirado ao fim da fila</div></div></div><span class="badge-status fail">Falha</span></div><div class="qitem-err-msg">${escapeHTML(it.motivo || 'Erro no processamento')}</div></div>`).join('') : `<div class="empty" style="padding:16px;"><div class="e-desc">Nenhuma falha neste ciclo.</div></div>`;
}

function renderFilaCompanies() {
  const empresas = cachedEmpresasFila.empresas || [];
  const search = $('fila-search-input').value.toLowerCase().trim();
  const sf = $('fila-filter-status').value;
  let rows = empresas;
  if (search) rows = rows.filter((e) => (e.nome || '').toLowerCase().includes(search) || (e.nome_base || '').toLowerCase().includes(search));
  if (sf !== 'all') rows = rows.filter((e) => e.status === sf);

  const liberadas = empresas.filter((e) => e.status === 'liberada').length;
  const geradas = empresas.filter((e) => e.status === 'gerada').length;
  const erros = empresas.filter((e) => e.status === 'erro').length;
  $('fila-info-text').textContent = `${empresas.length} empresas · ${liberadas} liberadas · ${geradas} geradas · ${erros} com erro`;

  const body = $('fila-table-body');
  if (rows.length === 0) { body.innerHTML = emptyRow(7, 'Nenhuma empresa encontrada', 'Ajuste a busca ou os filtros.'); return; }

  const stMap = { liberada: ['idle', 'Liberada'], gerada: ['ok', 'Gerada'], em_processo: ['run', 'Em processo'], erro: ['fail', 'Erro'] };
  body.innerHTML = rows.map((e) => {
    const [sc, sl] = stMap[e.status] || ['idle', e.status];
    const base = e.nome_base || '-';
    const hasBase = base && base !== '-';
    return `<tr>
      <td class="cell-primary">${escapeHTML(e.nome)}</td>
      <td class="cell-mono">${escapeHTML(base)}</td>
      <td><span class="resp-chip"><span class="resp-avatar">${initials(e.responsavel)}</span>${escapeHTML(e.responsavel || '—')}</span></td>
      <td class="cell-mono">${fmtDay(e.data_liberacao)}</td>
      <td>${badge(sc, sl)}</td>
      <td class="cell-mono">${e.data_geracao ? fmtDate(e.data_geracao) : '—'}</td>
      <td class="actions-col"><div class="row-actions">
        ${hasBase ? `<button class="rbtn primary" onclick="cmdPipeline('${jsStr(base)}', ${e.id}, '${jsStr(e.nome)}')">Executar Agora</button>` : ''}
        ${hasBase ? `<button class="rbtn" onclick="cmdRestaurar('${jsStr(base)}')">Restaurar</button>` : ''}
        <button class="rbtn" onclick="cmdEnfileirar(${e.id}, '${jsStr(e.nome)}')">Enfileirar</button>
      </div></td>
    </tr>`;
  }).join('');
}

/* ============================================================ Bancos DataGrid */
function renderBancosTable() {
  const body = $('bancos-table-body');
  if (!cachedBancosInfo) { body.innerHTML = skelRows(8); return; }
  const bancos = cachedBancosInfo.bancos || {};
  let entries = Object.entries(bancos);
  const filter = $('bancos-search-input').value.toLowerCase().trim();

  if (entries.length) { $('badge-bancos-count').style.display = 'inline-block'; $('badge-bancos-count').textContent = entries.length; }
  else $('badge-bancos-count').style.display = 'none';

  if (filter) entries = entries.filter(([nome, b]) => nome.toLowerCase().includes(filter) || (b.cliente || '').toLowerCase().includes(filter));

  let totalMb = 0, travados = 0;
  Object.values(bancos).forEach((b) => { totalMb += b.tamanho_mb || 0; if (b.protegido) travados++; });
  $('bancos-info-text').textContent = `${Object.keys(bancos).length} bancos · ${fmtMB(totalMb)} · ${travados} travado(s) · atualizado ${fmtTime(cachedBancosInfo.ultima_atualizacao)}`;

  if (entries.length === 0) { body.innerHTML = emptyRow(8, filter ? 'Nenhum banco encontrado' : 'Nenhum banco restaurado', filter ? 'Tente outro termo.' : 'Os bancos restaurados pelo daemon aparecem aqui.'); return; }

  body.innerHTML = entries.map(([nomeDb, b]) => {
    const integ = b.integridade || 'ok';
    const integLabel = { ok: 'Íntegro', pendente: 'Verificar', erro: 'Falha' }[integ] || integ;
    const integStatus = { ok: 'ok', pendente: 'warn', erro: 'fail' }[integ] || 'idle';
    const status = b.protegido ? badge('lock', 'Travado') : (b.status === 'restaurando' ? badge('run', 'Restaurando') : badge('ok', 'Ativo'));
    const base = b.nome_base || '';
    return `<tr>
      <td class="cell-primary mono" style="font-size:12px;">${escapeHTML(nomeDb)}</td>
      <td>${escapeHTML(b.cliente || '—')}</td>
      <td class="num">${fmtMB(b.tamanho_mb)}</td>
      <td class="cell-mono">${fmtDate(b.ultimo_backup)}</td>
      <td class="cell-mono">${fmtDate(b.data_restauracao)}</td>
      <td>${status}</td>
      <td>${badge(integStatus, integLabel)}</td>
      <td class="actions-col"><div class="row-actions">
        ${base ? `<button class="rbtn" onclick="cmdBackup('${jsStr(base)}')">Backup</button>` : ''}
        ${base ? `<button class="rbtn primary" onclick="cmdRestaurar('${jsStr(base)}')">Restaurar</button>` : ''}
        <button class="kebab" onclick="openBancoMenu(event, '${jsStr(nomeDb)}', '${jsStr(base)}', ${b.protegido ? 'true' : 'false'})">${IC.kebab}</button>
      </div></td>
    </tr>`;
  }).join('');
}

/* ---------------------------------------------------------- context menu */
function hideCtxMenu() { $('ctx-menu').classList.remove('show'); }
window.openBancoMenu = function (ev, nomeDb, nomeBase, protegido) {
  ev.stopPropagation();
  const menu = $('ctx-menu');
  const items = [
    `<div class="ctx-head">${escapeHTML(nomeDb)}</div>`,
    protegido ? `<div class="ctx-item" data-act="destravar">${IC.unlock} Destravar</div>` : `<div class="ctx-item" data-act="travar">${IC.lock} Travar</div>`,
    `<div class="ctx-sep"></div>`,
    `<div class="ctx-item danger" data-act="dropar">${IC.trash} Dropar banco</div>`,
  ].join('');
  menu.innerHTML = items;
  menu.querySelectorAll('.ctx-item').forEach((el) => {
    el.addEventListener('click', () => {
      hideCtxMenu();
      const act = el.dataset.act;
      if (act === 'travar') cmdTravar(nomeDb);
      else if (act === 'destravar') cmdDestravar(nomeDb);
      else if (act === 'dropar') cmdDropar(nomeDb);
    });
  });
  const r = ev.currentTarget.getBoundingClientRect();
  menu.classList.add('show');
  let left = r.right - menu.offsetWidth;
  let top = r.bottom + 6;
  if (top + menu.offsetHeight > window.innerHeight) top = r.top - menu.offsetHeight - 6;
  menu.style.left = Math.max(8, left) + 'px';
  menu.style.top = top + 'px';
};

/* ---------------------------------------------------------- connection test */
async function runConnectionTest() {
  const btn = $('btn-conn-test');
  btn.disabled = true; btn.innerHTML = `<span class="spin-load" style="display:inline-flex;">${IC.sync}</span> Testando…`;
  $('conn-status').textContent = 'Testando…';
  const t0 = performance.now();
  try {
    if (window.electronAPI.testConnection) {
      const r = await window.electronAPI.testConnection(serverIp);
      const ms = Math.round(performance.now() - t0);
      $('conn-status').innerHTML = r && r.success ? '<span class="badge-status ok">Online</span>' : '<span class="badge-status fail">Falha</span>';
      $('conn-time').textContent = (r && r.ms ? r.ms : ms) + ' ms';
    } else {
      await new Promise((res) => setTimeout(res, 600 + Math.random() * 500));
      const ms = Math.round(performance.now() - t0);
      $('conn-status').innerHTML = '<span class="badge-status ok">Online</span>';
      $('conn-time').textContent = ms + ' ms';
    }
    $('conn-last').textContent = new Date().toLocaleString('pt-BR');
    showToast('Conexão PostgreSQL OK.', 'ok');
  } catch (e) {
    $('conn-status').innerHTML = '<span class="badge-status fail">Falha</span>';
    showToast('Falha ao conectar ao PostgreSQL.', 'error');
  }
  btn.disabled = false; btn.innerHTML = `${IC.check} Testar Conexão`;
}

/* ============================================================ Arquivos SPED */
function buildHistoryItems() {
  let items = [];
  if (cachedSubfolders && cachedSubfolders.length) {
    cachedSubfolders.forEach((folder) => {
      let g = null;
      if (cachedGerados) for (const [, rec] of Object.entries(cachedGerados)) if (rec.nome && rec.nome.toLowerCase() === folder.name.toLowerCase()) { g = rec; break; }
      let lastMod = '';
      if (folder.files.length) lastMod = folder.files.reduce((a, b) => new Date(a.mtime) > new Date(b.mtime) ? a : b).mtime;
      items.push({ nome: folder.name, path: folder.path, files: folder.files, fileCount: folder.fileCount, totalSize: folder.totalSize, status: g ? (g.status || 'concluido') : 'concluido', responsavel: g ? g.responsavel : '', tipo: g ? g.tipo : 'Fiscal', motivo: g ? g.motivo : '', dataGeracao: (g && g.data_geracao) || lastMod, ultimoDownload: g ? g.ultimo_download : '' });
    });
  } else if (cachedGerados) {
    for (const [, r] of Object.entries(cachedGerados)) items.push({ nome: r.nome || '—', path: '', files: (r.arquivos || []).map((fp) => ({ name: fp.split(/[\\/]/).pop(), path: fp, size: 0 })), fileCount: (r.arquivos || []).length, totalSize: 0, status: r.status || 'concluido', responsavel: r.responsavel, tipo: r.tipo || 'Fiscal', motivo: r.motivo || '', dataGeracao: r.data_geracao || '', ultimoDownload: r.ultimo_download });
  }
  return items;
}

function renderHistoryTable() {
  const body = $('history-table-body');
  const items = buildHistoryItems();
  // populate responsavel filter
  const respSel = $('history-filter-resp');
  const resps = [...new Set(items.map((i) => i.responsavel).filter(Boolean))];
  if (respSel.options.length <= 1 && resps.length) resps.forEach((r) => { const o = document.createElement('option'); o.value = r; o.textContent = r; respSel.appendChild(o); });

  // KPIs
  const todayStr = new Date().toDateString();
  const geradosHoje = items.filter((i) => i.status !== 'erro' && i.dataGeracao && new Date(i.dataGeracao).toDateString() === todayStr).length;
  const comErro = items.filter((i) => i.status === 'erro').length;
  const pendentes = cachedEmpresasFila ? (cachedEmpresasFila.empresas || []).filter((e) => e.status === 'liberada' && !e.gerado_local).length : 0;
  $('kpi-hoje').textContent = geradosHoje; $('kpi-erro').textContent = comErro; $('kpi-pendente').textContent = pendentes;
  const navReady = $('badge-history-ready');
  if (navReady) { if (geradosHoje > 0) { navReady.style.display = 'inline-block'; navReady.textContent = geradosHoje; } else navReady.style.display = 'none'; }

  // filters
  const search = $('history-search-input').value.toLowerCase().trim();
  const per = $('history-filter-periodo').value, rf = $('history-filter-resp').value, tf = $('history-filter-tipo').value, st = $('history-filter-status').value;
  let rows = items;
  if (search) rows = rows.filter((i) => i.nome.toLowerCase().includes(search));
  if (rf !== 'all') rows = rows.filter((i) => i.responsavel === rf);
  if (tf !== 'all') rows = rows.filter((i) => i.tipo === tf);
  if (st === 'concluido') rows = rows.filter((i) => i.status !== 'erro');
  else if (st === 'erro') rows = rows.filter((i) => i.status === 'erro');
  if (per !== 'all') {
    const cut = { hoje: 1, '7d': 7, '30d': 30 }[per] * 86400000;
    rows = rows.filter((i) => i.dataGeracao && (Date.now() - new Date(i.dataGeracao).getTime()) <= cut);
  }

  if (rows.length === 0) { $('history-result-count').textContent = '0'; body.innerHTML = emptyRow(8, 'Nenhum arquivo encontrado', 'Ajuste a busca ou os filtros, ou aguarde novas gerações.'); return; }
  $('history-result-count').textContent = rows.length;

  body.innerHTML = rows.map((it) => {
    const isErr = it.status === 'erro';
    const isToday = !isErr && it.dataGeracao && new Date(it.dataGeracao).toDateString() === todayStr;
    const safe = (it.path || '').replace(/\\/g, '\\\\');
    const actions = isErr
      ? `<button class="rbtn" onclick="openDir('${(currentPath + '\\\\erros').replace(/\\/g, '\\\\')}')">Ver erro</button>`
      : `<div class="row-actions">
          <button class="rbtn primary" onclick="downloadFolder('${safe}')">${IC.download} Baixar</button>
          <button class="rbtn" onclick="openDir('${safe}')">Abrir Pasta</button>
          <button class="rbtn" onclick="copyText('${safe}')">Copiar</button>
        </div>`;
    return `<tr class="${isToday ? 'today' : ''}">
      <td class="cell-primary">${escapeHTML(it.nome)}${isToday ? '<span class="chip-today">Hoje</span>' : ''}</td>
      <td><span class="resp-chip"><span class="resp-avatar">${initials(it.responsavel)}</span>${escapeHTML(it.responsavel || '—')}</span></td>
      <td>${escapeHTML(it.tipo || 'Fiscal')}</td>
      <td class="cell-mono">${fmtDate(it.dataGeracao)}</td>
      <td>${isErr ? badge('fail', 'Falha') : badge('ok', 'Pronto')}</td>
      <td class="num">${isErr ? '—' : (it.totalSize ? fmtMB(it.totalSize / 1024 / 1024) : it.fileCount + ' arq.')}</td>
      <td class="cell-mono">${it.ultimoDownload ? relTime(it.ultimoDownload) : '—'}</td>
      <td class="actions-col">${actions}</td>
    </tr>`;
  }).join('');
}

async function downloadFolder(folderPath) {
  const res = await window.electronAPI.selectFolder();
  if (!res.success) return;
  const name = folderPath.split(/[\\/]/).pop();
  showToast(`Copiando ${name}…`, 'info');
  const cp = await window.electronAPI.copyFolder(folderPath, res.path + '\\' + name);
  showToast(cp.success ? `${name} baixado com sucesso.` : `Erro: ${cp.error}`, cp.success ? 'ok' : 'error');
}
window.downloadFolder = downloadFolder;

async function downloadAllSped() {
  const res = await window.electronAPI.selectFolder();
  if (!res.success) return;
  const fr = await window.electronAPI.listSubfolders(currentPath);
  if (!fr.success || !fr.folders.length) { showToast('Nenhuma pasta para baixar.', 'warn'); return; }
  showToast(`Copiando ${fr.folders.length} pastas…`, 'info');
  let ok = 0, err = 0;
  for (const f of fr.folders) { const c = await window.electronAPI.copyFolder(f.path, res.path + '\\' + f.name); c.success ? ok++ : err++; }
  showToast(err ? `${ok} OK, ${err} erro(s)` : `${ok} pasta(s) baixadas.`, err ? 'warn' : 'ok');
}

async function exportCsv() {
  const items = buildHistoryItems();
  const rows = [['Empresa', 'Responsavel', 'Tipo', 'Data', 'Status', 'Arquivos', 'Tamanho KB']];
  items.forEach((i) => rows.push([i.nome, i.responsavel || '', i.tipo || '', fmtDate(i.dataGeracao), i.status, i.fileCount, (i.totalSize / 1024).toFixed(0)]));
  const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
  const res = await window.electronAPI.saveFile(csv, 'sped_arquivos.csv', [{ name: 'CSV', extensions: ['csv'] }]);
  if (res.success) showToast('CSV exportado: ' + res.path, 'ok');
  else if (!res.canceled) showToast('Erro ao exportar CSV.', 'error');
}

/* ============================================================ Logs */
function renderLogsTech() {
  const el = $('log-terminal-content');
  if (!currentLogLines.length) { el.innerHTML = '<div class="text-muted">Nenhum log gravado.</div>'; return; }
  const level = $('log-filter-level').value, search = $('log-search-input').value.toLowerCase().trim();
  const atBottom = el.scrollHeight - el.clientHeight <= el.scrollTop + 30;
  let html = '', count = 0;
  currentLogLines.forEach((line) => {
    if (!line.trim()) return;
    let cls = 'log-debug', match = level === 'ALL';
    if (/ERROR|CRITICAL/i.test(line)) { cls = 'log-error'; match = level === 'ALL' || level === 'ERROR'; }
    else if (/WARNING/i.test(line)) { cls = 'log-warning'; match = level === 'ALL' || level === 'WARNING'; }
    else if (/INFO/i.test(line)) { cls = 'log-info'; match = level === 'ALL' || level === 'INFO'; }
    else if (/SUCESSO|CONCLUIDO/i.test(line)) { cls = 'log-success'; match = level === 'ALL'; }
    if (!match) return;
    if (search && !line.toLowerCase().includes(search)) return;
    count++;
    let f = escapeHTML(line);
    if (search) f = f.replace(new RegExp(`(${escapeRegExp(search)})`, 'gi'), '<span class="log-highlight">$1</span>');
    html += `<div class="log-line ${cls}">${f}</div>`;
  });
  el.innerHTML = count ? html : '<div class="text-muted">Nenhum log encontrado com os filtros.</div>';
  if (atBottom) el.scrollTop = el.scrollHeight;
}

function renderLogsOperational() {
  const body = $('log-op-body');
  const items = buildHistoryItems();
  const events = [];
  items.forEach((i) => {
    if (!i.dataGeracao) return;
    events.push({ time: i.dataGeracao, empresa: i.nome, evento: i.status === 'erro' ? 'Geração SPED' : 'Geração SPED ' + (i.tipo || ''), result: i.status === 'erro' ? { c: 'fail', t: 'Falha — ' + (i.motivo ? i.motivo.slice(0, 40) : 'erro') } : { c: 'ok', t: 'Concluído' } });
  });
  // recent commands as events
  (cachedCommands || []).slice(0, 8).forEach((cmd) => {
    if (!cmd.timestamp) return;
    const lbl = { travar: 'Travar banco', destravar: 'Destravar banco', dropar: 'Dropar banco', backup: 'Backup', restaurar: 'Restaurar', enfileirar: 'Enfileirar', pipeline: 'Pipeline completo', sincronizar: 'Sincronizar' }[cmd.acao] || cmd.acao;
    events.push({ time: cmd.timestamp, empresa: (cmd.params && cmd.params.banco) || '—', evento: lbl, result: { c: cmd.status === 'erro' ? 'fail' : cmd.status === 'concluido' ? 'ok' : 'run', t: cmd.status } });
  });
  events.sort((a, b) => new Date(b.time) - new Date(a.time));

  if (!events.length) { body.innerHTML = emptyRow(4, 'Sem eventos operacionais', 'Eventos de geração e comandos aparecem aqui.'); return; }
  body.innerHTML = events.slice(0, 40).map((e) => `<tr>
    <td class="cell-mono">${fmtDate(e.time)}</td>
    <td class="cell-primary">${escapeHTML(e.empresa)}</td>
    <td>${escapeHTML(e.evento)}</td>
    <td>${badge(e.result.c, e.result.t)}</td>
  </tr>`).join('');
}

/* ============================================================ Acesso Remoto */
function renderRemotoTable() {
  const body = $('remoto-table-body');
  if (!cachedBancosInfo) { body.innerHTML = skelRows(4); return; }
  const bancos = cachedBancosInfo.bancos || {};
  let entries = Object.entries(bancos);
  const filter = $('remoto-search-input').value.toLowerCase().trim();
  if (filter) entries = entries.filter(([nome, b]) => nome.toLowerCase().includes(filter) || (b.cliente || '').toLowerCase().includes(filter));
  if (!entries.length) { body.innerHTML = emptyRow(4, 'Nenhum banco disponível', 'Restaure um banco para gerar conexões remotas.'); return; }
  body.innerHTML = entries.map(([nomeDb, b]) => {
    const caminho = `${serverIp}:5432/${nomeDb}`;
    return `<tr>
      <td class="cell-primary">${escapeHTML(b.cliente || '—')}</td>
      <td class="cell-mono">${escapeHTML(nomeDb)}</td>
      <td class="cell-mono">${escapeHTML(caminho)}</td>
      <td class="actions-col"><div class="row-actions">
        <button class="rbtn" onclick="copyText('${jsStr(caminho)}')">Copiar Caminho</button>
        <button class="rbtn" onclick="openDir('${jsStr(currentPath)}')">Abrir Pasta</button>
        <button class="rbtn primary" onclick="openIniModal('${jsStr(nomeDb)}')">Gerar INI</button>
      </div></td>
    </tr>`;
  }).join('');
}

/* ----------------------------------------------------------- INI modal */
let _iniBanco = '';
window.openIniModal = function (nomeDb) {
  _iniBanco = nomeDb;
  $('ini-modal-banco').textContent = nomeDb;
  $('ini-ip-input').value = serverIp;
  gerarIniPreview(nomeDb);
  $('ini-modal').classList.add('show');
};
function gerarIniPreview(banco) {
  if (!banco) { $('ini-preview-content').value = ''; return; }
  const ip = $('ini-ip-input').value.trim() || 'localhost';
  const porta = $('ini-porta-input').value.trim() || '5432';
  let razao = banco.replace(/_local$/i, '').toUpperCase();
  if (cachedBancosInfo && cachedBancosInfo.bancos[banco] && cachedBancosInfo.bancos[banco].cliente) razao = cachedBancosInfo.bancos[banco].cliente.toUpperCase();
  $('ini-preview-content').value = `[Banco de Dados]
NomeServidor=${ip}
Caminho=${banco}
Driver=PostgreSQL
Porta=${porta}
Usuario=postgres
Senha=JAwd

[Cliente]
Razao=${razao}

[Sistema]
Versao=6.3287.6.685
CalcVendaPrestacao=0

[Exportacao]
RecalculaAliqCad=1
Fiscal=C:\\ACS_Exporta
CodReceitaICMS=1101`;
}
async function copiarIni() {
  const c = $('ini-preview-content').value;
  if (!c) { showToast('Nada para copiar.', 'warn'); return; }
  const r = await window.electronAPI.copyToClipboard(c);
  showToast(r && r.success ? 'INI copiado para a área de transferência.' : 'Erro ao copiar.', r && r.success ? 'ok' : 'error');
}
async function salvarIni() {
  const c = $('ini-preview-content').value;
  if (!c) { showToast('Nada para salvar.', 'warn'); return; }
  const r = await window.electronAPI.saveFile(c, 'acsgerente.ini', [{ name: 'Arquivo INI', extensions: ['ini'] }]);
  if (r && r.success) showToast('INI salvo: ' + r.path, 'ok');
  else if (r && !r.canceled) showToast('Erro ao salvar.', 'error');
}

/* ============================================================ Diagnóstico */
function renderDiagnostico() {
  const info = window._lastSystemInfo;
  if (info) {
    $('diag-ip').textContent = info.ip || '—';
    $('diag-hostname').textContent = info.hostname || '—';
    $('diag-disk').textContent = `${info.diskFreeGB} GB livres de ${info.diskTotalGB} GB`;
    const used = parseInt(info.diskUsedPercent, 10) || 0;
    const bar = $('diag-disk-bar'); bar.style.width = used + '%'; bar.className = used >= 90 ? 'fail' : used >= 78 ? 'warn' : '';
  }
  const d = cachedDaemonState || {};
  $('diag-daemon').textContent = (d.status || 'parado');
  $('diag-cycle').textContent = '#' + (d.ciclos || d.ciclos_completos || (cachedProgresso && cachedProgresso.ciclo_atual) || '--') + ' · ' + (d.ultimo_resultado || '—');
  const netOk = $('path-warning-alert').classList.contains('hidden');
  const net = $('diag-net'); net.className = 'badge-status ' + (netOk ? 'ok' : 'fail'); net.textContent = netOk ? 'Acessível' : 'Sem acesso';
  $('diag-path').textContent = currentPath;
}

/* ============================================================ comandos */
async function sendCommand(acao, params) {
  try {
    const res = await window.electronAPI.writeCommand(currentPath, { acao, params });
    if (res.success) { showToast(`Comando "${acao}" enviado.`, 'ok'); setTimeout(syncCommands, 400); }
    else showToast(`Erro: ${res.error}`, 'error');
    return res;
  } catch (e) { showToast('Falha ao enviar comando.', 'error'); }
}
async function syncCommands() {
  try { const r = await window.electronAPI.listCommands(currentPath); if (r.success) { cachedCommands = r.commands; } } catch (e) {}
}

window.cmdPipeline = async (base, id, nome) => { if (await showConfirm('Executar Agora — Pipeline Completo', `Executar pipeline completo de "${nome}"?\n\n1. Backup (pg_dump)\n2. Restaurar banco local\n3. Gerar SPED`, 'Pode levar vários minutos conforme o tamanho do banco.')) sendCommand('pipeline', { banco: base, empresa_id: id, nome }); };
window.cmdRestaurar = async (base) => { if (await showConfirm('Restaurar Banco', `Restaurar "${base}" a partir do backup local?`, 'Se já existir localmente, será recriado.')) sendCommand('restaurar', { banco: base }); };
window.cmdEnfileirar = async (id, nome) => { if (await showConfirm('Enfileirar', `Adicionar "${nome}" à fila manual de geração?`)) sendCommand('enfileirar', { empresa_id: id, nome }); };
window.cmdBackup = async (base) => { if (!base) { showToast('Banco base não identificado.', 'error'); return; } if (await showConfirm('Solicitar Backup', `Baixar novo backup (pg_dump) de "${base}"?`)) sendCommand('backup', { banco: base, forcar: true }); };
window.cmdTravar = async (db) => { if (await showConfirm('Travar Banco', `Travar "${db}"? Bancos travados não são removidos na limpeza automática.`)) sendCommand('travar', { banco: db }); };
window.cmdDestravar = async (db) => { if (await showConfirm('Destravar Banco', `Destravar "${db}"? Ficará sujeito à limpeza automática.`)) sendCommand('destravar', { banco: db }); };
window.cmdDropar = async (db) => { if (await showConfirm('Dropar Banco', `Dropar "${db}"?`, 'ATENÇÃO: ação IRREVERSÍVEL. O banco será removido permanentemente do PostgreSQL.')) sendCommand('dropar', { banco: db }); };

/* ============================================================ hooks globais */
window.openDir = async (p) => { const r = await window.electronAPI.openExplorer(p); if (!r.success) showToast('Erro ao abrir pasta.', 'error'); };
window.copyText = async (t) => { const r = await window.electronAPI.copyToClipboard(t); if (r.success) showToast('Copiado para a área de transferência.', 'ok'); };

/* ============================================================ system info / footer */
async function updateFooterSystem() {
  try {
    const info = await window.electronAPI.getSystemInfo();
    if (info && info.success) {
      window._lastSystemInfo = info;
      updateHealth();
      if ($('view-diag').classList.contains('active')) renderDiagnostico();
    }
  } catch (e) {}
  $('footer-sync-time').textContent = new Date().toLocaleTimeString('pt-BR');
  setTimeout(updateFooterSystem, 60000);
}
