# SpedGenerator — Contexto do Projeto

> Robô que gera arquivos SPED Fiscal/Contribuições automaticamente para os clientes
> (postos de combustível) a partir dos bancos de dados na nuvem. Roda 24h como daemon.
> Última grande manutenção: **2026-07-07** (erro "NAT incompatível" resolvido: NAT = count da tabela `atualizacoes`; `fix_nat_compatibilidade()` remove migrações extras no banco `_local` — `ACS_NAT_COMPATIVEL=279` no `.env`, **ajustar ao atualizar o gerente.exe** — detalhes em `resultado_teste_nat.md`; correção da tela de exportação presa que causava 1/3 arquivos). Antes: 2026-07-03 (correção automática de "Departamento sem CFOP" via `cfop_fixer.py` + teto da geração ACS subiu de 15 para 50 min enquanto houver atividade); 2026-07-02 (falha definitiva no tracking + Reprocessar força backup novo + botão "Refazer todos com erro"); 2026-06-26 (resolução de nome de banco + sincronização do backup diário).
>
> ⚠️ **2026-07-07 ~18:15: os arquivos da raiz de C:\SpedGenerator foram deletados por automação externa e o projeto foi RECONSTRUÍDO a partir dos transcripts do Claude Code + cópia antiga (C:\SpedGeneretor, de 07/06) + catálogo do servidor.** Fontes preservadas em `Desktop\RECUPERACAO_SPED`. Conferir comportamento em produção nos primeiros ciclos; pequenas divergências de texto de log são possíveis.

---

## 1. O QUE O SISTEMA FAZ (visão de 30 segundos)

A cada ciclo (intervalo do `.env`, ~5 min) o daemon:
1. Pergunta ao **Supabase** quais empresas estão `liberada` (contador disse "pode gerar").
2. Para cada uma, baixa o **banco de dados atualizado** do servidor remoto (`pg_dump`).
3. Restaura esse banco no **PostgreSQL local**.
4. Abre o **ACS Gerente** (programa desktop) e, via automação de tela, gera os `.txt` do SPED.
5. Move os arquivos para `C:\ACS_Exporta\{NOME DO POSTO}\` e marca como concluído.

Em paralelo, um **backup diário** (`Backup Novo.bat`) baixa um `.backup` de cada banco para
`C:\Backups_Novo` (não confundir com o download sob demanda do pipeline — ver §3).

Supabase é **somente leitura** (o sistema nunca muda status lá). O controle do que já foi
gerado fica em `C:\ACS_Exporta\gerados.json`.

---

## 2. FLUXO DE DADOS (onde tudo acontece)

```
Supabase (empresas liberadas)
        │  supabase_client.listar_empresas_liberadas()
        ▼
main.py (daemon, loop) ── filtra já-gerados (tracking.ja_gerado) ── checa controle.py (pausar/parar)
        │
        ├─ PREPARAÇÃO (background, PREP_WORKERS em paralelo; download serial):
        │     mapping_config.obter_base_mapeada()  ← corrige nome_base errado no Supabase
        │     backup_finder.encontrar_backup()     ← valida data do .backup vs data_liberacao
        │         └─ se velho/vazio: backup_manager.executar_pg_dump(forcar=True)  ← baixa do servidor (1 por vez)
        │     postgres_manager.criar_e_restaurar()  ← DROPA banco _local e restaura o backup ATUAL
        │     postgres_manager.fix_* ← ajustes que o ACS exige
        │
        └─ GERAÇÃO (foreground, 1 por vez):
              ini_manager.atualizar_ini()  ← aponta o ACS para o banco _local
              acs_runner.executar_acs_e_gerar_sped()
                  └─ acs_automation.*  ← dirige a GUI do ACS Gerente (abrir, login, menus, gerar)
              file_manager.organizar_sped_posto() ← valida CNPJ/contagem e move
              auditoria.* ← grava timeline por empresa + AUDITORIA_GERACAO.txt
              tracking.registrar_gerado() / registrar_erro()

