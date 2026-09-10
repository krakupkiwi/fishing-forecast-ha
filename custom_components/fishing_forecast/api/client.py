"""Async Open-Meteo HTTP client.

Thin wrapper over an ``aiohttp.ClientSession`` (Home Assistant passes its shared
session). Returns the raw JSON payloads; parsing lives in ``open_meteo_weather``
and ``open_meteo_marine``.
"""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from ..const import (
    HTTP_TIMEOUT_SECONDS,
    MARINE_EXTENDED_MODEL,
    MARINE_HOURLY_FIELDS_EXTENDED,
    MARINE_HOURLY_FIELDS_FINE,
    MARINE_URL,
    WEATHER_DAILY_FIELDS,
    WEATHER_HOURLY_FIELDS,
    WEATHER_URL,
)
from ._common import OpenMeteoError, raise_for_error


class OpenMeteoClient:
    """Fetches weather + marine forecasts from Open-Meteo (no API key)."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def _get(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        try:
            async with asyncio.timeout(HTTP_TIMEOUT_SECONDS):
                resp = await self._session.get(url, params=params)
                payload: dict[str, Any] = await resp.json()
        except (TimeoutError, aiohttp.ClientError) as err:
            raise OpenMeteoError(f"request to {url} failed: {err}") from err
        raise_for_error(payload)
        return payload

    async def async_get_weather(
        self, latitude: float, longitude: float, timezone: str, forecast_days: int
    ) -> dict[str, Any]:
        return await self._get(
            WEATHER_URL,
            {
                "latitude": f"{latitude}",
                "longitude": f"{longitude}",
                "hourly": ",".join(WEATHER_HOURLY_FIELDS),
                "daily": ",".join(WEATHER_DAILY_FIELDS),
                "timezone": timezone,
                "forecast_days": str(forecast_days),
                "wind_speed_unit": "kmh",
            },
        )

    async def async_get_marine(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        forecast_days: int,
        *,
        extended: bool = False,
    ) -> dict[str, Any]:
        params: dict[str, str] = {
            "latitude": f"{latitude}",
            "longitude": f"{longitude}",
            "timezone": timezone,
            "forecast_days": str(forecast_days),
            "cell_selection": "sea",
        }
        if extended:
            params["hourly"] = ",".join(MARINE_HOURLY_FIELDS_EXTENDED)
            params["models"] = MARINE_EXTENDED_MODEL
        else:
            params["hourly"] = ",".join(MARINE_HOURLY_FIELDS_FINE)
        return await self._get(MARINE_URL, params)
