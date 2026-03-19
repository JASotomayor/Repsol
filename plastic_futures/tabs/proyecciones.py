"""
Tab 2 – Proyecciones
Previsión de precio con bandas de confianza, tabla de rangos y validación histórica.
"""

from __future__ import annotations
import pandas as pd
import streamlit as st

from utils.styling import section_header, kpi_card
from utils.charts import fan_chart, backtest_chart, feature_importance_chart
from models.forecasting import PlasticForecastEngine
from data.demo_data import get_product_series
from config.settings import DANGER_RED, SUCCESS_GREEN, DATA_START_YEAR, DATA_END_YEAR

_YEAR_OPTS = list(range(DATA_START_YEAR, DATA_END_YEAR + 1))
_GRAN_OPTS = ["Mensual", "Trimestral", "Anual"]
_QTR_OPTS  = ["Todos", "T1 (Ene–Mar)", "T2 (Abr–Jun)", "T3 (Jul–Sep)", "T4 (Oct–Dic)"]
_QTR_MONTHS = {
    "T1 (Ene–Mar)": [1, 2, 3], "T2 (Abr–Jun)": [4, 5, 6],
    "T3 (Jul–Sep)": [7, 8, 9], "T4 (Oct–Dic)": [10, 11, 12],
}


@st.cache_data(show_spinner=False, ttl=600)
def _fit_and_forecast(product: str, region: str, horizon: int, _key: str):
    from data.demo_data import load_demo_data
    data    = load_demo_data()
    series  = get_product_series(data, product, region)
    engine  = PlasticForecastEngine()
    engine.fit(series)
    forecast = engine.predict(horizon)
    backtest = engine.backtest()
    weights  = engine.model_weights()
    feat_imp = engine.feature_importances()
    return series, forecast, backtest, weights, feat_imp


