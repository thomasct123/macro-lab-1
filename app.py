"""
=============================================================================
LABORATÓRIO DE MACROECONOMETRIA — v2
=============================================================================
Novidades desta versão:
  · Estacionariedade ANTES de Transformar (ordem de diagnóstico correta)
  · Correlação integrada à aba de Regressão
  · Transformação de várias variáveis simultaneamente
  · Carregamento direto do GitHub (repositório pré-configurado)
  · Salvamento de outputs em pastas locais ou no GitHub
  · Projetos: salvar e restaurar configurações do app

Execução:  streamlit run app.py
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
import persistencia as P

st.set_page_config(page_title="Laboratório de Macroeconometria",
                   page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")

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
    .pill {display:inline-block; background:#edf2f7; color:#2d3748;
           padding:2px 9px; margin:2px; border-radius:10px; font-size:0.78rem;}
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
# ESTADO DA SESSÃO
# ---------------------------------------------------------------------------
_defaults = {
    "df": None,
    "df_trans": None,
    "origem_base": "",
    "vars_estacionariedade": [],   # lista trazida da aba de Estacionariedade
    "res_estacionariedade": None,
    "outputs": {},                 # resultados acumulados para salvar
    "pasta_saida": "",
    "gh_token": "",
    "gh_cfg": dict(P.GITHUB_PADRAO),
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def base_ativa():
    if st.session_state.df is None:
        return None
    if st.session_state.df_trans is None or st.session_state.df_trans.empty:
        return st.session_state.df
    return st.session_state.df.join(st.session_state.df_trans, how="left")


def registrar_output(chave, tabelas: dict):
    """Acumula resultados para salvamento posterior."""
    st.session_state.outputs[chave] = tabelas


def bloco_salvar(chave, nome_base, tabelas: dict, texto_extra=None):
    """Bloco padronizado de salvamento — usado em todas as abas de modelo."""
    with st.expander("💾 Salvar resultados"):
        c1, c2 = st.columns([3, 2])
        with c1:
            raiz = st.text_input("Pasta raiz", value=st.session_state.pasta_saida,
                                 key=f"raiz_{chave}",
                                 placeholder=r"C:\Users\Thomas\Desktop\Projetos\Resultados")
            existentes = P.listar_subpastas(raiz) if raiz.strip() else []
            if existentes:
                escolha = st.selectbox("Subpasta existente (opcional)",
                                       ["— criar nova —"] + existentes,
                                       key=f"sub_{chave}")
            else:
                escolha = "— criar nova —"
            nova = st.text_input("Subpasta (níveis separados por /)",
                                 key=f"nova_{chave}",
                                 placeholder="Projeto/VAR/rodada 1")
        with c2:
            st.caption("**Download direto**")
            try:
                st.download_button("⬇️ Baixar .xlsx",
                                   data=P.tabelas_para_bytes(tabelas),
                                   file_name=f"{nome_base}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   key=f"dl_{chave}", use_container_width=True)
            except Exception as e:
                st.caption(f"Indisponível: {e}")

        cs1, cs2 = st.columns(2)
        with cs1:
            if st.button("Salvar em pasta local", key=f"btn_local_{chave}",
                         use_container_width=True):
                if not raiz.strip():
                    st.error("Informe a pasta raiz.")
                else:
                    try:
                        niveis = []
                        if escolha != "— criar nova —":
                            niveis.append(escolha)
                        if nova.strip():
                            niveis += [n for n in nova.split("/") if n.strip()]
                        pasta = P.resolver_pasta(raiz, niveis)
                        dest = P.salvar_tabelas(tabelas, pasta, nome_base)
                        if texto_extra:
                            P.salvar_texto(texto_extra, pasta, nome_base + "_resumo")
                        st.session_state.pasta_saida = raiz
                        st.success(f"Salvo em: {dest}")
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
        with cs2:
            if st.button("Enviar ao GitHub", key=f"btn_gh_{chave}",
                         use_container_width=True):
                tok = st.session_state.gh_token
                if not tok:
                    st.error("Informe um token na barra lateral (seção GitHub).")
                else:
                    try:
                        cfg = st.session_state.gh_cfg
                        sub = "/".join([n for n in nova.split("/") if n.strip()]) \
                              if nova.strip() else "resultados"
                        caminho = f"{sub}/{nome_base}_{P.carimbo()}.xlsx"
                        p = P.enviar_para_github(
                            P.tabelas_para_bytes(tabelas), caminho,
                            cfg["owner"], cfg["repo"], cfg["branch"], tok)
                        st.success(f"Enviado: {p}")
                    except Exception as e:
                        st.error(f"Erro: {e}")


# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("📊 Laboratório")
    st.caption("Macroeconometria aplicada")
    st.divider()

    st.subheader("Carregar base")
    cfg = st.session_state.gh_cfg

    # ---- opção 1: um clique no repositório padrão -------------------------
    st.markdown("**Do GitHub**")
    st.caption(f"`{cfg['owner']}/{cfg['repo']}` · branch `{cfg['branch']}`")

    if st.button("🔎 Listar bases do repositório", use_container_width=True):
        try:
            arqs = P.listar_arquivos_github(cfg["owner"], cfg["repo"],
                                            cfg["branch"],
                                            token=st.session_state.gh_token or None)
            st.session_state["gh_arquivos"] = [a for a in arqs if not a.get("pasta")]
            if not st.session_state["gh_arquivos"]:
                st.warning("Nenhum .xlsx/.csv encontrado na raiz do repositório.")
        except Exception as e:
            st.error(str(e))

    arquivos = st.session_state.get("gh_arquivos", [])
    if arquivos:
        nomes = [f"{a['nome']}  ({a['tamanho_kb']} KB)" for a in arquivos]
        i = st.selectbox("Arquivo", range(len(nomes)),
                         format_func=lambda k: nomes[k], key="gh_sel")
        if st.button("⬇️ Carregar do GitHub", type="primary",
                     use_container_width=True):
            try:
                with st.spinner("Baixando…"):
                    df = P.baixar_base_github(
                        arquivos[i]["url"],
                        token=st.session_state.gh_token or None)
                st.session_state.df = core.carregar_base_df(df)
                st.session_state.df_trans = pd.DataFrame(index=st.session_state.df.index)
                st.session_state.origem_base = f"GitHub · {arquivos[i]['nome']}"
                st.success(f"{st.session_state.df.shape[0]} linhas × "
                           f"{st.session_state.df.shape[1]} colunas")
            except Exception as e:
                st.error(f"Erro: {e}")

    with st.expander("Outro repositório"):
        o = st.text_input("Owner", value=cfg["owner"], key="gh_o")
        rp = st.text_input("Repositório", value=cfg["repo"], key="gh_r")
        br = st.text_input("Branch", value=cfg["branch"], key="gh_b")
        if st.button("Aplicar", use_container_width=True):
            st.session_state.gh_cfg = {"owner": o, "repo": rp, "branch": br}
            st.session_state.pop("gh_arquivos", None)
            ok, msg = P.testar_conexao_github(o, rp, br,
                                              st.session_state.gh_token or None)
            (st.success if ok else st.error)(msg)

    st.divider()
    st.markdown("**Do computador**")
    up = st.file_uploader("Arquivo local", type=["xlsx", "xls", "csv"],
                          label_visibility="collapsed")
    cam = st.text_input("…ou caminho", value="", label_visibility="collapsed",
                        placeholder=r"C:\...\base.xlsx")
    if st.button("Carregar arquivo local", use_container_width=True):
        try:
            fonte = up if up is not None else (cam if cam.strip() else None)
            if fonte is None:
                st.error("Selecione um arquivo ou informe o caminho.")
            else:
                st.session_state.df = core.carregar_base(fonte)
                st.session_state.df_trans = pd.DataFrame(index=st.session_state.df.index)
                st.session_state.origem_base = getattr(fonte, "name", str(fonte))
                st.success(f"{st.session_state.df.shape[0]} linhas × "
                           f"{st.session_state.df.shape[1]} colunas")
        except Exception as e:
            st.error(f"Erro: {e}")

    st.divider()
    with st.expander("🔑 Token GitHub (opcional)"):
        st.caption("Necessário apenas para repositórios privados ou para "
                   "**enviar** resultados. Use um token com o menor escopo "
                   "possível. Ele fica apenas nesta sessão.")
        st.session_state.gh_token = st.text_input(
            "Token", value=st.session_state.gh_token, type="password",
            label_visibility="collapsed")

    if st.session_state.df is not None:
        d = st.session_state.df
        st.divider()
        st.caption(f"📁 {st.session_state.origem_base}")
        st.metric("Período", f"{d.index.min():%Y-%m} → {d.index.max():%Y-%m}")
        c1, c2 = st.columns(2)
        c1.metric("Variáveis", d.shape[1])
        nt = 0 if st.session_state.df_trans is None else st.session_state.df_trans.shape[1]
        c2.metric("Transformadas", nt)


# ---------------------------------------------------------------------------
# ABAS  (Estacionariedade agora vem ANTES de Transformar)
# ---------------------------------------------------------------------------
abas = st.tabs([
    "📖 Manual",
    "🔍 Explorar",
    "📏 Estacionariedade",
    "🔧 Transformar",
    "📉 Regressão",
    "🔗 Cointegração",
    "🌐 VAR / SVAR",
    "⚖️ VECM",
    "🎯 Probit/Logit",
    "🧲 Regularização",
    "🗂 Projetos",
])

# ===========================================================================
# 0 — MANUAL
# ===========================================================================
with abas[0]:
    manual.render()

# ===========================================================================
# 1 — EXPLORAR
# ===========================================================================
with abas[1]:
    st.header("Exploração dos dados")
    df = base_ativa()
    if df is None:
        st.info("Carregue uma base na barra lateral — o botão do GitHub traz "
                "sua base em dois cliques.")
    else:
        st.subheader("Cobertura e estatísticas descritivas")
        st.caption("A **amostra efetiva** de um modelo multivariado é a "
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
            bloco_salvar("explorar", "exploracao",
                         {"cobertura": cob, "series": plot})

# ===========================================================================
# 2 — ESTACIONARIEDADE  (antes de transformar)
# ===========================================================================
with abas[2]:
    st.header("Testes de raiz unitária")
    st.caption("Diagnostique **antes** de transformar: o resultado aqui define "
               "qual transformação cada série precisa.")
    caixa_equacao(
        "Regressão do teste ADF",
        r"\Delta y_t = \alpha + \beta t + \gamma y_{t-1} + \sum_{i=1}^{p}\delta_i \Delta y_{t-i} + \varepsilon_t",
        "H₀: γ = 0 (existe raiz unitária). Rejeitar H₀ ⟹ série estacionária.")

    st.markdown("""
