# DemandSense AI — Technical Notes & Domain Knowledge Guide

---

## 1. Prophet in Indian Retail & FMCG

### 1.1 Do companies in India use Meta's Prophet?
**Yes, extensively.** Leading Indian e-commerce, quick-commerce, retail, and FMCG enterprises (including **Flipkart, Swiggy, Zepto, BigBasket, Reliance Retail, and Hindustan Unilever**) utilize Prophet and Prophet-hybrid architectures for operational demand forecasting.

### 1.2 Why Prophet is exceptionally effective for the Indian Market
1. **Luni-Solar Festival Date Shifts**:
   * Unlike Western retail where major events occur on static calendar dates (e.g., Christmas on Dec 25), major Indian festivals (**Diwali, Eid, Holi, Raksha Bandhan, Dussehra, Ganesh Chaturthi**) follow lunar and luni-solar calendars.
   * A festival like Diwali can occur anywhere between mid-October and mid-November. Traditional ARIMA models struggle because the seasonal period is non-integer and shifts from year to year.
   * Prophet solves this using a dedicated **Holiday Regressor Matrix** ($h(t)$) where exact annual festival dates and asymmetrical ramp-up windows are provided:
     $$\text{Diwali Window: } \text{lower\_window} = -14 \text{ (2-week pre-festival stockup surge)}, \quad \text{upper\_window} = +1$$
2. **Robustness to Kirana & Tier-2/3 Distributor Data Gaps**:
   * Indian distribution data frequently contains missing timestamps, stockout zeroes, or distributor reporting gaps.
   * Because Prophet fits non-linear curves (Fourier series) rather than computing strict contiguous difference lags, it handles missing dates without pipeline breaks.
3. **Executive Interpretability & Additive Decomposition**:
   * Business heads and operations managers require explainable forecasts. Prophet isolates demand into distinct additive components:
     $$y(t) = g(t) + s(t) + h(t) + \epsilon_t$$
     * $g(t)$: Baseline growth trend
     * $s(t)$: Day-of-week & monthly seasonality
     * $h(t)$: Holiday/festival shock multipliers
     * $\epsilon_t$: Irregular residual variance

---

## 2. Exponential Smoothing & Parameter Optimization ($\alpha, \beta, \gamma$)

### 2.1 Parameter Roles in Exponential Smoothing
* **$\alpha$ (Alpha — Level Factor, $0 \le \alpha \le 1$)**: Controls how rapidly the model updates its baseline estimate in response to recent sales. A high $\alpha$ puts heavy weight on the latest days; a low $\alpha$ creates a slow, steady smoothed baseline.
* **$\beta$ (Beta — Trend Factor, $0 \le \beta \le 1$)**: Controls how quickly the model updates the trajectory (upward/downward slope) of growth.
* **$\gamma$ (Gamma — Seasonality Factor, $0 \le \gamma \le 1$)**: Controls how strongly repeating periodic cycles (e.g., Sunday grocery surges vs. Tuesday dips) influence predictions.

### 2.2 How Parameters Are Optimized in DemandSense AI
In `src/forecasting/exp_smoothing.py`, `statsmodels` is configured with:
```python
model = ExponentialSmoothing(
    series,
    trend="add",
    seasonal="add",
    seasonal_periods=7,
    initialization_method="estimated"
)
self.model_fit = model.fit(optimized=True)
```
* With `optimized=True`, the engine **does not use arbitrary or fixed parameters**.
* It runs **Maximum Likelihood Estimation (L-BFGS-B numerical optimization)** over the historical training window to mathematically minimize the Sum of Squared Errors (SSE), automatically solving for the optimal $\alpha, \beta, \gamma$ values unique to each SKU.

---

## 3. What is Holt-Winters (Triple Exponential Smoothing)?

### 3.1 The Progression of Smoothing Models
| Model | Smoothing Parameters | What It Captures | Typical Output |
| :--- | :--- | :--- | :--- |
| **Simple Exponential Smoothing (SES)** | $\alpha$ | Baseline Level | Flat horizontal forecast line (recent weighted average) |
| **Double Exponential Smoothing (Holt's Linear)** | $\alpha, \beta$ | Level + Linear Trend | Upward or downward sloping trendline without recurring day patterns |
| **Triple Exponential Smoothing (Holt-Winters)** | $\mathbf{\alpha, \beta, \gamma}$ | **Level + Trend + Seasonality** | **Full undulating wave capturing weekly sales cycles** |

### 3.2 Mathematical Formulation (Additive Holt-Winters)
At each time step $t$ with seasonal cycle period $m$ (where $m=7$ for weekly cycles):
1. **Level Update**:
   $$L_t = \alpha (y_t - S_{t-m}) + (1 - \alpha)(L_{t-1} + T_{t-1})$$
2. **Trend Update**:
   $$T_t = \beta (L_t - L_{t-1}) + (1 - \beta) T_{t-1}$$
3. **Seasonal Component Update**:
   $$S_t = \gamma (y_t - L_t) + (1 - \gamma) S_{t-m}$$
4. **$h$-step Ahead Forecast**:
   $$\hat{y}_{t+h} = L_t + h T_t + S_{t+h-m}$$

---

## 4. Application & Implementation in DemandSense AI

### 4.1 File Architecture
* **`src/forecasting/exp_smoothing.py`**: Standalone Holt-Winters forecaster with `seasonal_periods=7` (modeling the 7-day Indian supermarket/kirana retail cycle).
* **`src/forecasting/prophet_model.py`**: Meta Prophet implementation augmented with Indian festival calendars and an automatic fallback mechanism.
* **`src/forecasting/auto_selector.py`**: The Auto-ML Arena engine that fits all candidate models on historical data, scores them on an unseen 60-day test set, and selects the winning model based on MAPE.

### 4.2 Cloud Deployment Fallback Safeguard
* **Why Prophet and Exponential Smoothing may share identical metrics in cloud environments**:
  * Meta's official `prophet` package is built on C++ Stan (`cmdstanpy`), requiring heavy C++ toolchains and >500MB of RAM during compilation.
  * In resource-constrained free-tier cloud containers (e.g., Render's 512MB RAM cap), `prophet` is kept optional to guarantee ultra-fast builds and prevent container out-of-memory (OOM) crashes.
  * When `prophet` is not installed (`PROPHET_AVAILABLE = False`), `ProphetForecaster` automatically and safely delegates to `ExpSmoothingForecaster`. This ensures zero downtime while preserving accurate, production-ready forecasts.

---

## 5. AI Control Room & Prescriptive LLM Reasoning

* **Dual-Engine Design**:
  * **Primary (Google Gemini API)**: Analyzes stockout risks, safety stock requirements, and winning model rationales to generate structured CSCO action plans.
  * **Offline Fallback Engine**: A deterministic Python rule-based expert system guaranteeing 100% uptime when API keys are not supplied.
* **Data Privacy Guarantee**:
  * Raw customer CSVs, store-level logs, and transaction tables **never leave the local server**.
  * All ML training (XGBoost, SARIMAX, Holt-Winters) and supply chain equations (Safety Stock, Reorder Point, Days of Supply) execute locally in Python.
  * Only 5 aggregate numerical summary metrics are sent to the LLM for executive narrative synthesis.
