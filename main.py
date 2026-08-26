"""
DemandSense AI — FastAPI Backend
=================================
Serves the custom frontend and exposes JSON API endpoints
for all forecasting, analytics, and export operations.

Architecture decision: Default dataset is loaded once at startup (shared/read-only).
CSV uploads are session-scoped via cookie-based TTL dict (30-min expiry).
"""

import os
import sys
import io
import uuid
import time
import hashlib
import logging
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from functools import lru_cache

import numpy as np
import pandas as pd
from fastapi import FastAPI, Query, Request, Response, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import gzip
import json
import asyncio

# ── Ensure project root is on sys.path so `config` / `src` imports work ──
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Load .env if available ──
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

# ── Project imports (unchanged src/ modules) ──
from config import (
    PRODUCTS, REGIONS, SERVICE_LEVELS, DEFAULT_LEAD_TIME_DAYS,
    VERSION, INDIAN_FESTIVALS, PROJECT_NAME
)
from src.forecasting.auto_selector import ModelAutoSelector
from src.business_impact import OperationsImpactCalculator
from src.llm_agent import LLMPrescriptiveAgent
from src.pdf_exporter import generate_executive_pdf_report
from src.analytics_helpers import (
    decompose_time_series, prepare_radar_data,
    get_festival_impact_summary, generate_svg_sparkline, is_delta_favorable
)

# ── Logging ──
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("demandsense")

# ═══════════════════════════════════════════════════════════════
# GLOBAL STATE — loaded once at startup, shared read-only
# ═══════════════════════════════════════════════════════════════
DEFAULT_DF: pd.DataFrame = pd.DataFrame()
SESSION_STORE: dict = {}  # session_id → {"df": DataFrame, "expires": datetime}
SESSION_TTL = timedelta(minutes=30)


def _load_default_data() -> pd.DataFrame:
    """Load the default dataset using the same fallback chain as the Streamlit app."""
    processed = PROJECT_ROOT / "data" / "processed" / "featured_sales.csv"
    raw = PROJECT_ROOT / "data" / "raw" / "indian_fmcg_sales.csv"

    if processed.exists():
        logger.info(f"Loading processed data from {processed}")
        df = pd.read_csv(processed, parse_dates=["date"])
        # Optimize memory footprint for free-tier containers
        for col in df.select_dtypes(include=["float64"]).columns:
            df[col] = df[col].astype("float32")
        for col in df.select_dtypes(include=["int64"]).columns:
            if col != "date":
                df[col] = df[col].astype("int32")
        return df

    if raw.exists():
        logger.info(f"Loading raw data from {raw}, engineering features...")
        df = pd.read_csv(raw, parse_dates=["date"])
        try:
            from src.feature_engine import IndianSeasonalityEngine
            engine = IndianSeasonalityEngine()
            df = engine.engineer_features(df)
            for col in df.select_dtypes(include=["float64"]).columns:
                df[col] = df[col].astype("float32")
        except Exception as e:
            logger.warning(f"Feature engineering failed: {e}")
        return df

    logger.info("No data files found — generating synthetic data...")
    from src.data_generator import IndianFMCGDataGenerator
    gen = IndianFMCGDataGenerator()
    df = gen.generate()
    try:
        from src.feature_engine import IndianSeasonalityEngine
        engine = IndianSeasonalityEngine()
        df = engine.engineer_features(df)
    except Exception as e:
        logger.warning(f"Feature engineering on synthetic data failed: {e}")
    return df


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════
def _get_session_df(request: Request) -> pd.DataFrame:
    """Return session-scoped DataFrame if uploaded, else default."""
    global DEFAULT_DF
    sid = request.cookies.get("ds_session_id")
    if sid and sid in SESSION_STORE:
        entry = SESSION_STORE[sid]
        if datetime.now() < entry["expires"]:
            return entry["df"]
        else:
            del SESSION_STORE[sid]
    if DEFAULT_DF is None or DEFAULT_DF.empty:
        DEFAULT_DF = _load_default_data()
    return DEFAULT_DF


def _cleanup_sessions():
    """Evict expired sessions."""
    now = datetime.now()
    expired = [k for k, v in SESSION_STORE.items() if now >= v["expires"]]
    for k in expired:
        del SESSION_STORE[k]


def _filter_data(df: pd.DataFrame, sku_id: str, region: str = "ALL") -> pd.DataFrame:
    """Filter and aggregate the master dataset by SKU and region, matching app.py get_filtered_timeseries."""
    if df.empty:
        return df
    exclude_cols = {"sku_id", "sku_name", "category", "region_id", "region_name", "unit_price_inr", "revenue_inr", "date"}
    numeric_cols = [c for c in df.columns if c not in exclude_cols and pd.api.types.is_numeric_dtype(df[c])]
    if "units_sold" not in numeric_cols:
        numeric_cols.insert(0, "units_sold")

    norm_sku = sku_id.replace("-", "").upper()
    sku_mask = df["sku_id"].astype(str).str.replace("-", "").str.upper() == norm_sku

    if region == "ALL":
        filtered = df[sku_mask].groupby("date")[numeric_cols].sum().reset_index()
    else:
        if "region_id" in df.columns:
            filtered = df[sku_mask & (df["region_id"] == region)].groupby("date")[numeric_cols].sum().reset_index()
        else:
            filtered = df[sku_mask].groupby("date")[numeric_cols].sum().reset_index()
    return filtered.sort_values("date").reset_index(drop=True)


