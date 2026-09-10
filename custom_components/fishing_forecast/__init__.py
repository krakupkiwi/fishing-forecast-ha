"""Fishing Forecast integration for Home Assistant.

Home Assistant imports are done inside the setup functions rather than at module
level so that importing ``custom_components.fishing_forecast.models`` (and the rest
of the pure scoring core) does not require Home Assistant to be installed. See
``docs/architecture.md``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import FishingForecastConfigEntry

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: FishingForecastConfigEntry) -> bool:
    """Set up a fishing-forecast location from a config entry."""

    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from .api.client import OpenMeteoClient
    from .coordinator import FishingForecastCoordinator
    from .websocket import async_register_websockets

    client = OpenMeteoClient(async_get_clientsession(hass))
    coordinator = FishingForecastCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    async_register_websockets(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FishingForecastConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: FishingForecastConfigEntry) -> None:
    """Re-load when options (weights, window length, interval) change."""

    await hass.config_entries.async_reload(entry.entry_id)
