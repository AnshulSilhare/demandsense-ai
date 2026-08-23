"""
DemandSense AI — Moving Average Forecaster
===========================================
Baseline statistical model implementing Simple & Weighted Moving Averages.
Best suited for low-volatility, non-seasonal SKUs (e.g., Iodized Salt).

Author: Anshul Silhare
"""

import numpy as np
import pandas as pd
from .base_model import BaseForecaster


class MovingAverageForecaster(BaseForecaster):
    """
    Moving Average forecaster with support for 7, 14, and 30-day windows.
    Applies optional exponential weights (WMA) for recent days.
    """

    def __init__(self, window: int = 14, weighted: bool = True):
        super().__init__(f"MovingAverage_{window}d")
        self.window = window
        self.weighted = weighted
        self.last_values = None
        self.std_dev = 0

    def fit(self, train_df: pd.DataFrame) -> "MovingAverageForecaster":
        train_df = train_df.sort_values("date").reset_index(drop=True)
        recent = train_df["units_sold"].tail(self.window).values

        if len(recent) < self.window:
            # Pad if fewer records than window
            recent = np.pad(recent, (self.window - len(recent), 0), mode="edge")

        self.last_values = recent
        self.std_dev = float(train_df["units_sold"].tail(30).std() or 1.0)
        self.last_train_date = train_df["date"].max()
        self.is_fitted = True
        return self

    def predict(self, horizon_days: int = 30) -> pd.DataFrame:
        if not self.is_fitted:
            raise ValueError("Model must be fitted before predicting.")

        if self.weighted:
            # Exponentially decreasing weights for older days
            weights = np.exp(np.linspace(-1.0, 0.0, self.window))
            weights /= weights.sum()
            base_pred = np.sum(self.last_values * weights)
        else:
            base_pred = np.mean(self.last_values)

        future_dates = pd.date_range(
            self.last_train_date + pd.Timedelta(days=1),
            periods=horizon_days,
            freq="D"
        )

        preds = np.full(horizon_days, base_pred)
        # 95% confidence intervals based on rolling std dev
        margin = 1.96 * self.std_dev

        return pd.DataFrame({
            "date": future_dates,
            "predicted_units": np.maximum(0, np.round(preds, 2)),
            "lower_bound": np.maximum(0, np.round(preds - margin, 2)),
            "upper_bound": np.round(preds + margin, 2),
        })
