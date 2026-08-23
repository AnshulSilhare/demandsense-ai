"""
DemandSense AI — Model Auto-Selector Engine
============================================
The core intelligence engine of Phase 2.

For a given SKU and Region (or overall category):
  1. Splitting historical data into Train / Test sets (e.g. last 60 days test)
  2. Instantiate & fit all 5 forecasting models:
       - Moving Average (14d)
       - Exponential Smoothing (Holt-Winters)
       - SARIMAX / ARIMA
       - Prophet (with Indian festival calendar)
       - XGBoost Regressor
  3. Evaluate each model on unseen Test data using MAPE, RMSE, MAE, WAPE
  4. Select Winner based on primary metric (default: MAPE)
  5. Fit Winner on ALL data and generate future 30-day forecast

Returns a structured leaderboard & the winning forecast.

Author: Anshul Silhare
"""

import time
import warnings
import numpy as np
import pandas as pd

from .moving_average import MovingAverageForecaster
from .exp_smoothing import ExpSmoothingForecaster
from .arima_model import ARIMAForecaster
from .prophet_model import ProphetForecaster
from .xgboost_model import XGBoostForecaster

warnings.filterwarnings("ignore")


class ModelAutoSelector:
    """Automated model evaluation and selection pipeline."""

    def __init__(self, test_days: int = 60, metric: str = "mape"):
        self.test_days = test_days
        self.metric = metric.lower()  # 'mape', 'rmse', 'mae', or 'wape'

    def get_candidate_models(self):
        """Instantiate clean copies of all 5 forecasting models."""
        return [
            MovingAverageForecaster(window=14, weighted=True),
            ExpSmoothingForecaster(seasonal_periods=7),
            ARIMAForecaster(order=(1, 1, 1), seasonal_order=(1, 0, 1, 7)),
            ProphetForecaster(),
            XGBoostForecaster(),
        ]

    def evaluate_and_select(self, sku_df: pd.DataFrame) -> dict:
        """
        Evaluate all candidate models on test set and select the winner.

        Expects DataFrame for a single SKU (or single SKU-Region) sorted by date.

        Returns dict:
          - leaderboard : DataFrame of model performance metrics
          - winning_model_name : Name of the best model
          - winning_metrics : Performance dict of winning model
          - winning_forecast : 30-day future forecast from winner fitted on full data
        """
        sku_df = sku_df.sort_values("date").reset_index(drop=True)

        if len(sku_df) < (self.test_days + 30):
            raise ValueError(f"Insufficient data ({len(sku_df)} rows) for test split.")

        # Train/Test temporal split (no future data leakage)
        train_cutoff = sku_df["date"].max() - pd.Timedelta(days=self.test_days)
        train_df = sku_df[sku_df["date"] <= train_cutoff].copy()
        test_df = sku_df[sku_df["date"] > train_cutoff].copy()

        results = []

        for model in self.get_candidate_models():
            model_name = model.model_name
            t0 = time.time()

            try:
                # 1. Fit on Train
                model.fit(train_df)

                # 2. Predict on Test horizon
                test_pred = model.predict(horizon_days=len(test_df))

                # 3. Evaluate against ground-truth Test actuals
                metrics = model.evaluate(test_df, test_pred)
                exec_time = time.time() - t0

                results.append({
                    "model_name": model_name,
                    "mape": metrics["mape"],
                    "rmse": metrics["rmse"],
                    "mae": metrics["mae"],
                    "wape": metrics["wape"],
                    "fit_time_sec": round(exec_time, 2),
                    "status": "SUCCESS",
                    "model_obj": model,
                })
            except Exception as e:
                results.append({
                    "model_name": model_name,
                    "mape": 999.0,
                    "rmse": 999.0,
                    "mae": 999.0,
                    "wape": 999.0,
                    "fit_time_sec": 0.0,
                    "status": f"FAILED: {str(e)[:50]}",
                    "model_obj": None,
                })

        leaderboard_df = pd.DataFrame(results)

        # Sort leaderboard by chosen metric (ascending: lower error is better)
        sort_col = self.metric if self.metric in leaderboard_df.columns else "mape"
        leaderboard_df = leaderboard_df.sort_values(sort_col).reset_index(drop=True)

        winner_row = leaderboard_df.iloc[0]
        winner_name = winner_row["model_name"]

        # Re-fit winning model architecture on FULL dataset for production forecast
        winning_model = self._instantiate_model_by_name(winner_name)
        winning_model.fit(sku_df)
        production_forecast = winning_model.predict(horizon_days=30)

        # Clean display leaderboard (remove model_obj column)
        display_leaderboard = leaderboard_df.drop(columns=["model_obj"])

        return {
            "leaderboard": display_leaderboard,
            "winning_model_name": winner_name,
            "winning_metrics": {
                "mape": winner_row["mape"],
                "rmse": winner_row["rmse"],
                "mae": winner_row["mae"],
                "wape": winner_row["wape"],
            },
            "winning_forecast": production_forecast,
        }

    def _instantiate_model_by_name(self, model_name: str):
        """Factory helper to recreate model by name."""
        if "MovingAverage" in model_name:
            return MovingAverageForecaster(window=14, weighted=True)
        elif model_name == "ExponentialSmoothing":
            return ExpSmoothingForecaster(seasonal_periods=7)
        elif model_name == "SARIMAX":
            return ARIMAForecaster()
        elif model_name == "Prophet":
            return ProphetForecaster()
        elif model_name == "XGBoost":
            return XGBoostForecaster()
        else:
            return MovingAverageForecaster()
