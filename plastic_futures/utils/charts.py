"""
Plotly chart factory functions, all styled with the Repsol brand palette.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from config.settings import (
    REPSOL_ORANGE, REPSOL_MAGENTA, REPSOL_BLUE, DARK_NAVY, IVORY,
    SUCCESS_GREEN, WARNING_AMBER, DANGER_RED, MID_GRAY,
    BAND_COLORS, FORECAST_LINE_COLOR, HISTORY_LINE_COLOR,
    COLORSCALE, COLORSCALE_DIVERGING,
)

_PRODUCT_COLORS = {
    "HDPE": REPSOL_ORANGE,
    "LDPE": REPSOL_MAGENTA,
    "PP":   REPSOL_BLUE,
    "PVC":  SUCCESS_GREEN,
    "PET":  WARNING_AMBER,
    "PS":   DANGER_RED,
}

_SCENARIO_COLORS = {
    "Base":                REPSOL_BLUE,
    "Alcista (Bull)":      SUCCESS_GREEN,
    "Bajista (Bear)":      DANGER_RED,
    "Crisis energética":   REPSOL_MAGENTA,
    "Demanda débil":       WARNING_AMBER,
}


def _hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
    """Convert #RRGGBB to rgba(r,g,b,alpha) string."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ---------------------------------------------------------------------------
# Time filter helper  (used by all temporal charts)
# ---------------------------------------------------------------------------

def apply_time_filter(
    series: pd.Series,
    from_year: int = 2022,
    granularity: str = "Mensual",
) -> pd.Series:
    """
    Filter a DatetimeIndex Series to start from `from_year` and
    optionally resample to quarterly or annual frequency.
    """
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
    """Apply time filter to a DataFrame that has a date column."""
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


def _base_layout(title: str = "", height: int = 420) -> dict:
    return dict(
        title=dict(text=title, font=dict(size=14, color=DARK_NAVY, family="Inter, sans-serif")),
        height=height,
        paper_bgcolor=IVORY,
        plot_bgcolor="white",
        margin=dict(l=40, r=20, t=45, b=40),
        font=dict(family="Inter, sans-serif", size=11, color=DARK_NAVY),
        xaxis=dict(gridcolor="#E8E8E0", linecolor="#D0D0C8"),
        yaxis=dict(gridcolor="#E8E8E0", linecolor="#D0D0C8"),
    )


# ---------------------------------------------------------------------------
# Fan Chart (history + forecast + confidence bands)
# ---------------------------------------------------------------------------

