"""
DemandSense AI — Precompute Forecast Cache
============================================
Generates and serializes the complete forecast & impact bundle for all 20 default SKUs.
This guarantees <10ms instant response times on production without runtime model training.
"""

import sys
import os
import gzip
import json
import logging
from pathlib import Path

# Set up project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np

from config import PRODUCTS, DEFAULT_LEAD_TIME_DAYS
from main import (
    _load_default_data, _filter_data, _get_product_info,
    _run_forecast_pipeline, _serialize_forecast_res, _serialize_impact,
    _compute_kpi_bar, _cache_key
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("precompute")

def main():
    logger.info("Loading default dataset...")
    df = _load_default_data()
    logger.info(f"Loaded {len(df):,} records for {df['sku_id'].nunique()} SKUs.")

    cache_bundle = {}

    for i, prod in enumerate(PRODUCTS, 1):
        sku = prod["sku_id"]
        logger.info(f"[{i}/{len(PRODUCTS)}] Precomputing forecast for {sku} ({prod['name']})...")

        region = "ALL"
        lead_time = DEFAULT_LEAD_TIME_DAYS
        abc_class = "A"
        stock = 25000

        filtered = _filter_data(df, sku, region)
        if filtered.empty or len(filtered) < 30:
            logger.warning(f"Skipping {sku}: insufficient records ({len(filtered)})")
            continue

        forecast_res, impact_data, llm_report = _run_forecast_pipeline(
            filtered, sku, lead_time, abc_class, stock
        )

        sku_info = _get_product_info(sku)
        kpi_bar = _compute_kpi_bar(filtered, forecast_res["winning_forecast"], impact_data, sku_info)

        chart_history = filtered[["date", "units_sold"]].copy()
        chart_history["date"] = chart_history["date"].dt.strftime("%Y-%m-%d")
        chart_history["rolling_7d"] = filtered["units_sold"].rolling(7, min_periods=1).mean().round(1)

        result = {
            "forecast_res": _serialize_forecast_res(forecast_res),
            "impact_data": _serialize_impact(impact_data),
            "llm_report": llm_report,
            "kpi_bar": kpi_bar,
            "chart_history": chart_history.to_dict(orient="records"),
            "sku_info": sku_info,
            "data_summary": {
                "data_start": filtered["date"].min().strftime("%b %d, %Y"),
                "data_end": filtered["date"].max().strftime("%b %d, %Y"),
                "total_days": int((filtered["date"].max() - filtered["date"].min()).days),
                "total_skus": int(df["sku_id"].nunique()),
            }
        }

        # Store with both SKU direct key and MD5 cache key
        ck = _cache_key(None, sku, region, lead_time, abc_class, stock)
        cache_bundle[ck] = result
        cache_bundle[f"default_{sku}"] = result
        logger.info(f"-> {sku} computed successfully (Winner: {forecast_res['winning_model_name']}, MAPE: {forecast_res['winning_metrics']['mape']:.2f}%)")

    output_path = PROJECT_ROOT / "data" / "processed" / "precomputed_forecasts.json.gz"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Saving precomputed bundle to {output_path}...")
    with gzip.open(output_path, "wt", encoding="utf-8") as f:
        json.dump(cache_bundle, f)

    file_size_kb = output_path.stat().st_size / 1024
    logger.info(f"Done! Saved {len(PRODUCTS)} SKU precomputed forecasts ({file_size_kb:.1f} KB gzipped).")

if __name__ == "__main__":
    main()
