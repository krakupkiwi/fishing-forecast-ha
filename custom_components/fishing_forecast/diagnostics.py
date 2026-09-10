"""Config-entry diagnostics."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MARINE_LATITUDE,
    CONF_MARINE_LONGITUDE,
)
from .coordinator import FishingForecastConfigEntry
from .serialize import bundle_full

_REDACT = {CONF_LATITUDE, CONF_LONGITUDE, CONF_MARINE_LATITUDE, CONF_MARINE_LONGITUDE}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: FishingForecastConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    return {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), _REDACT),
            "options": dict(entry.options),
        },
        "location": {
            "id": coordinator.location.id,
            "name": coordinator.location.name,
            "coast_bearing": coordinator.location.coast_bearing,
            "timezone": coordinator.location.timezone,
        },
        "last_update_success": coordinator.last_update_success,
        "forecast": bundle_full(coordinator.data) if coordinator.data else None,
    }
