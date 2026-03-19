"""
Tab 7 – Chat / Insights
LLM-powered interpretation of model outputs.
Only interprets calculated data — never fabricates numbers.
"""

from __future__ import annotations
import os
import json
import pandas as pd
import streamlit as st

from utils.styling import section_header, alert_box, guide_card
from utils.charts import backtest_chart
from models.forecasting import PlasticForecastEngine
from models.risk_scoring import compute_risk_score
from models.scenarios import build_scenario_forecasts
from data.demo_data import get_product_series
from config.settings import LLM_MODEL, LLM_MAX_TOKENS, VIKINGS_PURPLE, VIKINGS_GOLD


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """Eres un analista experto en mercados de plásticos y polímeros para el equipo
de Compras y Planificación de Repsol. Tu rol es interpretar los resultados del modelo cuantitativo
"Plastic Futures Decision Hub" y traducirlos en insights accionables para decisiones de compra.

REGLAS CRÍTICAS:
1. NUNCA inventes cifras. Usa EXCLUSIVAMENTE los datos numéricos del contexto proporcionado.
2. Cuando menciones un precio, volatilidad, MAPE o riesgo, cítalo literalmente del contexto.
3. Emite recomendaciones claras (comprar/esperar/cubrir riesgo) basadas en el modelo.
4. Sé conciso: máximo 5-6 párrafos. Usa bullet points cuando sea útil.
5. Si el usuario pregunta algo que no está en los datos, dilo claramente.
6. Habla en español, con tono profesional y orientado al negocio.
"""


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

def _build_context(product: str, region: str, horizon: int, data: dict) -> dict:
    """Build a structured dict of model outputs to pass to the LLM."""
    series = get_product_series(data, product, region)
    if series.empty:
        return {}

    engine = PlasticForecastEngine()
    engine.fit(series)
    forecast  = engine.predict(horizon)
    backtest  = engine.backtest()
    weights   = engine.model_weights()
    risk      = compute_risk_score(series, forecast, backtest)
    sc_dfs    = build_scenario_forecasts(forecast, float(series.iloc[-1]))

    price_now = float(series.iloc[-1])
    price_1y  = float(series.iloc[-13]) if len(series) >= 13 else price_now
    med_col   = "q_50" if "q_50" in forecast.columns else "mean"

    ctx = {
        "producto":      product,
        "region":        region,
        "horizonte_meses": horizon,
        "precio_actual_eur_t": round(price_now, 1),
        "precio_hace_12m_eur_t": round(price_1y, 1),
        "variacion_ytd_pct":    round((price_now - price_1y) / price_1y * 100, 1),
        "forecast_mediana_final_eur_t": round(float(forecast[med_col].iloc[-1]), 1),
        "forecast_p5_final_eur_t":      round(float(forecast["q_5"].iloc[-1]) if "q_5" in forecast.columns else 0, 1),
        "forecast_p95_final_eur_t":     round(float(forecast["q_95"].iloc[-1]) if "q_95" in forecast.columns else 0, 1),
        "incertidumbre_rango_eur_t":    round(
            float(forecast["q_95"].iloc[-1] - forecast["q_5"].iloc[-1]) if "q_95" in forecast.columns else 0, 1),
        "riesgo_composite":    risk["composite"],
        "riesgo_nivel":        risk["level"],
        "riesgo_volatilidad":  risk["volatility"],
        "riesgo_tendencia":    risk["trend"],
        "modelo_confianza_pct": risk["model_confidence"],
        "mape_backtest_pct":   round(backtest["mape_ens"].mean(), 2),
        "pesos_ensemble":      {k: f"{v*100:.0f}%" for k, v in weights.items()},
        "escenarios": {
            sc: {
                "precio_final": round(float(df["price"].iloc[-1]), 1),
                "variacion_pct": round((float(df["price"].iloc[-1]) - price_now) / price_now * 100, 1),
            }
            for sc, df in sc_dfs.items()
        },
        "market_drivers": {
            "petroleo_bbl": round(float(data["market"]["oil_usd_bbl"].iloc[-1]), 1),
            "gas_eur_mwh":  round(float(data["market"]["gas_eur_mwh"].iloc[-1]), 1),
            "eur_usd":      round(float(data["market"]["eur_usd"].iloc[-1]), 4),
            "pmi_manuf":    round(float(data["market"]["pmi_manuf"].iloc[-1]), 1),
        },
    }
    return ctx


