# =============================================================================
# admin_supabase.py — Mini admin CLI para gerenciar empresas no Supabase
# Uso: python admin_supabase.py  OU  duplo-clique no AdminSupabase.exe
# =============================================================================

import os
import sys
import logging
from dotenv import load_dotenv

# Carrega .env do diretorio do exe (ou do script)
if getattr(sys, 'frozen', False):
    _base_dir = os.path.dirname(sys.executable)
else:
    _base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_base_dir, ".env"))

from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

logging.basicConfig(level=logging.WARNING)

_client: Client = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------

def listar_todas():
    """Lista todas as empresas."""
    resp = get_client().table("empresas").select("*").order("id").execute()
    return resp.data or []


def listar_por_status(status: str):
    """Lista empresas filtradas por status."""
    resp = (
        get_client().table("empresas")
        .select("*")
        .eq("status", status)
        .order("id")
        .execute()
    )
    return resp.data or []


def buscar_por_id(emp_id: int):
    """Busca empresa por ID."""
    resp = (
        get_client().table("empresas")
        .select("*")
        .eq("id", emp_id)
        .execute()
    )
    data = resp.data or []
    return data[0] if data else None


def buscar_por_nome(nome: str):
    """Busca empresas por nome (parcial, case-insensitive)."""
    resp = (
        get_client().table("empresas")
        .select("*")
        .ilike("nome", f"%{nome}%")
        .order("id")
        .execute()
    )
    return resp.data or []


# ---------------------------------------------------------------------------
# Alterações
# ---------------------------------------------------------------------------

def alterar_status(emp_id: int, novo_status: str):
    """Altera status de uma empresa."""
    resp = (
        get_client().table("empresas")
        .update({"status": novo_status})
        .eq("id", emp_id)
        .execute()
    )
    return resp.data


def alterar_campo(emp_id: int, campo: str, valor: str):
    """Altera campo genérico de uma empresa."""
    resp = (
        get_client().table("empresas")
        .update({campo: valor})
        .eq("id", emp_id)
        .execute()
    )
    return resp.data


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

CAMPOS_RESUMO = ["id", "nome", "status", "nome_base", "armazenamento", "data_liberacao", "informacoes_sped"]


def print_empresa(emp: dict, completo=False):
    """Imprime uma empresa formatada."""
    if completo:
        for k, v in emp.items():
            print(f"  {k}: {v}")
    else:
        emp_id = emp.get("id", "?")
        nome = emp.get("nome") or "?"
        status = emp.get("status") or "?"
        base = emp.get("nome_base") or ""
        info = emp.get("informacoes_sped") or "-"
        lib = emp.get("data_liberacao") or "-"
        # Trunca data pra ficar legivel
        if lib and len(lib) > 10:
            lib = lib[:10]
        print(f"  [{emp_id:>4}] {nome:<35} status={status:<12} base={base:<15} info={info:<20} lib={lib}")


def print_lista(empresas: list, completo=False):
    """Imprime lista de empresas."""
    if not empresas:
        print("  (nenhuma)")
        return
    for emp in empresas:
        print_empresa(emp, completo)
    print(f"\n  Total: {len(empresas)}")


def print_resumo(empresas: list):
    """Imprime resumo por status."""
    contagem = {}
    for emp in empresas:
        s = emp.get("status", "?")
        contagem[s] = contagem.get(s, 0) + 1
    print("\n  Resumo por status:")
    for status, qtd in sorted(contagem.items()):
        print(f"    {status:<15} {qtd}")
    print(f"    {'TOTAL':<15} {len(empresas)}")


# ---------------------------------------------------------------------------
# Menu interativo
# ---------------------------------------------------------------------------

MENU = """
========================================
  ADMIN SUPABASE — SpedGenerator
========================================

  1. Listar todas
  2. Listar por status
  3. Buscar por nome
  4. Buscar por ID (detalhes)
  5. Resumo (contagem por status)
  ---
  6. Alterar status
  7. Alterar campo
  8. Alterar status em lote
  ---
  0. Sair
"""


def input_int(prompt: str) -> int | None:
    val = input(prompt).strip()
    if not val:
        return None
    try:
        return int(val)
    except ValueError:
        print("  Valor invalido (esperado numero)")
        return None


