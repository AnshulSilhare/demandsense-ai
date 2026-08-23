"""
DemandSense AI — LLM Prescriptive Reasoning Agent
===================================================
Translates structured forecast outputs & inventory impact metrics into
executive natural language action plans.

Features:
  1. Primary Engine: Google Gemini API (gemini-1.5-flash / gemini-pro)
  2. Offline Fallback Engine: Rule-based template generator (100% reliable)
  3. Structured Output Parsing: Action items, financial risk, PO timing

Author: Anshul Silhare
"""

import os
import json
import numpy as np
import pandas as pd


class LLMPrescriptiveAgent:
    """LLM reasoning agent for demand forecasting and inventory action plans."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.use_gemini = False

        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel("gemini-1.5-flash")
                self.use_gemini = True
            except Exception as e:
                print(f"[LLM Agent] Gemini API initialization failed: {e}. Falling back to Rule Engine.")

    def generate_prescriptive_report(self, impact_dict: dict, winning_model_name: str, mape: float) -> dict:
        """
        Generate natural language prescriptive report.

        Args:
            impact_dict: Dict output from OperationsImpactCalculator
            winning_model_name: Name of winning forecasting model (e.g. 'Prophet')
            mape: MAPE error % of winning model

        Returns:
            dict containing:
              - executive_summary
              - recommended_action
              - financial_risk_narrative
              - model_rationale
              - priority_level ('CRITICAL', 'WARNING', 'INFO')
        """
        if self.use_gemini:
            try:
                return self._call_gemini_api(impact_dict, winning_model_name, mape)
            except Exception as e:
                print(f"[LLM Agent] Gemini call failed ({e}). Using offline engine.")
                return self._generate_rule_based_report(impact_dict, winning_model_name, mape)
        else:
            return self._generate_rule_based_report(impact_dict, winning_model_name, mape)

    def _call_gemini_api(self, impact_dict: dict, winning_model_name: str, mape: float) -> dict:
        """Call Gemini API with structured prompt."""
        prompt = f"""
You are an expert Chief Supply Chain Officer (CSCO) & Senior Operations Analyst at an Indian FMCG company.

Analyze the following operational & forecast metrics for {impact_dict['sku_name']} ({impact_dict['sku_id']}):

PRODUCT & INVENTORY STATUS:
- Category: {impact_dict['category']}
- MRP: ₹{impact_dict['unit_price_inr']}
- Current Inventory: {impact_dict['current_stock_units']} units ({impact_dict['days_of_supply']} days of supply)
- Safety Stock: {impact_dict['safety_stock_units']} units
- Reorder Point (ROP): {impact_dict['reorder_point_units']} units
- Lead Time: {impact_dict['lead_time_days']} days

FORECAST & MODEL METRICS:
- Winning Forecast Model: {winning_model_name} (MAPE: {mape}%)
- 30-Day Projected Demand: {impact_dict['total_30d_forecast_units']} units
- PO Trigger Status: {impact_dict['po_trigger_status']}
- Recommended PO Date: {impact_dict['po_trigger_date']}
- Recommended PO Qty: {impact_dict['recommended_po_qty_units']} units (Value: ₹{impact_dict['recommended_po_value_inr']:,.2f})

FINANCIAL RISK:
- Stockout Risk: {impact_dict['stockout_risk_units']} units -> Revenue at Risk: ₹{impact_dict['revenue_at_risk_inr']:,.2f}
- Excess Stock: {impact_dict['excess_stock_units']} units -> Monthly Holding Cost: ₹{impact_dict['monthly_holding_cost_inr']:,.2f}

INSTRUCTIONS:
Generate a concise, high-impact executive summary report in JSON format with these exact keys:
1. "priority_level": "CRITICAL" if revenue at risk > 0, "WARNING" if PO needed in <7 days, else "INFO"
2. "executive_summary": 2 clear sentences highlighting current state & key risk.
3. "recommended_action": Concrete step-by-step procurement directive (PO quantity, date, supplier urgency).
4. "financial_risk_narrative": Quantified rupee impact comparing stockout risk vs holding cost.
5. "model_rationale": 1-2 sentences explaining why {winning_model_name} was selected.

