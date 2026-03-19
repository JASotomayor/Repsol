"""
Tab 7 – Análisis e Insights
Chat con IA + Guía del modelo en lenguaje de negocio.
"""

from __future__ import annotations
import os
import json
import streamlit as st

from utils.styling import section_header, alert_box, guide_card
from models.forecasting import PlasticForecastEngine
from models.risk_scoring import compute_risk_score
from models.scenarios import build_scenario_forecasts
from data.demo_data import get_product_series
from config.settings import LLM_MODEL, LLM_MAX_TOKENS, VIKINGS_PURPLE, VIKINGS_GOLD, VIKINGS_DARK


# ---------------------------------------------------------------------------
# System prompt for the LLM
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """Eres un analista de mercado especializado en plásticos y polímeros,
con experiencia en soporte a decisiones de compra para grandes empresas industriales.
Tu misión es interpretar los resultados del sistema de previsión "Plastic Futures Decision Hub"
y traducirlos en recomendaciones claras y accionables para el equipo de Compras.

NORMAS ESTRICTAS:
1. Usa ÚNICAMENTE los números que aparecen en el contexto JSON proporcionado. No inventes ni estimes cifras.
2. Cuando cites un precio, un porcentaje de error o una puntuación de riesgo, cópialo literalmente del contexto.
3. Habla en español, con tono profesional y directo. Evita tecnicismos innecesarios.
4. Estructura tu respuesta con párrafos cortos. Máximo 5 párrafos o una lista de puntos.
5. Si el usuario pregunta algo que no está en los datos disponibles, dilo con claridad.
"""

# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

