"""
DemandSense AI — Supply Chain Control Tower & AI Demand Forecasting Engine
=============================================================================
Executive-grade Analytics Dashboard & Decision Support System
for Indian FMCG Demand Forecasting and Inventory Optimization.

Author: Anshul Silhare | Welingkar Institute of Management (WeSchool)
Target Audience: VPs, Ops Directors, and recruiters at EY / CTS / Infosys / Accenture / Dow / ITC / Marico
"""

import os
import sys
import base64
from datetime import timedelta
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# Setup project path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from tokens import DARK_TOKENS, LIGHT_TOKENS
from config import PRODUCTS, REGIONS, SERVICE_LEVELS, DEFAULT_LEAD_TIME_DAYS, VERSION, INDIAN_FESTIVALS
from src.forecasting.auto_selector import ModelAutoSelector
from src.business_impact import OperationsImpactCalculator
from src.llm_agent import LLMPrescriptiveAgent
from src.pdf_exporter import generate_executive_pdf_report
from src.analytics_helpers import (
    decompose_time_series,
    prepare_radar_data,
    get_festival_impact_summary,
    generate_svg_sparkline,
    is_delta_favorable,
)

# ═══════════════════════════════════════════════════════════════
# STREAMLIT PAGE CONFIGURATION
# ═══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="DemandSense AI — Supply Chain Control Tower",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for theme (defaults to dark)
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

is_dark = st.session_state.theme == "dark"

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

def extract_name(item: dict) -> str:
    """Robust extractor for inconsistent config schemas."""
    return item.get("name", item.get("sku_name", item.get("region_name", "Unknown")))

def get_filtered_timeseries(df, sku_id, region_id, cols):
    """Centralized Pandas filtering to prevent redundant groupby operations."""
    if region_id == "ALL":
        return df[df["sku_id"] == sku_id].groupby("date")[cols].sum().reset_index()
    return df[(df["sku_id"] == sku_id) & (df["region_id"] == region_id)].groupby("date")[cols].sum().reset_index()


# ═══════════════════════════════════════════════════════════════
# CSS INJECTOR — Blueprint Design Tokens & Typography
# ═══════════════════════════════════════════════════════════════
def inject_css(theme: str = "dark"):
    tokens = DARK_TOKENS if theme == "dark" else LIGHT_TOKENS
    is_dark = theme == "dark"
    glass_bg_outer = "rgba(15, 19, 32, 0.20)" if is_dark else "rgba(247, 246, 252, 0.30)"
    glass_bg_inner = "rgba(26, 32, 51, 0.38)" if is_dark else "rgba(255, 255, 255, 0.6)"
    glass_border = "rgba(255, 255, 255, 0.14)" if is_dark else "rgba(15, 23, 42, 0.08)"
    glass_highlight = "rgba(255, 255, 255, 0.28)" if is_dark else "rgba(255, 255, 255, 0.8)"
    glass_scroll_thumb = "rgba(255,255,255,0.15)" if is_dark else "rgba(15,23,42,0.15)"
    glass_input_bg = "rgba(255, 255, 255, 0.06)" if is_dark else "rgba(15, 23, 42, 0.04)"
    glass_input_border = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(15, 23, 42, 0.1)"
    glass_glow_start = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(255, 255, 255, 0.6)"
    glass_glow_mid = "rgba(255, 255, 255, 0.04)" if is_dark else "rgba(255, 255, 255, 0.2)"
    slider_knob = "rgba(255,255,255,0.4)" if is_dark else "rgba(110,86,207,0.4)"

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600;700&display=swap');

:root {{
    --bg-canvas: {tokens['bg_canvas']};
    --bg-shell: {tokens['bg_shell']};
    --bg-surface: {tokens['bg_surface']};
    --bg-surface-elevated: {tokens['bg_surface_elevated']};
    --bg-surface-hover: {tokens['bg_surface_hover']};
    --border-subtle: {tokens['border_subtle']};
    --border-default: {tokens['border_default']};
    --text-primary: {tokens['text_primary']};
    --text-secondary: {tokens['text_secondary']};
    --text-tertiary: {tokens['text_tertiary']};
    --accent-primary: {tokens['accent_primary']};
    --accent-primary-soft: {tokens['accent_primary_soft']};
    --accent-secondary: {tokens['accent_secondary']};
    --accent-secondary-soft: {tokens['accent_secondary_soft']};
    --status-critical: {tokens['status_critical']};
    --status-critical-bg: {tokens['status_critical_bg']};
    --status-warning: {tokens['status_warning']};
    --status-warning-bg: {tokens['status_warning_bg']};
    --status-healthy: {tokens['status_healthy']};
    --status-healthy-bg: {tokens['status_healthy_bg']};
    --shell-gap: 16px;
    --shell-radius: 24px;
    --glass-bg-outer: {glass_bg_outer};
    --glass-bg-inner: {glass_bg_inner};
    --glass-border: {glass_border};
    --glass-highlight: {glass_highlight};
}}

/* ═══ Phase 1: Global Canvas & Ambient Blob Layer ═══ */
.stApp {{
    background-color: var(--bg-canvas) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    position: relative;
    overflow-x: hidden;
}}
.block-container {{
    padding-top: 2rem !important;
    padding-bottom: 2rem !important;
}}
.stApp::before {{
    content: "";
    position: fixed;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    background:
        radial-gradient(600px circle at 8% 15%, rgba(110, 86, 207, 0.35), transparent 60%),
        radial-gradient(500px circle at 15% 75%, rgba(201, 138, 46, 0.22), transparent 60%),
        radial-gradient(700px circle at 90% 30%, rgba(34, 195, 182, 0.15), transparent 65%);
    filter: blur(60px);
    animation: ds-blob-drift 22s ease-in-out infinite alternate;
}}
@keyframes ds-blob-drift {{
    0%   {{ transform: translate(0, 0) scale(1); }}
    50%  {{ transform: translate(2%, -3%) scale(1.05); }}
    100% {{ transform: translate(-2%, 3%) scale(1); }}
}}

/* Reduced motion — respect OS/browser preference */
@media (prefers-reduced-motion: reduce) {{
    .stApp::before {{ animation: none; }}
    * {{ transition-duration: 0.01ms !important; animation-duration: 0.01ms !important; }}
}}

/* Content layers sit above the ambient blob */
[data-testid="stAppViewContainer"], [data-testid="stSidebar"] {{
    position: relative;
    z-index: 1;
}}

/* ═══ Floating Outer Shell Container ═══ */
[data-testid="stAppViewContainer"] > .main {{
    background: var(--bg-shell) !important;
    border-radius: var(--shell-radius) !important;
    margin: var(--shell-gap) !important;
    max-width: 1560px !important;
    padding: 20px 24px 40px 24px !important;
    border: 1px solid var(--border-subtle) !important;
    box-shadow: {tokens['shadow']} !important;
}}
[data-testid="stHeader"] {{
    background: transparent !important;
}}

/* ═══ Phase 2: Container Card Shells ═══ */
[data-testid="stVerticalBlockBorderWrapper"] {{
    background: var(--bg-surface) !important;
    border-radius: 16px !important;
    border: 1px solid var(--border-subtle) !important;
    box-shadow: {tokens['shadow']} !important;
    padding: 20px 24px !important;
    margin-bottom: 28px !important;
    transition: border-color 280ms cubic-bezier(0.22, 1, 0.36, 1) !important;
}}
[data-testid="stVerticalBlockBorderWrapper"]:hover {{
    border-color: var(--border-default) !important;
}}

/* Hide Streamlit's native element hover toolbar */
[data-testid="stElementToolbar"] {{ display: none !important; }}

/* ═══ Sticky Command Bar ═══ */
.command-bar {{
    position: sticky;
    top: 0;
    z-index: 100;
    backdrop-filter: blur(14px) saturate(140%);
    -webkit-backdrop-filter: blur(14px) saturate(140%);
    background: {tokens['command_bar_bg']};
    border-radius: 18px;
    padding: 20px 24px;
    margin-bottom: 32px;
    border: 1px solid var(--border-default);
    box-shadow: {tokens['shadow']};
}}

/* ═══ Standard Cards ═══ */
.ds-card {{
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 16px;
    padding: 22px 24px;
    box-shadow: {tokens['shadow']};
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
    min-height: 220px;
    transition: transform 280ms cubic-bezier(0.22, 1, 0.36, 1), border-color 280ms cubic-bezier(0.22, 1, 0.36, 1);
}}
.ds-card.clickable:hover {{
    transform: translateY(-2px);
    border-color: var(--accent-primary);
}}

/* ═══ Icon Chips ═══ */
.ds-icon-chip {{
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 14px;
}}
.ds-icon-chip.indigo {{ background: var(--accent-primary-soft); color: var(--accent-primary); }}
.ds-icon-chip.gold   {{ background: var(--accent-secondary-soft); color: var(--accent-secondary); }}
.ds-icon-chip.red    {{ background: var(--status-critical-bg); color: var(--status-critical); }}
.ds-icon-chip.teal   {{ background: rgba(34,195,182,0.14); color: #22C3B6; }}
.ds-icon-chip.green  {{ background: var(--status-healthy-bg); color: var(--status-healthy); }}

/* ═══ KPI Typography ═══ */
.ds-caption {{
    font-family: 'Inter', sans-serif;
    font-size: 0.74rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--text-secondary);
    margin-bottom: 6px;
}}
.ds-kpi-value {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 2.15rem;
    font-weight: 700;
    color: var(--text-primary);
    font-variant-numeric: tabular-nums;
    line-height: 1.1;
    letter-spacing: -0.02em;
    margin-bottom: 10px;
}}

/* ═══ Status Badges ═══ */
.ds-badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border-radius: 999px;
    padding: 5px 12px;
    font-family: 'Inter', sans-serif;
    font-size: 0.74rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}}
.ds-badge.critical {{ background: var(--status-critical-bg); color: var(--status-critical); border: 1px solid rgba(239,68,68,0.2); }}
.ds-badge.warning  {{ background: var(--status-warning-bg); color: var(--status-warning); border: 1px solid rgba(245,166,35,0.2); }}
.ds-badge.healthy  {{ background: var(--status-healthy-bg); color: var(--status-healthy); border: 1px solid rgba(34,197,94,0.2); }}

/* Pulsing Dot */
.ds-badge.pulse::before {{
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
    animation: ds-pulse 2s ease-in-out infinite;
}}
@keyframes ds-pulse {{
    0%, 100% {{ opacity: 0.3; transform: scale(0.9); }}
    50% {{ opacity: 1; transform: scale(1.1); }}
}}

/* ═══ Typography Hierarchy ═══ */
h1, h2, h3, h4 {{
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    color: var(--text-primary) !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
}}
h3, h4 {{
    margin-top: 12px !important;
    margin-bottom: 16px !important;
}}
p, span, label, div {{
    font-family: 'Inter', sans-serif;
}}

/* ═══ Tabs ═══ */
button[data-baseweb="tab"] {{
    background-color: transparent !important;
    color: var(--text-tertiary) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    padding: 12px 24px !important;
    border-radius: 8px !important;
    transition: color 280ms cubic-bezier(0.22, 1, 0.36, 1) !important;
    border: none !important;
}}
button[data-baseweb="tab"]:hover {{
    color: var(--text-primary) !important;
}}
button[aria-selected="true"] {{
    background-color: transparent !important;
    color: var(--accent-primary) !important;
    border-bottom: 2px solid var(--accent-primary) !important;
    border-radius: 0 !important;
}}
[data-baseweb="tab-list"] {{
    border-bottom: 1px solid var(--border-subtle) !important;
    gap: 16px !important;
    margin-bottom: 32px !important;
}}
.stTabs [data-baseweb="tab-panel"] {{
    padding-top: 20px !important;
    padding-bottom: 48px !important;
}}

/* ═══ Dataframe & Layout ═══ */
.stDataFrame {{
    border: 1px solid var(--border-subtle) !important;
    border-radius: 12px !important;
    margin-bottom: 16px !important;
}}
[data-testid="stTable"] td, [data-testid="stDataFrame"] td {{
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.85rem !important;
}}
.stApp hr {{
    border-color: var(--border-subtle) !important;
    margin-top: 32px !important;
    margin-bottom: 32px !important;
}}

/* ═══════════════════════════════════════════════════════════ */
/* Phase 3: Floating Liquid-Glass Sidebar Shell Architecture */
/* ═══════════════════════════════════════════════════════════ */

/* 3.1 — Sidebar is detached, floating, and has the Liquid Glass effect. */
[data-testid="stSidebar"] {{
    background: var(--glass-bg-outer) !important;
    backdrop-filter: blur(28px) saturate(180%);
    -webkit-backdrop-filter: blur(28px) saturate(180%);
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--shell-radius) !important;
    box-shadow: 8px 12px 40px rgba(0, 0, 0, 0.15) !important;
    margin: 12px !important;
    height: calc(100vh - 24px) !important;
}}

/* 3.1 — minimal padding on inner content to prevent compression */
[data-testid="stSidebarContent"],
[data-testid="stSidebarUserContent"] {{
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    padding: 16px 12px !important;
    overflow-y: auto;
    overflow-x: hidden;
    display: flex;
    flex-direction: column;
}}

