# =============================================================================
# postgres_manager.py - Criar DB, restaurar backup, dropar DB
# =============================================================================

import subprocess
import logging
import os
import shutil
from threading import RLock
from config import PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_BIN_DIR, LOCAL_BACKUP_DIR

logger = logging.getLogger(__name__)

_pg_env = {**os.environ, "PGPASSWORD": PG_PASSWORD}

# Serializa createdb/dropdb: CREATE DATABASE concorrente a partir do mesmo
# template1 falha no PostgreSQL ("template1 is being accessed by other users").
# RLock porque criar_banco chama dropar_banco. O pg_restore NAO entra na trava
# (e a parte demorada e pode rodar em paralelo entre bancos diferentes).
_ddl_lock = RLock()


def _run(cmd: list[str], desc: str) -> bool:
    """Executa comando subprocess, loga saida, retorna True se sucesso."""
    logger.info(f"{desc}: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            env=_pg_env,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            logger.error(f"{desc} FALHOU (codigo {result.returncode}):\n{result.stderr}")
            return False
        logger.info(f"{desc} OK")
        return True
    except subprocess.TimeoutExpired:
        logger.error(f"{desc} TIMEOUT (>10 min)")
        return False
    except Exception as e:
        logger.error(f"{desc} excecao: {e}")
        return False


def copiar_backup_local(backup_rede: str) -> str | None:
    """Copia .backup da rede para pasta local. Retorna caminho local."""
    os.makedirs(LOCAL_BACKUP_DIR, exist_ok=True)

    # Verifica espaco em disco antes de copiar
    try:
        tamanho_mb = os.path.getsize(backup_rede) / (1024 * 1024)
        usage = shutil.disk_usage(LOCAL_BACKUP_DIR)
        livre_mb = usage.free / (1024 * 1024)
        if livre_mb < tamanho_mb + 500:  # 500MB buffer
            logger.error(f"Disco insuficiente: {livre_mb:.0f}MB livre, precisa {tamanho_mb:.0f}MB + 500MB buffer")
            return None
    except Exception:
        pass  # Na duvida, continua

    nome_arquivo = os.path.basename(backup_rede)
    destino = os.path.join(LOCAL_BACKUP_DIR, nome_arquivo)
    try:
        logger.info(f"Copiando backup: {backup_rede} -> {destino}")
        shutil.copy2(backup_rede, destino)
        logger.info(f"Backup copiado: {destino}")
        return destino
    except Exception as e:
        logger.error(f"Erro ao copiar backup: {e}")
        return None


def db_existe(nome_db: str) -> bool:
    """Verifica se banco ja existe no PostgreSQL local."""
    psql = os.path.join(PG_BIN_DIR, "psql.exe")
    cmd = [
        psql, "-h", PG_HOST, "-p", str(PG_PORT), "-U", PG_USER,
        "-tAc", f"SELECT 1 FROM pg_database WHERE datname='{nome_db}'"
    ]
    try:
        result = subprocess.run(cmd, env=_pg_env, capture_output=True, text=True, timeout=15)
        return result.stdout.strip() == "1"
    except Exception:
        return False


def _desconectar_sessoes(nome_db: str):
    """Forca desconexao de todas sessoes no banco."""
    psql = os.path.join(PG_BIN_DIR, "psql.exe")
    cmd = [
        psql, "-h", PG_HOST, "-p", str(PG_PORT), "-U", PG_USER,
        "-c", f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{nome_db}' AND pid <> pg_backend_pid();"
    ]
    try:
        subprocess.run(cmd, env=_pg_env, capture_output=True, text=True, timeout=10)
        logger.info(f"Sessoes em '{nome_db}' desconectadas")
    except Exception:
        pass


def criar_banco(nome_db: str) -> bool:
    """Cria banco PostgreSQL local se nao existir."""
    with _ddl_lock:
        if db_existe(nome_db):
            logger.warning(f"Banco '{nome_db}' ja existe - sera recriado.")
            _desconectar_sessoes(nome_db)
            dropar_banco(nome_db)

        createdb = os.path.join(PG_BIN_DIR, "createdb.exe")
        cmd = [
            createdb,
            "-h", PG_HOST,
            "-p", str(PG_PORT),
            "-U", PG_USER,
            nome_db,
        ]
        return _run(cmd, f"createdb '{nome_db}'")


def restaurar_backup(nome_db: str, backup_path: str) -> bool:
    """
    Restaura arquivo .backup no banco PostgreSQL local.
    Timeout dinamico: 10 min base + 2 min por 100MB. Maximo 90 min.
    """
    import time as _time

    pg_restore = os.path.join(PG_BIN_DIR, "pg_restore.exe")
    cmd = [
        pg_restore,
        "-h", PG_HOST,
        "-p", str(PG_PORT),
        "-U", PG_USER,
        "-d", nome_db,
        "--no-owner",
        "--no-acl",
        backup_path,
    ]

    desc = f"pg_restore -> '{nome_db}'"
    logger.info(f"{desc}: {' '.join(cmd)}")

    try:
        tamanho_mb = os.path.getsize(backup_path) / (1024 * 1024)
        # Timeout dinamico ampliado: 30min base + 5min/100MB, max 120min pra evitar timeouts
        timeout_s = min(1800 + int(tamanho_mb / 100 * 300), 7200)
        logger.info(f"Backup: {tamanho_mb:.1f} MB — timeout={timeout_s}s")

        proc = subprocess.Popen(
            cmd,
            env=_pg_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        inicio = _time.time()
        ultimo_log = inicio

        while proc.poll() is None:
            _time.sleep(5)
            agora = _time.time()
            elapsed = int(agora - inicio)

            if elapsed > timeout_s:
                logger.error(f"{desc} TIMEOUT apos {elapsed}s (limite={timeout_s}s)")
                proc.kill()
                proc.wait()
                return False

            if agora - ultimo_log >= 60:
                logger.info(f"{desc}: ainda rodando... ({elapsed}s/{timeout_s}s)")
                ultimo_log = agora

        elapsed = int(_time.time() - inicio)
        _, stderr = proc.communicate()

        if proc.returncode != 0:
            logger.error(f"{desc} FALHOU apos {elapsed}s (codigo {proc.returncode}):\n{stderr.decode('utf-8', errors='replace')}")
            return False

        logger.info(f"{desc} OK ({elapsed}s para {tamanho_mb:.1f} MB)")
        return True

    except Exception as e:
        logger.error(f"{desc} excecao: {e}")
        return False


def dropar_banco(nome_db: str) -> bool:
    """Dropa banco PostgreSQL local (limpeza apos gerar SPED)."""
    with _ddl_lock:
        dropdb = os.path.join(PG_BIN_DIR, "dropdb.exe")
        cmd = [
            dropdb,
            "-h", PG_HOST,
            "-p", str(PG_PORT),
            "-U", PG_USER,
            "--if-exists",
            nome_db,
        ]
        return _run(cmd, f"dropdb '{nome_db}'")


def fix_saldo_mes_inventario(nome_db: str) -> bool:
    """
    Insere registro fim-do-mês-anterior em saldo_mes para TODAS empresas e estoques.
    ACS valida existência do registro antes de gerar SPED.
    Cruza empresa×estoque da tabela estoques, insere com produto dummy e valores zero.
    ON CONFLICT DO NOTHING — seguro rodar múltiplas vezes.
    """
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT,
            user=PG_USER, password=PG_PASSWORD,
            dbname=nome_db,
        )
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("""
            DO $$
            DECLARE
                v_data DATE := date_trunc('month', CURRENT_DATE) - INTERVAL '1 day';
            BEGIN
                INSERT INTO saldo_mes (cod_empresa, data, cod_estoque, cod_produto, saldo, custo, custo_medio, preco)
                SELECT e.cod_empresa, v_data, e.codigo, '00000000000001', 0, 0, 0, 0
                FROM estoques e
                WHERE NOT EXISTS (
                    SELECT 1 FROM saldo_mes sm
                    WHERE sm.cod_empresa = e.cod_empresa
                      AND sm.cod_estoque = e.codigo
                      AND sm.data = v_data
                )
                ON CONFLICT DO NOTHING;
            END $$;
        """)
        cur.close()
        conn.close()
        logger.info(f"fix_saldo_mes_inventario OK em '{nome_db}'")
        return True
    except Exception as e:
        logger.warning(f"fix_saldo_mes_inventario falhou em '{nome_db}': {e}")
        return False


def fix_nat_compatibilidade(nome_db: str) -> bool:
    """
    Compatibiliza o NAT do banco com o gerente.exe instalado (build 720 / NAT 279).
    O ACS calcula "NAT do Banco" contando as linhas de 'atualizacoes' (e reescreve
    versao.nat com esse count no startup). Bancos de clientes com Gerente mais novo
    (ex.: build 728 aplicou 3 migracoes em 07/2026) chegam com count > 279 e o ACS
    recusa abrir ("Versao (NAT) do Banco Sintese incompativel!").
    Remove as linhas MAIS RECENTES (data_hora) ate count == ACS_NAT_COMPATIVEL e
    alinha versao.nat. As migracoes extras observadas so alargam colunas — o schema
    novo continua legivel pelo exe antigo. So roda em bancos _local/_teste (copias
    descartaveis); o banco do servidor nunca e tocado.
    Validado em joaopedro_teste (2026-07-07): com as 3 linhas removidas o Gerente
    abriu e mostrou a tela de login normalmente.
    """
    from config import ACS_NAT_COMPATIVEL
    if not (nome_db.endswith("_local") or nome_db.endswith("_teste")):
        logger.warning(f"fix_nat_compatibilidade recusado: '{nome_db}' nao e copia _local/_teste")
        return False
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT,
            user=PG_USER, password=PG_PASSWORD,
            dbname=nome_db,
        )
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM atualizacoes")
        total = cur.fetchone()[0]
        excedente = total - ACS_NAT_COMPATIVEL
        if excedente <= 0:
            logger.info(f"fix_nat_compatibilidade OK em '{nome_db}' (NAT {total} <= {ACS_NAT_COMPATIVEL}, nada a fazer)")
        else:
            cur.execute("""
                SELECT id, versao, build_atual, id_cartao FROM atualizacoes
                ORDER BY data_hora DESC NULLS LAST LIMIT %s
            """, (excedente,))
            removidas = cur.fetchall()
            cur.execute("""
                DELETE FROM atualizacoes WHERE (id, versao) IN (
                    SELECT id, versao FROM atualizacoes
                    ORDER BY data_hora DESC NULLS LAST LIMIT %s
                )
            """, (excedente,))
            cur.execute("UPDATE versao SET nat = %s", (ACS_NAT_COMPATIVEL,))
            detalhes = "; ".join(f"{r[3] or r[0]} (build {r[2]})" for r in removidas)
            logger.info(
                f"fix_nat_compatibilidade em '{nome_db}': NAT {total} -> {ACS_NAT_COMPATIVEL}, "
                f"{excedente} atualizacao(oes) removida(s): {detalhes}"
            )
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.warning(f"fix_nat_compatibilidade falhou em '{nome_db}': {e}")
        return False


