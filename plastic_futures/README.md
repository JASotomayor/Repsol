# Plastic Futures Decision Hub

Market intelligence & procurement decision support for Repsol Compras & Planificación.

## Quick start

```bash
cd plastic_futures
pip install -r requirements.txt
streamlit run app.py
```

## Optional: LLM insights

Set your Anthropic API key to enable the Chat/Insights tab with real AI responses:

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # Linux/Mac
set ANTHROPIC_API_KEY=sk-ant-...      # Windows
streamlit run app.py
```

Without the key the tab shows structured, rule-based insights derived from the model outputs.

## Project structure

```
plastic_futures/
├── app.py                    # Entry point
├── requirements.txt
├── .streamlit/config.toml    # Repsol theme
├── config/settings.py        # Brand colours, domain constants
├── data/demo_data.py         # Synthetic 36-month plastic market data
├── models/
│   ├── forecasting.py        # Ensemble: Holt-Winters + Fourier LR + Random Forest
│   ├── risk_scoring.py       # Composite risk score + buy-now-vs-wait
│   └── scenarios.py          # Scenario forecasts + Monte Carlo GBM
├── tabs/
│   ├── overview.py           # KPIs, price history, risk heatmap, alerts
│   ├── proyecciones.py       # Fan chart, quantile table, backtesting
│   ├── riesgo.py             # Risk gauge, radar, buy/wait analysis
│   ├── escenarios.py         # Scenario comparison, MC simulation, tornado
│   ├── drivers.py            # Correlations, scatter, driver time series
│   ├── seguimiento.py        # Model accuracy, supplier prices, alerts
│   └── chat_insights.py      # LLM chat + quick-insight buttons
└── utils/
    ├── styling.py            # CSS injection, branded components
    └── charts.py             # Plotly chart factory (fan, heatmap, gauge…)
```

## Modelling approach

| Layer | Method | Purpose |
|---|---|---|
| Holt-Winters | Exponential Smoothing (additive trend + seasonal) | Level, trend, seasonality |
| Fourier LR | Linear regression with sin/cos features | Parsimonious seasonal baseline |
| Random Forest | 200 trees, lag 1/2/3/6/12M + Fourier features | Non-linear patterns |
| Ensemble | Inverse-MAPE weighted average | Combines strengths of each model |
| Uncertainty | Bootstrap residuals (heteroscedastic) | Prediction intervals |
| Conformal | Calibration-set residual quantiles | Coverage-guaranteed intervals |
| Backtesting | Walk-forward validation (6 folds) | Real-world accuracy estimation |
| Monte Carlo | GBM with configurable drift & vol | Stochastic scenario simulation |

## Risk score

```
Composite risk (0-100) =
  30% × Volatility (6M coefficient of variation)
+ 25% × Trend momentum (3M price change direction)
+ 25% × Uncertainty (90% CI width / price)
+ 20% × Model risk (100 - confidence score)
```

## Suggested improvements (roadmap)

- **Conformal prediction** with formal coverage guarantees (EnbPI)
- **SHAP values** for model explainability per forecast
- **Automated alerts** via email/Teams when risk crosses thresholds
- **Live data connectors** (ICIS, Platts, Bloomberg API)
- **Portfolio view**: aggregate risk across multiple plastics/suppliers
- **Contract optimisation**: optimal split between spot/forward given risk budget