def _build_context(product: str, region: str, horizon: int, data: dict) -> dict:
    series = get_product_series(data, product, region)
    if series.empty:
        return {}
    engine = PlasticForecastEngine()
    engine.fit(series)
    forecast = engine.predict(horizon)
    backtest = engine.backtest()
    weights  = engine.model_weights()
    risk     = compute_risk_score(series, forecast, backtest)
    sc_dfs   = build_scenario_forecasts(forecast, float(series.iloc[-1]))

    price_now = float(series.iloc[-1])
    price_1y  = float(series.iloc[-13]) if len(series) >= 13 else price_now
    med_col   = "q_50" if "q_50" in forecast.columns else "mean"

    return {
        "producto":                    product,
        "region":                      region,
        "horizonte_meses":             horizon,
        "precio_actual_eur_t":         round(price_now, 1),
        "precio_hace_12m_eur_t":       round(price_1y, 1),
        "variacion_12m_pct":           round((price_now - price_1y) / price_1y * 100, 1),
        "prevision_central_eur_t":     round(float(forecast[med_col].iloc[-1]), 1),
        "prevision_optimista_eur_t":   round(float(forecast["q_25"].iloc[-1]) if "q_25" in forecast.columns else 0, 1),
        "prevision_pesimista_eur_t":   round(float(forecast["q_75"].iloc[-1]) if "q_75" in forecast.columns else 0, 1),
        "rango_posible_min_eur_t":     round(float(forecast["q_5"].iloc[-1])  if "q_5"  in forecast.columns else 0, 1),
        "rango_posible_max_eur_t":     round(float(forecast["q_95"].iloc[-1]) if "q_95" in forecast.columns else 0, 1),
        "riesgo_compuesto_0_100":      risk["composite"],
        "nivel_riesgo":                risk["level"],
        "volatilidad_precio_0_100":    risk["volatility"],
        "presion_tendencia_0_100":     risk["trend"],
        "fiabilidad_modelo_pct":       risk["model_confidence"],
        "error_prevision_historico_pct": round(backtest["mape_ens"].mean(), 2),
        "pesos_modelos": {
            "tendencia_estacional": f"{weights.get('hw', 0)*100:.0f}%",
            "modelo_lineal":        f"{weights.get('lf', 0)*100:.0f}%",
            "modelo_predictivo":    f"{weights.get('rf', 0)*100:.0f}%",
        },
        "escenarios": {
            sc: {
                "precio_final_eur_t": round(float(df["price"].iloc[-1]), 1),
                "variacion_pct":      round((float(df["price"].iloc[-1]) - price_now) / price_now * 100, 1),
            }
            for sc, df in sc_dfs.items()
        },
        "factores_de_mercado": {
            "petroleo_usd_bbl":  round(float(data["market"]["oil_usd_bbl"].iloc[-1]), 1),
            "gas_eur_mwh":       round(float(data["market"]["gas_eur_mwh"].iloc[-1]), 1),
            "eur_usd":           round(float(data["market"]["eur_usd"].iloc[-1]), 4),
            "pmi_manufacturero": round(float(data["market"]["pmi_manuf"].iloc[-1]), 1),
        },
    }


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render(data: dict, filters: dict) -> None:
    product = filters["product"]
    region  = filters["region"]
    horizon = filters["horizon"]

    section_header(f"Análisis e Insights · {product} · {region}")

    # Two main sections: Chat and Guide
    s1, s2 = st.tabs(["Consulta al analista IA", "Guía del sistema de previsión"])

    # ── S1: Chat ─────────────────────────────────────────────────────────────
    with s1:
        col_ctx, col_chat = st.columns([1, 2], gap="large")

        with col_ctx:
            section_header("Datos del modelo")
            with st.spinner("Preparando contexto..."):
                ctx = _build_context(product, region, horizon, data)

            if ctx:
                st.markdown(f"""
                | | |
                |---|---|
                | **Precio actual** | {ctx['precio_actual_eur_t']:,} €/t |
                | **Variación 12M** | {ctx['variacion_12m_pct']:+.1f}% |
                | **Previsión ({horizon}M)** | {ctx['prevision_central_eur_t']:,} €/t |
                | Rango optimista | {ctx['prevision_optimista_eur_t']:,} €/t |
                | Rango pesimista | {ctx['prevision_pesimista_eur_t']:,} €/t |
                | **Riesgo** | {ctx['riesgo_compuesto_0_100']:.0f}/100 ({ctx['nivel_riesgo']}) |
                | **Fiabilidad** | {ctx['fiabilidad_modelo_pct']:.0f}% |
                | Error histórico | {ctx['error_prevision_historico_pct']:.1f}% |
                | Petróleo | {ctx['factores_de_mercado']['petroleo_usd_bbl']} $/bbl |
                | PMI Manuf. | {ctx['factores_de_mercado']['pmi_manufacturero']} |
                """)

                st.markdown("**Escenarios:**")
                for sc, vals in ctx["escenarios"].items():
                    arrow = "▲" if vals["variacion_pct"] > 0 else "▼"
                    c = "#C0392B" if vals["variacion_pct"] > 0 else "#1E8449"
                    st.markdown(
                        f"- **{sc}**: {vals['precio_final_eur_t']:,} €/t "
                        f"<span style='color:{c}'>{arrow}{abs(vals['variacion_pct']):.1f}%</span>",
                        unsafe_allow_html=True,
                    )

            st.markdown("---")
            section_header("Preguntas rápidas")
            quick_prompts = [
                "¿Debo comprar ahora o esperar?",
                "¿Cuáles son los principales riesgos del mercado?",
                "Explícame la previsión y los escenarios",
                "¿Qué señalan los factores de mercado?",
                "Dame una recomendación ejecutiva en 3 puntos",
            ]
            for qp in quick_prompts:
                if st.button(qp, use_container_width=True, key=f"qp_{qp[:20]}"):
                    st.session_state.setdefault("chat_messages", [])
                    st.session_state["chat_messages"].append({"role": "user", "content": qp})
                    st.session_state["trigger_llm"] = True
                    st.rerun()

        with col_chat:
            section_header("Chat con el analista")

            if "chat_messages" not in st.session_state:
                st.session_state["chat_messages"] = []

            ctx_key = f"{product}_{region}_{horizon}"
            if st.session_state.get("chat_context_key") != ctx_key:
                st.session_state["chat_context"] = ctx if ctx else {}
                st.session_state["chat_context_key"] = ctx_key

            # Message history
            for msg in st.session_state["chat_messages"]:
                css = "chat-user" if msg["role"] == "user" else "chat-assistant"
                icon = "🙋" if msg["role"] == "user" else "🤖"
                st.markdown(
                    f'<div class="{css}">{icon} {msg["content"]}</div>',
                    unsafe_allow_html=True,
                )

            user_input = st.chat_input("Escribe tu pregunta sobre el mercado o la decisión de compra…")
            if user_input:
                st.session_state["chat_messages"].append({"role": "user", "content": user_input})
                st.session_state["trigger_llm"] = True
                st.rerun()

            if st.session_state.get("trigger_llm"):
                st.session_state["trigger_llm"] = False
                msgs = st.session_state["chat_messages"]
                if msgs and msgs[-1]["role"] == "user":
                    with st.spinner("El analista está preparando la respuesta…"):
                        response = _get_llm_response(msgs, st.session_state.get("chat_context", {}))
                    st.session_state["chat_messages"].append({"role": "assistant", "content": response})
                    st.rerun()

            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Limpiar conversación", use_container_width=True):
                    st.session_state["chat_messages"] = []
                    st.rerun()
            with col_b:
                if st.button("Exportar conversación", use_container_width=True):
                    if st.session_state["chat_messages"]:
                        text = "\n\n".join(
                            f"[{m['role'].upper()}]\n{m['content']}"
                            for m in st.session_state["chat_messages"]
                        )
                        st.download_button(
                            "Descargar .txt", text,
                            file_name=f"analisis_{product}_{region}.txt",
                            mime="text/plain",
                        )

    # ── S2: Model Guide ───────────────────────────────────────────────────────
    with s2:
        _render_model_guide(data, product, region,
                            st.session_state.get("chat_context", {}))


