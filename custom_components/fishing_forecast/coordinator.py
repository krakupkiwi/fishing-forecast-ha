"""DataUpdateCoordinator: fetch Open-Meteo, run the core engine, expose a bundle.

The coordinator owns all I/O and the executor hop for ``ephem``. The scoring core
(``core.build_forecast``) stays pure and synchronous.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from functools import partial
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api._common import OpenMeteoError
from .api.client import OpenMeteoClient
from .const import DOMAIN
from .core import build_forecast
from .entry_data import (
    forecast_days,
    location_from_entry,
    profile_name,
    scoring_from_entry,
    update_minutes,
)
from .models import ForecastBundle

_LOGGER = logging.getLogger(__name__)

type FishingForecastConfigEntry = ConfigEntry[FishingForecastCoordinator]


class FishingForecastCoordinator(DataUpdateCoordinator[ForecastBundle]):
    """Polls Open-Meteo and produces a :class:`ForecastBundle` per location."""

    config_entry: FishingForecastConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: FishingForecastConfigEntry,
        client: OpenMeteoClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {entry.title}",
            config_entry=entry,
            update_interval=timedelta(minutes=update_minutes(entry.options)),
            always_update=False,
        )
        self._client = client
        self.location = location_from_entry(entry.data, entry.options)
        self.profile = profile_name(entry.data, entry.options)
        self._forecast_days = forecast_days(entry.data)

    async def _async_update_data(self) -> ForecastBundle:
        loc = self.location
        days = self._forecast_days

        weather_task = self._client.async_get_weather(
            loc.latitude, loc.longitude, loc.timezone, min(days + 2, 16)
        )
        marine_fine_task = self._client.async_get_marine(
            loc.marine_latitude, loc.marine_longitude, loc.timezone, 16
        )
        marine_ext_task = self._client.async_get_marine(
            loc.marine_latitude, loc.marine_longitude, loc.timezone, 16, extended=True
        )
        weather, marine_fine, marine_ext = await asyncio.gather(
            weather_task, marine_fine_task, marine_ext_task, return_exceptions=True
        )

        if isinstance(weather, BaseException):
            # No weather => nothing to score. Coordinator keeps the last good bundle.
            raise UpdateFailed(f"weather fetch failed: {weather}") from weather

        marine_fine_payload = _payload_or_none(marine_fine, "marine (fine)")
        marine_ext_payload = _payload_or_none(marine_ext, "marine (extended)")

        scoring = scoring_from_entry(self.config_entry.options, self.config_entry.data)
        try:
            return await self.hass.async_add_executor_job(
                partial(
                    build_forecast,
                    loc,
                    weather,
                    marine_fine_payload,
                    marine_ext_payload,
                    scoring,
                    days=days,
                    now_utc=datetime.now(UTC),
                )
            )
        except OpenMeteoError as err:
            raise UpdateFailed(f"forecast build failed: {err}") from err


def _payload_or_none(result: Any, label: str) -> dict[str, Any] | None:
    if isinstance(result, BaseException):
        _LOGGER.warning("%s fetch failed, continuing without it: %s", label, result)
        return None
    return result