COMANDOS MANUAIS (monitor web / painel Electron):
   monitor_web.py → escreve C:\ACS_Exporta\comandos\*.json
        └─ command_processor.py (thread DENTRO do daemon) executa:
             reprocessar, pipeline_completo, gerar_parcial, restaurar, backup,
             pausar/retomar/parar, fechamento_executar, ...
```

### Pastas/arquivos de estado em disco (tudo em `C:\ACS_Exporta`, **não** em `C:\SpedGenerator`)
| Local | Conteúdo |
|-------|----------|
| `C:\Backups_Novo\*.backup` | Backups dos bancos (do backup diário e do download sob demanda; original vive no servidor) |
| `C:\SpedGenerator\Bancos\` | Cópia temporária usada no restore |
| PostgreSQL local `{nome}_local` | Banco restaurado de cada posto |
| `C:\ACS_Exporta\{POSTO}\` | Arquivos SPED finais (.txt) + `AUDITORIA_GERACAO.txt` |
| `C:\ACS_Exporta\gerados.json` | Tracking do que já foi gerado / erros |
| `C:\ACS_Exporta\daemon_state.json` | Status do daemon (ciclo, próximo ciclo, último resultado) — lido pelo monitor |
| `C:\ACS_Exporta\progresso.json` / `progresso_backup.json` | Pipeline por empresa / pg_dump em andamento e fila |
| `C:\ACS_Exporta\empresas_fila.json` / `bancos_info.json` | Empresas Supabase / bancos `_local` (exportados p/ painel e monitor) |
| `C:\ACS_Exporta\fila_manual.json` | Empresas enfileiradas manualmente |
| `C:\ACS_Exporta\controle.json` | Estado operacional: `normal` / `pausado` / `parar` |
| `C:\ACS_Exporta\comandos\*.json` | Comandos do monitor/painel (consumidos pelo command_processor) |
| `C:\ACS_Exporta\spedgenerator.lock` | Trava de instância única (contém o PID) |
| `C:\Backups_Novo\pg_dump.lock` | Trava de serialização do pg_dump (1 dump por vez) |
| `C:\ACS_Exporta\Historico\{ano}\` | Zips do fechamento mensal + relatórios |
| `C:\ACS_Exporta\logs\empresas\{NOME}\timeline.jsonl` | Timeline por empresa (auditoria) |
| `C:\ACS_Exporta\daemon.log` / `C:\SpedGenerator\spedgenerator.log` | Logs |

---

## 3. ARQUIVOS E RESPONSABILIDADES

### Núcleo (produção — não quebrar)
| Arquivo | Responsabilidade |
|---------|------------------|
| `main.py` | Orquestrador. Loop do daemon (`run_daemon`), pipeline preparar→gerar (`PREP_WORKERS` paralelos), trava de instância única, checkpoints de controle, CLI (`--reprocessar`, `--limpar-tracking`). |
| `config.py` | Lê o `.env` e expõe constantes (`BACKUP_DIR`, `PG_BIN_DIR`, `DAEMON_INTERVAL_MINUTES`, `PG_DUMP_PARALLEL`, `PG_DUMP_TIMEOUT`, `PREP_WORKERS`, `ACS_NAT_COMPATIVEL`, `ACS_ABRIR_TIMEOUT_S`, `resolver_versao_acs`). 2026-07-08: timeout de abertura do ACS é **dinâmico por tamanho do banco `_local`** (`_timeout_abertura_acs` em acs_automation: ≥1.5 GB→90s, ≥4 GB→150s) — bancos grandes (remigio 7.5 GB) demoram mais que 45s legitimamente e eram mortos como "ACS não abriu". |
| `supabase_client.py` | Conexão com Supabase (somente leitura); `listar_empresas_liberadas()` (status=liberada, armazenamento=Nuvem **OU** nome_base preenchido). `combinar_info_sped()`: as **anotações** do contador são juntadas ao `informacoes_sped` (2026-07-02) — o modo de geração (ex.: "Inventario") às vezes só está nas anotações; vale para o pipeline e para o monitor (via `exportar_empresas_fila`). |
| `backup_finder.py` | `encontrar_backup()`: decide se o `.backup` em disco serve (data+hora e tamanho) ou precisa rebaixar. **Bloqueia a geração se não conseguir backup fresco.** Aplica `obter_base_mapeada`. |
| `backup_manager.py` | `executar_pg_dump()` (download remoto, serial via `_dump_serial_lock` + `pg_dump.lock`), `limpar_nome_base()` (tira " V. 569"), `resolver_nome_pg()`/`resolver_servidor()` (nome/credenciais via `bancos_nomes.json`/`servidores.json`; **fallback capitaliza** o nome quando a base não está no JSON), `listar_desatualizados()`, `backup_desatualizado()`. |
| `postgres_manager.py` | Restore local: `criar_e_restaurar()`, `criar_banco()` (dropa+recria, serial via `_ddl_lock`), `dropar_banco()`, `restaurar_backup()`, `fix_*` (inclui `fix_nat_compatibilidade` 2026-07-07: banco de cliente com Gerente mais novo tem linhas extras em `atualizacoes` → NAT > 279 → ACS recusa abrir; o fix deleta as mais recentes até `ACS_NAT_COMPATIVEL`), `consultar_cnpjs_empresa()`. |
| `acs_runner.py` | Orquestra a geração por empresa: `detectar_modo_sped()`, `_pipeline_multi_fiscal` (perfil A/B na mesma sessão), retry com sucesso parcial, `matar_acs()`, steps (FISCAL, FISCAL_A/B, INVENTARIO, COMITENS, SEMITENS, CONTRIB). |
| `acs_automation.py` | **Automação da GUI do ACS Gerente** (pywinauto/win32): abrir, login, menus, exportar, fechar popups, `executar_verificacoes_pre_geracao` (gate não-fatal). ⚠️ Ponto mais frágil (ver §5). 2026-07-07: `_limpar_subtelas_acs` agora responde o dialog 'Confirmação' via `_confirmar_saida_sped` ao fechar telas de exportação (a tela presa bloqueava o menu seguinte e causava geração 1/3). |
| `ini_manager.py` | Escreve `acsgerente.ini` apontando para o banco `_local` do posto. |
| `file_manager.py` | Valida e move os `.txt` gerados; `obter_arquivos_validos_existentes()`; `arquivar_speds_antigos()`; screenshots de erro. |
| `tracking.py` | `gerados.json`: `registrar_gerado/erro`, `ja_gerado()` (cooldown 15/60 min; erro **definitivo** — NCM/produto ou 3ª falha `[GERACAO]` — bloqueia até Reprocessar/re-liberação), prioridades, marcador de backup forçado (`forcar_backup.json`). |
| `banco_tracker.py` | Rastreia bancos `_local` ativos; proteção (travar/destravar); limpeza no fechamento mensal. |
| `mapping_config.py` | `obter_base_mapeada()` (ex.: `meneizao→rdl`, `jrcaicara→jr`), `deve_ignorar_base()` (bases Web/sem backup). |
| `cfop_fixer.py` | **Correção automática de "Departamento sem CFOP"** (2026-07-03): quando o ACS gera `Departamentos_Invalidos.txt`, `acs_automation` levanta `DepartamentoSemCfopError` com os pares (depto, cfop) e o `acs_runner` cadastra o CFOP no banco `_local` (clona template em `cfop_depto` — mesmo depto, ou mesmo CFOP de outro depto — e preenche o cabeçalho em `departamentos`) e repete a geração (1x por execução; se nada corrigível, vira erro definitivo). CLI manual: `python cfop_fixer.py <banco> [relatorio.txt] [--apply]` (sem `--apply` é dry-run). Só mexe no `_local` (cópia descartável); o banco do servidor não é tocado — se o erro voltar no próximo restore, corrige de novo. |
| `controle.py` | Estado operacional (`normal`/`pausado`/`parar`) em `controle.json`; `obter_estado()`/`definir_estado()`. |
| `command_processor.py` | Thread no daemon que consome `comandos\*.json` (monitor web/painel). Ações: reprocessar (**força backup novo**), reprocessar_erros (refaz todas com erro), pipeline_completo, gerar_parcial, restaurar, backup, pausar/retomar/parar, fechamento, sincronizar. Exporta `empresas_fila.json`/`bancos_info.json`. |
| `central_service.py` | Camada de serviços da central (consumida pelo monitor): `listar_empresas_completo()` (situação calculada por empresa), `resolver_solicitacao()` (steps→modo ACS), `registrar_override_geracao()`, `ler_timeline_empresa()`. |
| `auditoria.py` | Rastreabilidade best-effort: `evento()` (timeline por empresa), `gravar_auditoria()` (origem do dado junto ao SPED), `ler_timeline()`. |
| `progresso.py` | Escreve `progresso.json` para painel/monitor/overlay. |

### Interfaces / monitoramento
| Arquivo | Uso |
|---------|-----|
| `monitor_web.py` | **Dashboard web** (somente leitura + enfileira comandos) em `http://localhost:8777` (ou IP da máquina). Preferido pelo usuário ao painel. |
| `overlay_status.py` | Indicador flutuante sempre-no-topo/click-through (lê `progresso.json`). |
| `painel.py` | Painel local (legado, ainda funciona). `frontend_supabase.py`, `admin_supabase.py` auxiliares. ⚠️ Vieram da cópia de 07/06 na reconstrução. |
| `fechamento.py` | Fechamento mensal automático (todo dia 1º): arquiva o mês em `Historico\{ano}\{MM}.zip`, limpa área operacional, dropa bancos `_local` não-protegidos. **`C:\Backups_Novo` NUNCA é tocado**; originais só removidos após zip validado; não roda com pipeline/pg_dump/ACS ativos. |

