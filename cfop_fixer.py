# -*- coding: utf-8 -*-
"""
cfop_fixer.py — Correcao automatica de "Departamentos sem CFOP" do ACS Gerente.

Quando o ACS valida a exportacao do SPED e encontra departamento fiscal sem o
CFOP configurado, ele grava um relatorio (Departamentos_Invalidos.txt) na pasta
do Gerente com linhas no formato:

    Departamentos sem CFOP ou campos obrigatorios em branco:
    Departamento: 019, CFOP: 5102

Este modulo parseia esses pares e cadastra o CFOP que falta no banco LOCAL
(_local) da empresa:
  1. Em `cfop_depto` (grid de detalhe fiscal): clona uma linha template do
     mesmo departamento/empresa (prioridade: CFOP do cabecalho correspondente >
     CFOP de mesmo 1o digito > qualquer linha) trocando so o cod_cfop.
  2. Em `departamentos` (cabecalho): preenche a coluna correspondente ao
     1o digito do CFOP (1xxx->cfop_compra_1, 2xxx->cfop_compra_2,
     5xxx->cfop_venda_5, 6xxx->cfop_venda_6) se estiver vazia.
     cfop_venda_nfce / cfop_venda_fora_estab NAO sao tocados (sem regra segura).

O banco `_local` e' uma copia descartavel (dropado e restaurado a cada ciclo),
entao gravar nele e' seguro; se o erro voltar apos novo restore, o pipeline
corrige de novo automaticamente.

Uso manual (para diagnostico):
    python cfop_fixer.py <nome_db> [caminho_relatorio.txt] [--apply]
    (sem --apply mostra o plano e faz rollback; caminho default e' o
     Departamentos_Invalidos.txt na pasta do ACS Gerente)
"""

import logging
import os
import re
import sys

from config import PG_HOST, PG_PORT, PG_USER, PG_PASSWORD

logger = logging.getLogger(__name__)

# Regex do relatorio do ACS — formato variavel, um par por linha
RE_PAR = re.compile(r"Departamento:\s*(\d+)\s*,\s*CFOP:\s*(\d+)", re.IGNORECASE)

# Colunas fiscais clonadas do template ao inserir novo CFOP em cfop_depto
CFOP_DEPTO_COLS = [
    "sit_tributaria", "cst_simples", "icms", "cst_pis", "pis", "cst_cofins", "cofins",
    "cod_receita_pis", "cod_receita_cofins", "cod_cred_pis", "cod_cred_cofins",
    "nat_bc_cred", "cod_contribuicao", "red_base_icms", "informa_base_pis_cofins",
    "informa_base_icms", "cod_conta", "aliq_fcp", "informa_base_fcp",
    "icms_efetivo", "red_base_icms_efetivo",
]

# 1o digito do CFOP -> coluna do cabecalho em `departamentos`
DIGITO_PARA_COLUNA_HEADER = {
    "1": "cfop_compra_1",
    "2": "cfop_compra_2",
    "5": "cfop_venda_5",
    "6": "cfop_venda_6",
}


class DepartamentoSemCfopError(Exception):
    """Relatorio 'Departamentos sem CFOP' detectado durante a geracao no ACS.

    A mensagem contem 'invalido' de proposito: se a correcao automatica nao
    resolver e a excecao propagar ate o tracking, e' classificada como erro
    DEFINITIVO de dados (mesma regra de NCM/produto).
    """

    def __init__(self, mensagem: str, pares: list[tuple[str, str]]):
        super().__init__(f"[CFOP invalido] {mensagem}")
        self.pares = pares


def extrair_pares(texto: str) -> list[tuple[str, str]]:
    """Extrai pares (depto, cfop) do texto do relatorio. Lista vazia se nao casar."""
    return [(m.group(1), m.group(2)) for m in RE_PAR.finditer(texto or "")]


def _variantes_codigo(codigo: str) -> list[str]:
    """Variantes de formatacao do codigo do depto (com/sem zero a esquerda)."""
    sem_zero = codigo.lstrip("0") or "0"
    return list({codigo, sem_zero})


