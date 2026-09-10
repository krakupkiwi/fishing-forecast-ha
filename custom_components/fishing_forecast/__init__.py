"""Fishing Forecast integration for Home Assistant.

Phase 3 will implement setup here:

    async def async_setup_entry(hass, entry) -> bool:
        session = async_get_clientsession(hass)
        client = OpenMeteoClient(session)
        coordinator = FishingForecastCoordinator(hass, entry, client)
        await coordinator.async_config_entry_first_refresh()
        entry.runtime_data = coordinator
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        return True

    async def async_unload_entry(hass, entry) -> bool:
        return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

Not implemented yet — see docs/research.md §5 and docs/architecture.md.
"""

from __future__ import annotations

PLATFORMS: list[str] = ["sensor"]
