# Prompt para o Claude Code — Integrar o novo frontend do SPEEDSPED

> Cole o bloco abaixo no Claude Code, na raiz do repositório do app Electron (`painel-sped/`).
> Ele descreve **exatamente** os arquivos novos, o contrato de dados e o que **não** deve ser alterado.

---

## PROMPT (copie a partir daqui)

Você está trabalhando no **SPEEDSPED**, um app **Electron desktop** usado por um escritório contábil para gerar e distribuir **SPED Fiscal/Contribuições**. O processamento pesado (download de backups PostgreSQL via `pg_dump`, restore local, automação do ACS Gerente Delphi, geração do SPED e sincronização) é feito por um **daemon Python** que grava arquivos JSON e logs numa pasta compartilhada. O frontend é **HTML/CSS/JS vanilla** carregado pelo Electron e conversa com o main process via `window.electronAPI` (preload + IPC).

O frontend foi **refatorado**. Sua tarefa é **identificar, integrar e validar** o novo frontend no app Electron existente, **sem alterar backend, Python, Supabase ou a arquitetura de IPC**.

### Arquivos do novo frontend (já presentes em `painel-sped/`)
- `index.html` — shell + 9 telas (Arquivos SPED, Fila SPED, Painel Geral/NOC, Status do Pipeline, Bancos de Dados, Acesso Remoto, Log do Sistema, Diagnóstico, Configurações).
- `style.css` — design system "Steel Dark Operations" (inline-free, tokens em `:root`).
- `renderer.js` — toda a lógica: polling em tempo real, render das tabelas/drawer/context-menu/modais, comandos, geração de INI, teste de conexão.
- `mock-data.js` — **camada de demonstração só para navegador**. Ela define `window.electronAPI` **apenas quando ele não existe**. Dentro do Electron real (preload ativo) ela é **inerte**. Em produção você pode manter (inofensiva) ou remover do `index.html`.

### O que fazer
1. **Substituir** os arquivos antigos do renderer por estes (`index.html`, `style.css`, `renderer.js`) e garantir que o `BrowserWindow` carrega este `index.html`.
2. **Conferir o preload**: o `renderer.js` consome a superfície `window.electronAPI` abaixo. Garanta que o `preload.js` expõe **todos** estes métodos com as **mesmas assinaturas e formatos de retorno**:

   ```
   windowMinimize()  windowMaximize()  windowClose()
   shellOpen(url)
   dirExists(path)                         -> boolean | { exists: boolean }
   readJson(path, fileName)                -> { success, data }     // ler JSON da pasta
   readLog(path, fileName, maxLines)       -> { success, lines: string[] }
   listSubfolders(path)                    -> { success, folders: [{ name, path, fileCount, totalSize, files:[{name,path,size,mtime}] }] }
   listCommands(path)                      -> { success, commands: [{ acao, params, status, resultado, timestamp }] }
   writeCommand(path, { acao, params })    -> { success, error? }
   selectFolder()                          -> { success, path }
   copyFolder(src, dest)                   -> { success, error? }
   saveFile(content, suggestedName, filters)-> { success, path, canceled?, error? }
   openExplorer(path)                      -> { success, error? }
   copyToClipboard(text)                   -> { success, error? }
   showNotification(title, body)
   getSystemInfo()                         -> { success, diskFreeGB, diskTotalGB, diskUsedPercent, ip, hostname }
   ```
   **Opcional (novo):** `testConnection(ip)` -> `{ success, ms }`. Se não existir, o frontend **simula** o teste de conexão — não quebra.

3. **Arquivos JSON lidos** pelo polling (a cada 2,5 s os 3 primeiros; demais a cada ~7,5 s):
   `daemon_state.json`, `progresso.json`, `progresso_backup.json`, `gerados.json`, `bancos_info.json`, `empresas_fila.json`, e fallback `bancos_ativos.json`. Log: `spedgenerator.log`.

4. **Comandos** gravados via `writeCommand` (campo `acao`): `pipeline`, `restaurar`, `enfileirar`, `backup`, `travar`, `destravar`, `dropar`, `sincronizar`. Confirme que o daemon entende esses nomes (já eram os usados antes — não mudaram).

### Contrato de dados — campos NOVOS que a UI agora exibe
O frontend lê estes campos extras **com fallback gracioso** (ausência não quebra, só mostra "—"). Para popular as telas novas, faça o daemon/Supabase incluir:

- `empresas_fila.json` → `empresas[]`: **`responsavel`** (string), **`tipo`** ("Fiscal" | "Contribuições"), `cnpj` (opcional).
- `bancos_info.json` → `bancos[<db>]`: **`cliente`** (string), **`ultimo_backup`** (ISO date), **`integridade`** ("ok" | "pendente" | "erro").
- `gerados.json` → `<id>`: **`responsavel`**, **`tipo`**, **`ultimo_download`** (ISO date, opcional).
- `progresso.json`: **`progresso_pct`** (0–100, opcional, da empresa ativa); em `pipeline[<id>]`: **`responsavel`**, **`base`** (nome base do banco).

> Esses campos são **somente leitura de exibição**. Não invente lógica de backend — apenas garanta que, quando existirem, cheguem nesses JSONs.

### Mudanças de UX que você verá no código (para não "consertar" como se fosse bug)
- A tela inicial é **Arquivos SPED** (não o Painel). É a 1ª da navegação, com **busca em destaque (autofoco)**, filtros recolhidos atrás do botão "Filtros", ação primária **Baixar**, e realce "Hoje" nas linhas geradas no dia.
- Tabelas seguem **um único padrão**: ações frequentes inline + **kebab só para ações destrutivas** (em Bancos: Travar/Destravar/Dropar).
- Status usa **um só componente de badge**; nada de estilos paralelos.
- Em **Configurações › Geral** só existem **IP do servidor PostgreSQL** e **Pasta compartilhada** (sem Supabase, sem canal de atualização). A seção de Atualizações é um **placeholder visual para CI/CD futuro** (GitHub Actions → Build → Release → auto-update) — ainda não há lógica de update implementada.

### NÃO faça
- Não altere Python, o daemon, o schema do Supabase ou a estrutura dos JSONs além de **adicionar** os campos listados.
- Não converta para framework (React/Vue). O frontend é vanilla por requisito.
- Não remova `window.electronAPI`; não troque os nomes de comando.

### Validação final
- Rodar `npm start`; confirmar que abre em **Arquivos SPED**, sem erros no console.
- Verificar que a busca filtra clientes, **Baixar/Abrir Pasta/Copiar** disparam os handlers (`copyFolder`/`openExplorer`/`copyToClipboard`).
- Em Bancos, testar Backup/Restaurar (inline) e o kebab (Travar/Destravar/Dropar → `writeCommand`).
- Conferir Painel Geral, Pipeline (drawer com timeline), Logs (abas Operacional/Técnica), Acesso Remoto (modal de INI), Diagnóstico e Configurações (salvar IP + pasta em `localStorage`: chaves `sped_config_path` e `sped_server_ip`).

Ao terminar, liste: (1) ajustes feitos no preload/main, (2) campos JSON que o daemon ainda precisa fornecer, (3) qualquer método de `electronAPI` ausente.
