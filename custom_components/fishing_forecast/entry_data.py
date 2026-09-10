"""Translate a config entry's ``data`` / ``options`` mappings into the core
dataclasses. Kept free of Home Assistant imports so it is trivially testable.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from .const import (
    CONF_COAST_BEARING,
    CONF_FORECAST_DAYS,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MARINE_LATITUDE,
    CONF_MARINE_LONGITUDE,
    CONF_NAME,
    CONF_PROFILE,
    CONF_TIDE_STATION,
    CONF_TIMEZONE,
    DEFAULT_FORECAST_DAYS,
    DEFAULT_UPDATE_MINUTES,
    DEFAULT_WINDOW_HOURS,
    OPT_COAST_BEARING,
    OPT_PREFERRED_END,
    OPT_PREFERRED_START,
    OPT_PROFILE,
    OPT_UPDATE_MINUTES,
    OPT_WEIGHT_PREFIX,
    OPT_WINDOW_HOURS,
)
from .models import Component, LocationConfig, ScoringConfig
from .profiles import DEFAULT_PROFILE, scoring_config_for
from .util import wrap360


def slugify_id(latitude: float, longitude: float) -> str:
    """Stable unique id for a location (also used as the entry unique_id)."""

    return f"{latitude:.4f}_{longitude:.4f}".replace("-", "m").replace(".", "_")


def location_from_entry(data: Mapping[str, Any], options: Mapping[str, Any]) -> LocationConfig:
    coast_bearing = float(options.get(OPT_COAST_BEARING, data[CONF_COAST_BEARING]))
    return LocationConfig(
        id=slugify_id(float(data[CONF_LATITUDE]), float(data[CONF_LONGITUDE])),
        name=str(data[CONF_NAME]),
        latitude=float(data[CONF_LATITUDE]),
        longitude=float(data[CONF_LONGITUDE]),
        marine_latitude=float(data[CONF_MARINE_LATITUDE]),
        marine_longitude=float(data[CONF_MARINE_LONGITUDE]),
        coast_bearing=wrap360(coast_bearing),
        timezone=str(data.get(CONF_TIMEZONE) or "UTC"),
        tide_station=(options.get(CONF_TIDE_STATION) or data.get(CONF_TIDE_STATION) or None),
    )


def forecast_days(data: Mapping[str, Any]) -> int:
    return int(data.get(CONF_FORECAST_DAYS, DEFAULT_FORECAST_DAYS))


def update_minutes(options: Mapping[str, Any]) -> int:
    return int(options.get(OPT_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES))


def profile_name(data: Mapping[str, Any], options: Mapping[str, Any]) -> str:
    return str(options.get(OPT_PROFILE) or data.get(CONF_PROFILE) or DEFAULT_PROFILE)


def scoring_from_entry(
    options: Mapping[str, Any], data: Mapping[str, Any] | None = None
) -> ScoringConfig:
    cfg = scoring_config_for(profile_name(data or {}, options))

    window_hours = int(options.get(OPT_WINDOW_HOURS, DEFAULT_WINDOW_HOURS))

    start = options.get(OPT_PREFERRED_START)
    end = options.get(OPT_PREFERRED_END)
    preferred = (int(start), int(end)) if start is not None and end is not None else None

    full_weights = dict(cfg.full_weights)
    overrides = {
        comp: float(options[f"{OPT_WEIGHT_PREFIX}{comp.value}"]) / 100.0
        for comp in Component
        if f"{OPT_WEIGHT_PREFIX}{comp.value}" in options
    }
    if overrides:
        full_weights.update(overrides)
        total = sum(full_weights.values())
        if total > 0:
            full_weights = {c: w / total for c, w in full_weights.items()}

    return replace(
        cfg,
        full_weights=full_weights,
        window_hours=window_hours,
        preferred_hours=preferred,
    )
