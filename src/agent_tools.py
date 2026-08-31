"""
Author: Anshul Silhare
"""

import os, sys, logging
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
    
    gen = IndianFMCGDataGenerator()
    df = gen.generate()
    sku_df = df[df["sku_id"] == sku_id].copy()
    
    agg_df = sku_df.groupby("date").agg({
        "units_sold": "sum",
        "revenue_inr": "sum"
    }).reset_index()
    agg_df["sku_id"] = sku_id
    agg_df["region_id"] = "ALL"
    
    engine = IndianSeasonalityEngine()
    featured_df = engine.engineer_features(agg_df)
    
    selector = ModelAutoSelector(test_days=60)
    result = selector.evaluate_and_select(featured_df)
    
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
        "mape_pct": mape_pct,
        "total_30d_forecast_units": float(total_30d_forecast_units),
        "avg_daily_forecast": float(avg_daily_forecast),
        "forecast_trend": forecast_trend,
        "model_leaderboard": result.get("leaderboard").to_dict(orient="records") if result.get("leaderboard") is not None else []
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
    
    gen = IndianFMCGDataGenerator()
    df = gen.generate()
    sku_df = df[df["sku_id"] == sku_id].copy()
    
    agg_df = sku_df.groupby("date").agg({"units_sold": "sum", "revenue_inr": "sum"}).reset_index()
    agg_df["sku_id"] = sku_id
    agg_df["region_id"] = "ALL"
    
    engine = IndianSeasonalityEngine()
    featured_df = engine.engineer_features(agg_df)
    
    selector = ModelAutoSelector(test_days=60)
    result = selector.evaluate_and_select(featured_df)
    
    calc = OperationsImpactCalculator(lead_time_days=DEFAULT_LEAD_TIME_DAYS)
    impact = calc.calculate_sku_impact(product, featured_df, result.get("winning_forecast"), current_stock, 'A')
    
    if "inventory_trajectory" in impact:
        del impact["inventory_trajectory"]
        
    return {
        "winning_model": result.get("winning_model_name"),
        "mape_pct": result.get("winning_metrics", {}).get("mape"),
        **impact
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
    window_end = today + timedelta(days=days_ahead)
    
    upcoming = []
    for fest_id, fest_info in INDIAN_FESTIVALS.items():
        for d in fest_info.get("dates", []):
            if isinstance(d, str):
                try:
                    d = datetime.strptime(d, "%Y-%m-%d").date()
                except ValueError:
                    continue
            elif isinstance(d, datetime):
                d = d.date()
                
            if today <= d <= window_end:
                days_until = (d - today).days
                upcoming.append({
                    "festival_id": fest_id,
                    "festival_name": fest_info.get("name"),
                    "date": str(d),
                    "days_until": days_until,
                    "ramp_up_days": fest_info.get("ramp_up_days"),
                    "post_days": fest_info.get("post_days"),
                    "demand_impact": fest_info.get("peak_offset")
                })
                
    upcoming.sort(key=lambda x: x["days_until"])
    return {
        "window_days": days_ahead,
        "total_upcoming": len(upcoming),
        "festivals": upcoming,
        "today": str(today)
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
def run_whatif_scenario(sku_id: str, price_change_pct: float = 0, promo_lift_pct: float = 0, demand_change_pct: float = 0, lead_time_change_days: int = 0, current_stock: int = 1500) -> dict:
    product = next((p for p in PRODUCTS if p.get("sku_id") == sku_id), None)
    if not product:
        return {"error": f"SKU {sku_id} not found."}
        
    gen = IndianFMCGDataGenerator()
    df = gen.generate()
    sku_df = df[df["sku_id"] == sku_id].copy()
    
    agg_df = sku_df.groupby("date").agg({"units_sold": "sum", "revenue_inr": "sum"}).reset_index()
    agg_df["sku_id"] = sku_id
    agg_df["region_id"] = "ALL"
    
    engine = IndianSeasonalityEngine()
    featured_df = engine.engineer_features(agg_df)
    
    selector = ModelAutoSelector(test_days=60)
    result = selector.evaluate_and_select(featured_df)
    base_forecast = result.get("winning_forecast")
    
    ELASTICITY = -1.2
    eff_lt = max(1, DEFAULT_LEAD_TIME_DAYS + lead_time_change_days)
    price_delta = price_change_pct / 100.0
    elasticity_demand_delta = price_delta * ELASTICITY
    base_price = product.get("base_price", 100)
    eff_price = base_price * (1.0 + price_delta)
    eff_demand_scale = (1 + demand_change_pct/100) * (1 + elasticity_demand_delta) * (1 + promo_lift_pct/100)
    
    sim_forecast = base_forecast.copy()
    sim_forecast['predicted_units'] = (base_forecast['predicted_units'] * eff_demand_scale).clip(lower=0)
    
    sim_product = product.copy()
    sim_product["base_price"] = eff_price
    
    calc_base = OperationsImpactCalculator(lead_time_days=DEFAULT_LEAD_TIME_DAYS)
    base_impact = calc_base.calculate_sku_impact(product, featured_df, base_forecast, current_stock, 'A')
    
    calc_sim = OperationsImpactCalculator(lead_time_days=eff_lt)
    sim_impact = calc_sim.calculate_sku_impact(sim_product, featured_df, sim_forecast, current_stock, 'A')
    
    if "inventory_trajectory" in base_impact: del base_impact["inventory_trajectory"]
    if "inventory_trajectory" in sim_impact: del sim_impact["inventory_trajectory"]
    
    base_total = base_forecast['predicted_units'].sum()
    sim_total = sim_forecast['predicted_units'].sum()
    forecast_change_pct = ((sim_total - base_total) / base_total * 100) if base_total > 0 else 0
    
    return {
        "scenario_parameters": {
            "price_change_pct": price_change_pct,
            "promo_lift_pct": promo_lift_pct,
            "demand_change_pct": demand_change_pct,
            "lead_time_change_days": lead_time_change_days,
            "effective_lead_time": eff_lt,
            "effective_price": eff_price,
            "effective_demand_scale": eff_demand_scale
        },
        "simulated_impact": sim_impact,
        "baseline_comparison": base_impact,
        "forecast_change_pct": float(forecast_change_pct)
    }