### Configuração / dados
| Arquivo | Conteúdo |
|---------|----------|
| `.env` | Credenciais e caminhos. `DISABLE_REMOTE_BACKUP=False` (download ligado). `ACS_NAT_COMPATIVEL=279`. |
| `bancos_nomes.json` | Formato `{"bancos": {chave(lowercase) → {host, port, user, password, dbname(case-correto)}}}`. **Reconstruído 2026-07-07 a partir do catálogo do servidor (144 bancos).** Host padrão: `pgsql.e-prosys.com`. **Salvar sempre SEM BOM** (relido por mtime). |
| `servidores.json` | Fallback de credenciais: `padrao` (pgsql.e-prosys.com) e `santavitoria` (187.45.181.113). |
| `acs_versoes.json` | Versões alternativas do ACS (GerenteDM, Gerente659 — ⚠️ executáveis podem não existir). ⚠️ Veio da cópia de 07/06. |

### Entrada / operação (.bat)
| Arquivo | Uso |
|---------|-----|
| `iniciar_sistema.bat` | **Ponto de entrada oficial.** Finaliza tudo e sobe daemon + interfaces. |
| `finalizar_sistema.bat` | Encerra daemon, ACS, pg_dump/restore e libera o lock. |
| `Backup Novo.bat` | **Backup diário em produção** (roda todo dia): `pg_dump -F c` de cada banco → `C:\Backups_Novo\<Nome>.backup`. ⚠️ Reconstruído de leitura de 26/06 (78 bancos) — **conferir/ressincronizar com bancos_nomes.json (144)**. Cada bloco tem 2 linhas de `pg_dump`: a `bin\pg_dump` falha de propósito (o `cd ...\15\bin` no topo faz virar `...\bin\bin\pg_dump`) — quem dumpa é a linha `pg_dump` nua. Os `break` são no-op no cmd.exe. |
| `baixar_pendentes.py` / `.bat` | Baixa manualmente só os backups desatualizados. |