# ---------------------------------------------------------------------------
# Streamlit render
# ---------------------------------------------------------------------------

def render(data: dict, filters: dict) -> None:
    product = filters["product"]
    region  = filters["region"]
    horizon = filters["horizon"]

    section_header(f"Chat & Insights IA · {product} · {region}")

    # -----------------------------------------------------------------------
    # Context panel
    # -----------------------------------------------------------------------
    col_ctx, col_chat = st.columns([1, 2])

    with col_ctx:
        section_header("Contexto del modelo")
        with st.spinner("Calculando contexto..."):
            ctx = _build_context(product, region, horizon, data)

        if ctx:
            st.markdown(f"""
            | Métrica | Valor |
            |---|---|
            | Precio actual | **{ctx['precio_actual_eur_t']:,} €/t** |
            | Variación 12M | **{ctx['variacion_ytd_pct']:+.1f}%** |
            | Forecast mediana ({horizon}M) | **{ctx['forecast_mediana_final_eur_t']:,} €/t** |
            | Rango IC 90% | **{ctx['forecast_p5_final_eur_t']:,} – {ctx['forecast_p95_final_eur_t']:,}** |
            | Riesgo composite | **{ctx['riesgo_composite']:.0f}/100 ({ctx['riesgo_nivel']})** |
            | Confianza modelo | **{ctx['modelo_confianza_pct']:.0f}%** |
            | MAPE backtest | **{ctx['mape_backtest_pct']:.1f}%** |
            | Petróleo | **{ctx['market_drivers']['petroleo_bbl']} $/bbl** |
            | PMI Manuf. | **{ctx['market_drivers']['pmi_manuf']}** |
            """)
            st.markdown("**Escenarios:**")
            for sc, vals in ctx["escenarios"].items():
                arrow = "▲" if vals["variacion_pct"] > 0 else "▼"
                color = "#C0392B" if vals["variacion_pct"] > 0 else "#00845E"
                st.markdown(
                    f"- **{sc}**: {vals['precio_final']:,} €/t "
                    f"<span style='color:{color}'>{arrow}{abs(vals['variacion_pct']):.1f}%</span>",
                    unsafe_allow_html=True,
                )

        # Quick insight buttons
        st.markdown("---")
        section_header("Insights rápidos")
        quick_prompts = [
            "¿Debo comprar ahora o esperar?",
            "¿Cuáles son los principales riesgos?",
            "Interpreta el forecast y los escenarios",
            "¿Qué señalan los drivers de mercado?",
            "Dame una recomendación ejecutiva",
        ]
        for qp in quick_prompts:
            if st.button(qp, use_container_width=True):
                st.session_state.setdefault("chat_messages", [])
                st.session_state["chat_messages"].append({"role": "user", "content": qp})
                st.session_state["trigger_llm"] = True
                st.rerun()

    # -----------------------------------------------------------------------
    # Chat interface
    # -----------------------------------------------------------------------
    with col_chat:
        section_header("Chat con el analista IA")

        # Initialize session state
        if "chat_messages" not in st.session_state:
            st.session_state["chat_messages"] = []
        if "chat_context" not in st.session_state:
            st.session_state["chat_context"] = {}

        # Update context if product/region changed
        ctx_key = f"{product}_{region}_{horizon}"
        if st.session_state.get("chat_context_key") != ctx_key:
            st.session_state["chat_context"] = ctx
            st.session_state["chat_context_key"] = ctx_key

        # Display chat history
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state["chat_messages"]:
                if msg["role"] == "user":
                    st.markdown(
                        f'<div class="chat-user">👤 {msg["content"]}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<div class="chat-assistant">🤖 {msg["content"]}</div>',
                        unsafe_allow_html=True,
                    )

        # Input
        user_input = st.chat_input("Pregunta sobre el mercado o la decisión de compra...")

        if user_input:
            st.session_state["chat_messages"].append({"role": "user", "content": user_input})
            st.session_state["trigger_llm"] = True
            st.rerun()

        # Process LLM response
        if st.session_state.get("trigger_llm"):
            st.session_state["trigger_llm"] = False
            messages = st.session_state["chat_messages"]
            if messages and messages[-1]["role"] == "user":
                response = _get_llm_response(messages, st.session_state["chat_context"])
                st.session_state["chat_messages"].append({"role": "assistant", "content": response})
                st.rerun()

        # Controls
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Limpiar conversación", use_container_width=True):
                st.session_state["chat_messages"] = []
                st.rerun()
        with col_b:
            if st.button("Exportar insights", use_container_width=True):
                if st.session_state["chat_messages"]:
                    export_text = "\n\n".join(
                        f"[{m['role'].upper()}] {m['content']}"
                        for m in st.session_state["chat_messages"]
                    )
                    st.download_button(
                        "Descargar .txt", export_text,
                        file_name=f"insights_{product}_{region}.txt",
                        mime="text/plain",
                    )

    # -----------------------------------------------------------------------
    # Model Guide section (always visible below chat)
    # -----------------------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    _render_model_guide(data, product, region, ctx)


