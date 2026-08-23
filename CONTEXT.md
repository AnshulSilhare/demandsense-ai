# DemandSense AI — Project Context & Handover Document

## Executive Summary

DemandSense AI is an enterprise-grade FMCG Demand Forecasting Engine & Supply Chain Control Tower built as a placement portfolio project by Anshul Silhare (Welingkar Institute of Management / WeSchool). It targets executive decision-makers — VPs of Operations, Supply Chain Directors, and technical recruiters at firms like EY, Accenture, Infosys, Dow, ITC, and Marico.

The system integrates multi-model AI forecasting (XGBoost, Prophet, SARIMAX, ARIMA, Exponential Smoothing) with real-time financial risk modeling, inventory optimization (Safety Stock, Reorder Point, EOQ), what-if stress testing with price elasticity feedback, and an executive dashboard powered by Streamlit.

**Key Differentiators:**
- Indian FMCG domain expertise: 20 SKUs across 5 regions with real festival seasonality (Diwali, Holi, Navratri, Eid, Ganesh Chaturthi, Pongal), monsoon patterns, salary cycle effects, and day-of-week demand multipliers.
- 5-model Auto-ML arena with automatic winner selection per SKU based on MAPE, RMSE, MAE, WAPE on 60-day unseen test sets.
- Price elasticity feedback loop in the What-If Simulator: price changes automatically feed back into demand volume using configurable elasticity coefficients.
- Apple "Liquid Glass" (iOS 18 / visionOS) design language with floating glass paneling, specular highlight streaks, ambient animated blob backgrounds, and a fully custom CSS token system with native Streamlit dark theme sync.
- LLM prescriptive agent (Gemini API primary, rule-based offline fallback) generating executive natural language procurement briefs.

---

## Architecture & Tech Stack

### Core Frameworks & Libraries
- **Frontend / Dashboard**: Streamlit (Python) with a custom CSS token system and Apple Liquid Glass design language. Native Streamlit base theme set to Dark Mode (`config.toml`), with smooth session-state toggle support.
- **Data Engineering & Analytics**: Pandas, NumPy, Scikit-learn, XGBoost, Statsmodels, Prophet.
- **Data Visualization**: Plotly Express & Graph Objects (transparent polar radar, dynamic time-series, regional hub scatter map), SVG inline sparklines (Catmull-Rom smoothed Bezier paths with gradient fills).
- **Document Generation**: ReportLab for executive 1-page PDF briefs.
- **Export System**: Base64 Data URI HTML anchor tags (bypassing IDM / download manager interception — NEVER use `st.download_button`).

### Python Dependencies (`requirements.txt`)
```
pandas>=2.0.0
numpy>=1.24.0
statsmodels>=0.14.0
xgboost>=2.0.0
scikit-learn>=1.3.0
plotly>=5.18.0
streamlit>=1.28.0
reportlab>=4.0.0
# prophet>=1.1.0          (Optional: install separately if needed)
# google-generativeai>=0.3.0 (Optional: for Gemini LLM, offline fallback works without it)
```

