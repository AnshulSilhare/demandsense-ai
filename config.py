"""
DemandSense AI — Configuration Module
======================================
Central configuration for product catalog, regional parameters,
Indian festival calendar, and business constants.

Every product has a unique seasonality profile grounded in real
Indian FMCG demand behavior — this is what makes the synthetic
data realistic and the project defensible in interviews.

Author: Anshul Silhare
"""

from datetime import date

# ═══════════════════════════════════════════════════════════════
# PROJECT METADATA
# ═══════════════════════════════════════════════════════════════
PROJECT_NAME = "DemandSense AI"
PROJECT_TAGLINE = "Intelligent Demand Forecasting Engine for Indian FMCG"
VERSION = "1.0.19"

# ═══════════════════════════════════════════════════════════════
# DATA GENERATION PARAMETERS
# ═══════════════════════════════════════════════════════════════
DATA_START_DATE = "2023-01-01"
DATA_END_DATE = "2025-12-31"
RANDOM_SEED = 42

# ═══════════════════════════════════════════════════════════════
# PRODUCT CATALOG — 20 Indian FMCG SKUs
# ═══════════════════════════════════════════════════════════════
# Each product defines:
#   sku_id        : Unique identifier
#   name          : Display name
#   category      : Product category
#   base_price    : MRP in ₹
#   base_demand   : Average daily units sold per region (baseline)
#   seasonality   : Multipliers for each seasonal factor
#                   1.0 = no effect, >1.0 = demand boost, <1.0 = demand dip
#   noise_std     : Standard deviation of daily random noise (as fraction)
#   trend_pct_monthly : Monthly demand growth rate (%)