### Auxiliares / dev / teste (NÃO são produção)
`_diag_*.py`, `_teste_*.py`, `testar_*.py`, `observar_startup_nat.py` (diagnóstico NAT: abre o
Gerente sem fecha-dialogs e loga janelas/dialogs em observacao_nat.log), `baixar_pendentes.py`.
⚠️ Alguns auxiliares antigos (debug_menu, gravador, capture_screen, watcher, bats noturnos)
não foram recuperados — se precisar, estão na cópia 07/06 em `C:\SpedGeneretor`.

---

## 4. O QUE FUNCIONA

✅ **Detecção de liberação** no Supabase e agendamento do daemon.
✅ **Backup sempre fresco**: compara **data + hora** do `.backup` com a `data_liberacao`. Se anterior, baixa novo.
✅ **Download sob demanda** (1 por vez, serial — trava global) ao processar cada empresa.
✅ **Restore sempre do backup atual**: o banco `_local` é dropado e recriado; só reaproveitado dentro do mesmo ciclo.
✅ **Proteção de dados**: download que falha grava em temp único e só substitui o bom com `os.replace`; backup < 100 bytes é rejeitado.
✅ **Resolução de nome de banco robusta** (2026-06-26): bases Nuvem sem entrada no JSON resolvem pelo **fallback que capitaliza**. Ver §7.
✅ **Erro NAT resolvido** (2026-07-07): `fix_nat_compatibilidade` no pipeline; JOAO PEDRO e SABUGI geraram em produção.
✅ **Trava de instância única** + **serialização de pg_dump/DDL**.
✅ **Controle operacional**: PAUSAR/RETOMAR/PARAR via monitor (checkpoints entre etapas).
✅ **Geração ACS**: abre, faz login e gera Fiscal/Contribuições pelo pipeline normal (geração parcial inclusive).
✅ **Fechamento mensal** automático (dia 1º) e **auditoria/timeline** por empresa.
✅ **Monitor web** com central de empresas, ações em lote e log ao vivo.

