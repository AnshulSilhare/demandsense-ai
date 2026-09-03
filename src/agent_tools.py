"""
Author: Anshul Silhare
"""

import os, sys, logging, json, gzip
from datetime import datetime, timedelta
import numpy as np, pandas as pd

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.agent_harness import ToolRegistry
logger = logging.getLogger("demandsense.agent.tools")

tools = ToolRegistry()  # Global instance

from config import PRODUCTS, INDIAN_FESTIVALS, DEFAULT_LEAD_TIME_DAYS
from src.data_generator import IndianFMCGDataGenerator
from src.feature_engine import IndianSeasonalityEngine
from src.forecasting.auto_selector import ModelAutoSelector
from src.business_impact import OperationsImpactCalculator

import gzip

# ── IN-MEMORY CACHE & PRECOMPUTED ARTIFACT INTEGRATION ──
_CACHE = {
    "raw_df": None,
    "featured_dfs": {},
    "forecast_cache": {},
}

_PRECOMPUTED_BUNDLE = None
_FEATURED_SALES_DF = None

def _get_precomputed_bundle():
    global _PRECOMPUTED_BUNDLE
    if _PRECOMPUTED_BUNDLE is None:
        cache_path = os.path.join(_PROJECT_ROOT, "data", "processed", "precomputed_forecasts.json.gz")
        if os.path.exists(cache_path):
            try:
                with gzip.open(cache_path, "rt", encoding="utf-8") as f:
                    _PRECOMPUTED_BUNDLE = json.load(f)
            except Exception as e:
                logger.warning(f"[Agent Tools] Failed loading precomputed bundle: {e}")
                _PRECOMPUTED_BUNDLE = {}
        else:
            _PRECOMPUTED_BUNDLE = {}
    return _PRECOMPUTED_BUNDLE

def _get_featured_sales_df():
    global _FEATURED_SALES_DF
    if _FEATURED_SALES_DF is None:
        csv_path = os.path.join(_PROJECT_ROOT, "data", "processed", "featured_sales.csv")
        if os.path.exists(csv_path):
            try:
                _FEATURED_SALES_DF = pd.read_csv(csv_path, parse_dates=["date"])
            except Exception as e:
                logger.warning(f"[Agent Tools] Failed loading featured_sales.csv: {e}")
                _FEATURED_SALES_DF = None
    return _FEATURED_SALES_DF

def _get_raw_data() -> pd.DataFrame:
    if _CACHE["raw_df"] is None:
        logger.info("[Agent Tools] Generating shared base FMCG dataset...")
        gen = IndianFMCGDataGenerator()
        _CACHE["raw_df"] = gen.generate()
    return _CACHE["raw_df"]

def _get_featured_sku_data(sku_id: str) -> pd.DataFrame:
    if sku_id not in _CACHE["featured_dfs"]:
        featured_all = _get_featured_sales_df()
        if featured_all is not None and "sku_id" in featured_all:
            sku_df = featured_all[featured_all["sku_id"] == sku_id].copy()
            if not sku_df.empty:
                agg_df = sku_df.groupby("date").agg({
                    "units_sold": "sum",
                    "revenue_inr": "sum"
                }).reset_index()
                agg_df["sku_id"] = sku_id
                agg_df["region_id"] = "ALL"
                engine = IndianSeasonalityEngine()
                _CACHE["featured_dfs"][sku_id] = engine.engineer_features(agg_df)
                return _CACHE["featured_dfs"][sku_id]

        # Fallback to generator
        df = _get_raw_data()
        sku_df = df[df["sku_id"] == sku_id].copy()
        agg_df = sku_df.groupby("date").agg({
            "units_sold": "sum",
            "revenue_inr": "sum"
        }).reset_index()
        agg_df["sku_id"] = sku_id
        agg_df["region_id"] = "ALL"
        engine = IndianSeasonalityEngine()
        _CACHE["featured_dfs"][sku_id] = engine.engineer_features(agg_df)
    return _CACHE["featured_dfs"][sku_id]

def _get_sku_forecast(sku_id: str) -> dict:
    if sku_id not in _CACHE["forecast_cache"]:
        bundle = _get_precomputed_bundle()
        # Look up default_SKUxxx or SKUxxx
        key = f"default_{sku_id}" if f"default_{sku_id}" in bundle else (sku_id if sku_id in bundle else None)
        if key and key in bundle:
            entry = bundle[key]
            fc_res = entry.get("forecast_res", {})
            winning_forecast = pd.DataFrame(fc_res.get("winning_forecast", []))
            _CACHE["forecast_cache"][sku_id] = {
                "winning_model_name": fc_res.get("winning_model_name", "Prophet"),
                "winning_metrics": fc_res.get("winning_metrics", {}),
                "winning_forecast": winning_forecast,
                "all_models_metrics": fc_res.get("all_models_metrics", {})
            }
            return _CACHE["forecast_cache"][sku_id]

        # Fallback to on-the-fly training
        featured_df = _get_featured_sku_data(sku_id)
        selector = ModelAutoSelector(test_days=60)
        _CACHE["forecast_cache"][sku_id] = selector.evaluate_and_select(featured_df)
    return _CACHE["forecast_cache"][sku_id]