def fan_chart(
    history: pd.Series,
    forecast: pd.DataFrame,
    title: str = "Previsión de precio",
    unit: str = "€/ton",
    product: str = "",
    from_year: int = 2022,
    granularity: str = "Mensual",
    active_months: list[int] | None = None,
) -> go.Figure:
    """
    Fan chart combining historical prices with probabilistic forecast bands.
    forecast columns expected: q_5, q_10, q_25, q_50, q_75, q_90, q_95, mean
    """
    # Apply time filter to the displayed history window
    history = apply_time_filter(history, from_year, granularity)
    if active_months:
        history = history[history.index.month.isin(active_months)]

    fig = go.Figure()

    # ---- 95 % band ----
    if "q_5" in forecast.columns and "q_95" in forecast.columns:
        fig.add_trace(go.Scatter(
            x=list(forecast.index) + list(forecast.index[::-1]),
            y=list(forecast["q_95"]) + list(forecast["q_5"][::-1]),
            fill="toself", fillcolor=BAND_COLORS["95"],
            line=dict(width=0), name="IC 95 %", showlegend=True,
        ))

    # ---- 80 % band ----
    if "q_10" in forecast.columns and "q_90" in forecast.columns:
        fig.add_trace(go.Scatter(
            x=list(forecast.index) + list(forecast.index[::-1]),
            y=list(forecast["q_90"]) + list(forecast["q_10"][::-1]),
            fill="toself", fillcolor=BAND_COLORS["80"],
            line=dict(width=0), name="IC 80 %", showlegend=True,
        ))

    # ---- 50 % band ----
    if "q_25" in forecast.columns and "q_75" in forecast.columns:
        fig.add_trace(go.Scatter(
            x=list(forecast.index) + list(forecast.index[::-1]),
            y=list(forecast["q_75"]) + list(forecast["q_25"][::-1]),
            fill="toself", fillcolor=BAND_COLORS["50"],
            line=dict(width=0), name="IC 50 %", showlegend=True,
        ))

    # ---- Historical line ----
    fig.add_trace(go.Scatter(
        x=history.index, y=history.values,
        mode="lines", name="Histórico",
        line=dict(color=HISTORY_LINE_COLOR, width=2.5),
    ))

    # ---- Forecast median ----
    med_col = "q_50" if "q_50" in forecast.columns else "mean"
    fig.add_trace(go.Scatter(
        x=forecast.index, y=forecast[med_col],
        mode="lines", name="Previsión central",
        line=dict(color=FORECAST_LINE_COLOR, width=2.5, dash="dash"),
    ))

    # ---- Vertical line at last historical point ----
    last_date = history.index[-1]
    last_val  = history.iloc[-1]
    fig.add_vline(x=last_date, line_dash="dot", line_color=MID_GRAY, line_width=1.5)
    fig.add_annotation(
        x=last_date, y=last_val, text="Hoy",
        showarrow=True, arrowhead=2, arrowcolor=MID_GRAY,
        font=dict(size=10, color=MID_GRAY),
    )

    layout = _base_layout(title, height=430)
    layout["yaxis"]["title"] = unit
    layout["legend"] = dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)")
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# Multi-product price lines
# ---------------------------------------------------------------------------

def multi_product_lines(
    price_df: pd.DataFrame,
    products: list[str],
    region: str,
    title: str = "Histórico de precios",
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
            line=dict(color=_PRODUCT_COLORS.get(prod, REPSOL_BLUE), width=2),
            marker=dict(size=6),
        ))
    layout = _base_layout(title, height=380)
    layout["yaxis"]["title"] = "€/ton"
    layout["legend"] = dict(orientation="h", yanchor="bottom", y=1.02,
                            bgcolor="rgba(0,0,0,0)")
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# Heatmap (risk or price matrix)
# ---------------------------------------------------------------------------

def heatmap_chart(
    matrix: pd.DataFrame,
    title: str = "Mapa de calor",
    colorscale: list | None = None,
    zmin: float | None = None,
    zmax: float | None = None,
    text_format: str = ".0f",
) -> go.Figure:
    if colorscale is None:
        colorscale = COLORSCALE

    text = matrix.applymap(lambda v: f"{v:{text_format}}" if pd.notna(v) else "")

    fig = go.Figure(go.Heatmap(
        z=matrix.values,
        x=matrix.columns.tolist(),
        y=matrix.index.tolist(),
        colorscale=colorscale,
        zmin=zmin, zmax=zmax,
        text=text.values,
        texttemplate="%{text}",
        hovertemplate="%{y} – %{x}<br>Valor: %{z:.1f}<extra></extra>",
        colorbar=dict(thickness=12, tickfont=dict(size=10)),
    ))
    layout = _base_layout(title, height=380)
    layout.pop("xaxis", None)
    layout.pop("yaxis", None)
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# Scenario comparison chart
# ---------------------------------------------------------------------------

