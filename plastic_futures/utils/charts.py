"""
Plotly chart factory — Vikings palette, executive-quality aesthetics.
All charts follow a consistent visual language:
  · White plot area, very-light grid, no chart junk
  · Readable axis labels and hover tooltips
  · Consistent brand colours
"""

from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config.settings import (
    REPSOL_ORANGE, REPSOL_MAGENTA, REPSOL_BLUE, DARK_NAVY, IVORY,
    SUCCESS_GREEN, WARNING_AMBER, DANGER_RED, MID_GRAY,
    BAND_COLORS, FORECAST_LINE_COLOR, HISTORY_LINE_COLOR,
    COLORSCALE, COLORSCALE_DIVERGING,
    VIKINGS_PURPLE, VIKINGS_GOLD, VIKINGS_MID, VIKINGS_DARK,
)

_PRODUCT_COLORS = {
    "HDPE": VIKINGS_PURPLE,
    "LDPE": "#7B5EA7",
    "PP":   VIKINGS_GOLD,
    "PVC":  SUCCESS_GREEN,
    "PET":  "#E17055",
    "PS":   MID_GRAY,
}

_SCENARIO_COLORS = {
    "Base":                VIKINGS_PURPLE,
    "Alcista (Bull)":      SUCCESS_GREEN,
    "Bajista (Bear)":      DANGER_RED,
    "Crisis energética":   "#E17055",
    "Demanda débil":       MID_GRAY,
}

_GRID_COLOR    = "#F0EBF8"
_AXIS_COLOR    = "#D5CCE8"
_FONT_COLOR    = VIKINGS_DARK
_PLOT_BG       = "#FFFFFF"
_PAPER_BG      = "#F8F6FF"
_FONT_FAMILY   = "'Segoe UI', 'Inter', Arial, sans-serif"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _base_layout(title: str = "", height: int = 400) -> dict:
    return dict(
        title=dict(
            text=title,
            font=dict(size=13, color=_FONT_COLOR, family=_FONT_FAMILY),
            x=0, xanchor="left", pad=dict(l=4),
        ),
        height=height,
        paper_bgcolor=_PAPER_BG,
        plot_bgcolor=_PLOT_BG,
        margin=dict(l=48, r=20, t=42, b=44),
        font=dict(family=_FONT_FAMILY, size=11, color=_FONT_COLOR),
        xaxis=dict(
            gridcolor=_GRID_COLOR, linecolor=_AXIS_COLOR, linewidth=1,
            tickfont=dict(size=10), showgrid=True,
            zeroline=False,
        ),
        yaxis=dict(
            gridcolor=_GRID_COLOR, linecolor=_AXIS_COLOR, linewidth=1,
            tickfont=dict(size=10), showgrid=True,
            zeroline=False,
        ),
    )


# ---------------------------------------------------------------------------
# Time filter helper
# ---------------------------------------------------------------------------

def apply_time_filter(
    series: pd.Series,
    from_year: int = 2022,
    granularity: str = "Mensual",
) -> pd.Series:
    s = series[series.index.year >= from_year].copy()
    if s.empty:
        return s
    if granularity == "Trimestral":
        s = s.resample("QS").mean()
    elif granularity == "Anual":
        s = s.resample("YS").mean()
    return s


def apply_time_filter_df(
    df: pd.DataFrame,
    date_col: str = "date",
    from_year: int = 2022,
    granularity: str = "Mensual",
) -> pd.DataFrame:
    df = df[df[date_col].dt.year >= from_year].copy()
    if granularity != "Mensual":
        freq = "QS" if granularity == "Trimestral" else "YS"
        numeric_cols = df.select_dtypes("number").columns.tolist()
        df = (
            df.set_index(date_col)[numeric_cols]
            .resample(freq).mean()
            .reset_index()
            .rename(columns={"index": date_col})
        )
    return df


# ---------------------------------------------------------------------------
# Fan Chart
# ---------------------------------------------------------------------------

