"""
DemandSense AI — SARIMAX / ARIMA Forecaster
============================================
Implements Seasonal AutoRegressive Integrated Moving Average (SARIMAX).
Captures complex autocorrelation structures and weekly seasonality.

Author: Anshul Silhare
"""

import warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
from .base_model import BaseForecaster

warnings.filterwarnings("ignore")


class ARIMAForecaster(BaseForecaster):
    """SARIMAX (p,d,q) x (P,D,Q,s) forecaster."""

    def __init__(self, order=(1, 1, 1), seasonal_order=(1, 0, 1, 7)):
        super().__init__("SARIMAX")
        self.order = order
        self.seasonal_order = seasonal_order
        self.model_fit = None

    def fit(self, train_df: pd.DataFrame) -> "ARIMAForecaster":
        train_df = train_df.sort_values("date").reset_index(drop=True)
        series = train_df["units_sold"].astype(float).values

        try:
            model = SARIMAX(
                series,
                order=self.order,
                seasonal_order=self.seasonal_order,
                enforce_stationarity=False,
                enforce_invertibility=False,
            )
            self.model_fit = model.fit(disp=False, maxiter=100)
        except Exception:
            # Fallback simple ARIMA if SARIMAX fails to converge
            model = SARIMAX(series, order=(1, 1, 0), enforce_stationarity=False)
            self.model_fit = model.fit(disp=False, maxiter=50)

        self.last_train_date = train_df["date"].max()
        self.is_fitted = True
        return self

    def predict(self, horizon_days: int = 30) -> pd.DataFrame:
        if not self.is_fitted:
            raise ValueError("Model must be fitted before predicting.")

        forecast_res = self.model_fit.get_forecast(steps=horizon_days)
        preds = np.maximum(0, forecast_res.predicted_mean)

        ci = forecast_res.conf_int(alpha=0.05)
        lower = np.maximum(0, ci[:, 0]) if ci.ndim > 1 else np.maximum(0, ci[0])
        upper = ci[:, 1] if ci.ndim > 1 else ci[1]

        future_dates = pd.date_range(
            self.last_train_date + pd.Timedelta(days=1),
            periods=horizon_days,
            freq="D"
        )

        return pd.DataFrame({
            "date": future_dates,
            "predicted_units": np.round(preds, 2),
            "lower_bound": np.round(lower, 2),
            "upper_bound": np.round(upper, 2),
        })
