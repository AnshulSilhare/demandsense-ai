"""
DemandSense AI — Autonomous Agentic Harness (Enhanced)
=========================================================
Dynamic Tool Registry + ReAct Reasoning Loop with
Intelligent Offline Fallback that executes tools and formats answers.

Author: Anshul Silhare
"""

import os
import sys
import json
import re
import logging
from typing import Callable, Any, Dict, List, Optional
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("demandsense.agent")

SYSTEM_PROMPT = """You are DemandSense AI, an expert autonomous supply chain agent for Indian FMCG enterprise operations.
You are assisting operations managers, demand planners, and supply chain directors.

Capabilities & Guidelines:
1. Break down complex operational questions step-by-step using available tools.
2. Always execute tools to fetch accurate real-time data before formulating conclusions.
3. Quantify financial risk in Indian Rupees (₹ INR), days of supply (DOS), safety stock, and MAPE accuracy metrics.
4. Consider Indian market specifics: festivals (Diwali, Holi, Navratri, etc.), regional demand patterns, seasonality, and supplier lead times.
5. Structure answers cleanly:
   - **Key Findings**: Clear bullet points with quantified numbers.
   - **Recommended Actions**: Prioritized, actionable procurement or inventory directives.
   - **Financial & Risk Impact**: Quantified rupee implications of action vs. inaction.
"""


class ToolRegistry:
    """Dynamic tool registration and dispatching container."""

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, description: str, parameters: dict):
        """Decorator to register a function as an agent tool."""
        def decorator(func: Callable):
            self._tools[name] = {
                "func": func,
                "description": description,
                "parameters": parameters,
            }
            return func
        return decorator

    def get_tool_schemas(self) -> List[dict]:
        """Return schema definitions compatible with Gemini / OpenAPI."""
        schemas = []
        for name, data in self._tools.items():
            schemas.append({
                "name": name,
                "description": data["description"],
                "parameters": data["parameters"]
            })
        return schemas

    def get_tool_names(self) -> List[str]:
        """Return list of registered tool names."""
        return list(self._tools.keys())

    def call(self, name: str, arguments: dict) -> str:
        """Execute a registered tool and return JSON string response."""
        if name not in self._tools:
            return json.dumps({"error": f"Tool '{name}' is not registered."})

        func = self._tools[name]["func"]
        try:
            result = func(**arguments)
            return json.dumps(result, default=str, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}", exc_info=True)
            return json.dumps({"error": f"Execution failed for '{name}': {str(e)}"})

    def get_tools_description_text(self) -> str:
        """Return human-readable tool documentation."""
        lines = []
        for name, data in self._tools.items():
            lines.append(f"- **{name}**: {data['description']}")
        return "\n".join(lines)