---

## 5. O QUE ESTÁ FRÁGIL

### 🟡 Automação GUI do ACS (ponto mais frágil)
- Depende de títulos de janela/popups → quebra com update do ACS ou mudança de tela/resolução.
- **"ACS não abrir em 45s"** já foi causado por `acsgerente.ini` desatualizado (corrigido 11/06). Se voltar, **cheque primeiro o .ini**. Popup **"Atenção" (`#32770`)** no startup ainda aparece intermitente em algumas bases.
- **"Runtime error 217 at 005B0593"** (dialog `Error`) derrubando o Gerente em QUALQUER banco = problema ambiental da máquina → **reiniciar o servidor** (aconteceu e resolveu em 07/07).
- **Contribuições/SEMITENS após Fiscal na mesma sessão (1/3 gerados)**: a tela "Exportação para o SPED" ficava presa (fechá-la dispara dialog 'Confirmação' que ninguém respondia) e bloqueava o menu seguinte. **Correção aplicada 2026-07-07** em `_limpar_subtelas_acs` (chama `_confirmar_saida_sped`). Validar em produção.
- **Uso da máquina durante a geração** (LogMeIn/terminal em primeiro plano) faz a automação falhar ("nenhum arquivo gerado"). Não usar mouse/teclado com a faixa vermelha na tela.

