"""
=============================================================================
LABORATÓRIO DE MACROECONOMETRIA
=============================================================================
Ambiente interativo para exploração, transformação, teste e modelagem
de séries macroeconômicas.

Execução:
    streamlit run app.py
=============================================================================
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

import core
import modelos as M
import manual

st.set_page_config(page_title="Laboratório de Macroeconometria",
                   page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")

# ---------------------------------------------------------------------------
# Estilo
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .main .block-container {padding-top: 2rem; max-width: 1400px;}
    h1 {font-size: 2rem !important; font-weight: 700;}
    h2 {font-size: 1.4rem !important; margin-top: 1.5rem;}
    h3 {font-size: 1.1rem !important;}
    .eq-box {background:#f0f4f8; border-left:4px solid #2c5282;
             padding:12px 16px; margin:12px 0; border-radius:4px;}
    .interp-box {background:#f0fff4; border-left:4px solid #38a169;
             padding:12px 16px; margin:12px 0; border-radius:4px;}
    .warn-box {background:#fffaf0; border-left:4px solid #dd6b20;
             padding:12px 16px; margin:12px 0; border-radius:4px;}
    div[data-testid="stMetricValue"] {font-size: 1.3rem;}
</style>
""", unsafe_allow_html=True)


def caixa_equacao(titulo, latex, nota=""):
    st.markdown(f"**{titulo}**")
    st.latex(latex)
    if nota:
        st.caption(nota)


def caixa_interp(texto):
    st.markdown(f'<div class="interp-box">{texto}</div>', unsafe_allow_html=True)