/* Custom scrollbar on sidebar */
[data-testid="stSidebarContent"]::-webkit-scrollbar {{ width: 6px; }}
[data-testid="stSidebarContent"]::-webkit-scrollbar-thumb {{ background: {glass_scroll_thumb}; border-radius: 999px; }}
[data-testid="stSidebarContent"]::-webkit-scrollbar-track {{ background: transparent; }}

/* Sidebar text */
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p {{ color: var(--text-secondary) !important; }}
[data-testid="stSidebar"] hr {{ border-color: var(--glass-border) !important; margin: 18px 0 !important; }}

/* 3.2 — Nested glass section panels with specular highlight */
[data-testid="stSidebarContent"] [data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stSidebarUserContent"] [data-testid="stVerticalBlockBorderWrapper"] {{
    position: relative !important;
    background: var(--glass-bg-inner) !important;
    backdrop-filter: blur(18px) saturate(160%) !important;
    -webkit-backdrop-filter: blur(18px) saturate(160%) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 20px !important;
    box-shadow: inset 0 1px 0 var(--glass-highlight), 0 8px 24px rgba(0, 0, 0, 0.28) !important;
    padding: 16px 18px !important;
    margin-bottom: 16px !important;
    overflow: hidden !important;
    transition: transform 280ms cubic-bezier(0.22, 1, 0.36, 1),
                box-shadow 280ms cubic-bezier(0.22, 1, 0.36, 1) !important;
}}

/* Specular highlight streak — diagonal light-catch */
[data-testid="stSidebarContent"] [data-testid="stVerticalBlockBorderWrapper"]::before,
[data-testid="stSidebarUserContent"] [data-testid="stVerticalBlockBorderWrapper"]::before {{
    content: "";
    position: absolute;
    top: -50%;
    left: -20%;
    width: 60%;
    height: 200%;
    background: linear-gradient(
        115deg,
        {glass_glow_start} 0%,
        {glass_glow_mid} 35%,
        transparent 55%
    );
    transform: rotate(8deg);
    pointer-events: none;
}}

/* Hover lift on sidebar cards */
[data-testid="stSidebarContent"] [data-testid="stVerticalBlockBorderWrapper"]:hover,
[data-testid="stSidebarUserContent"] [data-testid="stVerticalBlockBorderWrapper"]:hover {{
    transform: translateY(-2px) !important;
    box-shadow: inset 0 1px 0 var(--glass-highlight), 0 12px 32px rgba(0, 0, 0, 0.34) !important;
}}

/* Sidebar Expander Glass Look */
[data-testid="stSidebarContent"] [data-testid="stExpander"],
[data-testid="stSidebarUserContent"] [data-testid="stExpander"] {{
    background: var(--glass-bg-inner) !important;
    backdrop-filter: blur(18px) saturate(160%) !important;
    -webkit-backdrop-filter: blur(18px) saturate(160%) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 20px !important;
    box-shadow: inset 0 1px 0 var(--glass-highlight), 0 8px 24px rgba(0, 0, 0, 0.28) !important;
    margin-bottom: 16px !important;
    overflow: hidden !important;
}}
[data-testid="stSidebarContent"] [data-testid="stExpander"] details,
[data-testid="stSidebarContent"] [data-testid="stExpander"] summary,
[data-testid="stSidebarContent"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
    background: transparent !important;
}}

/* 3.3 — Glass Input Controls */
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-testid="stNumberInput"] > div > div {{
    background: {glass_input_bg} !important;
    border: 1px solid {glass_input_border} !important;
    border-radius: 12px !important;
    color: var(--text-primary) !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}}
[data-testid="stSidebar"] [data-testid="stNumberInput"] input,
[data-testid="stSidebar"] [data-testid="stNumberInput"] button,
[data-testid="stSidebar"] [data-testid="stNumberInput"] [data-baseweb="button"] {{
    background: transparent !important;
    color: var(--text-primary) !important;
}}
[data-testid="stSidebar"] [data-baseweb="select"] > div:focus-within {{
    border-color: var(--accent-primary) !important;
    box-shadow: 0 0 0 3px rgba(110, 86, 207, 0.2) !important;
}}

/* Sliders */
[data-testid="stSidebar"] [data-baseweb="slider"] [role="slider"]:hover {{
    transform: scale(1.1) !important;
    border: 2px solid {slider_knob} !important;
    box-shadow: 0 0 0 5px rgba(110, 86, 207, 0.18), 0 2px 6px rgba(0,0,0,0.3) !important;
}}
[data-testid="stSidebar"] [data-baseweb="slider"] [role="slider"] {{
    background-color: var(--accent-primary) !important;
    box-shadow: 0 0 0 5px rgba(110, 86, 207, 0.18), 0 2px 6px rgba(0,0,0,0.3) !important;
    border: 2px solid rgba(255,255,255,0.4) !important;
}}
[data-testid="stSidebar"] [data-baseweb="slider"] > div > div:nth-child(2) {{
    background: var(--accent-primary) !important;
}}

/* 3.4 — Dropdown Popover Fix.
   When a selectbox opens, the option list is portaled to <body> —
   it is NOT nested inside the sidebar DOM. This unscoped rule catches it. */
[data-baseweb="popover"] [role="listbox"] {{
    background: var(--glass-bg-inner) !important;
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid var(--glass-border) !important;
    border-radius: 14px !important;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4);
}}
[data-baseweb="popover"] [role="option"]:hover {{
    background: rgba(110, 86, 207, 0.16) !important;
}}

/* 3.5 — Dark mode toggle pinned to bottom */
.sidebar-bottom-anchor {{
    position: sticky;
    bottom: 0;
    margin-top: auto;
    z-index: 5;
}}
[data-testid="stSidebar"] [data-testid="stToggle"] label div:first-child {{
    background: var(--accent-primary) !important;
}}

/* 3.6 — Mobile / narrow-viewport fallback.
   Below ~640px Streamlit switches the sidebar from a persistent column
   to a full-screen overlay drawer — relax the floating treatment. */
@media (max-width: 640px) {{
    [data-testid="stSidebarContent"],
    [data-testid="stSidebarUserContent"] {{
        border-radius: 0 !important;
        margin: 0 !important;
        height: 100vh;
        min-height: 100vh;
    }}
    [data-testid="stSidebar"] {{
        padding: 0 !important;
    }}
}}

/* ═══ Buttons ═══ */
.stButton > button {{
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    transition: all 280ms cubic-bezier(0.22, 1, 0.36, 1) !important;
    padding: 0.6rem 1.4rem !important;
}}
.btn-gold button {{
    background: var(--accent-secondary) !important;
    color: #FFFFFF !important;
    border: none !important;
}}
.btn-gold button:hover {{
    background: #B87A1F !important;
    transform: translateY(-1px) !important;
}}

/* ═══ Text Area ═══ */
.stTextArea textarea {{
    background-color: var(--bg-surface-elevated) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-default) !important;
    font-family: 'IBM Plex Mono', monospace !important;
    border-radius: 8px !important;
    font-size: 0.85rem !important;
}}

/* ═══ Export Buttons ═══ */
.ds-export-btn {{
    display: inline-block;
    padding: 0.6rem 1.2rem;
    color: #FFFFFF;
    text-decoration: none;
    border-radius: 10px;
    font-weight: 600;
    font-size: 0.9rem;
    font-family: 'Inter', sans-serif;
    text-align: center;
    width: 100%;
    transition: opacity 280ms cubic-bezier(0.22, 1, 0.36, 1), transform 280ms cubic-bezier(0.22, 1, 0.36, 1);
}}
.ds-export-btn:hover {{
    opacity: 0.88;
    transform: translateY(-1px);
}}
.ds-export-btn.gold {{ background: var(--accent-secondary); }}
.ds-export-btn.indigo {{ background: var(--accent-primary); }}

/* ═══ Skeleton Loading Shimmer ═══ */
.ds-skeleton {{
    border-radius: 12px;
    height: 100%;
    min-height: 220px;
    background: linear-gradient(110deg, var(--bg-surface) 30%, var(--bg-surface-hover) 50%, var(--bg-surface) 70%);
    background-size: 200% 100%;
    animation: ds-shimmer 1.6s ease-in-out infinite;
}}
@keyframes ds-shimmer {{ to {{ background-position: -200% 0; }} }}

/* ═══ Phase 4: Accessibility ═══ */
:focus-visible {{
    outline: 2px solid var(--accent-primary);
    outline-offset: 2px;
}}

/* ═══ Animated KPI Counter ═══ */
@property --kpi-num {{
    syntax: '<integer>';
    initial-value: 0;
    inherits: false;
}}
.ds-kpi-value[data-animate] {{
    animation: ds-count-up 800ms cubic-bezier(0.22, 1, 0.36, 1) forwards;
    counter-reset: kpi var(--kpi-num);
}}
@keyframes ds-count-up {{
    from {{ --kpi-num: 0; opacity: 0.3; transform: translateY(6px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}

/* ═══ Last Updated Footer ═══ */
.ds-last-updated {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    color: var(--text-tertiary);
    text-align: center;
    padding: 8px 0 4px;
    letter-spacing: 0.02em;
}}

/* ═══ SKU Info Strip ═══ */
.ds-sku-info-strip {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 6px 0 12px;
}}
.ds-sku-info-strip .ds-info-tag {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 10px;
    border-radius: 999px;
    font-family: 'Inter', sans-serif;
    font-size: 0.68rem;
    font-weight: 500;
    background: var(--accent-primary-soft);
    color: var(--text-secondary);
    border: 1px solid rgba(110, 86, 207, 0.1);
}}

/* ═══ Preset Scenario Buttons ═══ */
.ds-preset-row {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 16px;
}}
.ds-preset-btn {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 6px 14px;
    border-radius: 999px;
    font-family: 'Inter', sans-serif;
    font-size: 0.76rem;
    font-weight: 600;
    background: var(--bg-surface-elevated);
    color: var(--text-secondary);
    border: 1px solid var(--border-subtle);
    cursor: pointer;
    transition: all 200ms cubic-bezier(0.22, 1, 0.36, 1);
}}
.ds-preset-btn:hover {{
    background: var(--accent-primary-soft);
    color: var(--accent-primary);
    border-color: var(--accent-primary);
    transform: translateY(-1px);
}}

/* ═══ Alert Banner (Tab 5) ═══ */
.ds-alert-banner {{
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 16px 24px;
    border-radius: 16px;
    margin-bottom: 24px;
    backdrop-filter: blur(12px) saturate(160%);
    -webkit-backdrop-filter: blur(12px) saturate(160%);
    transition: all 280ms cubic-bezier(0.22, 1, 0.36, 1);
}}
.ds-alert-banner.critical {{
    background: linear-gradient(135deg, rgba(239,68,68,0.10), rgba(239,68,68,0.04));
    border: 1px solid rgba(239,68,68,0.25);
}}
.ds-alert-banner.warning {{
    background: linear-gradient(135deg, rgba(245,166,35,0.10), rgba(245,166,35,0.04));
    border: 1px solid rgba(245,166,35,0.25);
}}
.ds-alert-banner.healthy {{
    background: linear-gradient(135deg, rgba(34,197,94,0.10), rgba(34,197,94,0.04));
    border: 1px solid rgba(34,197,94,0.25);
}}
.ds-alert-banner .ds-alert-icon {{
    font-size: 1.6rem;
    flex-shrink: 0;
}}
.ds-alert-banner .ds-alert-text {{
    flex: 1;
}}
.ds-alert-banner .ds-alert-title {{
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-weight: 700;
    font-size: 0.95rem;
    margin-bottom: 2px;
}}
.ds-alert-banner .ds-alert-sub {{
    font-family: 'Inter', sans-serif;
    font-size: 0.8rem;
    color: var(--text-secondary);
}}

/* ═══ PO Preview Card ═══ */
.ds-po-preview {{
    background: var(--bg-surface-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 16px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.82rem;
}}
.ds-po-preview .ds-po-row {{
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid var(--border-subtle);
}}
.ds-po-preview .ds-po-row:last-child {{
    border-bottom: none;
}}
.ds-po-preview .ds-po-label {{
    color: var(--text-tertiary);
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
    font-weight: 500;
}}
.ds-po-preview .ds-po-val {{
    color: var(--text-primary);
    font-weight: 600;
}}

/* ═══ AI Structured Bullets ═══ */
.ds-ai-bullets {{
    list-style: none;
    padding: 0;
    margin: 8px 0 0;
}}
.ds-ai-bullets li {{
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 6px 0;
    font-size: 0.88rem;
    line-height: 1.55;
    color: var(--text-primary);
    font-family: 'Inter', sans-serif;
}}
.ds-ai-bullets li .ds-bullet-icon {{
    flex-shrink: 0;
    margin-top: 2px;
}}

/* ═══ Data Freshness Badge ═══ */
.ds-data-freshness {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: var(--text-tertiary);
    padding: 6px 10px;
    border-radius: 8px;
    background: var(--bg-surface-elevated);
    border: 1px solid var(--border-subtle);
    margin: 8px 0 12px;
    line-height: 1.5;
}}

/* ═══ Phase 5: Power BI-style Chart Interaction Controls ═══ */