def fan_chart(
    history: pd.Series,
    forecast: pd.DataFrame,
    title: str = "Evolución y previsión de precio",
    unit: str = "€/ton",
    product: str = "",
    from_year: int = 2022,
    granularity: str = "Mensual",
    active_months: list[int] | None = None,
) -> go.Figure:
    history = apply_time_filter(history, from_year, granularity)
    if active_months:
        history = history[history.index.month.isin(active_months)]

    fig = go.Figure()

    # Confidence bands (outermost to innermost)
    band_defs = [
        ("q_5",  "q_95", "Zona posible (95%)",      _hex_to_rgba(VIKINGS_PURPLE, 0.07)),
        ("q_10", "q_90", "Zona probable (80%)",      _hex_to_rgba(VIKINGS_GOLD,   0.14)),
        ("q_25", "q_75", "Zona más probable (50%)",  _hex_to_rgba(VIKINGS_PURPLE, 0.18)),
    ]
    for lo, hi, name, fill in band_defs:
        if lo in forecast.columns and hi in forecast.columns:
            fig.add_trace(go.Scatter(
                x=list(forecast.index) + list(forecast.index[::-1]),
                y=list(forecast[hi])   + list(forecast[lo][::-1]),
                fill="toself", fillcolor=fill,
                line=dict(width=0), name=name, showlegend=True,
                hoverinfo="skip",
            ))

    # Historical line
    fig.add_trace(go.Scatter(
        x=history.index, y=history.values,
        mode="lines", name="Precio histórico",
        line=dict(color=VIKINGS_PURPLE, width=2.2),
        hovertemplate="<b>%{x|%b %Y}</b><br>Precio: <b>%{y:,.0f} €/t</b><extra></extra>",
    ))

    # Central forecast
    med_col = "q_50" if "q_50" in forecast.columns else "mean"
    fig.add_trace(go.Scatter(
        x=forecast.index, y=forecast[med_col],
        mode="lines", name="Previsión central",
        line=dict(color=VIKINGS_GOLD, width=2.2, dash="dash"),
        hovertemplate="<b>%{x|%b %Y}</b><br>Previsión: <b>%{y:,.0f} €/t</b><extra></extra>",
    ))

    # Today divider
    if len(history) > 0:
        last_date = history.index[-1]
        fig.add_vline(x=last_date, line_dash="dot", line_color=_AXIS_COLOR, line_width=1.5)
        fig.add_annotation(
            x=last_date, y=history.iloc[-1],
            text="  Hoy", showarrow=False,
            font=dict(size=9, color=MID_GRAY),
            xanchor="left",
        )

    layout = _base_layout(title, height=450)
    layout["yaxis"]["title"] = dict(text=unit, font=dict(size=11, color=MID_GRAY))
    layout["legend"] = dict(
        orientation="h",
        yanchor="top", y=-0.13,
        xanchor="center", x=0.5,
        font=dict(size=12, color=VIKINGS_DARK),
        bgcolor="rgba(255,255,255,0.90)",
        bordercolor="#E8E0F5", borderwidth=1,
    )
    layout["margin"] = dict(l=52, r=20, t=40, b=80)
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# Multi-product lines
# ---------------------------------------------------------------------------