class AgentHarness:
    """
    Autonomous ReAct Agent Harness with Gemini Function Calling
    and an intelligent offline fallback that executes tools locally.
    """

    def __init__(self, tools: ToolRegistry, api_key: str = None, max_steps: int = 8):
        self.tools = tools
        self.max_steps = max_steps
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.use_gemini = False
        self.model = None
        self._memory = []
        self._sessions = {}  # session_id -> {"active_sku": str, "history": list}

        self._try_init_gemini()

    def get_session(self, session_id: str = "default") -> dict:
        """Get or initialize conversation session memory."""
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "active_sku": "SKU001",
                "history": []
            }
        return self._sessions[session_id]

    def get_active_sku(self, session_id: str = "default") -> str:
        """Get the current conversation's focus SKU."""
        return self.get_session(session_id).get("active_sku", "SKU001")

    def _record_history(self, session_id: str, query: str, sku: str, intent: str, summary: str = ""):
        """Record turn in multi-turn conversation history."""
        sess = self.get_session(session_id)
        sess["history"].append({
            "query": query,
            "sku": sku,
            "intent": intent,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        })
        if len(sess["history"]) > 20:
            sess["history"] = sess["history"][-20:]

    def _resolve_sku_from_text(self, text: str) -> tuple[Optional[str], Optional[str]]:
        """Extract SKU code or product name from user query for seamless natural conversation."""
        from config import PRODUCTS

        # 1. Match SKU pattern: SKU001..SKU020, sku003, SKU 003, sku 3, #3
        m = re.search(r'\bSKU[\s\-#]?(\d{1,3})\b', text, re.IGNORECASE)
        if m:
            num = int(m.group(1))
            sku_id = f"SKU{num:03d}"
            prod = next((p for p in PRODUCTS if p["sku_id"] == sku_id), None)
            return sku_id, (prod["name"] if prod else sku_id)

        # 2. Match product name / distinctive keywords
        lower = text.lower()
        stop_words = {"pack", "grams", "gram", "bottle", "citrus", "powder", "gentle", "pure", "order", "stock", "price", "delay"}
        for p in PRODUCTS:
            p_name_lower = p["name"].lower()
            if p_name_lower in lower:
                return p["sku_id"], p["name"]

            words = [w for w in re.split(r'[\s\d\-]+', p_name_lower) if len(w) > 3 and w not in stop_words]
            if any(w in lower for w in words):
                return p["sku_id"], p["name"]

        return None, None

    def _try_init_gemini(self):
        """Attempt to initialize Gemini if key is present."""
        key = self.api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            self.use_gemini = False
            return

        try:
            import google.generativeai as genai
            genai.configure(api_key=key)

            model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
            declarations = self._build_function_declarations()

            self.model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=SYSTEM_PROMPT,
                tools=declarations
            )
            self.use_gemini = True
            self.api_key = key
            logger.info(f"[Agent Harness] Live Gemini AI initialized ({model_name}).")
        except Exception as e:
            logger.warning(f"[Agent Harness] Gemini init failed: {e}. Using intelligent offline engine.")
            self.use_gemini = False

    def _build_function_declarations(self) -> list:
        """Convert tool schemas to Gemini FunctionDeclarations."""
        try:
            import google.generativeai as genai
            declarations = []
            for schema in self.tools.get_tool_schemas():
                decl_kwargs = {
                    "name": schema["name"],
                    "description": schema["description"]
                }
                if "parameters" in schema:
                    decl_kwargs["parameters"] = schema["parameters"]
                decl = genai.protos.FunctionDeclaration(**decl_kwargs)
                declarations.append(decl)

            if not declarations:
                return None
            return [genai.protos.Tool(function_declarations=declarations)]
        except Exception:
            return None

    async def run(self, user_query: str, session_context: dict = None, session_id: str = "default") -> dict:
        """Run agent with Gemini ReAct loop, fallback to intelligent offline engine."""
        sess = self.get_session(session_id)
        detected_sku, detected_name = self._resolve_sku_from_text(user_query)
        if detected_sku:
            sess["active_sku"] = detected_sku

        session_context = session_context or {}
        if "sku_id" not in session_context or detected_sku:
            session_context["sku_id"] = sess["active_sku"]

        if not self.use_gemini and os.environ.get("GEMINI_API_KEY"):
            self._try_init_gemini()

        if self.use_gemini:
            try:
                res = await self._run_gemini_agent(user_query, session_context)
                res["active_sku"] = sess["active_sku"]
                self._record_history(session_id, user_query, sess["active_sku"], "gemini", res.get("answer", "")[:100])
                return res
            except Exception as e:
                logger.error(f"[Agent Harness] Gemini runtime error: {e}. Falling back to offline.")
                return self._run_offline_agent(user_query, session_context, session_id=session_id)
        else:
            return self._run_offline_agent(user_query, session_context, session_id=session_id)

    async def _run_gemini_agent(self, user_query: str, session_context: dict = None) -> dict:
        import google.generativeai as genai

        tools_called = []
        steps = []

        context_prompt = ""
        if session_context:
            context_prompt = f"[System Context: Active SKU={session_context.get('sku_id','SKU001')}, Region={session_context.get('region','ALL')}, Stock={session_context.get('current_stock',1500)} units, Lead Time={session_context.get('lead_time',7)} days]\n\n"

        chat = self.model.start_chat(history=self._memory)
        response = chat.send_message(context_prompt + user_query)

        for step_num in range(self.max_steps):
            if not response.candidates or not response.candidates[0].content.parts:
                break

            candidate = response.candidates[0]
            function_responses = []
            text_answer = None

            for part in candidate.content.parts:
                if hasattr(part, 'function_call') and part.function_call.name:
                    fn = part.function_call
                    name = fn.name
                    args = dict(fn.args) if fn.args else {}

                    for k, v in args.items():
                        if isinstance(v, float) and v == int(v):
                            args[k] = int(v)

                    tools_called.append(name)
                    steps.append({"type": "tool_call", "tool": name, "args": args})

                    result_str = self.tools.call(name, args)
                    if len(result_str) > 3000:
                        result_str = result_str[:3000] + "... [truncated]"

                    steps.append({"type": "tool_result", "tool": name, "result": result_str})

                    func_response = genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=name,
                            response={"result": result_str}
                        )
                    )
                    function_responses.append(func_response)
                elif hasattr(part, 'text') and part.text:
                    text_answer = part.text

            if text_answer:
                self._memory = chat.history
                return {
                    "answer": text_answer,
                    "steps": steps,
                    "tools_called": tools_called
                }

            if function_responses:
                content = genai.protos.Content(parts=function_responses)
                response = chat.send_message(content)
            else:
                break

        try:
            summary_response = chat.send_message("Please summarize the findings so far into actionable points.")
            self._memory = chat.history
            return {
                "answer": summary_response.text,
                "steps": steps,
                "tools_called": tools_called
            }
        except Exception:
            return {
                "answer": "Analysis complete based on tool execution.",
                "steps": steps,
                "tools_called": tools_called
            }

    def _run_offline_agent(self, user_query: str, session_context: dict = None, session_id: str = "default") -> dict:
        session_context = session_context or {}
        sess = self.get_session(session_id)

        # 1. Resolve SKU from text or maintain continuous conversation thread
        detected_sku, detected_name = self._resolve_sku_from_text(user_query)
        if detected_sku:
            target_sku = detected_sku
            sess["active_sku"] = target_sku
        else:
            target_sku = sess.get("active_sku") or session_context.get("sku_id", "SKU001")
            sess["active_sku"] = target_sku

        from config import PRODUCTS
        prod = next((p for p in PRODUCTS if p["sku_id"] == target_sku), None)
        sku_name = prod["name"] if prod else target_sku
        current_stock = session_context.get("current_stock", 25000)

        lower_query = user_query.lower()
        tools_called = []
        steps = []

        def match_words(pattern: str) -> bool:
            return bool(re.search(r'\b(?:' + pattern + r')\b', lower_query, re.IGNORECASE))

        # 1. War Room Intent
        if match_words(r"war\s*room|warroom|specialist|specialists|council|convene"):
            tools_called.append("run_warroom")
            steps.append({"type": "warroom_consensus", "sku": target_sku})
            try:
                from src.agent_warroom import MultiAgentWarRoom, SPECIALISTS
                warroom = MultiAgentWarRoom(tools=self.tools)
                reports = [
                    warroom._run_offline_specialist(sid, SPECIALISTS[sid], user_query, session_context={"sku_id": target_sku, "current_stock": current_stock})
                    for sid in ["demand_planner", "inventory_controller", "risk_analyst"]
                ]
                synthesis = warroom._synthesize_reports(user_query, reports)
                answer = f"### 🏛️ Multi-Agent War Room Executive Consensus: {sku_name} ({target_sku})\n\n{synthesis}"
                self._record_history(session_id, user_query, target_sku, "warroom", f"War Room for {sku_name}")
                return {"answer": answer, "steps": steps, "tools_called": tools_called, "active_sku": target_sku}
            except Exception as e:
                logger.error(f"Offline war room failed: {e}")

        # 2. Portfolio Brief Intent
        if match_words(r"brief|portfolio|all skus|morning brief|overview"):
            tools_called.append("generate_portfolio_brief")
            raw_brief = self.tools.call("generate_portfolio_brief", {})
            steps.append({"type": "tool_call", "tool": "generate_portfolio_brief", "args": {}})
            steps.append({"type": "tool_result", "tool": "generate_portfolio_brief", "result": raw_brief})
            brief_data = json.loads(raw_brief) if isinstance(raw_brief, str) else raw_brief
            brief_text = brief_data.get("brief", "Portfolio scan complete.")
            self._record_history(session_id, user_query, target_sku, "brief", "Executive portfolio brief")
            return {"answer": brief_text, "steps": steps, "tools_called": tools_called, "active_sku": target_sku}

        # 3. Forecast Intent
        if match_words(r"forecast|predict|prediction|trend|demand|model|mape|burn rate|accuracy|sales|trajectory"):
            tools_called.append("run_demand_forecast")
            steps.append({"type": "tool_call", "tool": "run_demand_forecast", "args": {"sku_id": target_sku}})

            raw_fc = self.tools.call("run_demand_forecast", {"sku_id": target_sku})
            steps.append({"type": "tool_result", "tool": "run_demand_forecast", "result": raw_fc})
            fc_data = json.loads(raw_fc) if isinstance(raw_fc, str) else raw_fc

            if "error" in fc_data:
                answer = f"⚠️ Could not run forecast for {sku_name} ({target_sku}): {fc_data['error']}"
            else:
                winning = fc_data.get("winning_model", "Auto-ML")
                mape = fc_data.get("mape_pct", 0)
                tot_30d = fc_data.get("total_30d_forecast_units", 0)
                avg_daily = fc_data.get("avg_daily_forecast", 0)
                trend = fc_data.get("forecast_trend", "stable")

                answer = (
                    f"### 🔮 30-Day Demand Forecast: {sku_name} ({target_sku})\n\n"
                    f"#### 🔍 Key Findings:\n"
                    f"- **Auto-ML Winning Model:** **{winning}** (MAPE: **{mape:.2f}%** benchmarked on test set)\n"
                    f"- **Total 30-Day Projected Demand:** **{tot_30d:,} units**\n"
                    f"- **Average Daily Burn Rate:** **{avg_daily:.1f} units/day**\n"
                    f"- **Demand Trajectory:** **{trend.capitalize()}**\n\n"
                    f"#### 📋 Recommended Actions:\n"
                    f"1. Align production schedules with the daily run rate of **{avg_daily:.0f} units/day**.\n"
                    f"2. Calibrate warehouse buffer stock based on the **{mape:.1f}%** forecast error margin."
                )

            self._record_history(session_id, user_query, target_sku, "forecast", f"Forecast for {sku_name}")
            return {"answer": answer, "steps": steps, "tools_called": tools_called, "active_sku": target_sku}

        # 4. Reorder / Inventory Intent
        if match_words(r"inventory|stock|reorder|order|purchase order|\bpo\b|shortage|stockout|rop|safety stock|dos|coverage|replenish"):
            tools_called.append("check_inventory_status")
            steps.append({"type": "tool_call", "tool": "check_inventory_status", "args": {"sku_id": target_sku, "current_stock": current_stock}})

            raw_inv = self.tools.call("check_inventory_status", {"sku_id": target_sku, "current_stock": current_stock})
            steps.append({"type": "tool_result", "tool": "check_inventory_status", "result": raw_inv})
            inv_data = json.loads(raw_inv) if isinstance(raw_inv, str) else raw_inv

            if "error" in inv_data:
                answer = f"⚠️ Could not retrieve inventory for {sku_name} ({target_sku}): {inv_data['error']}"
            else:
                dos = inv_data.get("days_of_supply", 0)
                ss = inv_data.get("safety_stock_units", 0)
                rop = inv_data.get("reorder_point_units", 0)
                po_qty = inv_data.get("recommended_po_qty_units", 0)
                po_val = inv_data.get("recommended_po_value_inr", 0)
                risk_inr = inv_data.get("revenue_at_risk_inr", 0)
                status = inv_data.get("po_trigger_status", "STABLE")

                is_urgent = dos < 15 or "TRIGGERED" in status or "CRITICAL" in status
                status_badge = "🔴 URGENT REORDER REQUIRED" if is_urgent else "🟢 STOCK HEALTHY"

                answer = (
                    f"### 📦 Inventory & Procurement Analysis: {sku_name} ({target_sku})\n\n"
                    f"**Operational Status:** {status_badge}\n\n"
                    f"#### 🔍 Key Findings:\n"
                    f"- **On-Hand Inventory:** {current_stock:,} units ({dos} Days of Supply)\n"
                    f"- **Safety Stock Required (SS):** {ss:,} units\n"
                    f"- **Reorder Point (ROP):** {rop:,} units\n"
                    f"- **Revenue at Risk:** ₹{risk_inr:,.2f}\n\n"
                    f"#### 📋 Recommended Directive:\n"
                    f"1. {'**Place immediate Purchase Order**' if is_urgent else 'Hold new orders; monitor depletion'} for **{po_qty:,} units** (Est. Cost: **₹{po_val:,.2f}**).\n"
                    f"2. Standard supplier lead time is **7 days**. Maintaining {dos} DOS ensures service level compliance.\n\n"
                    f"#### 💰 Financial Summary:\n"
                    f"Acting now prevents up to **₹{risk_inr:,.2f}** in projected stockout losses over the 30-day window."
                )

            self._record_history(session_id, user_query, target_sku, "inventory", f"Inventory for {sku_name}")
            return {"answer": answer, "steps": steps, "tools_called": tools_called, "active_sku": target_sku}

        # 5. Festival Intent
        if match_words(r"festivals?|holidays?|diwali|holi|navratri|eid|spike|surge"):
            tools_called.append("get_upcoming_festivals")
            steps.append({"type": "tool_call", "tool": "get_upcoming_festivals", "args": {"days_ahead": 60}})

            raw_fest = self.tools.call("get_upcoming_festivals", {"days_ahead": 60})
            steps.append({"type": "tool_result", "tool": "get_upcoming_festivals", "result": raw_fest})
            fest_data = json.loads(raw_fest) if isinstance(raw_fest, str) else raw_fest

            festivals = fest_data.get("festivals", [])
            lines = [f"### 🎉 Upcoming Indian Festival Demand Windows (Next 60 Days)\n"]
            if festivals:
                for f in festivals:
                    lines.append(f"- **{f['festival_name']}** ({f['date']}, in **{f['days_until']} days**): {f['demand_impact']} (Ramp-up: {f['ramp_up_days']} days prior)")
                lines.append("\n**Procurement Directive:** Ensure replenishment POs are dispatched at least 14 days before the ramp-up window to capture full peak demand.")
            else:
                lines.append("No major festival peaks detected in the next 60 days. Standard baseline demand applies.")

            answer = "\n".join(lines)
            self._record_history(session_id, user_query, target_sku, "festivals", "Festival demand windows")
            return {"answer": answer, "steps": steps, "tools_called": tools_called, "active_sku": target_sku}

        # 6. What-If Intent
        if match_words(r"simulate|simulation|what-if|what if|scenario|delay|promo|promotion|elasticity|price"):
            tools_called.append("run_whatif_scenario")
            params = {"sku_id": target_sku, "promo_lift_pct": 15, "lead_time_change_days": 3, "current_stock": current_stock}
            steps.append({"type": "tool_call", "tool": "run_whatif_scenario", "args": params})

            raw_sim = self.tools.call("run_whatif_scenario", params)
            steps.append({"type": "tool_result", "tool": "run_whatif_scenario", "result": raw_sim})
            sim_data = json.loads(raw_sim) if isinstance(raw_sim, str) else raw_sim

            sim_impact = sim_data.get("simulated_impact", {})
            baseline = sim_data.get("baseline_comparison", {})

            answer = (
                f"### ⚡ What-If Simulation: {sku_name} ({target_sku}) (+15% Promo, +3-Day Delay)\n\n"
                f"#### 🔍 Scenario Comparison:\n"
                f"- **30-Day Demand:** {sim_impact.get('total_30d_forecast_units', 0):,} units (vs. Baseline {baseline.get('total_30d_forecast_units', 0):,} units)\n"
                f"- **Days of Supply:** {sim_impact.get('days_of_supply', 0)} DOS (vs. Baseline {baseline.get('days_of_supply', 0)} DOS)\n"
                f"- **Revenue at Risk:** ₹{sim_impact.get('revenue_at_risk_inr', 0):,.2f}\n"
                f"- **Recommended PO:** {sim_impact.get('recommended_po_qty_units', 0):,} units (₹{sim_impact.get('recommended_po_value_inr', 0):,.2f})\n\n"
                f"#### 📋 Strategic Recommendation:\n"
                f"Place an expedited PO for {sim_impact.get('recommended_po_qty_units', 0):,} units to buffer against the 3-day supplier delay during the promotional surge."
            )
            self._record_history(session_id, user_query, target_sku, "whatif", f"What-If simulation for {sku_name}")
            return {"answer": answer, "steps": steps, "tools_called": tools_called, "active_sku": target_sku}

        # 7. Greetings & Help (Only when no domain intent was matched)
        if match_words(r"hi|hello|hey|greetings|help|who are you|what can you do"):
            answer = (
                "👋 **Hello! I am the DemandSense Autonomous Supply Chain Agent.**\n\n"
                "I operate in both **Live Gemini AI Mode** and **High-Availability Engine Mode**. Here is what I can do:\n\n"
                "1. 🔮 **Demand Forecasting**: Benchmark 5 ML models & forecast 30-day demand (`run_demand_forecast`)\n"
                "2. 📦 **Inventory & Reorder Decisions**: Calculate safety stock, ROP, days of supply, and POs (`check_inventory_status`)\n"
                "3. 🎉 **Festival Surge Analysis**: Check upcoming Indian festival demand multipliers (`get_upcoming_festivals`)\n"
                "4. ⚡ **What-If Simulations**: Model price elasticity, promotional lift, and supply delays (`run_whatif_scenario`)\n"
                "5. 🏛️ **War Room**: Multi-agent specialist review combining demand, inventory, and risk\n\n"
                "💡 *Try clicking any quick-action chip above or asking: 'Should I reorder SKU007 for Navratri?'*"
            )
            self._record_history(session_id, user_query, target_sku, "greeting", "Intro greeting")
            return {"answer": answer, "steps": [], "tools_called": [], "active_sku": target_sku}

        # 8. Default Diagnostic (or SKU switch)
        tools_called.append("check_inventory_status")
        steps.append({"type": "tool_call", "tool": "check_inventory_status", "args": {"sku_id": target_sku, "current_stock": current_stock}})
        raw_inv = self.tools.call("check_inventory_status", {"sku_id": target_sku, "current_stock": current_stock})
        steps.append({"type": "tool_result", "tool": "check_inventory_status", "result": raw_inv})
        inv_data = json.loads(raw_inv) if isinstance(raw_inv, str) else raw_inv

        dos = inv_data.get("days_of_supply", 0)
        po_qty = inv_data.get("recommended_po_qty_units", 0)
        po_val = inv_data.get("recommended_po_value_inr", 0)
        risk = inv_data.get("revenue_at_risk_inr", 0)

        answer = (
            f"### 🤖 Operational Diagnostic: {sku_name} ({target_sku})\n\n"
            f"#### 🔍 Key Findings:\n"
            f"- **Current Stock Coverage:** {current_stock:,} units ({dos} Days of Supply)\n"
            f"- **Safety Stock Threshold:** {inv_data.get('safety_stock_units', 0):,} units\n"
            f"- **Revenue at Risk:** ₹{risk:,.2f}\n\n"
            f"#### 📋 Action Directives:\n"
            f"1. Recommended replenishment order: **{po_qty:,} units** (Est. Cost: **₹{po_val:,.2f}**).\n"
            f"2. You can also explore **`🏛️ War Room Analysis`** or **`🔮 Scenario Copilot`** for **{sku_name}** by asking below."
        )

        self._record_history(session_id, user_query, target_sku, "diagnostic", f"Diagnostic for {sku_name}")
        return {"answer": answer, "steps": steps, "tools_called": tools_called, "active_sku": target_sku}

    def reset_memory(self, session_id: Optional[str] = None):
        self._memory = []
        if session_id and session_id in self._sessions:
            del self._sessions[session_id]
        else:
            self._sessions.clear()
        logger.info(f"[Agent Harness] Conversation memory reset (session={session_id or 'all'}).")