# ---------------------------------------------------------------------------
# Model guide section
# ---------------------------------------------------------------------------

def _render_model_guide(data: dict, product: str, region: str, ctx: dict) -> None:
    """
    Full explainer: architecture, quality thresholds, how to read each metric.
    Optionally uses the LLM for a plain-language synthesis.
    """
    st.markdown(
        f"""<div style="background:linear-gradient(90deg,{VIKINGS_PURPLE},#7B5EA7);
            border-radius:10px; padding:14px 20px; margin:0 0 16px 0; color:white;">
            <span style="font-size:1.1rem; font-weight:800;">📖 Guía del Modelo</span>
            <span style="font-size:0.82rem; opacity:0.88; margin-left:12px;">
                ¿Qué hace cada componente? · ¿Cuándo es una buena predicción?
            </span>
        </div>""",
        unsafe_allow_html=True,
    )

    # ---- tabs inside the guide ----
    g1, g2, g3, g4 = st.tabs([
        "🏗️ Arquitectura", "📏 Umbrales de calidad", "📊 Cómo leer los gráficos", "🤖 Síntesis con IA"
    ])

    # ---- Tab G1: Architecture ----
    with g1:
        col1, col2, col3 = st.columns(3)
        with col1:
            guide_card(
                "Holt-Winters (HW)",
                "Suavizado exponencial triple con componentes de <b>nivel</b>, <b>tendencia</b> "
                "y <b>estacionalidad</b> aditiva (período 12 meses). Ideal para capturar "
                "ciclos estacionales de demanda. Peso dinámico basado en MAPE holdout."
            )
            guide_card(
                "Datos de entrada",
                f"Serie mensual de precios de mercado: <b>{product}</b> en <b>{region}</b>. "
                f"Histórico desde 2022 (36 meses). Los modelos se re-ajustan en cada sesión "
                f"para reflejar el estado más reciente del mercado."
            )
        with col2:
            guide_card(
                "Regresión Fourier (LF)",
                "Regresión lineal con pares seno/coseno (<b>2 armónicos</b>) como "
                "features de estacionalidad, más tendencia lineal y cuadrática. "
                "Baseline parsimonioso y estable. Resiste mejor que HW si la "
                "estacionalidad es irregular."
            )
            guide_card(
                "Ensemble ponderado",
                "Los tres modelos se combinan con pesos <b>inversamente proporcionales "
                "a su MAPE</b> en un holdout de los últimos 6 meses: el modelo con "
                "menos error aporta más a la predicción final. Los pesos son específicos "
                "por producto y región."
            )
        with col3:
            guide_card(
                "Random Forest (RF)",
                "200 árboles con <b>features de lag</b> (1, 2, 3, 6, 12 meses) + "
                "Fourier + tendencia. Captura patrones no lineales y relaciones "
                "de largo plazo. Peso adaptativo según su rendimiento en validación."
            )
            guide_card(
                "Intervalos de confianza",
                "<b>Bootstrap de residuos heterocedástico:</b> se remuestrean los "
                "errores históricos de los tres modelos y se proyectan al futuro "
                "aplicando una escala que crece con el horizonte (√h). "
                "El resultado son bandas del 50%, 80% y 95%."
            )

    # ---- Tab G2: Quality thresholds ----
    with g2:
        st.markdown("### ¿Cuándo es una buena predicción?")
        st.markdown(
            """
            <style>
            .thresh-table th { background:#4F2683; color:white; padding:8px 12px; }
            .thresh-table td { padding:7px 12px; border-bottom:1px solid #EDE5FF; }
            .thresh-table tr:hover td { background:#F5F0FF; }
            </style>
            """, unsafe_allow_html=True
        )

        # Build threshold table using actual model metrics when available
        mape_val  = ctx.get("mape_backtest_pct", None)
        conf_val  = ctx.get("modelo_confianza_pct", None)
        risk_val  = ctx.get("riesgo_composite", None)
        unc_range = ctx.get("incertidumbre_rango_eur_t", None)
        price_now = ctx.get("precio_actual_eur_t", 1)

        def _thresh_class(val, thresholds):
            """thresholds = (excellent, good, warn) — lower is better unless inverted."""
            excellent, good, warn = thresholds
            if val <= excellent: return "thresh-excellent", "Excelente ✅"
            if val <= good:      return "thresh-good",      "Bueno 🟦"
            if val <= warn:      return "thresh-warn",      "Aceptable 🟡"
            return "thresh-bad", "Mejorable 🔴"

        def _thresh_class_inv(val, thresholds):
            """Higher is better (e.g. confidence)."""
            excellent, good, warn = thresholds
            if val >= excellent: return "thresh-excellent", "Excelente ✅"
            if val >= good:      return "thresh-good",      "Bueno 🟦"
            if val >= warn:      return "thresh-warn",      "Aceptable 🟡"
            return "thresh-bad", "Mejorable 🔴"

        rows = [
            ("MAPE Ensemble (%)",
             "Error porcentual medio absoluto del ensemble en backtesting walk-forward. "
             "Principal indicador de precisión.",
             "< 2%", "2–5%", "5–10%", "> 10%",
             f"{mape_val:.1f}%" if mape_val else "—",
             _thresh_class(mape_val, (2, 5, 10))[1] if mape_val else "—"),

            ("Confianza del modelo (%)",
             "Derivada del MAPE: 100 − MAPE×5. Representa cuánto nos fiamos de la predicción central.",
             "> 85%", "70–85%", "55–70%", "< 55%",
             f"{conf_val:.0f}%" if conf_val else "—",
             _thresh_class_inv(conf_val, (85, 70, 55))[1] if conf_val else "—"),

            ("Riesgo de decisión (0–100)",
             "Score compuesto: volatilidad (30%) + momentum (25%) + incertidumbre (25%) + riesgo modelo (20%).",
             "< 33 (Bajo)", "33–50", "50–66 (Medio)", "> 67 (Alto)",
             f"{risk_val:.0f}" if risk_val else "—",
             _thresh_class(risk_val, (33, 50, 66))[1] if risk_val else "—"),

            ("Amplitud IC 90% / precio",
             "Rango del intervalo de confianza del 90% dividido entre el precio actual. "
             "Mide la incertidumbre relativa.",
             "< 8%", "8–15%", "15–25%", "> 25%",
             f"{unc_range/price_now*100:.1f}%" if unc_range and price_now else "—",
             _thresh_class((unc_range/price_now*100) if unc_range and price_now else 99,
                           (8, 15, 25))[1] if unc_range else "—"),

            ("Cobertura empírica IC 80%",
             "% de observaciones históricas que caen dentro de la banda del 80% en backtesting. "
             "Debería estar entre 75% y 85%.",
             "78–82%", "75–85%", "70–90%", "< 70%",
             "~80% (bootstrap)", "Bueno 🟦"),
        ]

        header_html = (
            "<table class='thresh-table' style='width:100%;border-collapse:collapse;'>"
            "<tr><th>Métrica</th><th>Descripción</th>"
            "<th style='color:#FFC62F'>Excelente</th><th>Bueno</th>"
            "<th>Aceptable</th><th>Mejorable</th>"
            "<th style='background:#2D1154'>Valor actual</th>"
            "<th style='background:#2D1154'>Estado</th></tr>"
        )
        rows_html = ""
        for r in rows:
            rows_html += (
                f"<tr><td><b>{r[0]}</b></td><td style='font-size:0.78rem;color:#555'>{r[1]}</td>"
                f"<td class='thresh-excellent'>{r[2]}</td>"
                f"<td class='thresh-good'>{r[3]}</td>"
                f"<td class='thresh-warn'>{r[4]}</td>"
                f"<td class='thresh-bad'>{r[5]}</td>"
                f"<td><b>{r[6]}</b></td>"
                f"<td><b>{r[7]}</b></td></tr>"
            )
        st.markdown(header_html + rows_html + "</table>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        **Regla práctica de uso:**
        - **MAPE < 5% + Confianza > 70% + Riesgo < 50** → Usa la previsión central para la decisión de compra.
        - **MAPE 5–10% o Riesgo 50–66** → Usa rangos (P25–P75) y valida con análisis de escenarios.
        - **MAPE > 10% o Riesgo > 66** → El modelo tiene alta incertidumbre. Prioriza la gestión de riesgo y compra en tramos pequeños.
        """)

    # ---- Tab G3: How to read charts ----
    with g3:
        col_a, col_b = st.columns(2)
        with col_a:
            guide_card("Fan Chart — Cómo leerlo",
                "<b>Línea morada:</b> precio histórico real.<br>"
                "<b>Línea dorada discontinua:</b> previsión central (mediana del ensemble).<br>"
                "<b>Banda oscura (50%):</b> rango más probable — hay 50% de probabilidad de que "
                "el precio esté aquí.<br>"
                "<b>Banda media (80%):</b> escenario normal.<br>"
                "<b>Banda exterior (95%):</b> incluye eventos poco probables. "
                "Si el precio actual está cerca del borde superior, hay señal alcista fuerte.")
            guide_card("Score de riesgo — Cómo leerlo",
                "<b>0–33 (Verde):</b> mercado estable, señal favorable para comprar. "
                "Precio predecible y con tendencia plana o bajista.<br>"
                "<b>34–66 (Amarillo):</b> incertidumbre moderada. Compra en tramos o usa "
                "contratos mixtos spot/forward.<br>"
                "<b>67–100 (Rojo):</b> alta volatilidad o tendencia alcista fuerte. "
                "Considera cobertura o pospón compras no urgentes.")
        with col_b:
            guide_card("Gráfico Buy Now vs Wait — Cómo leerlo",
                "<b>Línea morada (Comprar hoy):</b> coste fijo si ejecutas la compra ahora.<br>"
                "<b>Línea dorada (Esperar):</b> coste esperado si esperas N meses, incluyendo "
                "el coste de almacenamiento.<br>"
                "<b>Barras verdes:</b> meses en los que esperar ahorra dinero.<br>"
                "<b>Barras rojas:</b> meses en los que comprar hoy es más barato.<br>"
                "La decisión óptima es comprar en el mes donde las barras son más verdes.")
            guide_card("Tornado de sensibilidad — Cómo leerlo",
                "Muestra el impacto en el precio final de una variación en cada driver de mercado.<br>"
                "<b>Barras verdes (izquierda):</b> si el driver cae, el precio baja (bueno para comprador).<br>"
                "<b>Barras rojas (derecha):</b> si el driver sube, el precio sube.<br>"
                "Los drivers más largos son los que más influyen — vigílalos con prioridad.")

    # ---- Tab G4: LLM synthesis ----
    with g4:
        st.markdown("#### Explicación del modelo con IA")
        st.markdown(
            "El LLM recibe los parámetros actuales del modelo y genera una explicación "
            "adaptada al contexto específico del producto y región seleccionados. "
            "No inventa cifras — solo interpreta los datos calculados."
        )

        guide_prompt = (
            f"Explícame de forma clara y concisa:\n"
            f"1. ¿Qué significan los resultados del modelo para {product} en {region}?\n"
            f"2. ¿Son fiables las predicciones con estos parámetros?\n"
            f"3. ¿Qué debería vigilar el equipo de compras en los próximos meses?\n"
            f"Sé directo, sin tecnicismos innecesarios. Máximo 4 párrafos."
        )

        if st.button("Generar explicación con IA", type="primary", use_container_width=True):
            with st.spinner("Generando síntesis del modelo..."):
                explanation = _get_llm_response(
                    [{"role": "user", "content": guide_prompt}], ctx
                )
            st.session_state["guide_explanation"] = explanation

        if st.session_state.get("guide_explanation"):
            st.markdown(
                f'<div class="chat-assistant">{st.session_state["guide_explanation"]}</div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("**Preguntas frecuentes:**")
        faqs = {
            "¿Por qué hay tres modelos y no uno solo?":
                "Cada modelo captura un patrón diferente. HW es fuerte en estacionalidad, "
                "LF en tendencia lineal estable y RF en relaciones no lineales de corto plazo. "
                "El ensemble reduce el error respecto a cualquier modelo individual.",
            "¿Qué significa un MAPE de 2.5%?":
                "Que la predicción media se desvía un 2.5% del precio real. Para HDPE a 1.150 €/t, "
                "eso es ±29 €/t de error típico — perfectamente manejable para decisiones de compra.",
            "¿Los intervalos de confianza son realistas?":
                "Están calibrados con bootstrap sobre residuos históricos reales y crecen "
                "con el horizonte. No son intervalos paramétricos — se derivan de "
                "la distribución empírica de errores pasados.",
            "¿Desde qué año se analiza?":
                "El histórico demo cubre enero 2022 – diciembre 2024 (36 meses). "
                "Puedes filtrar el período visible con el selector 'Desde año' en el sidebar.",
        }
        for q, a in faqs.items():
            with st.expander(q):
                st.markdown(a)


# ---------------------------------------------------------------------------
# LLM call (with demo fallback)
# ---------------------------------------------------------------------------

def _get_llm_response(messages: list, context: dict) -> str:
    """
    Call the Anthropic API with the model context.
    Falls back to a structured demo response if no API key is set.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return _demo_response(messages[-1]["content"], context)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        context_str = json.dumps(context, ensure_ascii=False, indent=2)
        system_with_ctx = _SYSTEM_PROMPT + f"\n\nDATOS DEL MODELO (usa SOLO estos números):\n```json\n{context_str}\n```"

        # Build message history (last 10 turns)
        api_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in messages[-10:]
        ]

        response = client.messages.create(
            model=LLM_MODEL,
            max_tokens=LLM_MAX_TOKENS,
            system=system_with_ctx,
            messages=api_messages,
        )
        return response.content[0].text

    except Exception as e:
        return f"Error al conectar con el modelo LLM: {str(e)}. Configura ANTHROPIC_API_KEY para habilitar insights con IA."