def caixa_alerta(texto):
    st.markdown(f'<div class="warn-box">⚠️ {texto}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Estado da sessão
# ---------------------------------------------------------------------------
if "df" not in st.session_state:
    st.session_state.df = None
if "df_trans" not in st.session_state:
    st.session_state.df_trans = None


def base_ativa():
    """Base original + transformações criadas pelo usuário."""
    if st.session_state.df is None:
        return None
    if st.session_state.df_trans is None or st.session_state.df_trans.empty:
        return st.session_state.df
    return st.session_state.df.join(st.session_state.df_trans, how="left")


# ---------------------------------------------------------------------------
# SIDEBAR — carregamento
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("📊 Laboratório")
    st.caption("Macroeconometria aplicada")
    st.divider()

    st.subheader("1. Dados")
    up = st.file_uploader("Base (.xlsx ou .csv)", type=["xlsx", "xls", "csv"])
    cam = st.text_input("…ou caminho local", value="",
                        placeholder="C:/…/base_geral_dessaz_int_lag.xlsx")

    if st.button("Carregar base", type="primary", use_container_width=True):
        try:
            fonte = up if up is not None else (cam if cam.strip() else None)
            if fonte is None:
                st.error("Informe um arquivo ou caminho.")
            else:
                st.session_state.df = core.carregar_base(fonte)
                st.session_state.df_trans = pd.DataFrame(
                    index=st.session_state.df.index)
                st.success(f"{st.session_state.df.shape[0]} linhas × "
                           f"{st.session_state.df.shape[1]} colunas")
        except Exception as e:
            st.error(f"Erro: {e}")

    if st.session_state.df is not None:
        d = st.session_state.df
        st.divider()
        st.metric("Período", f"{d.index.min():%Y-%m} → {d.index.max():%Y-%m}")
        st.metric("Variáveis", d.shape[1])
        nt = 0 if st.session_state.df_trans is None else st.session_state.df_trans.shape[1]
        st.metric("Transformadas", nt)

    st.divider()
    st.caption("💡 Comece pelo **Manual** se for sua primeira vez.")


# ---------------------------------------------------------------------------
# ABAS
# ---------------------------------------------------------------------------
abas = st.tabs([
    "📖 Manual",
    "🔍 Explorar",
    "🔧 Transformar",
    "📏 Estacionariedade",
    "📉 Regressão",
    "🔗 Cointegração",
    "🌐 VAR / SVAR",
    "⚖️ VECM",
    "🎯 Probit/Logit",
    "🧲 Regularização",
])

# ===========================================================================
# ABA 0 — MANUAL
# ===========================================================================
with abas[0]:
    manual.render()

# ===========================================================================
# ABA 1 — EXPLORAR
# ===========================================================================
with abas[1]:
    st.header("Exploração dos dados")
    df = base_ativa()
    if df is None:
        st.info("Carregue uma base na barra lateral.")
    else:
        st.subheader("Cobertura e estatísticas descritivas")
        st.caption("A **amostra efetiva** de qualquer modelo multivariado é a "
                   "interseção das séries usadas — a coluna `inicio` mostra o gargalo.")
        cob = core.resumo_cobertura(df)
        filtro = st.text_input("Filtrar variáveis", "", key="f_cob")
        if filtro:
            cob = cob[cob["variavel"].str.contains(filtro, case=False)]
        st.dataframe(cob, use_container_width=True, height=280)

        st.divider()
        st.subheader("Visualizar séries")
        c1, c2 = st.columns([3, 1])
        with c1:
            sel = st.multiselect("Variáveis", list(df.columns),
                                 default=list(df.columns[1:3]), key="ms_expl")
        with c2:
            normal = st.checkbox("Normalizar (z-score)", value=False)
            eixo2 = st.checkbox("Segundo eixo Y", value=False)

        if sel:
            plot = df[sel].dropna(how="all")
            if normal:
                plot = (plot - plot.mean()) / plot.std()
            if eixo2 and len(sel) == 2:
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                fig.add_trace(go.Scatter(x=plot.index, y=plot[sel[0]],
                                         name=sel[0]), secondary_y=False)
                fig.add_trace(go.Scatter(x=plot.index, y=plot[sel[1]],
                                         name=sel[1]), secondary_y=True)
            else:
                fig = go.Figure()
                for c in sel:
                    fig.add_trace(go.Scatter(x=plot.index, y=plot[c], name=c))
            fig.update_layout(height=420, hovermode="x unified",
                              margin=dict(t=30, b=30))
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Matriz de correlação")
            corr = df[sel].corr()
            fig2 = px.imshow(corr, text_auto=".2f", aspect="auto",
                             color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
            fig2.update_layout(height=380, margin=dict(t=30))
            st.plotly_chart(fig2, use_container_width=True)
            caixa_alerta("Correlações acima de 0,9 entre regressores indicam "
                         "multicolinearidade — os coeficientes ficam instáveis. "
                         "É o caso típico entre vértices vizinhos da curva de juros.")

# ===========================================================================
# ABA 2 — TRANSFORMAR
# ===========================================================================
with abas[2]:
    st.header("Transformações")
    st.caption("Regressões com séries não-estacionárias produzem **regressão "
               "espúria** (Granger & Newbold, 1974): R² alto e t-estatísticas "
               "grandes sem relação real. Transforme antes de modelar.")
    df = base_ativa()
    if df is None:
        st.info("Carregue uma base na barra lateral.")
    else:
        st.subheader("Criar variável transformada")
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            var = st.selectbox("Variável de origem", list(st.session_state.df.columns))
        with c2:
            tipo = st.selectbox("Transformação", list(core.TRANSFORMACOES.keys()),
                                format_func=lambda t: core.TRANSFORMACOES[t])
        with c3:
            st.write("")
            st.write("")
            criar = st.button("➕ Criar", type="primary", use_container_width=True)

        with st.expander("Qual transformação usar?"):
            st.markdown("""
| Tipo de série | Transformação | Resultado |
|---|---|---|
| Índice com tendência (PIB) | `logdiff` | crescimento % mensal |
| Índice com sazonalidade | `logdiff12` | crescimento % anual |
| Volume monetário (crédito) | `logdiff` ou `logdiff12` | expansão % |
| Taxa em nível (Selic, desemprego) | `diff` | variação em p.p. |
| Taxa já em variação (IPCA mensal) | `nivel` ou `acum12` | inflação acumulada 12m |
| Extrair componente cíclico | `hp_ciclo` | desvio da tendência (hiato) |
| Preparar para regularização | `zscore` | escala comparável |
""")

        if criar:
            try:
                nova = core.aplicar_transformacao(st.session_state.df[var], tipo)
                nome = f"{var}{core.sufixo(tipo)}"
                st.session_state.df_trans[nome] = nova
                st.success(f"Criada: `{nome}` ({nova.notna().sum()} observações)")
            except Exception as e:
                st.error(f"Erro: {e}")

        st.divider()
        st.subheader("Construir spread (inclinação da curva)")
        st.caption("O spread longo − curto é o preditor de recessão mais robusto "
                   "da literatura e resolve a colinearidade entre vértices.")
        cs = st.columns([2, 2, 1])
        num = [c for c in st.session_state.df.columns]
        with cs[0]:
            longo = st.selectbox("Taxa longa", num,
                                 index=num.index("prazo_12m") if "prazo_12m" in num else 0)
        with cs[1]:
            curto = st.selectbox("Taxa curta", num,
                                 index=num.index("prazo_1m") if "prazo_1m" in num else 0)
        with cs[2]:
            st.write("")
            st.write("")
            if st.button("➕ Criar spread", use_container_width=True):
                nome = f"spread_{longo}_{curto}"
                st.session_state.df_trans[nome] = (st.session_state.df[longo]
                                                   - st.session_state.df[curto])
                st.success(f"Criado: `{nome}`")

        st.divider()
        st.subheader("Variáveis transformadas nesta sessão")
        if st.session_state.df_trans is not None and not st.session_state.df_trans.empty:
            st.dataframe(core.resumo_cobertura(st.session_state.df_trans),
                         use_container_width=True)
            rem = st.multiselect("Remover", list(st.session_state.df_trans.columns))
            if rem and st.button("🗑 Remover selecionadas"):
                st.session_state.df_trans.drop(columns=rem, inplace=True)
                st.rerun()

            vis = st.selectbox("Visualizar", list(st.session_state.df_trans.columns))
            orig = vis
            for s in ["_dln12", "_dln", "_pct12", "_pct", "_dd", "_d", "_ln",
                      "_ma3", "_ma12", "_z", "_ac12", "_hpc", "_hpt"]:
                if vis.endswith(s):
                    orig = vis[: -len(s)]
                    break
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                subplot_titles=(f"Original: {orig}",
                                                f"Transformada: {vis}"))
            if orig in st.session_state.df.columns:
                fig.add_trace(go.Scatter(x=st.session_state.df.index,
                                         y=st.session_state.df[orig],
                                         name=orig), row=1, col=1)
            fig.add_trace(go.Scatter(x=st.session_state.df_trans.index,
                                     y=st.session_state.df_trans[vis],
                                     name=vis, line=dict(color="#e53e3e")),
                          row=2, col=1)
            fig.update_layout(height=460, showlegend=False, margin=dict(t=40))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhuma transformação criada ainda.")

# ===========================================================================
# ABA 3 — ESTACIONARIEDADE
# ===========================================================================
with abas[3]:
    st.header("Testes de raiz unitária")
    caixa_equacao(
        "Regressão do teste ADF",
        r"\Delta y_t = \alpha + \beta t + \gamma y_{t-1} + \sum_{i=1}^{p}\delta_i \Delta y_{t-i} + \varepsilon_t",
        "H₀: γ = 0 (existe raiz unitária). Rejeitar H₀ ⟹ série estacionária.")

    st.markdown("""
| Teste | Hipótese nula (H₀) | p < 0,05 significa |
|---|---|---|
| **ADF** | tem raiz unitária (não-estacionária) | **é** estacionária |
| **KPSS** | é estacionária | **não é** estacionária |

As nulas são **opostas** — por isso rodamos os dois. Concordância dá diagnóstico
firme; divergência sugere tendência determinística ou amostra curta.
""")

    df = base_ativa()
    if df is None:
        st.info("Carregue uma base na barra lateral.")
    else:
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            vars_t = st.multiselect("Variáveis a testar", list(df.columns),
                                    default=list(df.columns[1:4]), key="ms_est")
        with c2:
            reg = st.selectbox("Especificação", ["c", "ct", "n"],
                               format_func={"c": "Constante", "ct": "Const.+tendência",
                                            "n": "Nenhuma"}.get)
        with c3:
            ini = st.text_input("Início (opcional)", "", placeholder="2012-01-01")

        if vars_t and st.button("Rodar testes", type="primary"):
            linhas = []
            for v in vars_t:
                s = df[v]
                if ini.strip():
                    s = s[s.index >= pd.Timestamp(ini)]
                s = s.dropna()
                a = M.teste_adf(s, regressao=reg)
                k = M.teste_kpss(s, regressao="c" if reg == "n" else reg)
                if "erro" in a or "erro" in k:
                    linhas.append({"variavel": v, "n": len(s),
                                   "diagnostico": "Amostra insuficiente"})
                    continue
                linhas.append({
                    "variavel": v, "n": len(s),
                    "ADF_estat": round(a["estatistica"], 3),
                    "ADF_p": core.formata_p(a["p_valor"]),
                    "KPSS_estat": round(k["estatistica"], 3),
                    "KPSS_p": core.formata_p(k["p_valor"]),
                    "diagnostico": M.diagnostico_conjunto(a, k),
                    "ordem_I(d)": M.ordem_integracao(s),
                })
            res = pd.DataFrame(linhas)
            st.dataframe(res, use_container_width=True)

            caixa_interp("""
<b>Como ler:</b><br>
✅ <b>I(0)</b> — pode entrar em nível em regressões e VAR.<br>
⚠️ <b>I(1)</b> — precisa ser diferenciada, <i>ou</i> testada para cointegração
(se várias I(1) cointegram, use VECM em vez de diferenciar).<br>
❓ <b>Conflito</b> — inspecione o gráfico. Tendência determinística clara pede
especificação com tendência ("ct"); quebras estruturais (Plano Real, 2020)
distorcem ambos os testes.
""")

# ===========================================================================
# ABA 4 — REGRESSÃO
# ===========================================================================
with abas[4]:
    st.header("Regressão linear (MQO)")
    caixa_equacao("Modelo",
                  r"y_t = \beta_0 + \beta_1 x_{1t} + \beta_2 x_{2t} + \dots + \beta_k x_{kt} + \varepsilon_t")
    st.caption("Erros-padrão HAC (Newey-West) corrigem heterocedasticidade **e** "
               "autocorrelação — o padrão em séries temporais.")

    df = base_ativa()
    if df is None:
        st.info("Carregue uma base na barra lateral.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            y_var = st.selectbox("Variável dependente (y)", list(df.columns), key="ols_y")
        with c2:
            x_vars = st.multiselect("Explicativas (X)",
                                    [c for c in df.columns if c != y_var], key="ols_x")
        c3, c4, c5 = st.columns(3)
        with c3:
            rob = st.selectbox("Erros-padrão", ["HAC", "HC3", None],
                               format_func=lambda x: {"HAC": "HAC (Newey-West)",
                                                      "HC3": "HC3 (robusto)",
                                                      None: "Clássicos"}[x])
        with c4:
            maxl = st.number_input("Lags HAC", 1, 24, 4)
        with c5:
            per = st.text_input("Período (aaaa-mm-dd)", "", key="ols_per",
                                placeholder="2012-01-01")

        if y_var and x_vars and st.button("Estimar", type="primary", key="btn_ols"):
            d = core.amostra_comum(df, [y_var] + x_vars,
                                   inicio=per if per.strip() else None)
            if d.shape[0] < 10:
                st.error(f"Amostra muito pequena: {d.shape[0]} observações.")
            else:
                res = M.rodar_ols(d[y_var], d[x_vars], robusto=rob, maxlags=maxl)
                m = st.columns(5)
                m[0].metric("Observações", int(res.nobs))
                m[1].metric("R²", f"{res.rsquared:.4f}")
                m[2].metric("R² ajustado", f"{res.rsquared_adj:.4f}")
                m[3].metric("F (p-valor)", f"{res.f_pvalue:.4f}"
                            if not np.isnan(res.f_pvalue) else "—")
                m[4].metric("AIC", f"{res.aic:.1f}")

                st.subheader("Coeficientes")
                st.dataframe(M.tabela_coeficientes(res), use_container_width=True)
                st.caption("Significância: *** p<0,01 | ** p<0,05 | * p<0,10")

                st.subheader("Diagnóstico dos resíduos")
                dg = M.diagnosticos_residuos(res, d[x_vars])
                cols = st.columns(4)
                i = 0
                for k, v in dg.items():
                    if k.startswith("_"):
                        continue
                    cols[i % 4].metric(k, f"{v:.4f}" if isinstance(v, float) else v)
                    i += 1
                for k in ["_lb_txt", "_jb_txt", "_bp_txt"]:
                    if k in dg:
                        st.caption(f"• {dg[k]}")
                if dg.get("Ljung-Box(12) p", 1) < 0.05:
                    caixa_alerta("Autocorrelação nos resíduos: os erros-padrão "
                                 "clássicos ficam inválidos. Use HAC (já ativo por "
                                 "padrão), adicione defasagens de y, ou considere um VAR.")

                st.subheader("Multicolinearidade (VIF)")
                st.dataframe(M.calcular_vif(d[x_vars]), use_container_width=True)
                st.caption("VIF > 10 indica colinearidade grave — considere remover "
                           "variáveis, usar spreads, ou partir para regularização.")

                st.subheader("Ajuste e resíduos")
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[.62, .38],
                                    subplot_titles=("Observado vs. ajustado", "Resíduos"))
                fig.add_trace(go.Scatter(x=d.index, y=d[y_var], name="observado"), row=1, col=1)
                fig.add_trace(go.Scatter(x=d.index, y=res.fittedvalues,
                                         name="ajustado", line=dict(dash="dash")), row=1, col=1)
                fig.add_trace(go.Scatter(x=d.index, y=res.resid, name="resíduo",
                                         line=dict(color="#e53e3e")), row=2, col=1)
                fig.add_hline(y=0, line_dash="dot", row=2, col=1)
                fig.update_layout(height=520, hovermode="x unified", margin=dict(t=50))
                st.plotly_chart(fig, use_container_width=True)

                with st.expander("Avaliação fora da amostra (backtest recursivo)"):
                    jm = st.slider("Janela mínima de treino", 24, max(30, len(d) - 12),
                                   min(60, len(d) // 2), key="bt_j")
                    if st.button("Rodar backtest"):
                        bt = M.backtest_ols(d[y_var], d[x_vars], janela_min=jm)
                        if bt:
                            mm = st.columns(4)
                            for j, (k, v) in enumerate(bt["metricas"].items()):
                                mm[j].metric(k, f"{v:.4f}" if isinstance(v, float) else v)
                            f2 = go.Figure()
                            f2.add_trace(go.Scatter(x=bt["serie"].index,
                                                    y=bt["serie"]["real"], name="real"))
                            f2.add_trace(go.Scatter(x=bt["serie"].index,
                                                    y=bt["serie"]["previsto"],
                                                    name="previsto", line=dict(dash="dash")))
                            f2.update_layout(height=340, margin=dict(t=20))
                            st.plotly_chart(f2, use_container_width=True)
                            st.caption("RMSE fora da amostra é o teste real do modelo — "
                                       "R² alto dentro da amostra pode ser sobreajuste.")

# ===========================================================================
# ABA 5 — COINTEGRAÇÃO
# ===========================================================================
with abas[5]:
    st.header("Cointegração")
    st.markdown("""
Duas ou mais séries **I(1)** podem ter uma combinação linear **estacionária**:
compartilham uma tendência estocástica comum e existe uma **relação de
equilíbrio de longo prazo** entre elas. Nesse caso, regredir em nível **não** é
espúrio — e diferenciar tudo destruiria a informação de longo prazo.
""")
    caixa_equacao("Relação de longo prazo",
                  r"y_t - \beta x_t = u_t, \quad u_t \sim I(0)",
                  "Se o resíduo u é estacionário, y e x são cointegradas.")

    df = base_ativa()
    if df is None:
        st.info("Carregue uma base na barra lateral.")
    else:
        sub1, sub2 = st.tabs(["Engle-Granger (bivariado)", "Johansen (multivariado)"])

        with sub1:
            st.caption("H₀: **não** há cointegração. p < 0,05 ⟹ cointegradas. "
                       "Pré-requisito: ambas as séries devem ser I(1).")
            c1, c2 = st.columns(2)
            with c1:
                y1 = st.selectbox("Série y", list(df.columns), key="eg_y")
            with c2:
                x1 = st.selectbox("Série x", [c for c in df.columns if c != y1], key="eg_x")
            per_eg = st.text_input("Início (opcional)", "", key="eg_per")
            if st.button("Testar (Engle-Granger)", type="primary"):
                d = core.amostra_comum(df, [y1, x1],
                                       inicio=per_eg if per_eg.strip() else None)
                r = M.engle_granger(d[y1], d[x1])
                if "erro" in r:
                    st.error(r["erro"])
                else:
                    cc = st.columns(4)
                    cc[0].metric("Estatística", f"{r['estatistica']:.4f}")
                    cc[1].metric("p-valor", f"{r['p_valor']:.4f}")
                    cc[2].metric("Crítico 5%", f"{r['crit_5%']:.4f}")
                    cc[3].metric("Observações", d.shape[0])
                    if r["p_valor"] < 0.05:
                        caixa_interp(f"<b>{r['conclusao']}</b> — existe relação de "
                                     "longo prazo. Modele com VECM (aba seguinte) "
                                     "para separar dinâmica de curto prazo do "
                                     "ajuste ao equilíbrio.")
                    else:
                        caixa_alerta(f"{r['conclusao']}. Se ambas são I(1), "
                                     "modele em primeira diferença (VAR).")

        with sub2:
            st.caption("Testa **quantas** relações de cointegração (rank r) existem "
                       "num sistema com 2+ variáveis. Estatísticas do traço e do "
                       "máximo autovalor.")
            vj = st.multiselect("Variáveis do sistema", list(df.columns), key="joh_v")
            c1, c2, c3 = st.columns(3)
            with c1:
                det = st.selectbox("Termo determinístico", [-1, 0, 1],
                                   index=1,
                                   format_func={-1: "Sem constante", 0: "Constante no CE",
                                                1: "Tendência linear"}.get)
            with c2:
                kd = st.number_input("Lags em diferença (k)", 1, 12, 1, key="joh_k")
            with c3:
                per_j = st.text_input("Início (opcional)", "", key="joh_per")

            if len(vj) >= 2 and st.button("Testar (Johansen)", type="primary"):
                d = core.amostra_comum(df, vj, inicio=per_j if per_j.strip() else None)
                r = M.johansen(d, det_order=det, k_ar_diff=kd)
                if "erro" in r:
                    st.error(r["erro"])
                else:
                    st.metric("Rank de cointegração (traço)", r["rank_traco"])
                    st.dataframe(r["tabela"].round(4), use_container_width=True)
                    caixa_interp(f"""
<b>{r['interpretacao']}</b><br><br>
Leia linha a linha: em <code>r &lt;= 0</code>, rejeitar significa que há pelo menos
uma relação. Em <code>r &lt;= 1</code>, rejeitar significa pelo menos duas. O rank
é o número de rejeições consecutivas a partir do topo.<br><br>
Com rank ≥ 1, use <b>VECM</b> com esse mesmo rank.
""")

# ===========================================================================
# ABA 6 — VAR / SVAR
# ===========================================================================
with abas[6]:
    st.header("Vetor Autorregressivo (VAR)")
    caixa_equacao("Forma reduzida",
                  r"\mathbf{y}_t = \mathbf{c} + \mathbf{A}_1 \mathbf{y}_{t-1} + \dots + \mathbf{A}_p \mathbf{y}_{t-p} + \mathbf{u}_t",
                  "Todas as variáveis são endógenas. A leitura vem das funções de "
                  "resposta a impulso, da decomposição da variância e da causalidade "
                  "de Granger — não dos coeficientes individuais.")
    caixa_alerta("Todas as séries devem ser **estacionárias**. Se forem I(1) e "
                 "cointegradas, use VECM. Regra prática de amostra: observações ≥ "
                 "10 × (nº variáveis × nº lags).")

    df = base_ativa()
    if df is None:
        st.info("Carregue uma base na barra lateral.")
    else:
        vv = st.multiselect("Variáveis do sistema (ordem = ordenação de Cholesky)",
                            list(df.columns), key="var_v")
        st.caption("**Ordem importa** no SVAR: coloque as mais lentas a reagir "
                   "primeiro. Ordenação usual: atividade → preços → juros → crédito.")
        c1, c2, c3 = st.columns(3)
        with c1:
            per_v = st.text_input("Início", "", key="var_per", placeholder="2012-01-01")
        with c2:
            maxl_v = st.number_input("Máx. lags a testar", 1, 24, 8, key="var_ml")
        with c3:
            hor = st.number_input("Horizonte (meses)", 6, 60, 24, key="var_h")

        if len(vv) >= 2:
            d = core.amostra_comum(df, vv, inicio=per_v if per_v.strip() else None)
            st.info(f"Amostra efetiva: **{d.shape[0]} observações** "
                    f"({d.index.min():%Y-%m} a {d.index.max():%Y-%m})")

            if st.button("1. Selecionar ordem de lags"):
                try:
                    tab, _ = M.selecionar_lags_var(d, maxlags=maxl_v)
                    st.dataframe(tab, use_container_width=True)
                    st.caption("AIC tende a escolher mais lags (melhor para previsão); "
                               "BIC é mais parcimonioso (melhor para inferência).")
                except Exception as e:
                    st.error(f"Erro: {e}")

            lag_esc = st.number_input("2. Lags a usar", 1, 24, 2, key="var_lag")

            if st.button("3. Estimar VAR", type="primary"):
                try:
                    res = M.estimar_var(d, lag_esc)
                    st.session_state["var_res"] = res
                    st.session_state["var_d"] = d
                    st.success(f"VAR({lag_esc}) estimado com {res.nobs} observações.")
                except Exception as e:
                    st.error(f"Erro: {e}")

            if "var_res" in st.session_state:
                res = st.session_state["var_res"]
                est = M.testes_estabilidade_var(res)
                cc = st.columns(3)
                cc[0].metric("Maior raiz (módulo)", f"{est['max_raiz']:.4f}")
                cc[1].metric("Estável?", "Sim" if est["estavel"] else "Não")
                cc[2].metric("AIC", f"{res.aic:.2f}")
                if not est["estavel"]:
                    caixa_alerta(est["interpretacao"])

                t1, t2, t3, t4 = st.tabs(["Resposta a impulso", "Decomposição da variância",
                                          "Causalidade de Granger", "Coeficientes"])

                with t1:
                    st.caption("Resposta de cada variável a um choque de 1 desvio-padrão.")
                    cA, cB = st.columns(2)
                    with cA:
                        acum = st.checkbox("Resposta acumulada", value=False)
                    with cB:
                        ortog = st.checkbox("Ortogonalizada (Cholesky)", value=True)
                    try:
                        irf_df, irf_obj = M.irf_dataframe(res, hor, ortog, acum)
                        nomes = res.names
                        fig = make_subplots(rows=len(nomes), cols=len(nomes),
                                            subplot_titles=[f"{c}→{r}" for r in nomes
                                                            for c in nomes],
                                            shared_xaxes=True)
                        for i, r_ in enumerate(nomes):
                            for j, c_ in enumerate(nomes):
                                sub = irf_df[(irf_df["choque"] == c_) &
                                             (irf_df["resposta"] == r_)]
                                fig.add_trace(go.Scatter(x=sub["horizonte"],
                                                         y=sub["valor"],
                                                         showlegend=False,
                                                         line=dict(color="#2c5282")),
                                              row=i + 1, col=j + 1)
                                fig.add_hline(y=0, line_dash="dot", line_color="gray",
                                              row=i + 1, col=j + 1)
                        fig.update_layout(height=240 * len(nomes), margin=dict(t=60))
                        st.plotly_chart(fig, use_container_width=True)
                        caixa_interp("""
<b>Como ler:</b> cada painel mostra a resposta (linha) a um choque (coluna).
Se a resposta cruza zero e retorna, o efeito é transitório; se persiste,
é duradouro. Bandas de confiança não são exibidas aqui — use
<code>irf.plot(orth=True)</code> no statsmodels para obtê-las.<br><br>
<b>Exemplo típico:</b> choque positivo na Selic → queda do crédito nos meses
seguintes → queda da atividade com defasagem maior → recuo da inflação.
Defasagens de 6 a 12 meses são o padrão na transmissão monetária.
""")
                        st.dataframe(irf_df.round(6), use_container_width=True, height=240)
                    except Exception as e:
                        st.error(f"Erro na IRF: {e}")

                with t2:
                    try:
                        fe = M.fevd_dataframe(res, hor)
                        alvo = st.selectbox("Variável explicada", res.names, key="fevd_v")
                        sub = fe[fe["variavel"] == alvo]
                        fig = px.area(sub, x="horizonte", y="share", color="choque",
                                      labels={"share": "% da variância",
                                              "horizonte": "meses à frente"})
                        fig.update_layout(height=420, margin=dict(t=30))
                        st.plotly_chart(fig, use_container_width=True)
                        caixa_interp("Mostra <b>quanto</b> da incerteza de previsão de "
                                     "cada variável vem de cada choque. No horizonte 1 "
                                     "a própria variável domina; à medida que o horizonte "
                                     "cresce, os outros choques ganham peso.")
                        st.dataframe(sub.round(3), use_container_width=True, height=220)
                    except Exception as e:
                        st.error(f"Erro na FEVD: {e}")

                with t3:
                    st.caption("H₀: a variável-linha **não** Granger-causa a "
                               "variável-coluna. Valores são p-valores (mínimo entre lags).")
                    ml = st.number_input("Lags no teste", 1, 12, min(4, lag_esc), key="gr_l")
                    if st.button("Calcular matriz de Granger"):
                        g = M.granger_matriz(st.session_state["var_d"], ml)
                        fig = px.imshow(g, text_auto=".3f", aspect="auto",
                                        color_continuous_scale="RdYlGn_r", zmin=0, zmax=0.2,
                                        labels=dict(x="→ efeito", y="causa →"))
                        fig.update_layout(height=380, margin=dict(t=30))
                        st.plotly_chart(fig, use_container_width=True)
                        caixa_interp("Células <b>verdes</b> (p < 0,05) indicam que a "
                                     "variável da linha ajuda a prever a da coluna. "
                                     "Isso é <b>precedência temporal</b>, não causalidade "
                                     "estrutural — ambas podem responder a um terceiro fator.")

                with t4:
                    st.text(str(res.summary()))

# ===========================================================================
# ABA 7 — VECM
# ===========================================================================
with abas[7]:
    st.header("Modelo Vetorial de Correção de Erros (VECM)")
    caixa_equacao("Especificação",
                  r"\Delta \mathbf{y}_t = \boldsymbol{\alpha}\boldsymbol{\beta}'\mathbf{y}_{t-1} + \sum_{i=1}^{k-1}\boldsymbol{\Gamma}_i \Delta \mathbf{y}_{t-i} + \boldsymbol{\varepsilon}_t",
                  "β = relação de longo prazo (equilíbrio). α = velocidade de ajuste "
                  "ao desequilíbrio. Γ = dinâmica de curto prazo.")
    st.markdown("""
Use quando as séries são **I(1) e cointegradas**. O VECM preserva a informação
de longo prazo que seria perdida ao diferenciar tudo.
""")

    df = base_ativa()
    if df is None:
        st.info("Carregue uma base na barra lateral.")
    else:
        vv2 = st.multiselect("Variáveis do sistema", list(df.columns), key="vecm_v")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            per_ve = st.text_input("Início", "", key="vecm_per")
        with c2:
            k2 = st.number_input("Lags em diferença", 1, 12, 1, key="vecm_k")
        with c3:
            rank = st.number_input("Rank de cointegração", 1, 5, 1, key="vecm_r")
        with c4:
            deterministic = st.selectbox("Determinístico", ["ci", "co", "cili", "nc"],
                                         format_func={"ci": "Constante no CE",
                                                      "co": "Constante fora",
                                                      "cili": "Const.+tend. no CE",
                                                      "nc": "Nenhum"}.get)

        if len(vv2) >= 2:
            d = core.amostra_comum(df, vv2, inicio=per_ve if per_ve.strip() else None)
            st.info(f"Amostra efetiva: **{d.shape[0]} observações**")
            if st.button("Sugerir rank (Johansen)"):
                sr = M.sugerir_rank(d, k_ar_diff=k2)
                st.metric("Rank sugerido", sr if sr is not None else "indeterminado")

            if st.button("Estimar VECM", type="primary"):
                try:
                    res = M.estimar_vecm(d, k_ar_diff=k2, coint_rank=rank,
                                         deterministic=deterministic)
                    alpha, beta = M.tabela_vecm(res, list(d.columns))
                    c1, c2 = st.columns(2)
                    with c1:
                        st.subheader("α — velocidade de ajuste")
                        st.dataframe(alpha.round(5), use_container_width=True)
                        st.caption("Negativo e significativo ⟹ a variável **se ajusta** "
                                   "de volta ao equilíbrio. Magnitude = fração do "
                                   "desequilíbrio corrigida por mês.")
                    with c2:
                        st.subheader("β — relação de longo prazo")
                        st.dataframe(beta.round(5), use_container_width=True)
                        st.caption("Normalizado na primeira variável. Lê-se como a "
                                   "elasticidade de equilíbrio entre as séries.")

                    caixa_interp("""
<b>Interpretação prática:</b> um α de −0,05 na equação do PIB significa que,
a cada mês, 5% do desvio em relação ao equilíbrio de longo prazo é corrigido —
meia-vida de aproximadamente 14 meses. Quem tem α próximo de zero é a variável
<i>fracamente exógena</i>: ela empurra o sistema, mas não se ajusta a ele.
""")
                    st.subheader("Resumo completo")
                    st.text(str(res.summary()))
                except Exception as e:
                    st.error(f"Erro: {e}")

# ===========================================================================
# ABA 8 — PROBIT / LOGIT
# ===========================================================================
with abas[8]:
    st.header("Modelos de resposta binária (Probit / Logit)")
    caixa_equacao("Probabilidade de recessão h meses à frente",
                  r"P(R_{t+h}=1 \mid X_t) = \Phi(\beta_0 + \beta_1 x_{1t} + \dots + \beta_k x_{kt})",
                  "Φ = função de distribuição acumulada da normal padrão (Probit). "
                  "No Logit, usa-se a função logística.")
    st.markdown("""
Aplicação clássica: **previsão de recessão**. A inclinação da curva de juros
(spread longo − curto) é o preditor mais robusto documentado na literatura.
Avaliação por **AUC/ROC**, não por R².
""")

    df = base_ativa()
    if df is None:
        st.info("Carregue uma base na barra lateral.")
    else:
        st.subheader("1. Definir a variável binária")
        modo = st.radio("Origem", ["Construir a partir de uma série",
                                   "Usar coluna binária existente"], horizontal=True)
        y_bin = None
        if modo == "Construir a partir de uma série":
            c1, c2, c3 = st.columns(3)
            with c1:
                base_y = st.selectbox("Série de referência", list(df.columns), key="pb_y")
            with c2:
                cond = st.selectbox("Condição", ["< limiar", "> limiar"])
            with c3:
                lim = st.number_input("Limiar", value=0.0, step=0.1, format="%.4f")
            s = df[base_y]
            y_bin = ((s < lim) if cond == "< limiar" else (s > lim)).astype(float)
            y_bin[s.isna()] = np.nan
            st.caption(f"Eventos marcados: **{int(y_bin.sum())}** de "
                       f"{int(y_bin.notna().sum())} observações "
                       f"({100*y_bin.mean():.1f}%)")
            if y_bin.sum() < 10:
                caixa_alerta("Menos de 10 eventos — o modelo será frágil. Modelos "
                             "binários precisam de eventos suficientes para estimar "
                             "com precisão.")
        else:
            colb = st.selectbox("Coluna binária", list(df.columns), key="pb_col")
            y_bin = df[colb]

        st.subheader("2. Preditores e horizonte")
        c1, c2, c3 = st.columns(3)
        with c1:
            xb = st.multiselect("Preditores", list(df.columns), key="pb_x")
        with c2:
            h = st.number_input("Horizonte h (meses à frente)", 0, 24, 6)
        with c3:
            tipo_b = st.selectbox("Modelo", ["probit", "logit"])
        per_b = st.text_input("Início (opcional)", "", key="pb_per")

        if xb and y_bin is not None and st.button("Estimar", type="primary", key="btn_pb"):
            try:
                yv = y_bin.shift(-h).rename("evento")
                d = pd.concat([yv, df[xb]], axis=1)
                if per_b.strip():
                    d = d[d.index >= pd.Timestamp(per_b)]
                d = d.dropna()
                if d.shape[0] < 20 or d["evento"].sum() < 3:
                    st.error("Amostra ou número de eventos insuficiente.")
                else:
                    res = M.rodar_binario(d["evento"], d[xb], tipo_b)
                    mt = M.metricas_classificacao(res, d["evento"], d[xb])
                    cc = st.columns(4)
                    cc[0].metric("Observações", int(res.nobs))
                    cc[1].metric("Eventos", int(d["evento"].sum()))
                    cc[2].metric("Pseudo-R²", f"{mt['pseudo_R2']:.4f}")
                    cc[3].metric("AUC", f"{mt['AUC']:.4f}" if not np.isnan(mt["AUC"]) else "—")

                    st.subheader("Coeficientes")
                    st.dataframe(M.tabela_coeficientes(res), use_container_width=True)
                    st.caption("O **sinal** é interpretável diretamente; a magnitude não "
                               "(é efeito sobre o índice latente, não sobre a probabilidade).")

                    st.subheader("Efeitos marginais médios")
                    try:
                        mfx = res.get_margeff(at="mean")
                        st.text(str(mfx.summary()))
                        st.caption("Aqui sim: variação na **probabilidade** por unidade "
                                   "do preditor.")
                    except Exception:
                        st.caption("Efeitos marginais indisponíveis.")

                    c1, c2 = st.columns(2)
                    with c1:
                        st.subheader("Curva ROC")
                        if mt["fpr"] is not None:
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(x=mt["fpr"], y=mt["tpr"],
                                                     name=f"AUC={mt['AUC']:.3f}",
                                                     fill="tozeroy"))
                            fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], name="aleatório",
                                                     line=dict(dash="dash", color="gray")))
                            fig.update_layout(height=380, xaxis_title="Falso positivo",
                                              yaxis_title="Verdadeiro positivo",
                                              margin=dict(t=30))
                            st.plotly_chart(fig, use_container_width=True)
                    with c2:
                        st.subheader("Probabilidade prevista")
                        fig2 = go.Figure()
                        fig2.add_trace(go.Scatter(x=d.index, y=mt["prob"],
                                                  name="P(evento)", fill="tozeroy"))
                        fig2.add_trace(go.Scatter(x=d.index, y=d["evento"],
                                                  name="ocorrido", mode="markers",
                                                  marker=dict(size=4, color="red")))
                        fig2.update_layout(height=380, margin=dict(t=30))
                        st.plotly_chart(fig2, use_container_width=True)

                    caixa_interp("""
<b>AUC:</b> 0,5 = aleatório | 0,7–0,8 = aceitável | 0,8–0,9 = bom | >0,9 = excelente
(desconfie de sobreajuste se a amostra for pequena).<br><br>
<b>Cuidado central:</b> com poucos eventos de recessão na amostra, o modelo pode
parecer ótimo dentro da amostra e falhar fora dela. Valide sempre em período
reservado.
""")
            except Exception as e:
                st.error(f"Erro: {e}")