PRODUCTS = [
    {
        "sku_id": "SKU001",
        "name": "Premium Detergent 1kg",
        "category": "Home Care",
        "base_price": 225,
        "base_demand": 150,
        "seasonality": {
            "diwali": 1.45,              # Pre-Diwali deep cleaning tradition
            "holi": 1.25,                # Post-Holi stain removal
            "navratri": 1.10,
            "eid": 1.05,
            "ganesh_chaturthi": 1.05,
            "pongal": 1.05,
            "monsoon": 0.88,             # Drying issues reduce wash frequency
            "winter": 1.00,
            "summer": 1.05,
            "wedding": 1.00,
            "trend_pct_monthly": 0.15,
            "noise_std": 0.08,
        },
    },
    {
        "sku_id": "SKU002",
        "name": "Instant Noodles 4-Pack",
        "category": "Packaged Food",
        "base_price": 56,
        "base_demand": 480,
        "seasonality": {
            "diwali": 1.10,
            "holi": 1.05,
            "navratri": 0.70,            # Fasting period — reduced consumption
            "eid": 1.05,
            "ganesh_chaturthi": 1.00,
            "pongal": 1.00,
            "monsoon": 1.30,             # Comfort food on rainy days
            "winter": 1.25,              # Warm food demand
            "summer": 0.90,
            "wedding": 1.00,
            "trend_pct_monthly": 0.25,
            "noise_std": 0.10,
        },
    },
    {
        "sku_id": "SKU003",
        "name": "Fresh Butter 500g",
        "category": "Dairy",
        "base_price": 275,
        "base_demand": 85,
        "seasonality": {
            "diwali": 1.35,              # Sweets & festival cooking
            "holi": 1.15,
            "navratri": 1.20,            # Fasting-compatible cooking
            "eid": 1.15,
            "ganesh_chaturthi": 1.25,    # Modak preparation
            "pongal": 1.20,
            "monsoon": 0.95,
            "winter": 1.30,              # Paratha season
            "summer": 0.80,              # Melts easily, reduced usage
            "wedding": 1.25,             # Catering demand
            "trend_pct_monthly": 0.10,
            "noise_std": 0.12,
        },
    },
    {
        "sku_id": "SKU004",
        "name": "Iodized Salt 1kg",
        "category": "Staples",
        "base_price": 28,
        "base_demand": 300,
        "seasonality": {
            "diwali": 1.05,
            "holi": 1.02,
            "navratri": 1.02,
            "eid": 1.02,
            "ganesh_chaturthi": 1.02,
            "pongal": 1.02,
            "monsoon": 1.02,             # Essential — near-zero seasonality
            "winter": 1.02,
            "summer": 1.02,
            "wedding": 1.05,
            "trend_pct_monthly": 0.05,   # Very slow organic growth
            "noise_std": 0.05,           # Very low variance
        },
    },
    {
        "sku_id": "SKU005",
        "name": "Glucose Biscuits 800g",
        "category": "Packaged Food",
        "base_price": 50,
        "base_demand": 400,
        "seasonality": {
            "diwali": 1.50,              # Festival gifting & chai-time
            "holi": 1.15,
            "navratri": 1.05,
            "eid": 1.20,
            "ganesh_chaturthi": 1.10,
            "pongal": 1.10,
            "monsoon": 1.15,             # Tea + biscuits on rainy days
            "winter": 1.10,
            "summer": 0.95,
            "wedding": 1.10,
            "trend_pct_monthly": 0.12,
            "noise_std": 0.09,
        },
    },
    {
        "sku_id": "SKU006",
        "name": "Pure Honey 500g",
        "category": "Health Foods",
        "base_price": 350,
        "base_demand": 55,
        "seasonality": {
            "diwali": 1.15,
            "holi": 1.05,
            "navratri": 1.10,
            "eid": 1.05,
            "ganesh_chaturthi": 1.00,
            "pongal": 1.10,
            "monsoon": 0.75,             # Hot humid → low demand
            "winter": 1.80,              # Immunity season — warm honey water
            "summer": 0.65,              # Very low
            "wedding": 1.00,
            "trend_pct_monthly": 0.30,   # Strong health-trend growth
            "noise_std": 0.15,
        },
    },
    {
        "sku_id": "SKU007",
        "name": "Traditional Namkeen 400g",
        "category": "Snacks",
        "base_price": 120,
        "base_demand": 180,
        "seasonality": {
            "diwali": 2.80,              # MASSIVE — Diwali gifting staple
            "holi": 1.60,                # Party snack
            "navratri": 1.20,
            "eid": 1.50,                 # Eid celebrations
            "ganesh_chaturthi": 1.30,
            "pongal": 1.15,
            "monsoon": 0.85,
            "winter": 1.10,
            "summer": 0.90,
            "wedding": 1.50,             # Wedding snacks & gifting
            "trend_pct_monthly": 0.20,
            "noise_std": 0.12,
        },
    },
    {
        "sku_id": "SKU008",
        "name": "Mango Juice 1L",
        "category": "Beverages",
        "base_price": 95,
        "base_demand": 220,
        "seasonality": {
            "diwali": 1.00,
            "holi": 1.40,                # Holi party drink
            "navratri": 0.85,
            "eid": 1.10,
            "ganesh_chaturthi": 1.05,
            "pongal": 1.15,
            "monsoon": 0.70,             # Cool weather → cold drinks dip
            "winter": 0.45,              # Very low — off-season
            "summer": 2.20,              # PEAK — mango season + heat
            "wedding": 1.15,             # Event catering
            "trend_pct_monthly": 0.18,
            "noise_std": 0.14,
        },
    },
    {
        "sku_id": "SKU009",
        "name": "Coconut Hair Oil 200ml",
        "category": "Personal Care",
        "base_price": 110,
        "base_demand": 170,
        "seasonality": {
            "diwali": 1.20,
            "holi": 1.05,
            "navratri": 1.10,
            "eid": 1.05,
            "ganesh_chaturthi": 1.05,
            "pongal": 1.15,
            "monsoon": 1.10,             # Frizz control
            "winter": 1.35,              # Dry scalp → more oil usage
            "summer": 0.85,              # Oily feel → reduced usage
            "wedding": 1.40,             # Bridal grooming demand
            "trend_pct_monthly": 0.08,
            "noise_std": 0.07,
        },
    },
    {
        "sku_id": "SKU010",
        "name": "Dishwash Liquid 500ml",
        "category": "Home Care",
        "base_price": 99,
        "base_demand": 190,
        "seasonality": {
            "diwali": 1.40,              # Kitchen deep cleaning
            "holi": 1.15,                # Post-celebration cleanup
            "navratri": 1.10,
            "eid": 1.10,
            "ganesh_chaturthi": 1.15,
            "pongal": 1.10,
            "monsoon": 0.92,
            "winter": 0.95,
            "summer": 1.05,
            "wedding": 1.10,
            "trend_pct_monthly": 0.12,
            "noise_std": 0.06,
        },
    },
    {
        "sku_id": "SKU011",
        "name": "Basmati Rice 5kg",
        "category": "Staples",
        "base_price": 450,
        "base_demand": 110,
        "seasonality": {
            "diwali": 1.30,              # Festival cooking
            "holi": 1.10,
            "navratri": 1.05,
            "eid": 1.40,                 # Biryani for Eid
            "ganesh_chaturthi": 1.10,
            "pongal": 1.50,              # Pongal is literally a rice dish
            "monsoon": 1.00,
            "winter": 1.10,
            "summer": 0.95,
            "wedding": 1.60,             # Wedding feast catering
            "trend_pct_monthly": 0.08,
            "noise_std": 0.10,
        },
    },
    {
        "sku_id": "SKU012",
        "name": "Sunflower Oil 1L",
        "category": "Staples",
        "base_price": 180,
        "base_demand": 200,
        "seasonality": {
            "diwali": 1.45,              # Heavy cooking & sweets frying
            "holi": 1.20,                # Gujiya & puranpoli frying
            "navratri": 1.15,
            "eid": 1.25,
            "ganesh_chaturthi": 1.20,
            "pongal": 1.15,
            "monsoon": 0.95,
            "winter": 1.10,
            "summer": 0.95,
            "wedding": 1.35,             # Large-scale catering
            "trend_pct_monthly": 0.10,
            "noise_std": 0.08,
        },
    },
    {
        "sku_id": "SKU013",
        "name": "Green Tea 100 Bags",
        "category": "Beverages",
        "base_price": 250,
        "base_demand": 85,
        "seasonality": {
            "diwali": 1.00,
            "holi": 1.00,
            "navratri": 1.00,
            "eid": 1.00,
            "ganesh_chaturthi": 1.00,
            "pongal": 1.00,
            "monsoon": 1.20,             # Hot drinks in rain
            "winter": 1.40,              # Hot beverages peak
            "summer": 0.75,              # Cold drinks preferred
            "wedding": 1.00,
            "trend_pct_monthly": 0.40,   # Strong health-consciousness trend
            "noise_std": 0.10,
        },
    },
    {
        "sku_id": "SKU014",
        "name": "Face Wash 100ml",
        "category": "Personal Care",
        "base_price": 175,
        "base_demand": 145,
        "seasonality": {
            "diwali": 1.10,
            "holi": 1.25,                # Post-Holi color removal
            "navratri": 1.00,
            "eid": 1.05,
            "ganesh_chaturthi": 1.00,
            "pongal": 1.00,
            "monsoon": 1.25,             # Humid → oily skin → more usage
            "winter": 0.85,              # Dry skin → less frequent washing
            "summer": 1.35,              # Sweat & oil → peak demand
            "wedding": 1.15,             # Grooming
            "trend_pct_monthly": 0.22,
            "noise_std": 0.08,
        },
    },
    {
        "sku_id": "SKU015",
        "name": "Premium Chips 150g",
        "category": "Snacks",
        "base_price": 40,
        "base_demand": 350,
        "seasonality": {
            "diwali": 1.40,              # Party snacks
            "holi": 1.30,
            "navratri": 0.80,            # Fasting reduces snacking
            "eid": 1.20,
            "ganesh_chaturthi": 1.15,
            "pongal": 1.10,
            "monsoon": 1.15,             # Indoor snacking
            "winter": 1.10,
            "summer": 0.90,              # Humidity → soggy chips concern
            "wedding": 1.20,
            "trend_pct_monthly": 0.15,
            "noise_std": 0.11,
        },
    },
    {
        "sku_id": "SKU016",
        "name": "Chyawanprash 500g",
        "category": "Health Foods",
        "base_price": 320,
        "base_demand": 65,
        "seasonality": {
            "diwali": 1.05,
            "holi": 1.00,
            "navratri": 1.00,
            "eid": 1.00,
            "ganesh_chaturthi": 1.00,
            "pongal": 1.05,
            "monsoon": 0.60,             # Not popular in hot humid weather
            "winter": 2.50,              # MASSIVE — immunity season
            "summer": 0.40,              # Dead season
            "wedding": 1.00,
            "trend_pct_monthly": 0.20,
            "noise_std": 0.18,
        },
    },
    {
        "sku_id": "SKU017",
        "name": "Tomato Ketchup 500g",
        "category": "Condiments",
        "base_price": 110,
        "base_demand": 175,
        "seasonality": {
            "diwali": 1.10,
            "holi": 1.05,
            "navratri": 0.90,
            "eid": 1.05,
            "ganesh_chaturthi": 1.00,
            "pongal": 1.00,
            "monsoon": 1.10,             # Comfort food pairing
            "winter": 1.05,
            "summer": 1.00,
            "wedding": 1.05,
            "trend_pct_monthly": 0.10,
            "noise_std": 0.07,
        },
    },
    {
        "sku_id": "SKU018",
        "name": "Floor Cleaner 1L",
        "category": "Home Care",
        "base_price": 145,
        "base_demand": 125,
        "seasonality": {
            "diwali": 1.70,              # Deep cleaning tradition
            "holi": 1.30,                # Post-color cleanup
            "navratri": 1.15,
            "eid": 1.15,
            "ganesh_chaturthi": 1.10,
            "pongal": 1.10,
            "monsoon": 1.35,             # Muddy floors & hygiene
            "winter": 0.90,
            "summer": 1.00,
            "wedding": 1.05,
            "trend_pct_monthly": 0.15,
            "noise_std": 0.09,
        },
    },
    {
        "sku_id": "SKU019",
        "name": "Chocolate Bar 50g",
        "category": "Confectionery",
        "base_price": 45,
        "base_demand": 280,
        "seasonality": {
            "diwali": 1.60,              # Festival gifting
            "holi": 1.20,
            "navratri": 0.85,
            "eid": 1.30,                 # Eid gifting
            "ganesh_chaturthi": 1.10,
            "pongal": 1.05,
            "monsoon": 1.05,
            "winter": 1.35,              # Chocolate stays solid, comfort food
            "summer": 0.55,              # Melting → significant demand drop
            "wedding": 1.20,
            "trend_pct_monthly": 0.18,
            "noise_std": 0.12,
        },
    },
    {
        "sku_id": "SKU020",
        "name": "Mosquito Repellent 45ml",
        "category": "Home Care",
        "base_price": 85,
        "base_demand": 180,
        "seasonality": {
            "diwali": 0.90,
            "holi": 1.00,
            "navratri": 1.00,
            "eid": 1.00,
            "ganesh_chaturthi": 1.10,
            "pongal": 0.80,
            "monsoon": 2.40,             # MASSIVE — mosquito breeding season
            "winter": 0.50,              # Very low — cold kills mosquitoes
            "summer": 1.30,              # Pre-monsoon uptick
            "wedding": 1.00,
            "trend_pct_monthly": 0.12,
            "noise_std": 0.15,
        },
    },
]


