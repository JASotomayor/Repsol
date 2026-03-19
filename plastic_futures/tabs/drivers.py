"""
Tab 5 – Drivers de mercado
Correlation matrix, feature importance, driver time series, scatter plots.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from utils.styling import section_header, time_filter_info
from utils.charts import correlation_heatmap, feature_importance_chart, apply_time_filter
from data.demo_data import get_product_series
from config.settings import REPSOL_ORANGE, REPSOL_BLUE, REPSOL_MAGENTA, DARK_NAVY, IVORY


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

    price_series = get_product_series(data, product, region)

    # -----------------------------------------------------------------------
    # Build combined DataFrame for correlation
    # -----------------------------------------------------------------------
    combined = market_df.set_index("date")[
        ["oil_usd_bbl", "eur_usd", "pmi_manuf", "demand_index", "gas_eur_mwh"]
    ].copy()
    combined["price"] = price_series

    # Add all product prices for cross-product correlation
    for p in products:
        s = get_product_series(data, p, region)
        if not s.empty:
            combined[f"px_{p}"] = s

    combined.dropna(inplace=True)

    section_header(f"Drivers de Mercado · {product} · {region}")

    # -----------------------------------------------------------------------
    # 1. Correlation heatmap
    # -----------------------------------------------------------------------
    col_corr, col_scatter = st.columns([2, 1])
    with col_corr:
        section_header("Correlaciones entre variables")
        corr = combined.corr()
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
        corr.rename(index=friendly, columns=friendly, inplace=True)
        fig_corr = correlation_heatmap(corr)
        st.plotly_chart(fig_corr, use_container_width=True)

    with col_scatter:
        section_header("Dispersión precio vs driver")
        driver_sel = st.selectbox(
            "Selecciona driver", ["oil_usd_bbl", "gas_eur_mwh", "eur_usd", "pmi_manuf", "demand_index"],
            format_func=lambda x: friendly.get(x, x),
        )
        fig_sc = go.Figure()
        fig_sc.add_trace(go.Scatter(
            x=combined[driver_sel], y=combined["price"],
            mode="markers",
            marker=dict(
                color=combined.index.month,
                colorscale=[[0, REPSOL_BLUE], [0.5, REPSOL_ORANGE], [1, REPSOL_MAGENTA]],
                size=7, opacity=0.75,
                showscale=True,
                colorbar=dict(title="Mes", thickness=10),
            ),
            hovertemplate=(f"{friendly.get(driver_sel, driver_sel)}: %{{x:.2f}}<br>"
                           f"Precio {product}: %{{y:,.0f}} €/t<extra></extra>"),
        ))
        # Trend line
        z = np.polyfit(combined[driver_sel], combined["price"], 1)
        x_range = np.linspace(combined[driver_sel].min(), combined[driver_sel].max(), 50)
        fig_sc.add_trace(go.Scatter(
            x=x_range, y=np.polyval(z, x_range),
            mode="lines", name="Tendencia",
            line=dict(color=REPSOL_ORANGE, width=2, dash="dash"),
        ))
        fig_sc.update_layout(
            paper_bgcolor=IVORY, plot_bgcolor="white", height=330,
            margin=dict(l=40, r=20, t=30, b=40),
            xaxis_title=friendly.get(driver_sel, driver_sel),
            yaxis_title=f"Precio {product} (€/t)",
            showlegend=False,
            font=dict(family="Inter, sans-serif", size=11, color=DARK_NAVY),
            xaxis=dict(gridcolor="#E8E8E0"), yaxis=dict(gridcolor="#E8E8E0"),
        )
        st.plotly_chart(fig_sc, use_container_width=True)

    # -----------------------------------------------------------------------
    # 2. Driver time series panel
    # -----------------------------------------------------------------------
    section_header("Evolución temporal de drivers clave")
    time_filter_info(from_year, granularity, quarter_label if quarter_label != "Todos" else "")

    driver_list = ["oil_usd_bbl", "gas_eur_mwh", "pmi_manuf", "demand_index"]
    driver_labels = {
        "oil_usd_bbl":  "Petróleo Brent ($/bbl)",
        "gas_eur_mwh":  "Gas EU (€/MWh)",
        "pmi_manuf":    "PMI Manufacturero",
        "demand_index": "Índice de demanda",
    }
    driver_colors = {
        "oil_usd_bbl":  DARK_NAVY,
        "gas_eur_mwh":  REPSOL_MAGENTA,
        "pmi_manuf":    REPSOL_BLUE,
        "demand_index": REPSOL_ORANGE,
    }

    cols_d = st.columns(2)
    for i, (drv, label) in enumerate(driver_labels.items()):
        with cols_d[i % 2]:
            series_d = market_df.set_index("date")[drv]
            # Apply time filter
            series_d = apply_time_filter(series_d, from_year, granularity)
            if active_months:
                series_d = series_d[series_d.index.month.isin(active_months)]
            mode_d = "lines+markers" if granularity == "Anual" else "lines"
            fig_d = go.Figure()
            fig_d.add_trace(go.Scatter(
                x=series_d.index, y=series_d.values,
                mode=mode_d, fill="tozeroy",
                fillcolor=_hex_to_rgba(driver_colors[drv], 0.12),
                line=dict(color=driver_colors[drv], width=2),
                marker=dict(size=5),
                name=label,
            ))
            # Add a reference line for threshold if PMI
            if drv == "pmi_manuf":
                fig_d.add_hline(y=50, line_dash="dot", line_color="#888", line_width=1.2,
                                annotation_text="50 = neutral")
            fig_d.update_layout(
                title=dict(text=label, font=dict(size=12, color=DARK_NAVY)),
                height=220, margin=dict(l=30, r=10, t=35, b=30),
                paper_bgcolor=IVORY, plot_bgcolor="white",
                xaxis=dict(gridcolor="#E8E8E0"),
                yaxis=dict(gridcolor="#E8E8E0"),
                showlegend=False,
                font=dict(family="Inter, sans-serif", size=10, color=DARK_NAVY),
            )
            st.plotly_chart(fig_d, use_container_width=True)

    # -----------------------------------------------------------------------
    # 3. Cross-product price correlation table
    # -----------------------------------------------------------------------
    section_header("Correlaciones cruzadas de precios entre productos")
    cross_corr_cols = [c for c in combined.columns if c.startswith("px_") or c == "price"]
    cross_corr = combined[cross_corr_cols].corr()
    cross_corr.index   = [c.replace("px_", "").replace("price", product) for c in cross_corr.index]
    cross_corr.columns = cross_corr.index.tolist()

    fig_cc = correlation_heatmap(cross_corr, title="")
    st.plotly_chart(fig_cc, use_container_width=True)


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convert #RRGGBB to rgba(R,G,B,alpha) string."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"