| Teste | Hipótese nula (H₀) | p < 0,05 significa |
|---|---|---|
| **ADF** | tem raiz unitária (não-estacionária) | **é** estacionária |
| **KPSS** | é estacionária | **não é** estacionária |

As nulas são **opostas** — por isso rodamos os dois.
""")

    df = base_ativa()
    if df is None:
        st.info("Carregue uma base na barra lateral.")
    else:
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            vars_t = st.multiselect("Variáveis a testar", list(df.columns),
                                    default=st.session_state.vars_estacionariedade
                                    or list(df.columns[1:4]), key="ms_est")
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
                d_ordem = M.ordem_integracao(s)
                linhas.append({
                    "variavel": v, "n": len(s),
                    "ADF_estat": round(a["estatistica"], 3),
                    "ADF_p": core.formata_p(a["p_valor"]),
                    "KPSS_estat": round(k["estatistica"], 3),
                    "KPSS_p": core.formata_p(k["p_valor"]),
                    "diagnostico": M.diagnostico_conjunto(a, k),
                    "ordem_I(d)": d_ordem,
                    "sugestao": ("manter em nível" if d_ordem == 0
                                 else "1ª diferença ou log-diferença" if d_ordem == 1
                                 else "2ª diferença" if d_ordem == 2
                                 else "verificar quebras"),
                })
            res = pd.DataFrame(linhas)
            st.session_state.res_estacionariedade = res
            # >>> guarda a lista para a aba Transformar (item 7)
            st.session_state.vars_estacionariedade = list(vars_t)

        if st.session_state.res_estacionariedade is not None:
            res = st.session_state.res_estacionariedade
            st.dataframe(res, use_container_width=True)
            caixa_interp("""
