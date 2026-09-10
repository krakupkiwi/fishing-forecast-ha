"""Phase 1 guard tests: the committed fixtures still have the shape the research
in docs/research.md depends on, and the core models import cleanly with no
Home Assistant present.
"""

from __future__ import annotations

from custom_components.fishing_forecast.const import (
    DEFAULT_FULL_WEIGHTS,
    DEFAULT_OUTLOOK_WEIGHTS,
    default_scoring_config,
)
from custom_components.fishing_forecast.models import Rating, rating_for


def test_models_and_const_import_without_home_assistant() -> None:
    cfg = default_scoring_config()
    assert cfg.window_hours == 3
    assert abs(sum(DEFAULT_FULL_WEIGHTS.values()) - 1.0) < 1e-9
    assert abs(sum(DEFAULT_OUTLOOK_WEIGHTS.values()) - 1.0) < 1e-9


def test_rating_bands() -> None:
    assert rating_for(91) is Rating.EXCEPTIONAL
    assert rating_for(85) is Rating.EXCELLENT
    assert rating_for(70) is Rating.GOOD
    assert rating_for(60) is Rating.FAIR
    assert rating_for(55) is Rating.MARGINAL
    assert rating_for(10) is Rating.POOR
    assert rating_for(None) is Rating.UNKNOWN


def test_weather_fixture_shape(weather_payload: dict) -> None:
    assert weather_payload["timezone"] == "Australia/Perth"
    assert weather_payload["utc_offset_seconds"] == 28800
    hourly = weather_payload["hourly"]
    assert len(hourly["time"]) == 384  # 16 days
    for field in (
        "wind_speed_10m",
        "wind_direction_10m",
        "wind_gusts_10m",
        "precipitation",
        "pressure_msl",
        "cloud_cover",
    ):
        values = hourly[field]
        assert len(values) == 384
        assert all(v is not None for v in values), f"{field} has nulls"
    daily = weather_payload["daily"]
    assert set(daily) >= {"sunrise", "sunset", "moonrise", "moonset", "moon_phase"}
    assert weather_payload["daily_units"]["moon_phase"] == "fraction"


def test_marine_fine_fixture_has_partial_horizon_and_tide(marine_fine_payload: dict) -> None:
    hourly = marine_fine_payload["hourly"]
    assert len(hourly["time"]) == 384
    non_null = sum(1 for v in hourly["sea_level_height_msl"] if v is not None)
    # best_match tide (MeteoFrance SMOC) runs ~9.5 days, not the full 16.
    assert 200 < non_null < 260
    assert hourly["swell_wave_height"][0] is not None


def test_marine_extended_fixture_covers_full_horizon_but_no_tide(
    marine_extended_payload: dict,
) -> None:
    hourly = marine_extended_payload["hourly"]
    assert len(hourly["time"]) == 384
    assert all(v is not None for v in hourly["swell_wave_height"])
    assert "sea_level_height_msl" not in hourly  # gfswave carries no tide field