def render(data: dict, filters: dict) -> None:
    product = filters["product"]
    region  = filters["region"]
    horizon = filters["horizon"]

    with st.spinner("Calculando previsiones..."):
        series, forecast, backtest, weights, feat_imp = _fit_and_forecast(
            product, region, horizon, f"{product}_{region}_{horizon}"
        )

    last_price  = series.iloc[-1]
    med_col     = "q_50" if "q_50" in forecast.columns else "mean"
    price_end   = forecast[med_col].iloc[-1]
    pct_change  = (price_end - last_price) / last_price * 100
    avg_mape    = backtest["mape_ens"].mean()
    model_conf  = max(0, 100 - avg_mape * 5)
    ci_width    = float(forecast["q_95"].iloc[-1] - forecast["q_5"].iloc[-1]) if "q_95" in forecast.columns else 0

    # ── KPIs ────────────────────────────────────────────────────────────────
    section_header(f"Previsión de precio · {product} · {region}")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Precio de mercado hoy", f"{last_price:,.0f} €/t",
                 delta="Último dato disponible", delta_dir="neu")
    with c2:
        d = "neg" if pct_change > 5 else ("pos" if pct_change < -5 else "neu")
        kpi_card(f"Previsión a {horizon} meses", f"{price_end:,.0f} €/t",
                 delta=f"{pct_change:+.1f}% respecto al precio actual", delta_dir=d)
    with c3:
        d2 = "pos" if model_conf > 70 else ("neu" if model_conf > 50 else "neg")
        kpi_card("Fiabilidad del modelo", f"{model_conf:.0f}%",
                 delta=f"Error medio histórico: {avg_mape:.1f}%", delta_dir=d2)
    with c4:
        d3 = "neg" if ci_width / last_price > 0.15 else "neu"
        kpi_card("Margen de incertidumbre",
                 f"±{ci_width/2:,.0f} €/t",
                 delta=f"Rango posible en mes {horizon}", delta_dir=d3)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Fan chart + panel lateral ────────────────────────────────────────────
    col_main, col_side = st.columns([3, 1], gap="large")
    with col_main:
        # Inline time filters
        fi1, fi2, fi3, _fpad = st.columns([1, 1.2, 1.4, 2])
        with fi1:
            fc_year = st.selectbox("📅 Desde", _YEAR_OPTS,
                                   index=0, key="proy_year")
        with fi2:
            fc_gran = st.selectbox("📊 Agrupación", _GRAN_OPTS, key="proy_gran")
        with fi3:
            fc_qtr = st.selectbox("🗓 Trimestre", _QTR_OPTS, key="proy_qtr")
        fc_months = _QTR_MONTHS.get(fc_qtr)

        fig = fan_chart(
            series, forecast,
            title=f"Evolución y previsión — {product} ({region})",
            from_year=fc_year, granularity=fc_gran, active_months=fc_months,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_side:
        section_header("Modelo combinado")
        model_labels = {"hw": "Tendencia estacional", "lf": "Modelo lineal", "rf": "Modelo predictivo"}
        for k, label in model_labels.items():
            w = weights.get(k, 0)
            bar_w = int(w * 100)
            st.markdown(f"""
            <div style="margin-bottom:10px;">
                <div style="font-size:0.72rem; color:#7B5EA7; font-weight:600; margin-bottom:3px;">{label}</div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <div style="flex:1; background:#EDE8F8; border-radius:4px; height:8px;">
                        <div style="width:{bar_w}%; background:#4F2683; border-radius:4px; height:8px;"></div>
                    </div>
                    <div style="font-size:0.78rem; font-weight:700; color:#2D1154; min-width:32px;">{w*100:.0f}%</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        section_header("Rangos previstos")
        if "q_25" in forecast.columns:
            rows = [
                ("Optimista (P25)",    forecast["q_25"].iloc[-1], SUCCESS_GREEN),
                ("Central (mediana)",  forecast[med_col].iloc[-1], "#4F2683"),
                ("Pesimista (P75)",    forecast["q_75"].iloc[-1], DANGER_RED),
            ]
            for label, val, color in rows:
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;'
                    f'padding:5px 0;border-bottom:1px solid #EDE8F8;">'
                    f'<span style="font-size:0.76rem;color:#7B5EA7;">{label}</span>'
                    f'<span style="font-size:0.82rem;font-weight:700;color:{color};">'
                    f'{val:,.0f} €/t</span></div>',
                    unsafe_allow_html=True,
                )

    # ── Tabla de rangos por mes ─────────────────────────────────────────────
    section_header("Rangos mensuales de previsión (€/ton)")
    st.caption("ℹ️ Formato americano: la coma ( , ) es separador de miles. Ejemplo: 1,206 = mil doscientos seis €/t.")

    q_cols = [c for c in ["q_5", "q_25", "q_50", "q_75", "q_95"] if c in forecast.columns]
    show_df = forecast[q_cols + ["mean", "std"]].copy()
    show_df.index = show_df.index.strftime("%b %Y")
    col_rename = {
        "q_5": "Mínimo posible", "q_25": "Optimista",
        "q_50": "Previsión central", "q_75": "Pesimista",
        "q_95": "Máximo posible", "mean": "Media", "std": "Desv. estándar",
    }
    show_df.rename(columns=col_rename, inplace=True)

    # Format: integers with thousands separator, no decimals
    show_fmt = show_df.applymap(lambda v: f"{int(round(v)):,}" if pd.notna(v) else "")

    def _color_cell(val: str) -> str:
        try:
            v = float(val.replace(",", ""))
            pct = (v - last_price) / last_price
            if pct > 0.05:  return "color:#C0392B; font-weight:600;"
            if pct < -0.05: return "color:#1E8449; font-weight:600;"
        except Exception:
            pass
        return ""

    st.dataframe(
        show_fmt.style.map(_color_cell),
        use_container_width=True, height=280,
    )

    # ── Validación y variables influyentes ──────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    col_bt, col_fi = st.columns([3, 2], gap="large")
    with col_bt:
        section_header("Precisión histórica del modelo")
        with st.expander("¿Qué muestra este gráfico?", expanded=False):
            st.markdown("""
            Para saber si el modelo es fiable, lo entrenamos **6 veces** sobre períodos históricos
            distintos, ocultándole datos reales que luego comparamos con lo que predijo.

            - **Barras (error %)**: cuánto se desvió la previsión del precio real en cada período.
              Verde < 3% · Amarillo < 7% · Rojo ≥ 7%.
            - **Líneas**: error individual de cada modelo (estacional, lineal, predictivo).
            - **Fila inferior (fiabilidad %)**: resumen de cuán preciso fue el modelo.
              Por encima del 70% es un resultado aceptable para tomar decisiones de compra.

            Cuanto más bajos los errores y más alta la fiabilidad, más confianza puedes
            depositar en la previsión central.
            """)
        fig_bt = backtest_chart(backtest)
        st.plotly_chart(fig_bt, use_container_width=True)

    with col_fi:
        section_header("¿Qué información usa el modelo?")
        with st.expander("Ver detalle de variables influyentes", expanded=False):
            st.markdown("""
            Muestra qué **señales del mercado** tienen más peso en la previsión.

            - **Precio hace 12 meses**: captura la estacionalidad anual del plástico.
            - **Precio mes anterior / hace 6 meses**: inercia reciente del mercado.
            - **Tendencia general**: dirección del precio a largo plazo.
            - **Estacionalidad cíclica**: ciclos periódicos del mercado (p. ej. mayor demanda en verano).

            Barras más largas = ese factor tiene más influencia en la previsión.
            Si el "Precio hace 12 meses" domina, el mercado sigue patrones estacionales claros.
            Si domina "Precio mes anterior", el mercado reacciona más a la inercia reciente.
            """)
            if feat_imp:
                fig_fi = feature_importance_chart(feat_imp)
                st.plotly_chart(fig_fi, use_container_width=True)

    with st.expander("¿Cómo se calculan las bandas de confianza?"):
        st.markdown("""
        La previsión central es el resultado de combinar tres modelos matemáticos
        (tendencia estacional, modelo lineal y modelo predictivo avanzado), ponderando
        cada uno según su rendimiento histórico.

        Las **bandas de confianza** muestran el rango de precios posibles:
        - **Zona más probable (50%)**: el precio debería caer aquí la mitad de las veces.
        - **Zona probable (80%)**: cubre la gran mayoría de los escenarios razonables.
        - **Zona posible (95%)**: incluye situaciones extremas pero factibles.

        Las bandas se amplían con el tiempo porque la incertidumbre crece
        cuanto más lejos se proyecta la previsión.

        La **fiabilidad del modelo** se mide con el error medio de previsiones
        realizadas sobre datos históricos que el modelo no había visto.
        """)