def scenario_chart(
    history: pd.Series,
    scenario_dfs: dict[str, pd.DataFrame],
    title: str = "Comparación de escenarios",
) -> go.Figure:
    fig = go.Figure()

    # History
    fig.add_trace(go.Scatter(
        x=history.index, y=history.values,
        mode="lines", name="Histórico",
        line=dict(color=HISTORY_LINE_COLOR, width=2.5),
    ))

    for sc_name, df in scenario_dfs.items():
        color = _SCENARIO_COLORS.get(sc_name, MID_GRAY)
        # Shaded band
        if "lo80" in df.columns and "hi80" in df.columns:
            fig.add_trace(go.Scatter(
                x=list(df.index) + list(df.index[::-1]),
                y=list(df["hi80"]) + list(df["lo80"][::-1]),
                fill="toself",
                fillcolor=_hex_to_rgba(color, 0.10),
                line=dict(width=0), showlegend=False,
                hoverinfo="skip",
            ))
        fig.add_trace(go.Scatter(
            x=df.index, y=df["price"],
            mode="lines", name=sc_name,
            line=dict(color=color, width=2, dash="dash" if sc_name == "Base" else "solid"),
        ))

    last_date = history.index[-1]
    fig.add_vline(x=last_date, line_dash="dot", line_color=MID_GRAY, line_width=1.5)
    layout = _base_layout(title, height=430)
    layout["yaxis"]["title"] = "€/ton"
    layout["legend"] = dict(orientation="h", yanchor="bottom", y=1.02,
                            bgcolor="rgba(0,0,0,0)")
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# Risk gauge
# ---------------------------------------------------------------------------

def risk_gauge(score: float, title: str = "Riesgo de decisión") -> go.Figure:
    color = DANGER_RED if score >= 67 else (WARNING_AMBER if score >= 34 else SUCCESS_GREEN)
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        delta={"reference": 50, "valueformat": ".1f"},
        title={"text": title, "font": {"size": 14, "color": DARK_NAVY}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": DARK_NAVY},
            "bar": {"color": color, "thickness": 0.3},
            "bgcolor": "white",
            "borderwidth": 2,
            "bordercolor": "#E0E0D8",
            "steps": [
                {"range": [0,  33], "color": "#E8F8F5"},
                {"range": [33, 67], "color": "#FFF8E1"},
                {"range": [67, 100], "color": "#FEF0ED"},
            ],
            "threshold": {
                "line": {"color": DARK_NAVY, "width": 2},
                "thickness": 0.8, "value": score,
            },
        },
    ))
    fig.update_layout(
        paper_bgcolor=IVORY, height=260,
        margin=dict(l=20, r=20, t=50, b=20),
        font=dict(family="Inter, sans-serif", size=11),
    )
    return fig


# ---------------------------------------------------------------------------
# Radar / Spider chart for risk components
# ---------------------------------------------------------------------------

def risk_radar(risk_scores: dict) -> go.Figure:
    categories = ["Volatilidad", "Tendencia", "Incertidumbre", "Confianza modelo"]
    values = [
        risk_scores.get("volatility", 50),
        risk_scores.get("trend", 50),
        risk_scores.get("uncertainty", 50),
        100 - risk_scores.get("model_confidence", 50),  # risk = 100 - confidence
    ]
    values_closed = values + [values[0]]
    categories_closed = categories + [categories[0]]

    fig = go.Figure(go.Scatterpolar(
        r=values_closed, theta=categories_closed,
        fill="toself", fillcolor=f"rgba(255,102,0,0.15)",
        line=dict(color=REPSOL_ORANGE, width=2),
        name="Riesgo actual",
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100],
                            tickfont=dict(size=9), gridcolor="#E0E0D8"),
            angularaxis=dict(tickfont=dict(size=10, color=DARK_NAVY)),
        ),
        showlegend=False,
        paper_bgcolor=IVORY,
        height=300,
        margin=dict(l=40, r=40, t=20, b=20),
        font=dict(family="Inter, sans-serif"),
    )
    return fig


# ---------------------------------------------------------------------------
# Monte Carlo paths
# ---------------------------------------------------------------------------

