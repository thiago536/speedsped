# CONTEXTO ATUAL — SpedGenerator (2026-07-08, manhã)

> Arquivo de retomada: tudo o que foi feito em 07-08/07/2026 e o estado real do
> sistema. Complementa o CLAUDE.md (arquitetura) — aqui é o "diário de bordo".

---

## 1. RESUMO EXECUTIVO

1. **Erro NAT resolvido (07/07)** — causa raiz descoberta e correção automática
   em produção (`fix_nat_compatibilidade`).
2. **Runtime error 217** era problema ambiental separado — resolvido com reboot.
3. **Tela de exportação presa corrigida (07/07)** — era a causa dos "1/3 arquivos"
   (faltar SEMITENS/CONTRIB). Validado: SAO MARCOS gerou 3/3 na madrugada de 08/07.
4. **INCIDENTE GRAVE (07/07 ~18:15)**: todos os arquivos da raiz de
   C:\SpedGenerator foram DELETADOS durante operação do Antigravity. Projeto
   **reconstruído na mesma noite** a partir dos transcripts do Claude Code +
   cópia antiga (C:\SpedGeneretor, 07/06) + catálogo do servidor. Sistema voltou
   a produzir na mesma noite.
5. **JE resolvido (07-08/07)**: faltava entrada no bancos_nomes.json (`je→JE`);
   gerou OK às 07:03 de 08/07.
6. **Timeout de abertura dinâmico (08/07)**: bancos `_local` grandes (remigio
   7,5 GB) ganham 90-150s para o ACS abrir em vez de 45s fixos — resolve os
   postos "lentos mas saudáveis" (H7/REMIGIO) sem hardcodar nomes.
7. **Bats reconstruídos estavam com LF** (sem CR) — cmd.exe engasgava e o
   finalizar não matava o daemon. Corrigido (CRLF em 15 bats) e sistema
   reiniciado limpo.

## 2. O ERRO NAT (referência rápida)

- "NAT do Banco" que o Gerente valida = **count(*) da tabela `atualizacoes`**
  (não `versao.nat` — o Gerente reconta e reescreve esse campo no startup).
- Nosso gerente.exe = build 720 → aceita NAT **279** (`ACS_NAT_COMPATIVEL` no .env).
- Cliente com Gerente mais novo aplica migrações no banco → count > 279 → dialog
  "Versão (NAT) do Banco Sintese incompatível" → mascarado como "ACS não abriu".
- Correção: `fix_nat_compatibilidade()` (postgres_manager.py, chamado no bloco
  de fixes do main.py) deleta as linhas mais recentes de `atualizacoes` até 279
  e alinha `versao.nat`. Só roda em `*_local`/`*_teste`.
- Docs: `resultado_teste_nat.md`, `EXPLICACAO_ERRO_NAT.txt`.
- **Ao atualizar o gerente.exe do servidor → ajustar `ACS_NAT_COMPATIVEL`.**

## 3. RECONSTRUÇÃO DO PROJETO (o que veio de onde)

- **Fontes**: transcripts JSONL do Claude Code (100 arquivos com histórico,
  extraídos para `Desktop\RECUPERACAO_SPED`), cópia antiga `C:\SpedGeneretor`
  (07/06), `__pycache__` sobrevivente, environ do daemon vivo (`.env`),
  catálogo do servidor (`bancos_nomes.json` regenerado com 144 bancos).
- **Verificado**: 23 módulos importam; funções nas mesmas linhas do arquivo
  vivo; todos os fixes presentes (NAT, saldo_mes, aberturas/volume,
  prestacao, controle_processos, cfop_fixer completo).
- **Perdido**: 2 melhorias do Antigravity em acs_automation (timeout 120s —
  já substituída pela versão dinâmica melhor; menu via Alt+O — pendente),
  auxiliares legados vieram da cópia de 07/06.
- **Proteções**: `Desktop\SpedGenerator_SNAPSHOT_20260707.zip`;
  `PROMPT_ANTIGRAVITY.txt` (regras para o Antigravity operar);
  ⚠️ `Desktop\env_recuperado.txt` tem SENHAS — apagar quando puder.
  ⚠️ **Git ainda não instalado** — recomendação nº 1 pendente.

## 4. STATUS POR POSTO (estado 08/07 manhã)