### 🟡 Dívidas técnicas / cuidados
- **Monitor mostra `pipeline_completo` como "concluido"** assim que enfileira o download (thread). Se o `pg_dump` falhar depois, só aparece no `daemon.log` — não na UI.
- **Tracking não detecta re-liberação por nova data**: `ja_gerado()` olha `empresa_id + informacoes_sped`. Para forçar: `--reprocessar <id>` / `--limpar-tracking <id>`.
- **Servidor remoto recusa dumps concorrentes** (gera 0 byte). Por isso `PG_DUMP_PARALLEL=1` e dump serial. **Não aumentar o paralelismo de dump** (`PREP_WORKERS` paraleliza só restore+fixes, ≤2-3).
- **Acúmulo em disco**: bancos `_local` já chegaram a ~73 GB; limpeza é no fechamento mensal. Monitorar `C:`.
- **Dados faltando no Supabase** (`nome_base` vazio → não processáveis até preencher): POSTO CUBATI I, POSTO MARANHAO, POSTO SAO CRISTOVAO, POSTO SAO FRANCISCO BELEM (tem `nome_base='belem'`, que **não existe no servidor**).
- **Nomes de empresa que não batem com o banco** (erro "empresa não encontrada"/combo): POSTO NOSSA SENHORA DOS MILAGRES, POSTO FAGUNDES ("AUTO POSTO FAGUNDES" não está no combo do ACS), conferir também MONTEIRENSE/E.LEITE — checar `nome_fantasia` no banco e mapear.
- **MASTODONTE**: servidor diferente; corretamente bloqueado (não gera com dado velho).
- **`acs_versoes.json`** aponta executáveis (GerenteDM, Gerente659) que podem não existir.

---

## 6. COMO RODAR / OPERAR

```
# Subir (oficial): duplo clique em
C:\SpedGenerator\iniciar_sistema.bat

# Encerrar tudo
C:\SpedGenerator\finalizar_sistema.bat

# Monitor web (somente leitura + comandos)
http://localhost:8777   (ou http://IP-DA-MAQUINA:8777)

# Baixar manualmente backups desatualizados
C:\SpedGenerator\baixar_pendentes.bat

# Forçar reprocessar uma empresa (ID do Supabase)
python main.py --reprocessar <id>
python main.py --limpar-tracking <id>   # ou "todos"
```

- **Python**: `C:\Users\SERVIDOR SPED\AppData\Local\Python\pythoncore-3.14-64\python.exe`
- **PostgreSQL local**: `C:\Program Files\PostgreSQL\15\bin` (senha local `123`)
- **Servidor remoto**: `pgsql.e-prosys.com:5432` (user `postgres`); Santavitória em `187.45.181.113`
- **ACS Gerente**: `C:\ACSSoft\Sintese\Gerente SPED\gerente.exe` (build 720, NAT 279)

---

## 7. REGRAS PARA QUEM FOR MEXER

1. **Nunca gerar SPED com dado velho.** Se não dá para garantir backup fresco, `encontrar_backup` retorna `None` e a geração é bloqueada — comportamento desejado.
2. **Um `pg_dump` por vez.** Dumps concorrentes falham e podem zerar backups. Mantenha serial; não aumente o paralelismo de dump.
3. **Backup é cópia; o dado real está no servidor.** Apagar um `.backup` local não perde dado — rebaixa sob demanda.
4. **Salvar `bancos_nomes.json` sem BOM** (UTF-8 puro), senão `backup_manager` cai em fallback errado.
5. **Empresa Nuvem nova precisa entrar em DOIS lugares**: `bancos_nomes.json` (geração sob demanda) **e** `Backup Novo.bat` (backup diário). O `dbname` deve ser o **case-correto do servidor** — confirme com `psql ... -c "SELECT datname FROM pg_database WHERE datname ILIKE '%x%'"`. O fallback capitalize é só rede de segurança.
6. **Backup/dados e geração-ACS são problemas separados.** Conserte/teste um sem assumir que afeta o outro.
7. **Ao atualizar o gerente.exe, ajustar `ACS_NAT_COMPATIVEL` no `.env`** (o dialog de erro NAT informa o valor compatível do exe novo).