def fix_aberturas_medicao(nome_db: str) -> bool:
    """
    Garante que aberturas tenha registro pra CADA empresa×tanque×dia do mês SPED.
    1. Corrige zeros existentes (UPDATE volume=1 WHERE volume=0)
    2. Insere dias faltantes pra cada empresa×tanque (INSERT com volume=1)
    Banco é temporário — sem risco em corrigir tudo.
    Necessario antes de gerar SPED Fiscal — ACS valida medicoes lancadas.
    """
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT,
            user=PG_USER, password=PG_PASSWORD,
            dbname=nome_db,
        )
        conn.autocommit = True
        cur = conn.cursor()

        # 1. Corrige zeros existentes
        cur.execute("UPDATE aberturas SET volume = 1 WHERE volume = 0;")
        updated = cur.rowcount

        # 2. Insere datas_aberturas faltantes (FK de aberturas)
        cur.execute("""
            INSERT INTO datas_aberturas (cod_empresa, data, medicao_gerada)
            SELECT DISTINCT e.cod_empresa, d.dia::date, 'N'
            FROM (SELECT DISTINCT cod_empresa FROM estoques) e
            CROSS JOIN generate_series(
                (date_trunc('month', CURRENT_DATE) - INTERVAL '1 month')::date,
                (date_trunc('month', CURRENT_DATE))::date,
                '1 day'::interval
            ) AS d(dia)
            WHERE NOT EXISTS (
                SELECT 1 FROM datas_aberturas da
                WHERE da.cod_empresa = e.cod_empresa
                  AND da.data = d.dia::date
            )
            ON CONFLICT DO NOTHING;
        """)

        # 3. Insere aberturas faltantes pra cada empresa×tanque×dia
        cur.execute("""
            INSERT INTO aberturas (cod_empresa, cod_tanque, data, cod_combustivel, volume, altura)
            SELECT t.cod_empresa, t.codigo, d.dia::date, t.cod_combustivel, 1, 0
            FROM tanques t
            CROSS JOIN generate_series(
                (date_trunc('month', CURRENT_DATE) - INTERVAL '1 month')::date,
                (date_trunc('month', CURRENT_DATE))::date,
                '1 day'::interval
            ) AS d(dia)
            WHERE NOT EXISTS (
                SELECT 1 FROM aberturas a
                WHERE a.cod_empresa = t.cod_empresa
                  AND a.cod_tanque = t.codigo
                  AND a.data = d.dia::date
            )
            ON CONFLICT DO NOTHING;
        """)
        inserted = cur.rowcount

        cur.close()
        conn.close()
        logger.info(f"fix_aberturas_medicao OK em '{nome_db}' (updated={updated}, inserted={inserted})")
        return True
    except Exception as e:
        logger.warning(f"fix_aberturas_medicao falhou em '{nome_db}': {e}")
        return False