✅ <b>I(0)</b> — pode entrar em nível em regressões e VAR.<br>
⚠️ <b>I(1)</b> — diferencie, <i>ou</i> teste cointegração (se várias I(1)
cointegram, use VECM em vez de diferenciar).<br>
❓ <b>Conflito</b> — inspecione o gráfico; tendência determinística pede
especificação "ct"; quebras estruturais distorcem ambos os testes.
""")
            st.caption("➡️ As variáveis testadas ficam disponíveis na aba "
                       "**Transformar**.")
            bloco_salvar("estacionariedade", "testes_estacionariedade",
                         {"resultados": res})

# ===========================================================================
# 3 — TRANSFORMAR  (múltiplas variáveis + lista herdada)
# ===========================================================================
with abas[3]:
    st.header("Transformações")
    st.caption("Regressões com séries não-estacionárias produzem **regressão "
               "espúria**: R² alto sem relação real. Transforme conforme o "
               "diagnóstico da aba anterior.")
    df = base_ativa()
    if df is None:
        st.info("Carregue uma base na barra lateral.")
    else:
        herdadas = [v for v in st.session_state.vars_estacionariedade
                    if v in st.session_state.df.columns]
        if herdadas:
            st.caption("Da aba Estacionariedade: " +
                       " ".join(f'<span class="pill">{v}</span>' for v in herdadas)
                       if False else "")
            st.markdown("<div style='margin:-6px 0 8px 0'>"
                        "<span style='font-size:0.8rem;color:#718096'>"
                        "Testadas em Estacionariedade:</span> " +
                        " ".join(f'<span class="pill">{v}</span>' for v in herdadas) +
                        "</div>", unsafe_allow_html=True)

        st.subheader("Aplicar a várias variáveis de uma vez")
        c1, c2 = st.columns([3, 2])
        with c1:
            usar_herdadas = st.checkbox("Usar as variáveis testadas acima",
                                        value=bool(herdadas),
                                        disabled=not herdadas)
            alvo = st.multiselect(
                "Variáveis de origem", list(st.session_state.df.columns),
                default=herdadas if (usar_herdadas and herdadas) else [],
                key="ms_trans")
        with c2:
            tipos = st.multiselect(
                "Transformações a aplicar", list(core.TRANSFORMACOES.keys()),
                default=["logdiff"],
                format_func=lambda t: core.TRANSFORMACOES[t], key="ms_tipos")

        st.caption(f"Serão criadas **{len(alvo) * len(tipos)}** novas colunas "
                   f"({len(alvo)} variáveis × {len(tipos)} transformações).")

        if st.button("➕ Criar transformações", type="primary",
                     disabled=not (alvo and tipos)):
            criadas, falhas = [], []
            for v in alvo:
                for t in tipos:
                    try:
                        nova = core.aplicar_transformacao(st.session_state.df[v], t)
                        nome = f"{v}{core.sufixo(t)}"
                        st.session_state.df_trans[nome] = nova
                        criadas.append(nome)
                    except Exception as e:
                        falhas.append(f"{v} ({t}): {e}")
            if criadas:
                st.success(f"{len(criadas)} coluna(s) criada(s).")
                with st.expander("Ver colunas criadas"):
                    st.write(criadas)
            for f in falhas:
                st.warning(f)

        with st.expander("Qual transformação usar?"):
            st.markdown("""