def _get_product_info(sku_id: str) -> dict:
    """Get product info dict from config."""
    norm = sku_id.replace("-", "").upper()
    return next((p for p in PRODUCTS if p.get("sku_id", "").replace("-", "").upper() == norm), PRODUCTS[0])


def _parse_service_level(sl: str) -> str:
    """Parse service level string like 'A (98%)' or 'A' or 'B' to just 'A', 'B', 'C'."""
    if not sl:
        return "A"
    clean = str(sl).strip().upper()
    if clean.startswith("A"):
        return "A"
    if clean.startswith("B"):
        return "B"
    if clean.startswith("C"):
        return "C"
    return "A"


def _compute_kpi_bar(filtered_df, forecast_df, impact_data, sku_info):
    """Compute the 4 KPI values + deltas + sparklines for the command bar."""
    unit_price = float(sku_info.get("base_price", 100))

    # KPI 1: 30-Day Demand Forecast
    forecast_units = int(forecast_df["predicted_units"].sum())
    hist_last30 = float(filtered_df.tail(30)["units_sold"].sum())
    hist_prev30 = float(filtered_df.tail(60).head(30)["units_sold"].sum())
    demand_delta = float(((hist_last30 - hist_prev30) / max(1.0, hist_prev30)) * 100.0)

    # KPI 2: Projected Revenue
    proj_revenue = float(forecast_units * unit_price)
    rev_delta = float(demand_delta)  # Same ratio (flat price assumption)

    # KPI 3: Safety Stock Compliance %
    dos = float(impact_data.get("days_of_supply", 0.0))
    compliance = float(min(1.0, dos / 30.0) * 100.0)
    stock = float(impact_data.get("current_stock_units", 0.0))
    avg_prev = float(filtered_df.tail(60).head(30)["units_sold"].mean())
    prev_dos = float(stock / max(1.0, avg_prev))
    prev_compliance = float(min(1.0, prev_dos / 30.0) * 100.0)
    compliance_delta = float(compliance - prev_compliance)

    # KPI 4: Revenue at Risk
    rev_risk = float(impact_data.get("revenue_at_risk_inr", 0.0))
    prev_excess = float(max(0.0, hist_prev30 - stock) * unit_price * 0.15)
    risk_delta = float(((rev_risk - prev_excess) / max(1.0, prev_excess)) * 100.0) if prev_excess > 0 else 0.0

    # Sparklines (last 30 days of historical data)
    spark_values = [float(x) for x in filtered_df.tail(30)["units_sold"].tolist()]

    return {
        "kpis": [
            {
                "label": "30-Day Demand Forecast",
                "value": forecast_units,
                "value_fmt": f"{forecast_units:,}",
                "unit": "units",
                "delta_pct": round(demand_delta, 1),
                "favorable": bool(is_delta_favorable("demand", demand_delta)),
                "chip": "D", "chip_color": "indigo",
                "sparkline": spark_values
            },
            {
                "label": "Projected Revenue (30D)",
                "value": proj_revenue,
                "value_fmt": f"₹{proj_revenue / 100000:.1f}L" if proj_revenue < 1e7 else f"₹{proj_revenue / 1e7:.2f}Cr",
                "unit": "INR",
                "delta_pct": round(rev_delta, 1),
                "favorable": bool(is_delta_favorable("revenue", rev_delta)),
                "chip": "₹", "chip_color": "gold",
                "sparkline": spark_values
            },
            {
                "label": "Safety Stock Compliance",
                "value": round(compliance, 1),
                "value_fmt": f"{compliance:.1f}%",
                "unit": "%",
                "delta_pct": round(compliance_delta, 1),
                "favorable": bool(is_delta_favorable("compliance", compliance_delta)),
                "chip": "SS", "chip_color": "teal",
                "sparkline": spark_values
            },
            {
                "label": "Revenue at Risk",
                "value": rev_risk,
                "value_fmt": f"₹{rev_risk / 100000:.1f}L" if rev_risk < 1e7 else f"₹{rev_risk / 1e7:.2f}Cr",
                "unit": "INR",
                "delta_pct": round(risk_delta, 1),
                "favorable": bool(is_delta_favorable("risk", risk_delta)),
                "chip": "⚠", "chip_color": "red",
                "sparkline": spark_values
            }
        ]
    }