/* 5.1 — Segmented Control (Time Range Pill Capsule) */
div[data-testid="stSegmentedControl"] {{
    margin-bottom: 4px;
}}
div[data-testid="stSegmentedControl"] > div {{
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 999px !important;
    padding: 3px !important;
    gap: 2px !important;
}}
div[data-testid="stSegmentedControl"] button {{
    border-radius: 999px !important;
    padding: 3px 13px !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    letter-spacing: 0.02em !important;
    color: var(--text-tertiary) !important;
    border: none !important;
    background: transparent !important;
    transition: background 200ms ease, color 200ms ease !important;
    min-height: auto !important;
    height: auto !important;
    line-height: 1.4 !important;
}}
div[data-testid="stSegmentedControl"] button:hover {{
    color: var(--text-primary) !important;
    background: var(--bg-surface-hover) !important;
}}
div[data-testid="stSegmentedControl"] button[aria-pressed="true"],
div[data-testid="stSegmentedControl"] button[aria-checked="true"] {{
    background: var(--accent-primary) !important;
    color: #FFFFFF !important;
}}

/* 5.2 — Clear Filter Chip (cross-filter dismiss badge) */
.ds-clear-filter {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 14px;
    border-radius: 999px;
    font-family: 'Inter', sans-serif;
    font-size: 0.76rem;
    font-weight: 600;
    background: var(--accent-primary-soft);
    color: var(--accent-primary);
    border: 1px solid rgba(110, 86, 207, 0.2);
    cursor: pointer;
    transition: background 200ms ease, transform 200ms ease;
    margin-bottom: 12px;
}}
.ds-clear-filter:hover {{
    background: rgba(110, 86, 207, 0.22);
    transform: translateY(-1px);
}}

/* 5.3 — Focus Mode Expand Button (chart card header) */
button[title="Focus mode"] {{
    background: transparent !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 8px !important;
    padding: 4px 8px !important;
    font-size: 14px !important;
    color: var(--text-tertiary) !important;
    min-height: auto !important;
    height: auto !important;
    line-height: 1 !important;
    transition: all 200ms ease !important;
}}
button[title="Focus mode"]:hover {{
    border-color: var(--accent-primary) !important;
    color: var(--accent-primary) !important;
    background: var(--accent-primary-soft) !important;
}}

/* 5.4 — Chart Card Export Row */
.ds-chart-actions {{
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 8px;
    margin-top: 4px;
    padding-top: 8px;
    border-top: 1px solid var(--border-subtle);
}}

</style>
""", unsafe_allow_html=True)


inject_css(st.session_state.theme)



# ═══════════════════════════════════════════════════════════════
# PLOTLY MASTER TEMPLATE
# ═══════════════════════════════════════════════════════════════
def get_plotly_template(theme="dark"):
    dark = theme == "dark"
    tokens = DARK_TOKENS if dark else LIGHT_TOKENS
    return go.layout.Template(
        layout=go.Layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", size=12, color=tokens["text_secondary"]),
            title_font=dict(family="Plus Jakarta Sans, sans-serif", size=14, color=tokens["text_primary"]),
            xaxis=dict(
                gridcolor=tokens["border_subtle"],
                zerolinecolor=tokens["border_default"],
                linecolor=tokens["border_default"],
                tickfont=dict(color=tokens["text_tertiary"], size=11),
            ),
            yaxis=dict(
                gridcolor=tokens["border_subtle"],
                zerolinecolor=tokens["border_default"],
                linecolor=tokens["border_default"],
                tickfont=dict(color=tokens["text_tertiary"], size=11),
            ),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                bgcolor="rgba(0,0,0,0)", font=dict(size=11, color=tokens["text_secondary"]),
            ),
            hoverlabel=dict(
                bgcolor="rgba(26,32,51,0.92)" if dark else "rgba(255,255,255,0.95)",
                bordercolor="#6E56CF",
                font=dict(family="Inter, sans-serif", size=12, color=tokens["text_primary"]),
                align="left",
            ),
            dragmode=False,
            hovermode="x unified",
            margin=dict(l=10, r=10, t=30, b=10),
            colorway=["#6E56CF", "#C98A2E", "#22C3B6", "#F5A623", "#EF4444"],
        )
    )


# ═══════════════════════════════════════════════════════════════
# PLOTLY LOCKED-DOWN CONFIG & CHART RENDERING
# ═══════════════════════════════════════════════════════════════
PLOTLY_CONFIG = {
    "displayModeBar": False,
    "scrollZoom": False,
    "doubleClick": False,
}

def show_chart(fig, container=st, key=None, on_select=None, selection_mode=None):
    """Render a Plotly figure with locked-down navigation and optional cross-filter support."""
    kwargs = {"use_container_width": True, "config": PLOTLY_CONFIG, "theme": None}
    if key:
        kwargs["key"] = key
    if on_select:
        kwargs["on_select"] = on_select
    if selection_mode:
        kwargs["selection_mode"] = selection_mode
    return container.plotly_chart(fig, **kwargs)


# ═══════════════════════════════════════════════════════════════
# CHART INTERACTION UTILITIES (Power BI-style)
# ═══════════════════════════════════════════════════════════════
def filter_by_range(df, range_choice):
    """Filter a date-containing DataFrame to the selected time range."""
    if range_choice == "All" or range_choice is None:
        return df
    days_map = {"7D": 7, "30D": 30, "90D": 90, "1Y": 365}
    n_days = days_map.get(range_choice, len(df))
    return df.tail(n_days)


def render_chart_export_link(fig, filename, chart_height=600):
    """Render a Base64 PNG export as a glass-styled <a> tag (NOT st.download_button — IDM safe)."""
    try:
        png_bytes = fig.to_image(format="png", scale=2, width=1200, height=chart_height)
        b64 = base64.b64encode(png_bytes).decode("utf-8")
        href = f'<a href="data:image/png;base64,{b64}" download="{filename}" class="ds-export-btn indigo" style="font-size:0.78rem; padding:0.35rem 0.9rem; display:inline-block; margin-top:8px;">📥 Export PNG</a>'
        st.markdown(href, unsafe_allow_html=True)
    except Exception as e:
        st.caption(f"⚠ PNG export unavailable: {e}")


def get_festival_date_mask(df, festival_display_name):
    """Return a boolean mask of rows in df whose dates fall within a festival's ramp-up/post window."""
    for _key, info in INDIAN_FESTIVALS.items():
        if info["name"] == festival_display_name:
            mask = pd.Series(False, index=df.index)
            for d in info["dates"]:
                start = pd.Timestamp(d) - pd.Timedelta(days=info["ramp_up_days"])
                end = pd.Timestamp(d) + pd.Timedelta(days=info.get("post_days", 3))
                mask |= (df["date"] >= start) & (df["date"] <= end)
            return mask
    return None

# ═══════════════════════════════════════════════════════════════
# DATA LOADING & CACHING PIPELINE
# ═══════════════════════════════════════════════════════════════
@st.cache_data
def load_data():
    raw_path = os.path.join(PROJECT_ROOT, "data", "raw", "indian_fmcg_sales.csv")
    feat_path = os.path.join(PROJECT_ROOT, "data", "processed", "featured_sales.csv")

    if os.path.exists(feat_path):
        df = pd.read_csv(feat_path)
    elif os.path.exists(raw_path):
        df = pd.read_csv(raw_path)
    else:
        from src.data_generator import IndianFMCGDataGenerator
        generator = IndianFMCGDataGenerator()
        df = generator.generate()

    df["date"] = pd.to_datetime(df["date"])
    return df


df_sales = load_data()


# ═══════════════════════════════════════════════════════════════
# SIDEBAR NAVIGATION & CONTROLS
# ═══════════════════════════════════════════════════════════════
def sidebar_section(icon, title):
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:6px; margin:4px 0 8px;">
        <span style="font-size:13px;">{icon}</span>
        <span class="ds-caption" style="margin-bottom:0; font-family: 'Inter', sans-serif; font-size: 0.74rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; color: var(--text-secondary);">{title}</span>
    </div>""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:10px; padding-bottom:16px;">
        <div class="ds-icon-chip indigo" style="margin-bottom:0; width:32px; height:32px; border-radius:8px; font-size:14px; display:flex; align-items:center; justify-content:center; background:var(--accent-primary-soft); color:var(--accent-primary);">📈</div>
        <div>
            <div style="font-family:'Plus Jakarta Sans'; font-weight:700; font-size:17px; color:var(--text-primary); line-height:1.1;">DemandSense AI</div>
            <div style="font-size:11px; color:var(--text-tertiary);">FMCG Demand & Supply Control Tower</div>
        </div>
    </div>
    <hr>
    """, unsafe_allow_html=True)

    sidebar_section("🎯", "Product & Market Scope")
    sku_options = {p.get("sku_id", ""): f"{extract_name(p)} ({p.get('category', '')})" for p in PRODUCTS}
    selected_sku_id = st.selectbox(
        "Product SKU",
        options=list(sku_options.keys()),
        format_func=lambda x: sku_options[x],
        key="sb_sku"
    )

    region_options = {"ALL": "National Aggregation (India)"}
    region_options.update({r.get("id", r.get("region_id", "")): extract_name(r) for r in REGIONS})
    selected_region = st.selectbox(
        "Geographic Region",
        options=list(region_options.keys()),
        format_func=lambda x: region_options[x],
        key="sb_reg"
    )

    # G1: SKU Quick-Info Strip
    _sku_quick = next((p for p in PRODUCTS if p.get("sku_id") == selected_sku_id), PRODUCTS[0])
    _sku_cat = _sku_quick.get("category", "FMCG")
    _sku_price = _sku_quick.get("base_price", 100)
    _sku_region_label = region_options.get(selected_region, "National")
    st.markdown(f"""<div class="ds-sku-info-strip">
