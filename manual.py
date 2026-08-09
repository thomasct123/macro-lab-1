"""
manual.py — Guia de uso do Laboratório de Macroeconometria
Orientação sobre qual variável usar em cada teste/modelo e como interpretar.
"""
import streamlit as st


def render():
    st.header("📖 Manual do Laboratório")
    st.caption("Guia de escolha de variáveis, sequência de trabalho e "
               "interpretação de resultados.")

    t = st.tabs(["Fluxo de trabalho", "Escolha de variáveis",
                 "Guia dos modelos", "Interpretações comentadas",
                 "Armadilhas comuns"])

    # =======================================================================
    with t[0]:
        st.subheader("A sequência que evita erros")
        st.markdown("""
A ordem abaixo não é burocracia: cada etapa é pré-requisito estatístico da
seguinte. Pular a etapa 2 é a origem da maior parte dos resultados falsos em
macroeconometria aplicada.

**1. Explorar** — veja a cobertura de cada série. A amostra efetiva de um
modelo multivariado é a **interseção** das séries usadas. Se a curva DI começa
em 2015, qualquer modelo que a inclua começa em 2015, mesmo que a Selic tenha
dados desde 1974.

**2. Transformar** — deixe cada série estacionária. Índices e volumes viram
log-diferença; taxas em nível viram primeira diferença; taxas já em variação
podem ficar como estão.

**3. Testar estacionariedade** — confirme com ADF e KPSS. Não confie na
intuição: séries que parecem estacionárias no gráfico frequentemente não são.

**4. Escolher o modelo** conforme o diagnóstico:

| Situação | Modelo indicado |
|---|---|
| Todas I(0) | Regressão, VAR |
| Todas I(1), **sem** cointegração | VAR em primeiras diferenças |
| Todas I(1), **com** cointegração | VECM |
| Dependente binária | Probit / Logit |
| Muitos preditores, poucas observações | Elastic Net |

**5. Diagnosticar** — resíduos autocorrelacionados, VAR instável ou VIF alto
invalidam a leitura dos coeficientes, mesmo com R² alto.

**6. Validar fora da amostra** — R² dentro da amostra mede ajuste, não
capacidade preditiva. Use o backtest recursivo.
""")

        st.subheader("Sobre o gargalo amostral")
        st.info("""
**Regra prática para VAR:** você precisa de aproximadamente
10 × (nº de variáveis × nº de lags) observações. Um VAR com 4 variáveis e
6 lags implica ~240 observações — mais do que muitas séries brasileiras
recentes oferecem. Prefira sistemas de 3 a 4 variáveis com 2 a 4 lags.
""")

    # =======================================================================
    with t[1]:
        st.subheader("Que variável usar em cada situação")

        st.markdown("#### Por natureza da série")
        st.markdown("""
| Natureza | Exemplos | Transformação indicada | Por quê |
|---|---|---|---|
| Número-índice com tendência | PIB real | `logdiff` ou `logdiff12` | O nível é I(1); a variação é o conceito econômico relevante |
| Volume monetário | Concessões de crédito | `logdiff` ou `logdiff12` | Cresce exponencialmente; interessa a taxa de expansão |
| Taxa de juros em nível | Selic, vértices da curva | `nivel` ou `diff` | Costuma ser I(1); use `diff` se o teste confirmar |
| Taxa de variação | IPCA mensal | `nivel` ou `acum12` | Já é uma taxa; `acum12` dá inflação em 12 meses |
| Taxa de estoque | Desocupação | `diff` ou `hp_ciclo` | Nível é persistente; interessa a variação ou o desvio da tendência |
| Demografia | População | `logdiff12` | Cresce suavemente; raramente é regressor de ciclo |
| Expectativa | Focus t+1…t+4 | `nivel` | Já está em unidade comparável ao realizado |
| Estrutura a termo | prazo_1m…prazo_12m | **spread** | Vértices vizinhos têm correlação ~0,99 — use a inclinação |
""")

        st.markdown("#### Combinações que fazem sentido econômico")
        st.markdown("""
**Transmissão de política monetária (VAR/SVAR)**
Selic (Δ) → crédito (Δln) → atividade (Δln PIB) → inflação (IPCA).
Ordene do mais lento ao mais rápido a reagir.

**Curva de Phillips**
Dependente: IPCA. Explicativas: desocupação (ou hiato via `hp_ciclo`) e
expectativa `ipca_t1`. O coeficiente do desemprego mede o custo de desinflação;
o da expectativa mede ancoragem.

**Regra de Taylor**
Dependente: Selic. Explicativas: desvio da inflação esperada (`ipca_t1`) e hiato
do produto (`pib_real_indice_hpc`). O princípio de Taylor exige coeficiente
maior que 1 na inflação.

**Previsão de recessão (Probit)**
Dependente: binária construída de `pib_real_indice_dln < 0`.
Preditor central: `spread_prazo_12m_prazo_1m`. Complementos: expansão do crédito,
variação do desemprego.

**Cointegração de longo prazo**
Candidatos naturais: ln(PIB) e ln(crédito) — se compartilham tendência, existe
relação de equilíbrio e o VECM revela a velocidade de ajuste.
""")

        st.warning("""
**Variáveis a evitar como regressores:** `populacao_projecao` (é cenário, não
dado observado, e vai até 2060 — vai truncar sua amostra ou introduzir dado
sintético). As colunas `*_t1…t4` do Focus interpoladas entre dezembros também
merecem cautela: os valores intra-anuais são construídos, não pesquisados.
""")

    # =======================================================================
    with t[2]:
        st.subheader("Guia dos modelos")

        with st.expander("ADF e KPSS — testes de raiz unitária", expanded=True):
            st.latex(r"\Delta y_t = \alpha + \beta t + \gamma y_{t-1} + \sum \delta_i \Delta y_{t-i} + \varepsilon_t")
            st.markdown("""
**O que fazem:** determinam se uma série é estacionária.

**Hipóteses opostas:** ADF tem H₀ = *tem raiz unitária*; KPSS tem H₀ =
*é estacionária*. Rodar os dois dá diagnóstico cruzado.

**Quando usar:** sempre, antes de qualquer modelo de séries temporais.

**Limitação:** ambos perdem poder com quebras estruturais. O Plano Real (1994)
e a pandemia (2020) são quebras óbvias nas séries brasileiras — um teste pode
indicar não-estacionariedade que na verdade é quebra de nível.
""")

        with st.expander("Regressão (MQO) com erros HAC"):
            st.latex(r"y_t = \beta_0 + \sum_k \beta_k x_{kt} + \varepsilon_t")
            st.markdown("""
**O que faz:** estima relação linear entre dependente e explicativas.

**Erros-padrão HAC (Newey-West):** corrigem simultaneamente heterocedasticidade
e autocorrelação. Em séries temporais são o padrão — erros clássicos
subestimam a incerteza e produzem significância ilusória.

**Diagnósticos que importam:**
- *Ljung-Box*: p < 0,05 indica autocorrelação residual — o modelo está
  mal especificado (falta dinâmica). Considere adicionar defasagens ou usar VAR.
- *VIF > 10*: multicolinearidade grave; coeficientes instáveis.
- *Breusch-Pagan*: heterocedasticidade (já tratada pelo HAC).
""")

        with st.expander("VAR — Vetor Autorregressivo"):
            st.latex(r"\mathbf{y}_t = \mathbf{c} + \sum_{i=1}^{p}\mathbf{A}_i\mathbf{y}_{t-i} + \mathbf{u}_t")
            st.markdown("""
**O que faz:** trata todas as variáveis como endógenas, sem impor teoria a
priori (Sims, 1980).

**Não interprete os coeficientes individuais** — são muitos e sem significado
isolado. A leitura vem de três objetos:

1. **Resposta a impulso (IRF):** o que acontece com cada variável após um
   choque de um desvio-padrão em outra, ao longo de N meses.
2. **Decomposição da variância (FEVD):** que fração da incerteza de previsão
   de cada variável vem de cada choque.
3. **Causalidade de Granger:** se os lags de X melhoram a previsão de Y.

**SVAR e ordenação de Cholesky:** a identificação supõe que variáveis anteriores
na ordem não reagem contemporaneamente às posteriores. Ordem usual:
atividade → preços → juros → crédito. **Teste ordenações alternativas** — se os
resultados mudam muito, a identificação é frágil.

**Pré-requisito:** todas as séries estacionárias. Verifique a estabilidade
(todas as raízes com módulo < 1).
""")

        with st.expander("Cointegração e VECM"):
            st.latex(r"\Delta \mathbf{y}_t = \boldsymbol{\alpha}\boldsymbol{\beta}'\mathbf{y}_{t-1} + \sum_{i=1}^{k-1}\boldsymbol{\Gamma}_i\Delta\mathbf{y}_{t-i} + \boldsymbol{\varepsilon}_t")
            st.markdown("""
**Conceito:** séries I(1) podem ter uma combinação linear I(0) — compartilham
tendência estocástica comum. Nesse caso a regressão em nível **não** é espúria,
e diferenciar tudo destruiria a informação de longo prazo.

**Engle-Granger:** bivariado, dois passos. H₀ = não há cointegração.

**Johansen:** multivariado, identifica **quantas** relações existem (rank r).
Leia a tabela de cima para baixo: o rank é o número de rejeições consecutivas.

**Parâmetros do VECM:**
- **β** = relação de longo prazo (o equilíbrio).
- **α** = velocidade de ajuste. Negativo e significativo ⟹ a variável retorna ao
  equilíbrio. Magnitude = fração do desequilíbrio corrigida por período.
- **Γ** = dinâmica de curto prazo.

**α próximo de zero** ⟹ variável fracamente exógena: empurra o sistema mas não
se ajusta a ele.
""")

        with st.expander("Probit / Logit"):
            st.latex(r"P(y_t = 1 \mid X_t) = \Phi(X_t'\beta)")
            st.markdown("""
**O que faz:** modela a probabilidade de um evento binário — tipicamente
recessão h meses à frente.

**Interpretação dos coeficientes:** apenas o **sinal** é diretamente legível.
A magnitude refere-se ao índice latente, não à probabilidade — use os
**efeitos marginais** para isso.

**Avaliação:** AUC, não R². Referência: 0,5 = aleatório, 0,7–0,8 aceitável,
0,8–0,9 bom.

**Risco principal:** poucos eventos. Se sua amostra tem 2 ou 3 recessões, o
modelo memoriza esses episódios e não generaliza. Séries brasileiras pós-2015
têm essencialmente 2015-16 e 2020 — amostra apertada para inferência robusta.
""")

        with st.expander("LASSO, Ridge e Elastic Net"):
            st.latex(r"\min_\beta \frac{1}{2n}\|y - X\beta\|_2^2 + \lambda\left[\rho\|\beta\|_1 + \tfrac{1-\rho}{2}\|\beta\|_2^2\right]")
            st.markdown("""
**Quando usar:** muitos preditores relativamente ao número de observações, ou
colinearidade forte.

**Diferenças:**
- **LASSO (ρ=1):** zera coeficientes, faz seleção. Sob colinearidade, escolhe
  arbitrariamente um do grupo — e a escolha é instável.
- **Ridge (ρ=0):** encolhe sem zerar. Estável, mas não seleciona.
- **Elastic Net:** combina os dois. Seleciona **em grupo**, muito mais estável
  sob colinearidade. É a escolha indicada para estrutura a termo.

**Padronização é obrigatória** — a penalização é proporcional à escala.

**Limitação conceitual central:** estas são ferramentas de *predição e seleção*,
não de *inferência causal*. Uma variável selecionada prevê bem; isso não
significa que cause. E sob colinearidade, a não-seleção de uma variável não é
evidência de que ela seja irrelevante — a informação dela pode ter sido
absorvida por outra do mesmo grupo.

**Stability selection:** reamostra e conta a frequência de seleção. Variáveis
acima de 0,60 são consideravelmente mais confiáveis do que as escolhidas em um
único ajuste.
""")

    # =======================================================================
    with t[3]:
        st.subheader("Interpretações comentadas")

        st.markdown("#### Exemplo 1 — Curva de Phillips")
        st.code("""Dependente:   ipca_var_mensal_pct
Explicativas: taxa_desocupacao_pct, ipca_t1
Período:      2012-01-01 em diante""", language="text")
        st.markdown("""
Suponha que o resultado seja:

| variável | coef. | p-valor |
|---|---|---|
| taxa_desocupacao_pct | −0,042 | 0,018 ** |
| ipca_t1 | 0,610 | 0,000 *** |

**Leitura:** cada ponto percentual a mais de desemprego reduz a inflação mensal
em 0,042 p.p. — é a relação de Phillips com o sinal esperado. O coeficiente de
0,61 na expectativa indica ancoragem parcial: mais da metade da expectativa se
transmite à inflação corrente, mas não integralmente.

**O que checar antes de acreditar:** Ljung-Box nos resíduos (se houver
autocorrelação, falta dinâmica no modelo) e se o período inclui a pandemia,
que distorce fortemente a relação desemprego-inflação.
""")

        st.divider()
        st.markdown("#### Exemplo 2 — VAR de transmissão monetária")
        st.code("""Sistema: selic_realizada_pct_am_d, concessoes_total_rs_milhoes_dln,
         pib_real_indice_dln, ipca_var_mensal_pct
Lags: 3 | Horizonte: 24 meses""", language="text")
        st.markdown("""
**IRF esperada teoricamente:** choque positivo na Selic → contração do crédito
em 2 a 6 meses → desaceleração do PIB em 6 a 12 meses → recuo da inflação em
9 a 18 meses. Esse padrão de defasagens crescentes é a assinatura da transmissão
monetária.

**Se a IRF mostrar inflação *subindo* após aperto monetário** — o chamado
*price puzzle* — a causa usual é omissão de variável antecipatória (o BC sobe
juros porque *prevê* inflação futura). A correção padrão é incluir um índice de
commodities ou expectativa de inflação no sistema.

**FEVD:** se choques de juros explicam apenas 5% da variância do PIB em 24 meses,
a política monetária tem papel modesto nas flutuações daquele período — resultado
substantivo, não falha do modelo.
""")

        st.divider()
        st.markdown("#### Exemplo 3 — VECM entre PIB e crédito")
        st.code("""Sistema: log(pib_real_indice), log(concessoes_total_rs_milhoes)
Rank: 1 | Lags em diferença: 2""", language="text")
        st.markdown("""
Suponha α = −0,035 na equação do crédito e α = −0,002 na do PIB.

**Leitura:** o crédito corrige 3,5% do desequilíbrio por mês (meia-vida em torno
de 19 meses); o PIB praticamente não se ajusta. Isso indica que **o crédito é
quem retorna ao equilíbrio**, enquanto o PIB se comporta como fracamente exógeno
— empurra a relação sem responder a ela.

**Cuidado:** o β normalizado é uma relação de equilíbrio, não uma elasticidade
causal. E o resultado depende do rank escolhido — teste a sensibilidade.
""")

        st.divider()
        st.markdown("#### Exemplo 4 — Probit de recessão")
        st.code("""Dependente:  pib_real_indice_dln < 0  (h = 6 meses)
Preditor:    spread_prazo_12m_prazo_1m""", language="text")
        st.markdown("""
Coeficiente negativo e AUC de 0,72.

**Leitura:** achatamento ou inversão da curva (spread menor) eleva a
probabilidade de contração seis meses à frente — o resultado mais replicado da
literatura de previsão de recessão. AUC de 0,72 é desempenho aceitável.

**Ressalva séria:** com curva DI disponível apenas desde 2015, a amostra contém
pouquíssimos episódios de contração. Um AUC alto aqui pode refletir memorização
de dois eventos, não capacidade preditiva genuína. Reserve período para
validação antes de concluir qualquer coisa.
""")

    # =======================================================================
    with t[4]:
        st.subheader("Armadilhas comuns")

        st.error("""
**1. Regressão espúria**
Regredir duas séries com tendência produz R² alto e t-estatísticas grandes sem
qualquer relação real (Granger & Newbold, 1974). É o erro mais frequente.
*Antídoto:* teste estacionariedade **antes**; se ambas I(1), teste cointegração.
""")

        st.error("""
**2. Confundir Granger com causalidade**
Causalidade de Granger é **precedência temporal preditiva**. X pode
Granger-causar Y porque ambos respondem a um terceiro fator não incluído.
*Antídoto:* trate como evidência de precedência, não de mecanismo causal.
""")

        st.error("""
**3. Ignorar quebras estruturais**
Plano Real (1994), adoção do regime de metas (1999) e a pandemia (2020) são
quebras profundas. Estimar 1974–2026 num único regime supõe que a economia
brasileira funcionou da mesma forma o tempo todo — o que é insustentável.
*Antídoto:* recorte por regime; para relações comportamentais, tipicamente
pós-1999 ou pós-2003.
""")

        st.error("""
**4. Sobreajuste em amostras curtas**
Um VAR com 5 variáveis e 12 lags estima 300+ coeficientes. Com 140 observações,
o modelo ajusta ruído.
*Antídoto:* mantenha sistemas pequenos; valide fora da amostra; compare com
benchmark simples.
""")

        st.error("""
**5. Tratar dado interpolado como observação**
Séries trimestrais ou anuais convertidas para mensal por interpolação **não**
ganham informação nova — os pontos intermediários são função determinística dos
vizinhos. Isso infla artificialmente o n e a autocorrelação, produzindo
erros-padrão otimistas.
*Antídoto:* lembre que a frequência informacional do PIB continua trimestral;
considere modelar na frequência nativa quando a inferência for o objetivo.
""")

        st.error("""
**6. Misturar naturezas de dado sem distinguir**
Realizado, expectativa de mercado e projeção demográfica são epistemologicamente
diferentes. Colocá-los lado a lado como se fossem o mesmo tipo de regressor
pode gerar conclusões sem sentido — especialmente porque as expectativas
incorporam informação que o modelo trata como se fosse contemporânea.
""")

        st.error("""
**7. Interpretar seleção do LASSO como teste de teoria**
Sob colinearidade, a não-seleção de uma variável **não** é evidência de
irrelevância — a informação pode ter sido absorvida por outra do grupo. Um
LASSO que mantém `prazo_9m` e descarta o spread não provou que a inclinação não
importa.
*Antídoto:* use Elastic Net e stability selection; construa constructos
teóricos (spreads, razões) em vez de despejar variáveis cruas.
""")
