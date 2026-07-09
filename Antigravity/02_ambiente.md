# Ambiente de Produção

## Pastas Críticas

| Pasta | Função | Status |
|-------|--------|--------|
| `C:\SpedGenerator` | Código em produção (não editar diretamente) | ✅ |
| `C:\Backups_Novo` | Backups .backup dos clientes (fonte principal) | ✅ |
| `C:\ACS_Exporta` | SPEDs gerados + arquivos de estado do daemon | ✅ |
| `C:\SpedGenerator\Bancos` | Cópia temporária antes do pg_restore (pode ser eliminada — ver 06) | ✅ vazia |
| `C:\ACSSoft\Sintese\Gerente SPED` | ACS Gerente padrão | ✅ |
| `C:\ACSSoft\Sintese\GerenteDM` | ACS versão DM | ❌ não existe |
| `C:\ACSSoft\Sintese\Gerente659` | ACS versão 659 | ❌ não existe |

**Pasta de desenvolvimento (source code):**  
`C:\Users\User 2\Documents\Claude\Projects\SpedGeneretor`

## Arquivos de Estado (todos em C:\ACS_Exporta\)

| Arquivo | Conteúdo |
|---------|----------|
| `gerados.json` | Tracking de empresas: status, motivo, tentativas |
| `daemon_state.json` | PID, ciclo atual, próximo ciclo |
| `progresso.json` | Progresso do ciclo em execução |
| `progresso_backup.json` | Status dos downloads de backup |
| `spedgenerator.lock` | PID do daemon (lockfile) |
| `daemon.log` | Log fallback (erros não capturados) |
| `bancos_ativos.json` | Bancos PG restaurados e ativos |
| `empresas_fila.json` | Fila atual de empresas |

**Log principal (rotativo):** `C:\SpedGenerator\spedgenerator.log`

## Configurações (.env)

```env
SUPABASE_URL=https://clxoqogbypebxmpowjls.supabase.co
SUPABASE_KEY=<service_role_key>
PG_PASSWORD=123
BACKUP_DIR=C:\Backups_Novo
PG_BIN_DIR=C:\Program Files\PostgreSQL\15\bin
ACS_EXE_PATH=C:\ACSSoft\Sintese\Gerente SPED\gerente.exe
ACS_INI_PATH=C:\ACSSoft\Sintese\Gerente SPED\acsgerente.ini
LOCAL_BACKUP_DIR=C:\SpedGenerator\Bancos
SPED_EXPORT_DIR=C:\ACS_Exporta
DISABLE_REMOTE_BACKUP=True
```

## Versões

| Componente | Versão |
|------------|--------|
| PostgreSQL | 15 (`pg_restore (PostgreSQL) 15.18`) |
| Python | 3.13 (`C:\Users\SERVIDOR SPED\AppData\Local\Programs\Python\Python313\python.exe`) |
| PostgreSQL 14 | ❌ NÃO instalado |

## Servidores Remotos

**`servidores.json`** — fonte de verdade para conexão remota:
```json
{
  "padrao": { "host": "pgsql.e-prosys.com", "port": 5432, "user": "postgres" },
  "santavitoria": { "host": "187.45.181.113", "port": 5432 }
}
```

**`bancos_nomes.json`** — mapeamento de nome_base → dbname (case-correto para o PG).  
Foi corrigido em 2026-06-03: todos os hosts estavam com o IP antigo `131.100.25.4` (inacessível).  
Agora todos apontam para `pgsql.e-prosys.com`.

## Task Scheduler

| Tarefa | Script | Horário |
|--------|--------|---------|
| `SpedGenerator_Backup` | `atualizar_backups.bat` → `backup_manager.py --todos` | Diário 08:00 |

**Daemon principal** não é task agendada — roda via `iniciar_daemon.bat` no startup do Windows.
