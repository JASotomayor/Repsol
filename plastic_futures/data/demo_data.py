"""
Synthetic demo data generator for Plastic Futures Decision Hub.

Produces realistic plastic-market time series (2022-2024 history)
with trends, seasonality, correlated drivers, and supplier/region layers.
All prices in EUR/ton; volumes in tons/month.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
import streamlit as st
from config.settings import PRODUCTS, SUPPLIERS, REGIONS

# ---------------------------------------------------------------------------
# Reference price levels (EUR/ton) per product
# ---------------------------------------------------------------------------
_BASE_PRICES = {
    "HDPE": 1150,
    "LDPE": 1250,
    "PP":   1050,
    "PVC":   920,
    "PET":  1000,
    "PS":   1300,
}

# Seasonal amplitude as fraction of base price (higher in summer)
_SEASONAL_AMP = {
    "HDPE": 0.06, "LDPE": 0.05, "PP": 0.07,
    "PVC":  0.08, "PET":  0.09, "PS": 0.05,
}

# Long-term trend slope per product (EUR/ton/month)
_TREND_SLOPE = {
    "HDPE":  1.0, "LDPE":  0.8, "PP":  1.2,
    "PVC":  -0.5, "PET":   0.6, "PS":  0.9,
}

# Noise volatility (fraction of base)
_NOISE_VOL = {
    "HDPE": 0.03, "LDPE": 0.03, "PP": 0.04,
    "PVC":  0.025, "PET": 0.035, "PS": 0.045,
}

# Supplier pricing premium relative to market (fraction)
_SUPPLIER_PREMIUM = {
    "SABIC":          0.00,
    "BASF":           0.02,
    "LyondellBasell": 0.01,
    "Dow Chemical":  -0.01,
    "INEOS":         -0.02,
}

# Regional adjustment factor
_REGION_FACTOR = {
    "Europa":        1.00,
    "Asia-Pacífico": 0.92,
    "Américas":      0.95,
    "Oriente Medio": 0.88,
}

# ---------------------------------------------------------------------------
# Market driver baselines
# ---------------------------------------------------------------------------
_OIL_BASE_USD  = 85.0   # Brent crude USD/bbl
_EURUSD_BASE   = 1.08
_PMI_BASE      = 52.0
_DEMAND_BASE   = 100.0


# ---------------------------------------------------------------------------
# Core generator
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def load_demo_data() -> dict[str, pd.DataFrame]:
    """
    Returns a dict with keys:
      - 'prices'   : monthly price per product/region/supplier
      - 'market'   : monthly market drivers (oil, EUR/USD, PMI, demand index)
      - 'suppliers': supplier metadata
    """
    rng = np.random.default_rng(42)

    # 36 months history: Jan 2022 – Dec 2024
    hist_dates = pd.date_range("2022-01-01", periods=36, freq="MS")

    # -----------------------------------------------------------------------
    # 1. Market drivers (common across products)
    # -----------------------------------------------------------------------
    n = len(hist_dates)
    t = np.arange(n)

    # Oil price: high in 2022 (energy crisis), then declining, partial recovery
    oil_shock = np.where(t < 12, 20, 0) + np.where((t >= 12) & (t < 18), -5, 0)
    oil = (
        _OIL_BASE_USD
        + oil_shock
        + 8 * np.sin(2 * np.pi * t / 12)
        + rng.normal(0, 3, n)
    )
    oil = np.clip(oil, 55, 140).astype(float)

    eur_usd = (
        _EURUSD_BASE
        - 0.004 * t
        + 0.03 * np.sin(2 * np.pi * t / 12 + 1)
        + rng.normal(0, 0.01, n)
    )
    eur_usd = np.clip(eur_usd, 0.95, 1.25).astype(float)

    pmi = (
        _PMI_BASE
        + 3 * np.sin(2 * np.pi * t / 12)
        + rng.normal(0, 1.5, n)
    )
    pmi = np.clip(pmi, 44, 60).astype(float)

    demand_idx = (
        _DEMAND_BASE
        + 0.3 * t
        + 8 * np.sin(2 * np.pi * t / 12 - 0.5)
        + rng.normal(0, 4, n)
    )

    gas_price_eu = (
        35
        + 40 * np.exp(-0.15 * t) * (t < 12)
        + 15 * np.exp(-0.05 * (t - 12)) * (t >= 12)
        + rng.normal(0, 4, n)
    )
    gas_price_eu = np.clip(gas_price_eu, 15, 120).astype(float)

    market_df = pd.DataFrame({
        "date":         hist_dates,
        "oil_usd_bbl":  np.round(oil, 2),
        "eur_usd":      np.round(eur_usd, 4),
        "pmi_manuf":    np.round(pmi, 1),
        "demand_index": np.round(demand_idx, 1),
        "gas_eur_mwh":  np.round(gas_price_eu, 2),
    })

    # -----------------------------------------------------------------------
    # 2. Product prices per region and supplier
    # -----------------------------------------------------------------------
    records = []
    for product in PRODUCTS:
        base   = _BASE_PRICES[product]
        amp    = _SEASONAL_AMP[product]
        slope  = _TREND_SLOPE[product]
        vol    = _NOISE_VOL[product]

        # Oil-correlated component (20-35 % of price variation)
        oil_corr = 0.008 * (oil - _OIL_BASE_USD) * base / 100

        # Energy/gas correlation for energy-intensive plastics
        gas_corr_weight = {"HDPE": 0.5, "LDPE": 0.5, "PP": 0.6,
                           "PVC": 0.7, "PET": 0.4, "PS": 0.6}
        gas_corr = gas_corr_weight[product] * 0.3 * (gas_price_eu - 35)

        # Trend + seasonality + correlations + noise
        seasonal = amp * base * np.sin(2 * np.pi * t / 12 - 0.8)
        trend    = slope * t
        noise    = vol * base * rng.standard_normal(n)

        market_price = base + trend + seasonal + oil_corr + gas_corr + noise
        market_price = np.clip(market_price, base * 0.6, base * 1.7)

        for region in REGIONS:
            region_factor = _REGION_FACTOR[region]
            for supplier in SUPPLIERS:
                sup_prem = _SUPPLIER_PREMIUM[supplier]
                price = market_price * region_factor * (1 + sup_prem)
                # Add small idiosyncratic noise per supplier
                price += rng.normal(0, base * 0.008, n)
                price = np.round(price, 2)

                # Volume: base demand with some randomness
                volume_base = rng.uniform(200, 800)
                volume = (
                    volume_base
                    + 30 * np.sin(2 * np.pi * t / 12)
                    + rng.normal(0, 20, n)
                )
                volume = np.clip(volume, 50, 1200).round(0)

                for i, date in enumerate(hist_dates):
                    records.append({
                        "date":     date,
                        "product":  product,
                        "region":   region,
                        "supplier": supplier,
                        "price":    price[i],
                        "volume":   volume[i],
                        "market_price": round(market_price[i] * region_factor, 2),
                    })

    prices_df = pd.DataFrame(records)

    # -----------------------------------------------------------------------
    # 3. Supplier metadata
    # -----------------------------------------------------------------------
    suppliers_df = pd.DataFrame({
        "supplier":       SUPPLIERS,
        "country":        ["Arabia Saudí", "Alemania", "Países Bajos", "EE.UU.", "Reino Unido"],
        "rating":         [4.5, 4.3, 4.2, 4.0, 3.8],
        "lead_time_days": [45, 21, 28, 35, 18],
        "min_order_tons": [100, 50, 80, 120, 60],
        "sustainability_score": [72, 88, 78, 70, 81],
        "premium_pct":    [p * 100 for p in _SUPPLIER_PREMIUM.values()],
    })

    # -----------------------------------------------------------------------
    # 4. Alerts / events table (notable market events in the data)
    # -----------------------------------------------------------------------
    alerts_df = pd.DataFrame([
        {"date": "2022-03-01", "event": "Inicio conflicto Ucrania → subida gas y feedstock",
         "impact": "Alto", "products": "HDPE,LDPE,PP,PS"},
        {"date": "2022-07-01", "event": "Máximo precio gas europeo en verano 2022",
         "impact": "Alto", "products": "Todos"},
        {"date": "2023-02-01", "event": "Caída demanda Europa Q1-2023",
         "impact": "Medio", "products": "PVC,PET"},
        {"date": "2023-09-01", "event": "Aumento capacidad Asia → presión bajista",
         "impact": "Medio", "products": "HDPE,PP"},
        {"date": "2024-04-01", "event": "Recuperación PMI manufacturero",
         "impact": "Bajo", "products": "Todos"},
        {"date": "2024-10-01", "event": "Tensiones geopolíticas Mar Rojo → logística",
         "impact": "Medio", "products": "HDPE,PET,PS"},
    ])
    alerts_df["date"] = pd.to_datetime(alerts_df["date"])

    return {
        "prices":    prices_df,
        "market":    market_df,
        "suppliers": suppliers_df,
        "alerts":    alerts_df,
    }


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------
def get_product_series(data: dict, product: str, region: str) -> pd.Series:
    """Return monthly market price series for a product/region (index = date)."""
    df = data["prices"]
    mask = (df["product"] == product) & (df["region"] == region)
    s = df[mask].groupby("date")["market_price"].mean().sort_index()
    return s


def get_product_volume(data: dict, product: str, region: str) -> pd.Series:
    """Return total monthly volume series for a product/region."""
    df = data["prices"]
    mask = (df["product"] == product) & (df["region"] == region)
    s = df[mask].groupby("date")["volume"].sum().sort_index()
    return s
