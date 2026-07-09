# PainelSPED — Interface Electron v2.0

## Objetivo

Interface desktop moderna (Electron) para usuarios da rede local acompanharem E CONTROLAREM o sistema SpedGenerator. Leitura em tempo real + ações de controle via sistema de comandos.

## Arquitetura

```
SERVIDOR (PC dedicado)
├── Python Daemon (main.py --daemon)
│   ├── Pipeline: backup → restaurar → gerar SPED
│   ├── Command Processor (thread daemon)
│   │   Monitora comandos/ a cada 3s, executa acoes
│   │   Exporta bancos_info.json a cada 30s
│   │
│   └── Escreve JSONs de estado ↓
│
├── C:\ACS_Exporta\                      ← pasta compartilhada na rede
│   ├── progresso.json                   estado do pipeline tempo real
│   ├── progresso_backup.json            estado dos downloads (pg_dump)
│   ├── gerados.json                     historico de geracoes
│   ├── daemon_state.json                estado do daemon
│   ├── bancos_ativos.json               tracking de bancos restaurados
│   ├── bancos_info.json                 info completa bancos (tamanho, protecao) ← NOVO
│   ├── comandos/                        ← NOVO: fila de comandos
│   │   ├── {uuid}.json                  comando individual
│   │   └── ...
│   ├── {NOME_POSTO}\*.TXT              arquivos SPED gerados
│   └── erros\*.png                      screenshots de erro
│
└── PainelSPED.exe (Electron)            ← ESTE PROJETO
    Le arquivos + escreve comandos
```

## Comunicacao Electron ↔ Python

### Leitura (Electron → JSONs)
- progresso.json — pipeline tempo real (2.5s polling)
- progresso_backup.json — downloads pg_dump
- gerados.json — historico SPED
- daemon_state.json — estado daemon
- bancos_info.json — info bancos PostgreSQL
- comandos/*.json — status dos comandos enviados
- spedgenerator.log — logs do sistema

### Escrita (Electron → comandos/)
Electron escreve arquivos JSON em `comandos/` com:
```json
{
  "id": "uuid-gerado-pelo-electron",
  "acao": "travar",
  "params": { "banco": "nome_db" },
  "timestamp": "ISO",
  "status": "pendente",
  "origem": "HOSTNAME-DO-PC"
}
```

Python daemon le, processa, atualiza status para `executando` → `concluido`/`erro` com campo `resultado`.

### Acoes Suportadas
| Acao | Params | Descricao |
|------|--------|-----------|
| travar | banco: nome_db | Protege banco de drop automatico |
| destravar | banco: nome_db | Remove protecao |
| dropar | banco: nome_db | Drop permanente do PostgreSQL |
| backup | banco: nome_base, forcar: bool | pg_dump do servidor remoto |
| sincronizar | — | Forca atualizacao de bancos_info.json |

## Funcionalidades

### 1. Dashboard Principal
- Status daemon (rodando/parado/erro/aguardando)
- Contadores: concluidas, total, erros
- Empresa atual + etapa + progresso
- Proximo ciclo, ultimo resultado
- Auto-refresh 2.5s

### 2. Pipeline em Tempo Real
- Lista empresas do ciclo atual com etapa visual
- Etapas: pendente → backup → restaurando → corrigindo → aguardando → gerando → concluido/erro
- Filtro por nome
- Atualiza automaticamente

### 3. Fila de Backups
- Cards com status de cada pg_dump
- Tamanho MB, velocidade MB/min, tempo decorrido
- Status geral (executando/parado)

### 4. Bancos de Dados (CONTROLE)
- Lista todos bancos restaurados com tamanho e data
- **Travar** — protege de drop automatico (com confirmacao)
- **Destravar** — remove protecao (com confirmacao)
- **Dropar** — drop permanente (com confirmacao + aviso irreversivel)
- **Backup** — solicita novo pg_dump (com confirmacao)
- Filtro por nome
- Fila de comandos com status em tempo real
- Info bar: total bancos, tamanho, travados
- Dados de bancos_info.json (atualizado a cada 30s pelo servidor)

### 5. Historico / Arquivos SPED
- Lista empresas com SPED gerado
- Para cada: data, arquivos, status
- **Baixar pasta** — copia pasta do posto pra local (dialog nativo)
- **Baixar todos** — copia todas pastas SPED
- **Abrir pasta** — abre no Explorer
- **Copiar caminho** — copia pro clipboard
- Filtro por nome e status

### 6. Erros (Screenshots)
- Galeria de screenshots de erro
- Visualizador modal inline (base64 on-demand)
- Data/hora, tamanho, nome
- Abrir pasta no Explorer

### 7. Logs
- Ultimas 200 linhas de spedgenerator.log
- Filtro por nivel (INFO/WARNING/ERROR)
- Busca por texto com highlight
- Auto-scroll

### 8. Configuracoes
- Caminho base (local ou rede)
- Instrucoes de distribuicao

## Regras

### NAO ALTERAR
- Nenhum .py do backend (exceto command_processor.py que e NOVO)
- Nenhum processo de automacao (ACS, pg_dump, pg_restore)
- Nenhum banco de dados diretamente
- Nenhum .bat de agendamento

### COMUNICACAO SEGURA
- Acoes destrutivas (dropar) requerem confirmacao no frontend
- Todas acoes passam pelo command processor (thread segura)
- Bancos protegidos (travados) nao sao dropados pelo cleanup automatico
- Comandos processados sequencialmente (sem race conditions)
- Comandos antigos (>24h) limpos automaticamente

## Arquivos do Projeto

```
painel-sped/
├── main.js          — Electron main process + IPC handlers
├── preload.js       — Bridge segura (contextBridge)
├── renderer.js      — Logica do frontend (polling, renders, comandos)
├── index.html       — Layout com todas views
├── style.css        — Dark glassmorphism theme
└── package.json     — Electron + electron-builder config
```

## Stack Tecnico

- **Electron** — framework desktop
- **HTML/CSS/JS vanilla** — frontend
- **Node.js fs** — leitura/escrita via preload.js
- **electron-builder** — empacotamento .exe
- **JSON files** — comunicacao com Python daemon
- Sem banco de dados proprio
- Sem servidor web
- Sem dependencia do Python em runtime
