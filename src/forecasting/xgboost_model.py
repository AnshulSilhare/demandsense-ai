"""
DemandSense AI — XGBoost Forecaster
===================================
Gradient Boosted Decision Trees trained on engineered features:
  - Temporal features (day of week, month, salary window)
  - Indian festival proximity features
  - Season flags (monsoon, winter, wedding)
  - Lag features & rolling statistics

Includes graceful fallback to Scikit-Learn HistGradientBoostingRegressor
if `xgboost` package is not installed.

Author: Anshul Silhare
"""

import warnings
import numpy as np
import pandas as pd
from .base_model import BaseForecaster

warnings.filterwarnings("ignore")

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    from sklearn.ensemble import HistGradientBoostingRegressor

# Feature columns used for training
FEATURE_COLS = [
    "day_of_week", "day_of_month", "month", "quarter", "week_of_year",
    "is_weekend", "is_month_start", "is_month_end", "is_salary_window",
    "is_monsoon", "is_winter", "is_summer", "is_wedding_season",
    "is_any_festival_period", "days_to_nearest_festival",
    "lag_1", "lag_7", "lag_14", "lag_28",
    "rolling_mean_7", "rolling_std_7", "rolling_mean_14", "rolling_mean_30",
]


class XGBoostForecaster(BaseForecaster):
    """XGBoost / Gradient Boosted Regressor for feature-based demand forecasting."""

    def __init__(self):
        super().__init__("XGBoost" if XGBOOST_AVAILABLE else "GradientBoosting")
        self.model = None
        self.feature_names = None
        self.last_row = None
        self.std_err = 1.0

    def fit(self, train_df: pd.DataFrame) -> "XGBoostForecaster":
        train_df = train_df.sort_values("date").reset_index(drop=True)

        avail_features = [c for c in FEATURE_COLS if c in train_df.columns]
        self.feature_names = avail_features

        clean_df = train_df.dropna(subset=avail_features + ["units_sold"])

        if len(clean_df) < 30:
            clean_df = train_df.fillna(0)

        X = clean_df[avail_features]
        y = clean_df["units_sold"]

        if XGBOOST_AVAILABLE:
            self.model = xgb.XGBRegressor(
                n_estimators=150,
                learning_rate=0.05,
                max_depth=5,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                verbosity=0,
            )
        else:
            self.model = HistGradientBoostingRegressor(
                max_iter=150,
                learning_rate=0.05,
                max_depth=5,
                random_state=42
            )

        self.model.fit(X, y)

        preds = self.model.predict(X)
        self.std_err = float(np.std(y - preds) or 1.0)
        self.last_train_date = train_df["date"].max()
        self.last_row = train_df.iloc[-1]
        self.is_fitted = True
        return self

    def predict(self, horizon_days: int = 30) -> pd.DataFrame:
        if not self.is_fitted:
            raise ValueError("Model must be fitted before predicting.")

        future_dates = pd.date_range(
            self.last_train_date + pd.Timedelta(days=1),
            periods=horizon_days,
            freq="D"
        )

        preds = []
        current_feat = self.last_row[self.feature_names].copy()

        for d in future_dates:
            if "day_of_week" in current_feat:
                current_feat["day_of_week"] = d.dayofweek
            if "day_of_month" in current_feat:
                current_feat["day_of_month"] = d.day
            if "month" in current_feat:
                current_feat["month"] = d.month
            if "quarter" in current_feat:
                current_feat["quarter"] = d.quarter
            if "is_weekend" in current_feat:
                current_feat["is_weekend"] = int(d.dayofweek in [5, 6])
            if "is_salary_window" in current_feat:
                current_feat["is_salary_window"] = int(d.day >= 25 or d.day <= 5)

            X_step = pd.DataFrame([current_feat])[self.feature_names]
            step_pred = max(0.0, float(self.model.predict(X_step)[0]))
            preds.append(step_pred)

            if "lag_1" in current_feat:
                current_feat["lag_1"] = step_pred

        preds = np.array(preds)
        margin = 1.96 * self.std_err

        return pd.DataFrame({
            "date": future_dates,
            "predicted_units": np.round(preds, 2),
            "lower_bound": np.maximum(0, np.round(preds - margin, 2)),
            "upper_bound": np.round(preds + margin, 2),
        })

    def feature_importances(self) -> pd.Series:
        """Return feature importance rankings."""
        if not self.is_fitted:
            return pd.Series()

        if XGBOOST_AVAILABLE:
            imp = self.model.feature_importances_
        else:
            imp = np.ones(len(self.feature_names)) / len(self.feature_names)

        return pd.Series(imp, index=self.feature_names).sort_values(ascending=False)
