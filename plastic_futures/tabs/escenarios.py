"""
Tab 4 – Escenarios
Scenario comparison, Monte Carlo simulation, tornado sensitivity.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
import streamlit as st

from utils.styling import section_header, kpi_card
from utils.charts import scenario_chart, monte_carlo_chart, tornado_chart
from models.forecasting import PlasticForecastEngine
from models.scenarios import (
    build_scenario_forecasts, run_monte_carlo,
    monte_carlo_summary, sensitivity_analysis,
)
from data.demo_data import get_product_series
from config.settings import SCENARIOS


@st.cache_data(show_spinner=False, ttl=600)
def _get_scenario_data(product: str, region: str, horizon: int):
    from data.demo_data import load_demo_data
    data = load_demo_data()
    series = get_product_series(data, product, region)
    engine = PlasticForecastEngine()
    engine.fit(series)
    base_forecast = engine.predict(horizon)
    return series, base_forecast


def render(data: dict, filters: dict) -> None:
    product  = filters["product"]
    region   = filters["region"]
    horizon  = filters["horizon"]
    scenario = filters["scenario"]

    with st.spinner("Generando escenarios..."):
        series, base_forecast = _get_scenario_data(product, region, horizon)

    current_price = float(series.iloc[-1])
    sc_dfs = build_scenario_forecasts(base_forecast, current_price)

    # -----------------------------------------------------------------------
    # Scenario KPIs
    # -----------------------------------------------------------------------
    section_header(f"Análisis de Escenarios · {product} · {region}")

    cols = st.columns(len(SCENARIOS))
    icons = {"Base": "🔵", "Alcista (Bull)": "🟢", "Bajista (Bear)": "🔴",
             "Crisis energética": "🟣", "Demanda débil": "🟠"}
    for col_ui, sc_name in zip(cols, SCENARIOS):
        df = sc_dfs.get(sc_name)
        if df is None:
            continue
        end_price = df["price"].iloc[-1]
        pct_change = (end_price - current_price) / current_price * 100
        d_dir = "neg" if pct_change > 3 else ("pos" if pct_change < -3 else "neu")
        with col_ui:
            kpi_card(
                f"{icons.get(sc_name, '')} {sc_name}",
                f"{end_price:,.0f} €/t",
                delta=f"{pct_change:+.1f}% en {horizon}M",
                delta_dir=d_dir,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Scenario fan chart
    # -----------------------------------------------------------------------
    col_chart, col_sel = st.columns([4, 1])
    with col_sel:
        section_header("Escenarios")
        selected_scenarios = []
        for sc_name in SCENARIOS:
            if st.checkbox(sc_name, value=True, key=f"sc_check_{sc_name}"):
                selected_scenarios.append(sc_name)

    with col_chart:
        section_header("Comparación de escenarios de precio")
        selected_dfs = {k: v for k, v in sc_dfs.items() if k in selected_scenarios}
        fig_sc = scenario_chart(series, selected_dfs)
        st.plotly_chart(fig_sc, use_container_width=True)

    # -----------------------------------------------------------------------
    # Scenario detail table
    # -----------------------------------------------------------------------
    section_header("Tabla de precios por escenario (€/ton)")
    st.caption("ℹ️ Formato americano: la coma ( , ) es separador de miles. Ejemplo: 1,206 = mil doscientos seis €/t.")

    sc_table = {}
    for sc_name, df in sc_dfs.items():
        sc_table[sc_name] = df["price"]
    sc_df_table = pd.DataFrame(sc_table)
    sc_df_table.index = sc_df_table.index.strftime("%b %Y")

    # Format as integers with thousands separator — no decimals
    sc_df_fmt = sc_df_table.applymap(lambda v: f"{int(round(v)):,}" if pd.notna(v) else "")

    def _color_sc(val: str) -> str:
        try:
            v = float(val.replace(",", ""))
            pct = (v - current_price) / current_price
            if pct > 0.05:  return "color:#C0392B; font-weight:600;"
            if pct < -0.05: return "color:#00845E; font-weight:600;"
        except Exception:
            pass
        return ""

    st.dataframe(
        sc_df_fmt.style.map(_color_sc),
        use_container_width=True, height=280,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Monte Carlo
    # -----------------------------------------------------------------------
    col_mc, col_params = st.columns([3, 1])
    with col_params:
        section_header("Parámetros MC")
        annual_drift = st.slider("Drift anual (%)", -20, 20, 2, step=1) / 100
        annual_vol   = st.slider("Volatilidad anual (%)", 5, 40, 12, step=1) / 100
        n_paths      = st.select_slider("Simulaciones", options=[200, 500, 1000, 2000], value=1000)

    with col_mc:
        section_header(f"Simulación Monte Carlo — {n_paths} caminos")
        mc_paths = run_monte_carlo(
            current_price=current_price,
            horizon=horizon,
            annual_drift=annual_drift,
            annual_vol=annual_vol,
            n_paths=n_paths,
        )
        mc_summary = monte_carlo_summary(mc_paths)
        fig_mc = monte_carlo_chart(current_price, mc_summary, series)
        st.plotly_chart(fig_mc, use_container_width=True)

    # MC stats
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    final_col = mc_paths.iloc[:, -1]
    p_up = (final_col > current_price).mean()
    with col_s1:
        kpi_card("P(precio sube)", f"{p_up:.0%}", delta_dir="neg" if p_up > 0.5 else "pos")
    with col_s2:
        kpi_card("Mediana MC", f"{final_col.median():,.0f} €/t")
    with col_s3:
        kpi_card("P5 MC", f"{final_col.quantile(0.05):,.0f} €/t")
    with col_s4:
        kpi_card("P95 MC", f"{final_col.quantile(0.95):,.0f} €/t")

    # -----------------------------------------------------------------------
    # Tornado / Sensitivity
    # -----------------------------------------------------------------------
    section_header("Análisis de sensibilidad (Tornado)")
    sens_df = sensitivity_analysis(current_price, horizon=horizon)
    fig_tornado = tornado_chart(sens_df)
    st.plotly_chart(fig_tornado, use_container_width=True)

    with st.expander("Metodología de escenarios"):
        st.markdown("""
        **Escenarios deterministas**: cada escenario aplica un ajuste paramétrico sobre el
        forecast ensemble (desplazamiento de nivel, multiplicador de tendencia y escala de
        volatilidad). Los rangos se basan en percentiles históricos del mercado europeo de
        polímeros (2010-2024).

        **Monte Carlo GBM**: se simula el precio con Movimiento Browniano Geométrico,
        permitiendo configurar el drift (expectativa anual) y la volatilidad (desviación
        anualizada). Los cuantiles de los caminos simulados forman los intervalos de confianza.

        **Tornado**: la sensibilidad de cada driver se estima como elasticidad parcial
        respecto al precio de mercado, escala ajustada por horizonte.
        """)