# ═══════════════════════════════════════════════════════════════
# IN-MEMORY FORECAST CACHE & PRECOMPUTED BUNDLE (Blazing Fast <1ms responses)
# ═══════════════════════════════════════════════════════════════
FORECAST_CACHE: dict = {}  # hash → {"result": ..., "time": float}
PRECOMPUTED_BUNDLE: dict = {}  # "default_SKU001" / hash → result dict
SKU_FORECAST_CACHE: dict = {}  # (sid, sku, region) → base forecast dict
DECOMP_CACHE: dict = {}
FESTIVAL_CACHE: dict = {}
ABC_CACHE: dict = {}
REGIONAL_CACHE: dict = {}
FI_CACHE: dict = {}
CACHE_TTL = 3600 * 24  # 24 hours for live calculations


def _cache_key(sid: Optional[str], sku: str, region: str, lt: int, sl: str, stock: int) -> str:
    session_prefix = sid or "global_default"
    raw = f"{session_prefix}|{sku}|{region}|{lt}|{sl}|{stock}"
    return hashlib.md5(raw.encode()).hexdigest()


def _get_cached_forecast(key: str):
    if key in FORECAST_CACHE:
        entry = FORECAST_CACHE[key]
        if time.time() - entry["time"] < CACHE_TTL:
            return entry["result"]
        del FORECAST_CACHE[key]
    return None


def _set_cached_forecast(key: str, result):
    FORECAST_CACHE[key] = {"result": result, "time": time.time()}
    # Evict oldest non-permanent entry if cache grows too large
    if len(FORECAST_CACHE) > 300:
        evictable = [k for k, v in FORECAST_CACHE.items() if v["time"] != float("inf")]
        if evictable:
            oldest = min(evictable, key=lambda k: FORECAST_CACHE[k]["time"])
            del FORECAST_CACHE[oldest]


def _get_or_compute_base_forecast(request: Request, sku: str, region: str, sid: Optional[str]):
    """Retrieve base ML forecast (history, winning model, forecast points) from RAM or compute once.
    For non-ALL regions, uses the ALL-region forecast as base but filters historical data by region."""
    norm_sku = sku.replace("-", "").upper() if sku else "SKU001"
    cache_k = (sid or "default", norm_sku, region)
    if cache_k in SKU_FORECAST_CACHE:
        return SKU_FORECAST_CACHE[cache_k]
    if (sid or "default", sku, region) in SKU_FORECAST_CACHE:
        return SKU_FORECAST_CACHE[(sid or "default", sku, region)]

    df = _get_session_df(request)
    filtered = _filter_data(df, norm_sku, region)
    sku_info = _get_product_info(norm_sku)

    # For non-ALL regions or custom sessions, try to use ALL-region precomputed forecast as base
    # This avoids expensive ML retraining
    all_cache_k = (sid or "default", norm_sku, "ALL")
    if all_cache_k in SKU_FORECAST_CACHE:
        all_base = SKU_FORECAST_CACHE[all_cache_k]
        # Build a region-specific entry using ALL's ML forecast but region-filtered history
        if not filtered.empty and len(filtered) >= 7:
            chart_history = filtered[["date", "units_sold"]].copy()
            chart_history["date"] = chart_history["date"].dt.strftime("%Y-%m-%d")
            chart_history["rolling_7d"] = filtered["units_sold"].rolling(7, min_periods=1).mean().round(1)
            entry = {
                "forecast_res": all_base["forecast_res"],
                "forecast_df": all_base["forecast_df"],
                "chart_history": chart_history.to_dict(orient="records"),
                "data_summary": all_base["data_summary"],
                "sku_info": sku_info,
                "filtered": filtered
            }
        else:
            # Region has too little data, fall back to ALL region data entirely
            entry = {**all_base, "sku_info": sku_info}
        SKU_FORECAST_CACHE[cache_k] = entry
        return entry

    # Check precomputed bundle for default SKU on ALL region
    if (not sid or sid not in SESSION_STORE):
        for test_key in [f"default_{norm_sku}", f"default_{sku}", norm_sku]:
            if test_key in PRECOMPUTED_BUNDLE:
                bundle = PRECOMPUTED_BUNDLE[test_key]
                forecast_res = bundle["forecast_res"]
                chart_history = bundle["chart_history"]
                data_summary = bundle["data_summary"]
                forecast_df = pd.DataFrame(forecast_res["winning_forecast"])

                # Build ALL-region entry first
                all_filtered = _filter_data(df, norm_sku, "ALL")
                all_entry = {
                    "forecast_res": forecast_res,
                    "forecast_df": forecast_df,
                    "chart_history": chart_history,
                    "data_summary": data_summary,
                    "sku_info": sku_info,
                    "filtered": all_filtered
                }
                SKU_FORECAST_CACHE[(sid or "default", norm_sku, "ALL")] = all_entry

                if region == "ALL":
                    SKU_FORECAST_CACHE[cache_k] = all_entry
                    return all_entry
                else:
                    # Build region-specific entry
                    if not filtered.empty and len(filtered) >= 7:
                        r_chart = filtered[["date", "units_sold"]].copy()
                        r_chart["date"] = r_chart["date"].dt.strftime("%Y-%m-%d")
                        r_chart["rolling_7d"] = filtered["units_sold"].rolling(7, min_periods=1).mean().round(1)
                        entry = {
                            "forecast_res": forecast_res,
                            "forecast_df": forecast_df,
                            "chart_history": r_chart.to_dict(orient="records"),
                            "data_summary": data_summary,
                            "sku_info": sku_info,
                            "filtered": filtered
                        }
                    else:
                        entry = all_entry
                    SKU_FORECAST_CACHE[cache_k] = entry
                    return entry

    if filtered.empty or len(filtered) < 30:
        raise HTTPException(status_code=400, detail=f"Insufficient data for SKU {sku} in region {region}")

    # Last resort: compute ML models from scratch (only for custom CSV uploads)
    selector = ModelAutoSelector(test_days=60, metric="mape")
    res = selector.evaluate_and_select(filtered)
    forecast_df = res["winning_forecast"]
    forecast_res = _serialize_forecast_res(res)

    chart_history = filtered[["date", "units_sold"]].copy()
    chart_history["date"] = chart_history["date"].dt.strftime("%Y-%m-%d")
    chart_history["rolling_7d"] = filtered["units_sold"].rolling(7, min_periods=1).mean().round(1)

    data_summary = {
        "data_start": filtered["date"].min().strftime("%b %d, %Y"),
        "data_end": filtered["date"].max().strftime("%b %d, %Y"),
        "total_days": int((filtered["date"].max() - filtered["date"].min()).days),
        "total_skus": int(df["sku_id"].nunique()),
    }

    entry = {
        "forecast_res": forecast_res,
        "forecast_df": forecast_df,
        "chart_history": chart_history.to_dict(orient="records"),
        "data_summary": data_summary,
        "sku_info": sku_info,
        "filtered": filtered
    }
    SKU_FORECAST_CACHE[cache_k] = entry
    return entry


