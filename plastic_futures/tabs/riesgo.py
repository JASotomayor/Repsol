"""
Tab 3 – Riesgo de decisión
Puntuación de riesgo, análisis Comprar hoy vs Esperar, tabla de decisión.
"""

from __future__ import annotations
import streamlit as st

from utils.styling import section_header, kpi_card, risk_badge, alert_box
from utils.charts import risk_gauge, risk_radar, buy_vs_wait_chart
from models.risk_scoring import compute_risk_score, buy_now_vs_wait
from models.forecasting import PlasticForecastEngine
from data.demo_data import get_product_series
from config.settings import DEFAULT_VOLUME_TONS, CARRYING_COST_PER_TON_MONTH


@st.cache_data(show_spinner=False, ttl=600)
def _get_risk_data(product: str, region: str, horizon: int):
    from data.demo_data import load_demo_data
    data    = load_demo_data()
    series  = get_product_series(data, product, region)
    engine  = PlasticForecastEngine()
    engine.fit(series)
    forecast = engine.predict(horizon)
    backtest = engine.backtest()
    return series, forecast, backtest


def render(data: dict, filters: dict) -> None:
    product = filters["product"]
    region  = filters["region"]
    horizon = filters["horizon"]

    with st.spinner("Calculando puntuación de riesgo..."):
        series, forecast, backtest = _get_risk_data(product, region, horizon)

    risk          = compute_risk_score(series, forecast, backtest)
    current_price = float(series.iloc[-1])

    # ── KPIs ────────────────────────────────────────────────────────────────
    section_header(f"Riesgo de decisión de compra · {product} · {region}")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        d = "neg" if risk["level"] == "Alto" else ("neu" if risk["level"] == "Medio" else "pos")
        kpi_card("Índice de riesgo compuesto", f"{risk['composite']:.0f} / 100",
                 delta=f"Nivel: {risk['level']}", delta_dir=d)
    with c2:
        kpi_card("Volatilidad del precio", f"{risk['volatility']:.0f} / 100",
                 delta="Variabilidad en los últimos 6 meses",
                 delta_dir="neg" if risk["volatility"] > 60 else "pos")
    with c3:
        kpi_card("Presión de tendencia", f"{risk['trend']:.0f} / 100",
                 delta="Impulso alcista (alto = precio subiendo)",
                 delta_dir="neg" if risk["trend"] > 60 else "pos")
    with c4:
        kpi_card("Fiabilidad del modelo", f"{risk['model_confidence']:.0f}%",
                 delta="Basada en validación con datos históricos",
                 delta_dir="pos" if risk["model_confidence"] > 70 else "neg")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Gauge + Radar + Interpretación ──────────────────────────────────────
    col_g, col_r, col_info = st.columns([2, 2, 3], gap="large")

    with col_g:
        section_header("Índice de riesgo")
        fig_gauge = risk_gauge(risk["composite"])
        st.plotly_chart(fig_gauge, use_container_width=True)
        st.markdown("<div style='text-align:center; margin-top:4px;'>", unsafe_allow_html=True)
        risk_badge(risk["level"])
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r:
        section_header("Desglose del riesgo")
        fig_radar = risk_radar(risk)
        st.plotly_chart(fig_radar, use_container_width=True)

    with col_info:
        section_header("Lectura del riesgo")
        comp = risk["composite"]
        if comp >= 67:
            alert_box(
                "<strong>Riesgo alto:</strong> el mercado muestra alta incertidumbre "
                "o tendencia alcista marcada. Se recomienda fraccionar la compra en tramos, "
                "explorar contratos de precio fijo o esperar señales de estabilización.",
                level="high",
            )
        elif comp >= 34:
            alert_box(
                "<strong>Riesgo moderado:</strong> existe cierta volatilidad pero la "
                "situación es manejable. Considera comprar un volumen parcial ahora y "
                "revisar el mercado antes de comprometer el resto.",
            )
        else:
            alert_box(
                "<strong>Riesgo bajo:</strong> condiciones favorables para la compra. "
                "El precio es estable y la previsión apunta a continuidad. "
                "Puedes adelantar volumen si dispones de capacidad de almacenamiento.",
                level="low",
            )

        st.markdown("---")
        st.markdown(f"""
        | Componente | Puntuación | Peso |
        |---|---|---|
        | Volatilidad del precio (6M) | {risk['volatility']:.0f} / 100 | 30 % |
        | Presión de tendencia (3M) | {risk['trend']:.0f} / 100 | 25 % |
        | Amplitud de la previsión | {risk['uncertainty']:.0f} / 100 | 25 % |
        | Incertidumbre del modelo | {100-risk['model_confidence']:.0f} / 100 | 20 % |
        | **Índice compuesto** | **{risk['composite']:.0f} / 100** | — |
        """)

    # ── Comprar hoy vs Esperar ───────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("¿Comprar hoy o esperar?")

    col_params, col_chart = st.columns([1, 3], gap="large")
    with col_params:
        volume = st.number_input(
            "Volumen a comprar (toneladas)",
            min_value=50, max_value=5000, value=DEFAULT_VOLUME_TONS, step=50,
        )
        carry = st.number_input(
            "Coste de almacenamiento (€/t/mes)",
            min_value=0.0, max_value=50.0,
            value=float(CARRYING_COST_PER_TON_MONTH), step=0.5,
        )
        st.markdown("---")
        cost_now = current_price * volume
        st.markdown("**Si compras hoy:**")
        st.markdown(f"### {cost_now:,.0f} €")

    buy_wait_df = buy_now_vs_wait(current_price, forecast, volume_tons=volume, carrying_cost=carry)

    with col_chart:
        fig_bw = buy_vs_wait_chart(buy_wait_df)
        st.plotly_chart(fig_bw, use_container_width=True)

    # ── Tabla de decisión mensual ────────────────────────────────────────────
    section_header("Decisión recomendada por mes")
    display_df = buy_wait_df[[
        "expected_price", "cost_if_buy_now", "cost_if_wait",
        "expected_savings", "p_price_rises", "decision"
    ]].copy()
    display_df.index = display_df.index.strftime("%b %Y")
    display_df.columns = [
        "Precio esperado (€/t)", "Coste si compras hoy (€)",
        "Coste si esperas (€)", "Ahorro estimado (€)",
        "Prob. de subida de precio", "Recomendación",
    ]
    display_df["Prob. de subida de precio"] = display_df["Prob. de subida de precio"].apply(lambda x: f"{x:.0%}")

    def _dec_color(val):
        if val == "Esperar":      return "background-color:#EBF9F4; color:#1E8449; font-weight:700;"
        if val == "Comprar ahora": return "background-color:#FEF0ED; color:#C0392B; font-weight:700;"
        return ""

    def _sav_color(val):
        try:
            v = float(val)
            if v > 0:  return "color:#1E8449; font-weight:600;"
            if v < 0:  return "color:#C0392B; font-weight:600;"
        except Exception:
            pass
        return ""

    st.dataframe(
        display_df.style
            .map(_dec_color, subset=["Recomendación"])
            .map(_sav_color, subset=["Ahorro estimado (€)"]),
        use_container_width=True, height=280,
    )