def monte_carlo_chart(
    current_price: float,
    mc_summary: pd.DataFrame,
    history: pd.Series,
    title: str = "Simulación Monte Carlo",
) -> go.Figure:
    fig = go.Figure()

    # Historical
    fig.add_trace(go.Scatter(
        x=history.index, y=history.values,
        mode="lines", name="Histórico",
        line=dict(color=HISTORY_LINE_COLOR, width=2),
    ))

    # Future x-axis (month numbers → we'll offset from last date)
    last_date = history.index[-1]
    future_dates = pd.date_range(last_date + pd.offsets.MonthBegin(1),
                                  periods=len(mc_summary), freq="MS")
    # Bands
    for lo_col, hi_col, band_name, fillcolor in [
        ("q5",  "q95", "IC 90 %", "rgba(212,0,106,0.08)"),
        ("q25", "q75", "IC 50 %", "rgba(0,48,135,0.18)"),
    ]:
        fig.add_trace(go.Scatter(
            x=list(future_dates) + list(future_dates[::-1]),
            y=list(mc_summary[hi_col]) + list(mc_summary[lo_col][::-1]),
            fill="toself", fillcolor=fillcolor,
            line=dict(width=0), name=band_name, showlegend=True,
        ))

    fig.add_trace(go.Scatter(
        x=future_dates, y=mc_summary["q50"],
        mode="lines", name="Mediana MC",
        line=dict(color=REPSOL_ORANGE, width=2.5, dash="dash"),
    ))

    fig.add_vline(x=last_date, line_dash="dot", line_color=MID_GRAY, line_width=1.5)
    layout = _base_layout(title, height=420)
    layout["yaxis"]["title"] = "€/ton"
    layout["legend"] = dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)")
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# Tornado chart for sensitivity
# ---------------------------------------------------------------------------

def tornado_chart(sensitivity_df: pd.DataFrame, title: str = "Análisis de sensibilidad") -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=sensitivity_df["driver"],
        x=sensitivity_df["impact_low"],
        orientation="h",
        name="Escenario bajo",
        marker_color=SUCCESS_GREEN,
        hovertemplate="%{y}<br>Impacto: %{x:.1f} €/ton<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=sensitivity_df["driver"],
        x=sensitivity_df["impact_high"],
        orientation="h",
        name="Escenario alto",
        marker_color=DANGER_RED,
        hovertemplate="%{y}<br>Impacto: +%{x:.1f} €/ton<extra></extra>",
    ))
    layout = _base_layout(title, height=380)
    layout["barmode"] = "overlay"
    layout["xaxis_title"] = "Impacto en precio (€/ton)"
    layout["bargap"] = 0.25
    layout["legend"] = dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)")
    fig.update_layout(**layout)
    fig.add_vline(x=0, line_color=DARK_NAVY, line_width=1.5)
    return fig


# ---------------------------------------------------------------------------
# Backtesting chart
# ---------------------------------------------------------------------------

def backtest_chart(backtest_df: pd.DataFrame, title: str = "Backtesting walk-forward") -> go.Figure:
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("MAPE por fold (%)", "Confianza del modelo (%)"),
    )
    colors = [SUCCESS_GREEN if m < 3 else (WARNING_AMBER if m < 7 else DANGER_RED)
              for m in backtest_df["mape_ens"]]
    fig.add_trace(go.Bar(
        x=backtest_df["fold"].astype(str),
        y=backtest_df["mape_ens"],
        marker_color=colors, name="MAPE Ensemble",
        text=[f"{v:.1f}%" for v in backtest_df["mape_ens"]],
        textposition="outside",
    ), row=1, col=1)
    for col_name, color, name in [
        ("mape_hw", REPSOL_BLUE,    "Holt-Winters"),
        ("mape_lf", REPSOL_ORANGE,  "Lin. Fourier"),
        ("mape_rf", REPSOL_MAGENTA, "Random Forest"),
    ]:
        fig.add_trace(go.Scatter(
            x=backtest_df["fold"].astype(str),
            y=backtest_df[col_name],
            mode="lines+markers", name=name,
            line=dict(color=color, width=1.5),
        ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=backtest_df["fold"].astype(str),
        y=backtest_df["confidence"],
        marker_color=REPSOL_ORANGE, name="Confianza",
        text=[f"{v:.0f}%" for v in backtest_df["confidence"]],
        textposition="outside",
    ), row=1, col=2)
    layout = _base_layout(title, height=360)
    layout["showlegend"] = True
    layout["legend"] = dict(orientation="h", yanchor="bottom", y=-0.3,
                            bgcolor="rgba(0,0,0,0)")
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# Correlation heatmap
# ---------------------------------------------------------------------------