### Project Directory Structure
```
demand_forecasting_engine/
├── app.py                          # Main Streamlit application entry point & UI engine (~1600 lines)
├── config.py                       # Product catalog (20 SKUs), regional mappings (5 regions),
│                                   #   Indian festival calendar, business constants (633 lines)
├── tokens.py                       # Design system token definitions (Dark & Light modes, 59 lines)
├── .streamlit/
│   └── config.toml                 # Streamlit native theme configuration (Dark base theme sync)
├── requirements.txt                # Python dependency manifest
├── CONTEXT.md                      # This handover document
├── README.md                       # Public-facing project overview
├── HF_README.md                    # HuggingFace Spaces deployment README
├── src/
│   ├── __init__.py
│   ├── forecasting/
│   │   ├── __init__.py
│   │   ├── base_model.py           # Abstract base class for all forecasters
│   │   ├── auto_selector.py        # 5-model evaluation engine & winner selection pipeline
│   │   ├── moving_average.py       # Weighted 14-day moving average forecaster
│   │   ├── exp_smoothing.py        # Holt-Winters exponential smoothing (seasonal_periods=7)
│   │   ├── arima_model.py          # SARIMAX(1,1,1)(1,0,1,7) forecaster
│   │   ├── prophet_model.py        # Facebook Prophet with Indian festival regressor calendar
│   │   └── xgboost_model.py        # XGBoost regressor with feature importances
│   ├── feature_engine.py           # Indian Seasonality Feature Engine (~50+ engineered features)
│   ├── data_generator.py           # Synthetic Indian FMCG time-series generator (2023–2025)
│   ├── business_impact.py          # Inventory optimization & financial risk calculator
│   ├── analytics_helpers.py        # SVG sparkline generator, decomposition, radar prep, festival summaries
│   ├── llm_agent.py                # Prescriptive executive recommendation agent (Gemini + offline fallback)
│   └── pdf_exporter.py             # Executive PDF brief generator (ReportLab)
└── data/
    ├── raw/
    │   └── indian_fmcg_sales.csv   # Raw generated sales data (auto-created on first run)
    └── processed/
        └── featured_sales.csv      # Feature-engineered dataset (auto-created after feature engine run)
```

### Data Schema (`indian_fmcg_sales.csv`)
| Column         | Type      | Description                                      |
|----------------|-----------|--------------------------------------------------|
| `date`         | datetime  | Daily timestamp (2023-01-01 to 2025-12-31)       |
| `sku_id`       | string    | SKU identifier (SKU001 through SKU020)           |
| `sku_name`     | string    | Human-readable product name                      |
| `category`     | string    | Product category (Home Care, Packaged Food, etc.)|
| `region_id`    | string    | Region code (NORTH, SOUTH, WEST, EAST, CENTRAL)  |
| `region_name`  | string    | Display name (e.g. "North India (Delhi NCR)")    |
| `units_sold`   | integer   | Daily units sold                                 |
| `unit_price_inr`| float   | MRP in ₹                                         |
| `revenue_inr`  | float     | `units_sold × unit_price_inr`                    |

### Feature-Engineered Columns (generated by `feature_engine.py`)
- **Time Features** (11 cols): `day_of_week`, `month`, `quarter`, `is_weekend`, `day_of_month`, `week_of_year`, `is_month_start`, `is_month_end`, `is_salary_window`, etc.
- **Festival Features** (per festival): `is_diwali_period`, `days_to_diwali`, `is_navratri_period`, `is_holi_period`, etc.
- **Season Features**: `is_monsoon`, `is_winter`, `is_summer`, `is_wedding_season`.
- **Lag Features**: `lag_1`, `lag_7`, `lag_14`, `lag_28`, `lag_365`.
- **Rolling Features**: `rolling_mean_7`, `rolling_mean_14`, `rolling_std_7`, `rolling_std_14`, `rolling_mean_28`.

### Business Constants (`config.py`)
| Constant                  | Value  | Description                                            |
|---------------------------|--------|--------------------------------------------------------|
| `HOLDING_COST_PCT`        | 0.25   | 25% annual holding cost as fraction of product value   |
| `DEFAULT_LEAD_TIME_DAYS`  | 7      | Average supplier lead time                             |
| `STOCKOUT_COST_MULTIPLIER`| 1.5    | Lost sale cost = 1.5× gross margin                     |
| `GROSS_MARGIN_PCT`        | 0.30   | Assumed 30% gross margin for FMCG                      |
| `SALARY_CYCLE_BOOST`      | 1.08   | 8% demand lift during salary window (25th–5th)         |

### Service Level Tiers
| Class | Z-Score | Target % | Label         |
|-------|---------|----------|---------------|
| A     | 2.33    | 99.0%    | Critical SKU  |
| B     | 1.65    | 95.0%    | Important SKU |
| C     | 1.28    | 90.0%    | Standard SKU  |

### Inventory Optimization Formulae (`business_impact.py`)
```
Safety Stock (SS)    = Z × σ_demand × √(Lead Time)
Reorder Point (ROP)  = (Avg Daily Forecast × Lead Time) + SS
Days of Supply (DOS) = Current Stock / Avg Daily Forecast
Revenue at Risk      = Stockout Units × Selling Price
Holding Cost (Annual)= Excess Units × Unit Price × HOLDING_COST_PCT
Recommended PO Qty   = max(0, 30-Day Forecast + SS - Current Stock)
```

