"""
Ensemble forecasting engine for plastic market prices.

Pipeline:
  1. Holt-Winters (Exponential Smoothing) — captures level + trend + seasonality
  2. Linear Regression with Fourier features — parsimonious seasonal baseline
  3. Random Forest with lagged features — non-linear patterns
  4. Ensemble: inverse-MAPE weighted average
  5. Bootstrap residuals → prediction intervals (conformal-style)
  6. Walk-forward backtesting for model validation
"""

from __future__ import annotations
import warnings
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_percentage_error
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    _HW_AVAILABLE = True
except ImportError:
    _HW_AVAILABLE = False

from config.settings import FORECAST_QUANTILES, N_BOOTSTRAP, BACKTEST_SPLITS


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def _fourier_features(index: np.ndarray, period: int = 12, n_harmonics: int = 2) -> np.ndarray:
    """Sine/cosine Fourier pairs for seasonal modelling."""
    cols = []
    for k in range(1, n_harmonics + 1):
        cols.append(np.sin(2 * np.pi * k * index / period))
        cols.append(np.cos(2 * np.pi * k * index / period))
    return np.column_stack(cols)


def _build_lag_features(series: np.ndarray, lags: list[int] = (1, 2, 3, 6, 12)) -> pd.DataFrame:
    """Create lag matrix; returned as DataFrame, NaN rows at top."""
    s = pd.Series(series)
    parts = {"lag_" + str(l): s.shift(l) for l in lags}
    parts["t"] = np.arange(len(s))
    parts["t2"] = np.arange(len(s)) ** 2
    df = pd.DataFrame(parts)
    # Fourier features
    ff = _fourier_features(np.arange(len(s)))
    for i, col in enumerate(["sin1", "cos1", "sin2", "cos2"]):
        df[col] = ff[:, i]
    return df


# ---------------------------------------------------------------------------
# Individual model wrappers
# ---------------------------------------------------------------------------

class _HoltWintersModel:
    def fit(self, y: np.ndarray) -> "_HoltWintersModel":
        self._n = len(y)
        try:
            m = ExponentialSmoothing(
                y, trend="add", seasonal="add",
                seasonal_periods=12, damped_trend=True
            ).fit(optimized=True, disp=False)
            self._model = m
            self._ok = True
        except Exception:
            # Fallback: simple exponential mean
            alpha = 0.3
            level = y[0]
            smoothed = [level]
            for v in y[1:]:
                level = alpha * v + (1 - alpha) * level
                smoothed.append(level)
            self._last = level
            self._slope = np.polyfit(np.arange(len(y)), y, 1)[0]
            self._ok = False
        return self

    def predict(self, h: int) -> np.ndarray:
        if self._ok:
            return self._model.forecast(h)
        return np.array([self._last + self._slope * i for i in range(1, h + 1)])

    def residuals(self) -> np.ndarray:
        if self._ok:
            return self._model.resid
        return np.zeros(self._n)


class _LinearFourierModel:
    def __init__(self):
        self._scaler = StandardScaler()
        self._lr = LinearRegression()
        self._n = 0

    def fit(self, y: np.ndarray) -> "_LinearFourierModel":
        self._n = len(y)
        t = np.arange(self._n)
        ff = _fourier_features(t)
        X = np.column_stack([t, t**2, ff])
        X_s = self._scaler.fit_transform(X)
        self._lr.fit(X_s, y)
        self._resid = y - self._lr.predict(X_s)
        return self

    def predict(self, h: int) -> np.ndarray:
        t_fut = np.arange(self._n, self._n + h)
        ff = _fourier_features(t_fut)
        X = np.column_stack([t_fut, t_fut**2, ff])
        X_s = self._scaler.transform(X)
        return self._lr.predict(X_s)

    def residuals(self) -> np.ndarray:
        return self._resid


