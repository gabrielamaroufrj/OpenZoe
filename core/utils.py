# core/utils.py

def formatar_data(valor):
    """Formata data para exibição (apenas YYYY-MM-DD)."""
    return str(valor).split()[0] if valor else ""

def formatar_tempo(valor):
    """Remove milissegundos da string de tempo."""
    return str(valor).split()[0].replace('.000000', '') if valor else ""