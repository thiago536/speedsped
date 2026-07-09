# Contexto da Atualização — 2026-06-10/11

> Registro completo da manutenção/evolução feita em 10-11/06/2026 (sessão com Claude Code).
> Complementa o `CLAUDE.md` (que descreve a arquitetura base). Este arquivo descreve o que
> MUDOU, o estado atual e onde paramos.

---

## 1. RESUMO EM 30 SEGUNDOS

O sistema ganhou: **monitor web** (substitui o painel.py na prática), **central operacional**
(reprocessar/pipeline/geração parcial pelo navegador), **timeline + auditoria por empresa**,
**retry agressivo de abertura do ACS** (erro NAT), **fila de adiados**, **solicitação manual
que fura o filtro de status do Supabase**, **anti-falso-sucesso** (arquivamento de SPEDs
antigos) e **fechamento mensal automático** (ADD5).

Acesso ao monitor: **http://localhost:8777** (rede: http://192.168.0.103:8777 — precisa de
regra de firewall, ver §8). Inicia com `iniciar_monitor.bat`.

---

## 2. O QUE FOI IMPLEMENTADO (por ADD)

### ADD1 — Backup nunca velho + controle visual
- O bloqueio "backup >= data_liberacao" já existia; o problema real era **pg_dump concorrente**
  (servidor recusa e zera arquivos). Corrigido com **lock duplo** em `backup_manager.py`:
  `threading.Lock` no processo + lock-file `C:\Backups_Novo\pg_dump.lock` (com PID, detecta órfão).
- `painel.py` corrigido (status "executando (T.1)" não casava com "executando").

### ADD2 — Central operacional (monitor web)
- **`monitor_web.py`** (NOVO): servidor HTTP stdlib, porta 8777, dashboard dark de página única.
  Cards: Daemon, Máquina, Processos, Backup, Pipeline, Central de empresas, Liberadas,
  Tracking, Fechamento mensal, Log ao vivo.
- **`central_service.py`** (NOVO): camada de serviço compartilhada (HTML + futuro Electron).
  `listar_empresas_completo()` (todas as empresas com situação calculada),
  `resolver_solicitacao()` (steps → modo existente do acs_runner), override de geração parcial.
