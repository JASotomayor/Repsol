"""
Tab 6 – Seguimiento del modelo
Precisión histórica, tabla de proveedores, alertas de mercado.
"""

from __future__ import annotations
import streamlit as st

from utils.styling import section_header, kpi_card, alert_box
from utils.charts import backtest_chart
from models.forecasting import PlasticForecastEngine
from data.demo_data import get_product_series
from config.settings import PRODUCTS, SUCCESS_GREEN, DANGER_RED


@st.cache_data(show_spinner=False, ttl=600)
def _get_all_backtests(region: str):
    from data.demo_data import load_demo_data
    data = load_demo_data()
    rows = []
    for product in PRODUCTS:
        series = get_product_series(data, product, region)
        if len(series) < 20:
            continue
        engine = PlasticForecastEngine()
        engine.fit(series)
        bt = engine.backtest()
        w  = engine.model_weights()
        rows.append({
            "Producto":             product,
            "Error de previsión %": round(bt["mape_ens"].mean(), 2),
            "Error HW %":           round(bt["mape_hw"].mean(), 2),
            "Error RF %":           round(bt["mape_rf"].mean(), 2),
            "Desv. típica (€/t)":   round(bt["rmse_ens"].mean(), 1),
            "Fiabilidad %":         round(bt["confidence"].mean(), 1),
            "Peso tend. estacional": f"{w.get('hw', 0)*100:.0f}%",
            "Peso lineal":           f"{w.get('lf', 0)*100:.0f}%",
            "Peso predictivo":       f"{w.get('rf', 0)*100:.0f}%",
        })
    return pd.DataFrame(rows)


import pandas as pd


