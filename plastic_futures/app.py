"""
Plastic Futures Decision Hub
Compras & Planificación · Market Intelligence

Entry point. Run with:
    streamlit run app.py
"""

import streamlit as st

# ── Page config must be the very first Streamlit call ──────────────────────
from config.settings import PAGE_CONFIG
st.set_page_config(**PAGE_CONFIG)

# ── Imports ────────────────────────────────────────────────────────────────
from config.settings import (
    PRODUCTS, SUPPLIERS, REGIONS, HORIZONS, SCENARIOS, CHART_TYPES,
    DATA_START_YEAR, DATA_END_YEAR,
)
from data.demo_data import load_demo_data
from utils.styling import apply_custom_css, render_header, render_sidebar_brand

import tabs.overview       as tab_overview
import tabs.proyecciones   as tab_proyecciones
import tabs.riesgo         as tab_riesgo
import tabs.escenarios     as tab_escenarios
import tabs.drivers        as tab_drivers
import tabs.seguimiento    as tab_seguimiento
import tabs.chat_insights  as tab_chat


# ── CSS ─────────────────────────────────────────────────────────────────────
apply_custom_css()

# ── Data loading ─────────────────────────────────────────────────────────────
with st.spinner("Cargando datos del mercado..."):
    data = load_demo_data()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    render_sidebar_brand()

    st.markdown("### Filtros globales")

    product = st.selectbox(
        "Producto",
        PRODUCTS,
        index=0,
        help="Polímero principal de análisis",
    )

    products = st.multiselect(
        "Productos (comparativa)",
        PRODUCTS,
        default=PRODUCTS[:4],
        help="Selecciona los productos a incluir en gráficos comparativos",
    )
    if not products:
        products = [product]

    region = st.selectbox(
        "Región",
        REGIONS,
        index=0,
        help="Mercado geográfico de referencia",
    )

    horizon_label = st.select_slider(
        "Horizonte de previsión",
        options=list(HORIZONS.keys()),
        value="12 meses",
    )
    horizon = HORIZONS[horizon_label]

    scenario = st.selectbox(
        "Escenario principal",
        SCENARIOS,
        index=0,
        help="Escenario de referencia para el análisis de riesgo",
    )

    chart_type = st.selectbox(
        "Tipo de gráfico",
        CHART_TYPES,
        index=0,
    )

    # ── Período de análisis ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Período de análisis")

    available_years = list(range(DATA_START_YEAR, DATA_END_YEAR + 1))
    from_year = st.selectbox(
        "Desde año",
        available_years,
        index=0,
        help=f"Los datos históricos arrancan en {DATA_START_YEAR}",
    )

    granularity = st.radio(
        "Granularidad",
        ["Mensual", "Trimestral", "Anual"],
        horizontal=True,
        help="Agrupa los datos en la vista histórica",
    )

    # Quarter filter (only meaningful when Trimestral or Mensual)
    quarters_opts = ["Todos", "Q1 (Ene–Mar)", "Q2 (Abr–Jun)", "Q3 (Jul–Sep)", "Q4 (Oct–Dic)"]
    quarter_filter = st.selectbox(
        "Filtrar trimestre",
        quarters_opts,
        index=0,
        help="Muestra solo los meses de ese trimestre en el histórico",
    )
    quarter_months = {
        "Todos": None,
        "Q1 (Ene–Mar)": [1, 2, 3],
        "Q2 (Abr–Jun)": [4, 5, 6],
        "Q3 (Jul–Sep)": [7, 8, 9],
        "Q4 (Oct–Dic)": [10, 11, 12],
    }
    active_months = quarter_months[quarter_filter]

    st.markdown("---")

    # Quick price snapshot
    prices_df = data["prices"]
    sub = prices_df[
        (prices_df["product"] == product) &
        (prices_df["region"]  == region)
    ]
    if not sub.empty:
        latest = sub.groupby("date")["market_price"].mean().iloc[-1]
        prev   = sub.groupby("date")["market_price"].mean().iloc[-2]
        delta  = (latest - prev) / prev * 100
        arrow  = "▲" if delta > 0 else "▼"
        color  = "#E17055" if delta > 0 else "#00B894"
        st.markdown(
            f"""<div style="background:rgba(255,255,255,0.08); border-radius:8px;
                padding:12px; text-align:center;">
                <div style="font-size:0.68rem; color:#90A4AE; text-transform:uppercase;
                    letter-spacing:0.05em;">{product} · {region}</div>
                <div style="font-size:1.6rem; font-weight:800; color:white;">
                    {latest:,.0f} €/t</div>
                <div style="font-size:0.8rem; color:{color}; font-weight:600;">
                    {arrow} {abs(delta):.1f}% MoM</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.65rem; color:#C9B8F0; text-align:center;'>"
        f"Datos demo {DATA_START_YEAR}–{DATA_END_YEAR}<br>"
        "Modelos: HW + Fourier LR + Random Forest<br>"
        "v1.0 · Market Intelligence"
        "</div>",
        unsafe_allow_html=True,
    )

# ── Filters dict (shared across all tabs) ────────────────────────────────────
filters = {
    "product":        product,
    "products":       products,
    "region":         region,
    "horizon":        horizon,
    "scenario":       scenario,
    "chart_type":     chart_type,
    # Time period filters
    "from_year":      from_year,
    "granularity":    granularity,
    "active_months":  active_months,   # None = all, or list[int] for a quarter
    "quarter_label":  quarter_filter,
}

# ── Header ────────────────────────────────────────────────────────────────────
render_header()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Overview",
    "📈 Proyecciones",
    "⚠️ Riesgo de decisión",
    "🔮 Escenarios",
    "🔍 Drivers",
    "📋 Seguimiento",
    "💬 Chat / Guía del modelo",
])

with tab1:
    tab_overview.render(data, filters)

with tab2:
    tab_proyecciones.render(data, filters)

with tab3:
    tab_riesgo.render(data, filters)

with tab4:
    tab_escenarios.render(data, filters)

with tab5:
    tab_drivers.render(data, filters)

with tab6:
    tab_seguimiento.render(data, filters)

with tab7:
    tab_chat.render(data, filters)
