"""
Tab 2 – Proyecciones
Fan chart, ensemble model breakdown, quantile table, conformal prediction.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
import streamlit as st

from utils.styling import section_header, kpi_card
from utils.charts import fan_chart, backtest_chart, feature_importance_chart
from models.forecasting import PlasticForecastEngine
from data.demo_data import get_product_series
from config.settings import SUCCESS_GREEN, DANGER_RED, WARNING_AMBER, REPSOL_BLUE


@st.cache_data(show_spinner=False, ttl=600)
def _fit_and_forecast(product: str, region: str, horizon: int, _data_hash: str):
    """Cached fitting: keyed by product, region, horizon."""
    from data.demo_data import load_demo_data
    data = load_demo_data()
    series = get_product_series(data, product, region)
    engine = PlasticForecastEngine()
    engine.fit(series)
    forecast = engine.predict(horizon)
    backtest = engine.backtest()
    weights  = engine.model_weights()
    feat_imp = engine.feature_importances()
    return series, forecast, backtest, weights, feat_imp


def render(data: dict, filters: dict) -> None:
    product  = filters["product"]
    region   = filters["region"]
    horizon  = filters["horizon"]
    chart_tp = filters["chart_type"]

    # Use a simple hash so caching works
    data_hash = f"{product}_{region}_{horizon}"

    with st.spinner("Calculando previsiones del modelo ensemble..."):
        series, forecast, backtest, weights, feat_imp = _fit_and_forecast(
            product, region, horizon, data_hash
        )

    last_price   = series.iloc[-1]
    median_col   = "q_50" if "q_50" in forecast.columns else "mean"
    price_6m     = forecast[median_col].iloc[min(5, len(forecast)-1)]
    price_end    = forecast[median_col].iloc[-1]
    price_change = (price_end - last_price) / last_price * 100
    avg_mape     = backtest["mape_ens"].mean()
    model_conf   = max(0, 100 - avg_mape * 5)

    # -----------------------------------------------------------------------
    # KPI strip
    # -----------------------------------------------------------------------
    section_header(f"Previsión de precio · {product} · {region} · {horizon} meses")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Precio actual", f"{last_price:,.0f} €/t", delta="Último dato histórico", delta_dir="neu")
    with c2:
        d = "neg" if price_change > 5 else ("pos" if price_change < -5 else "neu")
        kpi_card(f"Previsión {horizon}M (mediana)", f"{price_end:,.0f} €/t",
                 delta=f"{price_change:+.1f}% vs hoy", delta_dir=d)
    with c3:
        kpi_card("Confianza modelo", f"{model_conf:.0f}%",
                 delta=f"MAPE medio: {avg_mape:.1f}%",
                 delta_dir="pos" if model_conf > 70 else ("neu" if model_conf > 50 else "neg"))
    with c4:
        ci_width = (forecast["q_95"].iloc[-1] - forecast["q_5"].iloc[-1]) if "q_95" in forecast.columns else 0
        kpi_card("Rango de incertidumbre",
                 f"±{ci_width/2:,.0f} €/t",
                 delta=f"IC 90% en mes {horizon}",
                 delta_dir="neg" if ci_width / last_price > 0.15 else "neu")

    st.markdown("<br>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Fan chart
    # -----------------------------------------------------------------------
    col_main, col_side = st.columns([3, 1])
    with col_main:
        if chart_tp in ("Fan Chart", "Líneas", "Área"):
            fig = fan_chart(series, forecast, title=f"Previsión fan chart — {product} ({region})")
        else:
            fig = fan_chart(series, forecast, title=f"Previsión fan chart — {product} ({region})")
        st.plotly_chart(fig, use_container_width=True)

    with col_side:
        section_header("Pesos del ensemble")
        for model_name, label in [("hw", "Holt-Winters"), ("lf", "Lin. Fourier"), ("rf", "Random Forest")]:
            w = weights.get(model_name, 0)
            color = REPSOL_BLUE if model_name == "hw" else ("FF6600" if model_name == "lf" else "D4006A")
            st.metric(label=label, value=f"{w*100:.1f}%")
        st.markdown("---")
        section_header("Estadísticas")
        if "q_25" in forecast.columns:
            st.markdown(f"**P25 final:** {forecast['q_25'].iloc[-1]:,.0f} €/t")
            st.markdown(f"**P50 final:** {forecast[median_col].iloc[-1]:,.0f} €/t")
            st.markdown(f"**P75 final:** {forecast['q_75'].iloc[-1]:,.0f} €/t")
        st.markdown(f"**Desv. estándar:** {forecast['std'].iloc[-1]:,.0f} €/t")

    # -----------------------------------------------------------------------
    # Quantile table
    # -----------------------------------------------------------------------
    section_header("Tabla de cuantiles de previsión")
    q_cols = [c for c in ["q_5", "q_10", "q_25", "q_50", "q_75", "q_90", "q_95"] if c in forecast.columns]
    show_df = forecast[q_cols + ["mean", "std"]].copy()
    show_df.index = show_df.index.strftime("%b %Y")
    show_df.columns = [c.replace("q_", "P") if c.startswith("q_") else c.capitalize() for c in show_df.columns]

    def _color_cell(val):
        last = last_price
        if isinstance(val, float):
            pct = (val - last) / last
            if pct > 0.05:   return "background-color:#FEF0ED; color:#C0392B;"
            if pct < -0.05:  return "background-color:#EBF9F4; color:#00845E;"
        return ""

    st.dataframe(
        show_df.round(1).style.applymap(_color_cell),
        use_container_width=True, height=300,
    )

    # -----------------------------------------------------------------------
    # Model comparison & backtesting
    # -----------------------------------------------------------------------
    col_bt, col_fi = st.columns([3, 2])
    with col_bt:
        section_header("Backtesting walk-forward")
        fig_bt = backtest_chart(backtest)
        st.plotly_chart(fig_bt, use_container_width=True)

    with col_fi:
        section_header("Importancia de variables (Random Forest)")
        if feat_imp:
            fig_fi = feature_importance_chart(feat_imp)
            st.plotly_chart(fig_fi, use_container_width=True)

    # -----------------------------------------------------------------------
    # Conformal prediction note
    # -----------------------------------------------------------------------
    with st.expander("¿Cómo se calculan los intervalos de confianza? (Conformal prediction)"):
        st.markdown("""
        Los intervalos de confianza del fan chart combinan dos técnicas:

        **Bootstrap de residuos (empírico)**
        Se remuestrean los errores históricos de los tres modelos base
        (Holt-Winters, Regresión Fourier y Random Forest) y se propagan
        al futuro, aplicando una escala heterocedástica que crece con el horizonte.

        **Corrección conformal**
        Los cuantiles resultantes respetan cobertura empírica: si el modelo dice IC 80%,
        históricamente el precio cae dentro del rango en ~80% de los casos.
        Se valida mediante backtesting walk-forward con expansión de ventana.

        **Ensemble ponderado**
        Los pesos de cada modelo se calibran con su MAPE en un holdout de los últimos
        6 meses (inversamente proporcional al error).
        """)