def menu_listar_todas():
    empresas = listar_todas()
    print()
    print_lista(empresas)


def menu_listar_status():
    status = input("  Status (liberada/gerada/em_processo/erro): ").strip()
    if not status:
        return
    empresas = listar_por_status(status)
    print()
    print_lista(empresas)


def menu_buscar_nome():
    nome = input("  Nome (parcial): ").strip()
    if not nome:
        return
    empresas = buscar_por_nome(nome)
    print()
    print_lista(empresas)


def menu_buscar_id():
    emp_id = input_int("  ID: ")
    if emp_id is None:
        return
    emp = buscar_por_id(emp_id)
    if emp:
        print()
        print_empresa(emp, completo=True)
    else:
        print(f"  Empresa {emp_id} nao encontrada")


def menu_resumo():
    empresas = listar_todas()
    print_resumo(empresas)


def menu_alterar_status():
    emp_id = input_int("  ID da empresa: ")
    if emp_id is None:
        return
    emp = buscar_por_id(emp_id)
    if not emp:
        print(f"  Empresa {emp_id} nao encontrada")
        return
    print(f"  Empresa: {emp['nome']} (status atual: {emp['status']})")
    novo = input("  Novo status (liberada/gerada/em_processo/erro): ").strip()
    if not novo:
        return
    confirm = input(f"  Confirma alterar '{emp['nome']}' para '{novo}'? (s/n): ").strip().lower()
    if confirm != "s":
        print("  Cancelado")
        return
    alterar_status(emp_id, novo)
    print(f"  Status alterado: {emp['status']} -> {novo}")


def menu_alterar_campo():
    emp_id = input_int("  ID da empresa: ")
    if emp_id is None:
        return
    emp = buscar_por_id(emp_id)
    if not emp:
        print(f"  Empresa {emp_id} nao encontrada")
        return
    print(f"  Empresa: {emp['nome']}")
    print(f"  Campos disponiveis: {', '.join(emp.keys())}")
    campo = input("  Campo a alterar: ").strip()
    if not campo or campo not in emp:
        print("  Campo invalido")
        return
    print(f"  Valor atual: {emp[campo]}")
    valor = input("  Novo valor: ").strip()
    confirm = input(f"  Confirma alterar '{campo}' de '{emp[campo]}' para '{valor}'? (s/n): ").strip().lower()
    if confirm != "s":
        print("  Cancelado")
        return
    alterar_campo(emp_id, campo, valor)
    print(f"  Campo '{campo}' alterado")


def menu_alterar_lote():
    status_atual = input("  Status atual das empresas a alterar: ").strip()
    if not status_atual:
        return
    empresas = listar_por_status(status_atual)
    if not empresas:
        print(f"  Nenhuma empresa com status '{status_atual}'")
        return
    print(f"\n  {len(empresas)} empresa(s) com status '{status_atual}':")
    print_lista(empresas)
    novo = input(f"\n  Novo status para TODAS: ").strip()
    if not novo:
        return
    confirm = input(f"  Confirma alterar {len(empresas)} empresas de '{status_atual}' para '{novo}'? (s/n): ").strip().lower()
    if confirm != "s":
        print("  Cancelado")
        return
    for emp in empresas:
        alterar_status(emp["id"], novo)
        print(f"    [{emp['id']}] {emp['nome']} -> {novo}")
    print(f"  {len(empresas)} empresa(s) alteradas")


def main():
    print(MENU)
    while True:
        try:
            opcao = input("\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n  Saindo...")
            break

        if opcao == "0":
            print("  Saindo...")
            break
        elif opcao == "1":
            menu_listar_todas()
        elif opcao == "2":
            menu_listar_status()
        elif opcao == "3":
            menu_buscar_nome()
        elif opcao == "4":
            menu_buscar_id()
        elif opcao == "5":
            menu_resumo()
        elif opcao == "6":
            menu_alterar_status()
        elif opcao == "7":
            menu_alterar_campo()
        elif opcao == "8":
            menu_alterar_lote()
        elif opcao == "":
            continue
        else:
            print("  Opcao invalida")
            print(MENU)


if __name__ == "__main__":
    main()