def correlation_heatmap(corr_matrix: pd.DataFrame, title: str = "Correlaciones de mercado") -> go.Figure:
    fig = go.Figure(go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns.tolist(),
        y=corr_matrix.index.tolist(),
        colorscale=COLORSCALE_DIVERGING,
        zmin=-1, zmax=1,
        text=corr_matrix.round(2).astype(str).values,
        texttemplate="%{text}",
        colorbar=dict(thickness=12, tickfont=dict(size=9)),
        hovertemplate="%{y} vs %{x}<br>Corr: %{z:.3f}<extra></extra>",
    ))
    layout = _base_layout(title, height=380)
    layout.pop("xaxis", None)
    layout.pop("yaxis", None)
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# Feature importance bar
# ---------------------------------------------------------------------------

def feature_importance_chart(importances: dict[str, float], title: str = "Importancia de variables (RF)") -> go.Figure:
    items = sorted(importances.items(), key=lambda x: x[1], reverse=False)
    labels = [i[0] for i in items]
    values = [i[1] * 100 for i in items]
    colors = [REPSOL_ORANGE if v > np.percentile(values, 66)
              else (REPSOL_BLUE if v > np.percentile(values, 33) else MID_GRAY)
              for v in values]
    fig = go.Figure(go.Bar(
        x=values, y=labels,
        orientation="h", marker_color=colors,
        text=[f"{v:.1f}%" for v in values], textposition="outside",
        hovertemplate="%{y}: %{x:.2f}%<extra></extra>",
    ))
    fig.update_layout(**_base_layout(title, height=max(300, len(labels) * 32)))
    fig.update_layout(xaxis_title="Importancia (%)")
    return fig


# ---------------------------------------------------------------------------
# Buy now vs wait chart
# ---------------------------------------------------------------------------

def buy_vs_wait_chart(buy_wait_df: pd.DataFrame, title: str = "Coste: Comprar ahora vs Esperar") -> go.Figure:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        subplot_titles=("Coste esperado (€)", "Ahorro estimado por esperar (€)"),
                        vertical_spacing=0.12)

    fig.add_trace(go.Scatter(
        x=buy_wait_df.index, y=[buy_wait_df["cost_if_buy_now"].iloc[0]] * len(buy_wait_df),
        mode="lines", name="Comprar ahora",
        line=dict(color=REPSOL_BLUE, width=2, dash="dash"),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=buy_wait_df.index, y=buy_wait_df["cost_if_wait"],
        mode="lines+markers", name="Esperar",
        line=dict(color=REPSOL_ORANGE, width=2),
        marker=dict(size=6),
    ), row=1, col=1)

    bar_colors = [SUCCESS_GREEN if s > 0 else DANGER_RED for s in buy_wait_df["expected_savings"]]
    fig.add_trace(go.Bar(
        x=buy_wait_df.index, y=buy_wait_df["expected_savings"],
        marker_color=bar_colors, name="Ahorro si espera",
        hovertemplate="%{x|%b %Y}<br>Ahorro: %{y:,.0f} €<extra></extra>",
    ), row=2, col=1)
    fig.add_hline(y=0, row=2, col=1, line_dash="dot", line_color=DARK_NAVY, line_width=1)

    layout = _base_layout(title, height=440)
    layout["showlegend"] = True
    layout["legend"] = dict(orientation="h", y=1.06, bgcolor="rgba(0,0,0,0)")
    fig.update_layout(**layout)
    return fig