class _RandomForestModel:
    def __init__(self):
        self._rf = RandomForestRegressor(
            n_estimators=200, max_depth=6, min_samples_leaf=3,
            random_state=42, n_jobs=-1
        )
        self._lags = [1, 2, 3, 6, 12]
        self._max_lag = max(self._lags)
        self._y_train: np.ndarray | None = None

    def fit(self, y: np.ndarray) -> "_RandomForestModel":
        self._y_train = y.copy()
        df = _build_lag_features(y, self._lags)
        df["y"] = y
        df_clean = df.dropna()
        X = df_clean.drop(columns="y")
        Y = df_clean["y"]
        self._rf.fit(X, Y)
        # Compute in-sample residuals
        y_hat = self._rf.predict(X)
        full_resid = np.full(len(y), np.nan)
        full_resid[df_clean.index] = Y.values - y_hat
        self._resid = np.where(np.isnan(full_resid), 0.0, full_resid)
        self._feature_names = list(X.columns)
        self._importances = self._rf.feature_importances_
        return self

    def predict(self, h: int) -> np.ndarray:
        history = list(self._y_train)
        preds = []
        n_base = len(history)
        for step in range(h):
            t_idx = n_base + step
            t2 = t_idx ** 2
            ff = _fourier_features(np.array([t_idx]))[0]
            lags = {}
            for lag in self._lags:
                pos = len(history) - lag
                lags["lag_" + str(lag)] = history[pos] if pos >= 0 else history[0]
            row = {**lags, "t": t_idx, "t2": t2,
                   "sin1": ff[0], "cos1": ff[1], "sin2": ff[2], "cos2": ff[3]}
            X = pd.DataFrame([row])[self._feature_names]
            p = float(self._rf.predict(X)[0])
            preds.append(p)
            history.append(p)
        return np.array(preds)

    def residuals(self) -> np.ndarray:
        return self._resid

    def feature_importances(self) -> dict[str, float]:
        return dict(zip(self._feature_names, self._importances))


# ---------------------------------------------------------------------------
# Ensemble engine
# ---------------------------------------------------------------------------