Return ONLY valid JSON.
"""
        response = self.model.generate_content(prompt)
        text = response.text.strip()

        # Clean JSON formatting backticks if present
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]

        return json.loads(text.strip())

    def _generate_rule_based_report(self, impact_dict: dict, winning_model_name: str, mape: float) -> dict:
        """Offline template engine guaranteeing 100% uptime without external API dependencies."""
        sku_name = impact_dict['sku_name']
        rev_at_risk = impact_dict['revenue_at_risk_inr']
        po_date = impact_dict['po_trigger_date']
        po_qty = impact_dict['recommended_po_qty_units']
        po_val = impact_dict['recommended_po_value_inr']
        dos = impact_dict['days_of_supply']
        stock = impact_dict['current_stock_units']
        rop = impact_dict['reorder_point_units']

        # Determine Priority Level
        if rev_at_risk > 0:
            priority = "CRITICAL"
        elif stock <= rop:
            priority = "WARNING"
        else:
            priority = "INFO"

        # Executive Summary
        if priority == "CRITICAL":
            exec_sum = (f"{sku_name} inventory is severely depleted ({dos} days of supply remaining). "
                        f"Projected demand will trigger a stockout resulting in ₹{rev_at_risk:,.2f} of revenue at risk.")
        elif priority == "WARNING":
            exec_sum = (f"{sku_name} stock ({stock} units) has crossed the Reorder Point ({rop} units). "
                        f"Action is required to avoid stockouts within the next 30 days.")
        else:
            exec_sum = (f"{sku_name} inventory remains healthy at {stock} units ({dos} days of supply). "
                        f"Demand is tracking as expected with no immediate stockout risk.")

        # Recommended Action
        if po_qty > 0:
            rec_action = (f"Issue Purchase Order for {po_qty:,} units (Total Value: ₹{po_val:,.2f}) "
                          f"by {po_date}. Maintain supplier lead time constraint of {impact_dict['lead_time_days']} days.")
        else:
            rec_action = (f"No purchase order needed at present. Re-evaluate stock on {po_date} "
                          f"or when inventory drops below {rop:,} units.")

        # Financial Risk Narrative
        if rev_at_risk > 0:
            fin_narrative = (f"Stockout Risk: {impact_dict['stockout_risk_units']:,} unmet units representing "
                             f"₹{rev_at_risk:,.2f} in lost gross revenue. Expedite PO to mitigate margin leakage.")
        elif impact_dict['excess_stock_units'] > 0:
            fin_narrative = (f"Holding Risk: {impact_dict['excess_stock_units']:,} excess units incurring "
                             f"₹{impact_dict['monthly_holding_cost_inr']:,.2f}/month in carrying costs.")
        else:
            fin_narrative = f"Inventory levels are balanced. Annual holding costs estimated at 25% of working capital."

        # Model Rationale
        if "Prophet" in winning_model_name:
            model_rat = (f"{winning_model_name} selected (MAPE: {mape}%) due to strong capability in modeling "
                         f"Indian festival seasonality curves and holiday proximity effects.")
        elif "XGBoost" in winning_model_name:
            model_rat = (f"{winning_model_name} selected (MAPE: {mape}%) for superior handling of non-linear "
                         f"feature interactions across temperature, weekend, and salary cycle flags.")
        elif "SARIMAX" in winning_model_name or "ARIMA" in winning_model_name:
            model_rat = (f"{winning_model_name} selected (MAPE: {mape}%) capturing complex weekly autocorrelation "
                         f"and stationary time series trends.")
        else:
            model_rat = (f"{winning_model_name} selected (MAPE: {mape}%) providing robust baseline performance "
                         f"with minimal variance for steady demand items.")

        return {
            "priority_level": priority,
            "executive_summary": exec_sum,
            "recommended_action": rec_action,
            "financial_risk_narrative": fin_narrative,
            "model_rationale": model_rat,
        }