# ═══════════════════════════════════════════════════════════════
# SERIALIZATION HELPERS (convert DataFrames/numpy to JSON-safe dicts)
# ═══════════════════════════════════════════════════════════════
def _df_to_records(df: pd.DataFrame) -> list:
    """Convert DataFrame to list of dicts, handling dates and numpy types."""
    records = df.copy()
    for col in records.columns:
        if pd.api.types.is_datetime64_any_dtype(records[col]):
            records[col] = records[col].dt.strftime("%Y-%m-%d")
    return records.to_dict(orient="records")


def _serialize_impact(impact: dict) -> dict:
    """Make impact_data JSON-serializable."""
    out = {}
    for k, v in impact.items():
        if isinstance(v, pd.DataFrame):
            out[k] = _df_to_records(v)
        elif isinstance(v, (np.integer,)):
            out[k] = int(v)
        elif isinstance(v, (np.floating,)):
            out[k] = float(v)
        elif isinstance(v, np.ndarray):
            out[k] = v.tolist()
        else:
            out[k] = v
    return out


def _serialize_forecast_res(res: dict) -> dict:
    """Serialize forecast results, including normalized radar scores."""
    leaderboard_df = res["leaderboard"]
    radar_df = prepare_radar_data(leaderboard_df)

    return {
        "winning_model_name": res["winning_model_name"],
        "winning_metrics": {k: float(v) for k, v in res["winning_metrics"].items()},
        "winning_forecast": _df_to_records(res["winning_forecast"]),
        "leaderboard": _df_to_records(res["leaderboard"]),
        "radar": _df_to_records(radar_df),
    }


# ═══════════════════════════════════════════════════════════════
# FASTAPI APP
# ═══════════════════════════════════════════════════════════════
app = FastAPI(title="DemandSense AI", version=VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    global DEFAULT_DF, PRECOMPUTED_BUNDLE, FORECAST_CACHE, SKU_FORECAST_CACHE
    DEFAULT_DF = _load_default_data()
    logger.info(f"Loaded {len(DEFAULT_DF):,} rows, {DEFAULT_DF['sku_id'].nunique()} SKUs")

    # Load precomputed forecasts bundle (<2ms load time)
    cache_file = PROJECT_ROOT / "data" / "processed" / "precomputed_forecasts.json.gz"
    if cache_file.exists():
        try:
            logger.info(f"Loading precomputed forecast cache from {cache_file.name}...")
            with gzip.open(cache_file, "rt", encoding="utf-8") as f:
                PRECOMPUTED_BUNDLE = json.load(f)
            for k, v in PRECOMPUTED_BUNDLE.items():
                FORECAST_CACHE[k] = {"result": v, "time": float("inf")}
                # Pre-populate SKU_FORECAST_CACHE with all aliases for 0ms instant responses
                if k.startswith("default_"):
                    raw_sku = k.replace("default_", "")
                    norm_sku = raw_sku.replace("-", "").upper()
                    forecast_res = v.get("forecast_res", {})
                    forecast_df = pd.DataFrame(forecast_res.get("winning_forecast", []))
                    sku_info = v.get("sku_info", {})
                    chart_history = v.get("chart_history", [])
                    data_summary = v.get("data_summary", {})
                    filtered = _filter_data(DEFAULT_DF, raw_sku, "ALL")

                    entry = {
                        "forecast_res": forecast_res,
                        "forecast_df": forecast_df,
                        "chart_history": chart_history,
                        "data_summary": data_summary,
                        "sku_info": sku_info,
                        "filtered": filtered
                    }
                    num_suffix = norm_sku.replace("SKU", "")
                    for s_alias in [raw_sku, norm_sku, f"SKU-{num_suffix}", f"SKU{num_suffix}"]:
                        for sid_alias in ["default", "global_default", None]:
                            SKU_FORECAST_CACHE[(sid_alias, s_alias, "ALL")] = entry

            logger.info(f"Precomputed cache active ({len(PRECOMPUTED_BUNDLE)} keys ready in RAM for instant <1ms response).")
        except Exception as e:
            logger.warning(f"Failed to load precomputed forecast cache: {e}")

    if os.environ.get("GEMINI_API_KEY"):
        logger.info("GEMINI_API_KEY detected — Gemini LLM active")
    else:
        logger.info("GEMINI_API_KEY not set — using offline rule-based AI engine")
    logger.info("DemandSense AI startup complete — event loop ready.")


# ── Serve the SPA ──
app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT / "static")), name="static")


