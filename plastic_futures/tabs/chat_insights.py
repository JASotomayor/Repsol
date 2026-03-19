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

from utils.styling import section_header, alert_box
from models.forecasting import PlasticForecastEngine
from models.risk_scoring import compute_risk_score
from models.scenarios import build_scenario_forecasts
from data.demo_data import get_product_series
from config.settings import LLM_MODEL, LLM_MAX_TOKENS


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
