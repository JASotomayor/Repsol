"""
CSS injection and UI helpers — Minnesota Vikings theme.
"""

from __future__ import annotations
import streamlit as st
from config.settings import (
    VIKINGS_PURPLE, VIKINGS_GOLD, VIKINGS_MID, VIKINGS_DARK, VIKINGS_LIGHT,
    IVORY_DARK, SUCCESS_GREEN, WARNING_AMBER, DANGER_RED, MID_GRAY,
    APP_TITLE, APP_SUBTITLE,
    # Aliases used throughout the rest of the code
    REPSOL_ORANGE, REPSOL_MAGENTA, REPSOL_BLUE, IVORY, DARK_NAVY,
)


# ---------------------------------------------------------------------------
# Main CSS injection
# ---------------------------------------------------------------------------

def apply_custom_css() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

        /* ---- Base ---- */
        html, body, [data-testid="stAppViewContainer"] {{
            background-color: {VIKINGS_LIGHT};
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }}

        /* ---- Sidebar ---- */
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {VIKINGS_DARK} 0%, {VIKINGS_PURPLE} 100%);
        }}
        [data-testid="stSidebar"] * {{
            color: #E8E0FF !important;
        }}
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stMultiSelect label,
        [data-testid="stSidebar"] .stSlider label,
        [data-testid="stSidebar"] .stRadio label {{
            color: #C9B8F0 !important;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        /* ---- Tab bar ---- */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 4px;
            background: {IVORY_DARK};
            border-radius: 12px;
            padding: 4px;
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: 600;
            font-size: 0.82rem;
            color: {VIKINGS_DARK};
            background: transparent;
        }}
        .stTabs [aria-selected="true"] {{
            background: {VIKINGS_PURPLE} !important;
            color: white !important;
        }}

        /* ---- KPI card ---- */
        .kpi-card {{
            background: white;
            border-left: 4px solid {VIKINGS_GOLD};
            border-radius: 10px;
            padding: 18px 20px;
            box-shadow: 0 2px 10px rgba(79,38,131,0.10);
            margin-bottom: 8px;
        }}
        .kpi-label {{
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: {VIKINGS_PURPLE};
            font-weight: 700;
            margin-bottom: 4px;
        }}
        .kpi-value {{
            font-size: 1.8rem;
            font-weight: 800;
            color: {VIKINGS_DARK};
            line-height: 1.1;
        }}
        .kpi-delta {{
            font-size: 0.78rem;
            font-weight: 600;
            margin-top: 4px;
        }}
        .kpi-delta.pos {{ color: {SUCCESS_GREEN}; }}
        .kpi-delta.neg {{ color: {DANGER_RED}; }}
        .kpi-delta.neu {{ color: {VIKINGS_MID}; }}

        /* ---- Section header ---- */
        .section-header {{
            font-size: 1.0rem;
            font-weight: 700;
            color: {VIKINGS_PURPLE};
            border-bottom: 2px solid {VIKINGS_GOLD};
            padding-bottom: 6px;
            margin: 20px 0 14px 0;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}

        /* ---- Risk badge ---- */
        .risk-badge {{
            display: inline-block;
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.04em;
        }}
        .risk-high   {{ background:#fde9e5; color:{DANGER_RED}; }}
        .risk-medio  {{ background:#fff8e1; color:#B7860B; }}
        .risk-bajo   {{ background:#e8f8f5; color:#00845E; }}

        /* ---- Alert box ---- */
        .alert-box {{
            border-left: 4px solid {VIKINGS_GOLD};
            background: #FFF9E6;
            border-radius: 6px;
            padding: 10px 14px;
            margin: 6px 0;
            font-size: 0.82rem;
        }}
        .alert-box.high {{
            border-color: {DANGER_RED};
            background: #FFF0ED;
        }}
        .alert-box.low {{
            border-color: {SUCCESS_GREEN};
            background: #EBF9F4;
        }}

        /* ---- App header ---- */
        .app-header {{
            background: linear-gradient(135deg,
                {VIKINGS_DARK} 0%,
                {VIKINGS_PURPLE} 45%,
                {VIKINGS_MID} 75%,
                {VIKINGS_GOLD} 100%);
            border-radius: 14px;
            padding: 22px 28px;
            margin-bottom: 20px;
            color: white;
        }}
        .app-header h1 {{
            font-size: 1.7rem;
            font-weight: 800;
            margin: 0 0 4px 0;
            color: white;
            text-shadow: 0 1px 4px rgba(0,0,0,0.25);
        }}
        .app-header p {{
            font-size: 0.85rem;
            margin: 0;
            opacity: 0.88;
        }}

        /* ---- Guide / model explanation cards ---- */
        .guide-card {{
            background: white;
            border-top: 3px solid {VIKINGS_PURPLE};
            border-radius: 10px;
            padding: 16px 18px;
            box-shadow: 0 2px 8px rgba(79,38,131,0.08);
            margin-bottom: 12px;
        }}
        .guide-card h4 {{
            color: {VIKINGS_PURPLE};
            font-size: 0.9rem;
            font-weight: 700;
            margin: 0 0 8px 0;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        .guide-card p, .guide-card li {{
            color: {VIKINGS_DARK};
            font-size: 0.82rem;
            line-height: 1.55;
        }}

        /* ---- Threshold badge ---- */
        .thresh-excellent {{ color:#00845E; font-weight:700; }}
        .thresh-good      {{ color:{VIKINGS_PURPLE}; font-weight:600; }}
        .thresh-warn      {{ color:#B7860B; font-weight:600; }}
        .thresh-bad       {{ color:{DANGER_RED}; font-weight:600; }}

        /* ---- Chat bubble ---- */
        .chat-user {{
            background: {IVORY_DARK};
            border-radius: 12px 12px 4px 12px;
            padding: 10px 14px;
            margin: 8px 60px 8px 0;
            font-size: 0.88rem;
            border-left: 3px solid {VIKINGS_MID};
        }}
        .chat-assistant {{
            background: white;
            border-left: 3px solid {VIKINGS_GOLD};
            border-radius: 4px 12px 12px 12px;
            padding: 12px 16px;
            margin: 8px 0 8px 60px;
            font-size: 0.88rem;
            box-shadow: 0 1px 6px rgba(79,38,131,0.08);
        }}

        /* ---- Metric override ---- */
        [data-testid="metric-container"] {{
            background: white;
            border-radius: 10px;
            padding: 14px !important;
            box-shadow: 0 2px 8px rgba(79,38,131,0.07);
        }}

        /* ---- Time filter pill ---- */
        .time-filter-bar {{
            background: white;
            border-radius: 8px;
            padding: 8px 14px;
            margin-bottom: 12px;
            border: 1px solid {IVORY_DARK};
            font-size: 0.78rem;
            color: {VIKINGS_MID};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Component helpers
# ---------------------------------------------------------------------------

def render_header() -> None:
    st.markdown(
        f"""
        <div class="app-header">
            <h1>🏈 {APP_TITLE}</h1>
            <p>{APP_SUBTITLE} &nbsp;|&nbsp; Forecasting · Risk Scoring · Decision Intelligence</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, delta: str = "", delta_dir: str = "neu") -> None:
    delta_html = (
        f'<div class="kpi-delta {delta_dir}">{delta}</div>'
        if delta else ""
    )
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(text: str) -> None:
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)


def risk_badge(level: str) -> None:
    css = {"Alto": "risk-high", "Medio": "risk-medio", "Bajo": "risk-bajo"}.get(level, "risk-bajo")
    icons = {"Alto": "🔴", "Medio": "🟡", "Bajo": "🟢"}
    st.markdown(
        f'<span class="risk-badge {css}">{icons.get(level, "")} Riesgo {level}</span>',
        unsafe_allow_html=True,
    )


def alert_box(msg: str, level: str = "medium") -> None:
    css = {"high": "high", "low": "low"}.get(level, "")
    st.markdown(f'<div class="alert-box {css}">{msg}</div>', unsafe_allow_html=True)


def guide_card(title: str, body: str) -> None:
    """Render a styled card for the model guide section."""
    st.markdown(
        f'<div class="guide-card"><h4>{title}</h4><p>{body}</p></div>',
        unsafe_allow_html=True,
    )


def render_sidebar_brand() -> None:
    st.markdown(
        f"""
        <div style="text-align:center; padding: 16px 0 24px 0;
            border-bottom: 1px solid rgba(255,255,255,0.15); margin-bottom: 20px;">
            <div style="font-size:2.2rem;">🏈</div>
            <div style="font-size:1.1rem; font-weight:800; color:white; margin:4px 0 2px 0;">
                Plastic Futures
            </div>
            <div style="font-size:0.68rem; color:#C9B8F0; letter-spacing:0.08em; text-transform:uppercase;">
                Decision Hub
            </div>
            <div style="margin-top:8px; display:inline-block; background:#FFC62F; color:#2D1154;
                font-size:0.62rem; font-weight:800; padding:2px 10px; border-radius:10px;
                letter-spacing:0.06em;">
                MINNESOTA Vikings EDITION
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def time_filter_info(from_year: int, granularity: str, period_label: str = "") -> None:
    """Small info bar showing active time filter."""
    extra = f" · {period_label}" if period_label else ""
    st.markdown(
        f'<div class="time-filter-bar">📅 Mostrando desde <strong>{from_year}</strong>'
        f' · Granularidad: <strong>{granularity}</strong>{extra}</div>',
        unsafe_allow_html=True,
    )
