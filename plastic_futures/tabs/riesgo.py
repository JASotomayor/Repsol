"""
Tab 3 – Riesgo de decisión
Risk gauge, radar, buy-now vs wait analysis, volatility table.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
import streamlit as st

from utils.styling import section_header, kpi_card, risk_badge, alert_box
from utils.charts import risk_gauge, risk_radar, buy_vs_wait_chart, heatmap_chart
from models.risk_scoring import compute_risk_score, buy_now_vs_wait
from models.forecasting import PlasticForecastEngine
from data.demo_data import get_product_series, get_product_volume
from config.settings import DEFAULT_VOLUME_TONS, CARRYING_COST_PER_TON_MONTH


@st.cache_data(show_spinner=False, ttl=600)
def _get_risk_data(product: str, region: str, horizon: int):
    from data.demo_data import load_demo_data
    data = load_demo_data()
    series = get_product_series(data, product, region)
    engine = PlasticForecastEngine()
    engine.fit(series)
    forecast  = engine.predict(horizon)
    backtest  = engine.backtest()
    return series, forecast, backtest


def render(data: dict, filters: dict) -> None:
    product = filters["product"]
    region  = filters["region"]
    horizon = filters["horizon"]

    with st.spinner("Calculando riesgo de decisión..."):
        series, forecast, backtest = _get_risk_data(product, region, horizon)

    risk = compute_risk_score(series, forecast, backtest)
    current_price = float(series.iloc[-1])

    # -----------------------------------------------------------------------
    # Header KPIs
    # -----------------------------------------------------------------------
    section_header(f"Riesgo de Decisión de Compra · {product} · {region}")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Score de riesgo compuesto", f"{risk['composite']:.0f} / 100",
                 delta=f"Nivel: {risk['level']}", delta_dir="neg" if risk["level"] == "Alto" else ("neu" if risk["level"] == "Medio" else "pos"))
    with c2:
        kpi_card("Riesgo de volatilidad", f"{risk['volatility']:.0f} / 100",
                 delta="Variabilidad 6M", delta_dir="neg" if risk["volatility"] > 60 else "pos")
    with c3:
        kpi_card("Riesgo de tendencia", f"{risk['trend']:.0f} / 100",
                 delta="Momentum 3M (↑ malo para comprador)", delta_dir="neg" if risk["trend"] > 60 else "pos")
    with c4:
        kpi_card("Confianza del modelo", f"{risk['model_confidence']:.0f}%",
                 delta="MAPE backtest", delta_dir="pos" if risk["model_confidence"] > 70 else "neg")

    st.markdown("<br>", unsafe_allow_html=True)
    col_g, col_r, col_info = st.columns([2, 2, 3])

    with col_g:
        section_header("Gauge de riesgo")
        fig_gauge = risk_gauge(risk["composite"])
        st.plotly_chart(fig_gauge, use_container_width=True)
        risk_badge(risk["level"])

    with col_r:
        section_header("Descomposición del riesgo")
        fig_radar = risk_radar(risk)
        st.plotly_chart(fig_radar, use_container_width=True)

    with col_info:
        section_header("Interpretación del riesgo")
        comp = risk["composite"]
        trend_v = risk["trend"]
        vol_v   = risk["volatility"]

        if comp >= 67:
            alert_box(
                "RIESGO ALTO: Alta incertidumbre en el precio. "
                "Considera comprar en tramos, usar contratos de precio fijo o esperar señales de estabilización.",
                level="high",
            )
        elif comp >= 34:
            alert_box(
                "RIESGO MEDIO: El mercado muestra volatilidad moderada. "
                "Vigila los indicadores de demanda y el precio del petróleo antes de comprometerte con grandes volúmenes.",
                level="medium",
            )
        else:
            alert_box(
                "RIESGO BAJO: Condiciones favorables para compra. "
                "Precio estable y tendencia favorable. Considera adelantar volumen si tienes capacidad de almacenamiento.",
                level="low",
            )

        st.markdown("---")
        st.markdown(f"""
        | Factor | Score | Peso |
        |---|---|---|
        | Volatilidad 6M | {risk['volatility']:.0f}/100 | 30% |
        | Momentum tendencia | {risk['trend']:.0f}/100 | 25% |
        | Amplitud IC forecast | {risk['uncertainty']:.0f}/100 | 25% |
        | Riesgo modelo | {100-risk['model_confidence']:.0f}/100 | 20% |
        | **Composite** | **{risk['composite']:.0f}/100** | — |
        """)

    # -----------------------------------------------------------------------
    # Buy now vs wait
    # -----------------------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("Análisis Comprar Ahora vs Esperar")

    col_params, col_chart = st.columns([1, 3])
    with col_params:
        volume = st.number_input(
            "Volumen a comprar (toneladas)", min_value=50, max_value=5000,
            value=DEFAULT_VOLUME_TONS, step=50,
        )
        carry = st.number_input(
            "Coste de almacenamiento (€/t/mes)", min_value=0.0, max_value=50.0,
            value=float(CARRYING_COST_PER_TON_MONTH), step=0.5,
        )
        st.markdown("---")
        cost_now = current_price * volume
        st.markdown(f"**Coste si compras hoy:**")
        st.markdown(f"### {cost_now:,.0f} €")

    buy_wait_df = buy_now_vs_wait(current_price, forecast, volume_tons=volume, carrying_cost=carry)

    with col_chart:
        fig_bw = buy_vs_wait_chart(buy_wait_df)
        st.plotly_chart(fig_bw, use_container_width=True)

    # -----------------------------------------------------------------------
    # Decision table
    # -----------------------------------------------------------------------
    section_header("Tabla de decisión mensual")
    display_df = buy_wait_df[["expected_price", "cost_if_buy_now", "cost_if_wait",
                               "expected_savings", "p_price_rises", "decision"]].copy()
    display_df.index = display_df.index.strftime("%b %Y")
    display_df.columns = ["Precio esperado (€/t)", "Coste comprar hoy (€)",
                           "Coste si espera (€)", "Ahorro esperado (€)",
                           "P(precio sube)", "Decisión sugerida"]
    display_df["P(precio sube)"] = display_df["P(precio sube)"].apply(lambda x: f"{x:.0%}")

    def _decision_color(val):
        if val == "Esperar":
            return "background-color:#EBF9F4; color:#00845E; font-weight:700;"
        elif val == "Comprar ahora":
            return "background-color:#FEF0ED; color:#C0392B; font-weight:700;"
        return ""

    def _savings_color(val):
        try:
            v = float(val)
            if v > 0:   return "color:#00845E; font-weight:600;"
            if v < 0:   return "color:#C0392B; font-weight:600;"
        except Exception:
            pass
        return ""

    st.dataframe(
        display_df.style
        .applymap(_decision_color, subset=["Decisión sugerida"])
        .applymap(_savings_color,  subset=["Ahorro esperado (€)"]),
        use_container_width=True,
        height=280,
    )
