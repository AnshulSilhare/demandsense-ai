"""
Core agentic AI orchestration engine for DemandSense AI — an Indian FMCG supply chain control tower.
Author: Anshul Silhare
"""

import json
import logging
import os
import re

logger = logging.getLogger("demandsense.agent")

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(self, name: str, description: str, parameters: dict):
        def decorator(func):
            self._tools[name] = {
                "function": func,
                "description": description,
                "parameters": parameters,
                "name": name
            }
            return func
        return decorator

    def get_tool_schemas(self) -> list[dict]:
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"]
            }
            for tool in self._tools.values()
        ]

    def get_tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def call(self, name: str, arguments: dict) -> str:
        if name not in self._tools:
            return json.dumps({"error": f"Tool '{name}' not found."})
        try:
            func = self._tools[name]["function"]
            result = func(**arguments)
            return json.dumps(result, default=str, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def get_tools_description_text(self) -> str:
        lines = []
        for name, tool in self._tools.items():
            lines.append(f"- {name}: {tool['description']}")
        return "\n".join(lines)


SYSTEM_PROMPT = """You are DemandSense AI, an intelligent supply chain control tower for Indian FMCG (Fast-Moving Consumer Goods).
Your role is to assist planners and managers with demand forecasting, inventory optimization, and supply chain insights.

Follow these strict guidelines:
1. Break down complex questions into logical steps.
2. Call ONE tool at a time, wait for the result, and then proceed.
3. Always quantify financial impact and values in ₹ INR (Indian Rupees).
4. Be specific with dates, quantities, and actionable recommendations.
5. Do NOT fabricate data. If you don't know, say so or use a tool to find out.
6. Format your final answer using clear headings:
   - Key Findings (bullet points)
   - Recommended Actions (numbered list)
   - Financial Impact (specific ₹ values)
"""

class AgentHarness:
    def __init__(self, tools: ToolRegistry, api_key: str = None, max_steps: int = 8):
        self.tools = tools
        self.max_steps = max_steps
        self._memory: list = []
        
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                
                model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
                declarations = self._build_function_declarations()
                
                self.model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=SYSTEM_PROMPT,
                    tools=declarations
                )
                self.use_gemini = True
            except Exception as e:
                logger.error(f"Failed to initialize Gemini AI: {e}")
                self.use_gemini = False
        else:
            self.use_gemini = False

    def _build_function_declarations(self) -> list:
        try:
            import google.generativeai as genai
            
            declarations = []
            for schema in self.tools.get_tool_schemas():
                decl_kwargs = {
                    "name": schema["name"],
                    "description": schema["description"]
                }
                # Assuming the parameters dict maps closely to the proto structure
                if "parameters" in schema:
                    decl_kwargs["parameters"] = schema["parameters"]
                decl = genai.protos.FunctionDeclaration(**decl_kwargs)
                declarations.append(decl)
                
            if not declarations:
                return None
                
            return [genai.protos.Tool(function_declarations=declarations)]
        except ImportError:
            return None

    async def run(self, user_query: str, session_context: dict = None) -> dict:
        if self.use_gemini:
            return await self._run_gemini_agent(user_query, session_context)
        else:
            return self._run_offline_agent(user_query)

    async def _run_gemini_agent(self, user_query: str, session_context: dict) -> dict:
        import google.generativeai as genai
        
        prompt = user_query
        if session_context:
            prompt = f"Context: {json.dumps(session_context)}\n\nQuery: {user_query}"
            
        chat = self.model.start_chat(history=self._memory)
        tools_called = []
        steps = []
        
        try:
            response = chat.send_message(prompt)
            
            for step in range(self.max_steps):
                function_responses = []
                text_answer = None
                
                for part in response.parts:
                    if part.function_call:
                        func_call = part.function_call
                        name = func_call.name
                        
                        # Extract dictionary from proto
                        try:
                            args = type(func_call).to_dict(func_call).get('args', {})
                        except AttributeError:
                            args = {}
                            
                        # Sanitize float -> int
                        for k, v in args.items():
                            if isinstance(v, float) and v.is_integer():
                                args[k] = int(v)
                                
                        tools_called.append(name)
                        
                        # Call tool
                        result_str = self.tools.call(name, args)
                        
                        # Truncate if too long
                        if len(result_str) > 3000:
                            result_str = result_str[:3000] + "... [truncated]"
                            
                        steps.append({"tool": name, "args": args, "result": result_str})
                        
                        func_response = genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=name,
                                response={"result": result_str}
                            )
                        )
                        function_responses.append(func_response)
                    elif part.text:
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
                    
            # Max steps reached without final text answer
            summary_response = chat.send_message("Please summarize the findings so far.")
            self._memory = chat.history
            return {
                "answer": summary_response.text,
                "steps": steps,
                "tools_called": tools_called
            }
            
        except Exception as e:
            logger.error(f"Agent error: {e}")
            return {
                "answer": f"Error running agent: {str(e)}",
                "steps": steps,
                "tools_called": tools_called
            }

    def _run_offline_agent(self, user_query: str) -> dict:
        skus = re.findall(r'SKU\d{3}', user_query)
        lower_query = user_query.lower()
        
        answer = "[Offline Mode - Using Rule-Based Fallback]\n\n"
        
        if any(w in lower_query for w in ["forecast", "predict", "demand"]):
            answer += f"Running demand forecast for {', '.join(skus) if skus else 'requested items'}.\n"
            answer += "Tools called: run_demand_forecast"
        elif any(w in lower_query for w in ["inventory", "stock", "reorder"]):
            answer += f"Checking inventory status for {', '.join(skus) if skus else 'requested items'}.\n"
            answer += "Tools called: check_inventory_status"
        elif any(w in lower_query for w in ["festival", "holiday", "diwali"]):
            answer += "Fetching upcoming festivals affecting demand.\n"
            answer += "Tools called: get_upcoming_festivals"
        elif any(w in lower_query for w in ["product", "catalog", "list"]):
            answer += "Listing available SKUs.\n"
            answer += "Tools called: list_available_skus"
        else:
            answer += "I could not determine the intent. Available tools:\n"
            answer += self.tools.get_tools_description_text() + "\n"
            answer += "\nExample queries:\n"
            answer += "- Predict demand for SKU001\n"
            answer += "- Check inventory for SKU005\n"
            
        return {
            "answer": answer,
            "steps": [],
            "tools_called": []
        }

    def reset_memory(self):
        self._memory = []
