"""
DemandSense AI — Indian Seasonality Feature Engine
====================================================
Transforms raw sales data into ML-ready features for forecasting.

Feature Groups:
  1. Time Features      — day_of_week, month, quarter, is_weekend, etc.
  2. Festival Features  — is_diwali_period, days_to_navratri, etc.
  3. Season Features    — is_monsoon, is_winter, is_wedding_season, etc.
  4. Lag Features       — lag_1, lag_7, lag_14, lag_28, lag_365
  5. Rolling Features   — rolling_mean_7, rolling_std_14, etc.

All lag/rolling features are computed per (SKU, Region) group
to prevent data leakage across products.

Author: Anshul Silhare
"""

import numpy as np
import pandas as pd
from config import INDIAN_FESTIVALS


class IndianSeasonalityEngine:
    """
    Feature engineering pipeline optimized for Indian demand forecasting.

    Usage:
        engine = IndianSeasonalityEngine()
        featured_df = engine.engineer_features(raw_df)
    """

    def __init__(self):
        self.festival_flat = self._flatten_festival_dates()

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add all feature groups to the dataframe.

        Expects minimum columns: date, sku_id, region_id, units_sold
        Returns: DataFrame with ~50+ engineered features
        """
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])

        print("Engineering features...")

        # 1. Time-based features
        df = self._add_time_features(df)
        print("  [OK] Time features (11 columns)")

        # 2. Indian festival proximity features
        df = self._add_festival_features(df)
        festival_cols = [c for c in df.columns if "festival" in c or c.startswith("is_") and c.endswith("_period")]
        print(f"  [OK] Festival features ({len(festival_cols)} columns)")

        # 3. Season flags
        df = self._add_season_features(df)
        print("  [OK] Season features (8 columns)")

        # 4. Lag features (per SKU-Region)
        df = self._add_lag_features(df)
        print("  [OK] Lag features (5 columns)")

        # 5. Rolling statistics (per SKU-Region)
        df = self._add_rolling_features(df)
        print("  [OK] Rolling features (8 columns)")

        total_features = len(df.columns)
        print(f"\n[OK] Feature engineering complete - {total_features} total columns")
        return df

    # ──────────────────────────────────────────────────────
    # GROUP 1: TIME FEATURES
    # ──────────────────────────────────────────────────────

    def _add_time_features(self, df):
        """Basic temporal features derived from the date column."""
        df["day_of_week"] = df["date"].dt.dayofweek           # 0=Mon, 6=Sun
        df["day_of_month"] = df["date"].dt.day
        df["month"] = df["date"].dt.month
        df["quarter"] = df["date"].dt.quarter
        df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
        df["year"] = df["date"].dt.year
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
        df["is_month_start"] = (df["day_of_month"] <= 5).astype(int)
        df["is_month_end"] = (df["day_of_month"] >= 25).astype(int)
        df["is_quarter_end"] = df["date"].dt.is_quarter_end.astype(int)
        df["is_salary_window"] = (
            (df["day_of_month"] >= 25) | (df["day_of_month"] <= 5)
        ).astype(int)
        return df

    # ──────────────────────────────────────────────────────
    # GROUP 2: INDIAN FESTIVAL FEATURES
    # ──────────────────────────────────────────────────────

    def _add_festival_features(self, df):
        """
        For each Indian festival, create:
          - is_{festival}_period : Binary flag (within influence window)
          - days_to_{festival}   : Signed distance to nearest occurrence
        Plus composite features:
          - days_to_nearest_festival
          - is_any_festival_period
        """
        dates_array = df["date"].dt.date.values

        for festival_key, festival_info in INDIAN_FESTIVALS.items():
            period_col = f"is_{festival_key}_period"
            distance_col = f"days_to_{festival_key}"

            ramp = festival_info["ramp_up_days"]
            post = festival_info["post_days"]
            festival_dates = festival_info["dates"]

            period_flags = []
            distances = []

            for d in dates_array:
                # Find closest festival occurrence
                diffs = [(d - fd).days for fd in festival_dates]
                abs_diffs = [abs(x) for x in diffs]
                closest_idx = abs_diffs.index(min(abs_diffs))
                closest_diff = diffs[closest_idx]

                distances.append(closest_diff)
                period_flags.append(1 if -ramp <= closest_diff <= post else 0)

            df[period_col] = period_flags
            df[distance_col] = distances

        # Composite: nearest festival distance (any festival)
        distance_cols = [c for c in df.columns if c.startswith("days_to_") and c != "days_to_nearest_festival"]
        df["days_to_nearest_festival"] = df[distance_cols].abs().min(axis=1)

        # Composite: any festival active
        period_cols = [c for c in df.columns if c.endswith("_period")]
        df["is_any_festival_period"] = df[period_cols].max(axis=1)

        return df

    # ──────────────────────────────────────────────────────
    # GROUP 3: SEASON FEATURES
    # ──────────────────────────────────────────────────────

    def _add_season_features(self, df):
        """Indian climate and cultural season flags."""
        month = df["month"]

        df["is_monsoon"] = month.isin([6, 7, 8, 9]).astype(int)
        df["is_peak_monsoon"] = month.isin([7, 8]).astype(int)
        df["is_winter"] = month.isin([11, 12, 1, 2]).astype(int)
        df["is_peak_winter"] = month.isin([12, 1]).astype(int)
        df["is_summer"] = month.isin([4, 5]).astype(int)
        df["is_pre_monsoon"] = month.isin([5, 6]).astype(int)
        df["is_wedding_season"] = month.isin([11, 12, 1, 2, 4, 5]).astype(int)
        df["is_harvest_season"] = month.isin([10, 11, 3, 4]).astype(int)

        return df

    # ──────────────────────────────────────────────────────
    # GROUP 4: LAG FEATURES
    # ──────────────────────────────────────────────────────

    def _add_lag_features(self, df):
        """
        Lagged demand values per SKU-Region group.
        Critical for XGBoost and other ML models.
        NaN values for early dates are expected and handled in modeling.
        """
        group_cols = ["sku_id", "region_id"]
        df = df.sort_values(["sku_id", "region_id", "date"])

        for lag in [1, 7, 14, 28]:
            df[f"lag_{lag}"] = df.groupby(group_cols)["units_sold"].shift(lag)

        # Year-over-year comparison
        df["lag_365"] = df.groupby(group_cols)["units_sold"].shift(365)

        return df

    # ──────────────────────────────────────────────────────
    # GROUP 5: ROLLING STATISTICS
    # ──────────────────────────────────────────────────────

    def _add_rolling_features(self, df):
        """
        Rolling window statistics per SKU-Region group.
        These capture recent demand trends and volatility.
        """
        group_cols = ["sku_id", "region_id"]
        df = df.sort_values(["sku_id", "region_id", "date"])

        for window in [7, 14, 30]:
            grouped = df.groupby(group_cols)["units_sold"]

            df[f"rolling_mean_{window}"] = grouped.transform(
                lambda x: x.rolling(window, min_periods=1).mean()
            )
            df[f"rolling_std_{window}"] = grouped.transform(
                lambda x: x.rolling(window, min_periods=1).std().fillna(0)
            )

        # 7-day min/max for range detection
        grouped = df.groupby(group_cols)["units_sold"]
        df["rolling_min_7"] = grouped.transform(
            lambda x: x.rolling(7, min_periods=1).min()
        )
        df["rolling_max_7"] = grouped.transform(
            lambda x: x.rolling(7, min_periods=1).max()
        )

        return df

    # ──────────────────────────────────────────────────────
    # UTILITIES
    # ──────────────────────────────────────────────────────

    def _flatten_festival_dates(self):
        """Create a sorted flat list of all festival dates for lookups."""
        all_dates = []
        for key, info in INDIAN_FESTIVALS.items():
            for d in info["dates"]:
                all_dates.append({
                    "date": d,
                    "festival": key,
                    "name": info["name"],
                })
        return sorted(all_dates, key=lambda x: x["date"])

    def save(self, df, filepath):
        """Save featured data to CSV."""
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        df.to_csv(filepath, index=False)
        print(f"[OK] Saved featured data to {filepath} "
              f"({len(df):,} rows, {len(df.columns)} columns)")