# ═══════════════════════════════════════════════════════════════
# REGIONAL DEFINITIONS — 5 Indian Markets
# ═══════════════════════════════════════════════════════════════
# Each region has different:
#   demand_multiplier   : Scales base demand (purchasing power proxy)
#   monsoon_intensity   : How strongly monsoon affects this region
#   winter_intensity    : How strongly winter affects this region
#   summer_intensity    : How strongly summer affects this region

REGIONS = [
    {
        "id": "NORTH",
        "name": "North India (Delhi NCR)",
        "demand_multiplier": 1.20,       # High purchasing power
        "monsoon_intensity": 0.7,        # Moderate monsoon
        "winter_intensity": 1.4,         # Harsh winters
        "summer_intensity": 1.3,         # Extreme summers
    },
    {
        "id": "SOUTH",
        "name": "South India (Chennai)",
        "demand_multiplier": 0.90,
        "monsoon_intensity": 0.8,        # NE monsoon different timing
        "winter_intensity": 0.4,         # Very mild winters
        "summer_intensity": 1.1,
    },
    {
        "id": "WEST",
        "name": "West India (Mumbai)",
        "demand_multiplier": 1.30,       # Highest purchasing power
        "monsoon_intensity": 1.5,        # VERY heavy Mumbai monsoon
        "winter_intensity": 0.3,         # Almost no winter
        "summer_intensity": 1.0,
    },
    {
        "id": "EAST",
        "name": "East India (Kolkata)",
        "demand_multiplier": 0.85,
        "monsoon_intensity": 1.2,        # Heavy rainfall
        "winter_intensity": 1.0,         # Moderate winters
        "summer_intensity": 1.1,
    },
    {
        "id": "CENTRAL",
        "name": "Central India (Nagpur)",
        "demand_multiplier": 0.70,       # Smaller market
        "monsoon_intensity": 0.9,
        "winter_intensity": 1.1,
        "summer_intensity": 1.2,         # Known for extreme heat
    },
]


