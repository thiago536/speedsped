// ============================================================================
//  SPEEDSPED — Demo Data Layer  (mock-data.js)
//  Fornece um shim de window.electronAPI APENAS quando rodando fora do Electron
//  (ex.: navegador / preview de design). Dentro do Electron, o preload já define
//  window.electronAPI e este arquivo NÃO faz nada — pode ser mantido ou removido
//  na build de produção sem efeito colateral.
// ============================================================================
(function () {
  if (window.electronAPI) return; // Electron real → não sobrescreve nada.

  console.info('[SPEEDSPED] electronAPI ausente — carregando camada de dados de demonstração.');

  // ---------------------------------------------------------------- helpers
  const now = () => new Date();
  const iso = (d) => d.toISOString();
  const minsAgo = (m) => iso(new Date(Date.now() - m * 60000));
  const hoursAgo = (h) => iso(new Date(Date.now() - h * 3600000));
  const daysAgo = (d) => iso(new Date(Date.now() - d * 86400000));
  const today = (hh, mm) => { const d = now(); d.setHours(hh, mm, 0, 0); return iso(d); };

  // --------------------------------------------------- cadastro de empresas
  // Fonte única de verdade; as demais estruturas JSON são derivadas daqui.
  const RESP = {
    marina: 'Marina Costa', rafael: 'Rafael Andrade', juliana: 'Juliana Mendes',
    bruno: 'Bruno Tavares', patricia: 'Patrícia Lima',
  };

  // estado: gerando | backup | restaurando | aguardando | pendente | erro | concluido
  const EMP = [
    { id: 1,  nome: 'Comercial Aurora Ltda',      base: 'aurora',      cnpj: '12.345.678/0001-90', resp: RESP.marina,   estado: 'gerando',     lib: daysAgo(0),  size: 842,  tipo: 'Fiscal' },
    { id: 2,  nome: 'Distribuidora Nova Era',      base: 'novaera',     cnpj: '23.456.789/0001-12', resp: RESP.rafael,   estado: 'backup',      lib: daysAgo(0),  size: 1320, tipo: 'Fiscal' },
    { id: 3,  nome: 'Auto Peças Veloz',            base: 'veloz',       cnpj: '34.567.890/0001-34', resp: RESP.bruno,    estado: 'restaurando', lib: daysAgo(0),  size: 615,  tipo: 'Contribuições' },
    { id: 4,  nome: 'Supermercado Bom Preço',      base: 'bompreco',    cnpj: '45.678.901/0001-56', resp: RESP.marina,   estado: 'aguardando',  lib: daysAgo(0),  size: 2410, tipo: 'Fiscal' },
    { id: 5,  nome: 'Materiais Construsul',        base: 'construsul',  cnpj: '56.789.012/0001-78', resp: RESP.juliana,  estado: 'pendente',    lib: daysAgo(1),  size: 980,  tipo: 'Fiscal' },
    { id: 6,  nome: 'Padaria Pão Dourado',         base: 'paodourado',  cnpj: '67.890.123/0001-90', resp: RESP.patricia, estado: 'pendente',    lib: daysAgo(1),  size: 320,  tipo: 'Contribuições' },
    { id: 7,  nome: 'Farmácia Saúde Total',        base: 'saudetotal',  cnpj: '78.901.234/0001-11', resp: RESP.rafael,   estado: 'erro',        lib: daysAgo(0),  size: 540,  tipo: 'Fiscal', motivo: 'pg_restore: timeout ao restaurar dump (excedeu 600s)' },
    { id: 8,  nome: 'Transportes Rápido Sul',      base: 'rapidosul',   cnpj: '89.012.345/0001-22', resp: RESP.bruno,    estado: 'erro',        lib: daysAgo(0),  size: 720,  tipo: 'Fiscal', motivo: 'SpedGenerator: registro C170 inconsistente — geração abortada' },
    { id: 9,  nome: 'Restaurante Sabor & Cia',     base: 'saborecia',   cnpj: '90.123.456/0001-33', resp: RESP.juliana,  estado: 'concluido',   lib: daysAgo(0),  size: 410,  tipo: 'Fiscal' },
    { id: 10, nome: 'Papelaria Escriba',           base: 'escriba',     cnpj: '01.234.567/0001-44', resp: RESP.patricia, estado: 'concluido',   lib: daysAgo(0),  size: 215,  tipo: 'Contribuições' },
    { id: 11, nome: 'Móveis Conforto Lar',         base: 'confortolar', cnpj: '11.222.333/0001-55', resp: RESP.marina,   estado: 'concluido',   lib: daysAgo(0),  size: 1180, tipo: 'Fiscal' },
    { id: 12, nome: 'Açougue Boi Gordo',           base: 'boigordo',    cnpj: '22.333.444/0001-66', resp: RESP.rafael,   estado: 'concluido',   lib: daysAgo(1),  size: 305,  tipo: 'Fiscal' },
    { id: 13, nome: 'Posto Estrada Real',          base: 'estradareal', cnpj: '33.444.555/0001-77', resp: RESP.bruno,    estado: 'concluido',   lib: daysAgo(1),  size: 1620, tipo: 'Contribuições' },
    { id: 14, nome: 'Confecções Bella Moda',       base: 'bellamoda',   cnpj: '44.555.666/0001-88', resp: RESP.juliana,  estado: 'concluido',   lib: daysAgo(2),  size: 525,  tipo: 'Fiscal' },
  ];

  // ----------------------------------------------------- estado de simulação
  const sim = {
    cycle: 47,
    activeId: 1,
    progress: 34,          // % da empresa ativa
    startedAt: minsAgo(6),
    nextCycle: today(now().getHours() + 1, 0).slice(11, 19),
    ticks: 0,
  };

  function empById(id) { return EMP.find((e) => e.id === id); }

  // Avança a simulação a cada poll para a NOC "respirar".
  function tick() {
    sim.ticks++;
    const active = empById(sim.activeId);
    if (active && active.estado === 'gerando') {
      sim.progress = Math.min(100, sim.progress + 1.5 + Math.random() * 3);
      if (sim.progress >= 100) {
        // conclui e promove a próxima aguardando
        active.estado = 'concluido';
        active.dataGeracao = iso(now());
        const next = EMP.find((e) => e.estado === 'aguardando') || EMP.find((e) => e.estado === 'restaurando');
        if (next) {
          next.estado = 'gerando';
          sim.activeId = next.id;
          sim.progress = 6;
          sim.startedAt = iso(now());
          sim.cycle++;
        }
      }
    }
    // promove preparações lentamente
    if (sim.ticks % 14 === 0) {
      const bk = EMP.find((e) => e.estado === 'backup');
      if (bk) bk.estado = 'restaurando';
      const rs = EMP.find((e) => e.estado === 'restaurando' && e.id !== sim.activeId);
      if (rs && !EMP.some((e) => e.estado === 'gerando')) rs.estado = 'gerando', (sim.activeId = rs.id);
      else if (rs && Math.random() > 0.6) rs.estado = 'aguardando';
    }
  }

  // ------------------------------------------------------- builders de JSON
  function buildProgresso() {
    const active = empById(sim.activeId);
    const concluidos = EMP.filter((e) => e.estado === 'concluido').map((e) => e.nome);
    const erros = EMP.filter((e) => e.estado === 'erro').map((e) => `${e.nome}: ${e.motivo || 'Erro desconhecido'}`);
    const pipeline = {};
    EMP.forEach((e) => {
      let etapa = e.estado;
      if (e.estado === 'concluido') etapa = 'concluido';
      pipeline['emp_' + e.id] = { nome: e.nome, etapa, motivo: e.motivo || '', responsavel: e.resp, base: e.base };
    });
    return {
      ciclo_atual: sim.cycle,
      indice_atual: concluidos.length + 1,
      total_empresas: EMP.length,
      concluidos,
      erros,
      ativo: !!(active && active.estado === 'gerando'),
      empresa_atual: active ? active.nome : '',
      etapa: 'Gerando SPED Fiscal',
      inicio: sim.startedAt,
      progresso_pct: Math.round(sim.progress),
      pipeline,
    };
  }

  function buildDaemonState() {
    return {
      status: 'executando',
      ultima_atualizacao: iso(now()),
      proximo_ciclo: sim.nextCycle,
      ciclos: sim.cycle,
      ultimo_resultado: 'OK',
    };
  }

  function buildBackupProgress() {
    const bancos = {};
    EMP.filter((e) => e.estado === 'backup' || e.estado === 'restaurando').forEach((e) => {
      bancos[e.base] = {
        status: e.estado === 'backup' ? 'executando' : 'concluido',
        elapsed: 120 + Math.floor(Math.random() * 200),
        tamanho_mb: e.size,
        etapa: e.estado,
      };
    });
    return { status: 'executando', bancos };
  }

  function buildBancosInfo() {
    const bancos = {};
    EMP.forEach((e) => {
      // bancos restaurados localmente (todos menos os ainda pendentes de preparação)
      if (e.estado === 'pendente') return;
      bancos[e.base + '_local'] = {
        nome_base: e.base,
        cliente: e.nome,
        tamanho_mb: e.size,
        data_restauracao: e.estado === 'restaurando' ? iso(now()) : hoursAgo(2 + e.id),
        ultimo_backup: hoursAgo(3 + e.id),
        protegido: [11, 13].includes(e.id),
        status: e.estado === 'restaurando' ? 'restaurando' : 'ativo',
        integridade: e.estado === 'erro' ? 'erro' : (e.id % 5 === 0 ? 'pendente' : 'ok'),
        empresas: [e.nome],
      };
    });
    return { bancos, total: Object.keys(bancos).length, ultima_atualizacao: iso(now()) };
  }

  function buildEmpresasFila() {
    const statusMap = {
      gerando: 'em_processo', backup: 'liberada', restaurando: 'liberada',
      aguardando: 'liberada', pendente: 'liberada', erro: 'erro', concluido: 'gerada',
    };
    const empresas = EMP.map((e) => ({
      id: e.id,
      nome: e.nome,
      nome_base: e.base,
      cnpj: e.cnpj,
      responsavel: e.resp,
      tipo: e.tipo,
      status: statusMap[e.estado] || 'liberada',
      data_liberacao: e.lib,
      gerado_local: e.estado === 'concluido',
      erro_local: e.estado === 'erro',
      data_geracao: e.dataGeracao || (e.estado === 'concluido' ? hoursAgo(1 + e.id) : ''),
    }));
    const fila_manual = [
      { empresa_id: 5, nome: 'Materiais Construsul', status: 'pendente', solicitado_em: minsAgo(12) },
      { empresa_id: 6, nome: 'Padaria Pão Dourado', status: 'pendente', solicitado_em: minsAgo(4) },
    ];
    return { empresas, fila_manual, ultima_atualizacao: iso(now()) };
  }

  function buildGerados() {
    const out = {};
    EMP.filter((e) => e.estado === 'concluido' || e.estado === 'erro').forEach((e) => {
      out['g_' + e.id] = {
        nome: e.nome,
        responsavel: e.resp,
        tipo: e.tipo,
        status: e.estado === 'erro' ? 'erro' : 'concluido',
        data_geracao: e.dataGeracao || hoursAgo(1 + e.id),
        motivo: e.motivo || '',
        ultimo_download: e.id % 3 === 0 ? hoursAgo(e.id) : '',
        arquivos: e.estado === 'erro' ? [] : [
          `C:\\ACS_Exporta\\${e.nome}\\SPED_FISCAL_${e.base}.txt`,
          `C:\\ACS_Exporta\\${e.nome}\\SPED_CONTRIB_${e.base}.txt`,
        ],
      };
    });
    return out;
  }

  function buildSubfolders() {
    return EMP.filter((e) => e.estado === 'concluido' || e.estado === 'erro').map((e) => ({
      name: e.nome,
      path: `C:\\ACS_Exporta\\${e.nome}`,
      fileCount: e.estado === 'erro' ? 0 : 2,
      totalSize: e.size * 1024,
      files: e.estado === 'erro' ? [] : [
        { name: `SPED_FISCAL_${e.base}.txt`, path: `C:\\ACS_Exporta\\${e.nome}\\SPED_FISCAL_${e.base}.txt`, size: e.size * 512, mtime: e.dataGeracao || hoursAgo(1 + e.id) },
        { name: `SPED_CONTRIB_${e.base}.txt`, path: `C:\\ACS_Exporta\\${e.nome}\\SPED_CONTRIB_${e.base}.txt`, size: e.size * 512, mtime: e.dataGeracao || hoursAgo(1 + e.id) },
      ],
    }));
  }

  // -------------------------------------------------------------- log demo
  const LOG_SEED = [
    `[INFO] Daemon iniciado — ciclo #${sim.cycle}`,
    '[INFO] Conexão Supabase estabelecida (latência 38ms)',
    '[INFO] 14 empresas liberadas carregadas do Supabase',
    '[INFO] pg_dump iniciado: distribuidora novaera',
    '[INFO] Backup novaera concluído — 1320 MB em 3m12s',
    '[INFO] pg_restore iniciado: veloz_local',
    '[WARNING] Espaço em disco em 26% livre (54 GB)',
    '[INFO] SpedGenerator: gerando Comercial Aurora Ltda',
    '[ERROR] pg_restore: timeout ao restaurar saudetotal_local (>600s)',
    '[INFO] Reenfileirando Farmácia Saúde Total ao fim da fila',
    '[ERROR] SpedGenerator: registro C170 inconsistente em rapidosul',
    '[SUCESSO] SPED Fiscal de Restaurante Sabor & Cia gerado e validado',
    '[SUCESSO] SPED Fiscal de Papelaria Escriba gerado e validado',
    '[INFO] Sincronização de arquivos para o compartilhamento de rede OK',
  ];

  // --------------------------------------------------- fila de comandos demo
  const commands = [
    { acao: 'pipeline', params: { banco: 'aurora' }, status: 'executando', resultado: '', timestamp: minsAgo(6) },
    { acao: 'backup', params: { banco: 'novaera' }, status: 'concluido', resultado: '1320 MB', timestamp: minsAgo(14) },
    { acao: 'travar', params: { banco: 'confortolar_local' }, status: 'concluido', resultado: 'protegido', timestamp: hoursAgo(2) },
    { acao: 'restaurar', params: { banco: 'veloz' }, status: 'executando', resultado: '', timestamp: minsAgo(3) },
  ];

  // ============================================================ electronAPI
  const ok = (extra) => Promise.resolve(Object.assign({ success: true }, extra));

  window.electronAPI = {
    // janela
    windowMinimize() {}, windowMaximize() {}, windowClose() {},
    shellOpen(url) { window.open(url, '_blank'); },

    dirExists() { return ok({ exists: true }); },

    readJson(_path, file) {
      const map = {
        'daemon_state.json': buildDaemonState,
        'progresso.json': function () { tick(); return buildProgresso(); },
        'progresso_backup.json': buildBackupProgress,
        'bancos_info.json': buildBancosInfo,
        'empresas_fila.json': buildEmpresasFila,
        'gerados.json': buildGerados,
      };
      if (map[file]) return ok({ data: map[file]() });
      return Promise.resolve({ success: false, error: 'not found' });
    },

    readLog() {
      const t = now().toLocaleTimeString('pt-BR');
      const lines = LOG_SEED.map((l, i) => `${new Date(Date.now() - (LOG_SEED.length - i) * 45000).toLocaleString('pt-BR')}  ${l}`);
      lines.push(`${now().toLocaleString('pt-BR')}  [INFO] Polling de status — ciclo #${sim.cycle} (${Math.round(sim.progress)}%)`);
      return ok({ lines });
    },

    listSubfolders() { return ok({ folders: buildSubfolders() }); },

    listCommands() { return ok({ commands: commands.slice().reverse() }); },
    writeCommand(_path, cmd) {
      commands.push({ acao: cmd.acao, params: cmd.params || {}, status: 'pendente', resultado: '', timestamp: iso(now()) });
      return ok();
    },

    selectFolder() { return ok({ path: 'C:\\Downloads' }); },
    copyFolder() { return ok(); },
    saveFile(_content, name) { return ok({ path: 'C:\\Downloads\\' + (name || 'arquivo') }); },
    openExplorer() { return ok(); },
    copyToClipboard(text) {
      try { navigator.clipboard && navigator.clipboard.writeText(text); } catch (e) {}
      return ok();
    },
    showNotification(title, body) { console.info('[notif]', title, body); },
    getSystemInfo() {
      return ok({ diskFreeGB: '54.2', diskTotalGB: '237.0', diskUsedPercent: '77', ip: '192.168.1.100', hostname: 'SERVIDOR-ACS' });
    },
  };
})();
