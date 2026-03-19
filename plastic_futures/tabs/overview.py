"""
Tab 1 – Overview
Market snapshot: KPIs, multi-product price history, risk heat-map, alerts.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

from utils.styling import kpi_card, section_header, alert_box
from utils.charts import multi_product_lines, heatmap_chart, apply_time_filter
from models.risk_scoring import build_risk_heatmap
from config.settings import (
    REPSOL_ORANGE, REPSOL_BLUE, SUCCESS_GREEN, DANGER_RED, WARNING_AMBER,
    DATA_START_YEAR, DATA_END_YEAR,
)


def render(data: dict, filters: dict) -> None:
    product       = filters["product"]
    region        = filters["region"]
    products      = filters["products"]
    from_year     = filters.get("from_year", 2022)
    granularity   = filters.get("granularity", "Mensual")
    active_months = filters.get("active_months")
    quarter_label = filters.get("quarter_label", "Todos")

    prices_df = data["prices"]
    market_df = data["market"]
    alerts_df = data["alerts"]

    # -----------------------------------------------------------------------
    # Current price stats for selected product / region (always full series for KPIs)
    # -----------------------------------------------------------------------
    subset = prices_df[(prices_df["product"] == product) & (prices_df["region"] == region)]
    market_series_full = subset.groupby("date")["market_price"].mean().sort_index()

    # Filtered view for charts
    market_series_chart = apply_time_filter(market_series_full, from_year, granularity)
    if active_months:
        market_series_chart = market_series_chart[market_series_chart.index.month.isin(active_months)]

    market_series = market_series_full   # KPIs always use full series

    latest_price = market_series.iloc[-1]
    prev_price   = market_series.iloc[-2]
    ytd_start    = market_series[market_series.index.year == market_series.index[-1].year].iloc[0]
    ytd_change   = (latest_price - ytd_start) / ytd_start * 100
    mom_change   = (latest_price - prev_price) / prev_price * 100
    rolling_vol  = market_series.rolling(6).std().iloc[-1]
    avg_price_3m = market_series.tail(3).mean()

    # Market driver current values
    latest_market = market_df.iloc[-1]

    # -----------------------------------------------------------------------
    # KPI row
    # -----------------------------------------------------------------------
    section_header(f"Snapshot de Mercado · {product} · {region}")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        delta_dir = "pos" if mom_change < 0 else ("neg" if mom_change > 0 else "neu")
        kpi_card(
            f"Precio actual {product}",
            f"{latest_price:,.0f} €/t",
            delta=f"{'▲' if mom_change > 0 else '▼'} {abs(mom_change):.1f}% vs mes ant.",
            delta_dir=delta_dir,
        )
    with c2:
        delta_dir2 = "neg" if ytd_change > 0 else "pos"
        kpi_card(
            "Variación YTD",
            f"{ytd_change:+.1f}%",
            delta=f"Desde {ytd_start:,.0f} €/t",
            delta_dir=delta_dir2,
        )
    with c3:
        kpi_card(
            "Media 3 meses",
            f"{avg_price_3m:,.0f} €/t",
            delta=f"Volatilidad 6M: ±{rolling_vol:.0f}",
            delta_dir="neu",
        )
    with c4:
        kpi_card(
            "Petróleo Brent",
            f"{latest_market['oil_usd_bbl']:.1f} $/bbl",
            delta=f"Gas EU: {latest_market['gas_eur_mwh']:.1f} €/MWh",
            delta_dir="neu",
        )
    with c5:
        kpi_card(
            "PMI Manufacturero",
            f"{latest_market['pmi_manuf']:.1f}",
            delta=f"EUR/USD: {latest_market['eur_usd']:.3f}",
            delta_dir="pos" if latest_market["pmi_manuf"] > 50 else "neg",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Historical price chart — full width with inline time filters
    # -----------------------------------------------------------------------
    section_header("Histórico de precios por producto")

    # Inline compact filter row
    _year_opts = list(range(DATA_START_YEAR, DATA_END_YEAR + 1))
    _gran_opts  = ["Mensual", "Trimestral", "Anual"]
    _qtr_opts   = ["Todos", "T1 (Ene–Mar)", "T2 (Abr–Jun)", "T3 (Jul–Sep)", "T4 (Oct–Dic)"]
    _qtr_months = {
        "T1 (Ene–Mar)": [1, 2, 3], "T2 (Abr–Jun)": [4, 5, 6],
        "T3 (Jul–Sep)": [7, 8, 9], "T4 (Oct–Dic)": [10, 11, 12],
    }

    fi1, fi2, fi3, _fpad = st.columns([1, 1.2, 1.4, 3])
    with fi1:
        ov_year = st.selectbox(
            "📅 Desde", _year_opts,
            index=_year_opts.index(from_year) if from_year in _year_opts else 0,
            key="ov_from_year",
        )
    with fi2:
        ov_gran = st.selectbox(
            "📊 Granularidad", _gran_opts,
            index=_gran_opts.index(granularity) if granularity in _gran_opts else 0,
            key="ov_granularity",
        )
    with fi3:
        ov_qtr_label = st.selectbox(
            "🗓 Trimestre", _qtr_opts,
            key="ov_quarter",
        )
    ov_active_months = _qtr_months.get(ov_qtr_label)

    fig = multi_product_lines(
        prices_df, products, region,
        title="",
        from_year=ov_year, granularity=ov_gran, active_months=ov_active_months,
    )
    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------------------------
    # Risk heatmap — below price chart, with explanation expander
    # -----------------------------------------------------------------------
    section_header("Mapa de riesgo por producto")

    with st.expander("¿Qué muestra este mapa?", expanded=False):
        st.markdown("""
        El **mapa de riesgo** muestra la volatilidad de precio de cada producto mes a mes,
        expresada como un índice de **0 a 100**:

        - 🟢 **Verde (0–33):** mercado estable, baja incertidumbre de precio.
        - 🟡 **Amarillo (34–66):** variabilidad moderada, conviene seguimiento activo.
        - 🔴 **Rojo (67–100):** alta volatilidad o tendencia alcista marcada; mayor riesgo en la decisión de compra.

        El índice combina la **variación de precio en el mes** respecto a la media móvil
        y la **volatilidad acumulada** de los últimos 3 meses.
        Úsalo para identificar de un vistazo qué productos han tenido períodos de mayor riesgo
        y si ese patrón se repite estacionalmente.
        """)

    risk_hm = build_risk_heatmap(data, region, products)
    risk_hm = risk_hm.dropna(axis=1, how="all").fillna(0)
    if not risk_hm.empty:
        fig_hm = heatmap_chart(
            risk_hm,
            title="",
            colorscale=[
                [0.00, "#1A9850"],   # verde saturado  — riesgo bajo
                [0.33, "#FEE08B"],   # amarillo claro  — transición
                [0.55, "#F46D43"],   # naranja          — riesgo moderado-alto
                [1.00, "#A50026"],   # rojo oscuro      — riesgo alto
            ],
            zmin=0, zmax=100,
        )
        st.plotly_chart(fig_hm, use_container_width=True)

    # -----------------------------------------------------------------------
    # Market drivers mini strip
    # -----------------------------------------------------------------------
    section_header("Drivers de mercado recientes")
    cols = st.columns(4)
    driver_specs = [
        ("Petróleo ($/bbl)",  "oil_usd_bbl",   70,  110),
        ("Gas EU (€/MWh)",    "gas_eur_mwh",    15,  80),
        ("EUR/USD",           "eur_usd",         0.95, 1.20),
        ("Índice de demanda", "demand_index",    90,  115),
    ]
    for col_ui, (label, col_name, lo, hi) in zip(cols, driver_specs):
        with col_ui:
            series_d = market_df.set_index("date")[col_name].tail(12)
            last_v   = series_d.iloc[-1]
            prev_v   = series_d.iloc[-2]
            delta_pct = (last_v - prev_v) / prev_v * 100
            fig_mini = go.Figure(go.Scatter(
                x=series_d.index, y=series_d.values,
                mode="lines", fill="tozeroy",
                fillcolor="rgba(255,102,0,0.12)",
                line=dict(color=REPSOL_ORANGE, width=2),
            ))
            fig_mini.update_layout(
                height=100, margin=dict(l=0, r=0, t=0, b=0),
                paper_bgcolor="white", plot_bgcolor="white",
                xaxis=dict(visible=False), yaxis=dict(visible=False),
                showlegend=False,
            )
            st.markdown(
                f"""<div style="background:white;border-radius:8px;padding:12px;
                    box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-bottom:4px;">
                    <div style="font-size:0.68rem;font-weight:700;color:#003087;
                        text-transform:uppercase;letter-spacing:0.05em;">{label}</div>
                    <div style="font-size:1.4rem;font-weight:800;color:#1A1A2E;">
                        {last_v:.2f}</div>
                    <div style="font-size:0.75rem;color:{'#00B894' if delta_pct < 0 else '#E17055'}">
                        {'▲' if delta_pct > 0 else '▼'} {abs(delta_pct):.1f}%</div>
                </div>""",
                unsafe_allow_html=True,
            )
            st.plotly_chart(fig_mini, use_container_width=True)

    # -----------------------------------------------------------------------
    # Alerts
    # -----------------------------------------------------------------------
    section_header("Eventos de mercado destacados")
    for _, row in alerts_df.sort_values("date", ascending=False).iterrows():
        level_map = {"Alto": "high", "Medio": "medium", "Bajo": "low"}
        icon_map  = {"Alto": "🔴", "Medio": "🟡", "Bajo": "🟢"}
        alert_box(
            f"{icon_map.get(row['impact'], '⚪')} <strong>{row['date'].strftime('%b %Y')}</strong> "
            f"– {row['event']} <em>({row['products']})</em>",
            level=level_map.get(row["impact"], "medium"),
        )
