# 🔮 DemandSense AI - Intelligent Demand Forecasting Engine for Indian FMCG

> An AI Agent-powered demand forecasting & inventory optimization system built for the Indian FMCG sector. Combines multi-model ML forecasting, prescriptive supply chain analytics, and LLM reasoning into a single interactive decision-support platform.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://huggingface.co/spaces/anshul-silhare/demandsense-ai)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   DEMANDSENSE AI                         │
│                                                          │
│  Layer 1: Indian FMCG Data & Feature Pipeline            │
│  ├─ 20 SKUs × 5 Regions × 3 Years = 109,600 records     │
│  ├─ Indian Festival Calendar (Diwali, Holi, Navratri...) │
│  └─ 55 Engineered Features (lag, rolling, seasonal)      │
│                         ▼                                │
│  Layer 2: 5-Model Auto-Selector Engine                   │
│  ├─ Moving Average (14d WMA)                             │
│  ├─ Exponential Smoothing (Holt-Winters)                 │
│  ├─ SARIMAX (Seasonal ARIMA)                             │
│  ├─ Prophet (with Indian Holiday Regressors)             │
│  └─ XGBoost (Gradient Boosted Trees)                     │
│                         ▼                                │
│  Layer 3: Operations & Financial Impact Calculator       │
│  ├─ Safety Stock: SS = Z × σ × √LT                      │
│  ├─ Reorder Point (ROP)                                  │
│  ├─ PO Trigger Date Detection                            │
│  ├─ Revenue at Risk (₹)                                  │
│  └─ Pareto ABC Classification                            │
│                         ▼                                │
│  Layer 4: LLM Prescriptive Reasoning Agent               │
│  ├─ Google Gemini API (Primary)                          │
│  └─ Offline Rule Engine (100% Uptime Fallback)           │
│                         ▼                                │
│  Layer 5: Streamlit Interactive Control Tower             │
│  ├─ Demand Forecast Dashboard + Confidence Bands         │
│  ├─ Auto-ML Model Benchmark Leaderboard                  │
│  ├─ Real-Time What-If Scenario Simulator                 │
│  └─ Batch SKU Inventory Action Matrix                    │
└──────────────────────────────────────────────────────────┘
```

---

## Key Features

### Indian Market Intelligence
- **Festival Demand Modeling:** Diwali (+180% Namkeen), Holi (+40% Juice), Monsoon (+140% Repellent), Winter (+150% Chyawanprash)
- **Regional Demand Variation:** Mumbai (high purchasing power, extreme monsoon), Delhi NCR (harsh winters, extreme summers), Chennai (mild winters)
- **Salary Cycle Effect:** 8% demand boost during the 25th-5th monthly salary window
- **Wedding Season Spikes:** Peak Nov-Feb, secondary Apr-May

### Auto-ML Forecasting
- Automatically benchmarks 5 forecasting models on 60-day unseen test data
- Selects the winning model per SKU based on MAPE/RMSE/WAPE metrics
- Generates 30-day production forecast with 95% confidence intervals

### Prescriptive Supply Chain Analytics
- **Safety Stock** calculated using service-level Z-scores (Class A: 99%, B: 95%, C: 90%)
- **Reorder Point** with configurable supplier lead times
- **Revenue at Risk** quantified in rupees for projected stockouts
- **ABC-Pareto Classification** across all 20 national SKUs

### 🧠 Enterprise Agentic AI Suite (5 Autonomous Modes)

1. **Option A — Autonomous Portfolio Monitoring (`Live Sentinel`)**:
   - Continuous background polling scanning all 20 SKUs against stock levels & festival multipliers
   - Live notification badge and instant glass alert banner on stockout risk detection
2. **Option B — Conversational Decision Support (`ReAct Copilot`)**:
   - Multi-turn natural language dialogue with dynamic Gemini Function Calling
   - Dynamic tool orchestration with collapsible step-by-step reasoning trace (XAI)
3. **Option C — Multi-Agent War Room (`Specialist Collaboration`)**:
   - 3 domain-specialized agents executing in parallel:
     - 🔮 **Demand Planner**: Forecast trends, festival spikes, and seasonality
     - 📦 **Inventory Controller**: Safety stock, ROP, days of supply, and PO quantities
     - 💰 **Risk Analyst**: Rupee financial risk, holding costs, and stress testing
   - Executive synthesis engine harmonizing specialist outputs into a single actionable brief
4. **Option D — Daily Executive Brief (`Automated Intelligence`)**:
   - One-click holistic portfolio scan quantifying total revenue at risk (₹)
   - Prioritized procurement directives and upcoming festival multiplier calendar
5. **Option E — Scenario Planning Copilot (`Automated What-If Analysis`)**:
   - Auto-generates 4 strategic scenarios (Baseline, Promo, Supply Disruption, Conservative)
   - Side-by-side comparison matrix with automated scoring and optimal strategy recommendation

- **Dynamic Tool Registry (5 Enterprise Tools):** `run_demand_forecast`, `check_inventory_status`, `get_upcoming_festivals`, `run_whatif_scenario`, `list_available_skus`
- **Dual-Engine Architecture:** Google Gemini API (Primary) + Offline Rule Engine (100% Uptime Fallback)

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/anshul-silhare/demandsense-ai.git
cd demandsense-ai

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate synthetic Indian FMCG data (first run only)
python scripts/generate_data.py

# 4. Launch the interactive dashboard
streamlit run app.py
```