@tools.register(
    name="list_available_skus",
    description="List all available SKUs in the system.",
    parameters={"type": "object", "properties": {}, "required": []}
)
def list_available_skus() -> dict:
    total_skus = len(PRODUCTS)
    products = [
        {
            "sku_id": p.get("sku_id"),
            "name": p.get("name"),
            "category": p.get("category"),
            "base_price_inr": p.get("base_price"),
            "base_daily_demand": p.get("base_demand")
        } for p in PRODUCTS
    ]
    return {"total_skus": total_skus, "products": products}


@tools.register(
    name="run_demand_forecast",
    description="Run a demand forecast for a specific SKU.",
    parameters={
        "type": "object",
        "properties": {
            "sku_id": {"type": "string"}
        },
        "required": ["sku_id"]
    }
)
def run_demand_forecast(sku_id: str) -> dict:
    product = next((p for p in PRODUCTS if p.get("sku_id") == sku_id), None)
    if not product:
        return {"error": f"SKU {sku_id} not found."}
    
    result = _get_sku_forecast(sku_id)
    
    winning_model = result.get("winning_model_name")
    mape_pct = result.get("winning_metrics", {}).get("mape")
    forecast = result.get("winning_forecast")
    
    total_30d_forecast_units = forecast["predicted_units"].head(30).sum()
    avg_daily_forecast = forecast["predicted_units"].head(30).mean()
    forecast_trend = "up" if forecast["predicted_units"].iloc[-1] > forecast["predicted_units"].iloc[0] else "down"
    
    return {
        "sku_id": sku_id,
        "sku_name": product.get("name"),
        "category": product.get("category"),
        "winning_model": winning_model,
        "mape_pct": float(mape_pct) if mape_pct else 0.0,
        "total_30d_forecast_units": float(total_30d_forecast_units),
        "avg_daily_forecast": float(avg_daily_forecast),
        "forecast_trend": forecast_trend
    }


@tools.register(
    name="check_inventory_status",
    description="Check inventory status for a specific SKU.",
    parameters={
        "type": "object",
        "properties": {
            "sku_id": {"type": "string"},
            "current_stock": {"type": "integer"}
        },
        "required": ["sku_id"]
    }
)
def check_inventory_status(sku_id: str, current_stock: int = 1500) -> dict:
    product = next((p for p in PRODUCTS if p.get("sku_id") == sku_id), None)
    if not product:
        return {"error": f"SKU {sku_id} not found."}
    
    featured_df = _get_featured_sku_data(sku_id)
    result = _get_sku_forecast(sku_id)
    winning_forecast = result.get("winning_forecast")
    
    calc = OperationsImpactCalculator(lead_time_days=DEFAULT_LEAD_TIME_DAYS)
    impact = calc.calculate_sku_impact(
        product_info=product,
        historical_df=featured_df,
        forecast_df=winning_forecast,
        current_stock=current_stock,
        abc_class="A"
    )
    
    # Remove DataFrame object before returning
    impact.pop("inventory_trajectory", None)
    
    return {
        "sku_id": sku_id,
        "sku_name": product.get("name"),
        "category": product.get("category"),
        "current_stock": current_stock,
        "days_of_supply": float(impact.get("days_of_supply", 0)),
        "safety_stock_units": int(impact.get("safety_stock_units", 0)),
        "reorder_point_units": int(impact.get("reorder_point_units", 0)),
        "recommended_po_qty_units": int(impact.get("recommended_po_qty_units", 0)),
        "recommended_po_value_inr": float(impact.get("recommended_po_value_inr", 0)),
        "revenue_at_risk_inr": float(impact.get("revenue_at_risk_inr", 0)),
        "stockout_risk_units": int(impact.get("stockout_risk_units", 0)),
        "po_trigger_status": impact.get("po_trigger_status", "STABLE"),
        "winning_model": result.get("winning_model_name"),
        "mape_pct": float(result.get("winning_metrics", {}).get("mape", 0))
    }