- **Comandos novos** no `command_processor.py` (arquivos em `C:\ACS_Exporta\comandos\`):
  `reprocessar`, `pipeline_completo`, `gerar_parcial`, `fechamento_simular`, `fechamento_executar`.
- **Modal de verificação**: antes de executar ações em lote, mostra por cliente exatamente
  quais arquivos serão gerados (Fiscal A/B, Inventário etc. — mesma regra do `acs_runner`).
- **Fix do retry** (dor principal): `tracking.ja_gerado()` detecta **re-liberação**
  (data_liberacao > último registro → zera tentativas e reprocessa).

### ADD3 — Auditoria + auto-recuperação + logs estruturados
- **`auditoria.py`** (NOVO):
  - Timeline por empresa: `C:\ACS_Exporta\logs\empresas\{NOME}\timeline.jsonl`
    (categorias BACKUP/RESTORE/ACS/GERACAO/RECUPERACAO/SISTEMA; nunca quebra o pipeline).
  - `AUDITORIA_GERACAO.txt` na pasta final de cada posto: empresa, base, CNPJ, data liberação,
    backup usado (arquivo/data/tamanho), hora do restore, hora da geração, arquivos, resultado.
    Alerta `DADOS_POTENCIALMENTE_ANTIGOS` se backup < liberação.
- **Banco local ausente → restore automático** antes da geração (só falha se o restore falhar).
- **Erros nomeados**: `[GERACAO] Fiscal B nao gerado(s) apos as tentativas` em vez de genérico;
  prefixos de categoria em todos os erros do tracking.
- Monitor: clicar no nome da empresa abre o **histórico/timeline** no modal (`GET /api/timeline`).

### ADD4 — ACS que não abre (erro NAT) nunca desiste rápido
- ADD4 alegava que a auditoria renomeava `.backup` — **falso alarme verificado** (nenhum
  rename existe; auditoria só lê mtime/size).
- `tracking.ja_gerado`: bloqueio de 3 tentativas/dia **REMOVIDO** → cooldown 15 min (até a 3ª)
  e 60 min (da 4ª em diante). O sistema tenta o dia inteiro.
- **Retry de abertura**: `acs_runner` tenta abrir o ACS **12x com 20s de intervalo**
  (`ACS_ABRIR_MAX_TENTATIVAS`/`ACS_ABRIR_INTERVALO_S`); se não abrir → `AcsNaoAbriuError`.
- **Fila de adiados** em `main._run_pipeline`: posto cujo ACS não abriu fica `ADIADO`,
  os outros passam na frente; no fim do ciclo volta nele 1x; só então vira erro real.
- **Comprovado em produção**: FAGUNDES abriu na tentativa 4/12 (NAT é intermitente).

### Solicitação manual ignorada (caso EXPRESSO)
- Causa: postos `em_processo` no Supabase nunca entravam no ciclo (filtro `status='liberada'`).
- Correção em `main._run_interno`: **IDs na fila de prioridade entram no ciclo seja qual for
  o status** (Supabase segue somente leitura). Sem data_liberacao → assume "agora" (força
  backup fresco).
- Backup ausente já baixava sozinho (`encontrar_backup` → pg_dump com o nome da base).

### Anti-falso-sucesso (arquivos antigos reaproveitados)
- Bug: pasta do posto com SPEDs antigos fazia o sistema marcar sucesso SEM abrir o ACS.
- **`file_manager.arquivar_speds_antigos()`** (NOVO): move SPEDs antigos para
  `{POSTO}\anteriores\{timestamp}\` (nunca apaga).
  - Reprocessar / Pipeline completo → arquiva TUDO (geração nova garantida).
  - Gerar parcial → arquiva só os steps solicitados.
- Proteção extra no pipeline: arquivo mais antigo que a `data_liberacao` vigente nunca
  conta como "já gerado" (cobre re-liberação mensal).

### ADD5 — Fechamento mensal automático
- **`fechamento.py`** (NOVO):
  - Arquiva pastas de postos **sem atividade no mês corrente** + screenshots + timelines
    em `C:\ACS_Exporta\Historico\{ano}\{MM_MES}.zip`.
  - Zip validado (testzip + contagem) **antes** de remover qualquer original.
  - Dropa bancos `_local` não-protegidos (via `banco_tracker.dropar_banco_controlado`).
  - Relatório `FECHAMENTO_MENSAL_YYYY_MM.txt` + `fechamento_historico.json`.
  - **Guard**: aborta se pipeline ativo ou pg_dump/pg_restore/gerente rodando (testado: funcionou).
  - Marker `.fechado_YYYY_MM` impede repetição do automático.
  - **`C:\Backups_Novo` NUNCA é tocado.**
- Automático: daemon roda no início do ciclo todo **dia 1º** do mês.
- Monitor: card "Fechamento mensal" → Simular / Executar / Histórico.
- Simulação real em 11/06: 48 bancos `_local`, ~91,6 GB candidatos a limpeza.

---

## 3. ARQUIVOS NOVOS / MODIFICADOS

| Arquivo | Status | O quê |
|---|---|---|
| `monitor_web.py` | NOVO | Dashboard web 8777 + endpoints API |
| `central_service.py` | NOVO | Camada de serviço (empresas, parcial, timeline) |
| `auditoria.py` | NOVO | Timeline jsonl + AUDITORIA_GERACAO.txt |
| `fechamento.py` | NOVO | Fechamento mensal (ADD5) |
| `iniciar_monitor.bat` | NOVO | Sobe o monitor web |
| `main.py` | MOD | Adiados, auto-restore, manual fura status, erros nomeados, auditoria, fechamento automático |
| `acs_runner.py` | MOD | Retry abertura 12x20s, AcsNaoAbriuError, eventos timeline, modo_override |
| `tracking.py` | MOD | Re-liberação zera tentativas; cooldown 15/60min (sem bloqueio diário) |
| `backup_manager.py` | MOD | Lock duplo de pg_dump (serialização global) |
| `command_processor.py` | MOD | Handlers reprocessar/pipeline_completo/gerar_parcial/fechamento_*, arquivamento de antigos |
| `file_manager.py` | MOD | `arquivar_speds_antigos()` |
| `supabase_client.py` | MOD | select inclui `status` |
| `painel.py` | MOD | Fix exibição de status do backup |

**`acs_automation.py` NÃO foi tocado** (regra mantida — automação de GUI intacta).

### Arquivos de estado novos em C:\ACS_Exporta
- `logs\empresas\{NOME}\timeline.jsonl` — histórico por empresa
- `{POSTO}\AUDITORIA_GERACAO.txt` — origem dos dados de cada geração
- `{POSTO}\anteriores\{timestamp}\` — SPEDs antigos arquivados em reprocessamentos
- `geracao_override.json` — pedidos de geração parcial (one-shot)
- `Historico\` — zips mensais + relatórios de fechamento
- `C:\Backups_Novo\pg_dump.lock` — serialização de dumps entre processos

---

## 4. STATUS ATUAL (11/06/2026 de manhã)

✅ **Funcionando e comprovado em produção:**
- EXPRESSO II e III gerados de verdade (10/06 ~23h) após arquivamento dos antigos —
  inclusive com retry entre ciclos completando só o step que faltava.
- POSTO ZABELE gerou (estava "nunca processável", nome_base foi preenchido no Supabase).
- FAGUNDES: ACS abriu na tentativa 4/12 do retry — mas caiu em **erro real de dados:
  NCM inválido nos produtos** `7898924825167` e `7898924826058` → precisa correção manual
  no cadastro da base, depois Reprocessar.
- Timeline/auditoria gravando em todas as gerações.

⚠️ **Pendências:**
1. ~~Reiniciar daemon + monitor com o código do ADD5~~ **FEITO em 11/06 de manhã**:
   daemon reiniciado (PID 15756) e monitor recarregado com o card "Fechamento mensal".
2. **Firewall porta 8777** (acesso pela rede) — rodar como admin:
   `netsh advfirewall firewall add rule name="SpedGenerator Monitor (8777)" dir=in action=allow protocol=TCP localport=8777`
3. **FAGUNDES**: corrigir NCM dos 2 produtos na base → Reprocessar.
4. **FERREIRA E TAVARES**: aguardando próximo retry (cooldown) com o código novo de 12 tentativas.
5. `iniciar_sistema.bat` não sobe o monitor web — subir junto via `iniciar_monitor.bat`
   (considerar adicionar ao bat oficial).

---

## 5. COMO OPERAR (novidades)

```
# Monitor web (preferido ao painel.py)
http://localhost:8777        → iniciar_monitor.bat

# Central de empresas (no monitor):
- buscar/filtrar por situação (PENDENTE, ERRO, ADIADO, CONCLUIDO, ...)
- selecionar clientes → Reprocessar | Pipeline completo | Gerar parcial (com steps)
- modal de verificação mostra os arquivos antes de confirmar
- clicar no NOME da empresa → timeline completa (backup, restore, tentativas ACS, erros)

# Fechamento mensal (card no monitor):
- Simular → mostra o que seria arquivado/removido (não altera nada)
- Executar → zip + limpeza + drop de bancos (só com sistema ocioso)
- Histórico → execuções anteriores e GB recuperados
- Automático: todo dia 1º do mês
```

## 6. COMPORTAMENTOS NOVOS IMPORTANTES

- **Pedido manual NUNCA é ignorado**: entra no ciclo mesmo com status ≠ liberada.
- **Reprocessar = geração nova garantida**: os arquivos atuais vão para `anteriores\`.
- **ACS com NAT**: 12 tentativas de abrir (20s entre elas) → ADIADO (outros passam na
  frente) → retorno final → só então erro. E o tracking continua tentando o dia todo
  (cooldown 15/60 min) — nunca mais "desiste até amanhã".
- **Toda geração concluída** deixa `AUDITORIA_GERACAO.txt` na pasta do posto dizendo
  exatamente qual backup originou os arquivos.
