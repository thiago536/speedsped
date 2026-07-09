# =============================================================================
# mapping_config.py — Dicionário de De-Para e Configurações de Mapeamento Local
#
# Permite resolver divergências cadastrais entre o Supabase e as bases locais
# sem precisar alterar o schema ou os dados no Supabase.
# =============================================================================

# 1. BASES A IGNORAR: Bases de dados que devem ser completamente puladas.
# Exemplo: Bases do tipo Web que não possuem arquivo físico de backup.
BASES_IGNORAR = {
    "borborema",  # Aliança CG (Web, não possui backup físico)
    "veneza",     # Posto Veneza (não é nuvem e nem está na lista de liberados - ignorar)
}

# 2. DE-PARA DE BASES: Mapeia o 'nome_base' do Supabase para o nome real do backup local.
# Sintaxe: { "NomeNoSupabase": "NomeRealDoBackup" } (Insensível a maiúsculas/minúsculas)
MAPEAMENTO_BASES = {
    "jrcaicara": "jr",  # O banco JRcaicara na verdade usa o backup/banco 'jr'
    "meneizao": "rdl",  # Supabase diz 'Meneizao' mas o banco no servidor e 'RDL' (AUTO POSTO RDL LTDA, conferido 2026-06-11)
}

# 3. DE-PARA DE EMPRESAS: Mapeia o nome fantasia do Supabase para o nome fantasia interno
# gravado dentro da tabela 'empresa' no banco de dados local daquele posto.
# Sintaxe: { "NomeNoSupabase": "NomeInternoNoDelphi" }
MAPEAMENTO_EMPRESAS = {
    "POSTO DM ITAJÁ": "POSTO DM IV",         # DM Itajá é na verdade DM IV no banco
    "POSTO DM SANTA LUZIA": "POSTO DM VI",   # Santa Luzia é DM VI no banco
    "DM POSTO SAO MIGUEL JUCURUTU": "POSTO DM SM", # Jucurutu é DM SM no banco
    "POSTO DM ANGICOS": "POSTO DM V",        # DM Angicos é na verdade DM V no banco
    "POSTO PEDRO RAMOS": "AUTO POSTO JM",    # Pedro Ramos usa a base que tem 'AUTO POSTO JM' internamente
    "FERREIRA E TAVARES": "POSTO REIS",      # Base FerreiraeTavares tem só 'POSTO REIS' (CNPJ 20320813000176) internamente
}


def obter_base_mapeada(nome_base: str) -> str:
    """Retorna o nome da base real traduzido pelo mapeamento local."""
    nb_lower = (nome_base or "").strip().lower()
    return MAPEAMENTO_BASES.get(nb_lower, nb_lower)


def obter_empresa_mapeada(nome_empresa: str) -> str:
    """Retorna o nome fantasia interno traduzido pelo mapeamento local."""
    ne_strip = (nome_empresa or "").strip()
    return MAPEAMENTO_EMPRESAS.get(ne_strip, ne_strip)


def deve_ignorar_base(nome_base: str) -> bool:
    """Retorna True se a base de dados deve ser ignorada no processamento."""
    nb_lower = (nome_base or "").strip().lower()
    return nb_lower in BASES_IGNORAR