def fix_prestacao_update_alias(nome_db: str) -> bool:
    """
    Cria o tipo prestacao_wrapper, adiciona a coluna 'p' de tipo prestacao_wrapper na tabela 'prestacao'
    e instala o trigger BEFORE UPDATE para redirecionar atualizações da coluna fake 'p' para as colunas reais.
    Evita erro do PostgreSQL 'column p of relation prestacao does not exist' quando o ACS executa:
    UPDATE prestacao p SET p.conferido = 'S' ...
    """
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT,
            user=PG_USER, password=PG_PASSWORD,
            dbname=nome_db,
        )
        conn.autocommit = True
        cur = conn.cursor()

        # 1. Verifica se a tabela prestacao existe
        cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'prestacao';")
        if not cur.fetchone():
            cur.close()
            conn.close()
            logger.info(f"Tabela 'prestacao' nao existe em '{nome_db}' — skip fix")
            return True

        # 2. Recria o tipo prestacao_wrapper e a coluna 'p' com a definição completa de campos
        cur.execute("DROP TRIGGER IF EXISTS trg_prestacao_alias ON prestacao;")
        cur.execute("ALTER TABLE prestacao DROP COLUMN IF EXISTS p;")
        cur.execute("DROP TYPE IF EXISTS prestacao_wrapper;")

        cur.execute("""
            CREATE TYPE prestacao_wrapper AS (
                cod_empresa           character(2),
                data                  date,
                turno                 character(1),
                cod_grupo_pdv         character(3),
                cod_operador          character(3),
                conferido             character(1),
                bloqueado             character(1),
                descontos             numeric(9,2),
                receb_tk              numeric(9,2),
                sangria_tk            numeric(9,2)
            );
        """)
        logger.info("Tipo 'prestacao_wrapper' criado/atualizado")

        # 3. Adiciona a coluna 'p'
        cur.execute("ALTER TABLE prestacao ADD COLUMN p prestacao_wrapper;")
        logger.info("Coluna 'p' adicionada na tabela 'prestacao'")

        # 4. Cria a função do trigger
        cur.execute("""
            CREATE OR REPLACE FUNCTION trg_prestacao_update_alias()
            RETURNS TRIGGER AS $$
            BEGIN
                IF NOT (NEW.p IS NULL) THEN
                    IF (NEW.p).conferido IS NOT NULL THEN
                        NEW.conferido := (NEW.p).conferido;
                    END IF;
                    IF (NEW.p).bloqueado IS NOT NULL THEN
                        NEW.bloqueado := (NEW.p).bloqueado;
                    END IF;
                    IF (NEW.p).descontos IS NOT NULL THEN
                        NEW.descontos := (NEW.p).descontos;
                    END IF;
                    IF (NEW.p).receb_tk IS NOT NULL THEN
                        NEW.receb_tk := (NEW.p).receb_tk;
                    END IF;
                    IF (NEW.p).sangria_tk IS NOT NULL THEN
                        NEW.sangria_tk := (NEW.p).sangria_tk;
                    END IF;
                    NEW.p := NULL;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)

        # 5. Cria o trigger
        cur.execute("""
            CREATE TRIGGER trg_prestacao_alias
            BEFORE UPDATE ON prestacao
            FOR EACH ROW
            EXECUTE FUNCTION trg_prestacao_update_alias();
        """)
        logger.info("Trigger 'trg_prestacao_alias' criado/atualizado")

        cur.close()
        conn.close()
        logger.info(f"fix_prestacao_update_alias OK em '{nome_db}'")
        return True
    except Exception as e:
        logger.warning(f"fix_prestacao_update_alias falhou em '{nome_db}': {e}")
        return False


def consultar_cnpjs_empresa(nome_db: str) -> list[str]:
    """
    Retorna lista de CNPJs (14 dígitos, só números) de todas empresas no banco local.
    Auto-descobre nome da coluna CNPJ (varia entre versões do ACS: cgc, cnpj, etc).
    Retorna lista vazia se falhar (validação de CNPJ será pulada, não bloqueia).
    """
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT,
            user=PG_USER, password=PG_PASSWORD,
            dbname=nome_db,
        )
        cur = conn.cursor()
        # Descobre nome da coluna CNPJ
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'empresa'
            AND column_name IN ('cgc', 'cnpj', 'cpf_cnpj', 'nr_cnpj')
            LIMIT 1
        """)
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            logger.warning(f"Coluna CNPJ não encontrada na tabela empresa em '{nome_db}'")
            return []

        col = row[0]
        cur.execute(f"SELECT DISTINCT {col} FROM empresa WHERE {col} IS NOT NULL AND {col} != ''")
        cnpjs = []
        for row in cur.fetchall():
            # Strip formatação (pontos, barras, traços) — mantém só dígitos
            cnpj = "".join(c for c in str(row[0]) if c.isdigit())
            if len(cnpj) == 14:
                cnpjs.append(cnpj)
        cur.close()
        conn.close()
        if cnpjs:
            logger.info(f"CNPJs em '{nome_db}': {cnpjs}")
        else:
            logger.warning(f"Nenhum CNPJ válido (14 dígitos) em '{nome_db}'")
        return cnpjs
    except Exception as e:
        logger.warning(f"Erro ao consultar CNPJs em '{nome_db}': {e}")
        return []


