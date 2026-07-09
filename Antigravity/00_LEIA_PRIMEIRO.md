# Antigravity — Base de Conhecimento do SpedGenerator

> Leia este arquivo antes de qualquer outro. Ele define a ordem de leitura e o propósito de cada documento.

## O que é o Antigravity?

É o agente Claude responsável por **monitorar, corrigir e evoluir** o SpedGenerator em produção.  
O nome vem da ideia de "ir contra a gravidade" — manter o sistema no ar 24/7 mesmo quando tudo quer cair.

## Ordem de Leitura

| # | Arquivo | Quando ler |
|---|---------|-----------|
| 1 | `01_arquitetura.md` | Sempre — é o mapa do sistema |
| 2 | `02_ambiente.md` | Sempre — paths, configs, versões |
| 3 | `03_diagnostico_checklist.md` | No início de cada sessão |
| 4 | `04_problemas_conhecidos.md` | Quando algo falha |
| 5 | `05_sessao_2026-06-03.md` | Histórico do que foi feito hoje |
| 6 | `06_ideia_simplificacao.md` | Próxima melhoria planejada |

## Regras do Antigravity

1. **Nunca edite código direto em produção** sem necessidade explícita — `C:\SpedGenerator` é produção.
2. **Sempre leia `ClaudeContext.md`** na raiz antes de começar.
3. **O daemon (PID variável) não deve ser reiniciado** sem motivo — ele é 24/7.
4. **`gerados.json` é o reset de emergência** — apagar força retry de todas as empresas.
5. **Backups ficam em `C:\Backups_Novo`** — não em `C:\SpedGenerator\Bancos` (pasta auxiliar temporária).
