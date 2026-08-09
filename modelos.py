"""
modelos.py — Motor econométrico do Laboratório
Testes de raiz unitária, regressão, cointegração, VAR/SVAR, VECM,
modelos binários e regularização.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, kpss, coint, grangercausalitytests
from statsmodels.tsa.api import VAR
from statsmodels.tsa.vector_ar.vecm import coint_johansen, VECM, select_coint_rank
from statsmodels.stats.diagnostic import acorr_ljungbox, het_breuschpagan
from statsmodels.stats.stattools import jarque_bera, durbin_watson
from statsmodels.stats.outliers_influence import variance_inflation_factor


# ============================================================================
# 1. TESTES DE RAIZ UNITÁRIA / ESTACIONARIEDADE
# ============================================================================
def teste_adf(serie, regressao="c", maxlag=None, autolag="AIC"):
    """
    Augmented Dickey-Fuller.
    H0: a série TEM raiz unitária (é NÃO-estacionária).
    Rejeitar H0 (p < 0.05) => série estacionária.
    """
    s = pd.Series(serie).dropna()
    if s.size < 12:
        return {"erro": "amostra insuficiente (< 12 obs)"}
    r = adfuller(s, regression=regressao, maxlag=maxlag, autolag=autolag)
    return {
        "estatistica": r[0], "p_valor": r[1], "lags_usados": r[2],
        "n_obs": r[3], "crit_1%": r[4]["1%"], "crit_5%": r[4]["5%"],
        "crit_10%": r[4]["10%"],
        "conclusao": "Estacionária (rejeita H0)" if r[1] < 0.05
                     else "Não-estacionária (não rejeita H0)",
    }


def teste_kpss(serie, regressao="c", nlags="auto"):
    """
    KPSS — hipótese INVERTIDA em relação ao ADF.
    H0: a série É estacionária.
    Rejeitar H0 (p < 0.05) => série NÃO-estacionária.
    """
    s = pd.Series(serie).dropna()
    if s.size < 12:
        return {"erro": "amostra insuficiente (< 12 obs)"}
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = kpss(s, regression=regressao, nlags=nlags)
    return {
        "estatistica": r[0], "p_valor": r[1], "lags_usados": r[2],
        "crit_1%": r[3]["1%"], "crit_5%": r[3]["5%"], "crit_10%": r[3]["10%"],
        "conclusao": "Não-estacionária (rejeita H0)" if r[1] < 0.05
                     else "Estacionária (não rejeita H0)",
    }


def diagnostico_conjunto(adf_res, kpss_res):
    """Combina ADF + KPSS — o diagnóstico cruzado recomendado."""
    if "erro" in adf_res or "erro" in kpss_res:
        return "Amostra insuficiente"
    adf_est = adf_res["p_valor"] < 0.05
    kpss_est = kpss_res["p_valor"] >= 0.05
    if adf_est and kpss_est:
        return "✅ I(0) — ambos indicam estacionariedade"
    if not adf_est and not kpss_est:
        return "⚠️ I(1) — ambos indicam raiz unitária: diferencie"
    if adf_est and not kpss_est:
        return "❓ Conflito — possível tendência determinística"
    return "❓ Conflito — resultado ambíguo, inspecione o gráfico"


def ordem_integracao(serie, max_d=2):
    """Determina a ordem de integração testando diferenças sucessivas."""
    s = pd.Series(serie).dropna()
    for d in range(max_d + 1):
        atual = s if d == 0 else s.diff(d).dropna()
        if atual.size < 12:
            break
        a = teste_adf(atual)
        if "erro" not in a and a["p_valor"] < 0.05:
            return d
    return None


# ============================================================================
# 2. REGRESSÃO LINEAR (OLS) COM DIAGNÓSTICOS
# ============================================================================
def rodar_ols(y, X, adicionar_constante=True, robusto="HAC", maxlags=4):
    """
    OLS com erros-padrão robustos.
    robusto: None | 'HC3' (heterocedasticidade) | 'HAC' (Newey-West:
    heterocedasticidade + autocorrelação — padrão em séries temporais).
    """
    X = sm.add_constant(X) if adicionar_constante else X
    modelo = sm.OLS(y, X, missing="drop")
    if robusto == "HAC":
        res = modelo.fit(cov_type="HAC", cov_kwds={"maxlags": maxlags})
    elif robusto == "HC3":
        res = modelo.fit(cov_type="HC3")
    else:
        res = modelo.fit()
    return res


def tabela_coeficientes(res):
    """Extrai tabela legível de coeficientes."""
    df = pd.DataFrame({
        "coeficiente": res.params,
        "erro_padrao": res.bse,
        "estatistica_t": res.tvalues,
        "p_valor": res.pvalues,
        "IC_2.5%": res.conf_int()[0],
        "IC_97.5%": res.conf_int()[1],
    })
    df["signif"] = df["p_valor"].apply(
        lambda p: "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else "")
    return df.round(6)


def diagnosticos_residuos(res, X=None):
    """Bateria de testes sobre os resíduos."""
    out = {}
    resid = res.resid
    try:
        lb = acorr_ljungbox(resid, lags=[12], return_df=True)
        out["Ljung-Box(12) p"] = float(lb["lb_pvalue"].iloc[0])
        out["_lb_txt"] = ("Autocorrelação nos resíduos (problema)"
                          if out["Ljung-Box(12) p"] < 0.05 else "Sem autocorrelação (ok)")
    except Exception:
        pass
    try:
        jb = jarque_bera(resid)
        out["Jarque-Bera p"] = float(jb[1])
        out["_jb_txt"] = ("Resíduos não-normais" if jb[1] < 0.05 else "Normalidade ok")
    except Exception:
        pass
    try:
        out["Durbin-Watson"] = float(durbin_watson(resid))
    except Exception:
        pass
    if X is not None:
        try:
            Xc = sm.add_constant(X) if "const" not in X.columns else X
            bp = het_breuschpagan(resid, Xc.loc[resid.index])
            out["Breusch-Pagan p"] = float(bp[1])
            out["_bp_txt"] = ("Heterocedasticidade presente"
                              if bp[1] < 0.05 else "Homocedasticidade ok")
        except Exception:
            pass
    return out


def calcular_vif(X):
    """Fator de Inflação da Variância — detecta multicolinearidade."""
    Xc = sm.add_constant(X.dropna())
    vals = []
    for i, c in enumerate(Xc.columns):
        if c == "const":
            continue
        try:
            vals.append({"variavel": c, "VIF": variance_inflation_factor(Xc.values, i)})
        except Exception:
            vals.append({"variavel": c, "VIF": np.nan})
    df = pd.DataFrame(vals)
    if not df.empty:
        df["avaliacao"] = df["VIF"].apply(
            lambda v: "Grave (>10)" if v > 10 else "Moderada (>5)" if v > 5 else "Ok")
    return df


# ============================================================================
# 3. COINTEGRAÇÃO
# ============================================================================
def engle_granger(y, x, trend="c"):
    """
    Engle-Granger bivariado.
    H0: NÃO há cointegração. p < 0.05 => existe relação de longo prazo.
    """
    d = pd.concat([pd.Series(y), pd.Series(x)], axis=1).dropna()
    if d.shape[0] < 20:
        return {"erro": "amostra insuficiente"}
    stat, p, crit = coint(d.iloc[:, 0], d.iloc[:, 1], trend=trend)
    return {"estatistica": stat, "p_valor": p,
            "crit_1%": crit[0], "crit_5%": crit[1], "crit_10%": crit[2],
            "conclusao": "Cointegradas (rejeita H0)" if p < 0.05
                         else "Não cointegradas"}


def johansen(df, det_order=0, k_ar_diff=1):
    """
    Teste de Johansen (multivariado).
    det_order: -1 sem constante | 0 constante no CE | 1 tendência linear.
    Retorna estatísticas do traço e do máximo autovalor.
    """
    d = df.dropna()
    if d.shape[0] < 20:
        return {"erro": "amostra insuficiente"}
    r = coint_johansen(d, det_order, k_ar_diff)
    n = d.shape[1]
    linhas = []
    for i in range(n):
        linhas.append({
            "hipotese": f"r <= {i}",
            "traco": r.lr1[i],
            "traco_crit_5%": r.cvt[i, 1],
            "traco_rejeita": r.lr1[i] > r.cvt[i, 1],
            "max_autovalor": r.lr2[i],
            "max_crit_5%": r.cvm[i, 1],
            "max_rejeita": r.lr2[i] > r.cvm[i, 1],
            "autovalor": r.eig[i],
        })
    tab = pd.DataFrame(linhas)
    rank = int(tab["traco_rejeita"].sum())
    return {"tabela": tab, "rank_traco": rank,
            "interpretacao": (f"{rank} relação(ões) de cointegração pelo traço"
                              if rank > 0 else "Sem cointegração pelo traço")}


# ============================================================================
# 4. VAR / SVAR
# ============================================================================
def selecionar_lags_var(df, maxlags=12):
    """Critérios de informação para escolha da ordem do VAR."""
    d = df.dropna()
    maxlags = int(min(maxlags, max(1, (d.shape[0] // (d.shape[1] + 1)) - 1)))
    modelo = VAR(d)
    sel = modelo.select_order(maxlags=maxlags)
    tab = pd.DataFrame({
        "criterio": ["AIC", "BIC", "FPE", "HQIC"],
        "lag_sugerido": [sel.aic, sel.bic, sel.fpe, sel.hqic],
    })
    return tab, sel


def estimar_var(df, lags, trend="c"):
    d = df.dropna()
    return VAR(d).fit(lags, trend=trend)


def irf_dataframe(res_var, periodos=24, ortogonal=True, acumulada=False):
    """Funções de resposta a impulso em formato longo."""
    irf = res_var.irf(periodos)
    arr = irf.orth_irfs if ortogonal else irf.irfs
    if acumulada:
        arr = np.cumsum(arr, axis=0)
    nomes = res_var.names
    reg = []
    for h in range(arr.shape[0]):
        for i, choque in enumerate(nomes):
            for j, resposta in enumerate(nomes):
                reg.append({"horizonte": h, "choque": choque,
                            "resposta": resposta, "valor": arr[h, j, i]})
    return pd.DataFrame(reg), irf


def fevd_dataframe(res_var, periodos=24):
    """Decomposição da variância do erro de previsão."""
    fe = res_var.fevd(periodos)
    nomes = res_var.names
    reg = []
    for j, var in enumerate(nomes):
        for h in range(periodos):
            for i, choque in enumerate(nomes):
                reg.append({"variavel": var, "horizonte": h + 1,
                            "choque": choque, "share": fe.decomp[j, h, i] * 100})
    return pd.DataFrame(reg)


def granger_matriz(df, maxlag=4):
    """Matriz de causalidade de Granger (p-valores)."""
    d = df.dropna()
    cols = d.columns
    mat = pd.DataFrame(np.nan, index=cols, columns=cols, dtype=float)
    import warnings, io, contextlib
    for causa in cols:
        for efeito in cols:
            if causa == efeito:
                continue
            try:
                with warnings.catch_warnings(), \
                     contextlib.redirect_stdout(io.StringIO()):
                    warnings.simplefilter("ignore")
                    r = grangercausalitytests(d[[efeito, causa]], maxlag=maxlag)
                ps = [r[l][0]["ssr_ftest"][1] for l in range(1, maxlag + 1)]
                mat.loc[causa, efeito] = float(np.min(ps))
            except Exception:
                pass
    return mat


def testes_estabilidade_var(res_var):
    """Raízes do polinômio característico — VAR estável se todas < 1."""
    raizes = np.abs(res_var.roots)
    return {"raizes_modulo": raizes, "max_raiz": float(np.max(raizes)),
            "estavel": bool(np.all(raizes < 1)),
            "interpretacao": ("VAR estável (todas as raízes dentro do círculo unitário)"
                              if np.all(raizes < 1) else
                              "VAR INSTÁVEL — reduza lags ou diferencie as séries")}


# ============================================================================
# 5. VECM
# ============================================================================
def estimar_vecm(df, k_ar_diff=1, coint_rank=1, deterministic="ci"):
    d = df.dropna()
    modelo = VECM(d, k_ar_diff=k_ar_diff, coint_rank=coint_rank,
                  deterministic=deterministic)
    return modelo.fit()


def tabela_vecm(res_vecm, nomes):
    """Extrai alfa (velocidade de ajuste) e beta (relação de longo prazo)."""
    alpha = pd.DataFrame(res_vecm.alpha, index=nomes,
                         columns=[f"alpha_{i+1}" for i in range(res_vecm.alpha.shape[1])])
    beta = pd.DataFrame(res_vecm.beta, index=nomes[:res_vecm.beta.shape[0]],
                        columns=[f"beta_{i+1}" for i in range(res_vecm.beta.shape[1])])
    return alpha, beta


def sugerir_rank(df, det_order=0, k_ar_diff=1):
    d = df.dropna()
    try:
        r = select_coint_rank(d, det_order=det_order, k_ar_diff=k_ar_diff)
        return int(r.rank)
    except Exception:
        return None


# ============================================================================
# 6. MODELOS BINÁRIOS (PROBIT / LOGIT)
# ============================================================================
def rodar_binario(y, X, tipo="probit", adicionar_constante=True):
    X = sm.add_constant(X) if adicionar_constante else X
    modelo = sm.Probit(y, X, missing="drop") if tipo == "probit" \
        else sm.Logit(y, X, missing="drop")
    return modelo.fit(disp=False)


def metricas_classificacao(res, y_true, X, adicionar_constante=True):
    from sklearn.metrics import roc_auc_score, roc_curve
    Xc = sm.add_constant(X) if adicionar_constante else X
    d = pd.concat([pd.Series(y_true, name="y"), Xc], axis=1).dropna()
    prob = res.predict(d[Xc.columns])
    try:
        auc = roc_auc_score(d["y"], prob)
        fpr, tpr, _ = roc_curve(d["y"], prob)
    except Exception:
        auc, fpr, tpr = np.nan, None, None
    return {"AUC": auc, "fpr": fpr, "tpr": tpr, "prob": prob,
            "pseudo_R2": float(res.prsquared), "y": d["y"]}


# ============================================================================
# 7. REGULARIZAÇÃO (LASSO / RIDGE / ELASTIC NET)
# ============================================================================
def rodar_regularizacao(y, X, metodo="elasticnet", l1_ratio=0.5, cv=5,
                        padronizar=True, n_alphas=100):
    """
    Regularização com validação cruzada temporal (TimeSeriesSplit).
    metodo: 'lasso' (L1) | 'ridge' (L2) | 'elasticnet' (mistura)
    """
    from sklearn.linear_model import LassoCV, RidgeCV, ElasticNetCV
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import TimeSeriesSplit

    d = pd.concat([pd.Series(y, name="__y"), X], axis=1).dropna()
    yv, Xv = d["__y"].values, d.drop(columns="__y")
    cols = Xv.columns
    Xm = Xv.values

    scaler = None
    if padronizar:
        scaler = StandardScaler()
        Xm = scaler.fit_transform(Xm)

    tscv = TimeSeriesSplit(n_splits=cv)
    if metodo == "lasso":
        mod = LassoCV(cv=tscv, n_alphas=n_alphas, max_iter=20000, random_state=0)
    elif metodo == "ridge":
        mod = RidgeCV(alphas=np.logspace(-4, 3, n_alphas), cv=tscv)
    else:
        mod = ElasticNetCV(cv=tscv, l1_ratio=l1_ratio, n_alphas=n_alphas,
                           max_iter=20000, random_state=0)
    mod.fit(Xm, yv)

    coefs = pd.DataFrame({"variavel": cols, "coeficiente": mod.coef_})
    coefs["abs"] = coefs["coeficiente"].abs()
    coefs["selecionada"] = coefs["coeficiente"] != 0
    coefs = coefs.sort_values("abs", ascending=False).drop(columns="abs")

    alpha = getattr(mod, "alpha_", None)
    r2 = mod.score(Xm, yv)
    return {"modelo": mod, "coeficientes": coefs, "alpha": alpha,
            "R2_in_sample": r2, "n_selecionadas": int((mod.coef_ != 0).sum()),
            "n_total": len(cols), "indice": d.index, "scaler": scaler}


def stability_selection(y, X, metodo="elasticnet", l1_ratio=0.5,
                        n_boot=100, fracao=0.75, seed=0):
    """
    Stability selection: reamostra e conta a frequência de seleção
    de cada variável. Protege contra a instabilidade do LASSO sob colinearidade.
    """
    from sklearn.linear_model import Lasso, ElasticNet
    from sklearn.preprocessing import StandardScaler

    rng = np.random.default_rng(seed)
    d = pd.concat([pd.Series(y, name="__y"), X], axis=1).dropna()
    yv, Xv = d["__y"].values, d.drop(columns="__y")
    cols = Xv.columns
    Xm = StandardScaler().fit_transform(Xv.values)

    base = rodar_regularizacao(d["__y"], Xv, metodo=metodo, l1_ratio=l1_ratio)
    alpha = base["alpha"] or 0.01

    n = len(yv)
    cont = np.zeros(len(cols))
    tam = max(10, int(n * fracao))
    for _ in range(n_boot):
        idx = rng.choice(n, size=tam, replace=False)
        mod = (Lasso(alpha=alpha, max_iter=20000) if metodo == "lasso"
               else ElasticNet(alpha=alpha, l1_ratio=l1_ratio, max_iter=20000))
        try:
            mod.fit(Xm[idx], yv[idx])
            cont += (mod.coef_ != 0).astype(int)
        except Exception:
            continue
    freq = pd.DataFrame({"variavel": cols,
                         "freq_selecao": cont / n_boot}).sort_values(
        "freq_selecao", ascending=False)
    freq["estavel"] = freq["freq_selecao"] >= 0.60
    return freq


# ============================================================================
# 8. PREVISÃO / AVALIAÇÃO FORA DA AMOSTRA
# ============================================================================
def backtest_ols(y, X, janela_min=60, passo=1):
    """Avaliação recursiva out-of-sample de um OLS."""
    d = pd.concat([pd.Series(y, name="__y"), X], axis=1).dropna()
    preds, reais, datas = [], [], []
    for t in range(janela_min, len(d), passo):
        tr, te = d.iloc[:t], d.iloc[t:t + 1]
        try:
            m = sm.OLS(tr["__y"], sm.add_constant(tr.drop(columns="__y"))).fit()
            Xte = sm.add_constant(te.drop(columns="__y"), has_constant="add")
            preds.append(float(m.predict(Xte).iloc[0]))
            reais.append(float(te["__y"].iloc[0]))
            datas.append(te.index[0])
        except Exception:
            continue
    if not preds:
        return None
    res = pd.DataFrame({"data": datas, "real": reais, "previsto": preds}).set_index("data")
    err = res["real"] - res["previsto"]
    metricas = {"RMSE": float(np.sqrt((err ** 2).mean())),
                "MAE": float(err.abs().mean()),
                "viés": float(err.mean()), "n": len(res)}
    return {"serie": res, "metricas": metricas}
