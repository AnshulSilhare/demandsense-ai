"""
DemandSense AI — Multi-Agent War Room
========================================
Implements Option C: Specialized agents that collaborate like a real operations team.

Architecture:
  1. Demand Planner Agent   — Forecasts, trends, seasonality analysis
  2. Inventory Controller   — Stock levels, safety stock, reorder decisions
  3. Risk Analyst           — Financial quantification, scenario comparison
  4. Executive Synthesizer  — Combines all specialist outputs into unified brief

Author: Anshul Silhare
"""

import os
import json
import logging
import re
from typing import Optional

logger = logging.getLogger("demandsense.warroom")

SPECIALISTS = {
    "demand_planner": {
        "role": "Demand Planner",
        "icon": "🔮",
        "system_prompt": """You are the Demand Planner specialist in a supply chain war room.
Your expertise: demand forecasting, trend analysis, seasonality patterns, festival impact.
Focus strictly on demand-side metrics. Be concise with specific numbers.""",
        "tools": ["run_demand_forecast", "get_upcoming_festivals", "list_available_skus"],
    },
    "inventory_controller": {
        "role": "Inventory Controller",
        "icon": "📦",
        "system_prompt": """You are the Inventory Controller specialist in a supply chain war room.
Your expertise: warehouse stock levels, safety stock, reorder points, days of supply, PO timing.
Focus strictly on inventory coverage and replenishment. Be concise with specific quantities and dates.""",
        "tools": ["check_inventory_status", "list_available_skus"],
    },
    "risk_analyst": {
        "role": "Risk Analyst",
        "icon": "💰",
        "system_prompt": """You are the Risk Analyst specialist in a supply chain war room.
Your expertise: financial risk quantification, revenue at risk, holding costs, scenario comparison.
Focus strictly on rupee financial implications (₹ INR). Quantify everything in ₹.""",
        "tools": ["check_inventory_status", "run_whatif_scenario"],
    },
}


