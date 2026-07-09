# Resultado do teste do "Erro NAT" — 2026-07-07

## Causa raiz (confirmada)

O "NAT do Banco" que o ACS Gerente valida no startup **não é** o campo `versao.nat` —
é a **contagem de linhas da tabela `atualizacoes`** (o log de migrações de schema do
Sintese). No startup o Gerente conta as linhas, **reescreve** `versao.nat` com esse
valor e compara com o NAT que o exe suporta (build 720 → NAT **279**). Se o banco
tiver mais migrações do que o exe conhece, mostra:

> Versão (NAT) do Banco Sintese incompativel!
> Versão do sistema: 6.3287.6.720 / NAT compativel: 279 / NAT do Banco: 282

Por isso o Nível 1 do plano (UPDATE `versao.nat = 279`) **não funcionava**: o Gerente
recontava `atualizacoes` (282 linhas) e desfazia o UPDATE.

### De onde vieram as 282
Em **02/07/2026 18:01** o cliente JOAO PEDRO atualizou o Gerente local dele para o
**build 728**, que aplicou 3 migrações no banco do servidor:

| id_cartao | build | descrição |
|-----------|-------|-----------|
| SD-1924 | 728 | Envio automático da conciliação financeira (eConf) ao quitar faturas de convênio |
| SD-2062 | 728 | Aumento do campo codigo da tabela de cartões |
| SD-2081 | 728 | Aumento do campo codigo das tabelas de recebimento |

São mudanças retrocompatíveis (alargamento de colunas) — o exe build 720 lê o schema
novo sem problema; só o gate do NAT bloqueava.

## O Runtime error 217 era OUTRO problema

Antes do reboot de 07/07, o gerente.exe morria com dialog `Error`
"Runtime error 217 at 005B0593" em **qualquer** banco (até saomarcos, NAT 259).
Era ambiental: **o reboot do servidor resolveu** — depois dele, creddeda_local abriu
normal e o joaopedro passou a mostrar o dialog NAT de verdade (que antes o crash 217
mascarava). Se o 217 voltar, reiniciar a máquina é o primeiro passo.

## Correção implementada

`fix_nat_compatibilidade(nome_db)` em `postgres_manager.py`:
- Conta `atualizacoes`; se `count > ACS_NAT_COMPATIVEL` (`.env`, hoje **279**),
  DELETE das linhas mais recentes (`data_hora DESC`) até igualar, e alinha `versao.nat`.
- Só roda em bancos `_local`/`_teste` (cópias descartáveis; o servidor nunca é tocado —
  a cada restore o fix reaplica).
- Chamada no bloco de fixes do `main.py` (etapa "corrigindo"), antes dos demais fixes.

**Validação fim-a-fim (07/07 12:33):** `joaopedro_teste` recriado limpo do
`joaopedro_local` (NAT 282) → fix removeu SD-1924/2062/2081 → Gerente abriu na tela
de login "POSTO JOAO PEDRO" sem dialog nenhum.

## ⚠️ Manutenção futura

- **Ao atualizar o gerente.exe deste servidor**, ajustar `ACS_NAT_COMPATIVEL` no `.env`
  para o novo NAT (o dialog de erro informa o "NAT compativel" do exe).
- O fix descarta migrações que o exe não conhece. Até hoje são só alargamentos de
  coluna; se um dia uma migração criar tabela/coluna que a geração SPED usa, o
  caminho certo é **atualizar o Gerente do servidor**, não confiar no fix.
- Bancos afetados conhecidos em 07/07: joaopedro (282), sabugi (282), remigio (282),
  je (285 — build 737; o fix remove 6 linhas nesse caso).
