Laboratório de Macroeconometria
Ambiente interativo (Streamlit) para exploração, transformação, teste e
modelagem de séries macroeconômicas.
Instalação
```bash
pip install -r requirements.txt
```
Execução
```bash
streamlit run app.py
```
O navegador abre em `http://localhost:8501`.
Estrutura
Arquivo	Conteúdo
`app.py`	Interface: abas, gráficos, controles
`core.py`	Carregamento e transformações
`modelos.py`	Motor econométrico (testes, VAR, VECM, etc.)
`manual.py`	Guia de uso e interpretação
Abas
Manual — fluxo de trabalho, escolha de variáveis, interpretações
Explorar — cobertura, gráficos, correlações
Transformar — log-diff, diferenças, HP, z-score, spreads
Estacionariedade — ADF, KPSS, diagnóstico cruzado, ordem I(d)
Regressão — MQO com HAC, diagnósticos, VIF, backtest
Cointegração — Engle-Granger e Johansen
VAR/SVAR — seleção de lags, IRF, FEVD, Granger, estabilidade
VECM — alfa (ajuste) e beta (longo prazo)
Probit/Logit — previsão de recessão, ROC/AUC, efeitos marginais
Regularização — LASSO, Ridge, Elastic Net, stability selection
Uso
Na barra lateral, carregue a base (.xlsx ou .csv) com uma coluna `data`.
Comece pela aba Manual se for a primeira vez.
