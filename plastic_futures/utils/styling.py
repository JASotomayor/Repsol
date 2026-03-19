"""
CSS injection and UI helpers.
Vikings palette — light sidebar for full legibility of all native Streamlit components.
"""

from __future__ import annotations
import streamlit as st
from config.settings import (
    VIKINGS_PURPLE, VIKINGS_GOLD, VIKINGS_MID, VIKINGS_DARK, VIKINGS_LIGHT,
    IVORY_DARK, SUCCESS_GREEN, DANGER_RED,
    APP_TITLE, APP_SUBTITLE,
    REPSOL_ORANGE, REPSOL_BLUE, IVORY, DARK_NAVY,
)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

def apply_custom_css() -> None:
    st.markdown(f"""
    <style>
    /* ═══════════════════════════════════════════════════════════
       BASE
    ═══════════════════════════════════════════════════════════ */
    html, body, [data-testid="stAppViewContainer"] {{
        background-color: #F8F6FF;
        font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
    }}

    /* Remove default top padding from main content */
    .block-container {{
        padding-top: 1.2rem !important;
        padding-bottom: 2rem !important;
        max-width: 1400px;
    }}

    /* ═══════════════════════════════════════════════════════════
       SIDEBAR  —  DARK purple background, full white text
    ═══════════════════════════════════════════════════════════ */
    [data-testid="stSidebar"] {{
        background: {VIKINGS_DARK} !important;
        border-right: 1px solid {VIKINGS_PURPLE};
        box-shadow: 2px 0 16px rgba(0,0,0,0.25);
    }}

    /* All text elements white */
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] *,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] .stMarkdown {{
        color: rgba(255,255,255,0.92) !important;
    }}

    /* Component labels — soft gold uppercase */
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiSelect label,
    [data-testid="stSidebar"] .stSlider label,
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stNumberInput label {{
        color: {VIKINGS_GOLD} !important;
        font-size: 0.73rem !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}

    /* Select / multiselect boxes */
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-baseweb="input"] {{
        background: rgba(255,255,255,0.10) !important;
        border-color: rgba(255,255,255,0.25) !important;
        border-radius: 6px !important;
    }}
    [data-testid="stSidebar"] [data-baseweb="select"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] [data-baseweb="select"] span {{
        color: white !important;
    }}

    /* Slider track & thumb */
    [data-testid="stSidebar"] [data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {{
        background: {VIKINGS_GOLD} !important;
        border-color: {VIKINGS_GOLD} !important;
    }}
    [data-testid="stSidebar"] .stSlider [data-baseweb="slider"] > div > div:first-child {{
        background: rgba(255,255,255,0.20) !important;
    }}
    [data-testid="stSidebar"] .stSlider [data-baseweb="slider"] > div > div:nth-child(2) {{
        background: {VIKINGS_GOLD} !important;
    }}

    /* Multi-select tags */
    [data-testid="stSidebar"] [data-baseweb="tag"] {{
        background: {VIKINGS_PURPLE} !important;
        border: 1px solid rgba(255,255,255,0.30) !important;
    }}
    [data-testid="stSidebar"] [data-baseweb="tag"] span {{
        color: white !important;
    }}

    /* Tooltip icons */
    [data-testid="stSidebar"] [data-testid="stTooltipIcon"] svg {{
        fill: rgba(255,255,255,0.50) !important;
    }}

    /* Section dividers */
    [data-testid="stSidebar"] hr {{
        border-color: rgba(255,255,255,0.15);
        margin: 12px 0;
    }}

    /* Collapse arrow */
    [data-testid="stSidebarCollapseButton"] svg {{
        fill: white !important;
    }}
    [data-testid="stSidebarCollapseButton"] {{
        background: rgba(255,255,255,0.08) !important;
    }}

    /* ── Slider & select_slider on dark sidebar ── */

    /* Thumb circle */
    [data-testid="stSidebar"] [data-baseweb="slider"] [role="slider"] {{
        background: {VIKINGS_GOLD} !important;
        border-color: {VIKINGS_GOLD} !important;
        box-shadow: 0 0 0 4px rgba(255,198,47,0.22) !important;
        width: 18px !important;
        height: 18px !important;
    }}
    /* Filled track */
    [data-testid="stSidebar"] [data-baseweb="slider"] > div > div:nth-child(2) {{
        background: {VIKINGS_GOLD} !important;
    }}
    /* Empty track */
    [data-testid="stSidebar"] [data-baseweb="slider"] > div > div:first-child {{
        background: rgba(255,255,255,0.20) !important;
        height: 4px !important;
        border-radius: 4px !important;
    }}

    /* Tick labels below slider (min / max) */
    [data-testid="stSidebar"] [data-testid="stTickBar"] span,
    [data-testid="stSidebar"] [data-testid="stTickBar"] div {{
        color: rgba(255,255,255,0.60) !important;
        background: transparent !important;
        font-size: 0.70rem !important;
        font-weight: 500 !important;
    }}
    /* Current-value label above thumb */
    [data-testid="stSidebar"] [data-baseweb="tooltip"] > div {{
        background: {VIKINGS_PURPLE} !important;
        border-radius: 5px !important;
        padding: 2px 8px !important;
    }}
    [data-testid="stSidebar"] [data-baseweb="tooltip"] span,
    [data-testid="stSidebar"] [data-baseweb="tooltip"] div {{
        color: white !important;
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        background: transparent !important;
    }}

    /* select_slider: kill the orange pill on extreme values */
    [data-testid="stSidebar"] [data-testid="stSlider"] li {{
        background: transparent !important;
        color: rgba(255,255,255,0.60) !important;
        font-size: 0.70rem !important;
    }}
    [data-testid="stSidebar"] [data-testid="stSlider"] li[aria-selected="true"],
    [data-testid="stSidebar"] [data-testid="stSlider"] li[data-selected="true"] {{
        background: transparent !important;
        color: {VIKINGS_GOLD} !important;
        font-weight: 700 !important;
    }}

    /* ═══════════════════════════════════════════════════════════
       TAB BAR
    ═══════════════════════════════════════════════════════════ */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 3px;
        background: #EDE8F8;
        border-radius: 10px;
        padding: 4px;
        border: 1px solid #DDD5F3;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 7px;
        padding: 7px 15px;
        font-weight: 600;
        font-size: 0.80rem;
        color: {VIKINGS_MID};
        background: transparent;
        border: none;
        transition: all 0.15s ease;
    }}
    .stTabs [aria-selected="true"] {{
        background: {VIKINGS_PURPLE} !important;
        color: white !important;
        box-shadow: 0 2px 6px rgba(79,38,131,0.25);
    }}

    /* ═══════════════════════════════════════════════════════════
       KPI CARD
    ═══════════════════════════════════════════════════════════ */
    .kpi-card {{
        background: #FFFFFF;
        border-left: 3px solid {VIKINGS_GOLD};
        border-radius: 8px;
        padding: 16px 18px 14px 18px;
        box-shadow: 0 1px 6px rgba(79,38,131,0.08);
        margin-bottom: 0;
        height: 100%;
    }}
    .kpi-label {{
        font-size: 0.68rem;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: {VIKINGS_MID};
        font-weight: 700;
        margin-bottom: 6px;
    }}
    .kpi-value {{
        font-size: 1.65rem;
        font-weight: 800;
        color: {VIKINGS_DARK};
        line-height: 1.1;
        letter-spacing: -0.5px;
    }}
    .kpi-delta {{
        font-size: 0.74rem;
        font-weight: 600;
        margin-top: 5px;
    }}
    .kpi-delta.pos {{ color: {SUCCESS_GREEN}; }}
    .kpi-delta.neg {{ color: {DANGER_RED}; }}
    .kpi-delta.neu {{ color: {VIKINGS_MID}; }}

    /* ═══════════════════════════════════════════════════════════
       SECTION HEADER
    ═══════════════════════════════════════════════════════════ */
    .section-header {{
        font-size: 0.78rem;
        font-weight: 700;
        color: {VIKINGS_PURPLE};
        border-bottom: 2px solid {VIKINGS_GOLD};
        padding-bottom: 5px;
        margin: 22px 0 14px 0;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }}

    /* ═══════════════════════════════════════════════════════════
       APP HEADER
    ═══════════════════════════════════════════════════════════ */
    .app-header {{
        background: linear-gradient(115deg, {VIKINGS_DARK} 0%, {VIKINGS_PURPLE} 55%, {VIKINGS_MID} 100%);
        border-radius: 10px;
        padding: 20px 28px 18px 28px;
        margin-bottom: 18px;
        color: white;
        position: relative;
        overflow: hidden;
    }}
    .app-header::after {{
        content: '';
        position: absolute;
        right: -20px; top: -20px;
        width: 160px; height: 160px;
        background: radial-gradient(circle, rgba(255,198,47,0.18) 0%, transparent 70%);
        border-radius: 50%;
    }}
    .app-header h1 {{
        font-size: 1.55rem;
        font-weight: 800;
        margin: 0 0 3px 0;
        color: white;
        letter-spacing: -0.3px;
    }}
    .app-header p {{
        font-size: 0.82rem;
        margin: 0;
        color: rgba(255,255,255,0.78);
        font-weight: 400;
    }}
    .app-header .gold-pill {{
        display: inline-block;
        background: {VIKINGS_GOLD};
        color: {VIKINGS_DARK};
        font-size: 0.62rem;
        font-weight: 800;
        padding: 2px 10px;
        border-radius: 20px;
        letter-spacing: 0.06em;
        margin-left: 10px;
        vertical-align: middle;
        text-transform: uppercase;
    }}

    /* ═══════════════════════════════════════════════════════════
       RISK BADGE
    ═══════════════════════════════════════════════════════════ */
    .risk-badge {{
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 0.80rem;
        font-weight: 700;
        letter-spacing: 0.03em;
    }}
    .risk-high  {{ background:#fde9e5; color:#C0392B; border:1px solid #f5c6c0; }}
    .risk-medio {{ background:#fef9e7; color:#9A7D0A; border:1px solid #f9e79f; }}
    .risk-bajo  {{ background:#e9f7ef; color:#1E8449; border:1px solid #a9dfbf; }}

    /* ═══════════════════════════════════════════════════════════
       ALERT BOX
    ═══════════════════════════════════════════════════════════ */
    .alert-box {{
        border-left: 3px solid {VIKINGS_GOLD};
        background: #FFFBF0;
        border-radius: 0 6px 6px 0;
        padding: 10px 14px;
        margin: 5px 0;
        font-size: 0.81rem;
        line-height: 1.5;
        color: {VIKINGS_DARK};
    }}
    .alert-box.high {{
        border-color: {DANGER_RED};
        background: #FEF5F4;
    }}
    .alert-box.low {{
        border-color: {SUCCESS_GREEN};
        background: #F0FBF5;
    }}

    /* ═══════════════════════════════════════════════════════════
       GUIDE / EXPLAINER CARDS
    ═══════════════════════════════════════════════════════════ */
    .guide-card {{
        background: #FFFFFF;
        border: 1px solid #E8E0F5;
        border-top: 3px solid {VIKINGS_PURPLE};
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 12px;
        height: 100%;
    }}
    .guide-card h4 {{
        color: {VIKINGS_PURPLE};
        font-size: 0.78rem;
        font-weight: 700;
        margin: 0 0 7px 0;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }}
    .guide-card p, .guide-card li {{
        color: #3D2A5A;
        font-size: 0.80rem;
        line-height: 1.6;
        margin: 0;
    }}

    /* ═══════════════════════════════════════════════════════════
       QUALITY THRESHOLD CLASSES
    ═══════════════════════════════════════════════════════════ */
    .thresh-excellent {{ color:#1E8449; font-weight:700; }}
    .thresh-good      {{ color:{VIKINGS_PURPLE}; font-weight:600; }}
    .thresh-warn      {{ color:#9A7D0A; font-weight:600; }}
    .thresh-bad       {{ color:#C0392B; font-weight:600; }}

    /* ═══════════════════════════════════════════════════════════
       CHAT BUBBLES
    ═══════════════════════════════════════════════════════════ */
    .chat-user {{
        background: #F0EBF8;
        border-radius: 12px 12px 4px 12px;
        padding: 10px 14px;
        margin: 8px 50px 8px 0;
        font-size: 0.85rem;
        color: {VIKINGS_DARK};
        line-height: 1.5;
    }}
    .chat-assistant {{
        background: #FFFFFF;
        border-left: 3px solid {VIKINGS_GOLD};
        border-radius: 0 10px 10px 10px;
        padding: 12px 16px;
        margin: 8px 0 8px 50px;
        font-size: 0.85rem;
        color: {VIKINGS_DARK};
        line-height: 1.6;
        box-shadow: 0 1px 4px rgba(79,38,131,0.07);
    }}

    /* ═══════════════════════════════════════════════════════════
       TIME FILTER INFO BAR
    ═══════════════════════════════════════════════════════════ */
    .time-filter-bar {{
        background: #F0EBF8;
        border: 1px solid #DDD5F3;
        border-radius: 6px;
        padding: 6px 12px;
        margin-bottom: 10px;
        font-size: 0.76rem;
        color: {VIKINGS_MID};
        display: inline-block;
    }}

    /* ═══════════════════════════════════════════════════════════
       METRIC OVERRIDE
    ═══════════════════════════════════════════════════════════ */
    [data-testid="metric-container"] {{
        background: white;
        border-radius: 8px;
        padding: 14px !important;
        box-shadow: 0 1px 5px rgba(79,38,131,0.07);
        border: 1px solid #EDE8F8;
    }}

    /* ═══════════════════════════════════════════════════════════
       DATA TABLES
    ═══════════════════════════════════════════════════════════ */
    [data-testid="stDataFrame"] {{
        border: 1px solid #E8E0F5;
        border-radius: 8px;
        overflow: hidden;
    }}

    /* ═══════════════════════════════════════════════════════════
       EXPANDER
    ═══════════════════════════════════════════════════════════ */
    [data-testid="stExpander"] {{
        border: 1px solid #E2D9F3 !important;
        border-radius: 8px !important;
    }}
    [data-testid="stExpander"] summary {{
        font-size: 0.82rem;
        font-weight: 600;
        color: {VIKINGS_PURPLE};
    }}
    </style>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# UI component helpers
# ---------------------------------------------------------------------------

def render_header() -> None:
    st.markdown(f"""
    <div class="app-header">
        <h1>Plastic Futures <span class="gold-pill">Decision Hub</span></h1>
        <p>{APP_SUBTITLE} &nbsp;·&nbsp; Análisis de mercado · Previsión de precios · Soporte a decisiones de compra</p>
    </div>
    """, unsafe_allow_html=True)


def kpi_card(label: str, value: str, delta: str = "", delta_dir: str = "neu") -> None:
    delta_html = f'<div class="kpi-delta {delta_dir}">{delta}</div>' if delta else ""
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def section_header(text: str) -> None:
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)


def risk_badge(level: str) -> None:
    css   = {"Alto": "risk-high", "Medio": "risk-medio", "Bajo": "risk-bajo"}.get(level, "risk-bajo")
    icons = {"Alto": "●", "Medio": "●", "Bajo": "●"}
    colors= {"Alto": "#C0392B", "Medio": "#9A7D0A", "Bajo": "#1E8449"}
    st.markdown(
        f'<span class="risk-badge {css}">'
        f'<span style="color:{colors.get(level,"")}">●</span> Riesgo {level}</span>',
        unsafe_allow_html=True,
    )


def alert_box(msg: str, level: str = "medium") -> None:
    css = {"high": "high", "low": "low"}.get(level, "")
    st.markdown(f'<div class="alert-box {css}">{msg}</div>', unsafe_allow_html=True)


def guide_card(title: str, body: str) -> None:
    st.markdown(
        f'<div class="guide-card"><h4>{title}</h4><p>{body}</p></div>',
        unsafe_allow_html=True,
    )


def time_filter_info(from_year: int, granularity: str, period_label: str = "") -> None:
    extra = f" &nbsp;·&nbsp; {period_label}" if period_label and period_label != "Todos" else ""
    st.markdown(
        f'<span class="time-filter-bar">📅 Desde <strong>{from_year}</strong>'
        f' &nbsp;·&nbsp; <strong>{granularity}</strong>{extra}</span>',
        unsafe_allow_html=True,
    )


def render_sidebar_brand() -> None:
    st.markdown(f"""
    <div style="background:linear-gradient(115deg,{VIKINGS_PURPLE},{VIKINGS_MID});
        border-radius:8px; padding:16px 18px 14px; margin-bottom:18px;
        border:1px solid rgba(255,198,47,0.35);
        box-shadow:0 2px 12px rgba(0,0,0,0.30);">
        <div style="font-size:1.3rem; font-weight:800; color:white; letter-spacing:-0.3px;">
            Plastic Futures
        </div>
        <div style="font-size:0.7rem; color:{VIKINGS_GOLD}; letter-spacing:0.08em;
            text-transform:uppercase; margin-top:4px; font-weight:600;">
            Decision Hub &nbsp;·&nbsp; Market Intelligence
        </div>
    </div>
    """, unsafe_allow_html=True)