def multi_product_lines(
    price_df: pd.DataFrame,
    products: list[str],
    region: str,
    title: str = "Evolución de precios por producto",
    from_year: int = 2022,
    granularity: str = "Mensual",
    active_months: list[int] | None = None,
) -> go.Figure:
    fig = go.Figure()
    for prod in products:
        subset = price_df[(price_df["product"] == prod) & (price_df["region"] == region)]
        if subset.empty:
            continue
        series = subset.groupby("date")["market_price"].mean().sort_index()
        series = apply_time_filter(series, from_year, granularity)
        if active_months:
            series = series[series.index.month.isin(active_months)]
        if series.empty:
            continue
        mode = "lines+markers" if granularity == "Anual" else "lines"
        fig.add_trace(go.Scatter(
            x=series.index, y=series.values,
            mode=mode, name=prod,
            line=dict(color=_PRODUCT_COLORS.get(prod, VIKINGS_MID), width=2),
            marker=dict(size=5),
            hovertemplate=f"<b>{prod}</b> · %{{x|%b %Y}}<br>Precio: <b>%{{y:,.0f}} €/t</b><extra></extra>",
        ))
    layout = _base_layout(title, height=400)
    layout["yaxis"]["title"] = dict(text="€/ton", font=dict(size=11, color=MID_GRAY))
    # Legend below chart — avoids any overlap with the title
    layout["legend"] = dict(
        orientation="h",
        yanchor="top", y=-0.14,
        xanchor="center", x=0.5,
        font=dict(size=13, color=VIKINGS_DARK),
        bgcolor="rgba(255,255,255,0.90)",
        bordercolor="#E8E0F5", borderwidth=1,
    )
    layout["margin"] = dict(l=52, r=20, t=36, b=72)
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# Heatmap
# ---------------------------------------------------------------------------

def heatmap_chart(
    matrix: pd.DataFrame,
    title: str = "",
    colorscale: list | None = None,
    zmin: float | None = None,
    zmax: float | None = None,
    text_format: str = ".0f",
) -> go.Figure:
    if colorscale is None:
        colorscale = COLORSCALE

    text = matrix.map(lambda v: f"{v:{text_format}}" if pd.notna(v) else "")

    # Adaptive text color: white on dark cells, dark on light cells
    z_lo = zmin if zmin is not None else float(matrix.min().min())
    z_hi = zmax if zmax is not None else float(matrix.max().max())
    z_range = z_hi - z_lo if z_hi != z_lo else 1
    text_colors = matrix.map(
        lambda v: "white" if pd.notna(v) and (v - z_lo) / z_range > 0.55 else "#2D1154"
    )

    fig = go.Figure(go.Heatmap(
        z=matrix.values,
        x=matrix.columns.tolist(),
        y=matrix.index.tolist(),
        colorscale=colorscale,
        zmin=zmin, zmax=zmax,
        text=text.values,
        texttemplate="%{text}",
        textfont=dict(size=9, color="black"),
        hovertemplate="%{y} — %{x}<br>Riesgo: <b>%{z:.0f} / 100</b><extra></extra>",
        colorbar=dict(
            thickness=14, tickfont=dict(size=10), outlinewidth=0,
            tickvals=[0, 33, 66, 100],
            ticktext=["0 · Bajo", "33", "66 · Alto", "100"],
        ),
    ))
    layout = _base_layout(title, height=360)
    layout.pop("xaxis", None)
    layout.pop("yaxis", None)
    layout["legend"] = dict(bgcolor="rgba(0,0,0,0)")
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# Scenario comparison
# ---------------------------------------------------------------------------

def scenario_chart(
    history: pd.Series,
    scenario_dfs: dict[str, pd.DataFrame],
    title: str = "Comparación de escenarios de precio",
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=history.index, y=history.values,
        mode="lines", name="Histórico",
        line=dict(color=VIKINGS_PURPLE, width=2.2),
        hovertemplate="<b>%{x|%b %Y}</b><br>Precio: <b>%{y:,.0f} €/t</b><extra></extra>",
    ))
    for sc_name, df in scenario_dfs.items():
        color = _SCENARIO_COLORS.get(sc_name, MID_GRAY)
        if "lo80" in df.columns and "hi80" in df.columns:
            fig.add_trace(go.Scatter(
                x=list(df.index) + list(df.index[::-1]),
                y=list(df["hi80"]) + list(df["lo80"][::-1]),
                fill="toself", fillcolor=_hex_to_rgba(color, 0.08),
                line=dict(width=0), showlegend=False, hoverinfo="skip",
            ))
        fig.add_trace(go.Scatter(
            x=df.index, y=df["price"], mode="lines", name=sc_name,
            line=dict(color=color, width=1.8, dash="dash" if sc_name == "Base" else "solid"),
            hovertemplate=f"<b>{sc_name}</b> · %{{x|%b %Y}}<br>%{{y:,.0f}} €/t<extra></extra>",
        ))
    if len(history) > 0:
        last_date = history.index[-1]
        fig.add_vline(x=last_date, line_dash="dot", line_color=_AXIS_COLOR, line_width=1.5)
        fig.add_annotation(
            x=last_date, y=history.iloc[-1],
            text="  Hoy", showarrow=False,
            font=dict(size=9, color=MID_GRAY), xanchor="left",
        )
    layout = _base_layout(title, height=450)
    layout["yaxis"]["title"] = dict(text="€/ton", font=dict(size=11, color=MID_GRAY))
    # Legend below chart — avoids title overlap
    layout["legend"] = dict(
        orientation="h",
        yanchor="top", y=-0.13,
        xanchor="center", x=0.5,
        font=dict(size=12, color=VIKINGS_DARK),
        bgcolor="rgba(255,255,255,0.90)",
        bordercolor="#E8E0F5", borderwidth=1,
    )
    layout["margin"] = dict(l=52, r=20, t=40, b=80)
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# Risk gauge
# ---------------------------------------------------------------------------