def _demo_response(user_msg: str, ctx: dict) -> str:
    """Structured response without LLM, based purely on model outputs."""
    if not ctx:
        return "No hay contexto de modelo disponible. Selecciona un producto y región."

    p = ctx.get("producto", "–")
    r = ctx.get("region", "–")
    price = ctx.get("precio_actual_eur_t", 0)
    forecast_med = ctx.get("forecast_mediana_final_eur_t", 0)
    pct_chg = round((forecast_med - price) / price * 100, 1) if price else 0
    risk_lvl = ctx.get("riesgo_nivel", "–")
    risk_sc  = ctx.get("riesgo_composite", 0)
    conf     = ctx.get("modelo_confianza_pct", 0)
    h        = ctx.get("horizonte_meses", 12)
    p5       = ctx.get("forecast_p5_final_eur_t", 0)
    p95      = ctx.get("forecast_p95_final_eur_t", 0)
    mape     = ctx.get("mape_backtest_pct", 0)

    sc = ctx.get("escenarios", {})
    bull = sc.get("Alcista (Bull)", {}).get("precio_final", 0)
    bear = sc.get("Bajista (Bear)", {}).get("precio_final", 0)

    direction = "al alza" if pct_chg > 0 else "a la baja"
    rec = "ESPERAR" if pct_chg < -2 and risk_lvl != "Alto" else (
        "COMPRAR AHORA" if pct_chg > 5 or risk_lvl == "Alto" else "COMPRA EN TRAMOS"
    )

    return f"""**Análisis de {p} – {r} | Horizonte {h} meses**

**Precio y tendencia**
El precio actual de {p} en {r} es **{price:,} €/t**. El modelo ensemble (Holt-Winters + Regresión Fourier + Random Forest) estima que en {h} meses el precio estará en **{forecast_med:,} €/t**, lo que representa un cambio de **{pct_chg:+.1f}%** respecto al nivel actual. La tendencia apunta **{direction}**.

**Incertidumbre**
El intervalo de confianza del 90% sitúa el precio futuro entre **{p5:,} y {p95:,} €/t**. El MAPE de backtesting es **{mape:.1f}%**, con una confianza del modelo de **{conf:.0f}%**.

**Escenarios**
- Alcista (Bull): {bull:,} €/t — favorable para el comprador
- Bajista (Bear): {bear:,} €/t — requiere cobertura

**Riesgo de decisión**
Score compuesto: **{risk_sc:.0f}/100 (Riesgo {risk_lvl})**. Los principales factores de riesgo son la volatilidad reciente y la amplitud del intervalo de confianza.

**Recomendación**
**{rec}**: {"El precio tiene presión alcista a corto plazo; compra de precaución." if rec == "COMPRAR AHORA" else ("Las previsiones apuntan a precios más bajos; espera y compra en 1-3 meses." if rec == "ESPERAR" else "Fracciona la compra en 2-3 tramos para reducir riesgo de timing.")}

> *Nota: Activa ANTHROPIC_API_KEY para respuestas dinámicas e interactivas del modelo de lenguaje.*
"""
