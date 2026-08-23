"""
DemandSense AI — Exponential Smoothing (Holt-Winters) Forecaster
==================================================================
Implements Holt-Winters Triple Exponential Smoothing (Level, Trend, Seasonality).
Best suited for products with clear weekly/monthly seasonality.

Author: Anshul Silhare
"""

import warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from .base_model import BaseForecaster

warnings.filterwarnings("ignore")


class ExpSmoothingForecaster(BaseForecaster):
    """Holt-Winters Exponential Smoothing forecaster."""

    def __init__(self, seasonal_periods: int = 7, trend: str = "add", seasonal: str = "add"):
        super().__init__("ExponentialSmoothing")
        self.seasonal_periods = seasonal_periods
        self.trend = trend
        self.seasonal = seasonal
        self.model_fit = None
        self.residuals_std = 0

    def fit(self, train_df: pd.DataFrame) -> "ExpSmoothingForecaster":
        train_df = train_df.sort_values("date").reset_index(drop=True)
        series = train_df["units_sold"].astype(float).values

        # Ensure non-zero values for multiplicative modes
        series = np.maximum(0.1, series)

        try:
            model = ExponentialSmoothing(
                series,
                trend=self.trend,
                seasonal=self.seasonal,
                seasonal_periods=self.seasonal_periods,
                initialization_method="estimated",
            )
            self.model_fit = model.fit(optimized=True)
            residuals = series - self.model_fit.fittedvalues
            self.residuals_std = float(np.std(residuals) or 1.0)
        except Exception:
            # Fallback to simple exponential smoothing if Holt-Winters fails
            model = ExponentialSmoothing(series, trend=None, seasonal=None)
            self.model_fit = model.fit(optimized=True)
            self.residuals_std = float(np.std(series) or 1.0)

        self.last_train_date = train_df["date"].max()
        self.is_fitted = True
        return self

    def predict(self, horizon_days: int = 30) -> pd.DataFrame:
        if not self.is_fitted:
            raise ValueError("Model must be fitted before predicting.")

        preds = self.model_fit.forecast(horizon_days)
        preds = np.maximum(0, preds)

        future_dates = pd.date_range(
            self.last_train_date + pd.Timedelta(days=1),
            periods=horizon_days,
            freq="D"
        )

        margin = 1.96 * self.residuals_std

        return pd.DataFrame({
            "date": future_dates,
            "predicted_units": np.round(preds, 2),
            "lower_bound": np.maximum(0, np.round(preds - margin, 2)),
            "upper_bound": np.round(preds + margin, 2),
        })