# ── Health & Keep-Alive Routes (supports GET, HEAD, POST, OPTIONS for all uptime monitors) ──
@app.api_route("/health", methods=["GET", "HEAD", "POST", "OPTIONS"])
@app.api_route("/api/health", methods=["GET", "HEAD", "POST", "OPTIONS"])
@app.api_route("/ping", methods=["GET", "HEAD", "POST", "OPTIONS"])
@app.api_route("/status", methods=["GET", "HEAD", "POST", "OPTIONS"])
def health():
    """Lightweight health check — no computation, no DB reads.
    Handles GET, HEAD, POST, OPTIONS from any uptime monitoring service (UptimeRobot, BetterStack, Cron-job, etc.)"""
    return JSONResponse(content={"status": "ok", "version": VERSION, "timestamp": datetime.utcnow().isoformat()})


@app.api_route("/", methods=["GET", "HEAD"])
@app.api_route("/index.html", methods=["GET", "HEAD"])
def root(request: Request):
    if request.method == "HEAD":
        return Response(status_code=200, media_type="text/html")
    response = FileResponse(str(PROJECT_ROOT / "static" / "index.html"))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ═══════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/config")
def get_config():
    """Return app configuration: products, regions, service levels, festivals, defaults."""
    return {
        "project_name": PROJECT_NAME,
        "version": VERSION,
        "products": PRODUCTS,
        "regions": REGIONS,
        "service_levels": SERVICE_LEVELS,
        "default_lead_time": DEFAULT_LEAD_TIME_DAYS,
        "festivals": {
            k: {"name": v["name"], "dates": [d.isoformat() for d in v["dates"]]}
            for k, v in INDIAN_FESTIVALS.items()
        }
    }


@app.get("/api/forecast")
async def get_forecast(
    request: Request,
    sku: str = Query(default="SKU001"),
    region: str = Query(default="ALL"),
    lead_time: int = Query(default=DEFAULT_LEAD_TIME_DAYS),
    service_level: str = Query(default="A"),
    stock: int = Query(default=25000)
):
    """Main endpoint: returns forecast, impact, LLM report, and KPI bar data.
    Base ML forecast is served from RAM (<0.1ms). Impact/KPI are recomputed per-parameter."""
    norm_sku = sku.replace("-", "").upper() if sku else "SKU001"
    sid = request.cookies.get("ds_session_id")
    abc_class = _parse_service_level(service_level)

    # 1. Check full result cache (same SKU + same params = exact hit)
    ck = _cache_key(sid, norm_sku, region, lead_time, abc_class, stock)
    cached = _get_cached_forecast(ck)
    if cached:
        return cached

    # 2. Get base ML forecast from RAM (instant for all 20 default SKUs)
    try:
        base = await asyncio.to_thread(_get_or_compute_base_forecast, request, norm_sku, region, sid)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Base forecast failed for {norm_sku}/{region}: {e}")
        raise HTTPException(status_code=500, detail=f"Forecast computation failed: {e}")

    # 3. Recompute Operations Impact with user's ACTUAL lead_time, stock, service_level
    calc = OperationsImpactCalculator(lead_time_days=lead_time)
    p_info = base["sku_info"]
    impact_data = calc.calculate_sku_impact(
        product_info=p_info,
        historical_df=base["filtered"],
        forecast_df=base["forecast_df"],
        current_stock=stock,
        abc_class=abc_class
    )

    agent = LLMPrescriptiveAgent()
    try:
        llm_report = agent.generate_prescriptive_report(
            impact_data, base["forecast_res"]["winning_model_name"],
            float(base["forecast_res"]["winning_metrics"]["mape"])
        )
    except Exception as e:
        logger.warning(f"LLM Prescriptive Agent fallback: {e}")
        llm_report = agent._generate_rule_based_report(
            impact_data, base["forecast_res"]["winning_model_name"],
            float(base["forecast_res"]["winning_metrics"]["mape"])
        )

    kpi_bar = _compute_kpi_bar(base["filtered"], base["forecast_df"], impact_data, p_info)

    result = {
        "forecast_res": base["forecast_res"],
        "impact_data": _serialize_impact(impact_data),
        "llm_report": llm_report,
        "kpi_bar": kpi_bar,
        "chart_history": base["chart_history"],
        "sku_info": p_info,
        "data_summary": base["data_summary"]
    }

    _set_cached_forecast(ck, result)
    return result


