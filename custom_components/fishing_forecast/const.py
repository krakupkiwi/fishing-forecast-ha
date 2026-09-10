"""Constants and configurable scoring defaults.

Values only — this module deliberately imports nothing from Home Assistant so the
scoring core can read defaults without pulling in HA. See ``docs/scoring.md`` for the
rationale behind every number here.
"""

from __future__ import annotations

from typing import Any, Final

from .models import Component, ScoringConfig

DOMAIN: Final = "fishing_forecast"
MANUFACTURER: Final = "Fishing Forecast"

# --------------------------------------------------------------------------- #
# Coordinator / API
# --------------------------------------------------------------------------- #

DEFAULT_UPDATE_MINUTES: Final = 30
DEFAULT_FORECAST_DAYS: Final = 14  # request 16, surface up to this many
MAX_FORECAST_DAYS: Final = 16
DEFAULT_WINDOW_HOURS: Final = 3

WEATHER_URL: Final = "https://api.open-meteo.com/v1/forecast"
MARINE_URL: Final = "https://marine-api.open-meteo.com/v1/marine"
HTTP_TIMEOUT_SECONDS: Final = 30

WEATHER_HOURLY_FIELDS: Final = (
    "temperature_2m",
    "precipitation",
    "rain",
    "showers",
    "cloud_cover",
    "surface_pressure",
    "pressure_msl",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "weather_code",
)
WEATHER_DAILY_FIELDS: Final = (
    "sunrise",
    "sunset",
    "daylight_duration",
    "moonrise",
    "moonset",
    "moon_phase",
)
# best_match marine request — full field set incl. modelled tide (~9.5 day horizon).
MARINE_HOURLY_FIELDS_FINE: Final = (
    "wave_height",
    "wave_direction",
    "wave_period",
    "swell_wave_height",
    "swell_wave_direction",
    "swell_wave_period",
    "wind_wave_height",
    "wind_wave_direction",
    "wind_wave_period",
    "sea_surface_temperature",
    "sea_level_height_msl",
)
# ncep_gfswave025 request — waves/swell only, full 16 day horizon, no tide.
MARINE_HOURLY_FIELDS_EXTENDED: Final = (
    "wave_height",
    "wave_period",
    "swell_wave_height",
    "swell_wave_direction",
    "swell_wave_period",
    "wind_wave_height",
    "wind_wave_period",
)
MARINE_EXTENDED_MODEL: Final = "ncep_gfswave025"

# --------------------------------------------------------------------------- #
# Config-flow keys
# --------------------------------------------------------------------------- #

CONF_NAME: Final = "name"
CONF_LATITUDE: Final = "latitude"
CONF_LONGITUDE: Final = "longitude"
CONF_MARINE_LATITUDE: Final = "marine_latitude"
CONF_MARINE_LONGITUDE: Final = "marine_longitude"
CONF_COAST_BEARING: Final = "coast_bearing"
CONF_TIMEZONE: Final = "timezone"
CONF_FORECAST_DAYS: Final = "forecast_days"

OPT_WINDOW_HOURS: Final = "window_hours"
OPT_PREFERRED_HOURS: Final = "preferred_hours"
OPT_WEIGHTS_FULL: Final = "weights_full"
OPT_WEIGHTS_OUTLOOK: Final = "weights_outlook"
OPT_COAST_BEARING: Final = "coast_bearing"

# Mindarie, WA — the initial target location (spec).
DEFAULT_LOCATION: Final = {
    CONF_NAME: "Mindarie",
    CONF_LATITUDE: -31.69,
    CONF_LONGITUDE: 115.70,
    CONF_MARINE_LATITUDE: -31.72,
    CONF_MARINE_LONGITUDE: 115.55,
    CONF_COAST_BEARING: 270.0,
    CONF_TIMEZONE: "Australia/Perth",
}

# --------------------------------------------------------------------------- #
# Scoring defaults (docs/scoring.md is authoritative)
# --------------------------------------------------------------------------- #

DEFAULT_FULL_WEIGHTS: Final[dict[Component, float]] = {
    Component.WIND: 0.30,
    Component.SWELL: 0.20,
    Component.TIDE: 0.15,
    Component.SOLUNAR: 0.15,
    Component.SUN: 0.10,
    Component.RAIN: 0.05,
    Component.PRESSURE: 0.05,
}
DEFAULT_OUTLOOK_WEIGHTS: Final[dict[Component, float]] = {
    Component.WIND: 0.50,
    Component.SOLUNAR: 0.20,
    Component.SUN: 0.12,
    Component.RAIN: 0.09,
    Component.PRESSURE: 0.09,
}

