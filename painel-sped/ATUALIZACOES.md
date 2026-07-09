# SPEEDSPED — Guia de Atualizações

Pipeline de auto-update: GitHub Actions builda o instalador e publica num **repositório
público de releases** (`painel-sped-releases`). Cada PC cliente verifica atualizações
automaticamente ao abrir o app — **sem token**, via HTTPS público.

> **Arquitetura (importante):**
> - **`painel-sped`** (PRIVADO) — o código-fonte do painel. É aqui que você trabalha e cria as tags.
> - **`painel-sped-releases`** (PÚBLICO) — guarda só os instaladores `.exe`. O electron-updater
>   baixa daqui. Como é público, não precisa de token no cliente (eliminou as falhas antigas).
>
> A regra **tag == version**: a tag criada em `painel-sped` deve ser igual à `version` do
> `package.json` (ex: tag `v1.0.7` ⇄ `"version": "1.0.7"`).

> **Bootstrap (uma vez só):** um app instalado de uma versão ANTIGA (sem o auto-update novo)
> NÃO se atualiza sozinho. É preciso instalar manualmente UMA versão nova boa. A partir dela,
> todas as próximas chegam automaticamente.

> **Diagnóstico:** o auto-update grava log em
> `C:\Users\<usuario>\AppData\Roaming\SPEEDSPED\logs\main.log`.
> Em Configurações › Atualizações o botão **"Verificar agora"** força a checagem e mostra o resultado.

---

## Como lançar uma nova versão

**1. Faça as mudanças nos arquivos do frontend:**
- `index.html` — estrutura das telas
- `renderer.js` — lógica e interatividade
- `style.css` — visual / design system

**2. Atualize a versão em `package.json`:**
```json
"version": "1.1.0"
```
> A versão do `package.json` e a tag git DEVEM ser iguais (ex: ambas `1.1.0`).

**3. Suba os arquivos alterados no GitHub** (via interface web ou API).

**4. Crie a tag no GitHub Releases** ou peça ao Claude Code para criar via API:
```
Crie a tag v1.1.0 no repo painel-sped
```

O GitHub Actions roda automaticamente, gera o instalador e publica na Release.
Os PCs dos agentes recebem a atualização na próxima abertura do app.

---

## Estrutura do repositório

```
painel-sped/
├── index.html          ← UI: estrutura das 9 telas
├── renderer.js         ← UI: toda lógica de polling, render, comandos
├── style.css           ← UI: design system "Steel Dark Operations"
├── mock-data.js        ← UI: dados fake para testar no browser (inerte no Electron)
├── main.js             ← Electron: janela, IPC handlers, auto-updater
├── preload.js          ← Electron: bridge segura entre renderer e main
├── splash.html         ← Electron: tela de carregamento (2.5s)
├── package.json        ← Configuração do projeto e do electron-builder
├── assets/icons/       ← Ícones do app (icon.ico, icon.png)
└── .github/workflows/
    └── release.yml     ← Pipeline CI/CD (dispara em push de tag v*)
```

**Não entram no git** (`.gitignore`): `node_modules/`, `build-dist/`, `dist/`, `resources/`

---

## Secrets necessários no GitHub

Configurados em: `github.com/thiago536/painel-sped → Settings → Secrets → Actions`

| Secret | Uso |
|--------|-----|
| `GH_TOKEN` | Token com escopo `repo` — publica a Release e o instalador |
| `UPDATE_TOKEN` | Token read-only (Contents: Read) — embutido no instalador para os clientes baixarem updates |

---

## Como funciona o auto-update nos PCs clientes

```
App abre
  └─ main.js lê resources/update-config.json (token embutido pelo build)
       └─ autoUpdater.checkForUpdatesAndNotify()
            └─ Compara versão local vs latest.yml no GitHub Releases
                 └─ Nova versão? Baixa em background
                      └─ Dialog "Reiniciar agora / Depois"
                           └─ quitAndInstall() → app reinicia atualizado
```

O arquivo `resources/update-config.json` **não existe no código-fonte** — é criado pelo
workflow do GitHub Actions durante o build (step "Inject update token") e fica dentro
do instalador compilado.

---

## Distribuição inicial (novo PC)

1. Baixe o instalador mais recente em `github.com/thiago536/painel-sped/releases`
2. Envie o `SPEEDSPED-Setup-X.X.X.exe` para o agente (WhatsApp, Drive, pendrive)
3. O agente instala uma vez — a partir daí recebe tudo automaticamente

---

## Tokens

- **`GH_TOKEN`** (escopo `repo`): usado só no GitHub Actions (secret do repo, nunca sai do CI)
- **`UPDATE_TOKEN`** (fine-grained, Contents: Read no repo `painel-sped`): embutido no instalador pelo CI, permite que os clientes baixem releases de repo privado
