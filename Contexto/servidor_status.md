---
timestamp: 2026-06-04 11:20:00
maquina: SERVIDOR (C:\SpedGenerator)
status: PROBLEMA SISTEMICO — ACS MORRE DURANTE GERACAO EM TODOS OS POSTOS
---

## ESTADO ATUAL

Daemon PID 4232 rodando. LAISXII em geração agora (iniciou 11:10:34).
Histórico hoje: BELL e LAISXII ambos com o mesmo padrão de falha.

## Timeline completa do problema (AMBOS POSTOS)

```
1. Login OK
2. Formulário preenchido OK  
3. Click OK (Fiscal) OK
4. Click Sim (Confirmacao) OK
5. Dados do SPED apareceu e confirmado OK
6. "Aguardando geracao SPED" começa
7. ACS fica ATIVO por ~200s (gerando query interna)
8. ACS fica IDLE — processo gerente.exe NÃO existe mais
9. NENHUM arquivo .txt criado em C:\ACS_Exporta
10. Timeout 600s → registra como erro
```

## Fixes aplicados que funcionaram

- [OK] Login com `_focar_janela` — SetForegroundWindow error resolvido
- [OK] `_confirmar_atencao` sem "Aviso" em TITULOS_CONFIRMACAO — loop resolvido
- [OK] TITULOS_AVISO cobrindo "Atenção"/"Atencao"
- [OK] Monitoramento de arquivo em SPED_EXPORT_DIR (`import os` + `from config import SPED_EXPORT_DIR`)

## Problema atual — ACS encerra sem gerar arquivo

### Evidências:
- gerente.exe AUSENTE durante "Aguardando geracao" (verificado em 11:18)
- C:\ACS_Exporta: zero arquivos .txt após 200s de geração
- Acontece com BELL (bell_local, 249MB) E com LAISXII (laisxii_local, 708MB)
- Permissões C:\ACS_Exporta: OK (Authenticated Users: Modify)
- Caminho exportação no ini: `[Exportacao] Fiscal=C:\ACS_Exporta` — correto

### Logs ACS internos (C:\ACSSoft\Sintese\Gerente SPED\Log\):
- `Guardiao_04062026.txt`: "Falha ao acessar o serviço! Retorno: (1060) O serviço especificado não existe" — TODO startup
- `AjustaEstrutura_04062026.txt`: erro SQL `column "p" of relation "prestacao" does not exist` — ocorre em bell_local
- `VALIDA_ESTRUTURA_04062026.txt`: lock obtido/liberado rapidamente — estrutura OK
- `Tarefas_04062026.txt`: "Monitor de Tarefas já iniciado em outro micro" em alguns runs

### Hipóteses restantes:
A) **ACS encountra erro SQL durante geração SPED** (query de geração falha, ACS fecha silenciosamente)
B) **DialogHandler está fechando um dialog que causa saída do ACS** — precisa verificar
C) **Guardião service ausente interfere na geração** — improvável mas possível
D) **ACS escrevendo em subpasta ou caminho diferente** — improvável (template ini claro)

## Situação das empresas
- 20 liberadas no Supabase
- 19 com erro (tracking hoje) — serão retentadas amanhã
- LAISXII: gerando agora
- TEIMOSAO: próximo (base=laisxii_local, mesmo banco que LAISXII)
- POSTO SAO FRANCISCO BELEM: nome_base=None, aguardando Breno