def risk_gauge(score: float, title: str = "Índice de riesgo de compra") -> go.Figure:
    color = DANGER_RED if score >= 67 else (WARNING_AMBER if score >= 34 else SUCCESS_GREEN)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number=dict(font=dict(size=38, color=_FONT_COLOR, family=_FONT_FAMILY), suffix=" / 100"),
        title=dict(text=title, font=dict(size=12, color=MID_GRAY, family=_FONT_FAMILY)),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1, tickcolor=_AXIS_COLOR,
                      tickvals=[0, 33, 67, 100], ticktext=["0", "33", "67", "100"],
                      tickfont=dict(size=9)),
            bar=dict(color=color, thickness=0.28),
            bgcolor=_PLOT_BG,
            borderwidth=0,
            steps=[
                {"range": [0,  33], "color": "#EBF9F4"},
                {"range": [33, 67], "color": "#FEFAE6"},
                {"range": [67, 100], "color": "#FEF0ED"},
            ],
        ),
    ))
    fig.update_layout(
        paper_bgcolor=_PAPER_BG, height=240,
        margin=dict(l=16, r=16, t=44, b=8),
        font=dict(family=_FONT_FAMILY),
    )
    return fig


# ---------------------------------------------------------------------------
# Risk radar
# ---------------------------------------------------------------------------

def risk_radar(risk_scores: dict) -> go.Figure:
    categories = ["Volatilidad", "Tendencia", "Incertidumbre", "Fiabilidad\ndel modelo"]
    values = [
        risk_scores.get("volatility",       50),
        risk_scores.get("trend",            50),
        risk_scores.get("uncertainty",      50),
        100 - risk_scores.get("model_confidence", 50),
    ]
    v_c = values + [values[0]]
    c_c = categories + [categories[0]]
    fig = go.Figure(go.Scatterpolar(
        r=v_c, theta=c_c,
        fill="toself", fillcolor=_hex_to_rgba(VIKINGS_PURPLE, 0.15),
        line=dict(color=VIKINGS_PURPLE, width=2),
        name="Riesgo actual",
        hovertemplate="%{theta}: <b>%{r:.0f} / 100</b><extra></extra>",
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100],
                            tickfont=dict(size=8, color=MID_GRAY),
                            gridcolor=_GRID_COLOR, linecolor=_AXIS_COLOR),
            angularaxis=dict(tickfont=dict(size=10, color=_FONT_COLOR), linecolor=_AXIS_COLOR),
            bgcolor=_PLOT_BG,
        ),
        showlegend=False,
        paper_bgcolor=_PAPER_BG,
        height=290,
        margin=dict(l=40, r=40, t=16, b=16),
        font=dict(family=_FONT_FAMILY),
    )
    return fig


# ---------------------------------------------------------------------------
# Monte Carlo
# ---------------------------------------------------------------------------