@app.get("/api/decomposition")
def get_decomposition(
    request: Request,
    sku: str = Query(default="SKU001"),
    region: str = Query(default="ALL")
):
    """Time series decomposition for Tab 1 (cached <1ms)."""
    norm_sku = sku.replace("-", "").upper() if sku else "SKU001"
    sid = request.cookies.get("ds_session_id")
    cache_k = (sid or "default", norm_sku, region)
    if cache_k in DECOMP_CACHE:
        return DECOMP_CACHE[cache_k]

    df = _get_session_df(request)
    filtered = _filter_data(df, norm_sku, region)
    if filtered.empty:
        raise HTTPException(status_code=400, detail="No data for decomposition")

    decomp = decompose_time_series(filtered.tail(120), period=7)
    res = {
        "dates": decomp["date"].dt.strftime("%Y-%m-%d").tolist(),
        "trend": decomp["trend"].round(2).tolist(),
        "seasonal": decomp["seasonal"].round(2).tolist(),
        "residual": decomp["residual"].round(2).tolist()
    }
    DECOMP_CACHE[cache_k] = res
    return res


@app.get("/api/festival-impact")
def get_festival_impact(sku: str = Query(default="SKU001")):
    """Festival multiplier summary for Tab 1 (cached <1ms)."""
    norm_sku = sku.replace("-", "").upper() if sku else "SKU001"
    if norm_sku in FESTIVAL_CACHE:
        return FESTIVAL_CACHE[norm_sku]

    fest_df = get_festival_impact_summary(norm_sku)
    if fest_df.empty:
        res = {"festivals": []}
    else:
        res = {"festivals": fest_df.to_dict(orient="records")}
    FESTIVAL_CACHE[norm_sku] = res
    return res


@app.get("/api/abc-classification")
def get_abc_classification(request: Request):
    """Pareto ABC classification table for Tab 3 (cached <1ms)."""
    sid = request.cookies.get("ds_session_id")
    cache_k = sid or "default"
    if cache_k in ABC_CACHE:
        return ABC_CACHE[cache_k]

    df = _get_session_df(request)
    calc = OperationsImpactCalculator()
    try:
        abc = calc.compute_abc_classification(df)
        res = {"table": _df_to_records(abc)}
        ABC_CACHE[cache_k] = res
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ABC classification failed: {e}")


@app.get("/api/regional-summary")
def get_regional_summary(request: Request, sku: str = Query(default="SKU001")):
    """Regional demand/revenue summary for Tab 3 map (cached <1ms)."""
    norm_sku = sku.replace("-", "").upper() if sku else "SKU001"
    sid = request.cookies.get("ds_session_id")
    cache_k = (sid or "default", norm_sku)
    if cache_k in REGIONAL_CACHE:
        return REGIONAL_CACHE[cache_k]

    df = _get_session_df(request)
    sku_mask = df["sku_id"].astype(str).str.replace("-", "").str.upper() == norm_sku
    sku_data = df[sku_mask]

    if "region_id" not in sku_data.columns or "revenue_inr" not in sku_data.columns:
        return {"regions": []}

    region_map = {r["id"]: r for r in REGIONS}
    summary = sku_data.groupby("region_id").agg(
        total_units=("units_sold", "sum"),
        total_revenue=("revenue_inr", "sum"),
    ).reset_index()

    result = []
    for _, row in summary.iterrows():
        rid = row["region_id"]
        rinfo = region_map.get(rid, {})
        result.append({
            "region_id": rid,
            "region_name": rinfo.get("name", rid),
            "lat": {"NORTH": 28.6, "SOUTH": 13.0, "WEST": 19.0, "EAST": 22.5, "CENTRAL": 23.2}.get(rid, 22.0),
            "lon": {"NORTH": 77.2, "SOUTH": 77.6, "WEST": 72.8, "EAST": 88.3, "CENTRAL": 79.5}.get(rid, 78.0),
            "total_units": int(row["total_units"]),
            "total_revenue": float(row["total_revenue"]),
        })
    res = {"regions": result}
    REGIONAL_CACHE[cache_k] = res
    return res


