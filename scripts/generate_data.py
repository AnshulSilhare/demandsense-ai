"""
DemandSense AI — Phase 1 Runner: Data Generation & Feature Engineering
=======================================================================
Generates the synthetic Indian FMCG dataset and engineers all
Indian seasonality features. Run this to produce the two core
data files needed for all subsequent phases.

Output:
  data/raw/indian_fmcg_sales.csv         - Raw synthetic daily sales
  data/processed/featured_sales.csv      - Feature-engineered dataset

Usage:
  python scripts/generate_data.py

Author: Anshul Silhare
"""

import sys
import os
import time

# Add project root to Python path so imports work from any directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.data_generator import IndianFMCGDataGenerator
from src.feature_engine import IndianSeasonalityEngine


def main():
    """Execute Phase 1: Generate data and engineer features."""

    # Ensure output directories exist
    os.makedirs(os.path.join(PROJECT_ROOT, "data", "raw"), exist_ok=True)
    os.makedirs(os.path.join(PROJECT_ROOT, "data", "processed"), exist_ok=True)

    # ────────────────────────────────────────────────────
    # STEP 1: Generate Synthetic Indian FMCG Sales Data
    # ────────────────────────────────────────────────────
    print("=" * 65)
    print("  DEMANDSENSE AI - Phase 1A: Synthetic Data Generation")
    print("=" * 65)
    print()

    t0 = time.time()
    generator = IndianFMCGDataGenerator()
    raw_df = generator.generate()

    raw_path = os.path.join(PROJECT_ROOT, "data", "raw", "indian_fmcg_sales.csv")
    generator.save(raw_df, raw_path)
    t1 = time.time()
    print(f"  Time taken: {t1 - t0:.1f}s")

    # ────────────────────────────────────────────────────
    # STEP 2: Engineer Indian Seasonality Features
    # ────────────────────────────────────────────────────
    print()
    print("=" * 65)
    print("  DEMANDSENSE AI - Phase 1B: Feature Engineering")
    print("=" * 65)
    print()

    t2 = time.time()
    engine = IndianSeasonalityEngine()
    featured_df = engine.engineer_features(raw_df)

    featured_path = os.path.join(PROJECT_ROOT, "data", "processed", "featured_sales.csv")
    engine.save(featured_df, featured_path)
    t3 = time.time()
    print(f"  Time taken: {t3 - t2:.1f}s")

    # ────────────────────────────────────────────────────
    # STEP 3: Print Summary Report
    # ────────────────────────────────────────────────────
    print()
    print("=" * 65)
    print("  DEMANDSENSE AI - Phase 1 Summary")
    print("=" * 65)
    print()
    print(f"  Total records     : {len(featured_df):,}")
    print(f"  Date range        : {featured_df['date'].min().date()} -> "
          f"{featured_df['date'].max().date()}")
    print(f"  Unique SKUs       : {featured_df['sku_id'].nunique()}")
    print(f"  Unique Regions    : {featured_df['region_id'].nunique()}")
    print(f"  Total features    : {len(featured_df.columns)}")
    print(f"  Total revenue     : INR {featured_df['revenue_inr'].sum():,.0f}")
    print(f"  Total time        : {t3 - t0:.1f}s")

    # Top SKUs by revenue
    print()
    print("  -- Top 5 SKUs by Revenue --")
    top_skus = (featured_df.groupby("sku_name")["revenue_inr"]
                .sum().sort_values(ascending=False).head())
    for rank, (name, rev) in enumerate(top_skus.items(), 1):
        print(f"  {rank}. {name}: INR {rev:,.0f}")

    # Regional revenue split
    print()
    print("  -- Regional Revenue Split --")
    total_rev = featured_df["revenue_inr"].sum()
    regional = (featured_df.groupby("region_name")["revenue_inr"]
                .sum().sort_values(ascending=False))
    for name, rev in regional.items():
        pct = rev / total_rev * 100
        bar = "#" * int(pct / 2)
        print(f"  {name:30s} INR {rev:>14,.0f}  ({pct:5.1f}%) {bar}")

    # Category breakdown
    print()
    print("  -- Category Breakdown --")
    categories = (featured_df.groupby("category")["revenue_inr"]
                  .sum().sort_values(ascending=False))
    for cat, rev in categories.items():
        pct = rev / total_rev * 100
        print(f"  {cat:20s} INR {rev:>14,.0f}  ({pct:5.1f}%)")

    # Sample of feature columns
    print()
    print("  -- Feature Columns --")
    feature_cols = [c for c in featured_df.columns
                    if c not in ["date", "sku_id", "sku_name", "category",
                                 "region_id", "region_name", "units_sold",
                                 "unit_price_inr", "revenue_inr"]]
    for i, col in enumerate(feature_cols):
        print(f"  * {col}")

    print()
    print("=" * 65)
    print("  [OK] PHASE 1 COMPLETE - Ready for Phase 2 (Forecasting Engine)")
    print("=" * 65)


if __name__ == "__main__":
    main()
