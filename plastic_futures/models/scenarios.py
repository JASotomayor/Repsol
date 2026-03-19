"""
Scenario simulation module.

Generates named scenario forecasts and Monte Carlo paths for the
Plastic Futures Decision Hub.

Scenarios:
  - Base:              central ensemble forecast
  - Alcista (Bull):    lower quantile path (good for buyers → falling prices)
  - Bajista (Bear):    upper quantile path (bad for buyers → rising prices)
  - Crisis energética: shock to oil/gas costs → sharp price spike
  - Demanda débil:     demand destruction → accelerated price decline
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from config.settings import N_MONTE_CARLO, SCENARIOS


# ---------------------------------------------------------------------------
# Scenario parameter multipliers (relative to base forecast)
# ---------------------------------------------------------------------------
_SCENARIO_PARAMS = {
    "Base": {
        "level_shift": 0.00,
        "trend_mult":  1.00,
        "vol_mult":    1.00,
        "quantile":    0.50,
    },
    "Alcista (Bull)": {
        "level_shift": -0.05,
        "trend_mult":  0.70,
        "vol_mult":    0.80,
        "quantile":    0.20,
    },
    "Bajista (Bear)": {
        "level_shift": 0.08,
        "trend_mult":  1.30,
        "vol_mult":    1.20,
        "quantile":    0.80,
    },
    "Crisis energética": {
        "level_shift": 0.15,
        "trend_mult":  1.50,
        "vol_mult":    1.80,
        "quantile":    0.90,
    },
    "Demanda débil": {
        "level_shift": -0.10,
        "trend_mult":  0.50,
        "vol_mult":    1.10,
        "quantile":    0.15,
    },
}


# ---------------------------------------------------------------------------
# Main scenario builder
# ---------------------------------------------------------------------------

def build_scenario_forecasts(
    base_forecast: pd.DataFrame,
    current_price: float,
    scenarios: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Given the base probabilistic forecast DataFrame (from PlasticForecastEngine),
    return a dict {scenario_name → DataFrame with 'price', 'lo80', 'hi80'}.
    """
    if scenarios is None:
        scenarios = SCENARIOS

    results: dict[str, pd.DataFrame] = {}
    h = len(base_forecast)
    t = np.arange(1, h + 1)

    base_median = base_forecast["q_50"] if "q_50" in base_forecast.columns else base_forecast["mean"]
    base_std = base_forecast["std"] if "std" in base_forecast.columns else base_median * 0.05

    for sc_name in scenarios:
        params = _SCENARIO_PARAMS.get(sc_name, _SCENARIO_PARAMS["Base"])

        level_shift = params["level_shift"]
        trend_mult  = params["trend_mult"]
        vol_mult    = params["vol_mult"]

        # Apply scenario modifications to the base trend
        trend_base = base_median.values - current_price
        sc_trend   = trend_base * trend_mult
        sc_level   = current_price * (1 + level_shift)
        sc_mean    = sc_level + sc_trend

        sc_std = base_std.values * vol_mult
        # Grow uncertainty with horizon
        sc_std = sc_std * (1 + 0.04 * t)

        sc_lo80 = sc_mean - 1.28 * sc_std
        sc_hi80 = sc_mean + 1.28 * sc_std
        sc_lo95 = sc_mean - 1.96 * sc_std
        sc_hi95 = sc_mean + 1.96 * sc_std

        results[sc_name] = pd.DataFrame({
            "date":  base_forecast.index,
            "price": np.round(sc_mean, 2),
            "lo80":  np.round(sc_lo80, 2),
            "hi80":  np.round(sc_hi80, 2),
            "lo95":  np.round(sc_lo95, 2),
            "hi95":  np.round(sc_hi95, 2),
        }).set_index("date")

    return results


# ---------------------------------------------------------------------------
# Monte Carlo simulation
# ---------------------------------------------------------------------------

def run_monte_carlo(
    current_price: float,
    horizon: int,
    annual_drift: float = 0.02,
    annual_vol: float = 0.12,
    n_paths: int = N_MONTE_CARLO,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Geometric Brownian Motion simulation for plastic prices.

    Returns DataFrame of shape (n_paths, horizon) with simulated paths.
    Columns represent months ahead (1..horizon).
    """
    rng = np.random.default_rng(seed)
    dt = 1 / 12
    mu  = annual_drift
    sig = annual_vol

    paths = np.zeros((n_paths, horizon))
    for i in range(n_paths):
        price = current_price
        for j in range(horizon):
            z = rng.standard_normal()
            price = price * np.exp((mu - 0.5 * sig**2) * dt + sig * np.sqrt(dt) * z)
            paths[i, j] = price

    return pd.DataFrame(
        paths,
        columns=[f"m{j+1}" for j in range(horizon)],
    )


def monte_carlo_summary(mc_paths: pd.DataFrame) -> pd.DataFrame:
    """
    Summarise MC paths into quantile bands per month.
    Returns DataFrame with q5, q25, q50, q75, q95, mean, std.
    """
    q = mc_paths.quantile([0.05, 0.25, 0.50, 0.75, 0.95])
    summary = q.T.rename(columns={
        0.05: "q5", 0.25: "q25", 0.50: "q50", 0.75: "q75", 0.95: "q95"
    })
    summary["mean"] = mc_paths.mean()
    summary["std"]  = mc_paths.std()
    summary["month"] = np.arange(1, len(summary) + 1)
    return summary


# ---------------------------------------------------------------------------
# Sensitivity / Tornado analysis
# ---------------------------------------------------------------------------

def sensitivity_analysis(
    base_price: float,
    horizon: int = 6,
    drivers: dict[str, tuple[float, float]] | None = None,
) -> pd.DataFrame:
    """
    Tornado chart data: for each driver, compute price impact
    at low / high values vs baseline.

    `drivers` format: {driver_name: (low_pct_change, high_pct_change)}
    e.g. {"Oil price": (-0.20, +0.20), "EUR/USD": (-0.05, +0.05)}
    """
    if drivers is None:
        drivers = {
            "Precio petróleo":    (-0.25, +0.25),
            "Precio gas EU":      (-0.30, +0.35),
            "EUR/USD":            (-0.08, +0.08),
            "PMI manufacturero":  (-0.06, +0.04),
            "Demanda global":     (-0.10, +0.08),
            "Capacidad nueva":    (-0.05, +0.15),
            "Logística / flete":  (-0.03, +0.12),
        }

    # Elasticities (fraction of price change per unit driver change)
    # Rough empirical values for polymer pricing
    elasticities = {
        "Precio petróleo":    0.35,
        "Precio gas EU":      0.28,
        "EUR/USD":            0.20,
        "PMI manufacturero":  0.15,
        "Demanda global":     0.18,
        "Capacidad nueva":    0.12,
        "Logística / flete":  0.10,
    }

    records = []
    for driver, (lo, hi) in drivers.items():
        e = elasticities.get(driver, 0.10)
        # Project to horizon: impact grows ~sqrt(horizon/6)
        horizon_scale = np.sqrt(horizon / 6)
        price_lo = base_price * (1 + e * lo * horizon_scale)
        price_hi = base_price * (1 + e * hi * horizon_scale)
        records.append({
            "driver":    driver,
            "price_low": round(price_lo, 1),
            "price_high": round(price_hi, 1),
            "impact_low":  round(price_lo - base_price, 1),
            "impact_high": round(price_hi - base_price, 1),
        })

    return pd.DataFrame(records).sort_values("impact_high", ascending=True)
