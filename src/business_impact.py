"""
DemandSense AI — Operations & Business Impact Calculator
=========================================================
Translates raw unit forecasts into actionable supply chain metrics & financial risk values:

  1. Safety Stock (SS)       = Z × σ_demand × √(Lead Time)
  2. Reorder Point (ROP)      = (Avg Daily Forecast × Lead Time) + SS
  3. Reorder Date Trigger    = Date when current inventory hits ROP
  4. ₹ Revenue at Risk       = Potential stockout units × Selling Price
  5. ₹ Overstock Holding     = Excess units × Unit Cost × Annual Holding Rate
  6. ABC-FSN Classification  = Strategic priority matrix (Revenue + Velocity)

Author: Anshul Silhare
"""

import numpy as np
import pandas as pd
from config import (
    SERVICE_LEVELS, HOLDING_COST_PCT,
    DEFAULT_LEAD_TIME_DAYS, GROSS_MARGIN_PCT,
)


class OperationsImpactCalculator:
    """
    Calculates inventory optimization parameters and financial risk metrics
    from forecasted demand.
    """

    def __init__(self, lead_time_days: int = DEFAULT_LEAD_TIME_DAYS,
                 holding_cost_pct: float = HOLDING_COST_PCT):
        self.lead_time_days = lead_time_days
        self.holding_cost_pct = holding_cost_pct

    def calculate_sku_impact(self,
                             product_info: dict,
                             historical_df: pd.DataFrame,
                             forecast_df: pd.DataFrame,
                             current_stock: int = 1500,
                             abc_class: str = "A") -> dict:
        """
        Calculate complete operational & financial impact metrics for one SKU.

        Args:
            product_info: dict with keys ['sku_id', 'name', 'base_price', 'category']
            historical_df: historical daily sales DataFrame
            forecast_df: 30-day forecast DataFrame with 'predicted_units'
            current_stock: current warehouse inventory level
            abc_class: 'A', 'B', or 'C' for service level Z-score selection

        Returns:
            dict containing all inventory parameters, PO trigger dates, and ₹ risk values.
        """
        unit_price = product_info.get("base_price", 100.0)

        # 1. Historical demand volatility (σ_demand)
        recent_history = historical_df["units_sold"].tail(60) if "units_sold" in historical_df else pd.Series([100])
        daily_sigma = float(recent_history.std() or 10.0)

        # 2. Service level Z-score
        service_info = SERVICE_LEVELS.get(abc_class.upper(), SERVICE_LEVELS["B"])
        z_score = service_info["z_score"]

        # 3. Safety Stock (SS) = Z × σ × √LT
        safety_stock = int(np.ceil(z_score * daily_sigma * np.sqrt(self.lead_time_days)))

        # 4. Forecasted metrics
        next_lt_forecast = forecast_df.head(self.lead_time_days)
        avg_daily_forecast = float(next_lt_forecast["predicted_units"].mean() if len(next_lt_forecast) > 0 else 100.0)
        total_30d_forecast = int(np.round(forecast_df["predicted_units"].sum()))

        # 5. Reorder Point (ROP) = (Daily Demand × LT) + Safety Stock
        lead_time_demand = int(np.ceil(avg_daily_forecast * self.lead_time_days))
        reorder_point = lead_time_demand + safety_stock

        # 6. Days of Supply (DOS) remaining with current stock
        daily_burn_rate = max(1.0, avg_daily_forecast)
        days_of_supply = round(current_stock / daily_burn_rate, 1)

        # 7. Projected inventory trajectory over 30 days & PO Trigger Date
        inv_trajectory = []
        stock = float(current_stock)
        po_trigger_date = None
        stockout_occurred = False
        stockout_units = 0

        for idx, row in forecast_df.iterrows():
            d = row["date"]
            pred = row["predicted_units"]
            stock -= pred

            if stock <= reorder_point and po_trigger_date is None:
                po_trigger_date = d

            if stock < 0:
                stockout_occurred = True
                stockout_units += abs(stock)
                stock = 0.0

            inv_trajectory.append({"date": d, "projected_stock": round(stock, 1)})

        if po_trigger_date is None:
            # Current stock lasts beyond 30 days
            po_trigger_status = "STABLE — Stock sufficient for >30 days"
            po_trigger_date_str = "No PO needed in next 30 days"
        else:
            po_trigger_status = "ACTION REQUIRED — Place PO soon"
            if hasattr(po_trigger_date, 'strftime'):
                po_trigger_date_str = po_trigger_date.strftime("%d %b %Y")
            else:
                po_trigger_date_str = pd.to_datetime(po_trigger_date).strftime("%d %b %Y")

        # 8. Financial Risk Quantification
        # Revenue at risk = stockout units × selling price
        revenue_at_risk_inr = round(stockout_units * unit_price, 2)

        # Overstock holding cost if current stock > (ROP + 30-day forecast)
        max_recommended_stock = reorder_point + total_30d_forecast
        excess_units = max(0, current_stock - max_recommended_stock)
        annual_holding_cost_inr = round(excess_units * unit_price * self.holding_cost_pct, 2)
        monthly_holding_cost_inr = round(annual_holding_cost_inr / 12.0, 2)

        # Recommended PO Quantity (EOQ approximation / 30-day replenishment)
        recommended_po_qty = max(0, total_30d_forecast + safety_stock - current_stock)

        return {
            "sku_id": product_info.get("sku_id", "SKU000"),
            "sku_name": product_info.get("name", "Product"),
            "category": product_info.get("category", "General"),
            "unit_price_inr": unit_price,
            "abc_class": abc_class,
            "target_service_level_pct": service_info["target_pct"],
            "lead_time_days": self.lead_time_days,
            "daily_demand_sigma": round(daily_sigma, 2),
            "safety_stock_units": safety_stock,
            "reorder_point_units": reorder_point,
            "avg_daily_forecast": round(avg_daily_forecast, 1),
            "total_30d_forecast_units": total_30d_forecast,
            "current_stock_units": current_stock,
            "days_of_supply": days_of_supply,
            "po_trigger_date": po_trigger_date_str,
            "po_trigger_status": po_trigger_status,
            "recommended_po_qty_units": recommended_po_qty,
            "recommended_po_value_inr": round(recommended_po_qty * unit_price, 2),
            "stockout_risk_units": int(stockout_units),
            "revenue_at_risk_inr": revenue_at_risk_inr,
            "excess_stock_units": excess_units,
            "monthly_holding_cost_inr": monthly_holding_cost_inr,
            "inventory_trajectory": pd.DataFrame(inv_trajectory),
        }

    def compute_abc_classification(self, sales_df: pd.DataFrame) -> pd.DataFrame:
        """
        Perform Pareto ABC classification on SKUs based on historical revenue.
          - Class A: Top 80% revenue
          - Class B: Next 15% revenue
          - Class C: Bottom 5% revenue
        """
        sku_rev = (sales_df.groupby(["sku_id", "sku_name"])["revenue_inr"]
                   .sum().reset_index().sort_values("revenue_inr", ascending=False))

        total_rev = sku_rev["revenue_inr"].sum()
        sku_rev["cum_rev"] = sku_rev["revenue_inr"].cumsum()
        sku_rev["cum_pct"] = (sku_rev["cum_rev"] / total_rev) * 100

        abc_labels = []
        for pct in sku_rev["cum_pct"]:
            if pct <= 80.0:
                abc_labels.append("A")
            elif pct <= 95.0:
                abc_labels.append("B")
            else:
                abc_labels.append("C")

        sku_rev["abc_class"] = abc_labels
        return sku_rev
