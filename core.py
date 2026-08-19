"""
core.py — Utilidades do Laboratório de Macroeconometria
Carregamento, transformações e helpers compartilhados.
"""
import numpy as np
import pandas as pd


# ----------------------------------------------------------------------------
# Carregamento
# ----------------------------------------------------------------------------
def carregar_base(arquivo, col_data="data"):
    """Lê xlsx/csv e devolve DataFrame indexado por data (mensal)."""
    nome = getattr(arquivo, "name", str(arquivo))
    if nome.lower().endswith(".csv"):
        df = pd.read_csv(arquivo)
    else:
        df = pd.read_excel(arquivo)

    if col_data not in df.columns:
        cands = [c for c in df.columns if "dat" in str(c).lower()]
        if not cands:
            raise ValueError("Nenhuma coluna de data encontrada.")
        col_data = cands[0]

    df[col_data] = pd.to_datetime(df[col_data])
    df = df.sort_values(col_data).set_index(col_data)
    df.index.name = "data"
    df = df.apply(pd.to_numeric, errors="coerce")
    return df


def carregar_base_df(df, col_data="data"):
    """
    Normaliza um DataFrame já carregado (ex.: baixado do GitHub):
    identifica a coluna de data, indexa e força tipagem numérica.
    """
    df = df.copy()
    if col_data not in df.columns:
        cands = [c for c in df.columns if "dat" in str(c).lower()]
        if not cands:
            raise ValueError("Nenhuma coluna de data encontrada.")
        col_data = cands[0]
    df[col_data] = pd.to_datetime(df[col_data])
    df = df.sort_values(col_data).set_index(col_data)
    df.index.name = "data"
    return df.apply(pd.to_numeric, errors="coerce")


def resumo_cobertura(df):
    """Tabela com cobertura temporal e estatísticas de cada coluna."""
    linhas = []
    for c in df.columns:
        s = df[c].dropna()
        if s.empty:
            linhas.append({"variavel": c, "n": 0, "inicio": None, "fim": None,
                           "media": np.nan, "desvio": np.nan,
                           "min": np.nan, "max": np.nan, "%_faltante": 100.0})
            continue
        linhas.append({
            "variavel": c, "n": int(s.size),
            "inicio": s.index.min().date(), "fim": s.index.max().date(),
            "media": s.mean(), "desvio": s.std(),
            "min": s.min(), "max": s.max(),
            "%_faltante": 100 * df[c].isna().mean(),
        })
    return pd.DataFrame(linhas)


# ----------------------------------------------------------------------------
# Transformações
# ----------------------------------------------------------------------------
TRANSFORMACOES = {
    "nivel": "Nível (sem transformação)",
    "diff": "1ª diferença: Δy = y(t) − y(t−1)",
    "diff2": "2ª diferença: Δ²y",
    "log": "Logaritmo natural: ln(y)",
    "logdiff": "Log-diferença (≈ variação % mensal): Δln(y)×100",
    "logdiff12": "Log-diferença 12m (variação % anual): [ln(y_t)−ln(y_t−12)]×100",
    "pct": "Variação percentual mensal",
    "pct12": "Variação percentual em 12 meses",
    "ma3": "Média móvel de 3 meses",
    "ma12": "Média móvel de 12 meses",
    "zscore": "Padronização (z-score): (y−média)/desvio",
    "acum12": "Soma móvel 12 meses (acumula taxas mensais)",
    "hp_ciclo": "Ciclo Hodrick-Prescott (desvio da tendência)",
    "hp_tendencia": "Tendência Hodrick-Prescott",
}


def aplicar_transformacao(s: pd.Series, tipo: str, lamb_hp: float = 14400):
    """Aplica transformação a uma série. lamb_hp=14400 é o padrão mensal."""
    s = s.astype(float)
    if tipo == "nivel":
        return s
    if tipo == "diff":
        return s.diff()
    if tipo == "diff2":
        return s.diff().diff()
    if tipo == "log":
        return np.log(s.where(s > 0))
    if tipo == "logdiff":
        return np.log(s.where(s > 0)).diff() * 100
    if tipo == "logdiff12":
        return np.log(s.where(s > 0)).diff(12) * 100
    if tipo == "pct":
        return s.pct_change() * 100
    if tipo == "pct12":
        return s.pct_change(12) * 100
    if tipo == "ma3":
        return s.rolling(3).mean()
    if tipo == "ma12":
        return s.rolling(12).mean()
    if tipo == "zscore":
        return (s - s.mean()) / s.std()
    if tipo == "acum12":
        return s.rolling(12).sum()
    if tipo in ("hp_ciclo", "hp_tendencia"):
        from statsmodels.tsa.filters.hp_filter import hpfilter
        sc = s.dropna()
        if sc.size < 8:
            return pd.Series(np.nan, index=s.index)
        ciclo, tend = hpfilter(sc, lamb=lamb_hp)
        out = ciclo if tipo == "hp_ciclo" else tend
        return out.reindex(s.index)
    raise ValueError(f"Transformação desconhecida: {tipo}")


def sufixo(tipo):
    return {"nivel": "", "diff": "_d", "diff2": "_dd", "log": "_ln",
            "logdiff": "_dln", "logdiff12": "_dln12", "pct": "_pct",
            "pct12": "_pct12", "ma3": "_ma3", "ma12": "_ma12",
            "zscore": "_z", "acum12": "_ac12",
            "hp_ciclo": "_hpc", "hp_tendencia": "_hpt"}.get(tipo, f"_{tipo}")


def construir_spread(df, col_longo, col_curto, nome=None):
    """Spread (inclinação) = taxa longa − taxa curta."""
    nome = nome or f"spread_{col_longo}_{col_curto}"
    return pd.Series(df[col_longo] - df[col_curto], name=nome)


def gerar_lags(df, colunas, lags):
    """Gera defasagens explícitas."""
    out = pd.DataFrame(index=df.index)
    for c in colunas:
        for k in lags:
            out[f"{c}_lag{k}"] = df[c].shift(k)
    return out


def amostra_comum(df, colunas, inicio=None, fim=None, dropna=True):
    """Recorta o painel para a interseção de observações disponíveis."""
    sub = df[list(colunas)].copy()
    if inicio is not None:
        sub = sub[sub.index >= pd.Timestamp(inicio)]
    if fim is not None:
        sub = sub[sub.index <= pd.Timestamp(fim)]
    if dropna:
        sub = sub.dropna()
    return sub


def formata_p(p):
    """Formata p-valor com estrelas de significância."""
    if pd.isna(p):
        return "—"
    est = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""
    return f"{p:.4f}{est}"
