"""
Plastic Futures Decision Hub
Compras & Planificación · Market Intelligence

Run with:
    streamlit run app.py
"""

import streamlit as st

# Page config must be the very first Streamlit call
from config.settings import PAGE_CONFIG
st.set_page_config(**PAGE_CONFIG)

from config.settings import (
    PRODUCTS, REGIONS, HORIZONS, SCENARIOS, CHART_TYPES,
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

# ── Apply theme ──────────────────────────────────────────────────────────────
apply_custom_css()

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Cargando datos de mercado..."):
    data = load_demo_data()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    render_sidebar_brand()

    # ── Selección de producto ────────────────────────────────────────────────
    st.markdown("##### Producto y mercado")

    product = st.selectbox(
        "Producto principal",
        PRODUCTS,
        index=0,
        help="Polímero sobre el que se centrará el análisis de previsión y riesgo.",
    )

    region = st.selectbox(
        "Región de referencia",
        REGIONS,
        index=0,
        help="Mercado geográfico para los precios y previsiones.",
    )

    # ── Precio actual — justo debajo de producto + región ───────────────────
    prices_df = data["prices"]
    sub = prices_df[(prices_df["product"] == product) & (prices_df["region"] == region)]
    if not sub.empty:
        s = sub.groupby("date")["market_price"].mean()
        latest = s.iloc[-1]
        delta  = (s.iloc[-1] - s.iloc[-2]) / s.iloc[-2] * 100
        arrow  = "▲" if delta > 0 else "▼"
        d_color = "#E17055" if delta > 0 else "#00B894"
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.08); border:1px solid rgba(255,198,47,0.35);
            border-radius:10px; padding:14px 16px; text-align:center; margin-top:6px;">
            <div style="font-size:0.63rem; font-weight:700; color:#FFC62F;
                text-transform:uppercase; letter-spacing:0.08em; margin-bottom:4px;">
                {product} · {region}</div>
            <div style="font-size:1.65rem; font-weight:800; color:white; letter-spacing:-0.5px; margin:2px 0;">
                {latest:,.0f} <span style="font-size:0.9rem; font-weight:500; opacity:0.75;">€/t</span></div>
            <div style="font-size:0.76rem; font-weight:600; color:{d_color}; margin-top:3px;">
                {arrow} {abs(delta):.1f}% vs mes anterior</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    products = st.multiselect(
        "Productos en comparativa",
        PRODUCTS,
        default=PRODUCTS[:4],
        help="Productos que aparecerán en los gráficos comparativos.",
    )
    if not products:
        products = [product]

    st.divider()

    # ── Horizonte y escenario ────────────────────────────────────────────────
    st.markdown("##### Previsión")

    horizon_label = st.select_slider(
        "Horizonte de previsión",
        options=list(HORIZONS.keys()),
        value="12 meses",
        help="¿Cuántos meses hacia adelante quieres proyectar?",
    )
    horizon = HORIZONS[horizon_label]

    scenario = st.selectbox(
        "Escenario de referencia",
        SCENARIOS,
        index=0,
        help="Contexto de mercado asumido para el análisis de escenarios.",
    )

    chart_type = st.selectbox(
        "Tipo de gráfico",
        CHART_TYPES,
        index=0,
    )

    st.divider()

    st.markdown(f"""
    <div style="font-size:0.60rem; color:rgba(255,255,255,0.38); text-align:center; line-height:1.7;">
        Datos demo {DATA_START_YEAR}–{DATA_END_YEAR}<br>
        Tendencia estacional · Lineal · Predictivo avanzado
    </div>
    """, unsafe_allow_html=True)


# ── Filters dict ─────────────────────────────────────────────────────────────
filters = {
    "product":       product,
    "products":      products,
    "region":        region,
    "horizon":       horizon,
    "scenario":      scenario,
    "chart_type":    chart_type,
    # Time filters now live inline in each chart; defaults provided for fallback
    "from_year":     DATA_START_YEAR,
    "granularity":   "Mensual",
    "active_months": None,
    "quarter_label": "Todos",
}

# ── Header ────────────────────────────────────────────────────────────────────
render_header()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Visión general",
    "Proyecciones",
    "Riesgo de decisión",
    "Escenarios",
    "Factores de mercado",
    "Seguimiento",
    "Análisis e insights",
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