# Breakpoint tables: list[(x, score)], monotonic x, linear interpolation between.
DEFAULT_WIND: Final[dict[str, Any]] = {
    "speed_kmh_curve": [
        (0, 100),
        (8, 100),
        (15, 80),
        (20, 55),
        (25, 30),
        (30, 10),
        (40, 0),
        (50, 0),
    ],
    "direction_multiplier": {  # offshore-alignment degrees -> multiplier (interpolated)
        "0": 1.00,
        "45": 0.90,
        "90": 0.75,
        "135": 0.55,
        "180": 0.35,
    },
    # Wind speed (km/h) at which the directional multiplier reaches full effect.
    # Below this the coastline matters progressively less; at dead calm not at all.
    "direction_full_effect_kmh": 18.0,
    "gust_ratio_penalty": {"ratio": 1.6, "min_gust_kmh": 25, "factor": 0.85},
    "directional_hint_nudge": 0.10,
}
DEFAULT_SWELL: Final[dict[str, Any]] = {
    "height_m_curve": [
        (0.0, 55),
        (0.3, 70),
        (0.5, 90),
        (0.8, 100),
        (1.5, 100),
        (2.0, 70),
        (2.5, 40),
        (3.0, 10),
        (4.0, 0),
    ],
    "period_ref_s": 10.0,
    "period_exponent": 0.5,
    "period_clamp": [0.8, 1.4],
    "ideal_swell_min_m": 0.5,
    "ideal_swell_max_m": 1.5,
    "max_safe_swell_m": 2.5,
    "over_safe_cap": 10,
}
DEFAULT_TIDE: Final[dict[str, Any]] = {
    # hours relative to next/last high -> score (interpolated); +ve = after high
    "relative_to_high_curve": [
        (-2.0, 90),
        (-1.0, 100),
        (0.0, 95),
        (1.0, 85),
        (2.5, 60),
    ],
    "at_low_score": 50,
    "early_rise_score": 70,
    "generic_rising_score": 65,
    "generic_falling_score": 55,
    "min_prominence_m": 0.05,
    "min_extreme_spacing_h": 4.0,
}
DEFAULT_SOLUNAR: Final[dict[str, Any]] = {
    "major_minutes": 120,
    "minor_minutes": 60,
    "edge_grace_minutes": 30,
    "inside_major": 100,
    "near_major": 90,
    "inside_minor": 80,
    "near_minor": 70,
    "baseline": 50,
    "phase_bonus": 5,
    "phase_bonus_days": 2,
}
DEFAULT_SUN: Final[dict[str, Any]] = {
    "base": 40,
    "sunrise_window_min": [-60, 150],  # minutes relative to sunrise
    "sunset_window_min": [-150, 60],
    "peak": 100,
    "shoulder": 70,
    "shoulder_offset_min": 90,
}
DEFAULT_RAIN: Final[dict[str, Any]] = {
    "mm_h_curve": [(0.0, 100), (0.5, 90), (1.0, 75), (2.0, 55), (5.0, 30), (10.0, 5)],
}
DEFAULT_PRESSURE: Final[dict[str, Any]] = {
    "lookback_hours": 3,
    "bins": [  # (delta_hpa_upper_exclusive, trend, score); last bin is the catch-all
        (-3.0, "rapidly_falling", 80),
        (-1.0, "falling", 70),
        (1.0, "steady", 60),
        (3.0, "rising", 55),
        (999.0, "rapidly_rising", 45),
    ],
}


def default_scoring_config() -> ScoringConfig:
    """Return the built-in :class:`ScoringConfig`. The options flow overrides fields."""

    return ScoringConfig(
        full_weights=dict(DEFAULT_FULL_WEIGHTS),
        outlook_weights=dict(DEFAULT_OUTLOOK_WEIGHTS),
        window_hours=DEFAULT_WINDOW_HOURS,
        preferred_hours=None,
        wind=dict(DEFAULT_WIND),
        swell=dict(DEFAULT_SWELL),
        tide=dict(DEFAULT_TIDE),
        solunar=dict(DEFAULT_SOLUNAR),
        sun=dict(DEFAULT_SUN),
        rain=dict(DEFAULT_RAIN),
        pressure=dict(DEFAULT_PRESSURE),
    )
