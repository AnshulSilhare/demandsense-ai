"""
DemandSense AI — Synthetic Indian FMCG Data Generator
======================================================
Generates realistic daily sales data for 20 Indian FMCG products
across 5 regions with embedded seasonality signals:

  - Indian festival effects (Diwali, Holi, Navratri, Eid, etc.)
    using Gaussian proximity curves for realistic ramp-up/drop-off
  - Seasonal effects (monsoon, winter, summer) modulated by region
  - Wedding season demand spikes
  - Day-of-week patterns (weekend shopping boost)
  - Salary cycle effect (25th–5th month boost)
  - Long-term growth trend
  - Controlled random noise per product

Each effect is a separate multiplier method — this modular design
makes every component independently testable and explainable.

Author: Anshul Silhare
"""

import numpy as np
import pandas as pd
from config import (
    PRODUCTS, REGIONS, INDIAN_FESTIVALS,
    DOW_MULTIPLIERS, SALARY_CYCLE_BOOST,
    DATA_START_DATE, DATA_END_DATE, RANDOM_SEED,
)


class IndianFMCGDataGenerator:
    """
    Generates synthetic daily sales data for Indian FMCG products.

    Architecture:
        For each (product, region, date) combination, the daily demand
        is computed as:

        demand = base × trend × dow × festival × season × wedding × salary × noise

        Each factor is a multiplier around 1.0, making the effects
        composable and interpretable.
    """

    def __init__(self, start_date=None, end_date=None, seed=None):
        self.start_date = pd.Timestamp(start_date or DATA_START_DATE)
        self.end_date = pd.Timestamp(end_date or DATA_END_DATE)
        self.rng = np.random.default_rng(seed or RANDOM_SEED)
        self.dates = pd.date_range(self.start_date, self.end_date, freq="D")

    def generate(self) -> pd.DataFrame:
        """Generate complete dataset: all products × all regions × all dates."""
        total_combos = len(PRODUCTS) * len(REGIONS)
        print(f"Generating data: {len(PRODUCTS)} SKUs × {len(REGIONS)} regions "
              f"× {len(self.dates)} days = ~{total_combos * len(self.dates):,} records")

        all_records = []
        for i, product in enumerate(PRODUCTS, 1):
            for region in REGIONS:
                records = self._generate_sku_region_series(product, region)
                all_records.extend(records)
            print(f"  [{i}/{len(PRODUCTS)}] {product['name']} — done")

        df = pd.DataFrame(all_records)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values(["date", "sku_id", "region_id"]).reset_index(drop=True)

        print(f"\n[OK] Generated {len(df):,} records")
        print(f"  Date range : {df['date'].min().date()} -> {df['date'].max().date()}")
        print(f"  Total revenue : INR {df['revenue_inr'].sum():,.0f}")

        return df

    # ─────────────────────────────────────────────────────────
    # CORE GENERATION LOOP
    # ─────────────────────────────────────────────────────────

    def _generate_sku_region_series(self, product, region):
        """Generate daily sales for one SKU in one region."""
        seasonality = product["seasonality"]
        base = product["base_demand"] * region["demand_multiplier"]

        records = []
        for date in self.dates:
            # Compose all multiplicative effects
            demand = base
            demand *= self._trend_factor(date, seasonality)
            demand *= DOW_MULTIPLIERS[date.dayofweek]
            demand *= self._festival_factor(date, seasonality)
            demand *= self._seasonal_factor(date, seasonality, region)
            demand *= self._wedding_factor(date, seasonality)
            demand *= self._salary_cycle_factor(date)

            # Add controlled random noise
            noise_std = seasonality.get("noise_std", 0.08)
            noise = self.rng.normal(1.0, noise_std)
            demand *= max(0.5, noise)  # Clamp to avoid extreme negatives

            # Final: round to integer, minimum 0
            units = max(0, round(demand))

            records.append({
                "date": date,
                "sku_id": product["sku_id"],
                "sku_name": product["name"],
                "category": product["category"],
                "region_id": region["id"],
                "region_name": region["name"],
                "units_sold": units,
                "unit_price_inr": product["base_price"],
                "revenue_inr": units * product["base_price"],
            })

        return records

    # ─────────────────────────────────────────────────────────
    # EFFECT 1: LONG-TERM TREND
    # ─────────────────────────────────────────────────────────

    def _trend_factor(self, date, seasonality):
        """
        Linear growth trend over time.
        e.g., 0.15% monthly growth = ~1.8% annual growth.
        """
        months_elapsed = (date - self.start_date).days / 30.44
        monthly_growth = seasonality.get("trend_pct_monthly", 0.1) / 100
        return 1 + monthly_growth * months_elapsed

    # ─────────────────────────────────────────────────────────
    # EFFECT 2: INDIAN FESTIVAL PROXIMITY
    # ─────────────────────────────────────────────────────────

    def _festival_factor(self, date, seasonality):
        """
        Calculate festival demand effect using Gaussian proximity curves.

        For demand-boosting festivals: takes the MAX boost across all
        active festivals (prevents unrealistic compounding).

        For demand-reducing festivals (e.g., Navratri fasting):
        takes the MIN reduction.

        Final factor = max_boost × min_reduction
        """
        max_boost = 1.0
        min_reduce = 1.0

        for festival_key, festival_info in INDIAN_FESTIVALS.items():
            product_multiplier = seasonality.get(festival_key, 1.0)
            if product_multiplier == 1.0:
                continue

            for festival_date in festival_info["dates"]:
                days_diff = (date.date() - festival_date).days
                ramp = festival_info["ramp_up_days"]
                post = festival_info["post_days"]

                # Only apply if within the festival's influence window
                if not (-ramp <= days_diff <= post):
                    continue

                peak = festival_info.get("peak_offset", -1)

                # Gaussian proximity curve
                if days_diff <= 0:
                    # Pre-festival: gradual ramp-up
                    sigma = max(ramp / 2.5, 1)
                    effect = np.exp(-0.5 * ((days_diff - peak) / sigma) ** 2)
                else:
                    # Post-festival: sharper drop-off
                    sigma = max(post / 1.5, 1)
                    effect = np.exp(-0.5 * (days_diff / sigma) ** 2) * 0.3

                this_factor = 1 + (product_multiplier - 1) * effect

                if product_multiplier > 1.0:
                    max_boost = max(max_boost, this_factor)
                else:
                    min_reduce = min(min_reduce, this_factor)

        return max_boost * min_reduce

    # ─────────────────────────────────────────────────────────
    # EFFECT 3: SEASONAL (MONSOON / WINTER / SUMMER)
    # ─────────────────────────────────────────────────────────

    def _seasonal_factor(self, date, seasonality, region):
        """
        Seasonal effect modulated by regional intensity.
        Mumbai has 1.5× monsoon intensity; Delhi has 1.4× winter intensity.
        """
        month = date.month
        factor = 1.0

        if month in (6, 7, 8, 9):
            # Monsoon season
            product_effect = seasonality.get("monsoon", 1.0)
            regional_intensity = region.get("monsoon_intensity", 1.0)
            deviation = product_effect - 1.0
            factor = 1.0 + deviation * regional_intensity

        elif month in (11, 12, 1, 2):
            # Winter season
            product_effect = seasonality.get("winter", 1.0)
            regional_intensity = region.get("winter_intensity", 1.0)
            deviation = product_effect - 1.0
            factor = 1.0 + deviation * regional_intensity

        elif month in (3, 4, 5):
            # Summer season (peak in April-May)
            product_effect = seasonality.get("summer", 1.0)
            regional_intensity = region.get("summer_intensity", 1.0)
            # March is transition; April-May are peak summer
            intensity_scale = 0.6 if month == 3 else 1.0
            deviation = product_effect - 1.0
            factor = 1.0 + deviation * regional_intensity * intensity_scale

        # October is transition month — neutral
        return factor

    # ─────────────────────────────────────────────────────────
    # EFFECT 4: WEDDING SEASON
    # ─────────────────────────────────────────────────────────

    def _wedding_factor(self, date, seasonality):
        """
        Indian wedding season demand spike.
        Peak: Nov–Feb (winter weddings), Secondary: Apr–May (pre-monsoon).
        Off-season: Jun–Sep (Shravan, monsoon — inauspicious).
        """
        month = date.month
        wedding_boost = seasonality.get("wedding", 1.0)

        if wedding_boost <= 1.0:
            return 1.0

        if month in (11, 12, 1, 2):
            return 1 + (wedding_boost - 1) * 0.8     # Peak
        elif month in (4, 5):
            return 1 + (wedding_boost - 1) * 0.6     # Secondary
        elif month in (6, 7, 8):
            return 1.0                                 # Off-season
        else:
            return 1 + (wedding_boost - 1) * 0.3     # Mild

    # ─────────────────────────────────────────────────────────
    # EFFECT 5: SALARY CYCLE
    # ─────────────────────────────────────────────────────────

    def _salary_cycle_factor(self, date):
        """
        FMCG demand spikes when salaries credit.
        Most Indian companies pay between 25th and 1st.
        Consumer spending peaks in the 25th–5th window.
        """
        day = date.day
        if day >= 25 or day <= 5:
            return SALARY_CYCLE_BOOST
        return 1.0

    # ─────────────────────────────────────────────────────────
    # SAVE UTILITY
    # ─────────────────────────────────────────────────────────

    def save(self, df, filepath):
        """Save generated data to CSV."""
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        df.to_csv(filepath, index=False)
        print(f"[OK] Saved to {filepath} ({len(df):,} rows)")
