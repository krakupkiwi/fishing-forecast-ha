"""Open-Meteo weather client + parser — Phase 3 (parsing lands in Phase 2/3).

Endpoint (verified 2026-09-10, see docs/research.md §2):

    GET https://api.open-meteo.com/v1/forecast
        latitude, longitude
        hourly   = const.WEATHER_HOURLY_FIELDS
        daily    = const.WEATHER_DAILY_FIELDS
        timezone = <location tz>          # response is local wall-time
        forecast_days = 16                # 0..16, 17 -> HTTP 400
        wind_speed_unit = kmh

Response timestamps are naive local ISO ("2026-09-10T00:00"); combine with
``utc_offset_seconds`` from the payload, then convert to UTC. Error body:
``{"error": true, "reason": "..."}`` with HTTP 400.
"""

from __future__ import annotations

from typing import Any

from ..models import AstroDay, WeatherHour


def parse_weather(payload: dict[str, Any]) -> tuple[list[WeatherHour], list[AstroDay]]:
    """Parse an Open-Meteo forecast payload into typed rows. Not implemented (Phase 2)."""

    raise NotImplementedError("Phase 2: weather parsing + tz normalisation")
