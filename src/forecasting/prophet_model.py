"""
DemandSense AI — Prophet Forecaster (with Indian Holiday & Fourier Regressors)
=============================================================================
Implements Meta's Prophet model customized with Indian holiday dates.
Includes high-performance pure-Python Fourier & Indian festival regressor
engine as a zero-dependency fallback when Meta's `prophet` C++ Stan package
is not present.

Author: Anshul Silhare
"""

import warnings
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from config import INDIAN_FESTIVALS
from .base_model import BaseForecaster

warnings.filterwarnings("ignore")

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False


class ProphetForecaster(BaseForecaster):
    """Prophet forecaster enhanced with Indian festival calendar and pure-Python Fourier fallback."""

    def __init__(self, weekly_order: int = 3, yearly_order: int = 5, alpha: float = 1.0):
        super().__init__("Prophet")
        self.weekly_order = weekly_order
        self.yearly_order = yearly_order
        self.alpha = alpha
        self.model = None
        self.origin_date = None
        self.residuals_std = 1.0
        if PROPHET_AVAILABLE:
            self.holidays_df = self._build_indian_holidays_df()

    def _build_indian_holidays_df(self) -> pd.DataFrame:
        """Construct Prophet-compatible holidays DataFrame."""
        records = []
        for festival_key, info in INDIAN_FESTIVALS.items():
            for d in info["dates"]:
                records.append({
                    "holiday": info["name"],
                    "ds": pd.to_datetime(d),
                    "lower_window": -info["ramp_up_days"],
                    "upper_window": info["post_days"],
                })
        return pd.DataFrame(records)

    def _extract_fourier_features(self, dates: pd.Series) -> np.ndarray:
        """Construct Fourier seasonality & Indian festival shock regressors in pure Python."""
        dates = pd.to_datetime(dates)
        t = (dates - self.origin_date).dt.days.values.astype(float)
        
        feats = []
        # 1. Normalized Trend (Linear + Quadratic)
        t_norm = t / 365.25
        feats.append(t_norm)
        feats.append(t_norm ** 2)

        # 2. Weekly Seasonality (Fourier series, period=7)
        for k in range(1, self.weekly_order + 1):
            feats.append(np.sin(2 * np.pi * k * t / 7.0))
            feats.append(np.cos(2 * np.pi * k * t / 7.0))

        # 3. Yearly Seasonality (Fourier series, period=365.25)
        for k in range(1, self.yearly_order + 1):
            feats.append(np.sin(2 * np.pi * k * t / 365.25))
            feats.append(np.cos(2 * np.pi * k * t / 365.25))

        # 4. Indian Festival Regressors (with asymmetric ramp-up and post-event windows)
        for fest_key, info in INDIAN_FESTIVALS.items():
            fest_dates = [pd.to_datetime(d) for d in info["dates"]]
            ramp_up = info.get("ramp_up_days", 7)
            post_days = info.get("post_days", 2)
            
            fest_signal = np.zeros(len(dates), dtype=float)
            for fd in fest_dates:
                diff = (dates - fd).dt.days.values
                # Ramp up window (e.g. -14 to 0) -> gradual ramp-up
                in_ramp = (diff >= -ramp_up) & (diff <= 0)
                if np.any(in_ramp):
                    fest_signal[in_ramp] = np.maximum(fest_signal[in_ramp], 1.0 + diff[in_ramp] / (ramp_up + 1e-5))
                # Post days (e.g. 0 to +2)
                in_post = (diff > 0) & (diff <= post_days)
                if np.any(in_post):
                    fest_signal[in_post] = np.maximum(fest_signal[in_post], 1.0 - diff[in_post] / (post_days + 1e-5))

            feats.append(fest_signal)

        # 5. Salary Cycle / Month-End Purchasing Window
        dom = dates.dt.day.values
        is_salary = ((dom >= 28) | (dom <= 5)).astype(float)
        feats.append(is_salary)

        return np.column_stack(feats)

    def fit(self, train_df: pd.DataFrame) -> "ProphetForecaster":
        train_df = train_df.sort_values("date").reset_index(drop=True)
        self.origin_date = train_df["date"].min()
        self.last_train_date = train_df["date"].max()

        if not PROPHET_AVAILABLE:
            # Pure-Python Bayesian Fourier & Festival Regressor
            X = self._extract_fourier_features(train_df["date"])
            y = train_df["units_sold"].astype(float).values

            self.model = Ridge(alpha=self.alpha, fit_intercept=True)
            self.model.fit(X, y)

            y_pred = self.model.predict(X)
            self.residuals_std = float(np.std(y - y_pred) or 1.0)
            self.is_fitted = True
            return self

        prophet_df = pd.DataFrame({
            "ds": pd.to_datetime(train_df["date"]),
            "y": train_df["units_sold"].astype(float),
        })

        self.model = Prophet(
            holidays=self.holidays_df,
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            seasonality_mode="additive",
            changepoint_prior_scale=0.05,
        )

        import logging
        logging.getLogger("prophet").setLevel(logging.ERROR)

        self.model.fit(prophet_df)
        self.is_fitted = True
        return self

    def predict(self, horizon_days: int = 30) -> pd.DataFrame:
        if not self.is_fitted:
            raise ValueError("Model must be fitted before predicting.")

        if not PROPHET_AVAILABLE:
            future_dates = pd.date_range(
                self.last_train_date + pd.Timedelta(days=1),
                periods=horizon_days,
                freq="D"
            )
            future_series = pd.Series(future_dates)
            X_future = self._extract_fourier_features(future_series)

            preds = self.model.predict(X_future)
            preds = np.maximum(0.0, preds)

            margin = 1.96 * self.residuals_std

            return pd.DataFrame({
                "date": future_dates,
                "predicted_units": np.round(preds, 2),
                "lower_bound": np.maximum(0.0, np.round(preds - margin, 2)),
                "upper_bound": np.round(preds + margin, 2),
            })

        future = self.model.make_future_dataframe(periods=horizon_days, freq="D")
        forecast = self.model.predict(future)

        future_forecast = forecast.tail(horizon_days).copy()

        return pd.DataFrame({
            "date": pd.to_datetime(future_forecast["ds"]),
            "predicted_units": np.maximum(0, np.round(future_forecast["yhat"].values, 2)),
            "lower_bound": np.maximum(0, np.round(future_forecast["yhat_lower"].values, 2)),
            "upper_bound": np.round(future_forecast["yhat_upper"].values, 2),
        })