def monte_carlo_chart(
    current_price: float,
    mc_summary: pd.DataFrame,
    history: pd.Series,
    title: str = "Simulación de escenarios probabilísticos (Monte Carlo)",
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=history.index, y=history.values,
        mode="lines", name="Histórico",
        line=dict(color=VIKINGS_PURPLE, width=2),
        hovertemplate="<b>%{x|%b %Y}</b><br>%{y:,.0f} €/t<extra></extra>",
    ))
    last_date    = history.index[-1]
    future_dates = pd.date_range(last_date + pd.offsets.MonthBegin(1),
                                 periods=len(mc_summary), freq="MS")
    for lo_col, hi_col, band_name, fillcolor in [
        ("q5",  "q95", "Zona posible (90%)",    _hex_to_rgba(VIKINGS_PURPLE, 0.08)),
        ("q25", "q75", "Zona probable (50%)",   _hex_to_rgba(VIKINGS_GOLD,   0.18)),
    ]:
        fig.add_trace(go.Scatter(
            x=list(future_dates) + list(future_dates[::-1]),
            y=list(mc_summary[hi_col]) + list(mc_summary[lo_col][::-1]),
            fill="toself", fillcolor=fillcolor,
            line=dict(width=0), name=band_name,
            hoverinfo="skip",
        ))
    fig.add_trace(go.Scatter(
        x=future_dates, y=mc_summary["q50"],
        mode="lines", name="Precio mediano simulado",
        line=dict(color=VIKINGS_GOLD, width=2.2, dash="dash"),
        hovertemplate="<b>%{x|%b %Y}</b><br>Mediana: <b>%{y:,.0f} €/t</b><extra></extra>",
    ))
    fig.add_vline(x=last_date, line_dash="dot", line_color=_AXIS_COLOR, line_width=1.5)
    layout = _base_layout(title, height=450)
    layout["yaxis"]["title"] = dict(text="€/ton", font=dict(size=11, color=MID_GRAY))
    layout["legend"] = dict(
        orientation="h",
        yanchor="top", y=-0.13,
        xanchor="center", x=0.5,
        font=dict(size=12, color=VIKINGS_DARK),
        bgcolor="rgba(255,255,255,0.90)",
        bordercolor="#E8E0F5", borderwidth=1,
    )
    layout["margin"] = dict(l=52, r=20, t=40, b=80)
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# Tornado / Sensitivity
# ---------------------------------------------------------------------------

def tornado_chart(sensitivity_df: pd.DataFrame, title: str = "Sensibilidad del precio a factores externos") -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=sensitivity_df["driver"], x=sensitivity_df["impact_low"],
        orientation="h", name="Escenario favorable",
        marker_color=SUCCESS_GREEN, marker_line_width=0,
        hovertemplate="%{y}<br>Impacto: <b>%{x:.1f} €/t</b><extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=sensitivity_df["driver"], x=sensitivity_df["impact_high"],
        orientation="h", name="Escenario adverso",
        marker_color=DANGER_RED, marker_line_width=0,
        hovertemplate="%{y}<br>Impacto: <b>+%{x:.1f} €/t</b><extra></extra>",
    ))
    layout = _base_layout(title, height=370)
    layout["barmode"] = "overlay"
    layout["xaxis"]["title"] = dict(text="Variación en precio (€/ton)", font=dict(size=10, color=MID_GRAY))
    layout["bargap"] = 0.28
    layout["legend"] = dict(
        orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
        font=dict(size=10), bgcolor="rgba(0,0,0,0)",
    )
    fig.update_layout(**layout)
    fig.add_vline(x=0, line_color=_AXIS_COLOR, line_width=1.5)
    return fig


# ---------------------------------------------------------------------------
# Backtesting
# ---------------------------------------------------------------------------