| Tipo de série | Transformação | Resultado |
|---|---|---|
| Índice com tendência (PIB) | `logdiff` | crescimento % mensal |
| Índice com sazonalidade | `logdiff12` | crescimento % anual |
| Volume monetário (crédito) | `logdiff` ou `logdiff12` | expansão % |
| Taxa em nível (Selic, desemprego) | `diff` | variação em p.p. |
| Taxa já em variação (IPCA mensal) | `nivel` ou `acum12` | inflação acumulada 12m |
| Extrair componente cíclico | `hp_ciclo` | hiato |
| Preparar para regularização | `zscore` | escala comparável |
""")

        st.divider()
        st.subheader("Construir spread (inclinação da curva)")
        st.caption("O spread longo − curto resolve a colinearidade entre "
                   "vértices e é o preditor de recessão mais robusto da literatura.")
        cs = st.columns([2, 2, 1])
        num = list(st.session_state.df.columns)
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
                         use_container_width=True, height=220)
            c1, c2 = st.columns(2)
            with c1:
                rem = st.multiselect("Remover", list(st.session_state.df_trans.columns))
                if rem and st.button("🗑 Remover selecionadas"):
                    st.session_state.df_trans.drop(columns=rem, inplace=True)
                    st.rerun()
            with c2:
                vis = st.selectbox("Visualizar",
                                   list(st.session_state.df_trans.columns))
            if vis:
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
                fig.update_layout(height=440, showlegend=False, margin=dict(t=40))
                st.plotly_chart(fig, use_container_width=True)
            bloco_salvar("transformar", "base_transformada",
                         {"transformadas": st.session_state.df_trans})
        else:
            st.info("Nenhuma transformação criada ainda.")

# ===========================================================================
# 4 — REGRESSÃO (com seção de correlação)
# ===========================================================================
with abas[4]:
    st.header("Regressão linear (MQO)")
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

        # ---------------- CORRELAÇÃO (item 2) ----------------
        st.divider()
        st.subheader("Correlação entre as variáveis selecionadas")
        st.caption("Diagnóstico prévio: correlações acima de 0,9 entre "
                   "explicativas indicam redundância — os coeficientes ficarão "
                   "instáveis. Correlação alta com y sugere poder explicativo.")
        if x_vars:
            cols_corr = [y_var] + x_vars
            metodo = st.radio("Método", ["pearson", "spearman"], horizontal=True,
                              format_func={"pearson": "Pearson (linear)",
                                           "spearman": "Spearman (ordinal)"}.get,
                              key="corr_met")
            dcorr = df[cols_corr].dropna()
            corr = dcorr.corr(method=metodo)
            cA, cB = st.columns([3, 2])
            with cA:
                figc = px.imshow(corr, text_auto=".2f", aspect="auto",
                                 color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
                figc.update_layout(height=380, margin=dict(t=30))
                st.plotly_chart(figc, use_container_width=True)
            with cB:
                st.markdown("**Correlação com a dependente**")
                cy = corr[y_var].drop(y_var).sort_values(key=abs, ascending=False)
                st.dataframe(cy.rename("correlação").to_frame().round(4),
                             use_container_width=True)
                pares = []
                for i in range(len(x_vars)):
                    for j in range(i + 1, len(x_vars)):
                        v = corr.loc[x_vars[i], x_vars[j]]
                        if abs(v) > 0.9:
                            pares.append(f"`{x_vars[i]}` ↔ `{x_vars[j]}`: {v:.3f}")
                if pares:
                    caixa_alerta("Colinearidade severa entre explicativas:<br>"
                                 + "<br>".join(pares) +
                                 "<br><br>Considere remover uma delas, usar um "
                                 "spread, ou recorrer à regularização.")
            st.caption(f"Amostra da correlação: {dcorr.shape[0]} observações "
                       "(interseção das séries).")
        else:
            st.info("Selecione ao menos uma variável explicativa.")

        # ---------------- ESTIMAÇÃO ----------------
        st.divider()
        st.subheader("Estimação")
        caixa_equacao("Modelo",
                      r"y_t = \beta_0 + \beta_1 x_{1t} + \dots + \beta_k x_{kt} + \varepsilon_t")
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

                tab_coef = M.tabela_coeficientes(res)
                st.subheader("Coeficientes")
                st.dataframe(tab_coef, use_container_width=True)
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
                    caixa_alerta("Autocorrelação nos resíduos: há dinâmica não "
                                 "modelada. Considere defasagens de y ou um VAR.")

                tab_vif = M.calcular_vif(d[x_vars])
                st.subheader("Multicolinearidade (VIF)")
                st.dataframe(tab_vif, use_container_width=True)

                st.subheader("Ajuste e resíduos")
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                    row_heights=[.62, .38],
                                    subplot_titles=("Observado vs. ajustado", "Resíduos"))
                fig.add_trace(go.Scatter(x=d.index, y=d[y_var], name="observado"), row=1, col=1)
                fig.add_trace(go.Scatter(x=d.index, y=res.fittedvalues,
                                         name="ajustado", line=dict(dash="dash")), row=1, col=1)
                fig.add_trace(go.Scatter(x=d.index, y=res.resid, name="resíduo",
                                         line=dict(color="#e53e3e")), row=2, col=1)
                fig.add_hline(y=0, line_dash="dot", row=2, col=1)
                fig.update_layout(height=520, hovermode="x unified", margin=dict(t=50))
                st.plotly_chart(fig, use_container_width=True)

                tabelas = {"coeficientes": tab_coef, "VIF": tab_vif,
                           "correlacao": df[[y_var] + x_vars].dropna().corr(),
                           "diagnosticos": pd.DataFrame(
                               [{k: v for k, v in dg.items() if not k.startswith("_")}]),
                           "ajuste": pd.DataFrame({"observado": d[y_var],
                                                   "ajustado": res.fittedvalues,
                                                   "residuo": res.resid})}
                bloco_salvar("regressao", f"regressao_{y_var}", tabelas,
                             texto_extra=str(res.summary()))

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

# ===========================================================================
# 5 — COINTEGRAÇÃO
# ===========================================================================
with abas[5]:
    st.header("Cointegração")
    caixa_equacao("Relação de longo prazo",
                  r"y_t - \beta x_t = u_t, \quad u_t \sim I(0)",
                  "Se o desvio é estacionário, as séries não se afastam "
                  "indefinidamente: há equilíbrio de longo prazo.")
    df = base_ativa()
    if df is None:
        st.info("Carregue uma base na barra lateral.")
    else:
        sub1, sub2 = st.tabs(["Engle-Granger (bivariado)", "Johansen (multivariado)"])

        with sub1:
            st.caption("H₀: **não** há cointegração. p < 0,05 ⟹ cointegradas. "
                       "Pré-requisito: ambas I(1).")
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
                        caixa_interp(f"<b>{r['conclusao']}</b> — modele com VECM.")
                    else:
                        caixa_alerta(f"{r['conclusao']}. Se ambas I(1), use VAR "
                                     "em primeira diferença.")
                    bloco_salvar("eg", f"cointegracao_EG_{y1}_{x1}",
                                 {"resultado": pd.DataFrame([r])})

        with sub2:
            vj = st.multiselect("Variáveis do sistema", list(df.columns), key="joh_v")
            c1, c2, c3 = st.columns(3)
            with c1:
                det = st.selectbox("Termo determinístico", [-1, 0, 1], index=1,
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
                    caixa_interp(f"<b>{r['interpretacao']}</b><br>Leia de cima "
                                 "para baixo: o rank é o número de rejeições "
                                 "consecutivas. Com rank ≥ 1, use VECM.")
                    bloco_salvar("johansen", "cointegracao_Johansen",
                                 {"tabela": r["tabela"]})

# ===========================================================================
# 6 — VAR / SVAR
# ===========================================================================
with abas[6]:
    st.header("Vetor Autorregressivo (VAR)")
    caixa_equacao("Forma reduzida",
                  r"\mathbf{y}_t = \mathbf{c} + \mathbf{A}_1 \mathbf{y}_{t-1} + \dots + \mathbf{A}_p \mathbf{y}_{t-p} + \mathbf{u}_t",
                  "A leitura vem das respostas a impulso, da decomposição da "
                  "variância e da causalidade de Granger — não dos coeficientes.")
    caixa_alerta("Todas as séries devem ser **estacionárias**. Regra prática: "
                 "observações ≥ 10 × (nº variáveis × nº lags).")

    df = base_ativa()
    if df is None:
        st.info("Carregue uma base na barra lateral.")
    else:
        vv = st.multiselect("Variáveis do sistema (ordem = ordenação de Cholesky)",
                            list(df.columns), key="var_v")
        st.caption("**Ordem importa**: as mais lentas a reagir primeiro. "
                   "Usual: atividade → preços → juros → crédito.")
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
                    st.caption("AIC escolhe mais lags (previsão); BIC é mais "
                               "parcimonioso (inferência).")
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
                irf_df = fe = g = None

                with t1:
                    cA, cB = st.columns(2)
                    with cA:
                        acum = st.checkbox("Resposta acumulada", value=False)
                    with cB:
                        ortog = st.checkbox("Ortogonalizada (Cholesky)", value=True)
                    try:
                        irf_df, _ = M.irf_dataframe(res, hor, ortog, acum)
                        nomes = res.names
                        fig = make_subplots(rows=len(nomes), cols=len(nomes),
                                            subplot_titles=[f"{c}→{r}" for r in nomes
                                                            for c in nomes],
                                            shared_xaxes=True)
                        for i, r_ in enumerate(nomes):
                            for j, c_ in enumerate(nomes):
                                sub = irf_df[(irf_df["choque"] == c_) &
                                             (irf_df["resposta"] == r_)]
                                fig.add_trace(go.Scatter(x=sub["horizonte"], y=sub["valor"],
                                                         showlegend=False,
                                                         line=dict(color="#2c5282")),
                                              row=i + 1, col=j + 1)
                                fig.add_hline(y=0, line_dash="dot", line_color="gray",
                                              row=i + 1, col=j + 1)
                        fig.update_layout(height=240 * len(nomes), margin=dict(t=60))
                        st.plotly_chart(fig, use_container_width=True)
                        caixa_interp("Cada painel: resposta (linha) a um choque "
                                     "(coluna). Cruza zero e retorna ⟹ efeito "
                                     "transitório; persiste ⟹ duradouro.")
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
                    except Exception as e:
                        st.error(f"Erro na FEVD: {e}")

                with t3:
                    ml = st.number_input("Lags no teste", 1, 12, min(4, lag_esc), key="gr_l")
                    if st.button("Calcular matriz de Granger"):
                        g = M.granger_matriz(st.session_state["var_d"], ml)
                        st.session_state["granger_g"] = g
                    g = st.session_state.get("granger_g")
                    if g is not None:
                        fig = px.imshow(g, text_auto=".3f", aspect="auto",
                                        color_continuous_scale="RdYlGn_r",
                                        zmin=0, zmax=0.2,
                                        labels=dict(x="→ efeito", y="causa →"))
                        fig.update_layout(height=380, margin=dict(t=30))
                        st.plotly_chart(fig, use_container_width=True)
                        caixa_interp("Verde (p<0,05): a variável da linha ajuda a "
                                     "prever a da coluna. É <b>precedência "
                                     "temporal</b>, não causalidade estrutural.")

                with t4:
                    st.text(str(res.summary()))

                tabelas = {"IRF": irf_df, "FEVD": fe, "Granger": g,
                           "estabilidade": pd.DataFrame(
                               [{"max_raiz": est["max_raiz"],
                                 "estavel": est["estavel"]}])}
                bloco_salvar("var", "VAR_resultados",
                             {k: v for k, v in tabelas.items() if v is not None},
                             texto_extra=str(res.summary()))

# ===========================================================================
# 7 — VECM
# ===========================================================================
with abas[7]:
    st.header("Modelo Vetorial de Correção de Erros (VECM)")
    caixa_equacao("Especificação",
                  r"\Delta \mathbf{y}_t = \boldsymbol{\alpha}\boldsymbol{\beta}'\mathbf{y}_{t-1} + \sum_{i=1}^{k-1}\boldsymbol{\Gamma}_i \Delta \mathbf{y}_{t-i} + \boldsymbol{\varepsilon}_t",
                  "β = relação de longo prazo. α = velocidade de ajuste. "
                  "Γ = dinâmica de curto prazo.")
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
            determ = st.selectbox("Determinístico", ["ci", "co", "cili", "nc"],
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
                                         deterministic=determ)
                    alpha, beta = M.tabela_vecm(res, list(d.columns))
                    c1, c2 = st.columns(2)
                    with c1:
                        st.subheader("α — velocidade de ajuste")
                        st.dataframe(alpha.round(5), use_container_width=True)
                        st.caption("Negativo e significativo ⟹ a variável se "
                                   "ajusta ao equilíbrio.")
                    with c2:
                        st.subheader("β — relação de longo prazo")
                        st.dataframe(beta.round(5), use_container_width=True)
                    caixa_interp("α = −0,05 ⟹ 5% do desvio corrigido por mês "
                                 "(meia-vida ≈ 14 meses). α ≈ 0 ⟹ variável "
                                 "fracamente exógena: empurra o sistema sem "
                                 "responder a ele.")
                    st.text(str(res.summary()))
                    bloco_salvar("vecm", "VECM_resultados",
                                 {"alpha": alpha, "beta": beta},
                                 texto_extra=str(res.summary()))
                except Exception as e:
                    st.error(f"Erro: {e}")

# ===========================================================================
# 8 — PROBIT / LOGIT
# ===========================================================================
with abas[8]:
    st.header("Modelos de resposta binária (Probit / Logit)")
    caixa_equacao("Probabilidade de evento h meses à frente",
                  r"P(R_{t+h}=1 \mid X_t) = \Phi(\beta_0 + \beta_1 x_{1t} + \dots)")
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
                       f"{int(y_bin.notna().sum())} ({100*y_bin.mean():.1f}%)")
            if y_bin.sum() < 10:
                caixa_alerta("Menos de 10 eventos — o modelo será frágil.")
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
                    cc[3].metric("AUC", f"{mt['AUC']:.4f}"
                                 if not np.isnan(mt["AUC"]) else "—")

                    tab_c = M.tabela_coeficientes(res)
                    st.dataframe(tab_c, use_container_width=True)
                    st.caption("O **sinal** é interpretável; a magnitude não "
                               "(refere-se ao índice latente).")

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
                            fig.update_layout(height=380, margin=dict(t=30),
                                              xaxis_title="Falso positivo",
                                              yaxis_title="Verdadeiro positivo")
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

                    caixa_interp("<b>AUC:</b> 0,5 aleatório · 0,7–0,8 aceitável · "
                                 "0,8–0,9 bom. Com poucos eventos, desconfie de "
                                 "sobreajuste.")
                    bloco_salvar("probit", f"{tipo_b}_h{h}",
                                 {"coeficientes": tab_c,
                                  "probabilidades": pd.DataFrame(
                                      {"prob": mt["prob"], "evento": d["evento"]})},
                                 texto_extra=str(res.summary()))
            except Exception as e:
                st.error(f"Erro: {e}")

# ===========================================================================
# 9 — REGULARIZAÇÃO
# ===========================================================================
with abas[9]:
    st.header("Regularização: LASSO, Ridge e Elastic Net")
    caixa_equacao("Elastic Net",
                  r"\min_{\beta} \; \frac{1}{2n}\|y - X\beta\|^2_2 + \lambda\left[\rho\|\beta\|_1 + \frac{(1-\rho)}{2}\|\beta\|_2^2\right]",
                  "ρ = 1 → LASSO. ρ = 0 → Ridge. Entre os dois → Elastic Net.")
    caixa_alerta("Padronização é **obrigatória** — a penalização é proporcional "
                 "à escala (já aplicada por padrão).")
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
                                     "ótima zerou tudo — os preditores não "
                                     "explicam esta dependente nesta amostra.")

                    st.dataframe(r["coeficientes"].round(6),
                                 use_container_width=True, height=320)
                    nz = r["coeficientes"][r["coeficientes"]["selecionada"]]
                    if not nz.empty:
                        fig = px.bar(nz.head(25), x="coeficiente", y="variavel",
                                     orientation="h",
                                     color=nz.head(25)["coeficiente"] > 0,
                                     color_discrete_map={True: "#2c5282", False: "#c53030"})
                        fig.update_layout(height=max(300, 26 * len(nz.head(25))),
                                          showlegend=False, margin=dict(t=30))
                        st.plotly_chart(fig, use_container_width=True)

                    st.session_state["reg_coefs"] = r["coeficientes"]
                    st.divider()
                    st.subheader("Stability selection")
                    st.caption("Reamostra e conta a frequência de seleção — "
                               "protege contra a instabilidade do LASSO sob "
                               "colinearidade.")
                    nb = st.slider("Reamostragens", 20, 300, 100, 20, key="ss_n")
                    if st.button("Rodar stability selection"):
                        with st.spinner("Reamostrando…"):
                            ss = M.stability_selection(d[y_r], d[x_r], met, l1r, n_boot=nb)
                        st.session_state["reg_ss"] = ss
                        st.dataframe(ss.round(3), use_container_width=True, height=300)
                        fig2 = px.bar(ss.head(20), x="freq_selecao", y="variavel",
                                      orientation="h", color="estavel",
                                      color_discrete_map={True: "#38a169", False: "#a0aec0"})
                        fig2.add_vline(x=0.6, line_dash="dash", line_color="red")
                        fig2.update_layout(height=max(300, 26 * min(20, len(ss))),
                                           margin=dict(t=30))
                        st.plotly_chart(fig2, use_container_width=True)
                        caixa_interp("Frequência acima de <b>0,60</b> ⟹ seleção "
                                     "estável. Baixa frequência ⟹ escolhida por "
                                     "acaso; não interprete como achado.")

                    tabelas = {"coeficientes": r["coeficientes"]}
                    if "reg_ss" in st.session_state:
                        tabelas["stability"] = st.session_state["reg_ss"]
                    bloco_salvar("regularizacao", f"{met}_{y_r}", tabelas)
            except Exception as e:
                st.error(f"Erro: {e}")

# ===========================================================================
# 10 — PROJETOS
# ===========================================================================
with abas[10]:
    st.header("Projetos")
    st.caption("Salve a configuração atual do laboratório e retome depois. "
               "O que se guarda é a **receita** (variáveis, transformações, "
               "parâmetros) — ao restaurar, o app reconstrói o estado e você "
               "re-executa com a base atualizada.")

    pasta_proj = st.text_input(
        "Pasta dos projetos",
        value=str(P.pasta_projetos()),
        help="Padrão: uma pasta oculta na sua área de usuário. "
             "Pode apontar para uma pasta do seu projeto.")

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Salvar configuração atual")
        nome_proj = st.text_input("Nome do projeto",
                                  placeholder=" — crédito e curva")
        if st.button("💾 Salvar projeto", type="primary",
                     disabled=not nome_proj.strip()):
            cfg = {
                "origem_base": st.session_state.origem_base,
                "github": st.session_state.gh_cfg,
                "transformadas": (list(st.session_state.df_trans.columns)
                                  if st.session_state.df_trans is not None else []),
                "vars_estacionariedade": st.session_state.vars_estacionariedade,
                "regressao": {"y": st.session_state.get("ols_y"),
                              "x": st.session_state.get("ols_x", [])},
                "var_sistema": st.session_state.get("var_v", []),
                "var_lags": st.session_state.get("var_lag"),
                "vecm_sistema": st.session_state.get("vecm_v", []),
                "regularizacao": {"y": st.session_state.get("reg_y"),
                                  "x": st.session_state.get("reg_x", [])},
                "pasta_saida": st.session_state.pasta_saida,
            }
            try:
                dest = P.salvar_projeto(nome_proj, P.config_serializavel(cfg),
                                        base=pasta_proj)
                st.success(f"Projeto salvo: {dest.name}")
            except Exception as e:
                st.error(f"Erro: {e}")

    with c2:
        st.subheader("Restaurar projeto")
        try:
            projs = P.listar_projetos(base=pasta_proj)
        except Exception:
            projs = []
        if not projs:
            st.info("Nenhum projeto salvo nesta pasta.")
        else:
            rot = [f"{p['nome']}  ·  {p['salvo_em'][:16].replace('T',' ')}"
                   for p in projs]
            i = st.selectbox("Projeto", range(len(rot)),
                             format_func=lambda k: rot[k])
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("📂 Restaurar", use_container_width=True):
                    try:
                        cfg = P.carregar_projeto(projs[i]["caminho"])
                        st.session_state.vars_estacionariedade = cfg.get(
                            "vars_estacionariedade", [])
                        st.session_state.pasta_saida = cfg.get("pasta_saida", "")
                        if cfg.get("github"):
                            st.session_state.gh_cfg = cfg["github"]
                        st.session_state["_cfg_restaurada"] = cfg
                        st.success("Configuração restaurada. As seleções de "
                                   "modelo aparecem abaixo para você reaplicar.")
                    except Exception as e:
                        st.error(f"Erro: {e}")
            with cc2:
                if st.button("🗑 Excluir", use_container_width=True):
                    P.excluir_projeto(projs[i]["caminho"])
                    st.rerun()

    if "_cfg_restaurada" in st.session_state:
        st.divider()
        st.subheader("Configuração restaurada")
        cfg = st.session_state["_cfg_restaurada"]
        st.json(cfg, expanded=False)
        caixa_interp("""
As <b>transformações</b> precisam ser recriadas na aba Transformar — a lista
acima indica quais existiam. As seleções de variáveis para cada modelo estão
registradas; reaplique-as nas abas correspondentes. Guardamos a receita, não
os objetos estimados, de modo que tudo é recalculado com a base atual.
""")

    st.divider()
    st.subheader("Resultados acumulados nesta sessão")
    if st.session_state.outputs:
        for k in st.session_state.outputs:
            st.caption(f"• {k}")
    else:
        st.caption("Nenhum resultado registrado ainda. Cada aba de modelo tem "
                   "um bloco **Salvar resultados** ao final.")
