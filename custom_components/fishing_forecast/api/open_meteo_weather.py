"""Open-Meteo weather parsing (see docs/research.md §2).

Endpoint (Phase 3 wires the HTTP call; this module is the pure parser):

    GET https://api.open-meteo.com/v1/forecast
        hourly = const.WEATHER_HOURLY_FIELDS
        daily  = const.WEATHER_DAILY_FIELDS
        timezone = <location tz>, forecast_days = 16, wind_speed_unit = kmh
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from ..models import WeatherHour
from ..util import to_utc
from ._common import daily_rows, hourly_rows, opt_float, opt_int, raise_for_error


@dataclass(frozen=True, slots=True)
class OpenMeteoDailyAstro:
    """The API's own sun/moon fields — kept only as a cross-check for ephem."""

    date_local: date
    sunrise_utc: Any
    sunset_utc: Any
    moonrise_utc: Any
    moonset_utc: Any
    moon_phase_fraction: float | None


def parse_weather(payload: dict[str, Any]) -> list[WeatherHour]:
    rows: list[WeatherHour] = []
    for instant, f in hourly_rows(payload):
        rows.append(
            WeatherHour(
                time_utc=instant,
                wind_speed_kmh=opt_float(f.get("wind_speed_10m")),
                wind_direction_deg=opt_float(f.get("wind_direction_10m")),
                wind_gust_kmh=opt_float(f.get("wind_gusts_10m")),
                precip_mm_h=opt_float(f.get("precipitation")),
                rain_mm_h=opt_float(f.get("rain")),
                showers_mm_h=opt_float(f.get("showers")),
                cloud_cover_pct=opt_float(f.get("cloud_cover")),
                pressure_msl_hpa=opt_float(f.get("pressure_msl")),
                air_temp_c=opt_float(f.get("temperature_2m")),
                weather_code=opt_int(f.get("weather_code")),
            )
        )
    return rows


def parse_daily_astro(payload: dict[str, Any]) -> list[OpenMeteoDailyAstro]:
    raise_for_error(payload)
    offset = int(payload.get("utc_offset_seconds", 0))

    def _t(value: Any) -> datetime | None:
        return None if value is None else to_utc(datetime.fromisoformat(value), offset)

    out: list[OpenMeteoDailyAstro] = []
    for day, f in daily_rows(payload):
        out.append(
            OpenMeteoDailyAstro(
                date_local=date.fromisoformat(day),
                sunrise_utc=_t(f.get("sunrise")),
                sunset_utc=_t(f.get("sunset")),
                moonrise_utc=_t(f.get("moonrise")),
                moonset_utc=_t(f.get("moonset")),
                moon_phase_fraction=opt_float(f.get("moon_phase")),
            )
        )
    return out
