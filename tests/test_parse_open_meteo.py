"""Open-Meteo JSON -> typed rows, and the best_match / gfswave merge.
docs/research.md §3, §6.
"""

from __future__ import annotations

from datetime import UTC

import pytest

from custom_components.fishing_forecast.api._common import OpenMeteoError
from custom_components.fishing_forecast.api.open_meteo_marine import parse_marine
from custom_components.fishing_forecast.api.open_meteo_weather import (
    parse_daily_astro,
    parse_weather,
)


def test_weather_timestamps_convert_to_utc(weather_payload: dict) -> None:
    hours = parse_weather(weather_payload)
    assert len(hours) == 384
    first = hours[0]
    # 00:00 Australia/Perth (+08) == 16:00 UTC the previous day
    assert first.time_utc.tzinfo is UTC
    assert first.time_utc.hour == 16
    assert (hours[1].time_utc - first.time_utc).total_seconds() == 3600
    assert first.wind_speed_kmh is not None
    assert first.pressure_msl_hpa is not None


def test_weather_error_body_raises() -> None:
    with pytest.raises(OpenMeteoError, match="bad thing"):
        parse_weather({"error": True, "reason": "bad thing"})


def test_daily_astro_parses_moon_fields(weather_payload: dict) -> None:
    days = parse_daily_astro(weather_payload)
    assert len(days) == 16
    assert days[0].sunrise_utc.tzinfo is UTC
    assert 0.0 <= days[0].moon_phase_fraction <= 1.0


def test_marine_merge_prefers_fine_then_falls_back_to_gfswave(
    marine_fine_payload: dict, marine_extended_payload: dict
) -> None:
    rows = parse_marine(marine_fine_payload, marine_extended_payload)
    assert len(rows) == 384

    day1 = rows[0]
    assert day1.has_fine_marine and day1.has_tide
    assert day1.sea_level_m is not None

    day16 = rows[-1]
    assert day16.swell_height_m is not None  # from gfswave
    assert not day16.has_fine_marine
    assert not day16.has_tide
    assert day16.sea_level_m is None


def test_marine_fine_only(marine_fine_payload: dict) -> None:
    rows = parse_marine(marine_fine_payload, None)
    assert any(r.has_tide for r in rows)
    # modelled tide only ever comes from the fine model
    assert all(r.has_fine_marine for r in rows if r.has_tide)
    # and the fine model runs out well before 16 days
    assert sum(1 for r in rows if r.has_tide) < 300


def test_marine_none_none() -> None:
    assert parse_marine(None, None) == []