def _normalizar_nome(nome: str) -> str:
    """Remove prefixos POSTO/DM e normaliza acentos pra matching."""
    import unicodedata
    n = nome.strip().upper()
    # Remove acentos
    n = unicodedata.normalize("NFKD", n)
    n = "".join(c for c in n if not unicodedata.combining(c))
    # Strip prefixos comuns (ordem importa: mais longo primeiro)
    for prefix in ["AUTO POSTO DM ", "AUTO POSTO ", "POSTO DM ", "DM POSTO ", "POSTO ", "DM "]:
        if n.startswith(prefix):
            n = n[len(prefix):]
            break
    return n.strip()


# Abreviações comuns nos bancos locais
_ABBREV = {
    "SJ":  ["SAO JOAO", "SAO JOÃO", "SÃO JOAO", "SÃO JOÃO"],
    "SM":  ["SAO MIGUEL", "SÃO MIGUEL"],
    "BV":  ["BOA VIAGEM", "BOA VISTA"],
    "SL":  ["SANTA LUZIA", "SAO LUIZ"],
}

# Abreviacoes inline que devem ser expandidas antes de comparar
_INLINE_ABBREV = {
    "NSA": "NOSSA",
    "SRA": "SENHORA",
    "SR": "SENHOR",
    "STO": "SANTO",
    "STA": "SANTA",
    "PE": "PADRE",
    "DR": "DOUTOR",
    "LTDA": "",
    "S/A": "",
}


