"""
CSS injection and UI helpers for the Repsol brand experience.
"""

from __future__ import annotations
import streamlit as st
from config.settings import (
    REPSOL_ORANGE, REPSOL_MAGENTA, REPSOL_BLUE,
    IVORY, IVORY_DARK, DARK_NAVY, SUCCESS_GREEN, WARNING_AMBER, DANGER_RED,
    APP_TITLE, APP_SUBTITLE,
)


# ---------------------------------------------------------------------------
# Main CSS injection
# ---------------------------------------------------------------------------

def apply_custom_css() -> None:
    st.markdown(
        f"""
        <style>
        /* ---- Base ---- */
        html, body, [data-testid="stAppViewContainer"] {{
            background-color: {IVORY};
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }}
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {DARK_NAVY} 0%, #12244E 100%);
        }}
        [data-testid="stSidebar"] * {{
            color: #E8EDF5 !important;
        }}
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stMultiSelect label,
        [data-testid="stSidebar"] .stSlider label {{
            color: #B0BEC5 !important;
            font-size: 0.78rem;
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
            color: {DARK_NAVY};
            background: transparent;
        }}
        .stTabs [aria-selected="true"] {{
            background: {REPSOL_ORANGE} !important;
            color: white !important;
        }}

        /* ---- KPI card ---- */
        .kpi-card {{
            background: white;
            border-left: 4px solid {REPSOL_ORANGE};
            border-radius: 10px;
            padding: 18px 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.07);
            margin-bottom: 8px;
        }}
        .kpi-label {{
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: {REPSOL_BLUE};
            font-weight: 700;
            margin-bottom: 4px;
        }}
        .kpi-value {{
            font-size: 1.8rem;
            font-weight: 800;
            color: {DARK_NAVY};
            line-height: 1.1;
        }}
        .kpi-delta {{
            font-size: 0.78rem;
            font-weight: 600;
            margin-top: 4px;
        }}
        .kpi-delta.pos {{ color: {SUCCESS_GREEN}; }}
        .kpi-delta.neg {{ color: {DANGER_RED}; }}
        .kpi-delta.neu {{ color: {WARNING_AMBER}; }}

        /* ---- Section header ---- */
        .section-header {{
            font-size: 1.0rem;
            font-weight: 700;
            color: {REPSOL_BLUE};
            border-bottom: 2px solid {REPSOL_ORANGE};
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

        /* ---- Table highlight ---- */
        .dataframe tbody tr:hover {{ background-color: #FFF3EC !important; }}

        /* ---- Alert box ---- */
        .alert-box {{
            border-left: 4px solid {WARNING_AMBER};
            background: #FFF8E6;
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
                {REPSOL_ORANGE} 0%,
                {REPSOL_MAGENTA} 50%,
                {REPSOL_BLUE} 100%);
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
        }}
        .app-header p {{
            font-size: 0.85rem;
            margin: 0;
            opacity: 0.88;
        }}

        /* ---- Chat bubble ---- */
        .chat-user {{
            background: {IVORY_DARK};
            border-radius: 12px 12px 4px 12px;
            padding: 10px 14px;
            margin: 8px 60px 8px 0;
            font-size: 0.88rem;
        }}
        .chat-assistant {{
            background: linear-gradient(135deg, #FFF3EC, #FAFAF5);
            border-left: 3px solid {REPSOL_ORANGE};
            border-radius: 4px 12px 12px 12px;
            padding: 12px 16px;
            margin: 8px 0 8px 60px;
            font-size: 0.88rem;
        }}

        /* ---- Metric override ---- */
        [data-testid="metric-container"] {{
            background: white;
            border-radius: 10px;
            padding: 14px !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
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
            <h1>🛢️ {APP_TITLE}</h1>
            <p>{APP_SUBTITLE} &nbsp;|&nbsp; Market Intelligence & Procurement Decision Support</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, delta: str = "", delta_dir: str = "neu") -> None:
    """Render a branded KPI card."""
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


def render_sidebar_brand() -> None:
    """Brand mark + tagline inside sidebar."""
    st.markdown(
        f"""
        <div style="text-align:center; padding: 16px 0 24px 0; border-bottom: 1px solid rgba(255,255,255,0.12); margin-bottom: 20px;">
            <div style="font-size:2rem;">🛢️</div>
            <div style="font-size:1.1rem; font-weight:800; color:white; margin:4px 0 2px 0;">
                Plastic Futures
            </div>
            <div style="font-size:0.68rem; color:#7EC8E3; letter-spacing:0.08em; text-transform:uppercase;">
                Decision Hub · Repsol
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