# ═══════════════════════════════════════════════════════════════
# INDIAN FESTIVAL CALENDAR (2022–2026)
# ═══════════════════════════════════════════════════════════════
# Dates sourced from Hindu/Islamic lunar calendars.
# Each festival defines:
#   ramp_up_days  : How many days before the festival demand starts rising
#   post_days     : How many days after the festival demand remains elevated
#   peak_offset   : Days relative to festival when demand peaks
#                   (negative = before, 0 = on the day)

INDIAN_FESTIVALS = {
    "diwali": {
        "name": "Diwali",
        "dates": [
            date(2022, 10, 24), date(2023, 11, 12), date(2024, 11, 1),
            date(2025, 10, 20), date(2026, 10, 8),
        ],
        "ramp_up_days": 15,          # Shopping starts 2 weeks before
        "post_days": 3,              # Brief post-Diwali dip
        "peak_offset": -2,           # Peak demand 2 days before Diwali
    },
    "holi": {
        "name": "Holi",
        "dates": [
            date(2022, 3, 18), date(2023, 3, 8), date(2024, 3, 25),
            date(2025, 3, 14), date(2026, 3, 3),
        ],
        "ramp_up_days": 7,
        "post_days": 3,
        "peak_offset": -1,
    },
    "navratri": {
        "name": "Navratri (Sharad)",
        "dates": [
            date(2022, 9, 26), date(2023, 10, 15), date(2024, 10, 3),
            date(2025, 9, 22), date(2026, 10, 11),
        ],
        "ramp_up_days": 10,          # 9 nights + lead-up
        "post_days": 2,
        "peak_offset": -3,
    },
    "eid": {
        "name": "Eid ul-Fitr",
        "dates": [
            date(2022, 5, 3), date(2023, 4, 22), date(2024, 4, 11),
            date(2025, 3, 31), date(2026, 3, 21),
        ],
        "ramp_up_days": 7,
        "post_days": 3,
        "peak_offset": -1,
    },
    "ganesh_chaturthi": {
        "name": "Ganesh Chaturthi",
        "dates": [
            date(2022, 8, 31), date(2023, 9, 19), date(2024, 9, 7),
            date(2025, 8, 27), date(2026, 9, 15),
        ],
        "ramp_up_days": 5,
        "post_days": 10,             # 10-day celebration (Ganapati Visarjan)
        "peak_offset": 0,
    },
    "pongal": {
        "name": "Pongal / Makar Sankranti",
        "dates": [
            date(2022, 1, 14), date(2023, 1, 14), date(2024, 1, 15),
            date(2025, 1, 14), date(2026, 1, 14),
        ],
        "ramp_up_days": 5,
        "post_days": 2,
        "peak_offset": 0,
    },
}


