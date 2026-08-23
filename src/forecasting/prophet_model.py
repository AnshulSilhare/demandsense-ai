"""
DemandSense AI — Prophet Forecaster (with Indian Holiday Regressors)
=====================================================================
Implements Meta's Prophet model customized with Indian holiday dates.
Includes graceful fallback to Exponential Smoothing if `prophet` package
is not installed in the environment.

Author: Anshul Silhare
"""

import warnings
import numpy as np
import pandas as pd
from config import INDIAN_FESTIVALS
from .base_model import BaseForecaster
from .exp_smoothing import ExpSmoothingForecaster

warnings.filterwarnings("ignore")

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False


class ProphetForecaster(BaseForecaster):
    """Prophet forecaster enhanced with Indian festival calendar."""

    def __init__(self):
        super().__init__("Prophet")
        self.model = None
        self.fallback_model = None
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

    def fit(self, train_df: pd.DataFrame) -> "ProphetForecaster":
        train_df = train_df.sort_values("date").reset_index(drop=True)

        if not PROPHET_AVAILABLE:
            # Graceful fallback to Holt-Winters Exponential Smoothing
            self.fallback_model = ExpSmoothingForecaster(seasonal_periods=7)
            self.fallback_model.fit(train_df)
            self.last_train_date = train_df["date"].max()
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
        self.last_train_date = train_df["date"].max()
        self.is_fitted = True
        return self

    def predict(self, horizon_days: int = 30) -> pd.DataFrame:
        if not self.is_fitted:
            raise ValueError("Model must be fitted before predicting.")

        if not PROPHET_AVAILABLE and self.fallback_model:
            return self.fallback_model.predict(horizon_days)

        future = self.model.make_future_dataframe(periods=horizon_days, freq="D")
        forecast = self.model.predict(future)

        future_forecast = forecast.tail(horizon_days).copy()

        return pd.DataFrame({
            "date": pd.to_datetime(future_forecast["ds"]),
            "predicted_units": np.maximum(0, np.round(future_forecast["yhat"].values, 2)),
            "lower_bound": np.maximum(0, np.round(future_forecast["yhat_lower"].values, 2)),
            "upper_bound": np.round(future_forecast["yhat_upper"].values, 2),
        })