<span class="ds-info-tag">📦 {_sku_cat}</span>
<span class="ds-info-tag">💰 ₹{_sku_price:,.0f}</span>
<span class="ds-info-tag">📍 {_sku_region_label.split('(')[0].strip()}</span>
</div>""", unsafe_allow_html=True)

    sidebar_section("🚚", "Supply Chain Constraints")
    lead_time = st.slider("Supplier Lead Time (Days)", 1, 30, DEFAULT_LEAD_TIME_DAYS, key="sb_lt")
    abc_class_label = st.select_slider(
        "Service Level Target",
        options=["C (90%)", "B (95%)", "A (98%)"], value="A (98%)", key="sb_sl"
    )
    abc_class = abc_class_label[0]  # Extract "A", "B", or "C" from "A (98%)" etc.
    current_stock = st.number_input("Warehouse Current Stock (Units)", min_value=0, value=25000, step=1000, key="sb_stock")

    st.divider()
    with st.expander("Upload Enterprise Sales CSV"):
        uploaded_file = st.file_uploader("Upload custom CSV", type=["csv"])
        if uploaded_file is not None:
            try:
                user_df = pd.read_csv(uploaded_file)
                user_df["date"] = pd.to_datetime(user_df["date"])
                df_sales = user_df
                st.success("Custom sales CSV loaded successfully!")
            except Exception as e:
                st.error(f"Invalid CSV structure: {e}")

    # G2: Data Freshness Indicator
    _df_min = df_sales["date"].min().strftime("%b %d, %Y")
    _df_max = df_sales["date"].max().strftime("%b %d, %Y")
    _df_days = (df_sales["date"].max() - df_sales["date"].min()).days
    _df_skus = df_sales["sku_id"].nunique()
    st.markdown(f'<div class="ds-data-freshness">📅 {_df_min} → {_df_max}<br>{_df_days:,} days · {_df_skus} SKUs</div>', unsafe_allow_html=True)

    # Pinned Dark Mode Toggle at the bottom of the sidebar
    st.markdown('<div class="sidebar-bottom-anchor">', unsafe_allow_html=True)
    with st.container(border=True):
        col_a, col_b = st.columns([3, 1])
        with col_a:
            st.markdown('<span style="font-size:13px; color:var(--text-secondary); line-height: 2;">🌙 Dark Mode</span>', unsafe_allow_html=True)
        with col_b:
            st.toggle("Dark Mode", value=(st.session_state.theme == "dark"), label_visibility="collapsed", key="theme_toggle", on_change=toggle_theme)
    st.markdown('</div>', unsafe_allow_html=True)

    st.caption(f"Production Engine v{VERSION} • FMCG Ops Analytics")


# ═══════════════════════════════════════════════════════════════
# CACHED DATA PIPELINE & PERFORMANCE ENGINE
# ═══════════════════════════════════════════════════════════════
sku_info = next((p for p in PRODUCTS if p.get("sku_id") == selected_sku_id), PRODUCTS[0])

exclude_cols = {"sku_id", "sku_name", "category", "region_id", "region_name", "unit_price_inr", "revenue_inr", "date"}
feature_cols = [c for c in df_sales.columns if c not in exclude_cols]

filtered_df = get_filtered_timeseries(df_sales, selected_sku_id, selected_region, feature_cols)

chart_history = filtered_df.tail(365).copy()


@st.cache_data(show_spinner="Evaluating Auto-ML Models...")
def get_forecast_and_impact(_timeseries_df, sku_id, lead_t, service_c, stock_val):
    s_data = _timeseries_df

    selector = ModelAutoSelector(test_days=60, metric="mape")
    res = selector.evaluate_and_select(s_data)

    calc = OperationsImpactCalculator(lead_time_days=lead_t)
    p_info = next((p for p in PRODUCTS if p.get("sku_id") == sku_id), PRODUCTS[0])
    impact = calc.calculate_sku_impact(
        product_info=p_info,
        historical_df=s_data,
        forecast_df=res["winning_forecast"],
        current_stock=stock_val,
        abc_class=service_c
    )

    agent = LLMPrescriptiveAgent()
    llm_report = agent.generate_prescriptive_report(
        impact, res["winning_model_name"], res["winning_metrics"]["mape"]
    )

    return res, impact, llm_report


forecast_res, impact_data, llm_report = get_forecast_and_impact(
    filtered_df, selected_sku_id, lead_time, abc_class, current_stock
)

winning_model_name = forecast_res["winning_model_name"]
winning_metrics = forecast_res["winning_metrics"]
forecast_df = forecast_res["winning_forecast"]
leaderboard_df = forecast_res["leaderboard"]


@st.cache_data
def get_cached_abc_classification():
    calc_batch = OperationsImpactCalculator()
    return calc_batch.compute_abc_classification(df_sales)


@st.cache_data
def get_cached_regional_summary():
    geo_coords = {
        "North India (Delhi NCR)": {"lat": 28.6139, "lon": 77.2090},
        "West India (Mumbai)": {"lat": 19.0760, "lon": 72.8777},
        "South India (Chennai)": {"lat": 13.0827, "lon": 80.2707},
        "East India (Kolkata)": {"lat": 22.5726, "lon": 88.3639},
        "Central India (Nagpur)": {"lat": 21.1458, "lon": 79.0882}
    }
    reg_summary = (df_sales.groupby("region_name")
                   .agg(total_revenue=("revenue_inr", "sum"), total_units=("units_sold", "sum"))
                   .reset_index())
    reg_summary["lat"] = reg_summary["region_name"].map(lambda r: geo_coords.get(r, {}).get("lat", 20.5937))
    reg_summary["lon"] = reg_summary["region_name"].map(lambda r: geo_coords.get(r, {}).get("lon", 78.9629))
    return reg_summary


@st.cache_data
def get_cached_xgb_fi(_timeseries_df):
    s_data = _timeseries_df
    try:
        from src.forecasting.xgboost_model import XGBoostForecaster
        xgb_m = XGBoostForecaster()
        xgb_m.fit(s_data)
        fi = xgb_m.feature_importances().head(10).reset_index()
        fi.columns = ["feature", "importance"]
        return fi
    except Exception:
        return pd.DataFrame()


# ═══════════════════════════════════════════════════════════════
# COMPONENT BUILDERS (KPI CARD HTML & BADGES)
# ═══════════════════════════════════════════════════════════════
def render_kpi_card(chip_letter: str, chip_color: str, label: str, value_str: str,
                    delta_pct: float, metric_key: str, sparkline_values: list) -> str:
    is_good = is_delta_favorable(metric_key, delta_pct)
    badge_cls = "healthy" if is_good else "critical"
    arrow = "▲" if delta_pct >= 0 else "▼"
    
    spark_color = "#6E56CF" if chip_color == "indigo" else ("#C98A2E" if chip_color == "gold" else ("#EF4444" if chip_color == "red" else "#22C55E"))
    spark_svg = generate_svg_sparkline(sparkline_values, line_color=spark_color, fill_opacity=0.30, width=120, height=32)

    return f"""<div class="ds-card" style="margin-bottom: 0;">
