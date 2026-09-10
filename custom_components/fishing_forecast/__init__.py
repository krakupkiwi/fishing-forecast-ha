"""Fishing Forecast integration for Home Assistant.

Home Assistant imports are done inside the setup functions rather than at module
level so that importing ``custom_components.fishing_forecast.models`` (and the rest
of the pure scoring core) does not require Home Assistant to be installed. See
``docs/architecture.md``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import FishingForecastConfigEntry

PLATFORMS = ["sensor"]

CARD_URL = f"/{DOMAIN}/fishing-forecast-card.js"
CARD_PATH = Path(__file__).parent / "frontend" / "fishing-forecast-card.js"
_CARD_KEY = f"{DOMAIN}_card_registered"


async def async_setup_entry(hass: HomeAssistant, entry: FishingForecastConfigEntry) -> bool:
    """Set up a fishing-forecast location from a config entry."""

    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from .api.client import OpenMeteoClient
    from .coordinator import FishingForecastCoordinator
    from .feedback import async_register_feedback_service
    from .websocket import async_register_websockets

    client = OpenMeteoClient(async_get_clientsession(hass))
    coordinator = FishingForecastCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    async_register_websockets(hass)
    async_register_feedback_service(hass)
    await _async_register_card(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve the Lovelace card and add it as a dashboard resource (once).

    Best-effort: a failure here must not stop the integration from loading —
    the user can still add the resource manually (see docs/card.md).
    """

    if hass.data.get(_CARD_KEY):
        return
    hass.data[_CARD_KEY] = True

    try:
        from homeassistant.components.frontend import add_extra_js_url
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(CARD_PATH), cache_headers=False)]
        )
        # Load it as an ES module AND as a classic <script>. Some browsers
        # (seen on Firefox 155) don't register a custom element defined inside a
        # dynamic import(); the classic script works there. The card guards
        # against defining itself twice.
        add_extra_js_url(hass, CARD_URL)
        add_extra_js_url(hass, CARD_URL, es5=True)
    except Exception:  # card registration is optional; never block setup
        _LOGGER.warning(
            "Could not auto-register the Lovelace card; add %s as a dashboard "
            "resource manually if you want it",
            CARD_URL,
            exc_info=True,
        )


async def async_unload_entry(hass: HomeAssistant, entry: FishingForecastConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: FishingForecastConfigEntry) -> None:
    """Re-load when options (weights, window length, interval) change."""

    await hass.config_entries.async_reload(entry.entry_id)