def descobrir_nome_empresa(nome_db: str, nome_empresa_supabase: str) -> str | None:
    """
    Conecta no banco local restaurado e retorna nome_fantasia real da empresa
    que corresponde ao nome do Supabase. Usado pra selecionar no combo do login ACS.

    Estrategias (em ordem de confianca):
      1. Match exato
      2. Prefixo: local eh prefixo do Supabase (ex: "POSTO DM VIII" ~ "POSTO DM VIII (SOUZA)")
      3. Containment: local contido no Supabase (ex: "DM POCINHOS" em "POSTO DM POCINHOS")
      4. Core normalizado: strip POSTO/DM, compara nucleo (ex: "15 DE NOVEMBRO" = "15 DE NOVEMBRO")
      5. Parentetico: extrai conteudo de () do Supabase e tenta match (ex: "(DM III)" → "POSTO DM III")
      6. Abreviacao: expande sigla local e compara (ex: "SJ" → "SAO JOAO")
      7. Supabase contido no local (fallback original)

    Retorna None se nao encontrar.
    """
    try:
        import psycopg2
        import re
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT,
            user=PG_USER, password=PG_PASSWORD,
            dbname=nome_db,
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT codigo, nome_fantasia
            FROM empresa
            ORDER BY codigo ASC
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            logger.error(f"Tabela empresa vazia em '{nome_db}'")
            return None

        from mapping_config import obter_empresa_mapeada
        nome_empresa_mapeada = obter_empresa_mapeada(nome_empresa_supabase)
        alvo = nome_empresa_mapeada.strip().upper()

        # Log mapping completo pra auditoria
        logger.info(f"Empresas em '{nome_db}' ({len(rows)} total):")
        for codigo, nome_fant in rows:
            logger.info(f"  codigo={codigo} nome_fantasia='{nome_fant}'")

        # --- 1. Match exato ---
        for codigo, nome_fant in rows:
            if (nome_fant or "").strip().upper() == alvo:
                logger.info(f"Match exato: '{nome_empresa_supabase}' = '{nome_fant}' (codigo={codigo})")
                return (nome_fant or "").strip()

        # --- 1b. Match por Interseccao de Palavras Especificas (Maior Interseccao) ---
        # Evita que "POSTO EXTREMO II - MAMANGUAPE" case com "POSTO EXTREMO" (codigo 05) via prefixo,
        # forcando o casamento com "POSTO EXTREMO MAMANGUAPE" (codigo 03).
        palavras_desconsiderar = {"POSTO", "AUTO", "LTDA", "S/A", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "E", "DE", "DO", "DA", "-", ""}
        alvo_norm = _normalizar_nome(alvo)
        alvo_words = {w for w in alvo_norm.split() if w not in palavras_desconsiderar}
        
        melhor_match_intersec = None
        max_intersec_len = 0
        
        for codigo, nome_fant in rows:
            fant = (nome_fant or "").strip().upper()
            fant_norm = _normalizar_nome(fant)
            fant_words = {w for w in fant_norm.split() if w not in palavras_desconsiderar}
            
            # So considera se houver pelo menos 1 palavra significativa em comum
            intersec = alvo_words.intersection(fant_words)
            if intersec:
                if len(intersec) > max_intersec_len:
                    max_intersec_len = len(intersec)
                    melhor_match_intersec = (codigo, nome_fant)
                elif len(intersec) == max_intersec_len and melhor_match_intersec:
                    # Desempate pelo tamanho total do nome: prefere o que tem menor diferenca de tamanho com o alvo
                    diff_atual = abs(len(fant_norm) - len(alvo_norm))
                    diff_melhor = abs(len(_normalizar_nome(melhor_match_intersec[1])) - len(alvo_norm))
                    if diff_atual < diff_melhor:
                        melhor_match_intersec = (codigo, nome_fant)
                        
        if melhor_match_intersec and max_intersec_len >= 1:
            codigo, nome_fant = melhor_match_intersec
            logger.info(f"Match interseccao de palavras: '{nome_empresa_supabase}' ~ '{nome_fant}' (codigo={codigo}) [com {max_intersec_len} palavra(s) em comum]")
            return (nome_fant or "").strip()

        # --- 2. Prefixo: local eh prefixo do Supabase (word boundary) ---
        #    Pega match mais longo pra evitar "POSTO DM V" casar com "POSTO DM VIII"
        melhor_match = None
        melhor_len = 0
        for codigo, nome_fant in rows:
            fant = (nome_fant or "").strip().upper()
            if not fant:
                continue
            if alvo.startswith(fant):
                pos = len(fant)
                if pos >= len(alvo) or alvo[pos] in (" ", "(", "-"):
                    if len(fant) > melhor_len:
                        melhor_match = (codigo, nome_fant)
                        melhor_len = len(fant)
        if melhor_match:
            codigo, nome_fant = melhor_match
            logger.warning(f"Match prefixo: '{nome_empresa_supabase}' ~ '{nome_fant}' (codigo={codigo})")
            return (nome_fant or "").strip()

        # --- 3. Containment: local contido no Supabase (word boundary) ---
        #    Ex: "DM POCINHOS" contido em "POSTO DM POCINHOS"
        melhor_match = None
        melhor_len = 0
        for codigo, nome_fant in rows:
            fant = (nome_fant or "").strip().upper()
            if not fant or len(fant) < 4:
                continue
            if fant in alvo:
                pos = alvo.index(fant)
                end = pos + len(fant)
                if (pos == 0 or alvo[pos - 1] in (" ", "(")) and \
                   (end >= len(alvo) or alvo[end] in (" ", ")", "-")):
                    if len(fant) > melhor_len:
                        melhor_match = (codigo, nome_fant)
                        melhor_len = len(fant)
        if melhor_match:
            codigo, nome_fant = melhor_match
            logger.warning(f"Match containment: '{nome_empresa_supabase}' ~ '{nome_fant}' (codigo={codigo})")
            return (nome_fant or "").strip()

        # --- 4. Core normalizado: strip POSTO/DM, compara nucleo ---
        #    Ex: "DM POSTO 15 DE NOVEMBRO" → "15 DE NOVEMBRO" = "POSTO DM 15 DE NOVEMBRO" → "15 DE NOVEMBRO"
        alvo_core = _normalizar_nome(alvo)
        if alvo_core:
            for codigo, nome_fant in rows:
                fant_core = _normalizar_nome((nome_fant or "").strip())
                if fant_core and alvo_core == fant_core:
                    logger.warning(f"Match core: '{nome_empresa_supabase}' ~ '{nome_fant}' (codigo={codigo}) [core='{alvo_core}']")
                    return (nome_fant or "").strip()

        # --- 4b. Core com expansao de abreviacoes inline ---
        #    Ex: "NSA SRA APARECIDA" → "NOSSA SENHORA APARECIDA" = "NOSSA SENHORA APARECIDA"
        def _expandir(texto):
            palavras = texto.split()
            return " ".join(_INLINE_ABBREV.get(p, p) for p in palavras if _INLINE_ABBREV.get(p, p))

        alvo_exp = _expandir(alvo_core) if alvo_core else ""
        if alvo_exp and alvo_exp != alvo_core:
            for codigo, nome_fant in rows:
                fant_core = _normalizar_nome((nome_fant or "").strip())
                fant_exp = _expandir(fant_core) if fant_core else ""
                if alvo_exp and fant_exp and alvo_exp == fant_exp:
                    logger.warning(f"Match abrev-inline: '{nome_empresa_supabase}' ~ '{nome_fant}' (codigo={codigo}) ['{alvo_core}'→'{alvo_exp}']")
                    return (nome_fant or "").strip()
            # Tambem tenta: expandir so um lado
            for codigo, nome_fant in rows:
                fant_core = _normalizar_nome((nome_fant or "").strip())
                if fant_core and alvo_exp == fant_core:
                    logger.warning(f"Match abrev-inline: '{nome_empresa_supabase}' ~ '{nome_fant}' (codigo={codigo}) [expandido→'{alvo_exp}']")
                    return (nome_fant or "").strip()

        # --- 5. Parentetico: extrai conteudo de () e tenta match ---
        #    Ex: "POSTO DM ASSU (DM III)" → inner="DM III" → match "POSTO DM III"
        paren = re.search(r'\(([^)]+)\)', alvo)
        if paren:
            inner = paren.group(1).strip()
            inner_core = _normalizar_nome(inner)
            for codigo, nome_fant in rows:
                fant_core = _normalizar_nome((nome_fant or "").strip())
                if fant_core and inner_core and fant_core == inner_core:
                    logger.warning(f"Match parentetico: '{nome_empresa_supabase}' ~ '{nome_fant}' (codigo={codigo}) [inner='{inner}']")
                    return (nome_fant or "").strip()

        # --- 6. Abreviacao: expande sigla local, compara com Supabase ---
        #    Ex: local "POSTO DM SJ", SJ expande pra SAO JOAO, Supabase contem "SAO JOAO"
        alvo_norm = _normalizar_nome(alvo)
        for codigo, nome_fant in rows:
            fant = (nome_fant or "").strip().upper()
            fant_core = _normalizar_nome(fant)
            if not fant_core:
                continue
            # Pega ultima palavra do nome local como possivel sigla
            palavras = fant_core.split()
            if not palavras:
                continue
            sigla = palavras[-1]
            if sigla in _ABBREV:
                for expansao in _ABBREV[sigla]:
                    exp_norm = _normalizar_nome(expansao)
                    # Reconstroi nome local com expansao
                    fant_expandido = " ".join(palavras[:-1] + [exp_norm]) if len(palavras) > 1 else exp_norm
                    if alvo_norm == fant_expandido:
                        logger.warning(f"Match abreviacao: '{nome_empresa_supabase}' ~ '{nome_fant}' (codigo={codigo}) [{sigla}→{expansao}]")
                        return (nome_fant or "").strip()

        # --- 7. Supabase contido no local (fallback original) ---
        for codigo, nome_fant in rows:
            fant = (nome_fant or "").strip().upper()
            if alvo in fant:
                logger.warning(f"Match parcial: '{nome_empresa_supabase}' ~ '{nome_fant}' (codigo={codigo})")
                return (nome_fant or "").strip()

        # --- Nenhum match ---
        logger.error(f"Empresa '{nome_empresa_supabase}' nao encontrada em '{nome_db}'")
        return None

    except Exception as e:
        logger.error(f"Erro descobrir_nome_empresa em '{nome_db}': {e}")
        return None


