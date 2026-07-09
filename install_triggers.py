"""Install BEFORE INSERT trigger on controle_processos for all local databases."""
import psycopg2

PG = dict(host='localhost', port=5432, user='postgres', password='123')

# List all *_local databases
conn = psycopg2.connect(**PG, dbname='postgres')
conn.autocommit = True
cur = conn.cursor()
cur.execute("SELECT datname FROM pg_database WHERE datname LIKE '%_local'")
dbs = [r[0] for r in cur.fetchall()]
cur.close()
conn.close()

print(f"Found {len(dbs)} local databases: {dbs}")

TRIGGER_FN = """
CREATE OR REPLACE FUNCTION fn_controle_processos_upsert()
RETURNS TRIGGER AS $$
BEGIN
    DELETE FROM controle_processos
    WHERE processo = NEW.processo
      AND cod_empresa = NEW.cod_empresa;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

for db in dbs:
    try:
        c = psycopg2.connect(**PG, dbname=db)
        c.autocommit = True
        cr = c.cursor()
        cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'controle_processos'")
        if cr.fetchone():
            cr.execute("DELETE FROM controle_processos")
            cr.execute(TRIGGER_FN)
            cr.execute("DROP TRIGGER IF EXISTS trg_controle_processos_upsert ON controle_processos")
            cr.execute("""
                CREATE TRIGGER trg_controle_processos_upsert
                BEFORE INSERT ON controle_processos
                FOR EACH ROW
                EXECUTE FUNCTION fn_controle_processos_upsert()
            """)
            print(f"  {db}: trigger installed OK")
        else:
            print(f"  {db}: no controle_processos table")
        cr.close()
        c.close()
    except Exception as e:
        print(f"  {db}: ERROR - {e}")
