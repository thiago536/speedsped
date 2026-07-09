# Contexto do Sistema SpedGenerator para o Claude

> [!IMPORTANT]
> **Instrução Primordial para o Agente:** Antes de iniciar qualquer alteração, debug ou execução neste projeto, leia este arquivo de contexto e execute as verificações de diagnóstico listadas abaixo. O seu objetivo principal inicial em qualquer sessão é garantir que o ambiente está saudável.

Este arquivo documenta toda a arquitetura, configuração de ambiente e as premissas atuais do projeto `SpedGenerator`, que funciona em produção 24/7 sem interrupção.

## 1. Visão Geral da Arquitetura
O SpedGenerator é um sistema que roda como Daemon (bloqueante) no servidor para automatizar o download de backups, restauração de bancos de dados PostgreSQL locais e geração de arquivos SPED no sistema Contábil/Fiscal (ACS).

- **`main.py`**: É o orquestrador central. Ele processa concorrentemente a etapa de "Preparação" (validação e atualização de bancos) utilizando `ThreadPoolExecutor` e depois processa de forma síncrona a "Geração" interagindo com o painel de interface (automação via PyAutoGUI/pywinauto, scripts como `acs_runner.py`).
- **`backup_finder.py` e `backup_manager.py`**: Responsáveis por gerenciar os backups. Se um backup não for encontrado ou estiver desatualizado localmente, o sistema tenta restaurá-lo.
- **Daemon State e Lockfile**: Para evitar instâncias simultâneas, o `main.py` gera um `lockfile` (`PID 660` como exemplo). Seu estado é compartilhado via `daemon_state.json` e o andamento dos backups via `progresso_backup.json`. Estes estados são consumidos pelo painel de monitoria (`painel.py`).

## 2. Configurações Críticas (Ambiente)
- **Servidor DNS do Banco em Nuvem**: Atualmente utilizamos `pgsql.e-prosys.com` (Substituiu o IP antigo `131.100.25.4`). **Não utilize IP antigo para backups.**
- **Falha de Conexão no Backup**: O ambiente configurou `DISABLE_REMOTE_BACKUP=True` por padrão para evitar travamentos caso não haja conexão ou o timeout do PostgreSQL ultrapasse os limites normais. Quando ativo, prioriza procurar backups locais.
- **Ambiente de Execução (24/7)**: O sistema é operado ininterruptamente no servidor. A automação das tarefas agendadas via PowerShell (ex: `_agendar_tarefas.bat`) é executada com `-ExecutionTimeLimit 0` (Infinito). 

## 3. Diretórios e Arquivos Essenciais (DEV vs PRODUÇÃO)
É **CRÍTICO** que você (Claude) entenda em qual diretório está trabalhando para não fazer edições no lugar errado ou se confundir com a duplicidade de caminhos:

- **Pasta de Desenvolvimento (Dev/Source)**: `c:\Users\User 2\Documents\Claude\Projects\SpedGeneretor`
  - **Onde atuar:** TODAS as alterações de código, debug local e criação de arquivos devem ser feitas NESTA pasta.
- **Pasta de Produção (Deploy)**: `C:\SpedGenerator`
  - **Onde não atuar:** Esta pasta é exclusiva do servidor em produção (Daemon 24/7). Nós apenas copiamos os arquivos para lá via scripts de deploy. Nunca edite o código diretamente nela, a menos que solicitado.
- **Pasta de Exportação ACS**: `C:\ACS_Exporta` (Onde o sistema ACS gera os arquivos).
- **Pasta de Backups Locais**: `C:\Backups_Novo` (Ou `LOCAL_BACKUP_DIR=C:\Users\User 2\Documents\Bancos` no .env local).
- **Binários do PostgreSQL**: Essenciais para o `pg_dump` e `pg_restore`. Localizados em `C:\Program Files\PostgreSQL\15\bin` (local) ou `14\bin` (servidor).

> [!CAUTION]
> A falta de qualquer uma das pastas vitais (`C:\ACS_Exporta`, ou a pasta correta de `LOCAL_BACKUP_DIR`) irá travar a automação, uma vez que ele precisa exportar ou restaurar os dados de alguma parte.

## 4. O Arquivo `.env`
No projeto você precisa checar o `.env` ou `.env.example`. Chaves principais exigidas:
```env
SUPABASE_URL=https://clxoqogbypebxmpowjls.supabase.co
SUPABASE_KEY=<sua-key>
PG_PASSWORD=123
LOCAL_BACKUP_DIR=C:\Users\User 2\Documents\Bancos  # Ou C:\Backups_Novo
DISABLE_REMOTE_BACKUP=True # Evita timeouts severos em rede fraca
```

---

## 5. Script de Diagnóstico e Verificação (O que VOCÊ, Claude, deve fazer)

> [!TIP]
> Se o usuário pedir para verificar o sistema, criar uma nova feature ou identificar um bug, execute uma checagem baseada nos passos abaixo (ou construa um rápido script Python de diagnóstico):

### Checklist de Diagnóstico:
1. **Verificação de Lockfile e Processos Zumbis**:
   - Houve uma interrupção bruta? O arquivo de lock existe impedindo `main.py` de reiniciar? O erro `Outra instância rodando (PID XXX)` indica isso.
2. **Saúde das Variáveis de Ambiente**:
   - `DISABLE_REMOTE_BACKUP` está `True` ou `False`?
   - O `LOCAL_BACKUP_DIR` aponta para a pasta correta do servidor? Essa pasta existe?
3. **Binários do PG**:
   - Execute o comando no terminal (ou verifique em Python): `pg_restore --version` e `pg_dump --version`. Eles precisam estar no `PATH`.
4. **Verificar os Estados JSON**:
   - O `daemon_state.json` e `progresso_backup.json` estão legíveis?
5. **Teste o Conexão Supabase**:
   - O Supabase está retornando a lista de empresas? Se não listar empresas, verifique se a tabela `empresas` existe com os devidos schemas de permissões (RLS) ou se a `SUPABASE_KEY` tem as claims `service_role`.
6. **DNS do PostgreSQL Cloud**:
   - Em `servidores.json` e no `Backup Novo.bat` a DNS está setada como `pgsql.e-prosys.com`?

### Como Identificar onde Falhou
- **Se falhou no Início:** Provavelmente erro de `.env`, DNS (`servidores.json`) incorreta ou lockfile.
- **Se falhou na Preparação (Download/Restore):** Timeout de rede (verificar logs do `backup_manager.py`), falta do `pg_restore`, ou falta do backup local (`backup_finder.py`).
- **Se falhou na Geração (Sped):** Automação travou (`acs_runner.py`), resolução da tela mudou (arquivos de screenshots `.png` como `current_screen.png`), ou pasta `C:\ACS_Exporta` ausente.

## 6. Procedimento de Deploy / Correções (Regras)
- Nunca deixe instâncias paradas ou quebre o fluxo 24/7.
- Quando modificar `main.py`, certifique-se de tratar `Exceptions` e avisar via logs de sistema, pois o usuário não estará sempre olhando.
- Qualquer alteração na infra (DNS, caminhos, IPs) tem de ser substituída em **massa**, principalmente nos arquivos em batch (`.bat`) que fazem agendamento do Windows.

---
**Fim do Contexto do Claude**. 
Siga sempre esse manual antes de escrever ou apagar código.
