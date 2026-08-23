"""
DemandSense AI — Phase 2 Runner: Multi-Model Forecasting Engine
================================================================
Runs the Model Auto-Selector across sample SKUs to validate the
5-model benchmark leaderboard and future 30-day forecast generation.

Usage:
  python scripts/run_forecasting.py

Author: Anshul Silhare
"""

import sys
import os
import time
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.forecasting.auto_selector import ModelAutoSelector


def main():
    print("=" * 65)
    print("  DEMANDSENSE AI - Phase 2: Multi-Model Forecasting Engine")
    print("=" * 65)
    print()

    data_path = os.path.join(PROJECT_ROOT, "data", "processed", "featured_sales.csv")
    if not os.path.exists(data_path):
        print(f"[ERROR] Processed data file not found at {data_path}")
        print("Please run 'python scripts/generate_data.py' first.")
        return

    print("Loading feature-engineered dataset...")
    df = pd.read_csv(data_path)
    df["date"] = pd.to_datetime(df["date"])
    print(f"[OK] Loaded {len(df):,} records ({df['sku_id'].nunique()} SKUs across {df['region_id'].nunique()} regions)")
    print()

    # Test auto-selector on 3 representative SKUs with distinct demand profiles:
    #   1. SKU004: Iodized Salt (Stable / Non-seasonal)
    #   2. SKU007: Traditional Namkeen (Diwali peak / Highly seasonal)
    #   3. SKU020: Mosquito Repellent (Monsoon peak)

    test_skus = ["SKU004", "SKU007", "SKU020"]
    selector = ModelAutoSelector(test_days=60, metric="mape")

    for sku_id in test_skus:
        # Pass FULL featured data (with lag/rolling/festival columns) for XGBoost
        # Aggregate across regions but keep all feature columns via sum
        sku_full = df[df["sku_id"] == sku_id].copy()

        # Aggregate across regions: sum numeric feature columns, group by date
        exclude_cols = {"sku_id", "sku_name", "category", "region_id",
                        "region_name", "unit_price_inr", "revenue_inr", "date"}
        feature_cols = [c for c in sku_full.columns if c not in exclude_cols]
        sku_data = sku_full.groupby("date")[feature_cols].sum().reset_index()

        sku_name = df[df["sku_id"] == sku_id]["sku_name"].iloc[0]

        print("-" * 65)
        print(f"  EVALUATING MODEL LEADERBOARD FOR: {sku_name} ({sku_id})")
        print("-" * 65)

        t0 = time.time()
        res = selector.evaluate_and_select(sku_data)
        elapsed = time.time() - t0

        leaderboard = res["leaderboard"]
        winner = res["winning_model_name"]
        metrics = res["winning_metrics"]
        forecast = res["winning_forecast"]

        print(f"  Execution Time  : {elapsed:.1f}s")
        print(f"  Winning Model   : {winner}")
        print(f"  Winning MAPE    : {metrics['mape']}%")
        print(f"  Winning RMSE    : {metrics['rmse']} units")
        print(f"  Winning WAPE    : {metrics['wape']}%")
        print()
        print("  -- Full Benchmark Leaderboard --")
        for idx, row in leaderboard.iterrows():
            medal = " [WINNER]" if idx == 0 else f" #{idx+1}"
            print(f"  {row['model_name']:25s} | MAPE: {row['mape']:6.2f}% | RMSE: {row['rmse']:6.2f} | WAPE: {row['wape']:6.2f}% {medal}")

        print()
        print(f"  -- 30-Day Forecast Sample ({winner}) --")
        print(forecast.head(5).to_string(index=False))
        print()

    print("=" * 65)
    print("  [OK] PHASE 2 COMPLETE - Multi-Model Forecasting Engine Validated!")
    print("=" * 65)


if __name__ == "__main__":
    main()