# ═══════════════════════════════════════════════════════════════
# DAY-OF-WEEK DEMAND MULTIPLIERS
# ═══════════════════════════════════════════════════════════════
# FMCG pattern: slightly higher on weekends (family shopping trips)

DOW_MULTIPLIERS = {
    0: 0.95,     # Monday
    1: 0.93,     # Tuesday — lowest (post-weekend lull)
    2: 0.97,     # Wednesday
    3: 1.00,     # Thursday
    4: 1.05,     # Friday — pre-weekend stocking
    5: 1.12,     # Saturday — peak retail day
    6: 1.08,     # Sunday — family shopping
}


# ═══════════════════════════════════════════════════════════════
# SALARY CYCLE EFFECT
# ═══════════════════════════════════════════════════════════════
# Indian FMCG: demand spikes when salaries credit (25th–5th)

SALARY_CYCLE_BOOST = 1.08    # 8% demand boost during salary window


# ═══════════════════════════════════════════════════════════════
# BUSINESS CONSTANTS (Used in Phase 3)
# ═══════════════════════════════════════════════════════════════

SERVICE_LEVELS = {
    "A": {"z_score": 2.33, "target_pct": 99.0, "label": "Critical SKU"},
    "B": {"z_score": 1.65, "target_pct": 95.0, "label": "Important SKU"},
    "C": {"z_score": 1.28, "target_pct": 90.0, "label": "Standard SKU"},
}

HOLDING_COST_PCT = 0.25               # 25% of product value per year
DEFAULT_LEAD_TIME_DAYS = 7            # Average supplier lead time
STOCKOUT_COST_MULTIPLIER = 1.5        # Lost sale cost = 1.5× margin
GROSS_MARGIN_PCT = 0.30               # Assumed 30% gross margin for FMCG