<div class="ds-icon-chip {chip_color}">{chip_letter}</div>
<div class="ds-caption">{label}</div>
<div class="ds-kpi-value" data-animate>{value_str}</div>
<div style="display: flex; justify-content: space-between; align-items: flex-end;">
<span class="ds-badge {badge_cls}" style="margin-bottom: 4px;">{arrow} {abs(delta_pct):.1f}%</span>
<div style="margin-right: -12px; margin-bottom: -12px;">{spark_svg}</div>
</div>
</div>"""


# ═══════════════════════════════════════════════════════════════
# STICKY TOP COMMAND BAR — 4 KPI CARDS
# ═══════════════════════════════════════════════════════════════
total_fcst_units = impact_data.get("total_30d_forecast_units", impact_data.get("total_forecast_units_30d", 0))
unit_price = sku_info.get("base_price", 100)
total_fcst_rev = total_fcst_units * unit_price
rev_str = f"₹{total_fcst_rev / 1e7:.2f} Cr" if total_fcst_rev >= 1e7 else f"₹{total_fcst_rev / 1e5:.1f} Lakh"

days_supply = impact_data.get("days_of_supply", 30.0)
stock_coverage = min(1.0, days_supply / 30.0)
rev_at_risk = impact_data.get("revenue_at_risk_inr", 0.0)
risk_str = f"₹{rev_at_risk / 1e5:.1f} L" if rev_at_risk < 1e7 else f"₹{rev_at_risk / 1e7:.2f} Cr"

hist_recent_units = chart_history["units_sold"].tail(30).values
hist_recent_rev = (chart_history["units_sold"] * unit_price).tail(30).values

# Real period-over-period KPI delta calculations (last 30d vs prior 30d)
_hist_last30 = chart_history["units_sold"].tail(30)
_hist_prev30 = chart_history["units_sold"].iloc[-60:-30] if len(chart_history) >= 60 else chart_history["units_sold"].head(30)
_delta_fcst_pct = round((_hist_last30.sum() - _hist_prev30.sum()) / max(1, _hist_prev30.sum()) * 100, 1)
_delta_rev_pct = _delta_fcst_pct  # Revenue delta mirrors volume delta for same-price SKU
_prev_coverage = min(100.0, (current_stock / max(1, _hist_prev30.mean())) / 30.0 * 100)
_delta_compliance = round(stock_coverage * 100 - _prev_coverage, 1)
_prev_risk = max(0, _hist_prev30.sum() * unit_price - current_stock * unit_price) * 0.15  # Simplified prior-period risk estimate
_delta_risk_pct = round((rev_at_risk - _prev_risk) / max(1, _prev_risk) * 100, 1) if _prev_risk > 0 else 0.0

kpi_html = f"""<div class="command-bar" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; margin-bottom: 24px;">
{render_kpi_card("FC", "indigo", "30-DAY DEMAND FORECAST", f"{total_fcst_units:,.0f}", _delta_fcst_pct, "forecast_units", hist_recent_units)}
{render_kpi_card("₹", "gold", "PROJECTED REVENUE (30D)", rev_str, _delta_rev_pct, "revenue", hist_recent_rev)}
{render_kpi_card("SS", "green" if stock_coverage >= 0.8 else "red", "SAFETY STOCK COMPLIANCE", f"{stock_coverage * 100:.0f}%", _delta_compliance, "compliance", [95, 98, 96, 92, 94, 98, stock_coverage * 100])}
{render_kpi_card("Risk", "red", "REVENUE AT RISK", risk_str, _delta_risk_pct, "revenue_at_risk", [1.2, 1.4, 1.1, 1.8, 2.1, 1.9, rev_at_risk / 1e5])}
</div>"""
st.markdown(kpi_html, unsafe_allow_html=True)

# Last Updated Timestamp Footer
_data_start = df_sales["date"].min().strftime("%b %Y")
_data_end = df_sales["date"].max().strftime("%b %d, %Y")
_now_str = pd.Timestamp.now().strftime("%b %d, %Y %H:%M IST")
st.markdown(f'<div class="ds-last-updated">Forecast generated: {_now_str} · Model: {winning_model_name} · Data window: {_data_start} – {_data_end}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# TABS NAVIGATION
# ═══════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Demand Intelligence",
    "Auto-ML Model Arena",
    "Inventory Control Tower",
    "What-If Simulator",
    "AI Prescriptive Control Room"
])

current_template = get_plotly_template(st.session_state.theme)


# ───────────────────────────────────────────────────────────────
# TAB 1: DEMAND INTELLIGENCE & INDIAN SEASONALITY
# ───────────────────────────────────────────────────────────────
with tab1:
    st.markdown("### **Demand Intelligence & Indian Seasonality**")

    # A2: Dynamic contextual subtitle
    _fest_df_tab1 = get_festival_impact_summary(selected_sku_id)
    if not _fest_df_tab1.empty:
        _top_fest = _fest_df_tab1.iloc[0]
        if _top_fest["change_pct"] > 15:
            _tab1_subtitle = f"🎯 {_top_fest['festival']} surge detected — +{_top_fest['change_pct']:.0f}% above baseline for this SKU."
        elif _top_fest["change_pct"] > 0:
            _tab1_subtitle = f"📊 Moderate {_top_fest['festival']} seasonality (+{_top_fest['change_pct']:.0f}%) · 95% confidence bands active."
        else:
            _tab1_subtitle = "📊 Forecast stable — no significant festival uplift in current window."
    else:
        _tab1_subtitle = "Historical demand vs. 30-day AI ensemble forecast, 95% confidence bands, and Indian festival multipliers."
    st.caption(_tab1_subtitle)

    # ── Cross-filter state management ──
    active_filter = st.session_state.get("active_filter", None)

    # Clear filter chip (only shown when a cross-filter is active)
    if active_filter:
        if st.button(f"✕  Clear filter: {active_filter}", key="clear_filter_tab1"):
            st.session_state.pop("active_filter", None)
            st.session_state.pop("_last_festival_selection", None)
            st.rerun()

    # ── Hero Chart: Demand Trajectory & 95% Confidence Interval ──
    with st.container(border=True):
        # Card header row: title + time range control + focus button
        col_title, col_range, col_expand = st.columns([4, 5, 1])
        with col_title:
            st.markdown('<div class="ds-caption">Historical vs. 30-Day AI Forecast</div>', unsafe_allow_html=True)
        with col_range:
            range_choice = st.segmented_control(
                "Time Range", options=["7D", "30D", "90D", "1Y", "All"],
                default="All", key="range_hero", label_visibility="collapsed",
            )
        with col_expand:
            expand_hero = st.button("⤢", key="expand_hero", help="Focus mode")

        st.markdown("#### **Demand Trajectory & 95% Confidence Interval**")

        # Apply time-range filter before plotting
        display_history = filter_by_range(chart_history, range_choice)
        display_history = display_history.copy()
        display_history["rolling_7d"] = display_history["units_sold"].rolling(7, min_periods=1).mean()

        fig_hero = go.Figure()

        # 1. Raw Historical Demand (Soft Fill)
        fig_hero.add_trace(go.Scatter(
            x=display_history["date"],
            y=display_history["units_sold"],
            mode="lines",
            name="Raw Daily Demand",
            fill="tozeroy",
            fillcolor="rgba(154,163,184,0.05)",
            line=dict(color="rgba(154,163,184,0.40)", width=1),
            hovertemplate="<b>%{x|%b %d, %Y}</b><br>Raw Demand: %{y:,.0f} units<extra></extra>",
        ))

        # 2. Smooth 7-Day Rolling Trend
        fig_hero.add_trace(go.Scatter(
            x=display_history["date"],
            y=display_history["rolling_7d"],
            mode="lines",
            name="7-Day Rolling Trend",
            line=dict(color="#EDEFF3" if is_dark else "#14161F", width=2.5, shape="spline"),
            hovertemplate="<b>%{x|%b %d, %Y}</b><br>7D Trend: %{y:,.0f} units<extra></extra>",
        ))

        # 3. 95% Confidence Band Bounds
        fig_hero.add_trace(go.Scatter(
            x=forecast_df["date"],
            y=forecast_df["upper_bound"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip"
        ))
        fig_hero.add_trace(go.Scatter(
            x=forecast_df["date"],
            y=forecast_df["lower_bound"],
            mode="lines",
            fill="tonexty",
            fillcolor="rgba(110,86,207,0.16)",
            line=dict(width=0),
            name="95% Confidence Band"
        ))

        # 4. 30-Day Forecast Line (Intelligence Indigo) — with gradient fill
        fig_hero.add_trace(go.Scatter(
            x=forecast_df["date"],
            y=forecast_df["predicted_units"],
            mode="lines+markers",
            name=f"30-Day Forecast ({winning_model_name})",
            fill="tozeroy",
            fillcolor="rgba(110,86,207,0.08)",
            line=dict(color="#6E56CF", width=3, shape="spline"),
            marker=dict(size=5, color="#6E56CF"),
            hovertemplate="<b>%{x|%b %d, %Y}</b><br>Forecast: %{y:,.0f} units<extra></extra>",
        ))

        # 5. Forecast Start (Today) Vertical Line
        forecast_start_str = pd.to_datetime(forecast_df["date"].iloc[0]).strftime("%Y-%m-%d")
        fig_hero.add_shape(
            type="line",
            x0=forecast_start_str,
            x1=forecast_start_str,
            y0=0,
            y1=1,
            yref="paper",
            line=dict(color="#666F84", width=1.5, dash="dot")
        )
        fig_hero.add_annotation(
            x=forecast_start_str,
            y=1.0,
            yref="paper",
            text="Forecast Start (Today)",
            showarrow=False,
            xanchor="left",
            yanchor="bottom",
            font=dict(size=11, color="#9AA3B8")
        )

        # 6. ROP Line
        rop_val = impact_data.get("reorder_point_units", 0)
        fig_hero.add_hline(
            y=rop_val,
            line_dash="dash",
            line_color="#EF4444",
            line_width=1.5,
            annotation_text=f"Reorder Point (ROP: {rop_val:,} units)",
            annotation_position="bottom right"
        )

        # 7. Safety Stock Line
        ss_val = impact_data.get("safety_stock_units", 0)
        fig_hero.add_hline(
            y=ss_val,
            line_dash="dot",
            line_color="#F5A623",
            line_width=1.5,
            annotation_text=f"Safety Stock ({ss_val:,} units)",
            annotation_position="bottom left"
        )

        # ── Cross-filter highlighting: dim non-matching periods ──
        if active_filter:
            festival_mask = get_festival_date_mask(display_history, active_filter)
            if festival_mask is not None and festival_mask.any():
                # Add a highlighted overlay trace for the festival period
                fest_dates = display_history[festival_mask]
                fig_hero.add_trace(go.Scatter(
                    x=fest_dates["date"],
                    y=fest_dates["units_sold"],
                    mode="lines+markers",
                    name=f"📍 {active_filter} Period",
                    line=dict(color="#E8B04B", width=3),
                    marker=dict(size=7, color="#E8B04B", symbol="diamond"),
                    hovertemplate=f"<b>%{{x|%b %d, %Y}}</b><br>{active_filter} Period<br>Demand: %{{y:,.0f}} units<extra></extra>",
                ))
                # Dim the raw demand trace
                fig_hero.update_traces(
                    selector=dict(name="Raw Daily Demand"),
                    line=dict(color="rgba(154,163,184,0.15)"),
                    fillcolor="rgba(154,163,184,0.02)",
                )
                fig_hero.update_traces(
                    selector=dict(name="7-Day Rolling Trend"),
                    line=dict(color="rgba(237,239,243,0.25)" if is_dark else "rgba(20,22,31,0.25)"),
                )

        fig_hero.update_layout(template=current_template, height=430)
        show_chart(fig_hero, key="hero_chart_inline")

        # Chart actions row: export
        export_html = render_chart_export_link(fig_hero, "demand_forecast.png", chart_height=430)
        st.markdown(f'<div class="ds-chart-actions">{export_html}</div>', unsafe_allow_html=True)

    # Focus mode dialog for hero chart
    if expand_hero:
        @st.dialog("Demand Trajectory & 95% Confidence Interval", width="large")
        def _focus_hero():
            fig_focus = go.Figure(fig_hero)
            fig_focus.update_layout(height=560)
            show_chart(fig_focus, key="hero_focus_view")
            render_chart_export_link(fig_focus, "demand_forecast_focus.png", chart_height=560)
        _focus_hero()

    # ── 2-COLUMN GRID: Decomposition + Festival Cross-Filter ──
    col_decomp, col_fest = st.columns(2)

    with col_decomp:
        with st.container(border=True):
            col_dtitle, col_dexpand = st.columns([9, 1])
            with col_dtitle:
                st.markdown('<div class="ds-caption">Time-Series Breakdown</div>', unsafe_allow_html=True)
            with col_dexpand:
                expand_decomp = st.button("⤢", key="expand_decomp", help="Focus mode")

            st.markdown("#### **Additive Decomposition**")
            decomp_df = decompose_time_series(chart_history.tail(120), period=7)

            fig_decomp = make_subplots(
                rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                subplot_titles=("Growth Trend", "7-Day Weekly Seasonality", "Residual Noise")
            )
            # B4: Trend with gradient fill
            fig_decomp.add_trace(go.Scatter(
                x=decomp_df["date"], y=decomp_df["trend"],
                fill="tozeroy",
                fillcolor="rgba(110,86,207,0.08)",
                line=dict(color="#6E56CF", width=2.5, shape="spline"),
                hovertemplate="<b>%{x|%b %d}</b><br>Trend: %{y:,.0f}<extra></extra>",
            ), row=1, col=1)
            # B4: Seasonal with fill-to-zero (shows positive/negative split visually)
            fig_decomp.add_trace(go.Scatter(
                x=decomp_df["date"], y=decomp_df["seasonal"],
                fill="tozeroy",
                fillcolor="rgba(201,138,46,0.12)",
                line=dict(color="#C98A2E", width=2, shape="spline"),
                hovertemplate="<b>%{x|%b %d}</b><br>Seasonal: %{y:+,.0f}<extra></extra>",
            ), row=2, col=1)
            # Residual noise
            fig_decomp.add_trace(go.Scatter(
                x=decomp_df["date"], y=decomp_df["residual"],
                fill="tozeroy",
                fillcolor="rgba(154,163,184,0.06)",
                line=dict(color="#9AA3B8", width=1),
                hovertemplate="<b>%{x|%b %d}</b><br>Residual: %{y:+,.0f}<extra></extra>",
            ), row=3, col=1)

            # Add zero-line references on seasonal and residual panels
            for row_idx in [2, 3]:
                fig_decomp.add_hline(y=0, row=row_idx, col=1, line_dash="solid", line_color="rgba(154,163,184,0.25)", line_width=1)

            fig_decomp.update_layout(template=current_template, height=360, showlegend=False)
            show_chart(fig_decomp, key="decomp_chart")

            export_html = render_chart_export_link(fig_decomp, "decomposition.png", chart_height=360)
            st.markdown(f'<div class="ds-chart-actions">{export_html}</div>', unsafe_allow_html=True)

        # Focus mode for decomposition
        if expand_decomp:
            @st.dialog("Additive Time-Series Decomposition", width="large")
            def _focus_decomp():
                fig_fd = go.Figure(fig_decomp)
                fig_fd.update_layout(height=500)
                show_chart(fig_fd, key="decomp_focus_view")
                render_chart_export_link(fig_fd, "decomposition_focus.png", chart_height=500)
            _focus_decomp()

    with col_fest:
        with st.container(border=True):
            col_ftitle, col_fexpand = st.columns([9, 1])
            with col_ftitle:
                st.markdown('<div class="ds-caption">Indian Demand Signals — Click a bar to cross-filter ↑</div>', unsafe_allow_html=True)
            with col_fexpand:
                expand_fest = st.button("⤢", key="expand_fest", help="Focus mode")

            st.markdown("#### **Festival Multipliers vs. Baseline**")
            fest_df = get_festival_impact_summary(selected_sku_id)

            if not fest_df.empty:
                # B5: Lollipop Chart (thin stems + circle markers, cleaner than bars)
                fest_df_sorted = fest_df.sort_values("change_pct", ascending=True)
                dot_colors = ["#E8B04B" if f == "Diwali" else ("#C98A2E" if x > 0 else "#EF4444") for f, x in zip(fest_df_sorted["festival"], fest_df_sorted["change_pct"])]
                dot_sizes = [14 if f == "Diwali" else 10 for f in fest_df_sorted["festival"]]

                fig_fest = go.Figure()

                # Thin stems (bars with very low opacity for the stem line effect)
                fig_fest.add_trace(go.Bar(
                    y=fest_df_sorted["festival"],
                    x=fest_df_sorted["change_pct"],
                    orientation="h",
                    marker_color=[c.replace(")", ",0.35)").replace("rgb", "rgba").replace("#E8B04B", "rgba(232,176,75,0.35)").replace("#C98A2E", "rgba(201,138,46,0.35)").replace("#EF4444", "rgba(239,68,68,0.35)") if True else c for c in dot_colors],
                    marker_line_width=0,
                    width=0.12,
                    showlegend=False,
                    hoverinfo="skip",
                ))

                # Circle markers at the end of each stem
                fig_fest.add_trace(go.Scatter(
                    x=fest_df_sorted["change_pct"],
                    y=fest_df_sorted["festival"],
                    mode="markers+text",
                    text=[f"{x:+.1f}% ({m:.2f}×)" for x, m in zip(fest_df_sorted["change_pct"], fest_df_sorted["multiplier"])],
                    textposition="middle right",
                    textfont=dict(size=10, color=dot_colors),
                    marker=dict(
                        size=dot_sizes,
                        color=dot_colors,
                        line=dict(width=2, color=["rgba(232,176,75,0.4)" if f == "Diwali" else "rgba(0,0,0,0)" for f in fest_df_sorted["festival"]]),
                    ),
                    hovertemplate="<b>%{y}</b><br>Demand Change: %{x:+.1f}%<extra></extra>",
                ))

                max_x = max(5.0, fest_df_sorted["change_pct"].max() * 1.5)
                min_x = min(0.0, fest_df_sorted["change_pct"].min() * 1.2)

                fig_fest.update_layout(
                    template=current_template,
                    height=360,
                    xaxis=dict(range=[min_x, max_x], title="Demand Change (%)"),
                    margin=dict(l=10, r=25, t=20, b=40),
                    hovermode="closest",
                )

                # Baseline reference at x=0
                fig_fest.add_vline(x=0, line_dash="dash", line_color="rgba(154,163,184,0.35)", line_width=1.5)

                # Cross-filter: on_select triggers rerun and returns selection data
                fest_selection = show_chart(
                    fig_fest, key="festival_chart",
                    on_select="rerun", selection_mode=["points"],
                )

                # Process cross-filter selection
                if fest_selection and fest_selection.get("selection", {}).get("points"):
                    points = fest_selection["selection"]["points"]
                    clicked_festival = points[0].get("y", None) if points else None
                    last_processed = st.session_state.get("_last_festival_selection", None)
                    if clicked_festival and clicked_festival != last_processed:
                        st.session_state["_last_festival_selection"] = clicked_festival
                        st.session_state["active_filter"] = clicked_festival
                        st.rerun()

                export_html = render_chart_export_link(fig_fest, "festival_multipliers.png", chart_height=360)
                st.markdown(f'<div class="ds-chart-actions">{export_html}</div>', unsafe_allow_html=True)
            else:
                st.info("No festival multiplier data available for this SKU.")

        # Focus mode for festival chart
        if expand_fest and not fest_df.empty:
            @st.dialog("Festival Demand Multipliers vs. Baseline", width="large")
            def _focus_fest():
                fig_ff = go.Figure(fig_fest)
                fig_ff.update_layout(height=480)
                show_chart(fig_ff, key="fest_focus_view")
                render_chart_export_link(fig_ff, "festival_focus.png", chart_height=480)
            _focus_fest()


# ───────────────────────────────────────────────────────────────
# TAB 2: AUTO-ML MODEL ARENA
# ───────────────────────────────────────────────────────────────
with tab2:
    st.markdown("### **Auto-ML Model Benchmark Arena**")
    st.caption("5 forecasting architectures evaluated on 60-day unseen test data. The auto-selector automatically promotes the best architecture per SKU.")

    col_lead, col_radar = st.columns([1.2, 1])

    with col_lead:
        with st.container(border=True):
            st.markdown('<div class="ds-caption">Model Performance</div>', unsafe_allow_html=True)
            st.markdown("#### **Evaluation Leaderboard**")

            # C1: Winner treatment — trophy prefix in leaderboard
            formatted_lb = leaderboard_df.copy()
            formatted_lb["model_name"] = formatted_lb["model_name"].apply(
                lambda m: f"🏆 {m}" if m == winning_model_name else f"   {m}"
            )

            st.dataframe(
                formatted_lb.style.format({
                    "mape": "{:.2f}%",
                    "rmse": "{:,.1f}",
                    "mae": "{:,.1f}",
                    "wape": "{:.2f}%"
                }).highlight_min(subset=["mape", "rmse", "mae", "wape"], color="rgba(110,86,207,0.25)"),
                use_container_width=True,
                height=260
            )

            # C1: Styled winner banner
            st.markdown(f"""<div style="display:flex; align-items:center; gap:10px; padding:10px 16px; border-radius:12px; background:var(--accent-primary-soft); border:1px solid rgba(110,86,207,0.2); margin-top:8px;">
