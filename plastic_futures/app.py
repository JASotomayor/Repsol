"""
Plastic Futures Decision Hub
Compras & Planificación · Repsol

Entry point. Run with:
    streamlit run app.py
"""

import streamlit as st

# ── Page config must be the very first Streamlit call ──────────────────────
from config.settings import PAGE_CONFIG
st.set_page_config(**PAGE_CONFIG)

# ── Imports ────────────────────────────────────────────────────────────────
from config.settings import PRODUCTS, SUPPLIERS, REGIONS, HORIZONS, SCENARIOS, CHART_TYPES
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
        "<div style='font-size:0.65rem; color:#546E7A; text-align:center;'>"
        "Datos demo 2022-2024 · Modelos: HW + LF + RF<br>"
        "v1.0 · Repsol Compras & Planificación"
        "</div>",
        unsafe_allow_html=True,
    )

# ── Filters dict (shared across all tabs) ────────────────────────────────────
filters = {
    "product":    product,
    "products":   products,
    "region":     region,
    "horizon":    horizon,
    "scenario":   scenario,
    "chart_type": chart_type,
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
    "💬 Chat / Insights",
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
