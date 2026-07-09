# Arquitetura do SpedGenerator

## Visão Geral do Fluxo

```
[Supabase]
    │  Lista empresas com status="liberada"
    ▼
[main.py — Daemon 24/7]
    │  Ciclo a cada 5 min
    │
    ├─► [ETAPA 1 — Preparação] (ThreadPoolExecutor, paralelo)
    │       │
    │       ├── backup_finder.py → procura {nome_base}.backup em C:\Backups_Novo
    │       │       └── Se não existe → erro (DISABLE_REMOTE_BACKUP=True por padrão)
    │       │
    │       └── postgres_manager.py → pg_restore do backup para PostgreSQL local
    │               └── Cria banco local: {nome_base}_local
    │
    └─► [ETAPA 2 — Geração] (sequencial)
            │
            ├── acs_runner.py → abre ACS Gerente SPED via PyAutoGUI/pywinauto
            ├── Seleciona empresa, período, gera arquivo SPED
            └── file_manager.py → move arquivo para C:\ACS_Exporta\
```

## Componentes Principais

| Arquivo | Responsabilidade |
|---------|-----------------|
| `main.py` | Orquestrador central, loop daemon |
| `backup_finder.py` | Localiza arquivo .backup, valida freshness |
| `backup_manager.py` | pg_dump do servidor remoto → C:\Backups_Novo |
| `postgres_manager.py` | pg_restore para PostgreSQL local |
| `acs_runner.py` | Automação do ACS Gerente SPED |
| `tracking.py` | Rastreia tentativas/erros por empresa (gerados.json) |
| `banco_tracker.py` | Controla bancos PG restaurados (bancos_ativos.json) |
| `supabase_client.py` | Comunicação com Supabase |
| `config.py` | Carrega todas as variáveis do .env |
| `painel.py` | Interface de monitoramento (lê JSONs de estado) |

## Como os Backups Chegam em C:\Backups_Novo

**Dois processos independentes fazem isso:**

1. **`Backup Novo.bat`** — script manual/agendado, usa `pg_dump` direto com `pgsql.e-prosys.com`.  
   É a fonte primária e mais confiável.

2. **`backup_manager.py --todos`** — via Task Scheduler (`SpedGenerator_Backup`), roda diariamente às 08:00.  
   Usa `bancos_nomes.json` para resolver host/credenciais.

> O daemon (`main.py`) **nunca baixa backups** — ele só lê os que já estão em `C:\Backups_Novo`.  
> `DISABLE_REMOTE_BACKUP=True` é o comportamento correto nesta arquitetura.

## Tracking de Tentativas (regra crítica)

```python
# tracking.py linha 121
if tentativas >= 3:
    return True  # "já processada" — pula até amanhã
```

**Após 3 falhas no mesmo dia → empresa é ignorada até meia-noite.**  
Reset de emergência: apagar `C:\ACS_Exporta\gerados.json`.

## Versões do ACS Gerente

O campo `informacoes_sped` no Supabase define qual versão usar:

```json
// acs_versoes.json
{
  "padrao": "C:\\ACSSoft\\Sintese\\Gerente SPED",
  "DM":     "C:\\ACSSoft\\Sintese\\GerenteDM",
  "659":    "C:\\ACSSoft\\Sintese\\Gerente659"
}
```

> **Atenção:** `GerenteDM` e `Gerente659` não existem no servidor (apenas `Gerente SPED` existe).