@app.get("/api/feature-importance")
async def get_feature_importance(
    request: Request,
    sku: str = Query(default="SKU001"),
    region: str = Query(default="ALL")
):
    """XGBoost feature importance for Tab 2 (cached <1ms)."""
    norm_sku = sku.replace("-", "").upper() if sku else "SKU001"
    sid = request.cookies.get("ds_session_id")
    cache_k = (sid or "default", norm_sku, region)
    if cache_k in FI_CACHE:
        return FI_CACHE[cache_k]

    df = _get_session_df(request)
    filtered = _filter_data(df, norm_sku, region)

    def _fit_fi():
        from src.forecasting.xgboost_model import XGBoostForecaster, FEATURE_COLS
        xgb_model = XGBoostForecaster()
        available = [c for c in FEATURE_COLS if c in filtered.columns]
        train_df = filtered.dropna(subset=available + ["units_sold"])
        if len(train_df) < 30:
            return {"features": []}
        xgb_model.fit(train_df)
        fi = xgb_model.feature_importances()
        fi_top = fi.head(10)
        total = fi_top.sum()
        features = [
            {"name": name, "importance": float(val), "pct": round(float(val / total * 100), 1)}
            for name, val in fi_top.items()
        ]
        return {"features": features}

    try:
        res = await asyncio.to_thread(_fit_fi)
        FI_CACHE[cache_k] = res
        return res
    except Exception as e:
        logger.warning(f"Feature importance failed: {e}")
        return {"features": []}


@app.post("/api/simulate")
def simulate_scenario(request: Request, body: dict):
    """What-If scenario simulation for Tab 4 (<1ms)."""
    sku = body.get("sku", "SKU001")
    region = body.get("region", "ALL")
    lead_time = body.get("lead_time", DEFAULT_LEAD_TIME_DAYS)
    service_level = body.get("service_level", "A")
    stock = body.get("stock", 25000)
    sim_lt_add = body.get("sim_lt_add", 0)
    sim_demand_mult = body.get("sim_demand_mult", 0)
    sim_price_mult = body.get("sim_price_mult", 0)
    sim_elasticity = body.get("sim_elasticity", -1.2)
    sim_promo = body.get("sim_promo", 0)

    norm_sku = sku.replace("-", "").upper() if sku else "SKU001"
    abc_class = _parse_service_level(service_level)
    df = _get_session_df(request)
    filtered = _filter_data(df, norm_sku, region)

    if filtered.empty:
        raise HTTPException(status_code=400, detail="No data for simulation")

    # Get baseline forecast instantly from RAM
    sid = request.cookies.get("ds_session_id")
    base = _get_or_compute_base_forecast(request, norm_sku, region, sid)
    base_forecast_df = base["forecast_df"].copy()

    calc = OperationsImpactCalculator(lead_time_days=lead_time)
    p_info = base["sku_info"]
    base_impact_raw = calc.calculate_sku_impact(
        product_info=p_info,
        historical_df=base["filtered"],
        forecast_df=base_forecast_df,
        current_stock=stock,
        abc_class=abc_class
    )
    base_impact = _serialize_impact(base_impact_raw)

    # Compute effective parameters
    eff_lt = max(1, lead_time + sim_lt_add)
    price_delta_pct = sim_price_mult / 100.0
    elasticity_demand_delta = price_delta_pct * sim_elasticity
    eff_dem_scale = (1.0 + sim_demand_mult / 100.0) * (1.0 + elasticity_demand_delta) * (1.0 + sim_promo / 100.0)

    base_price = p_info.get("base_price", 100)
    eff_price = base_price * (1.0 + price_delta_pct)

    # Modify forecast
    sim_forecast = base_forecast_df.copy()
    if isinstance(sim_forecast, list):
        sim_forecast = pd.DataFrame(sim_forecast)
    if "predicted_units" in sim_forecast.columns:
        sim_forecast["predicted_units"] = (sim_forecast["predicted_units"] * eff_dem_scale).clip(lower=0)

    # Re-run impact calculator with modified params
    sim_calc = OperationsImpactCalculator(lead_time_days=eff_lt)

    # Need to create proper DataFrames for the calculator
    sim_forecast_for_calc = sim_forecast.copy()
    if "date" in sim_forecast_for_calc.columns:
        sim_forecast_for_calc["date"] = pd.to_datetime(sim_forecast_for_calc["date"])

    sim_p_info = p_info.copy()
    sim_p_info["base_price"] = eff_price

    sim_impact = sim_calc.calculate_sku_impact(
        product_info=sim_p_info,
        historical_df=filtered,
        forecast_df=sim_forecast_for_calc,
        current_stock=stock,
        abc_class=abc_class
    )

    return {
        "sim_impact": _serialize_impact(sim_impact),
        "base_trajectory": base_impact.get("inventory_trajectory", []),
        "eff_lt": eff_lt,
        "eff_dem_scale": round(eff_dem_scale, 4),
        "eff_price": round(eff_price, 2),
    }


