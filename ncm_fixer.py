# -*- coding: utf-8 -*-
"""
ncm_fixer.py — Correcao automatica de "Codigo de barras dos produtos com NCM
invalido" do ACS Gerente.

Quando a exportacao do SPED aborta com esse erro, a mensagem lista os codigos
de barras dos produtos problematicos:

    Codigo de barras dos produtos com NCM invalido:: 1701068, 17896480671096

Este modulo localiza cada produto no banco LOCAL (_local) e troca o cod_ncm
pelo NCM dos produtos IRMAOS (mesmo grupo, descricao parecida) — ex.: caso
POSTO ANDRADE 2026-07-11: 'BASE P LIMPADOR PERFUMADO EUCALIPTO' estava com NCM
1012100 (7 digitos, capitulo de animais vivos) enquanto todas as outras
'BASE P LIMPADOR PERFUMADO *' do grupo usam 28289011.

Heuristica de escolha do NCM (conservadora — se nao houver irmao claro, NAO
corrige e o erro vira definitivo como antes):
  1. NCM (8 digitos, != atual) mais comum entre produtos do MESMO grupo cuja
     descricao compartilha as 3 primeiras palavras (depois tenta 2).
  2. Senao, NCM mais comum no grupo com pelo menos 2 ocorrencias.

O banco `_local` e' uma copia descartavel (re-restaurada a cada ciclo); o banco
do servidor NUNCA e' tocado — se o erro voltar apos novo restore, o pipeline
corrige de novo automaticamente.

Uso manual: python ncm_fixer.py <nome_db> "<barras separadas por virgula>" [--apply]
"""

import logging
import re
import sys

from config import PG_HOST, PG_PORT, PG_USER, PG_PASSWORD

logger = logging.getLogger(__name__)

# Mensagem do ACS — barras separadas por virgula depois de "::"
RE_NCM_ERRO = re.compile(r"NCM\s+invalido[:\s]*(?::)?\s*([\d\s,;]+)", re.IGNORECASE)


def extrair_barras_ncm(mensagem: str) -> list[str]:
    """Extrai os codigos de barras da mensagem de erro de NCM do ACS.
    Lista vazia se a mensagem nao for desse tipo de erro."""
    if "ncm" not in (mensagem or "").lower():
        return []
    m = RE_NCM_ERRO.search(mensagem)
    if not m:
        return []
    return [b.strip() for b in re.split(r"[,;]", m.group(1)) if b.strip().isdigit()]


def _palavras(texto: str) -> list[str]:
    return [p for p in re.sub(r"\s+", " ", (texto or "").strip().upper()).split(" ") if p]


def _localizar_produto(cur, barra: str):
    """Retorna (codigo, descricao, cod_ncm, cod_grupo) do produto da barra, ou None."""
    cur.execute("""
        SELECT codigo, descricao, cod_ncm, cod_grupo FROM produtos
        WHERE trim(cod_barras) = %s OR trim(cod_barras_caixa) = %s
        LIMIT 1
    """, (barra, barra))
    r = cur.fetchone()
    if r:
        return r
    # codigo alternativo (tabela codigos_produto)
    cur.execute("""
        SELECT p.codigo, p.descricao, p.cod_ncm, p.cod_grupo
        FROM codigos_produto cp JOIN produtos p ON p.codigo = cp.cod_produto
        WHERE trim(cp.cod_alternativo) = %s
        LIMIT 1
    """, (barra,))
    return cur.fetchone()


