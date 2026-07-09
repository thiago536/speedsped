# SpedGenerator — Setup

## Pré-requisitos

- Python 3.11+
- PostgreSQL 15 instalado localmente
- AutoHotkey v2 instalado
- ACS Gerente instalado

## Instalação

```bash
pip install -r requirements.txt
```

## Configuração (config.py)

Edite `config.py` com seus valores:

| Campo | Descrição |
|---|---|
| `SUPABASE_URL` | URL do projeto Supabase |
| `SUPABASE_KEY` | service_role key (não a anon) |
| `BACKUP_DIR` | Pasta de rede com os .backup |
| `PG_PASSWORD` | Senha do postgres local |
| `PG_BIN_DIR` | Pasta bin do PostgreSQL 15 |
| `ACS_INI_PATH` | Caminho do acsgerente.ini |
| `ACS_EXE_PATH` | Caminho do ACSGerente.exe |
| `AHK_EXE_PATH` | Caminho do AutoHotkey64.exe |

## !! AÇÃO NECESSÁRIA: MenuNavegar.ahk !!

O arquivo `AHK/MenuNavegar.ahk` está como PLACEHOLDER.

Para ativá-lo, responda:
1. Qual o caminho exato de menu no ACS Gerente para SPED Fiscal?
   Ex: menu "Relatórios" → submenu "SPED" → item "SPED Fiscal"
2. E para SPED Contribuições?

Com isso, o script de navegação fica 100% funcional.

## Mapeamento nome_base → backup

Assumido: `nome_base` no Supabase = nome do arquivo `.backup` sem extensão.
- Ex: `nome_base = "FerreiraeTavares"` → backup = `FerreiraeTavares.backup` → DB = `FerreiraeTavares_local`

Se `nome_base` já inclui `_local` (ex: `"ferreira_local"`), edite em `backup_finder.py`:
```python
# Linha 36 — troque por:
nome_arquivo = f"{nome_base.replace('_local', '')}.backup"
```

## Executar

```bash
python main.py
```

Log salvo em `spedgenerator.log`.
