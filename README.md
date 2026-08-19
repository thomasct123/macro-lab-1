# Laboratório de Macroeconometria

Ambiente interativo (Streamlit) para exploração, transformação, teste e
modelagem de séries macroeconômicas.

## Instalação

```bash
pip install -r requirements.txt
```

## Execução

```bash
streamlit run app.py
```

O navegador abre em `http://localhost:8501`.

## Estrutura

| Arquivo | Conteúdo |
|---|---|
| `app.py` | Interface: abas, gráficos, controles |
| `core.py` | Carregamento e transformações |
| `modelos.py` | Motor econométrico (testes, VAR, VECM, etc.) |
| `manual.py` | Guia de uso e interpretação |

## Abas

1. **Manual** — fluxo de trabalho, escolha de variáveis, interpretações
2. **Explorar** — cobertura, gráficos, correlações
3. **Transformar** — log-diff, diferenças, HP, z-score, spreads
4. **Estacionariedade** — ADF, KPSS, diagnóstico cruzado, ordem I(d)
5. **Regressão** — MQO com HAC, diagnósticos, VIF, backtest
6. **Cointegração** — Engle-Granger e Johansen
7. **VAR/SVAR** — seleção de lags, IRF, FEVD, Granger, estabilidade
8. **VECM** — alfa (ajuste) e beta (longo prazo)
9. **Probit/Logit** — previsão de recessão, ROC/AUC, efeitos marginais
10. **Regularização** — LASSO, Ridge, Elastic Net, stability selection

## Uso

Na barra lateral, carregue a base (.xlsx ou .csv) com uma coluna `data`.
Comece pela aba Manual se for a primeira vez.
