"""Websocket command exposing the full hourly forecast to the Lovelace card.

Entity attributes only carry the ~14-row daily summary; the ~336-row hourly series
is fetched on demand through ``fishing_forecast/hourly``.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
import voluptuous as vol

from .const import DOMAIN
from .coordinator import FishingForecastCoordinator
from .serialize import bundle_full

_REGISTERED_KEY = f"{DOMAIN}_ws_registered"


@callback
def async_register_websockets(hass: HomeAssistant) -> None:
    """Register once, regardless of how many locations are configured."""

    if hass.data.get(_REGISTERED_KEY):
        return
    hass.data[_REGISTERED_KEY] = True
    websocket_api.async_register_command(hass, ws_hourly)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "fishing_forecast/hourly",
        vol.Required("entry_id"): str,
    }
)
@callback
def ws_hourly(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is None or entry.domain != DOMAIN:
        connection.send_error(msg["id"], "not_found", "Unknown config entry")
        return

    coordinator: FishingForecastCoordinator | None = getattr(entry, "runtime_data", None)
    if coordinator is None or coordinator.data is None:
        connection.send_error(msg["id"], "not_ready", "Forecast not available yet")
        return

    connection.send_result(msg["id"], bundle_full(coordinator.data))