---

## Dashboard Architecture — 5 Tabs

### Tab 1: Demand Intelligence & Indian Seasonality
- **Hero Chart**: Historical raw daily demand (fill-to-zero), 7-day rolling trend, 30-day AI forecast line (Intelligence Indigo `#6E56CF`), 95% confidence band (purple fill), forecast start vertical line, ROP & Safety Stock horizontal reference lines. Plotly engine configured with `theme=None` and custom transparent background template.
- **2-Column Grid**:
  - Left: Additive time-series decomposition (Trend / 7-Day Seasonality / Residual Noise) using `make_subplots(rows=3)`.
  - Right: Festival multiplier horizontal bar chart (sorted descending, Diwali highlighted in `#E8B04B`).

### Tab 2: Auto-ML Model Benchmark Arena
- **Leaderboard DataFrame**: 5 models ranked by MAPE, RMSE, MAE, WAPE with min-highlighting.
- **Performance Radar**: Scatterpolar chart with normalized 0–100 scores (inverted error metrics). Winner gets `rgba(110,86,207,0.14)` fill. Theme-aware polar grid lines.
- **XGBoost Feature Importance**: Horizontal bar chart of top-10 features.

### Tab 3: Inventory Control Tower
- **Stock Trajectory**: 30-day projected inventory depletion line with ROP and Safety Stock reference lines.
- **India Regional Map**: `go.Scattergeo` with calibrated coordinates for Delhi NCR, Mumbai, Chennai, Kolkata, Nagpur. Marker sizes proportional to revenue, `Purples` colorscale.
- **ABC Risk Matrix**: National SKU Pareto classification table (Class A = top 80% revenue, B = next 15%, C = bottom 5%).

### Tab 4: What-If Scenario Simulator
- **5 Simulation Sliders**:
  - Supplier Lead Time Delay (+/−5 to +15 days)
  - Demand Surge / Dip (−50% to +100%, step 5%)
  - Selling Price Adjustment (−30% to +50%, step 5%)
  - Price Elasticity Coefficient (−3.0 to 0.0, default −1.2, step 0.1)
  - Promo Campaign Boost (0% to +80%, step 5%)
- **Combined demand multiplier formula**:
  ```
  Total Scale = (1 + demand_surge%) × (1 + price_Δ% × elasticity) × (1 + promo_boost%)
  ```
- **Scenario Impact Narrative Card**: Dynamically generated plain-English summary of all active stress parameters, combined demand effect, and ₹ revenue delta.
- **6-Column Delta Metrics**: Lead Time, Safety Stock, Reorder Point, Revenue at Risk (inverse delta color), 30D Revenue Δ, PO Qty Δ.
- **Enhanced Trajectory Chart**: Fill-between shading for divergence gap, dual Safety Stock lines (baseline amber + simulated gold), labeled Simulated ROP, and a red `⚠ STOCKOUT` annotation marker if projected stock hits zero.

### Tab 5: AI Prescriptive Control Room
- **Priority Status Badge**: Pulsing dot animation for CRITICAL, static for WARNING/HEALTHY.
- **4 AI Action Cards** (1×4 horizontal grid with `min-height: 220px` for equal height):
  - Executive Summary | Procurement Directive | Financial Risk & Rupee Impact | AI Model Selection Rationale
- **Executive Export & PO Generator**: Purchase Order CSV and 1-page Executive PDF Brief exported via Base64 `data:` URIs.
- **Full Raw Text Brief**: `st.text_area` with complete procurement brief text.

### Sticky Command Bar (Above Tabs)
4-card CSS grid KPI command bar: 30-Day Demand Forecast, Projected Revenue, Safety Stock Compliance, Revenue at Risk. Each card has an icon chip, IBM Plex Mono KPI value, direction-aware delta badge, and a Catmull-Rom SVG sparkline.

---

## UI Design System