def _escolher_ncm(cur, codigo: str, descricao: str, ncm_atual: str, cod_grupo) -> str | None:
    """NCM de 8 digitos dos produtos irmaos; None se nao houver candidato claro."""
    ncm_atual = (ncm_atual or "").strip()
    palavras = _palavras(descricao)

    # Candidatos por prefixo de descricao. Desempate pela frequencia GLOBAL do
    # NCM no cadastro: irmao unico tambem pode estar com NCM lixo (caso
    # 'UZZILIM FLORES' com 97060000) — o NCM usado por mais produtos do banco
    # tende a ser o correto.
    def _top_ncm(where_desc: str, params: list) -> str | None:
        cur.execute(f"""
            SELECT s.ncm FROM (
                SELECT trim(cod_ncm) AS ncm, count(*) AS qtd FROM produtos
                WHERE cod_grupo = %s AND codigo <> %s
                  {where_desc}
                  AND length(trim(cod_ncm)) = 8 AND trim(cod_ncm) ~ '^[0-9]+$'
                  AND trim(cod_ncm) <> %s
                GROUP BY 1
            ) s
            WHERE s.qtd >= 2 OR (SELECT count(*) FROM produtos p2
                                 WHERE trim(p2.cod_ncm) = s.ncm) >= 2
            ORDER BY s.qtd DESC,
                     (SELECT count(*) FROM produtos p2
                      WHERE trim(p2.cod_ncm) = s.ncm) DESC
            LIMIT 1
        """, params)
        r = cur.fetchone()
        return r[0] if r else None

    # 1. Irmaos por prefixo de descricao (3 palavras, depois 2)
    for n in (3, 2):
        if len(palavras) < n:
            continue
        prefixo = " ".join(palavras[:n]) + "%"
        ncm = _top_ncm("AND upper(trim(descricao)) LIKE %s",
                       [cod_grupo, codigo, prefixo, ncm_atual])
        if ncm:
            return ncm

    # 1b. Primeira palavra como PREFIXO (>=5 letras): casa abreviacoes do
    #     cadastro, ex. 'DETERG EM PO ...' ~ 'DETERGENTE EM PO ...'
    if palavras and len(palavras[0]) >= 5:
        ncm = _top_ncm("AND upper(trim(descricao)) LIKE %s",
                       [cod_grupo, codigo, palavras[0] + "%", ncm_atual])
        if ncm:
            return ncm

    # 2. NCM dominante do grupo (minimo 2 ocorrencias)
    cur.execute("""
        SELECT trim(cod_ncm) AS ncm, count(*) AS qtd FROM produtos
        WHERE cod_grupo = %s AND codigo <> %s
          AND length(trim(cod_ncm)) = 8 AND trim(cod_ncm) ~ '^[0-9]+$'
          AND trim(cod_ncm) <> %s
        GROUP BY 1 ORDER BY 2 DESC LIMIT 1
    """, (cod_grupo, codigo, ncm_atual))
    r = cur.fetchone()
    if r and r[1] >= 2:
        return r[0]
    return None


def corrigir_ncms_banco(nome_db: str, barras: list[str],
                        aplicar: bool = True) -> tuple[bool, list[str]]:
    """Corrige o cod_ncm dos produtos das barras no banco `nome_db`.

    Retorna (corrigiu_algo, resumo). corrigiu_algo=False = nada foi/seria
    alterado (produto nao achado ou sem irmao claro) — repetir a geracao nao
    resolveria. Com aplicar=False faz dry-run (rollback no final).
    """
    import psycopg2

    resumo = [f"Banco {nome_db} — barras: {barras} — modo {'APPLY' if aplicar else 'DRY-RUN'}"]
    if not barras:
        resumo.append("Nenhum codigo de barras para corrigir")
        return False, resumo

    conn = psycopg2.connect(host=PG_HOST, port=PG_PORT,
                            user=PG_USER, password=PG_PASSWORD, dbname=nome_db)
    conn.autocommit = False
    try:
        cur = conn.cursor()
        mudancas = 0
        for barra in barras:
            prod = _localizar_produto(cur, barra)
            if not prod:
                resumo.append(f"barra {barra}: produto NAO encontrado (produtos/codigos_produto)")
                continue
            codigo, descricao, ncm_atual, cod_grupo = prod
            desc = (descricao or "").strip()
            novo_ncm = _escolher_ncm(cur, codigo, desc, ncm_atual, cod_grupo)
            if not novo_ncm:
                resumo.append(f"barra {barra} ({desc}): NCM atual {ncm_atual!r} — "
                              f"SEM irmao claro no grupo {cod_grupo}, nao corrigido")
                continue
            cur.execute("UPDATE produtos SET cod_ncm=%s WHERE codigo=%s", (novo_ncm, codigo))
            resumo.append(f"barra {barra} ({desc}): NCM {str(ncm_atual).strip()!r} -> "
                          f"{novo_ncm} (irmaos do grupo {str(cod_grupo).strip()})")
            mudancas += 1

        if mudancas and aplicar:
            conn.commit()
            resumo.append(f"COMMIT: {mudancas} produto(s) corrigido(s)")
        else:
            conn.rollback()
            resumo.append(f"ROLLBACK ({'dry-run' if not aplicar else 'nada a alterar'}) — "
                          f"{mudancas} alteracao(oes) simulada(s)")
        return mudancas > 0, resumo
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    aplicar = "--apply" in sys.argv
    if len(args) < 2:
        print(__doc__)
        print('Uso: python ncm_fixer.py <nome_db> "<barras separadas por virgula>" [--apply]')
        sys.exit(1)
    barras = [b.strip() for b in args[1].split(",") if b.strip()]
    corrigiu, resumo = corrigir_ncms_banco(args[0], barras, aplicar=aplicar)
    for linha in resumo:
        print(linha)
    print(f"Resultado: {'corrigiu/corrigiria algo' if corrigiu else 'nada a corrigir'}")


if __name__ == "__main__":
    main()
