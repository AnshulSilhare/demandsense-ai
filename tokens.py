"""
DemandSense AI — Design Tokens (Palette & Variables)
=====================================================
Single source of truth for color palette, surface colors, typography, and status tokens.
Supports both Executive Dark Mode (default) and Light Mode.

Author: Anshul Silhare
"""

DARK_TOKENS = {
    "bg_canvas": "#0A0D14",
    "bg_shell": "#0F1320",
    "bg_surface": "#131826",
    "bg_surface_elevated": "#1A2033",
    "bg_surface_hover": "#20273B",
    "border_subtle": "rgba(255, 255, 255, 0.06)",
    "border_default": "rgba(255, 255, 255, 0.12)",
    "text_primary": "#EDEFF3",
    "text_secondary": "#9AA3B8",
    "text_tertiary": "#666F84",
    "accent_primary": "#6E56CF",          # Intelligence Indigo
    "accent_primary_soft": "rgba(110, 86, 207, 0.14)",
    "accent_secondary": "#C98A2E",        # Marigold Gold (Indian Demand / Seasonality)
    "accent_secondary_soft": "rgba(201, 138, 46, 0.14)",
    "status_critical": "#EF4444",
    "status_critical_bg": "rgba(239, 68, 68, 0.12)",
    "status_warning": "#F5A623",
    "status_warning_bg": "rgba(245, 166, 35, 0.12)",
    "status_healthy": "#22C55E",
    "status_healthy_bg": "rgba(34, 197, 94, 0.12)",
    "command_bar_bg": "rgba(15, 19, 32, 0.75)",
    "shadow": "0 1px 2px rgba(0, 0, 0, 0.4), 0 8px 24px rgba(0, 0, 0, 0.28)",
}

LIGHT_TOKENS = {
    "bg_canvas": "#F2F1FA",
    "bg_shell": "#F7F6FC",
    "bg_surface": "#FFFFFF",
    "bg_surface_elevated": "#F8F7FD",
    "bg_surface_hover": "#F1F0F7",
    "border_subtle": "rgba(15, 23, 42, 0.06)",
    "border_default": "rgba(15, 23, 42, 0.12)",
    "text_primary": "#14161F",
    "text_secondary": "#5B6172",
    "text_tertiary": "#8B90A0",
    "accent_primary": "#6E56CF",          # Keep brand hue constant across themes
    "accent_primary_soft": "rgba(110, 86, 207, 0.12)",
    "accent_secondary": "#B87A1F",        # Deepened gold for AA contrast on light
    "accent_secondary_soft": "rgba(184, 122, 31, 0.12)",
    "status_critical": "#DC2626",
    "status_critical_bg": "#FEF2F2",
    "status_warning": "#D97706",
    "status_warning_bg": "#FFFBEB",
    "status_healthy": "#16A34A",
    "status_healthy_bg": "#F0FDF4",
    "command_bar_bg": "rgba(247, 246, 252, 0.85)",
    "shadow": "0 1px 2px rgba(15, 23, 42, 0.04), 0 8px 24px rgba(15, 23, 42, 0.07)",
}
