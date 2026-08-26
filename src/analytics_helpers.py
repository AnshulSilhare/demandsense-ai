"""
DemandSense AI — Analytics Helper Module
========================================
Utility calculations supporting visual analytics in the V2 Control Tower:
  - Additive time-series seasonal decomposition (Trend, Seasonality, Residuals)
  - Radar chart data normalization for model comparison
  - Festival demand impact summary per product

Author: Anshul Silhare
"""

import numpy as np
import pandas as pd
from config import PRODUCTS, INDIAN_FESTIVALS


def decompose_time_series(df: pd.DataFrame, period: int = 7) -> pd.DataFrame:
    """
    Perform classical additive time-series decomposition on daily sales.

    Y(t) = Trend(t) + Seasonal(t) + Residual(t)

    Returns DataFrame with columns:
      ['date', 'units_sold', 'trend', 'seasonal', 'residual']
    """
    ts = df.sort_values("date").copy()
    y = ts["units_sold"].values

    if len(y) < (period * 2):
        # Return raw series if data too short
        ts["trend"] = y
        ts["seasonal"] = 0.0
        ts["residual"] = 0.0
        return ts

    # 1. Trend component via centered moving average
    trend = pd.Series(y).rolling(window=period, center=True, min_periods=1).mean().values

    # 2. Detrended series
    detrended = y - trend

    # 3. Seasonal component (average pattern by day of week)
    dow = ts["date"].dt.dayofweek.values
    seasonal_dow = {}
    for d in range(7):
        mask = dow == d
        seasonal_dow[d] = np.nanmean(detrended[mask]) if np.any(mask) else 0.0

    # Center seasonal values so they sum to ~0 across a week
    mean_s = np.mean(list(seasonal_dow.values()))
    for d in seasonal_dow:
        seasonal_dow[d] -= mean_s

    seasonal = np.array([seasonal_dow[d] for d in dow])

    # 4. Residual noise component
    residual = y - trend - seasonal

    ts["trend"] = np.round(trend, 2)
    ts["seasonal"] = np.round(seasonal, 2)
    ts["residual"] = np.round(residual, 2)

    return ts