### Theme Engine
- **Default Theme**: Dark Mode set in `.streamlit/config.toml` (`base="dark"`, `backgroundColor="#0A0D14"`, `secondaryBackgroundColor="#131826"`, `textColor="#EDEFF3"`).
- **Session State**: `st.session_state.theme` defaults to `"dark"`, with toggle support.
- **Token Files**: `tokens.py` exports `DARK_TOKENS` and `LIGHT_TOKENS` dicts with 20+ CSS variable values each.

### Apple Liquid Glass Sidebar
- **Ambient Background Layer** (`.stApp::before`): Three radial gradient color blobs (`#6E56CF`, `#C98A2E`, `#22C3B6`) with `blur(60px)` and 22s `ds-blob-drift` animation.
- **Floating Outer Shell**: Detached sidebar with 12px outer margins, 24px rounded corners, `backdrop-filter: blur(28px) saturate(180%)`, and `rgba(15,19,32,0.45)` background.
- **Clean Inputs**: Unboxed Product SKU and Geographic Region selectboxes sitting directly on the floating glass panel.
- **Specular Highlight Streak**: `::before` pseudo-element with `linear-gradient(115deg, ...)` rotated 8°.
- **Spring Motion Physics**: `cubic-bezier(0.22, 1, 0.36, 1)` on hover transforms.
- **Glass Input Controls**: Selectboxes and number inputs use `rgba(255,255,255,0.06)` backgrounds with `blur(8px)`.
- **Slider Thumb**: `accent-primary` with `rgba(110,86,207,0.18)` ring shadow and white border.

### Color Palette
| Token                 | Dark Mode        | Light Mode       | Usage                      |
|-----------------------|------------------|------------------|----------------------------|
| `accent_primary`      | `#6E56CF`        | `#6E56CF`        | Intelligence Indigo        |
| `accent_secondary`    | `#C98A2E`        | `#B87A1F`        | Marigold Gold              |
| `status_critical`     | `#EF4444`        | `#DC2626`        | Stockout / High Risk       |
| `status_warning`      | `#F5A623`        | `#D97706`        | ROP Breach Imminent        |
| `status_healthy`      | `#22C55E`        | `#16A34A`        | Inventory Balanced         |

### Typography
- **Headlines**: Plus Jakarta Sans (700, −0.02em tracking)
- **Body**: Inter (400–600)
- **KPI Values / Code**: IBM Plex Mono (700, tabular-nums, −0.02em tracking)

---

## Completed Tasks & Features (All Recent Sessions)

### Session 1 — Foundation & Bug Fixes
1. Resolved `KeyError: 'avg_daily_demand_units'` in `pdf_exporter.py`.
2. Resolved Plotly timestamp math crash (`TypeError: Addition/subtraction of integers and integer-arrays with Timestamp is no longer supported`).
3. Fixed f-string indentation bug — multiline HTML strings.
4. Eliminated IDM download loop — switched from `st.download_button` to Base64 `data:` URI anchor tags.

### Session 2 — UI/UX Design System Overhaul
1. Apple Liquid Glass Sidebar: Floating design with 12px margin, 24px border-radius, ambient blob layer, dual-layer glass paneling, specular highlights, glass input controls, spring physics, and sticky dark mode toggle.
2. Main Canvas: Floating outer shell container with `border-radius: 24px`, `max-width: 1560px`.
3. Command Bar: 4-card sticky KPI grid with SVG sparklines.
4. Tab 5 redesign: 1×4 horizontal AI action card layout for desktop landscape.