class MultiAgentWarRoom:
    """
    Orchestrates multiple specialist agents to collaboratively analyze
    a supply chain query, then synthesizes their outputs.
    """

    def __init__(self, tools, api_key: Optional[str] = None):
        self.tools = tools
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.use_gemini = False
        self._genai = None

        if self.api_key:
            try:
                import google.generativeai as genai
                self._genai = genai
                genai.configure(api_key=self.api_key)
                self.use_gemini = True
                logger.info("[WarRoom] Gemini initialized for multi-agent collaboration.")
            except Exception as e:
                logger.warning(f"[WarRoom] Gemini init failed: {e}. Using offline engine.")

    async def analyze(self, query: str, session_context: dict = None) -> dict:
        session_context = session_context or {}
        # Re-check key
        if not self.use_gemini and os.environ.get("GEMINI_API_KEY"):
            try:
                import google.generativeai as genai
                self.api_key = os.environ.get("GEMINI_API_KEY")
                self._genai = genai
                genai.configure(api_key=self.api_key)
                self.use_gemini = True
            except Exception:
                pass

        specialist_reports = []
        all_tools_called = []

        for spec_id, spec in SPECIALISTS.items():
            report = await self._run_specialist(spec_id, spec, query, session_context)
            specialist_reports.append(report)
            all_tools_called.extend(report.get("tools_called", []))

        synthesis = self._synthesize_reports(query, specialist_reports)

        return {
            "query": query,
            "specialist_reports": specialist_reports,
            "synthesis": synthesis,
            "tools_called": list(set(all_tools_called)),
            "mode": "gemini" if self.use_gemini else "offline",
        }

    async def _run_specialist(self, spec_id, spec, query, session_context=None) -> dict:
        if self.use_gemini:
            try:
                return await self._run_gemini_specialist(spec_id, spec, query, session_context)
            except Exception as e:
                logger.error(f"[WarRoom] Specialist {spec_id} Gemini error: {e}. Using offline engine.")
                return self._run_offline_specialist(spec_id, spec, query, session_context)
        else:
            return self._run_offline_specialist(spec_id, spec, query, session_context)

    async def _run_gemini_specialist(self, spec_id, spec, query, session_context=None):
        genai = self._genai
        tools_called = []
        steps = []

        allowed_tools = spec["tools"]
        declarations = []
        for schema in self.tools.get_tool_schemas():
            if schema["name"] in allowed_tools:
                try:
                    declarations.append(genai.protos.FunctionDeclaration(
                        name=schema["name"],
                        description=schema["description"],
                        parameters=schema["parameters"],
                    ))
                except Exception:
                    pass

        gemini_tools = [genai.protos.Tool(function_declarations=declarations)] if declarations else None

        model = genai.GenerativeModel(
            model_name=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
            system_instruction=spec["system_prompt"],
            tools=gemini_tools,
        )

        context = ""
        if session_context:
            context = f"[Context: SKU={session_context.get('sku_id','SKU001')}, Stock={session_context.get('current_stock',1500)} units] "

        chat = model.start_chat()
        response = chat.send_message(context + query)

        for step_num in range(4):
            if not response.candidates or not response.candidates[0].content.parts:
                break
            candidate = response.candidates[0]

            function_responses = []
            final_text = ""
            has_text = False

            for part in candidate.content.parts:
                if hasattr(part, 'function_call') and part.function_call.name:
                    fn = part.function_call
                    tool_name = fn.name
                    tool_args = dict(fn.args) if fn.args else {}
                    for k, v in tool_args.items():
                        if isinstance(v, float) and v == int(v):
                            tool_args[k] = int(v)

                    tools_called.append(tool_name)
                    steps.append({"type": "tool_call", "tool": tool_name, "args": tool_args})

                    result_str = self.tools.call(tool_name, tool_args)
                    if len(result_str) > 2000:
                        result_str = result_str[:2000] + "..."

                    steps.append({"type": "tool_result", "tool": tool_name, "result": result_str})

                    function_responses.append(
                        genai.protos.Part(function_response=genai.protos.FunctionResponse(
                            name=tool_name, response={"result": result_str}
                        ))
                    )
                elif hasattr(part, 'text') and part.text:
                    has_text = True
                    final_text += part.text

            if function_responses:
                response = chat.send_message(genai.protos.Content(parts=function_responses))
                continue

            if has_text:
                return {
                    "specialist_id": spec_id,
                    "role": spec["role"],
                    "icon": spec["icon"],
                    "analysis": final_text,
                    "steps": steps,
                    "tools_called": tools_called,
                }

        return {
            "specialist_id": spec_id,
            "role": spec["role"],
            "icon": spec["icon"],
            "analysis": "Analysis synthesized based on domain tool execution.",
            "steps": steps,
            "tools_called": tools_called,
        }

    def _run_offline_specialist(self, spec_id, spec, query, session_context=None):
        session_context = session_context or {}
        skus = re.findall(r'SKU\d{3}', query.upper())
        target_sku = skus[0] if skus else session_context.get("sku_id", "SKU001")
        stock = session_context.get("current_stock", 1500)

        tools_called = []
        metrics = {}

        if spec_id == "demand_planner":
            fc_raw = self.tools.call("run_demand_forecast", {"sku_id": target_sku})
            tools_called.append("run_demand_forecast")
            fc = json.loads(fc_raw) if isinstance(fc_raw, str) else fc_raw

            fest_raw = self.tools.call("get_upcoming_festivals", {"days_ahead": 60})
            tools_called.append("get_upcoming_festivals")
            fest = json.loads(fest_raw) if isinstance(fest_raw, str) else fest_raw

            upcoming_str = ""
            fest_list = fest.get("festivals", [])
            upcoming_festival = None
            if fest_list:
                top_f = fest_list[0]
                upcoming_str = f" Approaching festival **{top_f['festival_name']}** in {top_f['days_until']} days will create an expected surge ({top_f['demand_impact']})."
                upcoming_festival = {
                    "name": top_f.get("festival_name", ""),
                    "days_until": top_f.get("days_until", 0),
                    "demand_impact": top_f.get("demand_impact", ""),
                }

            analysis = (
                f"**Demand Forecast & Seasonality ({target_sku}):**\n"
                f"- **Winning Auto-ML Model:** **{fc.get('winning_model', 'XGBoost')}** (MAPE: **{fc.get('mape_pct', 0):.2f}%**)\n"
                f"- **30-Day Forward Demand:** **{int(fc.get('total_30d_forecast_units', 0)):,} units** (Avg: **{fc.get('avg_daily_forecast', 0):.1f} units/day**)\n"
                f"- **Trajectory:** **{fc.get('forecast_trend', 'stable').capitalize()}**.{upcoming_str}"
            )

            metrics = {
                "winning_model": fc.get("winning_model", "XGBoost"),
                "mape_pct": round(fc.get("mape_pct", 0), 2),
                "total_30d_forecast_units": int(fc.get("total_30d_forecast_units", 0)),
                "avg_daily_forecast": round(fc.get("avg_daily_forecast", 0), 1),
                "forecast_trend": fc.get("forecast_trend", "stable"),
                "upcoming_festival": upcoming_festival,
            }

        elif spec_id == "inventory_controller":
            inv_raw = self.tools.call("check_inventory_status", {"sku_id": target_sku, "current_stock": stock})
            tools_called.append("check_inventory_status")
            inv = json.loads(inv_raw) if isinstance(inv_raw, str) else inv_raw

            dos = inv.get("days_of_supply", 0)
            ss = inv.get("safety_stock_units", 0)
            rop = inv.get("reorder_point_units", 0)
            po_qty = inv.get("recommended_po_qty_units", 0)
            po_val = inv.get("recommended_po_value_inr", 0)
            status = inv.get("po_trigger_status", "STABLE")

            analysis = (
                f"**Inventory Coverage & Procurement ({target_sku}):**\n"
                f"- **Current Warehouse Stock:** **{stock:,} units** (**{dos} Days of Supply**)\n"
                f"- **Safety Stock Required ($SS$):** **{ss:,} units** | **Reorder Point ($ROP$):** **{rop:,} units**\n"
                f"- **Procurement Status:** **{status}** → Immediate PO recommendation for **{po_qty:,} units**."
            )

            metrics = {
                "current_stock": stock,
                "days_of_supply": round(float(dos), 1),
                "safety_stock_units": int(ss),
                "reorder_point_units": int(rop),
                "recommended_po_qty_units": int(po_qty),
                "recommended_po_value_inr": round(float(po_val), 2),
                "po_trigger_status": status,
            }

        elif spec_id == "risk_analyst":
            inv_raw = self.tools.call("check_inventory_status", {"sku_id": target_sku, "current_stock": stock})
            tools_called.append("check_inventory_status")
            inv = json.loads(inv_raw) if isinstance(inv_raw, str) else inv_raw

            risk_inr = inv.get("revenue_at_risk_inr", 0)
            po_val = inv.get("recommended_po_value_inr", 0)
            stockout_units = inv.get("stockout_risk_units", 0)

            analysis = (
                f"**Rupee Financial Risk Assessment ({target_sku}):**\n"
                f"- **Projected Revenue at Risk:** **₹{risk_inr:,.2f}** ({stockout_units:,} units at risk)\n"
                f"- **Required Capital Outlay:** **₹{po_val:,.2f}** for replenishment PO\n"
                f"- **ROI on Action:** Acting now preserves **₹{risk_inr:,.2f}** in gross margin against holding cost of <₹5,000."
            )

            metrics = {
                "revenue_at_risk_inr": round(float(risk_inr), 2),
                "required_capital_outlay_inr": round(float(po_val), 2),
                "stockout_risk_units": int(stockout_units),
                "holding_cost_inr": 5000,
            }

        return {
            "specialist_id": spec_id,
            "role": spec["role"],
            "icon": spec["icon"],
            "analysis": analysis,
            "metrics": metrics,
            "steps": [],
            "tools_called": tools_called,
        }

    def _synthesize_reports(self, query, reports):
        """Build a dynamic executive synthesis from the specialist reports' metrics."""
        # Extract key metrics from specialist reports for dynamic synthesis
        demand_m = {}
        inv_m = {}
        risk_m = {}
        for r in reports:
            m = r.get("metrics", {})
            if r.get("specialist_id") == "demand_planner":
                demand_m = m
            elif r.get("specialist_id") == "inventory_controller":
                inv_m = m
            elif r.get("specialist_id") == "risk_analyst":
                risk_m = m

        po_qty = inv_m.get("recommended_po_qty_units", 0)
        po_val = inv_m.get("recommended_po_value_inr", 0)
        status = inv_m.get("po_trigger_status", "STABLE")
        model = demand_m.get("winning_model", "Auto-ML")
        risk_inr = risk_m.get("revenue_at_risk_inr", 0)

        # Build dynamic actions
        actions = []
        if po_qty > 0:
            actions.append(f"1. **Procurement**: Authorize immediate PO for **{po_qty:,} units** (₹{po_val:,.0f}) — status: **{status}**.")
        else:
            actions.append(f"1. **Procurement**: No immediate PO required — stock coverage is healthy.")
        actions.append(f"2. **Production Scheduling**: Align daily burn rates with the **{model}** forecast trajectory.")
        if risk_inr > 0:
            actions.append(f"3. **Risk Mitigation**: Release capital outlay to protect **₹{risk_inr:,.0f}** in revenue-at-risk.")
        else:
            actions.append(f"3. **Risk Mitigation**: No significant financial risk identified — maintain current procurement cadence.")

        lines = [
            "### 🏛️ War Room Unified Directive",
            "**Consensus Action Plan:**",
        ] + actions
        return "\n".join(lines)