# ---------------------------------------------------------------------------
# Model guide
# ---------------------------------------------------------------------------

def _render_model_guide(data: dict, product: str, region: str, ctx: dict) -> None:
    st.markdown(f"""
    <div style="background:{VIKINGS_DARK};
        border-left:4px solid {VIKINGS_GOLD}; border-radius:8px;
        padding:14px 20px; margin-bottom:18px;">
        <span style="font-size:1.05rem; font-weight:800; color:white;">
            Guía del sistema de previsión
        </span><br>
        <span style="font-size:0.80rem; color:rgba(255,255,255,0.65);">
            Cómo funciona el modelo · Qué indica cada métrica · Cuándo fiarse de la previsión
        </span>
    </div>
    """, unsafe_allow_html=True)

    g1, g2, g3, g4 = st.tabs([
        "Cómo funciona", "Indicadores de calidad", "Cómo leer los gráficos", "Explicación con IA"
    ])

    # ── G1: Architecture ────────────────────────────────────────────────────
    with g1:
        st.markdown(
            "El sistema combina **tres modelos de previsión** con enfoques complementarios. "
            "Cada modelo captura un tipo diferente de patrón en la evolución del precio. "
            "El resultado final es una **previsión combinada** que pesa cada modelo "
            "según su rendimiento reciente."
        )
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3, gap="medium")
        with c1:
            guide_card("Modelo de tendencia estacional",
                "Analiza el nivel del precio, su dirección y los ciclos estacionales "
                "(por ejemplo, mayor demanda en verano). Es especialmente útil cuando "
                "el precio sigue patrones repetitivos a lo largo del año.")
        with c2:
            guide_card("Modelo lineal",
                "Detecta la dirección general del mercado mediante una "
                "línea de tendencia que también incorpora patrones cíclicos. "
                "Es el más estable cuando el mercado es predecible.")
        with c3:
            guide_card("Modelo predictivo avanzado",
                "Aprende de los movimientos de precio de los últimos 1, 3, 6 y 12 meses "
                "para identificar patrones no evidentes. Funciona mejor cuando el precio "
                "muestra relaciones complejas con su propio historial.")

        st.markdown("<br>", unsafe_allow_html=True)
        c4, c5 = st.columns(2, gap="medium")
        with c4:
            guide_card("Previsión combinada",
                "Los tres modelos se combinan automáticamente asignando más peso "
                "al que mejor ha funcionado en los últimos meses. "
                "El resultado es una previsión más robusta que cualquier modelo por separado, "
                "porque compensa los errores individuales.")
        with c5:
            guide_card("Bandas de confianza",
                "No existe una única previsión correcta, sino un rango de posibilidades. "
                "Las bandas muestran dónde esperamos que caiga el precio con mayor o menor probabilidad: "
                "la banda central cubre el 50% de los casos más probables; "
                "la externa incluye también situaciones excepcionales.")

    # ── G2: Quality thresholds ──────────────────────────────────────────────
    with g2:
        st.markdown(
            "Estos son los indicadores que permiten saber si la previsión es fiable "
            "y qué nivel de confianza depositar en ella."
        )
        st.markdown("<br>", unsafe_allow_html=True)

        mape_val = ctx.get("error_prevision_historico_pct")
        conf_val = ctx.get("fiabilidad_modelo_pct")
        risk_val = ctx.get("riesgo_compuesto_0_100")
        price_now = ctx.get("precio_actual_eur_t", 1)
        unc_lo    = ctx.get("rango_posible_min_eur_t", 0)
        unc_hi    = ctx.get("rango_posible_max_eur_t", 0)
        unc_rel   = (unc_hi - unc_lo) / price_now * 100 if price_now else None

        def _badge(text: str, kind: str) -> str:
            colors = {
                "excelente": ("#E9F7EF", "#1E8449"),
                "bueno":     ("#EDE8F8", "#4F2683"),
                "aceptable": ("#FEFAE6", "#9A7D0A"),
                "mejorable": ("#FEF0ED", "#C0392B"),
            }
            bg, fg = colors.get(kind, ("#F5F5F5", "#555"))
            return f'<span style="background:{bg};color:{fg};padding:2px 8px;border-radius:10px;font-size:0.73rem;font-weight:700;">{text}</span>'

        def _state(val, thresholds, inv=False):
            if val is None: return "—", "—"
            ex, go, wa = thresholds
            if not inv:
                if val <= ex: return f"{val:.1f}%", _badge("Excelente", "excelente")
                if val <= go: return f"{val:.1f}%", _badge("Bueno", "bueno")
                if val <= wa: return f"{val:.1f}%", _badge("Aceptable", "aceptable")
                return f"{val:.1f}%", _badge("Mejorable", "mejorable")
            else:
                if val >= ex: return f"{val:.0f}%", _badge("Excelente", "excelente")
                if val >= go: return f"{val:.0f}%", _badge("Bueno", "bueno")
                if val >= wa: return f"{val:.0f}%", _badge("Aceptable", "aceptable")
                return f"{val:.0f}%", _badge("Mejorable", "mejorable")

        metrics = [
            (
                "Error de previsión histórico",
                "Diferencia media (%) entre lo que el modelo predijo y el precio real, "
                "medida en períodos pasados que el modelo no había visto.",
                "< 2%", "2–5%", "5–10%", "> 10%",
                *_state(mape_val, (2, 5, 10)),
            ),
            (
                "Fiabilidad del modelo",
                "Indicador resumen de la precisión: cuanto más alto, más confianza "
                "se puede depositar en la previsión central.",
                "> 85%", "70–85%", "55–70%", "< 55%",
                *_state(conf_val, (85, 70, 55), inv=True),
            ),
            (
                "Índice de riesgo de compra",
                "Puntuación 0–100 que combina la volatilidad del precio, "
                "la tendencia reciente y la incertidumbre de la previsión.",
                "< 33", "33–50", "51–66", "> 67",
                *(_state(risk_val, (33, 50, 66)) if risk_val else ("—", "—")),
            ),
            (
                "Amplitud del rango posible",
                "Diferencia entre el precio máximo y mínimo posible en el horizonte de previsión, "
                "como porcentaje del precio actual. Mide cuán incierto es el futuro.",
                "< 8%", "8–15%", "15–25%", "> 25%",
                *(_state(unc_rel, (8, 15, 25)) if unc_rel else ("—", "—")),
            ),
        ]

        header = (
            "<table style='width:100%;border-collapse:collapse;font-size:0.80rem;'>"
            f"<tr style='background:{VIKINGS_PURPLE};color:white;'>"
            "<th style='padding:9px 12px;text-align:left;font-weight:600;'>Indicador</th>"
            "<th style='padding:9px 12px;text-align:left;font-weight:600;'>Qué mide</th>"
            "<th style='padding:9px;'>Excelente</th><th style='padding:9px;'>Bueno</th>"
            "<th style='padding:9px;'>Aceptable</th><th style='padding:9px;'>Mejorable</th>"
            "<th style='padding:9px;font-weight:700;'>Valor actual</th>"
            "<th style='padding:9px;'>Estado</th></tr>"
        )
        rows_html = ""
        for i, r in enumerate(metrics):
            bg = "#FAFAFA" if i % 2 == 0 else "#FFFFFF"
            rows_html += (
                f"<tr style='background:{bg};'>"
                f"<td style='padding:8px 12px;font-weight:600;color:{VIKINGS_DARK};'>{r[0]}</td>"
                f"<td style='padding:8px 12px;color:#555;'>{r[1]}</td>"
                f"<td style='padding:8px;text-align:center;color:#1E8449;font-weight:600;'>{r[2]}</td>"
                f"<td style='padding:8px;text-align:center;color:{VIKINGS_PURPLE};'>{r[3]}</td>"
                f"<td style='padding:8px;text-align:center;color:#9A7D0A;'>{r[4]}</td>"
                f"<td style='padding:8px;text-align:center;color:#C0392B;'>{r[5]}</td>"
                f"<td style='padding:8px;text-align:center;font-weight:700;'>{r[6]}</td>"
                f"<td style='padding:8px;text-align:center;'>{r[7]}</td>"
                "</tr>"
            )
        st.markdown(header + rows_html + "</table>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.info(
            "**Regla práctica:** si el error es menor del 5% y la fiabilidad supera el 70%, "
            "la previsión central es un buen punto de partida para la decisión de compra. "
            "Si el riesgo supera 66 o el error supera el 10%, apóyate en los rangos "
            "y en el análisis de escenarios antes de comprometerte con un volumen alto."
        )

    # ── G3: How to read charts ───────────────────────────────────────────────
    with g3:
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            guide_card("Gráfico de previsión (fan chart)",
                "<b>Línea morada sólida:</b> precio histórico real.<br>"
                "<b>Línea dorada discontinua:</b> previsión central del modelo.<br>"
                "<b>Banda oscura:</b> zona donde caerá el precio en el 50% de los casos.<br>"
                "<b>Banda intermedia:</b> zona probable en la gran mayoría de los escenarios.<br>"
                "<b>Banda exterior:</b> incluye situaciones excepcionales.<br>"
                "Cuanto más estrechas son las bandas, más fiable es la previsión.")
            guide_card("Gráfico de riesgo (radar)",
                "Muestra los cuatro componentes del índice de riesgo:<br>"
                "<b>Volatilidad:</b> cuánto ha variado el precio recientemente.<br>"
                "<b>Tendencia:</b> si el precio está subiendo (perjudica al comprador).<br>"
                "<b>Incertidumbre:</b> cuán abierto es el rango de previsión.<br>"
                "<b>Fiabilidad del modelo:</b> si el modelo ha cometido errores recientes.<br>"
                "Un radar pequeño significa menor riesgo global.")
        with c2:
            guide_card("Gráfico Comprar hoy vs Esperar",
                "<b>Línea morada:</b> coste fijo si compras ahora.<br>"
                "<b>Línea dorada:</b> coste esperado si esperas, incluyendo el almacenamiento.<br>"
                "<b>Barras verdes:</b> meses en que esperar resulta más barato.<br>"
                "<b>Barras rojas:</b> meses en que comprar hoy es la opción económica.<br>"
                "No tiene en cuenta riesgos de suministro ni plazos de entrega.")
            guide_card("Gráfico de sensibilidad (tornado)",
                "Muestra qué factores externos tienen mayor impacto en el precio.<br>"
                "<b>Barra verde (izquierda):</b> si ese factor baja, el precio también baja.<br>"
                "<b>Barra roja (derecha):</b> si ese factor sube, el precio sube.<br>"
                "Los factores con barras más largas son los más importantes a vigilar.<br>"
                "Úsalo para entender qué noticias de mercado deben preocuparte más.")

    # ── G4: LLM synthesis ───────────────────────────────────────────────────
    with g4:
        st.markdown(
            "Pulsa el botón para que el analista de IA interprete los parámetros actuales "
            "del modelo y genere una explicación adaptada al contexto de "
            f"**{product}** en **{region}**."
        )
        st.markdown("<br>", unsafe_allow_html=True)

        guide_prompt = (
            f"Basándote exclusivamente en los datos del contexto proporcionado, explícame:\n"
            f"1. Qué nos dice el modelo sobre la evolución del precio de {product} en {region}.\n"
            f"2. Si los parámetros del modelo son fiables y por qué.\n"
            f"3. Cuáles son los principales puntos de atención para el equipo de compras.\n"
            f"Sé claro, directo y evita tecnicismos. Máximo 4 párrafos."
        )

        if st.button("Generar explicación del modelo", type="primary", use_container_width=True):
            ctx_current = st.session_state.get("chat_context", {})
            with st.spinner("Preparando análisis…"):
                explanation = _get_llm_response(
                    [{"role": "user", "content": guide_prompt}], ctx_current
                )
            st.session_state["guide_explanation"] = explanation

        if st.session_state.get("guide_explanation"):
            st.markdown(
                f'<div class="chat-assistant">{st.session_state["guide_explanation"]}</div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("**Preguntas frecuentes**")
        faqs = {
            "¿Por qué se combinan tres modelos?":
                "Cada modelo tiene puntos fuertes y puntos débiles según el tipo de mercado. "
                "Combinarlos reduce el riesgo de que un error de uno solo comprometa "
                "toda la previsión, y mejora la precisión media de forma consistente.",
            "¿Qué significa un error del 2,5%?":
                "Que la previsión se ha desviado una media del 2,5% del precio real "
                "en períodos históricos de validación. Para un precio de 1.150 €/t, "
                "eso equivale a unos ±29 €/t de margen de error típico.",
            "¿Las bandas de confianza son realistas?":
                "Sí. Se construyen a partir de los errores reales que el modelo ha cometido "
                "en el pasado, no de supuestos teóricos. Se amplían con el tiempo porque "
                "la incertidumbre crece cuanto más lejos se proyecta.",
            "¿Desde qué año parten los datos?":
                "El histórico de demostración cubre enero 2022 hasta diciembre 2024 (36 meses). "
                "El selector 'Desde el año' en el panel lateral permite ajustar el período visible "
                "en los gráficos históricos.",
            "¿Qué hago si el riesgo es alto?":
                "Un riesgo alto no significa que no debas comprar, sino que hay más incertidumbre. "
                "Las opciones habituales son: fraccionar la compra en varios meses, "
                "negociar un precio fijo con el proveedor, o esperar señales de estabilización "
                "del mercado antes de comprometer un volumen grande.",
        }
        for q, a in faqs.items():
            with st.expander(q):
                st.markdown(a)


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def _get_llm_response(messages: list, context: dict) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return _demo_response(messages[-1]["content"] if messages else "", context)
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        ctx_str = json.dumps(context, ensure_ascii=False, indent=2)
        system  = _SYSTEM_PROMPT + f"\n\nDATOS DEL MODELO (usa SOLO estos números):\n```json\n{ctx_str}\n```"
        api_msgs = [{"role": m["role"], "content": m["content"]} for m in messages[-10:]]
        response = client.messages.create(
            model=LLM_MODEL, max_tokens=LLM_MAX_TOKENS,
            system=system, messages=api_msgs,
        )
        return response.content[0].text
    except Exception as e:
        return f"No se ha podido conectar con el modelo de IA: {e}. Configura la variable ANTHROPIC_API_KEY para habilitar las respuestas dinámicas."


def _demo_response(user_msg: str, ctx: dict) -> str:
    if not ctx:
        return "No hay datos disponibles. Selecciona un producto y región en el panel lateral."

    p         = ctx.get("producto", "—")
    r         = ctx.get("region", "—")
    price     = ctx.get("precio_actual_eur_t", 0)
    prev_med  = ctx.get("prevision_central_eur_t", 0)
    prev_opt  = ctx.get("prevision_optimista_eur_t", 0)
    prev_pes  = ctx.get("prevision_pesimista_eur_t", 0)
    pct_chg   = round((prev_med - price) / price * 100, 1) if price else 0
    risk_lvl  = ctx.get("nivel_riesgo", "—")
    risk_sc   = ctx.get("riesgo_compuesto_0_100", 0)
    conf      = ctx.get("fiabilidad_modelo_pct", 0)
    h         = ctx.get("horizonte_meses", 12)
    mape      = ctx.get("error_prevision_historico_pct", 0)
    direction = "al alza" if pct_chg > 0 else "a la baja"
    rec = (
        "ESPERAR" if pct_chg < -2 and risk_lvl != "Alto" else
        "COMPRAR AHORA" if pct_chg > 5 or risk_lvl == "Alto" else
        "COMPRA EN TRAMOS"
    )

    return f"""**{p} · {r} — Horizonte {h} meses**

**Situación actual**
El precio de mercado de {p} en {r} se sitúa en **{price:,} €/t**. La previsión central apunta a **{prev_med:,} €/t** en {h} meses, lo que representa un cambio de **{pct_chg:+.1f}%**. La tendencia apunta **{direction}**.

**Rangos y confianza**
En el escenario más favorable, el precio podría situarse en **{prev_opt:,} €/t**; en el más adverso, en **{prev_pes:,} €/t**. El modelo tiene una fiabilidad del **{conf:.0f}%**, con un error histórico medio del **{mape:.1f}%**.

**Riesgo de decisión**
El índice de riesgo es **{risk_sc:.0f} sobre 100 (nivel {risk_lvl})**. {"El mercado muestra incertidumbre o presión alcista que conviene tener en cuenta." if risk_sc > 50 else "El mercado se encuentra en una zona de relativa estabilidad."}

**Recomendación**
**{rec}**: {"El precio tiene presión alcista; una compra preventiva reduce el riesgo de coste." if rec == "COMPRAR AHORA" else "La previsión apunta a precios más favorables; esperar puede generar ahorro." if rec == "ESPERAR" else "Fraccionar la compra en 2–3 entregas reduce la exposición al riesgo de precio."}

> *Activa la clave ANTHROPIC_API_KEY para obtener respuestas dinámicas e interactivas.*"""