| Posto | Status | Observação |
|-------|--------|------------|
| JOAO PEDRO, SABUGI | ✅ geraram 07/07 | provas do fix NAT |
| SAO MARCOS | ✅ 3/3 em 08/07 | prova do fix da tela presa |
| JE | ✅ 2 arq 08/07 07:03 | resolvido com entrada no bancos_nomes.json |
| SANTA CRUZ, CRED DEDA, ZABELE, CASA NOVA, AMIGÃO, CROSS | ✅ 07/07 | |
| H7 / REMIGIO | 🟡 lentos (banco 7,5 GB) | timeout dinâmico 150s ativo desde 08/07 ~10h — acompanhar |
| CONVENIENCIA H7 | ❌ "ACS não abriu" recorrente | investigar popup/startup |
| SANTA ROSA | ❌ "nenhum arquivo" recorrente | diagnóstico pendente (observar_startup_nat.py) |
| FAGUNDES | ❌ NCM inválido (dado do cliente) + nome não bate com combo | contador/mapeamento |
| MILAGRES, MONTEIRENSE, E.LEITE | ❌ nome não bate com nome_fantasia do banco | mapear |
| DM VIII | ❌ CFOP sem template p/ clonar | correção manual no cliente |
| ALIANÇA | ❌ **erro NAT relatado 08/07** | EM INVESTIGAÇÃO (ver §5) |

## 5. EM ABERTO / PRÓXIMAS AÇÕES

1. **ALIANÇA — RESOLVIDO O DIAGNÓSTICO (08/07 15:20)**: NÃO é NAT. Com a
   máquina ociosa o Gerente abriu o alianca_local em 3s, login normal, count
   259 intacto (NAT menor nem bloqueia). Nas tentativas do pipeline o
   gerente.exe MORRIA no startup porque a máquina estava sob I/O pesado
   (autovacuum em 3 bancos + restores paralelos) — mesmo padrão do "Runtime
   error 217" de 07/07, que sarou com reboot porque o reboot zerou a carga.
   JE e SAO MARCOS só passaram de madrugada (ociosa) pelo mesmo motivo.
   Mitigação aplicada: **PREP_WORKERS=1 no .env** (1 restore por vez).
   Fix estrutural sugerido: gate "não abrir o ACS enquanto houver pg_restore
   ativo" no main/acs_runner + investigar o crash do gerente sob I/O com a ACS.
   (O timeout dinâmico por tamanho/upgrade em _timeout_abertura_acs foi
   mantido — é teto, não atrasa banco que abre rápido.)
2. Postos com nome divergente (MILAGRES/MONTEIRENSE/E.LEITE/FAGUNDES):
   conferir `SELECT codigo, nome_fantasia FROM empresa` em cada `_local` e
   mapear (mapping_config ou correção no Supabase).
3. CONVENIENCIA H7 e SANTA ROSA: diagnóstico com observar_startup_nat.py
   (apontar o ini e rodar com a máquina livre).
4. Validar a 1ª execução diária do `Backup Novo.bat` regenerado (144 bancos).
5. Instalar git + commit inicial (winget install Git.Git).
6. Reaplicar melhoria Alt+O do Antigravity (se ele tiver o diff).
7. pythonw antigo (PID 4664) pode estar segurando a porta 8777 do monitor —
   matar como admin se o monitor mostrar dado velho.

## 6. MUDANÇAS DE CÓDIGO FEITAS EM 07-08/07 (além da reconstrução)

| Arquivo | Mudança |
|---------|---------|
| `postgres_manager.py` | +`fix_nat_compatibilidade()` |
| `main.py` | import + chamada do fix_nat no bloco de fixes |
| `config.py` | +`ACS_NAT_COMPATIVEL` (279), +`ACS_ABRIR_TIMEOUT_S` (45) |
| `.env` | +`ACS_NAT_COMPATIVEL=279` |
| `acs_automation.py` | `_limpar_subtelas_acs` responde dialog 'Confirmação' via `_confirmar_saida_sped` (fix da tela presa); +`_timeout_abertura_acs()` (timeout dinâmico por tamanho do banco) |
| `bancos_nomes.json` | regenerado (144 bancos, formato `{"bancos":{...}}`, sem BOM) |
| `Backup Novo.bat` | regenerado (144 bancos) |
| todos os `.bat` | convertidos para CRLF |
| `CLAUDE.md` | atualizado com tudo acima |

## 7. DOCUMENTOS DE REFERÊNCIA

- `CLAUDE.md` — arquitetura e regras (leia primeiro)
- `resultado_teste_nat.md` / `EXPLICACAO_ERRO_NAT.txt` — o caso NAT completo
- `PROMPT_ANTIGRAVITY.txt` — regras para o Antigravity operar o sistema
- `IDEIAS_ESCALA_PRODUTO.md` — roadmap de escala e produto (27 ideias)
- `Desktop\RECUPERACAO_SPED` — fontes da reconstrução
