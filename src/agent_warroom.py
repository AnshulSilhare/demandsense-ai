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
from typing import Optional

logger = logging.getLogger("demandsense.warroom")


# ── Specialist Definitions ──
SPECIALISTS = {
    "demand_planner": {
        "role": "Demand Planner",
        "icon": "\U0001f52e",
        "system_prompt": """You are the Demand Planner specialist in a supply chain war room.
Your expertise: demand forecasting, trend analysis, seasonality patterns, festival impact.
You ONLY focus on DEMAND-side analysis. Do NOT discuss inventory levels or financial risk.
Be concise: 3-5 bullet points max. Always mention specific numbers.""",
        "tools": ["run_demand_forecast", "get_upcoming_festivals", "list_available_skus"],
    },
    "inventory_controller": {
        "role": "Inventory Controller",
        "icon": "\U0001f4e6",
        "system_prompt": """You are the Inventory Controller specialist in a supply chain war room.
Your expertise: warehouse stock levels, safety stock, reorder points, days of supply, PO timing.
You ONLY focus on INVENTORY and PROCUREMENT. Do NOT discuss demand trends or financial risk.
Be concise: 3-5 bullet points max. Always mention specific quantities and dates.""",
        "tools": ["check_inventory_status", "list_available_skus"],
    },
    "risk_analyst": {
        "role": "Risk Analyst",
        "icon": "\U0001f4b0",
        "system_prompt": """You are the Risk Analyst specialist in a supply chain war room.
Your expertise: financial risk quantification, revenue at risk, holding costs, scenario comparison.
You ONLY focus on FINANCIAL IMPACT in INR (\u20b9). Do NOT discuss demand patterns or stock levels in detail.
Be concise: 3-5 bullet points max. Always quantify everything in \u20b9 rupees.""",
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
                logger.warning(f"[WarRoom] Gemini init failed: {e}. Using offline mode.")

    async def analyze(self, query: str, session_context: dict = None) -> dict:
        """
        Run query through all specialists and synthesize results.

        Returns:
            dict with specialist_reports (list), synthesis, tools_called
        """
        specialist_reports = []
        all_tools_called = []

        for spec_id, spec in SPECIALISTS.items():
            report = await self._run_specialist(spec_id, spec, query, session_context)
            specialist_reports.append(report)
            all_tools_called.extend(report.get("tools_called", []))

        # Synthesize
        synthesis = self._synthesize_reports(query, specialist_reports)

        return {
            "query": query,
            "specialist_reports": specialist_reports,
            "synthesis": synthesis,
            "tools_called": list(set(all_tools_called)),
            "mode": "gemini" if self.use_gemini else "offline",
        }

    async def _run_specialist(self, spec_id, spec, query, session_context=None) -> dict:
        """Run a single specialist agent."""
        if self.use_gemini:
            try:
                return await self._run_gemini_specialist(spec_id, spec, query, session_context)
            except Exception as e:
                logger.error(f"[WarRoom] Specialist {spec_id} Gemini error: {e}")
                return self._run_offline_specialist(spec_id, spec, query)
        else:
            return self._run_offline_specialist(spec_id, spec, query)

    async def _run_gemini_specialist(self, spec_id, spec, query, session_context=None):
        """Run specialist with Gemini function calling."""
        genai = self._genai
        tools_called = []
        steps = []

        # Build tool declarations for this specialist only
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
            context = f"[Context: SKU={session_context.get('sku_id','unknown')}, Stock={session_context.get('current_stock','unknown')} units] "

        chat = model.start_chat()
        response = chat.send_message(context + query)

        for step_num in range(5):
            candidate = response.candidates[0]
            if not candidate.content.parts:
                break

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
            "analysis": "Analysis incomplete — reached maximum reasoning steps.",
            "steps": steps,
            "tools_called": tools_called,
        }

    def _run_offline_specialist(self, spec_id, spec, query):
        """Offline fallback for a specialist."""
        tools_called = []
        analysis_parts = []

        # Extract SKU from query
        sku_id = None
        query_lower = query.lower()
        for i in range(1, 21):
            if f"sku{i:03d}" in query_lower:
                sku_id = f"SKU{i:03d}"
                break

        if spec_id == "demand_planner":
            if sku_id:
                result = self.tools.call("run_demand_forecast", {"sku_id": sku_id})
                tools_called.append("run_demand_forecast")
                analysis_parts.append(f"**Forecast Analysis for {sku_id}:**\n{result}")
            fest_result = self.tools.call("get_upcoming_festivals", {"days_ahead": 60})
            tools_called.append("get_upcoming_festivals")
            analysis_parts.append(f"**Upcoming Festival Windows:**\n{fest_result}")

        elif spec_id == "inventory_controller":
            if sku_id:
                result = self.tools.call("check_inventory_status", {"sku_id": sku_id})
                tools_called.append("check_inventory_status")
                analysis_parts.append(f"**Inventory Status for {sku_id}:**\n{result}")
            else:
                analysis_parts.append("Please specify a SKU ID for inventory analysis.")

        elif spec_id == "risk_analyst":
            if sku_id:
                base = self.tools.call("check_inventory_status", {"sku_id": sku_id})
                tools_called.append("check_inventory_status")
                scenario = self.tools.call("run_whatif_scenario", {"sku_id": sku_id, "demand_change_pct": 20})
                tools_called.append("run_whatif_scenario")
                analysis_parts.append(f"**Risk Assessment for {sku_id}:**\nBase: {base}\nStress Scenario (+20% demand): {scenario}")
            else:
                analysis_parts.append("Please specify a SKU ID for risk analysis.")

        return {
            "specialist_id": spec_id,
            "role": spec["role"],
            "icon": spec["icon"],
            "analysis": "\n\n".join(analysis_parts) if analysis_parts else "No analysis available. Specify a SKU ID.",
            "steps": [],
            "tools_called": tools_called,
        }

    def _synthesize_reports(self, query, reports):
        """Combine specialist reports into an executive synthesis."""
        lines = [
            "## \U0001f3db\ufe0f War Room Synthesis",
            "",
        ]
        for r in reports:
            lines.append(f"### {r['icon']} {r['role']}")
            lines.append(r["analysis"])
            lines.append("")

        lines.append("---")
        lines.append("*Multi-agent collaborative analysis complete. Each specialist operated with domain-restricted tool access.*")
        return "\n".join(lines)