<span style="font-size:1.3rem;">🏆</span>
<div>
<div style="font-family:'Plus Jakarta Sans',sans-serif; font-weight:700; font-size:0.88rem; color:var(--accent-primary);">BEST FIT: {winning_model_name}</div>
<div style="font-family:'IBM Plex Mono',monospace; font-size:0.76rem; color:var(--text-secondary);">MAPE {winning_metrics['mape']:.2f}% · RMSE {winning_metrics['rmse']:,.1f} · WAPE {winning_metrics['wape']:.2f}%</div>
</div>
</div>""", unsafe_allow_html=True)

    with col_radar:
        with st.container(border=True):
            col_rtitle, col_rexpand = st.columns([9, 1])
            with col_rtitle:
                st.markdown('<div class="ds-caption">Comparative Metrics</div>', unsafe_allow_html=True)
            with col_rexpand:
                expand_radar = st.button("⤢", key="expand_radar", help="Focus mode")

            st.markdown("#### **Performance Radar**")
            radar_df = prepare_radar_data(leaderboard_df)

            fig_radar = go.Figure()
            for model_name in leaderboard_df["model_name"]:
                _is_winner = model_name == winning_model_name
                m_sub = radar_df[radar_df["model_name"] == model_name]
                fig_radar.add_trace(go.Scatterpolar(
                    r=m_sub["score"],
                    theta=m_sub["metric"],
                    fill="toself",
                    fillcolor="rgba(110,86,207,0.14)" if _is_winner else "rgba(0,0,0,0)",
                    name=f"🏆 {model_name}" if _is_winner else model_name,
                    showlegend=True,
                    line=dict(width=2.5 if _is_winner else 1.2),
                    opacity=1.0 if _is_winner else 0.35,
                    visible=True,
                    hovertemplate="<b>%{theta}</b><br>Score: %{r:.1f}/100<br>Model: " + model_name + "<extra></extra>",
                ))

            _radar_grid = "rgba(255,255,255,0.06)" if is_dark else "rgba(15,23,42,0.08)"
            fig_radar.update_layout(
                template=current_template,
                polar=dict(
                    bgcolor="rgba(0,0,0,0)",
                    radialaxis=dict(visible=True, range=[0, 100], gridcolor=_radar_grid),
                    angularaxis=dict(gridcolor=_radar_grid)
                ),
                height=320,
                hovermode="closest",
            )
            show_chart(fig_radar, key="radar_chart")

            export_html = render_chart_export_link(fig_radar, "model_radar.png", chart_height=320)
            st.markdown(f'<div class="ds-chart-actions">{export_html}</div>', unsafe_allow_html=True)

        if expand_radar:
            @st.dialog("Model Performance Radar — All Architectures", width="large")
            def _focus_radar():
                fig_fr = go.Figure(fig_radar)
                fig_fr.update_layout(height=500)
                show_chart(fig_fr, key="radar_focus_view")
                render_chart_export_link(fig_fr, "model_radar_focus.png", chart_height=500)
            _focus_radar()

    # XGBoost Feature Importance
    with st.container(border=True):
        col_fititle, col_fiexpand = st.columns([9, 1])
        with col_fititle:
            st.markdown('<div class="ds-caption">Model Interpretability</div>', unsafe_allow_html=True)
        with col_fiexpand:
            expand_fi = st.button("⤢", key="expand_fi", help="Focus mode")

        st.markdown("#### **XGBoost Feature Importance Ranking**")
        fig_fi = None
        try:
            fi = get_cached_xgb_fi(filtered_df)
            if not fi.empty:
                fi_sorted = fi.sort_values("importance", ascending=True)
                # C4: Gradient colorscale + percentage labels
                fi_total = fi_sorted["importance"].sum()
                fi_pct = (fi_sorted["importance"] / fi_total * 100).round(1)
                fig_fi = go.Figure(go.Bar(
                    y=fi_sorted["feature"],
                    x=fi_sorted["importance"],
                    orientation="h",
                    text=[f"{p:.1f}%" for p in fi_pct],
                    textposition="outside",
                    textfont=dict(size=10, color="#9AA3B8"),
                    marker=dict(
                        color=fi_sorted["importance"],
                        colorscale=[[0, "rgba(110,86,207,0.3)"], [1, "#6E56CF"]],
                        cornerradius=4,
                    ),
                    marker_line_width=0,
                    hovertemplate="<b>%{y}</b><br>Importance: %{x:.4f}<br>Contribution: %{text}<extra></extra>",
                ))
                fig_fi.update_layout(template=current_template, height=300, margin=dict(l=10, r=50, t=10, b=30), hovermode="closest")
                show_chart(fig_fi, key="fi_chart")

                export_html = render_chart_export_link(fig_fi, "feature_importance.png", chart_height=300)
                st.markdown(f'<div class="ds-chart-actions">{export_html}</div>', unsafe_allow_html=True)
        except Exception as e:
            st.info(f"Feature importance unavailable: {e}")

    if expand_fi and fig_fi is not None:
        @st.dialog("XGBoost Feature Importance — Top 10", width="large")
        def _focus_fi():
            fig_ffi = go.Figure(fig_fi)
            fig_ffi.update_layout(height=440)
            show_chart(fig_ffi, key="fi_focus_view")
            render_chart_export_link(fig_ffi, "feature_importance_focus.png", chart_height=440)
        _focus_fi()

    # C5: Actual vs. Predicted Scatter Plot — ML model fit quality
    with st.container(border=True):
        col_aptitle, col_apexpand = st.columns([9, 1])
        with col_aptitle:
            st.markdown('<div class="ds-caption">Model Fit Quality</div>', unsafe_allow_html=True)
        with col_apexpand:
            expand_ap = st.button("⤢", key="expand_ap", help="Focus mode")

        st.markdown("#### **Actual vs. Predicted — Test Set Scatter**")
        fig_ap = None
        try:
            # Use the last 60 days of historical as actuals (test set) vs forecast
            _test_actuals = filtered_df.tail(60)["units_sold"].values
            _test_preds = forecast_res.get("test_predictions", None)
            if _test_preds is not None and len(_test_preds) > 0:
                _act = _test_actuals[:len(_test_preds)]
                _prd = _test_preds[:len(_act)]
            else:
                # Fallback: use forecast values vs recent history overlap
                _n = min(len(forecast_df), 30)
                _act = filtered_df.tail(_n)["units_sold"].values
                _prd = forecast_df.head(_n)["predicted_units"].values
                _act = _act[:len(_prd)]

            if len(_act) > 0 and len(_prd) > 0 and len(_act) == len(_prd):
                _errors = np.abs(np.array(_act) - np.array(_prd))
                _all_vals = np.concatenate([_act, _prd])
                _range_min = max(0, np.min(_all_vals) * 0.85)
                _range_max = np.max(_all_vals) * 1.15

                fig_ap = go.Figure()
                # 45-degree perfect-fit reference line
                fig_ap.add_trace(go.Scatter(
                    x=[_range_min, _range_max],
                    y=[_range_min, _range_max],
                    mode="lines",
                    name="Perfect Fit",
                    line=dict(color="rgba(154,163,184,0.4)", width=1.5, dash="dash"),
                    hoverinfo="skip",
                ))
                # Scatter dots colored by error magnitude
                fig_ap.add_trace(go.Scatter(
                    x=_act,
                    y=_prd,
                    mode="markers",
                    name="Data Points",
                    marker=dict(
                        size=8,
                        color=_errors,
                        colorscale=[[0, "#22C55E"], [0.5, "#F5A623"], [1, "#EF4444"]],
                        showscale=True,
                        colorbar=dict(title="Abs Error", thickness=12, len=0.6),
                        line=dict(width=1, color="rgba(255,255,255,0.2)"),
                    ),
                    hovertemplate="<b>Actual: %{x:,.0f}</b><br>Predicted: %{y:,.0f}<br>Error: %{marker.color:,.0f}<extra></extra>",
                ))
                fig_ap.update_layout(
                    template=current_template,
                    height=300,
                    xaxis_title="Actual Units",
                    yaxis_title="Predicted Units",
                    xaxis=dict(range=[_range_min, _range_max]),
                    yaxis=dict(range=[_range_min, _range_max]),
                    margin=dict(l=10, r=10, t=10, b=40),
                    hovermode="closest",
                )
                show_chart(fig_ap, key="ap_chart")

                export_html = render_chart_export_link(fig_ap, "actual_vs_predicted.png", chart_height=300)
                st.markdown(f'<div class="ds-chart-actions">{export_html}</div>', unsafe_allow_html=True)
            else:
                st.info("Actual vs. Predicted scatter requires sufficient test data overlap.")
        except Exception as e:
            st.info(f"Actual vs. Predicted unavailable: {e}")

    if expand_ap and fig_ap is not None:
        @st.dialog("Actual vs. Predicted — Model Fit Quality", width="large")
        def _focus_ap():
            fig_fap = go.Figure(fig_ap)
            fig_fap.update_layout(height=480)
            show_chart(fig_fap, key="ap_focus_view")
            render_chart_export_link(fig_fap, "actual_vs_predicted_focus.png", chart_height=480)
        _focus_ap()

# ───────────────────────────────────────────────────────────────
# TAB 3: INVENTORY CONTROL TOWER
# ───────────────────────────────────────────────────────────────
with tab3:
    st.markdown("### **Inventory Trajectory & National Risk Matrix**")
    st.caption("30-day stock depletion projections, safety stock compliance, and Pareto ABC risk heatmap across all 20 SKUs.")

    col_traj, col_reg = st.columns([1.5, 1])

    with col_traj:
        with st.container(border=True):
            col_invtitle, col_invexpand = st.columns([9, 1])
            with col_invtitle:
                st.markdown('<div class="ds-caption">Inventory Depletion</div>', unsafe_allow_html=True)
            with col_invexpand:
                expand_inv = st.button("⤢", key="expand_inv", help="Focus mode")

            st.markdown("#### **30-Day Projected Stock Trajectory**")
            inv_df = impact_data["inventory_trajectory"]

            fig_inv = go.Figure()

            # D1: Danger zone background shading
            _rop = impact_data.get("reorder_point_units", 0)
            _ss = impact_data.get("safety_stock_units", 0)
            _y_max = max(inv_df["projected_stock"].max() * 1.15, _rop * 1.3)

            # Green zone (above ROP)
            fig_inv.add_hrect(y0=_rop, y1=_y_max, fillcolor="rgba(34,197,94,0.04)", line_width=0)
            # Amber zone (between Safety Stock and ROP)
            fig_inv.add_hrect(y0=_ss, y1=_rop, fillcolor="rgba(245,166,35,0.06)", line_width=0)
            # Red zone (below Safety Stock)
            fig_inv.add_hrect(y0=0, y1=_ss, fillcolor="rgba(239,68,68,0.06)", line_width=0)

            fig_inv.add_trace(go.Scatter(
                x=inv_df["date"],
                y=inv_df["projected_stock"],
                mode="lines+markers",
                name="Projected Stock",
                line=dict(color="#6E56CF", width=3, shape="spline"),
                marker=dict(size=4),
                hovertemplate="<b>%{x|%b %d, %Y}</b><br>Projected Stock: %{y:,.0f} units<extra></extra>",
            ))
            fig_inv.add_hline(
                y=_rop,
                line_dash="dash", line_color="#EF4444",
                annotation_text=f"ROP ({_rop:,} u)",
                annotation_position="top right"
            )
            fig_inv.add_hline(
                y=_ss,
                line_dash="dot", line_color="#F5A623",
                annotation_text=f"Safety Stock ({_ss:,} u)",
                annotation_position="bottom right"
            )

            # D2: Days-to-stockout annotation
            _stockout_rows = inv_df[inv_df["projected_stock"] <= 0]
            if not _stockout_rows.empty:
                _stockout_day = _stockout_rows.index[0] + 1
                _stockout_date = pd.to_datetime(_stockout_rows.iloc[0]["date"]).strftime("%b %d")
                _stockout_label = f"⚠ STOCKOUT IN {_stockout_day} DAYS ({_stockout_date})"
                _label_color = "#EF4444"
            else:
                _stockout_label = "✓ Stock covers full 30-day horizon"
                _label_color = "#22C55E"
            fig_inv.add_annotation(
                x=0.5, y=1.02, xref="paper", yref="paper",
                text=_stockout_label, showarrow=False,
                font=dict(size=11, color=_label_color, family="Inter, sans-serif"),
                xanchor="center",
            )

            fig_inv.update_layout(template=current_template, height=360, yaxis=dict(range=[0, _y_max]))
            show_chart(fig_inv, key="inv_chart")

            export_html = render_chart_export_link(fig_inv, "inventory_trajectory.png", chart_height=360)
            st.markdown(f'<div class="ds-chart-actions">{export_html}</div>', unsafe_allow_html=True)

        if expand_inv:
            @st.dialog("30-Day Projected Stock Trajectory", width="large")
            def _focus_inv():
                fig_finv = go.Figure(fig_inv)
                fig_finv.update_layout(height=500)
                show_chart(fig_finv, key="inv_focus_view")
                render_chart_export_link(fig_finv, "inventory_focus.png", chart_height=500)
            _focus_inv()

    with col_reg:
        with st.container(border=True):
            col_maptitle, col_mapexpand = st.columns([9, 1])
            with col_maptitle:
                st.markdown('<div class="ds-caption">Geographic Distribution</div>', unsafe_allow_html=True)
            with col_mapexpand:
                expand_map = st.button("⤢", key="expand_map", help="Focus mode")

            st.markdown("#### **India Regional Demand Hubs**")
            reg_summary = get_cached_regional_summary()

            fig_map = go.Figure()
            fig_map.add_trace(go.Scattergeo(
                lon=reg_summary["lon"],
                lat=reg_summary["lat"],
                text=reg_summary["region_name"] + "<br>Rev: ₹" + (reg_summary["total_revenue"]/1e6).round(1).astype(str) + "M",
                mode="markers+text",
                textposition="top center",
                marker=dict(
                    size=(reg_summary["total_revenue"] / reg_summary["total_revenue"].max() * 28 + 12),
                    color=reg_summary["total_revenue"],
                    colorscale="Purples",
                    showscale=False,
                    line=dict(width=1.5, color="#6E56CF")
                ),
                hovertemplate="<b>%{text}</b><br>Units: %{customdata:,.0f}<extra></extra>",
                customdata=reg_summary["total_units"],
            ))

            fig_map.update_geos(
                scope="asia",
                center=dict(lat=22.0, lon=78.9),
                projection_scale=3.8,
                showland=True, landcolor="#1A2033" if is_dark else "#F1F0F7",
                showcountries=True, countrycolor="rgba(255,255,255,0.12)" if is_dark else "rgba(15,23,42,0.12)",
                showocean=True, oceancolor="#0A0D14" if is_dark else "#E2E8F0"
            )

            fig_map.update_layout(template=current_template, height=360, margin=dict(l=0, r=0, t=10, b=0), hovermode="closest")
            show_chart(fig_map, key="map_chart")

            export_html = render_chart_export_link(fig_map, "india_regional_hubs.png", chart_height=360)
            st.markdown(f'<div class="ds-chart-actions">{export_html}</div>', unsafe_allow_html=True)

        if expand_map:
            @st.dialog("India Regional Demand Hubs", width="large")
            def _focus_map():
                fig_fm = go.Figure(fig_map)
                fig_fm.update_layout(height=500)
                show_chart(fig_fm, key="map_focus_view")
                render_chart_export_link(fig_fm, "india_regional_focus.png", chart_height=500)
            _focus_map()

    # National SKU Risk Heatmap Table
    with st.container(border=True):
        st.markdown('<div class="ds-caption">Strategic Classification</div>', unsafe_allow_html=True)
        st.markdown("#### **National SKU Pareto ABC Classification & Risk Matrix**")
        abc_table = get_cached_abc_classification()

        # D5: Conditional row formatting for ABC classification
        def _abc_row_style(row):
            """Color-code rows by ABC class and highlight selected SKU."""
            styles = [""] * len(row)
            # ABC class color coding
            abc_col = None
            for col_name in ["abc_class", "class", "ABC_Class"]:
                if col_name in row.index:
                    abc_col = col_name
                    break
            if abc_col:
                cls = str(row.get(abc_col, "")).strip().upper()
                if cls == "A":
                    styles = ["background-color: rgba(239,68,68,0.08); border-left: 3px solid #EF4444"] * len(row)
                elif cls == "B":
                    styles = ["background-color: rgba(245,166,35,0.08); border-left: 3px solid #F5A623"] * len(row)
                elif cls == "C":
                    styles = ["background-color: rgba(34,197,94,0.08); border-left: 3px solid #22C55E"] * len(row)
            # Highlight selected SKU row
            sku_col = None
            for col_name in ["sku_id", "SKU_ID", "sku"]:
                if col_name in row.index:
                    sku_col = col_name
                    break
            if sku_col and str(row.get(sku_col, "")) == selected_sku_id:
                styles = ["background-color: rgba(110,86,207,0.15); border-left: 3px solid #6E56CF; font-weight: 600"] * len(row)
            return styles

        _fmt_dict = {}
        if "revenue_inr" in abc_table.columns:
            _fmt_dict["revenue_inr"] = "₹{:,.0f}"
        if "cum_rev" in abc_table.columns:
            _fmt_dict["cum_rev"] = "₹{:,.0f}"
        if "cum_pct" in abc_table.columns:
            _fmt_dict["cum_pct"] = "{:.1f}%"

        st.dataframe(
            abc_table.style.format(_fmt_dict).apply(_abc_row_style, axis=1),
            use_container_width=True,
            height=300
        )


# ───────────────────────────────────────────────────────────────
# TAB 4: REAL-TIME WHAT-IF SCENARIO SIMULATOR
# ───────────────────────────────────────────────────────────────
with tab4:
    st.markdown("### **Supply Chain Stress Test & What-If Simulator**")
    st.caption("Simulate operational shocks — price elasticity, promotional campaigns, supplier delays — and inspect instant recalculation deltas across inventory & revenue KPIs.")

    with st.container(border=True):
        st.markdown('<div class="ds-caption">Simulation Parameters</div>', unsafe_allow_html=True)
        st.markdown("#### **Operational Shock Controls**")

        # E1: Preset Scenario Buttons
        st.markdown('<div class="ds-caption" style="margin-bottom:8px;">Quick Presets</div>', unsafe_allow_html=True)
        preset_cols = st.columns(4)
        with preset_cols[0]:
            if st.button("🌧 Monsoon Disruption", key="preset_monsoon", use_container_width=True):
                st.session_state["sim_lt"] = 10
                st.session_state["sim_dem"] = -20
                st.session_state["sim_prc"] = 0
                st.session_state["sim_elast"] = -1.2
                st.session_state["sim_promo"] = 0
                st.rerun()
        with preset_cols[1]:
            if st.button("🪔 Diwali Rush", key="preset_diwali", use_container_width=True):
                st.session_state["sim_lt"] = 3
                st.session_state["sim_dem"] = 80
                st.session_state["sim_prc"] = 10
                st.session_state["sim_elast"] = -0.8
                st.session_state["sim_promo"] = 40
                st.rerun()
        with preset_cols[2]:
            if st.button("💥 Price War", key="preset_pricewar", use_container_width=True):
                st.session_state["sim_lt"] = 0
                st.session_state["sim_dem"] = 0
                st.session_state["sim_prc"] = -25
                st.session_state["sim_elast"] = -2.0
                st.session_state["sim_promo"] = 0
                st.rerun()
        with preset_cols[3]:
            if st.button("↺ Reset Baseline", key="preset_reset", use_container_width=True):
                st.session_state["sim_lt"] = 0
                st.session_state["sim_dem"] = 0
                st.session_state["sim_prc"] = 0
                st.session_state["sim_elast"] = -1.2
                st.session_state["sim_promo"] = 0
                st.rerun()

        st.markdown("---")
        s1, s2, s3 = st.columns(3)
        with s1:
            sim_lt_add = st.slider("Supplier Lead Time Delay (+/− Days)", -5, 15, 0, key="sim_lt")
        with s2:
            sim_demand_mult = st.slider("Demand Surge / Dip (% Change)", -50, 100, 0, step=5, key="sim_dem")
        with s3:
            sim_price_mult = st.slider("Selling Price Adjustment (% Change)", -30, 50, 0, step=5, key="sim_prc")

        st.markdown("---")
        st.markdown('<div class="ds-caption">Advanced Elasticity & Promotion Controls</div>', unsafe_allow_html=True)
        e1, e2 = st.columns(2)
        with e1:
            sim_elasticity = st.slider(
                "Price Elasticity Coefficient",
                min_value=-3.0, max_value=0.0, value=-1.2, step=0.1,
                help="FMCG typical: −1.2. A 10% price hike × −1.2 elasticity → 12% demand drop.",
                key="sim_elast"
            )
        with e2:
            sim_promo_boost = st.slider(
                "Promo Campaign Boost (%)",
                min_value=0, max_value=80, value=0, step=5,
                help="Short-term trade promotion lift applied on top of base demand, independent of price.",
                key="sim_promo"
            )

    @st.cache_data(show_spinner=False)
    def simulate_scenario(_historical_df, _forecast_df, _p_info, base_lt, lt_add, dem_mult, prc_mult, elasticity, promo_pct, stock, abc):
        eff_lt = max(1, base_lt + lt_add)

        # Price elasticity feedback: price change feeds back into demand
        price_delta_pct = prc_mult / 100.0
        elasticity_demand_delta = price_delta_pct * elasticity  # e.g. +0.10 × -1.2 = -0.12

        # Combined demand multiplier: manual surge × elasticity feedback × promo boost
        eff_dem_scale = (1.0 + dem_mult / 100.0) * (1.0 + elasticity_demand_delta) * (1.0 + promo_pct / 100.0)

        eff_prc = _p_info.get("base_price", 100) * (1.0 + price_delta_pct)

        s_forecast = _forecast_df.copy()
        s_forecast["predicted_units"] = (s_forecast["predicted_units"] * eff_dem_scale).clip(lower=0)

        s_calc = OperationsImpactCalculator(lead_time_days=eff_lt)
        s_info = _p_info.copy()
        s_info["base_price"] = eff_prc

        s_impact = s_calc.calculate_sku_impact(
            product_info=s_info,
            historical_df=_historical_df,
            forecast_df=s_forecast,
            current_stock=stock,
            abc_class=abc
        )
        return s_impact, eff_lt, eff_dem_scale, elasticity_demand_delta

    sim_impact, effective_lt, net_demand_scale, elast_feedback = simulate_scenario(
        filtered_df, forecast_df, sku_info, lead_time,
        sim_lt_add, sim_demand_mult, sim_price_mult, sim_elasticity, sim_promo_boost,
        current_stock, abc_class
    )

    # ── Scenario Impact Narrative Card ──
    net_demand_pct = (net_demand_scale - 1.0) * 100.0
    base_rev_30d = impact_data.get("total_30d_forecast_units", 0) * sku_info.get("base_price", 100)
    sim_rev_30d = sim_impact.get("total_30d_forecast_units", 0) * sku_info.get("base_price", 100) * (1.0 + sim_price_mult / 100.0)
    rev_delta = sim_rev_30d - base_rev_30d
    rev_delta_str = f"₹{abs(rev_delta)/1e5:.1f} Lakh" if abs(rev_delta) < 1e7 else f"₹{abs(rev_delta)/1e7:.2f} Cr"

    narrative_parts = []
    if sim_price_mult != 0:
        narrative_parts.append(f"A **{sim_price_mult:+d}% price adjustment** with elasticity **{sim_elasticity:.1f}** drives a **{elast_feedback*100:+.1f}%** demand feedback.")
    if sim_demand_mult != 0:
        narrative_parts.append(f"A **{sim_demand_mult:+d}% manual demand shock** is applied.")
    if sim_promo_boost > 0:
        narrative_parts.append(f"A **+{sim_promo_boost}% promotional campaign boost** lifts volume further.")
    if sim_lt_add != 0:
        narrative_parts.append(f"Supplier lead time shifts by **{sim_lt_add:+d} days** to **{effective_lt} days**.")

    if narrative_parts:
        rev_arrow = "▲" if rev_delta >= 0 else "▼"
        narrative_parts.append(f"**Net combined demand effect: {net_demand_pct:+.1f}%.** Projected 30-day revenue delta: **{rev_arrow} {rev_delta_str}**.")
        narrative_text = " ".join(narrative_parts)
    else:
        narrative_text = "All parameters at baseline — no scenario shocks applied. Adjust the sliders above to simulate operational stress conditions."

    with st.container(border=True):
        st.markdown('<div class="ds-caption">Scenario Impact Narrative</div>', unsafe_allow_html=True)
        st.markdown("#### **Combined Stress-Test Summary**")
        st.markdown(narrative_text)

    # ── Direction-Aware Delta Metrics Row ──
    delta_ss = sim_impact['safety_stock_units'] - impact_data['safety_stock_units']
    delta_rop = sim_impact['reorder_point_units'] - impact_data['reorder_point_units']
    delta_risk = sim_impact['revenue_at_risk_inr'] - impact_data['revenue_at_risk_inr']
    delta_po_qty = sim_impact.get('recommended_po_qty_units', 0) - impact_data.get('recommended_po_qty_units', 0)

    st.markdown("#### **Before vs. After Scenario Delta Metrics**")
    with st.container(border=True):
        m1, m2, m3, m4, m5, m6 = st.columns([1.0, 1.0, 1.0, 1.2, 1.2, 1.0])
        m1.metric("Lead Time", f"{effective_lt} Days", delta=f"{sim_lt_add:+d} d" if sim_lt_add != 0 else None)
        m2.metric("Safety Stock", f"{sim_impact['safety_stock_units']:,} u", delta=f"{delta_ss:+,d} u")
        m3.metric("Reorder Point", f"{sim_impact['reorder_point_units']:,} u", delta=f"{delta_rop:+,d} u")
        m4.metric("Rev. at Risk", f"₹{sim_impact['revenue_at_risk_inr']:,.0f}", delta=f"₹{delta_risk:+,.0f}", delta_color="inverse")
        m5.metric("30D Revenue Δ", f"{'▲' if rev_delta >= 0 else '▼'} {rev_delta_str}", delta=f"{(rev_delta/max(1,base_rev_30d))*100:+.1f}%")
        m6.metric("PO Qty Δ", f"{sim_impact.get('recommended_po_qty_units', 0):,} u", delta=f"{delta_po_qty:+,d} u")

    # ── Scenario Comparison Trajectory Chart ──
    with st.container(border=True):
        col_simtitle, col_simexpand = st.columns([9, 1])
        with col_simtitle:
            st.markdown('<div class="ds-caption">Trajectory Comparison</div>', unsafe_allow_html=True)
        with col_simexpand:
            expand_sim = st.button("⤢", key="expand_sim", help="Focus mode")

        st.markdown("#### **Baseline vs. Simulated Scenario Trajectory**")

        base_traj = impact_data["inventory_trajectory"]
        sim_traj = sim_impact["inventory_trajectory"]

        fig_sim = go.Figure()

        # Fill-between shading (upper bound first, then lower with fill)
        fig_sim.add_trace(go.Scatter(
            x=base_traj["date"],
            y=base_traj["projected_stock"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip"
        ))
        fig_sim.add_trace(go.Scatter(
            x=sim_traj["date"],
            y=sim_traj["projected_stock"],
            mode="lines",
            fill="tonexty",
            fillcolor="rgba(110,86,207,0.08)",
            line=dict(width=0),
            name="Divergence Gap",
            hoverinfo="skip"
        ))

        # Baseline trajectory (dashed)
        fig_sim.add_trace(go.Scatter(
            x=base_traj["date"],
            y=base_traj["projected_stock"],
            mode="lines",
            name="Baseline Stock Trajectory",
            line=dict(color="#9AA3B8", width=2, dash="dash"),
            hovertemplate="<b>%{x|%b %d, %Y}</b><br>Baseline: %{y:,.0f} units<extra></extra>",
        ))

        # Simulated trajectory (solid)
        fig_sim.add_trace(go.Scatter(
            x=sim_traj["date"],
            y=sim_traj["projected_stock"],
            mode="lines+markers",
            name="Simulated Scenario Trajectory",
            line=dict(color="#6E56CF", width=3, shape="spline"),
            marker=dict(size=4),
            hovertemplate="<b>%{x|%b %d, %Y}</b><br>Simulated: %{y:,.0f} units<extra></extra>",
        ))

        # Dual Safety Stock lines
        fig_sim.add_hline(
            y=impact_data["safety_stock_units"],
            line_dash="dot", line_color="#F5A623", line_width=1.5,
            annotation_text=f"Baseline SS ({impact_data['safety_stock_units']:,} u)",
            annotation_position="bottom left"
        )
        fig_sim.add_hline(
            y=sim_impact["safety_stock_units"],
            line_dash="dot", line_color="#C98A2E", line_width=1.5,
            annotation_text=f"Simulated SS ({sim_impact['safety_stock_units']:,} u)",
            annotation_position="top left"
        )

        # Simulated ROP line
        fig_sim.add_hline(
            y=sim_impact["reorder_point_units"],
            line_dash="dash", line_color="#EF4444", line_width=1.5,
            annotation_text=f"Simulated ROP ({sim_impact['reorder_point_units']:,} u)",
            annotation_position="top right"
        )

        # Stockout day marker
        sim_stockout_rows = sim_traj[sim_traj["projected_stock"] <= 0]
        if not sim_stockout_rows.empty:
            stockout_date = sim_stockout_rows.iloc[0]["date"]
            stockout_str = pd.to_datetime(stockout_date).strftime("%Y-%m-%d")
            fig_sim.add_shape(
                type="line",
                x0=stockout_str, x1=stockout_str,
                y0=0, y1=1, yref="paper",
                line=dict(color="#EF4444", width=2, dash="dot")
            )
            fig_sim.add_annotation(
                x=stockout_str, y=0.05, yref="paper",
                text="⚠ STOCKOUT",
                showarrow=True, arrowhead=2, arrowcolor="#EF4444",
                font=dict(size=12, color="#EF4444", family="Plus Jakarta Sans, sans-serif"),
                bgcolor="rgba(239,68,68,0.12)",
                bordercolor="#EF4444",
                borderwidth=1,
                borderpad=4,
                ax=0, ay=-40
            )

        fig_sim.update_layout(template=current_template, height=400)
        show_chart(fig_sim, key="sim_chart")

        export_html = render_chart_export_link(fig_sim, "scenario_comparison.png", chart_height=400)
        st.markdown(f'<div class="ds-chart-actions">{export_html}</div>', unsafe_allow_html=True)

    if expand_sim:
        @st.dialog("Baseline vs. Simulated Scenario Trajectory", width="large")
        def _focus_sim():
            fig_fsim = go.Figure(fig_sim)
            fig_fsim.update_layout(height=560)
            show_chart(fig_fsim, key="sim_focus_view")
            render_chart_export_link(fig_fsim, "scenario_focus.png", chart_height=560)
        _focus_sim()


# ───────────────────────────────────────────────────────────────
# TAB 5: AI PRESCRIPTIVE CONTROL ROOM
# ───────────────────────────────────────────────────────────────
with tab5:
    st.markdown("### **AI Prescriptive Decision Support System**")
    st.caption("GenAI operational recommendations for procurement, stock rebalancing, and financial risk mitigation.")

    status_str = impact_data.get("po_trigger_status", impact_data.get("inventory_status", "STABLE"))
    priority_level = llm_report.get("priority_level", "HEALTHY")

    # F2: Full-width glass alert banner
    if "CRITICAL" in status_str or priority_level == "CRITICAL":
        _alert_cls, _alert_icon, _alert_title = "critical", "🚨", "CRITICAL STOCKOUT RISK DETECTED"
        _alert_sub = f"Immediate procurement action required for {extract_name(sku_info)} — stock below safety threshold."
    elif "WARNING" in status_str or priority_level == "WARNING":
        _alert_cls, _alert_icon, _alert_title = "warning", "⚠️", "REORDER POINT BREACH IMMINENT"
        _alert_sub = f"Stock approaching reorder point for {extract_name(sku_info)} — review procurement pipeline."
    else:
        _alert_cls, _alert_icon, _alert_title = "healthy", "✅", "HEALTHY — INVENTORY BALANCED"
        _alert_sub = f"Stock levels healthy for {extract_name(sku_info)} — no immediate action needed."

    st.markdown(f"""<div class="ds-alert-banner {_alert_cls}">