### Session 5 — Power BI-Style Chart Interaction Redesign (Latest)
1. **Stripped Plotly Modebar & Navigation**: Extended `PLOTLY_CONFIG` (`displayModeBar: False`, `scrollZoom: False`, `doubleClick: False`) and set `dragmode=False` on Plotly template to lock all charts like a Power BI report visual.
2. **Time-Range Segmented Pill Control**: Replaced Plotly rangeselector with Streamlit `st.segmented_control` (`7D`, `30D`, `90D`, `1Y`, `All`), filtering pandas DataFrames before plotting.
3. **Click-to-Cross-Filter**: Clicking a bar on the Festival Multipliers chart updates `st.session_state["active_filter"]`, highlighting the festival window on the Hero chart in Marigold Gold (`#E8B04B`) and dimming non-matching periods (`opacity=0.15`). Added a `✕ Clear filter` glass chip for easy reset.
4. **Focus Mode Dialogs**: Added `⤢` expand icon buttons to all chart card headers, launching full-size 560px figures inside native `@st.dialog` modals.
5. **Glass Tooltips & IDM-Safe Exports**: Added custom multi-field `hovertemplate`s with dark glass `hoverlabel` styling, and explicit `📥 Export PNG` buttons using `kaleido` (v1.3.0) scale=2 retina rendering wrapped in Base64 `data:` URI anchor tags.

---

### Session 6 — React DOM Layout & Stability Fixes (Latest)
1. **HTML Fragment Bug Fix**: Fixed a critical layout bug where Streamlit widgets (buttons) were wrapped in split `st.markdown` calls (e.g., `st.markdown('<div class="ds-expand-btn">')` then `st.button()` then `st.markdown('</div>')`). This caused the browser to auto-close the `<div>` and orphan the `</div>`, prematurely closing the parent Tab container and hiding all contents.
2. **CSS Targeting**: Replaced the fragmented `div` wrappers by targeting native Streamlit elements directly via CSS attributes (e.g., `button[title="Focus mode"]`).
3. **Export Link Refactor**: Refactored the Base64 PNG export generator to return the complete `<a>` HTML string, wrapping it in a single `st.markdown` call to preserve DOM integrity.
4. **App Backup**: Created `app_backup.py` as a stable snapshot.


## Pending Implementation Roadmap

### Path A — Placement Interview Prep
1. Record a 3-minute Loom/screen walkthrough narrating each tab's business value.
2. Prepare a "Technical Deep Dive" slide deck (10–12 slides) covering:
   - Architecture diagram (data flow from raw CSV → feature engine → 5 models → auto-selector → impact calculator → LLM agent → PDF export)
   - Model selection methodology and why MAPE was chosen as the primary metric
   - Indian seasonality modeling rationale (festival calendar, monsoon, salary cycle)
   - Safety Stock / ROP / EOQ math with real examples from the dashboard
3. Practice common interview defense questions.

### Path B — HuggingFace Spaces Deployment
1. Create `Dockerfile` or `requirements.txt`-based HF Space.
2. Store `GEMINI_API_KEY` via HF Secrets (or rely on the offline rule-based LLM fallback).
3. Add pre-computation / caching for fast cold starts.
4. Publish public demo URL.

### Path C — V2 Feature Extensions
1. Multi-SKU Comparison View (Tab 1).
2. Anomaly Detection with Isolation Forest on time-series.
3. Supplier Reliability Risk Scoring.
4. Email alert integration for ROP breaches.

---

## Critical Edge Cases & Technical Constraints

1. **File Download Links**: NEVER use native `st.download_button` for dynamic PDF or CSV generation. Always encode data into Base64 `data:` URIs inside standard `<a>` tags.
2. **HTML Formatting in Streamlit**: NEVER indent multiline HTML strings inside `st.markdown(..., unsafe_allow_html=True)` by 4 or more spaces.
3. **Plotly Chart Container**: Plotly charts must be rendered with `theme=None` and use `paper_bgcolor="rgba(0,0,0,0)"` and `plot_bgcolor="rgba(0,0,0,0)"` so they inherit the dark glass container backgrounds cleanly.
4. **Streamlit Config Base Theme**: Ensure `.streamlit/config.toml` has `base = "dark"` so native Streamlit popups and inputs don't fall back to light mode background colors.
5. **App Execution**:
   ```bash
   streamlit run app.py --server.port 8514 --server.headless true
   ```
6. **DOM Integrity**: NEVER wrap Streamlit widgets in custom HTML `<div>` tags using split `st.markdown` calls. The browser will auto-close the first `<div>` and the final `</div>` will break the parent React DOM container.

---

*Last updated: 2026-08-22 19:30 IST | Session 6 — React DOM Layout Fixes

