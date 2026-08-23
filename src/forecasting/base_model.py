"""
DemandSense AI — Base Forecaster Interface
===========================================
Defines the standard abstract base class for all forecasting models
in DemandSense AI.

Every model inherits from BaseForecaster and implements:
  - fit(train_df)
  - predict(horizon_days=30)
  - evaluate(actuals, predictions)

Standardized output format:
  Returns a DataFrame with columns: ['date', 'predicted_units', 'lower_bound', 'upper_bound']

Author: Anshul Silhare
"""

from abc import ABC, abstractmethod
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error


class BaseForecaster(ABC):
    """Abstract base class for all forecasting models."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.is_fitted = False
        self.last_train_date = None

    @abstractmethod
    def fit(self, train_df: pd.DataFrame) -> "BaseForecaster":
        """
        Fit model on historical data.

        Expects DataFrame with columns: ['date', 'units_sold'] + features if ML
        """
        pass

    @abstractmethod
    def predict(self, horizon_days: int = 30) -> pd.DataFrame:
        """
        Generate out-of-sample forecast for N future days.

        Returns DataFrame with columns:
          ['date', 'predicted_units', 'lower_bound', 'upper_bound']
        """
        pass

    def evaluate(self, actual_df: pd.DataFrame, pred_df: pd.DataFrame) -> dict:
        """
        Compute evaluation metrics comparing actuals vs predictions.

        Returns dict: {'mape': float, 'rmse': float, 'mae': float, 'wape': float}
        """
        merged = pd.merge(actual_df, pred_df, on="date", how="inner")
        if len(merged) == 0:
            return {"mape": 999.0, "rmse": 999.0, "mae": 999.0, "wape": 999.0}

        y_true = merged["units_sold"].values
        y_pred = np.maximum(0, merged["predicted_units"].values)  # Non-negative

        # 1. MAPE (Mean Absolute Percentage Error)
        # Avoid division by zero by adding epsilon
        eps = 1e-5
        mape = np.mean(np.abs((y_true - y_pred) / np.maximum(y_true, eps))) * 100

        # 2. RMSE (Root Mean Squared Error)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))

        # 3. MAE (Mean Absolute Error)
        mae = mean_absolute_error(y_true, y_pred)

        # 4. WAPE (Weighted Absolute Percentage Error) — preferred in FMCG
        sum_actuals = np.sum(y_true)
        wape = (np.sum(np.abs(y_true - y_pred)) / max(1, sum_actuals)) * 100

        return {
            "mape": round(float(mape), 2),
            "rmse": round(float(rmse), 2),
            "mae": round(float(mae), 2),
            "wape": round(float(wape), 2),
        }
