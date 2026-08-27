import sys
import os
import gzip
import json
import logging
from pathlib import Path

# Set up project root
PROJECT_ROOT = Path(r"")
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np

from config import PRODUCTS, DEFAULT_LEAD_TIME_DAYS
from src.forecasting.auto_selector import ModelAutoSelector
from src.business_impact import OperationsImpactCalculator
from src.llm_agent import LLMPrescriptiveAgent
from main import (
    _load_default_data, _filter_data, _get_product_info,
    _serialize_forecast_res, _serialize_impact,
    _compute_kpi_bar, _cache_key
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("precompute")

def main():
    logger.info("Loading default dataset...")
    df = _load_default_data()
    logger.info(f"Loaded {len(df):,} records for {df['sku_id'].nunique()} SKUs.")

    cache_bundle = {}
    selector = ModelAutoSelector(test_days=60, metric="mape")
    calc = OperationsImpactCalculator(lead_time_days=DEFAULT_LEAD_TIME_DAYS)
    agent = LLMPrescriptiveAgent()

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

        # Run 5-model Auto-ML Tournament
        res = selector.evaluate_and_select(filtered)
        forecast_df = res["winning_forecast"]
        forecast_res = _serialize_forecast_res(res)

        sku_info = _get_product_info(sku)

        impact_raw = calc.calculate_sku_impact(
            product_info=sku_info,
            historical_df=filtered,
            forecast_df=forecast_df,
            current_stock=stock,
            abc_class=abc_class
        )
        impact_data = _serialize_impact(impact_raw)

        llm_report = agent._generate_rule_based_report(
            impact_data, forecast_res["winning_model_name"],
            float(forecast_res["winning_metrics"]["mape"])
        )

        kpi_bar = _compute_kpi_bar(filtered, forecast_df, impact_data, sku_info)

        chart_history = filtered[["date", "units_sold"]].copy()
        chart_history["date"] = chart_history["date"].dt.strftime("%Y-%m-%d")
        chart_history["rolling_7d"] = filtered["units_sold"].rolling(7, min_periods=1).mean().round(1)

        result = {
            "forecast_res": forecast_res,
            "impact_data": impact_data,
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

        # Store with both direct SKU keys and cache keys
        norm_sku = sku.replace("-", "").upper()
        num_suffix = norm_sku.replace("SKU", "")

        for s_alias in [sku, norm_sku, f"SKU-{num_suffix}", f"SKU{num_suffix}"]:
            cache_bundle[f"default_{s_alias}"] = result
            cache_bundle[s_alias] = result
            for sid_val in [None, "default", "global_default"]:
                ck = _cache_key(sid_val, s_alias, region, lead_time, abc_class, stock, False)
                cache_bundle[ck] = result

        logger.info(f"-> {sku} computed successfully (Winner: {forecast_res['winning_model_name']}, MAPE: {forecast_res['winning_metrics']['mape']:.2f}%)")

    output_path = PROJECT_ROOT / "data" / "processed" / "precomputed_forecasts.json.gz"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Saving precomputed bundle to {output_path}...")
    with gzip.open(output_path, "wt", encoding="utf-8") as f:
        json.dump(cache_bundle, f)

    file_size_kb = output_path.stat().st_size / 1024
    logger.info(f"Done! Saved {len(PRODUCTS)} SKU precomputed forecasts ({file_size_kb:.1f} KB gzipped).")

    # Also update scripts/build_forecast_cache.py with this clean implementation
    with open(PROJECT_ROOT / "scripts" / "build_forecast_cache.py", "w", encoding="utf-8") as f:
        with open(__file__, "r", encoding="utf-8") as src_f:
            f.write(src_f.read().replace(r"", ""))

if __name__ == "__main__":
    main()