def _table_exists(cur, table: str) -> bool:
    cur.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema='public' AND table_name=%s
    """, (table,))
    return cur.fetchone() is not None


def _corrigir_par(cur, resumo: list[str], depto: str, cfop: str) -> int:
    """Corrige um par (depto, cfop) no banco da conexao. Retorna qtd de mudancas."""
    variantes = _variantes_codigo(depto)
    placeholders = ", ".join(["%s"] * len(variantes))
    coluna_header = DIGITO_PARA_COLUNA_HEADER.get(cfop[0])
    mudancas = 0

    cur.execute(f"""
        SELECT codigo, descricao{', ' + coluna_header if coluna_header else ''}
        FROM departamentos
        WHERE trim(codigo) IN ({placeholders})
    """, variantes)
    depto_rows = cur.fetchall()

    if not depto_rows:
        resumo.append(f"depto {depto}: NAO existe na tabela departamentos deste banco")
        return 0

    for row in depto_rows:
        codigo_real, descricao = row[0], row[1]
        valor_header_atual = row[2] if coluna_header else None
        resumo.append(f"depto {str(codigo_real).strip()} ({str(descricao).strip()}) / CFOP alvo {cfop} — "
                      f"header {coluna_header or 'N/A'} = {valor_header_atual!r}")

        cur.execute(f"""
            SELECT DISTINCT cod_empresa FROM cfop_depto
            WHERE trim(cod_depto) IN ({placeholders})
        """, variantes)
        empresas = [r[0] for r in cur.fetchall()]

        # Depto sem NENHUMA linha no grid (caso Barauna): insere para todas as
        # empresas do banco, clonando o CFOP de outro departamento (fallback 4).
        if not empresas:
            cur.execute("SELECT DISTINCT cod_empresa FROM cfop_depto")
            empresas = [r[0] for r in cur.fetchall()]
            resumo.append(f"  depto sem linhas em cfop_depto — usando todas as empresas: {empresas}")

        for cod_empresa in empresas:
            cur.execute(f"""
                SELECT 1 FROM cfop_depto
                WHERE cod_empresa=%s AND trim(cod_depto) IN ({placeholders}) AND cod_cfop=%s
            """, [cod_empresa] + variantes + [cfop])
            if cur.fetchone():
                resumo.append(f"  empresa {cod_empresa}: CFOP {cfop} ja existe em cfop_depto")
                continue

            template_row, template_cfop = None, None

            # 1) template preferido: o CFOP que ja esta no campo do cabecalho
            if valor_header_atual and str(valor_header_atual).strip():
                cur.execute(f"""
                    SELECT {', '.join(CFOP_DEPTO_COLS)} FROM cfop_depto
                    WHERE cod_empresa=%s AND trim(cod_depto) IN ({placeholders}) AND cod_cfop=%s
                """, [cod_empresa] + variantes + [str(valor_header_atual).strip()])
                r = cur.fetchone()
                if r:
                    template_row, template_cfop = r, str(valor_header_atual).strip()

            # 2) qualquer CFOP existente do mesmo 1o digito
            if template_row is None:
                cur.execute(f"""
                    SELECT cod_cfop, {', '.join(CFOP_DEPTO_COLS)} FROM cfop_depto
                    WHERE cod_empresa=%s AND trim(cod_depto) IN ({placeholders}) AND cod_cfop LIKE %s
                    ORDER BY cod_cfop LIMIT 1
                """, [cod_empresa] + variantes + [f"{cfop[0]}%"])
                r = cur.fetchone()
                if r:
                    template_cfop, template_row = r[0], r[1:]

            # 3) ultimo recurso: qualquer linha do depto/empresa
            if template_row is None:
                cur.execute(f"""
                    SELECT cod_cfop, {', '.join(CFOP_DEPTO_COLS)} FROM cfop_depto
                    WHERE cod_empresa=%s AND trim(cod_depto) IN ({placeholders})
                    ORDER BY cod_cfop LIMIT 1
                """, [cod_empresa] + variantes)
                r = cur.fetchone()
                if r:
                    template_cfop, template_row = r[0], r[1:]

            # 4) OUTRO departamento da mesma empresa com o MESMO CFOP alvo
            #    (config fiscal e' por CFOP; clone exato de outro depto e' seguro)
            if template_row is None:
                cur.execute(f"""
                    SELECT cod_depto, {', '.join(CFOP_DEPTO_COLS)} FROM cfop_depto
                    WHERE cod_empresa=%s AND cod_cfop=%s
                    ORDER BY cod_depto LIMIT 1
                """, [cod_empresa, cfop])
                r = cur.fetchone()
                if r:
                    template_cfop = f"{cfop} (depto {str(r[0]).strip()})"
                    template_row = r[1:]

            if template_row is None:
                resumo.append(f"  empresa {cod_empresa}: SEM linha template em cfop_depto — nao inserido")
                continue

            cols_sql = ", ".join(["cod_empresa", "cod_depto", "cod_cfop"] + CFOP_DEPTO_COLS)
            vals_ph = ", ".join(["%s"] * (3 + len(CFOP_DEPTO_COLS)))
            cur.execute(
                f"INSERT INTO cfop_depto ({cols_sql}) VALUES ({vals_ph})",
                [cod_empresa, codigo_real, cfop] + list(template_row)
            )
            resumo.append(f"  empresa {cod_empresa}: INSERIDO CFOP {cfop} clonando de {template_cfop}")
            mudancas += 1

        if coluna_header and not (valor_header_atual and str(valor_header_atual).strip()):
            cur.execute(
                f"UPDATE departamentos SET {coluna_header}=%s WHERE trim(codigo) IN ({placeholders})",
                [cfop] + variantes
            )
            resumo.append(f"  cabecalho: {coluna_header} estava vazio -> preenchido com {cfop}")
            mudancas += 1

    return mudancas


def corrigir_cfops_banco(nome_db: str, pares: list[tuple[str, str]],
                         aplicar: bool = True) -> tuple[bool, list[str]]:
    """Cadastra no banco `nome_db` os CFOPs faltantes dos pares (depto, cfop).

    Retorna (corrigiu_algo, resumo). corrigiu_algo=False significa que nada
    foi/seria alterado (depto inexistente, sem template, ou tudo ja cadastrado)
    — nesse caso repetir a geracao nao resolve o erro.
    Com aplicar=False faz dry-run (rollback no final).
    """
    import psycopg2

    resumo = [f"Banco {nome_db} — pares: {pares} — modo {'APPLY' if aplicar else 'DRY-RUN'}"]
    if not pares:
        resumo.append("Nenhum par (depto, cfop) para corrigir")
        return False, resumo

    conn = psycopg2.connect(host=PG_HOST, port=PG_PORT,
                            user=PG_USER, password=PG_PASSWORD, dbname=nome_db)
    conn.autocommit = False
    try:
        cur = conn.cursor()
        if not _table_exists(cur, "departamentos") or not _table_exists(cur, "cfop_depto"):
            resumo.append("Tabelas departamentos/cfop_depto nao existem neste banco")
            conn.rollback()
            return False, resumo

        mudancas = 0
        for depto, cfop in pares:
            mudancas += _corrigir_par(cur, resumo, depto, cfop)

        if mudancas and aplicar:
            conn.commit()
            resumo.append(f"COMMIT: {mudancas} alteracao(oes) aplicada(s)")
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


RELATORIO_PADRAO = r"C:\ACSSoft\Sintese\Gerente SPED\Departamentos_Invalidos.txt"


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    aplicar = "--apply" in sys.argv

    if not args:
        print(__doc__)
        print("Uso: python cfop_fixer.py <nome_db> [relatorio.txt] [--apply]")
        sys.exit(1)

    nome_db = args[0]
    caminho = args[1] if len(args) > 1 else RELATORIO_PADRAO
    if not os.path.isfile(caminho):
        print(f"Relatorio nao encontrado: {caminho}")
        sys.exit(1)

    with open(caminho, encoding="utf-8", errors="replace") as f:
        pares = extrair_pares(f.read())
    print(f"Pares extraidos de {caminho}: {pares}")

    corrigiu, resumo = corrigir_cfops_banco(nome_db, pares, aplicar=aplicar)
    for linha in resumo:
        print(linha)
    print(f"Resultado: {'corrigiu/corrigiria algo' if corrigiu else 'nada a corrigir'}")


if __name__ == "__main__":
    main()