# ===========================================================================
# ABA 9 — REGULARIZAÇÃO
# ===========================================================================
with abas[9]:
    st.header("Regularização: LASSO, Ridge e Elastic Net")
    caixa_equacao("Elastic Net",
                  r"\min_{\beta} \; \frac{1}{2n}\|y - X\beta\|^2_2 + \lambda\left[\rho\|\beta\|_1 + \frac{(1-\rho)}{2}\|\beta\|_2^2\right]",
                  "ρ = 1 → LASSO (só L1, seleciona zerando). ρ = 0 → Ridge (só L2, "
                  "encolhe sem zerar). Entre os dois → Elastic Net.")
    st.markdown("""
Indicado quando há **muitos preditores** em relação ao número de observações, ou
**colinearidade forte** — o caso típico de vértices vizinhos de uma curva de juros.

**Por que Elastic Net e não LASSO puro:** sob colinearidade, o LASSO escolhe
*arbitrariamente* um preditor do grupo e zera os demais, e a escolha é instável
a pequenas perturbações. O termo L2 do Elastic Net faz o grupo ser
selecionado em conjunto, estabilizando o resultado.
""")
    caixa_alerta("A padronização é **obrigatória**: a penalização é proporcional à "
                 "escala dos coeficientes. Crédito em R$ milhões e Selic em % não "
                 "são comparáveis sem z-score (já aplicado por padrão).")

    df = base_ativa()
    if df is None:
        st.info("Carregue uma base na barra lateral.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            y_r = st.selectbox("Variável dependente", list(df.columns), key="reg_y")
        with c2:
            padrao = [c for c in df.columns if c.startswith("prazo_")][:12]
            x_r = st.multiselect("Preditores candidatos",
                                 [c for c in df.columns if c != y_r],
                                 default=padrao, key="reg_x")
        c3, c4, c5, c6 = st.columns(4)
        with c3:
            met = st.selectbox("Método", ["elasticnet", "lasso", "ridge"],
                               format_func={"elasticnet": "Elastic Net",
                                            "lasso": "LASSO", "ridge": "Ridge"}.get)
        with c4:
            l1r = st.slider("l1_ratio (ρ)", 0.05, 1.0, 0.5, 0.05,
                            disabled=(met != "elasticnet"))
        with c5:
            cvn = st.number_input("Folds (CV temporal)", 2, 10, 5)
        with c6:
            per_r = st.text_input("Início", "", key="reg_per")

        if y_r and x_r and st.button("Estimar", type="primary", key="btn_reg"):
            try:
                d = core.amostra_comum(df, [y_r] + x_r,
                                       inicio=per_r if per_r.strip() else None)
                if d.shape[0] < 20:
                    st.error(f"Amostra insuficiente: {d.shape[0]} observações.")
                else:
                    r = M.rodar_regularizacao(d[y_r], d[x_r], met, l1r, cv=cvn)
                    cc = st.columns(4)
                    cc[0].metric("Observações", d.shape[0])
                    cc[1].metric("α ótimo (CV)",
                                 f"{r['alpha']:.5f}" if r["alpha"] else "—")
                    cc[2].metric("Selecionadas",
                                 f"{r['n_selecionadas']} / {r['n_total']}")
                    cc[3].metric("R² (in-sample)", f"{r['R2_in_sample']:.4f}")

                    if r["n_selecionadas"] == 0:
                        caixa_alerta("Nenhuma variável selecionada: a penalização "
                                     "ótima zerou tudo, o que indica que os preditores "
                                     "não têm poder explicativo sobre esta variável "
                                     "nesta amostra. Tente outra transformação da "
                                     "dependente, outro período, ou reduza o l1_ratio.")

                    st.subheader("Coeficientes")
                    st.dataframe(r["coeficientes"].round(6), use_container_width=True,
                                 height=320)
                    nz = r["coeficientes"][r["coeficientes"]["selecionada"]]
                    if not nz.empty:
                        fig = px.bar(nz.head(25), x="coeficiente", y="variavel",
                                     orientation="h",
                                     color=nz.head(25)["coeficiente"] > 0,
                                     color_discrete_map={True: "#2c5282", False: "#c53030"})
                        fig.update_layout(height=max(300, 26 * len(nz.head(25))),
                                          showlegend=False, margin=dict(t=30))
                        st.plotly_chart(fig, use_container_width=True)
                        st.caption("Coeficientes de variáveis padronizadas: comparáveis "
                                   "entre si em magnitude.")

                    st.divider()
                    st.subheader("Stability selection")
                    st.caption("Reestima o modelo em centenas de subamostras e conta com "
                               "que frequência cada variável é selecionada. Protege "
                               "contra a instabilidade do LASSO sob colinearidade.")
                    nb = st.slider("Reamostragens", 20, 300, 100, 20, key="ss_n")
                    if st.button("Rodar stability selection"):
                        with st.spinner("Reamostrando…"):
                            ss = M.stability_selection(d[y_r], d[x_r], met, l1r, n_boot=nb)
                        st.dataframe(ss.round(3), use_container_width=True, height=300)
                        fig2 = px.bar(ss.head(20), x="freq_selecao", y="variavel",
                                      orientation="h", color="estavel",
                                      color_discrete_map={True: "#38a169", False: "#a0aec0"})
                        fig2.add_vline(x=0.6, line_dash="dash", line_color="red")
                        fig2.update_layout(height=max(300, 26 * min(20, len(ss))),
                                           margin=dict(t=30))
                        st.plotly_chart(fig2, use_container_width=True)
                        caixa_interp("Variáveis com frequência acima de <b>0,60</b> "
                                     "(linha vermelha) são consideradas estáveis. "
                                     "Uma variável selecionada no ajuste único mas com "
                                     "baixa frequência aqui foi escolhida por acaso — "
                                     "não a interprete como achado.")
            except Exception as e:
                st.error(f"Erro: {e}")