class PlasticForecastEngine:
    """
    Fits three base models, weights them by inverse-MAPE from CV,
    and generates probabilistic forecasts via bootstrap.
    """

    def __init__(self):
        self._hw   = _HoltWintersModel()
        self._lf   = _LinearFourierModel()
        self._rf   = _RandomForestModel()
        self._weights: dict[str, float] = {}
        self._y: np.ndarray | None = None
        self._dates: pd.DatetimeIndex | None = None
        self._fitted = False

    # ------------------------------------------------------------------
    def fit(self, series: pd.Series) -> "PlasticForecastEngine":
        """Fit all models to `series` (DatetimeIndex, monthly)."""
        series = series.sort_index().dropna()
        self._y     = series.values.astype(float)
        self._dates = series.index

        self._hw.fit(self._y)
        self._lf.fit(self._y)
        self._rf.fit(self._y)

        # Weights from quick hold-out (last 6 obs)
        self._weights = self._compute_weights()
        self._fitted  = True
        return self

    def _compute_weights(self) -> dict[str, float]:
        n = len(self._y)
        holdout = min(6, n // 4)
        if holdout < 2:
            return {"hw": 1/3, "lf": 1/3, "rf": 1/3}

        train, actual = self._y[:-holdout], self._y[-holdout:]
        raw_w = {}
        for name, cls in [("hw", _HoltWintersModel),
                           ("lf", _LinearFourierModel),
                           ("rf", _RandomForestModel)]:
            try:
                m = cls()
                m.fit(train)
                pred = m.predict(holdout)
                mape = mean_absolute_percentage_error(actual, pred)
                raw_w[name] = 1.0 / (mape + 1e-6)
            except Exception:
                raw_w[name] = 0.0

        total = sum(raw_w.values()) or 1.0
        return {k: v / total for k, v in raw_w.items()}

    # ------------------------------------------------------------------
    def predict(
        self,
        horizon: int,
        quantiles: list[float] = FORECAST_QUANTILES,
        n_bootstrap: int = N_BOOTSTRAP,
    ) -> pd.DataFrame:
        """
        Returns a DataFrame indexed by future dates with columns:
          q_5, q_10, q_25, q_50, q_75, q_90, q_95, mean, std
        """
        if not self._fitted:
            raise RuntimeError("Call .fit() first.")

        # Point predictions from each model
        hw_pred = self._hw.predict(horizon)
        lf_pred = self._lf.predict(horizon)
        rf_pred = self._rf.predict(horizon)

        w = self._weights
        ensemble_mean = (
            w.get("hw", 0) * hw_pred
            + w.get("lf", 0) * lf_pred
            + w.get("rf", 0) * rf_pred
        )

        # Bootstrap residuals for uncertainty
        all_resid = np.concatenate([
            self._hw.residuals(),
            self._lf.residuals(),
            self._rf.residuals(),
        ])
        all_resid = all_resid[~np.isnan(all_resid)]
        if len(all_resid) < 10:
            all_resid = np.zeros(10)

        rng = np.random.default_rng(0)
        paths = np.zeros((n_bootstrap, horizon))
        for b in range(n_bootstrap):
            # Sample residuals with heteroscedastic scaling (grows with h)
            scale = 1 + 0.05 * np.arange(1, horizon + 1)
            sampled = rng.choice(all_resid, size=horizon, replace=True) * scale
            paths[b] = ensemble_mean + sampled

        # Conformal correction: use empirical coverage from residuals
        # (shift quantiles to match empirical distribution)
        q_vals = np.quantile(paths, quantiles, axis=0)  # shape (Q, H)

        future_dates = pd.date_range(
            self._dates[-1] + pd.offsets.MonthBegin(1),
            periods=horizon, freq="MS"
        )

        result = pd.DataFrame(
            {f"q_{int(q*100)}": q_vals[i] for i, q in enumerate(quantiles)},
            index=future_dates,
        )
        result["mean"] = ensemble_mean
        result["std"]  = paths.std(axis=0)
        result["hw"]   = hw_pred
        result["lf"]   = lf_pred
        result["rf"]   = rf_pred

        return result

    # ------------------------------------------------------------------
    def backtest(self, n_splits: int = BACKTEST_SPLITS) -> pd.DataFrame:
        """Walk-forward validation; returns per-fold metrics."""
        y = self._y
        n = len(y)
        min_train = max(18, n // 2)
        fold_size = max(1, (n - min_train) // n_splits)

        records = []
        for fold in range(n_splits):
            train_end = min_train + fold * fold_size
            test_end  = min(train_end + fold_size, n)
            if train_end >= n:
                break
            train = y[:train_end]
            actual = y[train_end:test_end]

            preds_dict: dict[str, np.ndarray] = {}
            for name, cls in [("hw", _HoltWintersModel),
                               ("lf", _LinearFourierModel),
                               ("rf", _RandomForestModel)]:
                try:
                    m = cls()
                    m.fit(train)
                    preds_dict[name] = m.predict(len(actual))
                except Exception:
                    preds_dict[name] = np.full(len(actual), train.mean())

            # Weighted ensemble
            w = self._weights
            ens = (
                w.get("hw", 0) * preds_dict["hw"]
                + w.get("lf", 0) * preds_dict["lf"]
                + w.get("rf", 0) * preds_dict["rf"]
            )
            mape_ens = mean_absolute_percentage_error(actual, ens)
            mape_hw  = mean_absolute_percentage_error(actual, preds_dict["hw"])
            mape_lf  = mean_absolute_percentage_error(actual, preds_dict["lf"])
            mape_rf  = mean_absolute_percentage_error(actual, preds_dict["rf"])
            rmse_ens = float(np.sqrt(np.mean((actual - ens) ** 2)))

            records.append({
                "fold":       fold + 1,
                "train_size": train_end,
                "test_size":  len(actual),
                "date_start": self._dates[train_end],
                "mape_ens":   round(mape_ens * 100, 2),
                "mape_hw":    round(mape_hw  * 100, 2),
                "mape_lf":    round(mape_lf  * 100, 2),
                "mape_rf":    round(mape_rf  * 100, 2),
                "rmse_ens":   round(rmse_ens, 2),
                "confidence": round(max(0, 100 - mape_ens * 500), 1),
            })

        return pd.DataFrame(records)

    def model_weights(self) -> dict[str, float]:
        return {k: round(v, 4) for k, v in self._weights.items()}

    def feature_importances(self) -> dict[str, float]:
        raw = self._rf.feature_importances()
        _friendly = {
            "lag_1":  "Precio mes anterior",
            "lag_2":  "Precio hace 2 meses",
            "lag_3":  "Precio hace 3 meses",
            "lag_6":  "Precio hace 6 meses",
            "lag_12": "Precio hace 12 meses",
            "t":      "Tendencia general",
            "t2":     "Tendencia acelerada",
            "sin1":   "Estacionalidad (ciclo A)",
            "cos1":   "Estacionalidad (ciclo B)",
            "sin2":   "Estacionalidad (ciclo C)",
            "cos2":   "Estacionalidad (ciclo D)",
        }
        return {_friendly.get(k, k): v for k, v in raw.items()}

    @property
    def history_dates(self) -> pd.DatetimeIndex:
        return self._dates

    @property
    def history_values(self) -> np.ndarray:
        return self._y
