"""
Tab 6 – Seguimiento del modelo
Backtest accuracy, model confidence scores, supplier price table, alerts.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

from utils.styling import section_header, kpi_card, alert_box
from utils.charts import backtest_chart
from models.forecasting import PlasticForecastEngine
from data.demo_data import get_product_series
from config.settings import PRODUCTS, REPSOL_ORANGE, REPSOL_BLUE, SUCCESS_GREEN, DANGER_RED, WARNING_AMBER, IVORY


@st.cache_data(show_spinner=False, ttl=600)
def _get_all_backtests(region: str):
    """Backtest all products and return summary table."""
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
            "Producto":         product,
            "MAPE Ensemble %":  round(bt["mape_ens"].mean(), 2),
            "MAPE HW %":        round(bt["mape_hw"].mean(), 2),
            "MAPE RF %":        round(bt["mape_rf"].mean(), 2),
            "RMSE (€/t)":       round(bt["rmse_ens"].mean(), 1),
            "Confianza %":      round(bt["confidence"].mean(), 1),
            "Peso HW":          f"{w.get('hw', 0)*100:.0f}%",
            "Peso LF":          f"{w.get('lf', 0)*100:.0f}%",
            "Peso RF":          f"{w.get('rf', 0)*100:.0f}%",
        })
    return pd.DataFrame(rows), {p: None for p in PRODUCTS}


def render(data: dict, filters: dict) -> None:
    product = filters["product"]
    region  = filters["region"]

    section_header(f"Seguimiento del Modelo · Región: {region}")

    with st.spinner("Calculando métricas de todos los productos..."):
        summary_df, _ = _get_all_backtests(region)

    # -----------------------------------------------------------------------
    # Global summary KPIs
    # -----------------------------------------------------------------------
    avg_mape  = summary_df["MAPE Ensemble %"].mean()
    best_prod = summary_df.loc[summary_df["MAPE Ensemble %"].idxmin(), "Producto"]
    worst_prod = summary_df.loc[summary_df["MAPE Ensemble %"].idxmax(), "Producto"]
    avg_conf  = summary_df["Confianza %"].mean()

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("MAPE medio ensemble", f"{avg_mape:.1f}%",
                       delta="Media todos productos", delta_dir="pos" if avg_mape < 4 else "neg")
    with c2: kpi_card("Mejor producto", best_prod,
                       delta=f"MAPE: {summary_df[summary_df['Producto']==best_prod]['MAPE Ensemble %'].iloc[0]:.1f}%",
                       delta_dir="pos")
    with c3: kpi_card("Producto + difícil", worst_prod,
                       delta=f"MAPE: {summary_df[summary_df['Producto']==worst_prod]['MAPE Ensemble %'].iloc[0]:.1f}%",
                       delta_dir="neg")
    with c4: kpi_card("Confianza media", f"{avg_conf:.0f}%", delta_dir="pos" if avg_conf > 70 else "neu")

    st.markdown("<br>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Summary accuracy table (all products)
    # -----------------------------------------------------------------------
    section_header("Tabla de precisión por producto")

    def _mape_color(val):
        if isinstance(val, float):
            if val < 3:   return "background-color:#EBF9F4; color:#00845E; font-weight:700;"
            if val < 7:   return "background-color:#FFF8E1; color:#B7860B;"
            return "background-color:#FEF0ED; color:#C0392B;"
        return ""

    def _conf_color(val):
        if isinstance(val, float):
            if val >= 80: return "color:#00845E; font-weight:700;"
            if val >= 60: return "color:#B7860B;"
            return "color:#C0392B;"
        return ""

    st.dataframe(
        summary_df.style
        .applymap(_mape_color, subset=["MAPE Ensemble %", "MAPE HW %", "MAPE RF %"])
        .applymap(_conf_color, subset=["Confianza %"]),
        use_container_width=True, height=280,
    )

    # -----------------------------------------------------------------------
    # Selected product backtest detail
    # -----------------------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    section_header(f"Detalle backtest: {product}")

    from data.demo_data import load_demo_data
    _data = load_demo_data()
    series = get_product_series(_data, product, region)
    engine = PlasticForecastEngine()
    engine.fit(series)
    bt_detail = engine.backtest()

    fig_bt = backtest_chart(bt_detail, title=f"Walk-forward validation – {product}")
    st.plotly_chart(fig_bt, use_container_width=True)

    col_bt1, col_bt2 = st.columns(2)
    with col_bt1:
        section_header("Métricas por fold")
        display_bt = bt_detail[["fold", "date_start", "mape_ens", "mape_hw", "mape_lf", "mape_rf", "rmse_ens", "confidence"]].copy()
        display_bt["date_start"] = display_bt["date_start"].dt.strftime("%b %Y")
        display_bt.columns = ["Fold", "Inicio", "MAPE Ens%", "MAPE HW%", "MAPE LF%", "MAPE RF%", "RMSE", "Conf%"]
        st.dataframe(display_bt.style.applymap(_mape_color, subset=["MAPE Ens%", "MAPE HW%", "MAPE RF%"]),
                     use_container_width=True)

    with col_bt2:
        section_header("Pesos del ensemble por producto")
        weight_rows = []
        for p in PRODUCTS:
            s = get_product_series(_data, p, region)
            if s.empty or len(s) < 20:
                continue
            eng = PlasticForecastEngine()
            eng.fit(s)
            w = eng.model_weights()
            weight_rows.append({"Producto": p, "HW": f"{w.get('hw',0)*100:.0f}%",
                                  "LF": f"{w.get('lf',0)*100:.0f}%", "RF": f"{w.get('rf',0)*100:.0f}%"})
        if weight_rows:
            st.dataframe(pd.DataFrame(weight_rows), use_container_width=True)

    # -----------------------------------------------------------------------
    # Supplier price table
    # -----------------------------------------------------------------------
    section_header("Precios actuales por proveedor")
    prices_df = data["prices"]
    last_date = prices_df["date"].max()
    sup_prices = prices_df[
        (prices_df["product"] == product) &
        (prices_df["region"]  == region) &
        (prices_df["date"]    == last_date)
    ][["supplier", "price", "volume"]].copy()
    sup_prices = sup_prices.merge(data["suppliers"][["supplier", "lead_time_days", "rating", "sustainability_score"]],
                                   on="supplier", how="left")
    sup_prices = sup_prices.sort_values("price")
    sup_prices.columns = ["Proveedor", "Precio (€/t)", "Volumen (t)", "Lead time (días)", "Rating", "Sostenibilidad"]

    def _price_bar(val):
        return f"color:{DANGER_RED};" if isinstance(val, float) and val == sup_prices["Precio (€/t)"].max() else (
            f"color:{SUCCESS_GREEN}; font-weight:700;" if isinstance(val, float) and val == sup_prices["Precio (€/t)"].min() else "")

    st.dataframe(
        sup_prices.style.applymap(_price_bar, subset=["Precio (€/t)"]),
        use_container_width=True,
    )

    # -----------------------------------------------------------------------
    # Monitoring alerts
    # -----------------------------------------------------------------------
    section_header("Alertas de seguimiento")
    for p in PRODUCTS:
        s = get_product_series(_data, p, region)
        if s.empty:
            continue
        mom = (s.iloc[-1] - s.iloc[-4]) / s.iloc[-4] * 100
        vol = s.rolling(3).std().iloc[-1] / s.mean() * 100
        if abs(mom) > 8:
            alert_box(f"<strong>{p}</strong>: Movimiento brusco {mom:+.1f}% en 3 meses",
                      level="high" if abs(mom) > 12 else "medium")
        if vol > 6:
            alert_box(f"<strong>{p}</strong>: Volatilidad elevada ({vol:.1f}% CV-3M)",
                      level="medium")