@tools.register(
    name="get_upcoming_festivals",
    description="Get upcoming Indian festivals impacting demand.",
    parameters={
        "type": "object",
        "properties": {
            "days_ahead": {"type": "integer"}
        },
        "required": []
    }
)
def get_upcoming_festivals(days_ahead: int = 90) -> dict:
    today = datetime.now().date()
    end_date = today + timedelta(days=days_ahead)
    
    upcoming = []
    for fest_id, info in INDIAN_FESTIVALS.items():
        for d in info.get("dates", []):
            if isinstance(d, datetime):
                f_date = d.date()
            elif isinstance(d, str):
                f_date = datetime.strptime(d, "%Y-%m-%d").date()
            else:
                f_date = d
            
            # Look for festival dates in current and next calendar year
            f_this_year = f_date.replace(year=today.year)
            if f_this_year < today:
                f_this_year = f_date.replace(year=today.year + 1)

            days_until = (f_this_year - today).days
            if 0 <= days_until <= days_ahead:
                upcoming.append({
                    "festival_id": fest_id,
                    "festival_name": info.get("name"),
                    "date": f_this_year.strftime("%Y-%m-%d"),
                    "days_until": days_until,
                    "ramp_up_days": info.get("ramp_up_days", 14),
                    "post_days": info.get("post_days", 7),
                    "demand_impact": f"+{int(info.get('peak_offset', 1.5) * 100)}% demand surge expected"
                })
    
    upcoming.sort(key=lambda x: x["days_until"])
    return {
        "today": today.strftime("%Y-%m-%d"),
        "window_days": days_ahead,
        "total_upcoming": len(upcoming),
        "festivals": upcoming
    }


@tools.register(
    name="run_whatif_scenario",
    description="Run a what-if scenario adjusting demand, price, and lead time.",
    parameters={
        "type": "object",
        "properties": {
            "sku_id": {"type": "string"},
            "price_change_pct": {"type": "number"},
            "promo_lift_pct": {"type": "number"},
            "demand_change_pct": {"type": "number"},
            "lead_time_change_days": {"type": "integer"},
            "current_stock": {"type": "integer"}
        },
        "required": ["sku_id"]
    }
)
def run_whatif_scenario(
    sku_id: str,
    price_change_pct: float = 0.0,
    promo_lift_pct: float = 0.0,
    demand_change_pct: float = 0.0,
    lead_time_change_days: int = 0,
    current_stock: int = 1500
) -> dict:
    product = next((p for p in PRODUCTS if p.get("sku_id") == sku_id), None)
    if not product:
        return {"error": f"SKU {sku_id} not found."}
    
    featured_df = _get_featured_sku_data(sku_id)
    result = _get_sku_forecast(sku_id)
    base_forecast = result.get("winning_forecast").copy()
    
    ELASTICITY = -1.2
    eff_lt = max(1, DEFAULT_LEAD_TIME_DAYS + lead_time_change_days)
    price_delta = price_change_pct / 100.0
    elasticity_demand_delta = price_delta * ELASTICITY
    eff_demand_scale = (1.0 + demand_change_pct / 100.0) * (1.0 + elasticity_demand_delta) * (1.0 + promo_lift_pct / 100.0)
    eff_price = product.get("base_price", 100.0) * (1.0 + price_delta)
    
    sim_forecast = base_forecast.copy()
    sim_forecast["predicted_units"] = (sim_forecast["predicted_units"] * eff_demand_scale).clip(lower=0)
    
    calc = OperationsImpactCalculator(lead_time_days=eff_lt)
    sim_product = dict(product)
    sim_product["base_price"] = eff_price
    
    sim_impact = calc.calculate_sku_impact(
        product_info=sim_product,
        historical_df=featured_df,
        forecast_df=sim_forecast,
        current_stock=current_stock,
        abc_class="A"
    )
    sim_impact.pop("inventory_trajectory", None)
    
    # Base comparison
    base_calc = OperationsImpactCalculator(lead_time_days=DEFAULT_LEAD_TIME_DAYS)
    base_impact = base_calc.calculate_sku_impact(
        product_info=product,
        historical_df=featured_df,
        forecast_df=base_forecast,
        current_stock=current_stock,
        abc_class="A"
    )
    base_impact.pop("inventory_trajectory", None)
    
    return {
        "sku_id": sku_id,
        "sku_name": product.get("name"),
        "scenario_parameters": {
            "price_change_pct": price_change_pct,
            "promo_lift_pct": promo_lift_pct,
            "demand_change_pct": demand_change_pct,
            "lead_time_change_days": lead_time_change_days,
            "effective_lead_time": eff_lt,
            "effective_price": eff_price,
            "net_demand_multiplier": round(eff_demand_scale, 3)
        },
        "simulated_impact": {
            "total_30d_forecast_units": int(sim_forecast["predicted_units"].head(30).sum()),
            "days_of_supply": float(sim_impact.get("days_of_supply", 0)),
            "safety_stock_units": int(sim_impact.get("safety_stock_units", 0)),
            "reorder_point_units": int(sim_impact.get("reorder_point_units", 0)),
            "recommended_po_qty_units": int(sim_impact.get("recommended_po_qty_units", 0)),
            "recommended_po_value_inr": float(sim_impact.get("recommended_po_value_inr", 0)),
            "revenue_at_risk_inr": float(sim_impact.get("revenue_at_risk_inr", 0)),
            "po_trigger_status": sim_impact.get("po_trigger_status", "STABLE")
        },
        "baseline_comparison": {
            "total_30d_forecast_units": int(base_forecast["predicted_units"].head(30).sum()),
            "days_of_supply": float(base_impact.get("days_of_supply", 0)),
            "revenue_at_risk_inr": float(base_impact.get("revenue_at_risk_inr", 0))
        }
    }