def backtest_chart(backtest_df: pd.DataFrame, title: str = "Precisión histórica del modelo de previsión") -> go.Figure:
    # Use real dates as labels (e.g. "Ene 2023") instead of fold numbers
    if "date_start" in backtest_df.columns:
        labels = backtest_df["date_start"].dt.strftime("%b %Y").tolist()
    else:
        labels = backtest_df["fold"].astype(str).tolist()

    bar_colors = [
        SUCCESS_GREEN if m < 3 else (WARNING_AMBER if m < 7 else DANGER_RED)
        for m in backtest_df["mape_ens"]
    ]

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            "¿Cuánto se equivocó el modelo? (% de error por período)",
            "Fiabilidad del modelo por período (%)",
        ),
        vertical_spacing=0.22,
        row_heights=[0.55, 0.45],
    )

    # --- Row 1: error bars + individual model lines ---
    fig.add_trace(go.Bar(
        x=labels, y=backtest_df["mape_ens"],
        marker_color=bar_colors, marker_line_width=0,
        name="Error modelo combinado",
        text=[f"{v:.1f}%" for v in backtest_df["mape_ens"]],
        textposition="outside", textfont=dict(size=11, color=_FONT_COLOR),
        hovertemplate="<b>%{x}</b><br>Error combinado: <b>%{y:.1f}%</b><extra></extra>",
    ), row=1, col=1)

    for col_name, color, label in [
        ("mape_hw", VIKINGS_PURPLE, "Tend. estacional"),
        ("mape_lf", VIKINGS_GOLD,   "Modelo lineal"),
        ("mape_rf", MID_GRAY,       "Modelo predictivo"),
    ]:
        fig.add_trace(go.Scatter(
            x=labels, y=backtest_df[col_name],
            mode="lines+markers", name=label,
            line=dict(color=color, width=2),
            marker=dict(size=6, color=color),
            hovertemplate=f"<b>%{{x}}</b><br>{label}: <b>%{{y:.1f}}%</b><extra></extra>",
        ), row=1, col=1)

    # Reference lines
    for threshold, color, dash in [(3, SUCCESS_GREEN, "dot"), (7, DANGER_RED, "dot")]:
        fig.add_hline(y=threshold, row=1, col=1,
                      line_color=color, line_dash=dash, line_width=1,
                      annotation_text=f"  {threshold}% {'excelente' if threshold==3 else 'límite'}",
                      annotation_font=dict(size=9, color=color))

    # --- Row 2: confidence bars ---
    conf_colors = [
        VIKINGS_PURPLE if v >= 80 else (VIKINGS_MID if v >= 60 else DANGER_RED)
        for v in backtest_df["confidence"]
    ]
    fig.add_trace(go.Bar(
        x=labels, y=backtest_df["confidence"],
        marker_color=conf_colors, marker_line_width=0,
        name="Fiabilidad",
        text=[f"{v:.0f}%" for v in backtest_df["confidence"]],
        textposition="outside", textfont=dict(size=11, color=_FONT_COLOR),
        hovertemplate="<b>%{x}</b><br>Fiabilidad: <b>%{y:.0f}%</b><extra></extra>",
    ), row=2, col=1)
    fig.add_hline(y=70, row=2, col=1,
                  line_color=SUCCESS_GREEN, line_dash="dot", line_width=1.5,
                  annotation_text="  70% mínimo recomendado",
                  annotation_font=dict(size=9, color=SUCCESS_GREEN))

    layout = _base_layout(title, height=520)
    layout["showlegend"] = True
    layout["legend"] = dict(
        orientation="h",
        yanchor="top", y=-0.08,
        xanchor="center", x=0.5,
        font=dict(size=12, color=VIKINGS_DARK),
        bgcolor="rgba(255,255,255,0.90)",
        bordercolor="#E8E0F5", borderwidth=1,
    )
    layout["margin"] = dict(l=52, r=20, t=50, b=80)
    fig.update_layout(**layout)
    fig.update_yaxes(title_text="Error (%)", title_font=dict(size=10, color=MID_GRAY), row=1, col=1)
    fig.update_yaxes(title_text="Fiabilidad (%)", title_font=dict(size=10, color=MID_GRAY),
                     range=[0, 115], row=2, col=1)
    return fig


# ---------------------------------------------------------------------------
# Correlation heatmap
# ---------------------------------------------------------------------------