<span class="ds-alert-icon">{_alert_icon}</span>
<div class="ds-alert-text">
<div class="ds-alert-title" style="color:var(--status-{_alert_cls});">{_alert_title}</div>
<div class="ds-alert-sub">{_alert_sub}</div>
</div>
</div>""", unsafe_allow_html=True)

    exec_summary = llm_report.get("executive_summary", "N/A")
    fin_risk = llm_report.get("financial_risk_narrative", llm_report.get("financial_risk", "N/A"))
    proc_action = llm_report.get("recommended_action", llm_report.get("procurement_directive", "N/A"))
    model_rat = llm_report.get("model_rationale", "N/A")

    # F1: Helper to convert paragraph text into structured bullet HTML
    def _to_bullet_html(text, icon="📊"):
        """Split paragraph text into sentence-level bullets with icons."""
        if not text or text == "N/A":
            return f'<div style="color:var(--text-secondary); font-style:italic;">No data available.</div>'
        sentences = [s.strip() for s in text.replace(". ", ".\n").split("\n") if s.strip()]
        bullets = []
        for s in sentences[:5]:  # Cap at 5 bullets per card
            # Auto-detect icon based on content keywords
            if any(w in s.lower() for w in ["recommend", "order", "procure", "action", "should", "must"]):
                b_icon = "✅"
            elif any(w in s.lower() for w in ["risk", "warn", "critical", "stockout", "loss", "danger"]):
                b_icon = "⚠️"
            elif any(w in s.lower() for w in ["₹", "revenue", "cost", "margin", "profit", "lakh", "crore"]):
                b_icon = "💰"
            else:
                b_icon = icon
            bullets.append(f'<li><span class="ds-bullet-icon">{b_icon}</span><span>{s}</span></li>')
        return f'<ul class="ds-ai-bullets">{"".join(bullets)}</ul>'

    # 4 AI Action Cards Grid with structured bullets
    a1, a2, a3, a4 = st.columns(4)
    with a1:
        st.markdown(f"""<div class="ds-card">
