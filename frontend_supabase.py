# =============================================================================
# frontend_supabase.py — Frontend visual para gerenciar empresas no Supabase
# Uso: streamlit run frontend_supabase.py
# =============================================================================

import os
import sys
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# Carrega .env
_base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_base_dir, ".env"))

from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------

@st.cache_resource
def get_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def carregar_empresas() -> pd.DataFrame:
    resp = get_client().table("empresas").select("*").order("id").execute()
    data = resp.data or []
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    return df


def salvar_alteracoes(emp_id: int, campos: dict):
    get_client().table("empresas").update(campos).eq("id", emp_id).execute()


# ---------------------------------------------------------------------------
# Config pagina
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="SpedGenerator Admin",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------------------------------
# CSS customizado
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .stMetric { background: #f0f2f6; padding: 10px; border-radius: 8px; }
    div[data-testid="stDataFrame"] { width: 100% !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("SpedGenerator — Admin Supabase")

# ---------------------------------------------------------------------------
# Carregar dados
# ---------------------------------------------------------------------------

if "df" not in st.session_state or st.sidebar.button("Recarregar dados", use_container_width=True):
    st.session_state.df = carregar_empresas()

df = st.session_state.df

if df.empty:
    st.error("Nenhuma empresa encontrada no Supabase")
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar — Filtros
# ---------------------------------------------------------------------------

st.sidebar.header("Filtros")

# Status
todos_status = sorted(df["status"].dropna().unique().tolist())
status_selecionados = st.sidebar.multiselect(
    "Status",
    options=todos_status,
    default=todos_status,
)

# Busca por nome
busca_nome = st.sidebar.text_input("Buscar por nome", "")

# Filtro nome_base preenchido
apenas_nuvem = st.sidebar.checkbox("Apenas com nome_base (Nuvem)", False)

# Aplicar filtros
df_filtrado = df[df["status"].isin(status_selecionados)]
if busca_nome:
    df_filtrado = df_filtrado[
        df_filtrado["nome"].str.contains(busca_nome, case=False, na=False)
    ]
if apenas_nuvem:
    df_filtrado = df_filtrado[
        df_filtrado["nome_base"].fillna("").str.strip().astype(bool)
    ]

# ---------------------------------------------------------------------------
# Metricas
# ---------------------------------------------------------------------------

col1, col2, col3, col4, col5 = st.columns(5)

contagem = df["status"].value_counts()
col1.metric("Total", len(df))
col2.metric("Geradas", contagem.get("gerada", 0))
col3.metric("Liberadas", contagem.get("liberada", 0))
col4.metric("Nao liberadas", contagem.get("nao_liberada", 0))
col5.metric("Erros", contagem.get("erro", 0))

st.markdown("---")

# ---------------------------------------------------------------------------
# Tabela principal — editavel
# ---------------------------------------------------------------------------

COLUNAS_VISIVEIS = ["id", "nome", "status", "nome_base", "informacoes_sped", "data_liberacao", "armazenamento"]
colunas_existentes = [c for c in COLUNAS_VISIVEIS if c in df_filtrado.columns]

df_view = df_filtrado[colunas_existentes].copy()

# Formata data
if "data_liberacao" in df_view.columns:
    df_view["data_liberacao"] = df_view["data_liberacao"].apply(
        lambda x: str(x)[:10] if pd.notna(x) and x else ""
    )

st.subheader(f"Empresas ({len(df_view)} de {len(df)})")

STATUS_OPTIONS = ["liberada", "gerada", "em_processo", "erro", "nao_liberada"]

editado = st.data_editor(
    df_view,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    disabled=["id", "nome"],
    column_config={
        "id": st.column_config.NumberColumn("ID", width="small"),
        "nome": st.column_config.TextColumn("Nome", width="large"),
        "status": st.column_config.SelectboxColumn(
            "Status",
            options=STATUS_OPTIONS,
            width="medium",
            required=True,
        ),
        "nome_base": st.column_config.TextColumn("Base", width="medium"),
        "informacoes_sped": st.column_config.TextColumn("Info SPED", width="medium"),
        "data_liberacao": st.column_config.TextColumn("Liberacao", width="medium"),
        "armazenamento": st.column_config.TextColumn("Armazenamento", width="medium"),
    },
    key="tabela_empresas",
)

# ---------------------------------------------------------------------------
# Detectar e salvar alteracoes
# ---------------------------------------------------------------------------

# Compara editado com original
alteracoes = []
for idx_edit in editado.index:
    row_edit = editado.loc[idx_edit]
    row_orig = df_view.loc[idx_edit]
    emp_id = int(row_edit["id"])

    campos_alterados = {}
    for col in ["status", "nome_base", "informacoes_sped", "armazenamento"]:
        if col in row_edit and col in row_orig:
            val_edit = row_edit[col] if pd.notna(row_edit[col]) else ""
            val_orig = row_orig[col] if pd.notna(row_orig[col]) else ""
            if str(val_edit) != str(val_orig):
                campos_alterados[col] = val_edit

    if campos_alterados:
        alteracoes.append((emp_id, row_edit["nome"], campos_alterados))

if alteracoes:
    st.markdown("---")
    st.subheader(f"Alteracoes pendentes ({len(alteracoes)})")

    for emp_id, nome, campos in alteracoes:
        detalhes = ", ".join(f"**{k}** = `{v}`" for k, v in campos.items())
        st.markdown(f"- [{emp_id}] {nome}: {detalhes}")

    col_save, col_cancel = st.columns([1, 3])
    if col_save.button("Salvar alteracoes", type="primary", use_container_width=True):
        progresso = st.progress(0)
        for i, (emp_id, nome, campos) in enumerate(alteracoes):
            salvar_alteracoes(emp_id, campos)
            progresso.progress((i + 1) / len(alteracoes))
        st.success(f"{len(alteracoes)} empresa(s) atualizada(s)")
        # Recarrega
        st.session_state.df = carregar_empresas()
        st.rerun()

    if col_cancel.button("Descartar", use_container_width=True):
        st.session_state.df = carregar_empresas()
        st.rerun()

# ---------------------------------------------------------------------------
# Acao em lote
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("Acao em lote")

col_lote1, col_lote2, col_lote3 = st.columns(3)

status_de = col_lote1.selectbox("De status", STATUS_OPTIONS, index=0, key="lote_de")
status_para = col_lote2.selectbox("Para status", STATUS_OPTIONS, index=1, key="lote_para")

empresas_lote = df[df["status"] == status_de]
col_lote3.metric(f"Empresas com '{status_de}'", len(empresas_lote))

if len(empresas_lote) > 0 and status_de != status_para:
    if st.button(
        f"Alterar {len(empresas_lote)} empresas de '{status_de}' para '{status_para}'",
        type="secondary",
    ):
        progresso = st.progress(0)
        for i, (_, row) in enumerate(empresas_lote.iterrows()):
            salvar_alteracoes(int(row["id"]), {"status": status_para})
            progresso.progress((i + 1) / len(empresas_lote))
        st.success(f"{len(empresas_lote)} empresa(s) alterada(s)")
        st.session_state.df = carregar_empresas()
        st.rerun()
