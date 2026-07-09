# Ideia: Eliminar a Cópia para LOCAL_BACKUP_DIR

## O Problema Atual

O `postgres_manager.py` hoje faz:

```
C:\Backups_Novo\X.backup
        │
        │ shutil.copy (cópia desnecessária)
        ▼
C:\SpedGenerator\Bancos\X.backup
        │
        │ pg_restore
        ▼
PostgreSQL local (banco X_local)
        │
        │ delete da cópia
```

Isso desperdiça tempo e disco — às vezes centenas de MB por empresa.

## Por Que Existe

`LOCAL_BACKUP_DIR` faz sentido quando `BACKUP_DIR` é uma **pasta de rede** (share remoto, UNC path, drive mapeado).  
Nesse caso, copiar antes de restaurar evita:
- Lentidão durante o pg_restore (lê da rede linha a linha)
- Falha no meio se a rede cair

No servidor atual, **ambas as pastas são locais** → a cópia é redundante.

## A Simplificação

Remover a etapa de cópia e apontar o pg_restore direto para `C:\Backups_Novo`:

```
C:\Backups_Novo\X.backup
        │
        │ pg_restore (direto, sem cópia)
        ▼
PostgreSQL local (banco X_local)
```

### Mudança no código (`postgres_manager.py`)

Trocar de:
```python
# Copia para local antes de restaurar
local_path = os.path.join(LOCAL_BACKUP_DIR, os.path.basename(backup_path))
shutil.copy2(backup_path, local_path)
# ... pg_restore em local_path ...
os.remove(local_path)
```

Para:
```python
# pg_restore direto no arquivo de origem
# ... pg_restore em backup_path (C:\Backups_Novo\X.backup) ...
```

### O que muda no .env

`LOCAL_BACKUP_DIR` pode ser removido ou mantido apenas como documentação.

## Benefícios

| Antes | Depois |
|-------|--------|
| Cópia de centenas de MB antes de cada restore | Zero cópia |
| Disco: backup duplicado durante o processo | Backup original apenas |
| Tempo: +segundos/minutos por empresa | Direto ao restore |
| `C:\SpedGenerator\Bancos` precisa ter espaço | Pasta pode ser removida |

## Riscos / Quando NÃO fazer

- Se `BACKUP_DIR` mudar para um caminho de rede no futuro → reativar o copy
- Se o pg_restore corromper o .backup original (não acontece — pg_restore só lê) → sem risco

## Status

> Ideia discutida em 2026-06-03. Não implementada ainda.  
> Aguardando estabilização dos downloads e geração bem-sucedida dos SPEDs.