def prepare_radar_data(leaderboard_df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare normalized performance scores (0 to 100, 100 = best) for Radar Chart.

    Inverts error metrics so that higher scores represent better accuracy.
    """
    df = leaderboard_df.copy()

    metrics = ["mape", "rmse", "mae", "wape"]
    radar_rows = []

    for metric in metrics:
        if metric not in df.columns:
            continue

        vals = df[metric].values
        # Handle failed models (999.0)
        valid_vals = vals[vals < 900.0]
        max_val = np.max(valid_vals) if len(valid_vals) > 0 else 100.0
        min_val = np.min(valid_vals) if len(valid_vals) > 0 else 0.0

        for idx, row in df.iterrows():
            m_val = row[metric]
            if m_val >= 900.0:
                score = 0.0
            elif max_val == min_val:
                score = 100.0
            else:
                # Invert: min error -> 100 score, max error -> 20 score
                score = 100.0 - 80.0 * ((m_val - min_val) / max(1e-5, max_val - min_val))

            radar_rows.append({
                "model_name": row["model_name"],
                "metric": metric.upper(),
                "score": round(score, 1),
                "actual_value": row[metric],
            })

    return pd.DataFrame(radar_rows)


def get_festival_impact_summary(sku_id: str) -> pd.DataFrame:
    """
    Extract festival demand multipliers for a specific SKU from config.py.
    Returns DataFrame with columns: ['festival_name', 'multiplier_pct', 'impact_type']
    """
    norm = sku_id.replace("-", "").upper() if sku_id else "SKU001"
    sku_info = next((p for p in PRODUCTS if p.get("sku_id", "").replace("-", "").upper() == norm), PRODUCTS[0] if PRODUCTS else None)
    if not sku_info:
        return pd.DataFrame()

    seasonality = sku_info.get("seasonality", {})
    records = []

    for fest_key, fest_info in INDIAN_FESTIVALS.items():
        mult = seasonality.get(fest_key, 1.0)
        change_pct = (mult - 1.0) * 100.0

        if change_pct > 0:
            impact_type = "DEMAND BOOST (Surge)"
        elif change_pct < 0:
            impact_type = "DEMAND DIP (Fasting/Off-season)"
        else:
            impact_type = "NEUTRAL (No effect)"

        records.append({
            "festival": fest_info["name"],
            "multiplier": mult,
            "change_pct": round(change_pct, 1),
            "impact_type": impact_type,
            "ramp_up_days": fest_info["ramp_up_days"],
        })

    return pd.DataFrame(records).sort_values("multiplier", ascending=False)


def is_delta_favorable(metric_key: str, delta_pct: float) -> bool:
    """
    Direction-aware delta helper:
    For inverse metrics like revenue at risk or stockout risk, a rise (positive delta) is BAD news.
    """
    inverse_metrics = {"revenue_at_risk", "rop_breach_days", "stockout_probability", "revenue_at_risk_inr"}
    rose = delta_pct >= 0
    return not rose if metric_key in inverse_metrics else rose


def generate_svg_sparkline(values, line_color="#6E56CF", fill_opacity=0.35, width=120, height=32) -> str:
    """
    Generate a Catmull-Rom smoothed Bezier SVG sparkline string with soft gradient fill.
    Matches the smooth curved sparklines in the blueprint.
    """
    if len(values) < 2:
        return ""

    vals = np.array(values, dtype=float)
    min_v, max_v = np.min(vals), np.max(vals)
    range_v = max(1e-5, max_v - min_v)

    n = len(vals)
    dx = width / max(1, n - 1)
    padding = 3
    h_eff = height - 2 * padding

    points = []
    for i, v in enumerate(vals):
        x = i * dx
        y = height - padding - ((v - min_v) / range_v * h_eff)
        points.append((x, y))

    if len(points) == 2:
        line_path = f"M {points[0][0]:.1f},{points[0][1]:.1f} L {points[1][0]:.1f},{points[1][1]:.1f}"
    else:
        # Smooth Bezier curve control points
        path_cmds = [f"M {points[0][0]:.1f},{points[0][1]:.1f}"]
        for i in range(len(points) - 1):
            p0 = points[max(0, i - 1)]
            p1 = points[i]
            p2 = points[i + 1]
            p3 = points[min(len(points) - 1, i + 2)]

            cp1x = p1[0] + (p2[0] - p0[0]) / 6.0
            cp1y = p1[1] + (p2[1] - p0[1]) / 6.0
            cp2x = p2[0] - (p3[0] - p1[0]) / 6.0
            cp2y = p2[1] - (p3[1] - p1[1]) / 6.0

            path_cmds.append(f"C {cp1x:.1f},{cp1y:.1f} {cp2x:.1f},{cp2y:.1f} {p2[0]:.1f},{p2[1]:.1f}")
        line_path = " ".join(path_cmds)

    fill_path = f"{line_path} L {width:.1f},{height} L 0,{height} Z"
    grad_id = f"sparkGrad_{abs(hash(tuple(vals[:5]))) % 100000}"

    svg = f'''<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" style="width:100%;height:{height}px;display:block;margin-top:8px;">
        <defs>
            <linearGradient id="{grad_id}" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="{line_color}" stop-opacity="{fill_opacity}"/>
                <stop offset="100%" stop-color="{line_color}" stop-opacity="0"/>
            </linearGradient>
        </defs>
        <path d="{fill_path}" fill="url(#{grad_id})" stroke="none" />
        <path d="{line_path}" fill="none" stroke="{line_color}" stroke-width="1.75" stroke-linecap="round" />
        <circle cx="{points[-1][0]:.1f}" cy="{points[-1][1]:.1f}" r="2.5" fill="{line_color}" />
    </svg>'''
    return svg