@app.post("/api/upload-csv")
async def upload_csv(request: Request, response: Response, file: UploadFile = File(...)):
    """Upload a custom CSV dataset for session-scoped use."""
    _cleanup_sessions()

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")

    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content), parse_dates=["date"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV: {e}")

    required_cols = {"date", "sku_id", "units_sold"}
    missing = required_cols - set(df.columns)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {missing}")

    # Try feature engineering
    try:
        from src.feature_engine import IndianSeasonalityEngine
        engine = IndianSeasonalityEngine()
        df = engine.engineer_features(df)
    except Exception as e:
        logger.warning(f"Feature engineering on uploaded CSV failed: {e}")

    # Store in session (TTL: 30 minutes, completely isolated from other visitors)
    sid = request.cookies.get("ds_session_id") or str(uuid.uuid4())
    SESSION_STORE[sid] = {"df": df, "expires": datetime.now() + SESSION_TTL}

    response.set_cookie("ds_session_id", sid, max_age=int(SESSION_TTL.total_seconds()), httponly=True)
    return {
        "status": "ok",
        "rows": len(df),
        "skus": int(df["sku_id"].nunique()),
        "date_range": f"{df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}"
    }


@app.get("/api/export/po-csv")
def export_po_csv(
    request: Request,
    sku: str = Query(default="SKU001"),
    region: str = Query(default="ALL"),
    lead_time: int = Query(default=DEFAULT_LEAD_TIME_DAYS),
    service_level: str = Query(default="A"),
    stock: int = Query(default=25000)
):
    """Download Purchase Order as CSV."""
    norm_sku = sku.replace("-", "").upper() if sku else "SKU001"
    sid = request.cookies.get("ds_session_id")
    abc_class = _parse_service_level(service_level)

    base = _get_or_compute_base_forecast(request, norm_sku, region, sid)
    calc = OperationsImpactCalculator(lead_time_days=lead_time)
    p_info = base["sku_info"]
    impact_raw = calc.calculate_sku_impact(
        product_info=p_info,
        historical_df=base["filtered"],
        forecast_df=base["forecast_df"],
        current_stock=stock,
        abc_class=abc_class
    )
    impact_data = _serialize_impact(impact_raw)

    unit_price = p_info.get("base_price", 100)
    rec_qty = impact_data.get("recommended_po_qty_units", 0)
    status_str = impact_data.get("po_trigger_status", "STABLE")

    po_df = pd.DataFrame([{
        "PO_ID": f"PO-2026-{norm_sku}-01",
        "SKU_ID": norm_sku,
        "SKU_Name": p_info.get("name", p_info.get("sku_name", "")),
        "Category": p_info.get("category", "FMCG"),
        "Recommended_Order_Qty": rec_qty,
        "Unit_Cost_INR": unit_price * 0.7,
        "Total_PO_Value_INR": impact_data.get("recommended_po_value_inr", rec_qty * unit_price * 0.7),
        "Lead_Time_Days": lead_time,
        "Priority": "URGENT" if "CRITICAL" in str(status_str) else ("HIGH" if "WARNING" in str(status_str) else "NORMAL")
    }])

    csv_buffer = io.StringIO()
    po_df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    filename = f"PO_{norm_sku}_{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        io.BytesIO(csv_buffer.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.get("/api/export/brief-pdf")
def export_brief_pdf(
    request: Request,
    sku: str = Query(default="SKU001"),
    region: str = Query(default="ALL"),
    lead_time: int = Query(default=DEFAULT_LEAD_TIME_DAYS),
    service_level: str = Query(default="A"),
    stock: int = Query(default=25000)
):
    """Download Executive PDF Brief."""
    norm_sku = sku.replace("-", "").upper() if sku else "SKU001"
    sid = request.cookies.get("ds_session_id")
    abc_class = _parse_service_level(service_level)

    base = _get_or_compute_base_forecast(request, norm_sku, region, sid)
    calc = OperationsImpactCalculator(lead_time_days=lead_time)
    p_info = base["sku_info"]
    impact_raw = calc.calculate_sku_impact(
        product_info=p_info,
        historical_df=base["filtered"],
        forecast_df=base["forecast_df"],
        current_stock=stock,
        abc_class=abc_class
    )
    impact_data_raw = _serialize_impact(impact_raw)

    agent = LLMPrescriptiveAgent()
    try:
        llm_report = agent.generate_prescriptive_report(
            impact_data_raw, base["forecast_res"]["winning_model_name"],
            float(base["forecast_res"]["winning_metrics"]["mape"])
        )
    except Exception as e:
        logger.warning(f"LLM Prescriptive Agent fallback: {e}")
        llm_report = agent._generate_rule_based_report(
            impact_data_raw, base["forecast_res"]["winning_model_name"],
            float(base["forecast_res"]["winning_metrics"]["mape"])
        )

    winning_model = base["forecast_res"]["winning_model_name"]
    winning_mape = base["forecast_res"]["winning_metrics"]["mape"]

    region_options = {"ALL": "National Aggregation (India)"}
    region_options.update({r["id"]: f"{r['name']} ({r['id']})" for r in REGIONS})
    region_name = region_options.get(region, "National Aggregation (India)")

    pdf_bytes = generate_executive_pdf_report(
        sku_info=p_info,
        region_name=region_name,
        impact_data=impact_data_raw,
        winning_model=winning_model,
        winning_mape=winning_mape,
        llm_report=llm_report
    )

    filename = f"Executive_Brief_{norm_sku}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ═══════════════════════════════════════════════════════════════
# ENTRYPOINT
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
