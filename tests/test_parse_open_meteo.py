"""Open-Meteo JSON -> typed rows — Phase 2 skeleton (docs/research.md §6, §8.1)."""

from __future__ import annotations

from datetime import UTC

import pytest

pytestmark = pytest.mark.skip(reason="Phase 2: api parsing not implemented")


def test_weather_timestamps_convert_to_utc(weather_payload: dict) -> None:
    from custom_components.fishing_forecast.api.open_meteo_weather import parse_weather

    hours, _days = parse_weather(weather_payload)
    # first row is 2026-xx-xxT00:00 Australia/Perth == previous day 16:00 UTC
    assert hours[0].time_utc.tzinfo is UTC
    assert hours[0].time_utc.hour == 16
    assert len(hours) == 384


def test_marine_merge_prefers_fine_then_falls_back_to_gfswave(
    marine_fine_payload: dict, marine_extended_payload: dict
) -> None:
    from custom_components.fishing_forecast.api.open_meteo_marine import parse_marine

    rows = parse_marine(marine_fine_payload, marine_extended_payload)
    assert len(rows) == 384
    assert rows[0].has_fine_marine and rows[0].has_tide  # day 1: best_match
    assert rows[-1].swell_height_m is not None  # day 16: gfswave
    assert not rows[-1].has_fine_marine and not rows[-1].has_tide