---

## Project Structure

```
demand_forecasting_engine/
├── config.py                     # 20 Indian SKUs, 5 Regions, Festival Calendar
├── app.py                        # Streamlit Interactive Control Tower
├── requirements.txt              # Python dependencies
│
├── data/
│   ├── raw/
│   │   └── indian_fmcg_sales.csv        # 109,600 daily sales records
│   └── processed/
│       └── featured_sales.csv           # 55-feature ML-ready dataset
│
├── src/
│   ├── data_generator.py                # Synthetic data engine (5 modular effects)
│   ├── feature_engine.py                # Indian seasonality feature pipeline
│   ├── business_impact.py               # Safety Stock, ROP, Revenue at Risk
│   ├── llm_agent.py                     # Gemini API + Offline Rule Engine
│   └── forecasting/
│       ├── base_model.py                # Abstract forecaster interface
│       ├── moving_average.py            # 14-day Weighted Moving Average
│       ├── exp_smoothing.py             # Holt-Winters Triple Exponential Smoothing
│       ├── arima_model.py               # SARIMAX model
│       ├── prophet_model.py             # Meta Prophet + Indian holidays
│       ├── xgboost_model.py             # Gradient Boosted Trees
│       └── auto_selector.py             # Auto-ML benchmark & model selector
│
└── scripts/
    ├── generate_data.py                 # Phase 1 data pipeline runner
    └── run_forecasting.py               # Phase 2 model benchmark runner
```

---

## Dataset

The project uses **realistic synthetic Indian FMCG data** because real company data (HUL, ITC, Marico) is proprietary and not publicly available.

| Parameter | Value |
|---|---|
| Total Records | 109,600 |
| Date Range | Jan 2023 - Dec 2025 |
| Products | 20 Indian FMCG SKUs |
| Regions | 5 (Delhi NCR, Mumbai, Chennai, Kolkata, Nagpur) |
| Categories | Staples, Home Care, Personal Care, Beverages, Snacks, Health Foods, etc. |
| Engineered Features | 55 (temporal, festival proximity, seasonal, lag, rolling) |

> **Note:** The engine is data-agnostic. Replace the synthetic data with real ERP/SAP transactional data and the auto-selector will process it automatically.

---

## Technologies Used

| Layer | Technologies |
|---|---|
| **Data & Features** | Python, Pandas, NumPy |
| **Forecasting Models** | statsmodels, XGBoost, Prophet, scikit-learn |
| **Business Logic** | Custom Safety Stock, ROP, ABC calculations |
| **LLM Agent** | Google Gemini API (gemini-1.5-flash) |
| **Web Interface** | Streamlit, Plotly |
| **Deployment** | HuggingFace Spaces |

---

## Author

**Anshul Silhare**
- PGDM Operations Management - Welingkar Institute of Management (WeSchool)
- [LinkedIn](https://linkedin.com/in/anshul-silhare) | [GitHub](https://github.com/anshul-silhare)

---

## License

This project is licensed under the MIT License.