def criar_e_restaurar(nome_base: str, backup_rede: str) -> bool:
    """
    Pipeline completo:
    1. Copia .backup da rede para pasta local
    2. Cria banco '{nome_base}_local'
    3. pg_restore do arquivo local
    Retorna True se tudo OK.
    """
    # 1. Copiar pra local
    backup_local = copiar_backup_local(backup_rede)
    if not backup_local:
        return False

    # 2. Criar banco
    nome_db = f"{nome_base.lower()}_local"
    if not criar_banco(nome_db):
        try:
            if os.path.exists(backup_local):
                os.remove(backup_local)
        except OSError:
            pass
        return False

    # 3. Restaurar do local
    sucesso = False
    try:
        if restaurar_backup(nome_db, backup_local):
            sucesso = True
        else:
            dropar_banco(nome_db)
    finally:
        # SEMPRE remove a cópia local do backup para liberar espaço em disco!
        try:
            if os.path.exists(backup_local):
                os.remove(backup_local)
                logger.info(f"Copia local do backup removida para liberar espaco: {backup_local}")
        except OSError as e:
            logger.warning(f"Nao foi possivel remover copia local do backup {backup_local}: {e}")

    return sucesso


def fix_controle_processos(nome_db: str) -> bool:
    """
    Limpa a tabela CONTROLE_PROCESSOS e instala um trigger BEFORE INSERT
    que auto-deleta linhas conflitantes, evitando o erro de unique constraint
    que crasha o gerente.exe silenciosamente.

    O ACS Gerente insere um lock durante o startup (AjustaEstrutura) e depois
    tenta inserir novamente para o processo de exportação. Sem o trigger,
    a segunda inserção viola a constraint e o processo morre.
    """
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT,
            user=PG_USER, password=PG_PASSWORD,
            dbname=nome_db,
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Verifica se a tabela controle_processos existe
        cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'controle_processos';")
        if not cur.fetchone():
            cur.close()
            conn.close()
            return True

        # 1. Limpa locks residuais do backup
        cur.execute("DELETE FROM controle_processos;")

        # 2. Cria trigger function que remove a linha conflitante antes do INSERT
        cur.execute("""
            CREATE OR REPLACE FUNCTION fn_controle_processos_upsert()
            RETURNS TRIGGER AS $$
            BEGIN
                DELETE FROM controle_processos
                WHERE processo = NEW.processo
                  AND cod_empresa = NEW.cod_empresa;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)

        # 3. Cria o trigger BEFORE INSERT (drop primeiro para ser idempotente)
        cur.execute("""
            DROP TRIGGER IF EXISTS trg_controle_processos_upsert
            ON controle_processos;
        """)
        cur.execute("""
            CREATE TRIGGER trg_controle_processos_upsert
            BEFORE INSERT ON controle_processos
            FOR EACH ROW
            EXECUTE FUNCTION fn_controle_processos_upsert();
        """)

        logger.info(f"fix_controle_processos OK em '{nome_db}' (trigger upsert instalado)")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.warning(f"fix_controle_processos falhou em '{nome_db}': {e}")
        return False

