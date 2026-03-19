"""
Risk scoring module for procurement decisions.

Computes a composite 0-100 risk score and its sub-components:
  - Volatility risk    : recent price variability
  - Trend risk         : directional momentum (adverse for buyers)
  - Uncertainty risk   : width of forecast confidence bands
  - Model confidence   : inverse of backtest error

Also provides the "Buy Now vs Wait" cost comparison.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from config.settings import RISK_LEVELS, CARRYING_COST_PER_TON_MONTH


# ---------------------------------------------------------------------------
# Individual risk components
# ---------------------------------------------------------------------------

def _volatility_score(series: pd.Series, window: int = 6) -> float:
    """
    Coefficient of variation over the last `window` months, normalised to 0-100.
    Higher volatility → higher risk.
    """
    recent = series.tail(window)
    if recent.std() == 0 or recent.mean() == 0:
        return 0.0
    cv = recent.std() / recent.mean()
    # Empirical: CV of 0.10 → score ~70; cap at 1.0
    score = min(100.0, cv * 700)
    return round(score, 1)


def _trend_score(series: pd.Series, window: int = 3) -> float:
    """
    Momentum risk: % price change over last `window` months.
    Rising prices → higher risk for buyers; falling → lower risk.
    Score 0-100, centred at 50 (flat).
    """
    if len(series) < window + 1:
        return 50.0
    pct = (series.iloc[-1] - series.iloc[-(window + 1)]) / series.iloc[-(window + 1)]
    # +10 % rise → ~85 risk; -10 % fall → ~15 risk
    score = 50 + pct * 350
    return round(float(np.clip(score, 0, 100)), 1)


def _uncertainty_score(forecast_df: pd.DataFrame) -> float:
    """
    Relative width of the 90 % CI at the median forecast value.
    Wider band → higher uncertainty risk.
    """
    if "q_5" not in forecast_df.columns or "q_95" not in forecast_df.columns:
        return 50.0
    ci_width = (forecast_df["q_95"] - forecast_df["q_5"]).mean()
    midpoint  = forecast_df["q_50"].mean() if "q_50" in forecast_df.columns else forecast_df["mean"].mean()
    if midpoint == 0:
        return 50.0
    relative_width = ci_width / midpoint
    score = min(100.0, relative_width * 400)
    return round(score, 1)


def _model_confidence_score(backtest_df: pd.DataFrame) -> float:
    """
    Derives model confidence from backtest MAPE.
    MAPE 2 % → ~90 confidence; MAPE 10 % → ~50; MAPE 20 % → ~0.
    """
    if backtest_df is None or backtest_df.empty:
        return 50.0
    avg_mape = backtest_df["mape_ens"].mean()
    score = max(0.0, min(100.0, 100 - avg_mape * 5))
    return round(score, 1)


# ---------------------------------------------------------------------------
# Composite scorer
# ---------------------------------------------------------------------------

def compute_risk_score(
    series: pd.Series,
    forecast_df: pd.DataFrame,
    backtest_df: pd.DataFrame | None = None,
    weights: dict[str, float] | None = None,
) -> dict:
    """
    Returns a dict with:
      composite, volatility, trend, uncertainty, model_confidence,
      level ('Bajo'|'Medio'|'Alto'), color
    """
    if weights is None:
        weights = {"volatility": 0.30, "trend": 0.25, "uncertainty": 0.25, "confidence": 0.20}

    v_score  = _volatility_score(series)
    t_score  = _trend_score(series)
    u_score  = _uncertainty_score(forecast_df)
    mc_score = _model_confidence_score(backtest_df)

    # Confidence risk = inverse of confidence score
    conf_risk = 100 - mc_score

    composite = (
        weights["volatility"]  * v_score
        + weights["trend"]     * t_score
        + weights["uncertainty"] * u_score
        + weights["confidence"]  * conf_risk
    )
    composite = round(float(np.clip(composite, 0, 100)), 1)

    # Level and colour
    if composite <= RISK_LEVELS["Bajo"][1]:
        level, color = "Bajo",  "#00B894"
    elif composite <= RISK_LEVELS["Medio"][1]:
        level, color = "Medio", "#FDCB6E"
    else:
        level, color = "Alto",  "#E17055"

    return {
        "composite":         composite,
        "volatility":        v_score,
        "trend":             t_score,
        "uncertainty":       u_score,
        "model_confidence":  mc_score,
        "level":             level,
        "color":             color,
    }


# ---------------------------------------------------------------------------
# Buy Now vs Wait analysis
# ---------------------------------------------------------------------------

def buy_now_vs_wait(
    current_price: float,
    forecast_df: pd.DataFrame,
    volume_tons: float = 500,
    carrying_cost: float = CARRYING_COST_PER_TON_MONTH,
) -> pd.DataFrame:
    """
    For each forecast horizon month:
      - Expected cost if buy now  = current_price * volume
      - Expected cost if wait     = E[price_in_h] * volume + carrying_cost * h * volume
      - Expected savings (–)      = cost_now − cost_wait  (positive → save by waiting)
      - P(price rises)            = % bootstrap paths above current_price

    Returns a DataFrame indexed by future dates.
    """
    price_col = "q_50" if "q_50" in forecast_df.columns else "mean"
    expected_future = forecast_df[price_col]

    cost_now  = current_price * volume_tons
    cost_wait = expected_future * volume_tons + carrying_cost * np.arange(1, len(forecast_df) + 1) * volume_tons

    savings = cost_now - cost_wait  # positive → cheaper to wait

    # P(price rises): use q_50 vs q_25 spread as proxy for distribution
    if "q_25" in forecast_df.columns and "q_75" in forecast_df.columns:
        p_rise = (expected_future > current_price).astype(float)
        # Smooth with uncertainty
        spread = (forecast_df["q_75"] - forecast_df["q_25"]) / (2 * expected_future)
        p_rise = np.clip(p_rise + spread * 0.1, 0.05, 0.95)
    else:
        p_rise = (expected_future > current_price).astype(float)

    result = pd.DataFrame({
        "date":              forecast_df.index,
        "expected_price":    expected_future.round(2).values,
        "cost_if_buy_now":   round(cost_now, 0),
        "cost_if_wait":      cost_wait.round(0).values,
        "expected_savings":  savings.round(0).values,
        "p_price_rises":     p_rise.round(3).values,
        "decision":          ["Esperar" if s > 0 else "Comprar ahora" for s in savings],
    })
    result.set_index("date", inplace=True)
    return result


# ---------------------------------------------------------------------------
# Risk heatmap builder (product x month)
# ---------------------------------------------------------------------------

def build_risk_heatmap(
    data: dict,
    region: str,
    products: list[str],
) -> pd.DataFrame:
    """
    Returns a DataFrame of shape (products x months) with simple
    volatility-based risk scores, ready for a Plotly heatmap.
    """
    from data.demo_data import get_product_series

    rows = {}
    for p in products:
        s = get_product_series(data, p, region)
        if s.empty:
            continue
        # Rolling 3-month CV → risk per month
        rolling_cv = s.rolling(3).std() / s.rolling(3).mean()
        rows[p] = (rolling_cv * 700).clip(0, 100).round(1)

    df = pd.DataFrame(rows).T  # products as rows
    df.columns = [d.strftime("%b-%y") for d in df.columns]
    return df