def render(data: dict, filters: dict) -> None:
    product = filters["product"]
    region  = filters["region"]

    section_header(f"Seguimiento del modelo · Región: {region}")

    with st.spinner("Calculando métricas de todos los productos..."):
        summary_df = _get_all_backtests(region)

    # ── KPIs globales ────────────────────────────────────────────────────────
    avg_err   = summary_df["Error de previsión %"].mean()
    best_prod = summary_df.loc[summary_df["Error de previsión %"].idxmin(), "Producto"]
    worst_prod= summary_df.loc[summary_df["Error de previsión %"].idxmax(), "Producto"]
    avg_conf  = summary_df["Fiabilidad %"].mean()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Error medio de previsión", f"{avg_err:.1f}%",
                 delta="Promedio de todos los productos",
                 delta_dir="pos" if avg_err < 4 else "neg")
    with c2:
        kpi_card("Producto más predecible", best_prod,
                 delta=f"Error: {summary_df[summary_df['Producto']==best_prod]['Error de previsión %'].iloc[0]:.1f}%",
                 delta_dir="pos")
    with c3:
        kpi_card("Producto más volátil", worst_prod,
                 delta=f"Error: {summary_df[summary_df['Producto']==worst_prod]['Error de previsión %'].iloc[0]:.1f}%",
                 delta_dir="neg")
    with c4:
        kpi_card("Fiabilidad media", f"{avg_conf:.0f}%",
                 delta_dir="pos" if avg_conf > 70 else "neu")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabla de precisión ───────────────────────────────────────────────────
    section_header("Precisión por producto")

    def _err_color(val):
        if isinstance(val, float):
            if val < 3:   return "background-color:#E9F7EF; color:#1E8449; font-weight:700;"
            if val < 7:   return "background-color:#FEFAE6; color:#9A7D0A;"
            return "background-color:#FEF0ED; color:#C0392B;"
        return ""

    def _conf_color(val):
        if isinstance(val, float):
            if val >= 80: return "color:#1E8449; font-weight:700;"
            if val >= 60: return "color:#9A7D0A;"
            return "color:#C0392B;"
        return ""

    st.dataframe(
        summary_df.style
            .map(_err_color, subset=["Error de previsión %", "Error HW %", "Error RF %"])
            .map(_conf_color, subset=["Fiabilidad %"]),
        use_container_width=True, height=260,
    )

    # ── Detalle del producto seleccionado ────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section_header(f"Validación detallada: {product}")

    from data.demo_data import load_demo_data
    _data = load_demo_data()
    series = get_product_series(_data, product, region)
    engine = PlasticForecastEngine()
    engine.fit(series)
    bt_detail = engine.backtest()

    fig_bt = backtest_chart(bt_detail, title=f"Validación histórica — {product}")
    st.plotly_chart(fig_bt, use_container_width=True)

    col_bt1, col_bt2 = st.columns(2, gap="large")
    with col_bt1:
        section_header("Resultados por período de validación")
        display_bt = bt_detail[[
            "fold", "date_start",
            "mape_ens", "mape_hw", "mape_lf", "mape_rf",
            "rmse_ens", "confidence"
        ]].copy()
        display_bt["date_start"] = display_bt["date_start"].dt.strftime("%b %Y")
        display_bt.columns = [
            "Período", "Inicio", "Error total %",
            "Error estacional %", "Error lineal %", "Error predictivo %",
            "Desv. típica", "Fiabilidad %",
        ]
        st.dataframe(
            display_bt.style.map(_err_color, subset=["Error total %"]),
            use_container_width=True,
        )

    with col_bt2:
        section_header("Pesos del modelo por producto")
        weight_rows = []
        for p in PRODUCTS:
            s = get_product_series(_data, p, region)
            if s.empty or len(s) < 20:
                continue
            eng = PlasticForecastEngine()
            eng.fit(s)
            w = eng.model_weights()
            weight_rows.append({
                "Producto": p,
                "Tendencia estacional": f"{w.get('hw',0)*100:.0f}%",
                "Modelo lineal":        f"{w.get('lf',0)*100:.0f}%",
                "Modelo predictivo":    f"{w.get('rf',0)*100:.0f}%",
            })
        if weight_rows:
            st.dataframe(pd.DataFrame(weight_rows), use_container_width=True)

    # ── Tabla de proveedores ─────────────────────────────────────────────────
    section_header("Precios actuales por proveedor")
    prices_df = data["prices"]
    last_date = prices_df["date"].max()
    sup_prices = prices_df[
        (prices_df["product"] == product) &
        (prices_df["region"]  == region) &
        (prices_df["date"]    == last_date)
    ][["supplier", "price", "volume"]].copy()
    sup_prices = sup_prices.merge(
        data["suppliers"][["supplier", "lead_time_days", "rating", "sustainability_score"]],
        on="supplier", how="left"
    ).sort_values("price")
    sup_prices.columns = [
        "Proveedor", "Precio (€/t)", "Volumen (t)",
        "Plazo entrega (días)", "Valoración", "Puntuación sostenibilidad",
    ]

    best_price  = sup_prices["Precio (€/t)"].min()
    worst_price = sup_prices["Precio (€/t)"].max()

    def _price_bar(val):
        if isinstance(val, float):
            if val == best_price:  return f"color:{SUCCESS_GREEN}; font-weight:700;"
            if val == worst_price: return f"color:{DANGER_RED};"
        return ""

    st.dataframe(
        sup_prices.style.map(_price_bar, subset=["Precio (€/t)"]),
        use_container_width=True,
    )

    # ── Alertas de vigilancia ────────────────────────────────────────────────
    section_header("Señales de alerta por producto")
    alert_found = False
    for p in PRODUCTS:
        s = get_product_series(_data, p, region)
        if s.empty:
            continue
        mom = (s.iloc[-1] - s.iloc[-4]) / s.iloc[-4] * 100
        vol = s.rolling(3).std().iloc[-1] / s.mean() * 100
        if abs(mom) > 8:
            alert_box(
                f"<strong>{p}</strong>: variación de {mom:+.1f}% en los últimos 3 meses.",
                level="high" if abs(mom) > 12 else "medium",
            )
            alert_found = True
        if vol > 6:
            alert_box(
                f"<strong>{p}</strong>: volatilidad elevada ({vol:.1f}%) en los últimos 3 meses.",
            )
            alert_found = True
    if not alert_found:
        alert_box("No hay señales de alerta activas en este momento.", level="low")
