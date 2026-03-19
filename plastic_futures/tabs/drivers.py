"""
Tab 5 – Drivers de mercado
Correlation matrix, scatter, driver time series — each with inline filters.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

from utils.styling import section_header
from utils.charts import correlation_heatmap, apply_time_filter
from data.demo_data import get_product_series
from config.settings import (
    VIKINGS_PURPLE, VIKINGS_GOLD, VIKINGS_MID, VIKINGS_DARK,
    SUCCESS_GREEN, DANGER_RED, MID_GRAY,
    DATA_START_YEAR, DATA_END_YEAR,
)

_FONT = "'Segoe UI', 'Inter', Arial, sans-serif"
_PLOT_BG   = "#FFFFFF"
_PAPER_BG  = "#F8F6FF"
_GRID      = "#F0EBF8"

_DRIVER_COLORS = {
    "oil_usd_bbl":  VIKINGS_DARK,
    "gas_eur_mwh":  VIKINGS_MID,
    "pmi_manuf":    VIKINGS_PURPLE,
    "demand_index": VIKINGS_GOLD,
}
_DRIVER_LABELS = {
    "oil_usd_bbl":  "Petróleo Brent ($/bbl)",
    "gas_eur_mwh":  "Gas EU (€/MWh)",
    "pmi_manuf":    "PMI Manufacturero",
    "demand_index": "Índice de demanda",
}
_QUARTER_MONTHS = {
    "T1 (Ene–Mar)": [1, 2, 3], "T2 (Abr–Jun)": [4, 5, 6],
    "T3 (Jul–Sep)": [7, 8, 9], "T4 (Oct–Dic)": [10, 11, 12],
}
_YEAR_OPTS = list(range(DATA_START_YEAR, DATA_END_YEAR + 1))
_GRAN_OPTS = ["Mensual", "Trimestral", "Anual"]
_QTR_OPTS  = ["Todos"] + list(_QUARTER_MONTHS.keys())


def _inline_time_filters(key_prefix: str, default_year: int = DATA_START_YEAR):
    """Render compact inline time filter row; returns (from_year, granularity, active_months)."""
    c1, c2, c3, _pad = st.columns([1, 1.2, 1.4, 3])
    with c1:
        yr = st.selectbox("📅 Desde", _YEAR_OPTS,
                          index=_YEAR_OPTS.index(default_year),
                          key=f"{key_prefix}_year")
    with c2:
        gr = st.selectbox("📊 Agrupación", _GRAN_OPTS, key=f"{key_prefix}_gran")
    with c3:
        qt = st.selectbox("🗓 Trimestre", _QTR_OPTS, key=f"{key_prefix}_qtr")
    return yr, gr, _QUARTER_MONTHS.get(qt)


def render(data: dict, filters: dict) -> None:
    product  = filters["product"]
    region   = filters["region"]
    products = filters["products"]

    market_df    = data["market"]
    price_series = get_product_series(data, product, region)

    # Combined DataFrame (full history — filtered per section below)
    combined_full = market_df.set_index("date")[
        ["oil_usd_bbl", "eur_usd", "pmi_manuf", "demand_index", "gas_eur_mwh"]
    ].copy()
    combined_full["price"] = price_series
    for p in products:
        s = get_product_series(data, p, region)
        if not s.empty:
            combined_full[f"px_{p}"] = s
    combined_full.dropna(inplace=True)

    friendly = {
        "oil_usd_bbl":  "Petróleo ($/bbl)",
        "eur_usd":      "EUR/USD",
        "pmi_manuf":    "PMI Manuf.",
        "demand_index": "Demanda",
        "gas_eur_mwh":  "Gas EU (€/MWh)",
        "price":        f"Precio {product}",
    }
    for p in products:
        friendly[f"px_{p}"] = f"Precio {p}"

    section_header(f"Factores de Mercado · {product} · {region}")

    # -----------------------------------------------------------------------
    # 1. Correlation heatmap — full width, own time filter
    # -----------------------------------------------------------------------
    section_header("Correlaciones entre variables")
    corr_year, corr_gran, corr_months = _inline_time_filters("corr", DATA_START_YEAR)

    combined = combined_full[combined_full.index.year >= corr_year].copy()
    if corr_gran == "Trimestral":
        combined = combined.resample("QS").mean().dropna()
    elif corr_gran == "Anual":
        combined = combined.resample("YS").mean().dropna()
    if corr_months:
        combined = combined[combined.index.month.isin(corr_months)]

    if len(combined) >= 4:
        corr = combined.corr()
        corr.rename(index=friendly, columns=friendly, inplace=True)
        fig_corr = correlation_heatmap(corr)
        st.plotly_chart(fig_corr, use_container_width=True)
    else:
        st.info("No hay suficientes datos para calcular correlaciones con los filtros seleccionados.")

    # -----------------------------------------------------------------------
    # 2. Scatter precio vs driver — full width, own driver selector + time filter
    # -----------------------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("Dispersión precio vs factor de mercado")

    sc1, sc2, sc3, sc4, _scpad = st.columns([1.4, 1, 1.2, 1.4, 2])
    with sc1:
        driver_sel = st.selectbox(
            "Factor", ["oil_usd_bbl", "gas_eur_mwh", "eur_usd", "pmi_manuf", "demand_index"],
            format_func=lambda x: friendly.get(x, x), key="sc_driver",
        )
    with sc2:
        sc_year = st.selectbox("📅 Desde", _YEAR_OPTS,
                               index=_YEAR_OPTS.index(DATA_START_YEAR), key="sc_year")
    with sc3:
        sc_gran = st.selectbox("📊 Agrupación", _GRAN_OPTS, key="sc_gran")
    with sc4:
        sc_qtr = st.selectbox("🗓 Trimestre", _QTR_OPTS, key="sc_qtr")
    sc_months = _QUARTER_MONTHS.get(sc_qtr)

    sc_data = combined_full[combined_full.index.year >= sc_year].copy()
    if sc_gran == "Trimestral":
        sc_data = sc_data.resample("QS").mean().dropna()
    elif sc_gran == "Anual":
        sc_data = sc_data.resample("YS").mean().dropna()
    if sc_months:
        sc_data = sc_data[sc_data.index.month.isin(sc_months)]

    if len(sc_data) >= 4 and driver_sel in sc_data.columns:
        fig_sc = go.Figure()
        fig_sc.add_trace(go.Scatter(
            x=sc_data[driver_sel], y=sc_data["price"],
            mode="markers",
            marker=dict(
                color=sc_data.index.year,
                colorscale=[[0, VIKINGS_DARK], [0.5, VIKINGS_MID], [1, VIKINGS_GOLD]],
                size=8, opacity=0.78,
                showscale=True,
                colorbar=dict(
                    title=dict(text="Año", font=dict(size=11)),
                    thickness=12, tickfont=dict(size=10), outlinewidth=0,
                ),
            ),
            hovertemplate=(
                f"<b>%{{x:.2f}}</b> {friendly.get(driver_sel, '')}<br>"
                f"Precio {product}: <b>%{{y:,.0f}} €/t</b><extra></extra>"
            ),
        ))
        z = np.polyfit(sc_data[driver_sel], sc_data["price"], 1)
        x_range = np.linspace(sc_data[driver_sel].min(), sc_data[driver_sel].max(), 60)
        fig_sc.add_trace(go.Scatter(
            x=x_range, y=np.polyval(z, x_range),
            mode="lines", name="Tendencia lineal",
            line=dict(color=VIKINGS_GOLD, width=2.2, dash="dash"),
            hoverinfo="skip",
        ))
        fig_sc.update_layout(
            paper_bgcolor=_PAPER_BG, plot_bgcolor=_PLOT_BG, height=420,
            margin=dict(l=60, r=30, t=30, b=60),
            xaxis=dict(
                title=dict(text=friendly.get(driver_sel, driver_sel),
                           font=dict(size=12, color=VIKINGS_DARK)),
                gridcolor=_GRID, linecolor="#D5CCE8",
                tickfont=dict(size=11),
            ),
            yaxis=dict(
                title=dict(text=f"Precio {product} (€/t)",
                           font=dict(size=12, color=VIKINGS_DARK)),
                gridcolor=_GRID, linecolor="#D5CCE8",
                tickfont=dict(size=11),
            ),
            showlegend=False,
            font=dict(family=_FONT, size=11, color=VIKINGS_DARK),
        )
        st.plotly_chart(fig_sc, use_container_width=True)
    else:
        st.info("No hay datos suficientes con los filtros seleccionados.")

    # -----------------------------------------------------------------------
    # 3. Driver time series — 2-column grid, shared inline filter
    # -----------------------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("Evolución temporal de factores clave")
    ts_year, ts_gran, ts_months = _inline_time_filters("ts", DATA_START_YEAR)

    cols_d = st.columns(2)
    for i, (drv, label) in enumerate(_DRIVER_LABELS.items()):
        with cols_d[i % 2]:
            series_d = market_df.set_index("date")[drv]
            series_d = apply_time_filter(series_d, ts_year, ts_gran)
            if ts_months:
                series_d = series_d[series_d.index.month.isin(ts_months)]
            color = _DRIVER_COLORS[drv]
            mode_d = "lines+markers" if ts_gran == "Anual" else "lines"
            fig_d = go.Figure()
            fig_d.add_trace(go.Scatter(
                x=series_d.index, y=series_d.values,
                mode=mode_d, fill="tozeroy",
                fillcolor=_hex_to_rgba(color, 0.10),
                line=dict(color=color, width=2.2),
                marker=dict(size=5, color=color),
                hovertemplate=f"<b>%{{x|%b %Y}}</b><br>{label}: <b>%{{y:.2f}}</b><extra></extra>",
            ))
            if drv == "pmi_manuf":
                fig_d.add_hline(y=50, line_dash="dot", line_color=MID_GRAY, line_width=1.2,
                                annotation_text="50 = neutral",
                                annotation_font=dict(size=10, color=MID_GRAY))
            fig_d.update_layout(
                title=dict(text=label, font=dict(size=12, color=VIKINGS_DARK, family=_FONT)),
                height=230, paper_bgcolor=_PAPER_BG, plot_bgcolor=_PLOT_BG,
                margin=dict(l=46, r=14, t=40, b=32),
                xaxis=dict(gridcolor=_GRID, linecolor="#D5CCE8", tickfont=dict(size=9)),
                yaxis=dict(gridcolor=_GRID, linecolor="#D5CCE8", tickfont=dict(size=9)),
                showlegend=False,
                font=dict(family=_FONT, size=10, color=VIKINGS_DARK),
            )
            st.plotly_chart(fig_d, use_container_width=True)

    # -----------------------------------------------------------------------
    # 4. Cross-product price correlation
    # -----------------------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("Correlaciones cruzadas de precios entre productos")
    cross_cols = [c for c in combined_full.columns if c.startswith("px_") or c == "price"]
    if len(cross_cols) >= 2:
        cross_corr = combined_full[cross_cols].corr()
        cross_corr.index   = [c.replace("px_", "").replace("price", product) for c in cross_corr.index]
        cross_corr.columns = cross_corr.index.tolist()
        fig_cc = correlation_heatmap(cross_corr, title="")
        st.plotly_chart(fig_cc, use_container_width=True)


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"