<div class="ds-icon-chip indigo">AI</div>
<div class="ds-caption">Executive Summary</div>
{_to_bullet_html(exec_summary, "📊")}
</div>""", unsafe_allow_html=True)

    with a2:
        st.markdown(f"""<div class="ds-card">
<div class="ds-icon-chip gold">PO</div>
<div class="ds-caption">Procurement Directive</div>
{_to_bullet_html(proc_action, "📦")}
</div>""", unsafe_allow_html=True)

    with a3:
        st.markdown(f"""<div class="ds-card">
<div class="ds-icon-chip red">₹</div>
<div class="ds-caption">Financial Risk & Rupee Impact</div>
{_to_bullet_html(fin_risk, "💰")}
</div>""", unsafe_allow_html=True)

    with a4:
        st.markdown(f"""<div class="ds-card">
<div class="ds-icon-chip teal">ML</div>
<div class="ds-caption">AI Model Selection Rationale</div>
{_to_bullet_html(model_rat, "🧠")}
</div>""", unsafe_allow_html=True)

    st.divider()

    with st.container(border=True):
        st.markdown('<div class="ds-caption">Export & Logistics Trigger</div>', unsafe_allow_html=True)
        st.markdown("#### **Executive Export & Purchase Order Generator**")

        rec_qty = impact_data.get("recommended_po_qty_units", impact_data.get("recommended_order_qty", 0))
        total_po_val = impact_data.get("recommended_po_value_inr", rec_qty * unit_price * 0.7)

        # Purchase Order DataFrame
        po_df = pd.DataFrame([{
            "PO_ID": f"PO-2026-{selected_sku_id}-01",
            "SKU_ID": selected_sku_id,
            "SKU_Name": sku_info.get("sku_name", sku_info.get("name", "")),
            "Category": sku_info.get("category", "FMCG"),
            "Recommended_Order_Qty": rec_qty,
            "Unit_Cost_INR": unit_price * 0.7,
            "Total_PO_Value_INR": total_po_val,
            "Lead_Time_Days": lead_time,
            "Priority": "URGENT" if ("CRITICAL" in status_str or priority_level == "CRITICAL") else ("HIGH" if ("WARNING" in status_str or priority_level == "WARNING") else "NORMAL")
        }])

        po_csv = po_df.to_csv(index=False).encode('utf-8')

        pdf_bytes = generate_executive_pdf_report(
            sku_info=sku_info,
            region_name=region_options.get(selected_region, "National Aggregation (India)"),
            impact_data=impact_data,
            winning_model=winning_model_name,
            winning_mape=winning_metrics["mape"],
            llm_report=llm_report
        )

        # F3: Visual PO Preview Card
        _po_priority = "URGENT" if ("CRITICAL" in status_str or priority_level == "CRITICAL") else ("HIGH" if ("WARNING" in status_str or priority_level == "WARNING") else "NORMAL")
        _po_priority_color = "var(--status-critical)" if _po_priority == "URGENT" else ("var(--status-warning)" if _po_priority == "HIGH" else "var(--status-healthy)")
        _po_val_str = f"₹{total_po_val:,.0f}" if total_po_val < 1e7 else f"₹{total_po_val/1e7:.2f} Cr"
        st.markdown(f"""<div class="ds-po-preview">
<div style="font-family:'Plus Jakarta Sans',sans-serif; font-weight:700; font-size:0.85rem; color:var(--accent-primary); margin-bottom:10px;">📋 PURCHASE ORDER PREVIEW</div>
<div class="ds-po-row"><span class="ds-po-label">PO ID</span><span class="ds-po-val">PO-2026-{selected_sku_id}-01</span></div>
<div class="ds-po-row"><span class="ds-po-label">SKU</span><span class="ds-po-val">{extract_name(sku_info)} ({selected_sku_id})</span></div>
<div class="ds-po-row"><span class="ds-po-label">Order Qty</span><span class="ds-po-val">{rec_qty:,.0f} units</span></div>
<div class="ds-po-row"><span class="ds-po-label">Unit Cost</span><span class="ds-po-val">₹{unit_price * 0.7:,.0f}</span></div>
<div class="ds-po-row"><span class="ds-po-label">Total Value</span><span class="ds-po-val">{_po_val_str}</span></div>
<div class="ds-po-row"><span class="ds-po-label">Lead Time</span><span class="ds-po-val">{lead_time} days</span></div>
<div class="ds-po-row"><span class="ds-po-label">Priority</span><span class="ds-po-val" style="color:{_po_priority_color}; font-weight:700;">{_po_priority}</span></div>
</div>""", unsafe_allow_html=True)

        exp1, exp2 = st.columns([1, 1])

        b64_csv = base64.b64encode(po_csv).decode('utf-8')
        csv_filename = f"PO_{selected_sku_id}_{pd.Timestamp.now().strftime('%Y%m%d')}.csv"
        csv_href = f'''<a href="data:text/csv;base64,{b64_csv}" download="{csv_filename}" class="ds-export-btn gold">Download Purchase Order CSV</a>'''

        with exp1:
            st.markdown(csv_href, unsafe_allow_html=True)

        b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_filename = f"Executive_Brief_{selected_sku_id}.pdf"
        pdf_href = f'''<a href="data:application/pdf;base64,{b64_pdf}" download="{pdf_filename}" class="ds-export-btn indigo">Download 1-Page Executive PDF Brief</a>'''

        with exp2:
            st.markdown(pdf_href, unsafe_allow_html=True)

        full_text_brief = f"""DEMANDSENSE AI — EXECUTIVE PROCUREMENT BRIEF
Generated for SKU: {sku_info.get('name', selected_sku_id)} ({selected_sku_id})
Region: {region_options.get(selected_region, 'National Aggregation')}

EXECUTIVE SUMMARY:
{exec_summary}

RECOMMENDED PROCUREMENT DIRECTIVE:
{proc_action}

FINANCIAL RISK & RUPEE IMPACT:
{fin_risk}

AI MODEL SELECTION RATIONALE:
{model_rat}
"""
        st.text_area("Full Raw Text Brief", value=full_text_brief, height=160)