def correlation_heatmap(corr_matrix: pd.DataFrame, title: str = "Correlaciones entre variables") -> go.Figure:
    fig = go.Figure(go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns.tolist(),
        y=corr_matrix.index.tolist(),
        colorscale=COLORSCALE_DIVERGING,
        zmin=-1, zmax=1,
        text=corr_matrix.round(2).astype(str).values,
        texttemplate="%{text}",
        textfont=dict(size=10),
        colorbar=dict(thickness=10, tickfont=dict(size=9), outlinewidth=0),
        hovertemplate="%{y} vs %{x}<br>Correlación: <b>%{z:.2f}</b><extra></extra>",
    ))
    layout = _base_layout(title, height=370)
    layout.pop("xaxis", None)
    layout.pop("yaxis", None)
    layout["legend"] = dict(bgcolor="rgba(0,0,0,0)")
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# Feature importance
# ---------------------------------------------------------------------------

def feature_importance_chart(importances: dict[str, float], title: str = "Variables más influyentes en el modelo") -> go.Figure:
    items  = sorted(importances.items(), key=lambda x: x[1], reverse=False)
    labels = [i[0] for i in items]
    values = [i[1] * 100 for i in items]
    pcts   = np.array(values)
    colors = [VIKINGS_PURPLE if v > np.percentile(pcts, 66)
              else (VIKINGS_MID if v > np.percentile(pcts, 33) else MID_GRAY)
              for v in values]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker_color=colors, marker_line_width=0,
        text=[f"{v:.1f}%" for v in values], textposition="outside",
        textfont=dict(size=10),
        hovertemplate="%{y}: <b>%{x:.1f}%</b><extra></extra>",
    ))
    layout = _base_layout(title, height=max(280, len(labels) * 30))
    layout["xaxis"]["title"] = dict(text="Importancia (%)", font=dict(size=10, color=MID_GRAY))
    layout["legend"] = dict(bgcolor="rgba(0,0,0,0)")
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# Buy now vs wait
# ---------------------------------------------------------------------------

def buy_vs_wait_chart(buy_wait_df: pd.DataFrame, title: str = "Coste de compra: Hoy vs Esperar") -> go.Figure:
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        subplot_titles=("Coste total esperado (€)", "Ahorro estimado por esperar (€)"),
        vertical_spacing=0.14, row_heights=[0.55, 0.45],
    )
    cost_now = buy_wait_df["cost_if_buy_now"].iloc[0]
    fig.add_trace(go.Scatter(
        x=buy_wait_df.index,
        y=[cost_now] * len(buy_wait_df),
        mode="lines", name="Comprar hoy",
        line=dict(color=VIKINGS_PURPLE, width=2, dash="dash"),
        hovertemplate="Comprar hoy: <b>%{y:,.0f} €</b><extra></extra>",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=buy_wait_df.index, y=buy_wait_df["cost_if_wait"],
        mode="lines+markers", name="Esperar",
        line=dict(color=VIKINGS_GOLD, width=2),
        marker=dict(size=5, color=VIKINGS_GOLD),
        hovertemplate="%{x|%b %Y}<br>Coste si espera: <b>%{y:,.0f} €</b><extra></extra>",
    ), row=1, col=1)
    bar_colors = [SUCCESS_GREEN if s > 0 else DANGER_RED for s in buy_wait_df["expected_savings"]]
    fig.add_trace(go.Bar(
        x=buy_wait_df.index, y=buy_wait_df["expected_savings"],
        marker_color=bar_colors, marker_line_width=0, name="Ahorro si espera",
        hovertemplate="%{x|%b %Y}<br>Ahorro: <b>%{y:,.0f} €</b><extra></extra>",
    ), row=2, col=1)
    fig.add_hline(y=0, row=2, col=1, line_dash="dot", line_color=_AXIS_COLOR, line_width=1)
    layout = _base_layout(title, height=430)
    layout["showlegend"] = True
    layout["legend"] = dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
        font=dict(size=10), bgcolor="rgba(0,0,0,0)",
    )
    fig.update_layout(**layout)
    return fig
