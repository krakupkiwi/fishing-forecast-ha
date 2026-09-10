"""Weight renormalisation + aggregate hourly score. docs/scoring.md §1, §10."""

from __future__ import annotations

from typing import Any

import pytest

from custom_components.fishing_forecast.astronomy.solunar import periods as make_periods
from custom_components.fishing_forecast.const import default_scoring_config
from custom_components.fishing_forecast.models import (
    AstroDay,
    Component,
    Confidence,
    LocationConfig,
    MarineHour,
    Rating,
    TideDirection,
    TideExtreme,
    TideExtremePoint,
    TideState,
    WeatherHour,
)
from custom_components.fishing_forecast.scoring.engine import renormalise, score_hour
from tests.conftest import utc

CFG = default_scoring_config()

MINDARIE = LocationConfig(
    id="mindarie",
    name="Mindarie",
    latitude=-31.69,
    longitude=115.70,
    marine_latitude=-31.72,
    marine_longitude=115.55,
    coast_bearing=270.0,
)

ASTRO = AstroDay(
    date_local=utc(2026, 9, 13).date(),
    sunrise_utc=utc(2026, 9, 12, 22, 20),
    sunset_utc=utc(2026, 9, 13, 10, 5),
    moon_upper_transit_utc=utc(2026, 9, 13, 8),
    moon_lower_transit_utc=utc(2026, 9, 13, 20),
    moonrise_utc=utc(2026, 9, 13, 2),
    moonset_utc=utc(2026, 9, 13, 14),
    moon_phase_fraction=0.3,
)


def weather(**kw: Any) -> WeatherHour:
    base: dict[str, Any] = {
        "time_utc": utc(2026, 9, 13, 0),
        "wind_speed_kmh": 10.0,
        "wind_direction_deg": 90.0,
        "wind_gust_kmh": 15.0,
        "precip_mm_h": 0.0,
        "rain_mm_h": 0.0,
        "showers_mm_h": 0.0,
        "cloud_cover_pct": 10.0,
        "pressure_msl_hpa": 1018.0,
    }
    base.update(kw)
    return WeatherHour(**base)


def fine_marine() -> MarineHour:
    return MarineHour(
        time_utc=utc(2026, 9, 13, 0),
        swell_height_m=0.9,
        swell_period_s=13.0,
        swell_direction_deg=245.0,
        sea_level_m=0.3,
        has_fine_marine=True,
        has_tide=True,
    )


def tide_state() -> TideState:
    return TideState(
        time_utc=utc(2026, 9, 13, 0),
        height_m=0.3,
        direction=TideDirection.RISING,
        next_extreme=TideExtremePoint(utc(2026, 9, 13, 1), TideExtreme.HIGH, 0.5),
        minutes_to_next_extreme=60.0,
        last_extreme=TideExtremePoint(utc(2026, 9, 12, 19), TideExtreme.LOW, -0.4),
        minutes_since_last_extreme=300.0,
        rate_m_per_h=0.1,
    )


def periods() -> list:
    return make_periods([ASTRO], CFG)


def test_renormalise_drops_missing_and_sums_to_one() -> None:
    present = {Component.WIND, Component.SOLUNAR, Component.SUN, Component.RAIN, Component.PRESSURE}
    used = renormalise(CFG.full_weights, present)
    assert set(used) == present
    assert sum(used.values()) == pytest.approx(1.0)
    assert used[Component.WIND] == pytest.approx(0.30 / 0.65)


def test_renormalise_empty() -> None:
    assert renormalise(CFG.full_weights, set()) == {}


def test_full_confidence_uses_full_weights() -> None:
    hs = score_hour(MINDARIE, weather(), fine_marine(), tide_state(), periods(), ASTRO, 1017.0, CFG)
    assert hs.confidence is Confidence.FULL
    assert set(hs.weights_used) == set(Component)
    assert hs.score is not None
    assert 0 <= hs.score <= 100


def test_outlook_when_no_marine() -> None:
    hs = score_hour(MINDARIE, weather(), None, None, periods(), ASTRO, 1017.0, CFG)
    assert hs.confidence is Confidence.OUTLOOK
    assert Component.SWELL not in hs.weights_used
    assert Component.TIDE not in hs.weights_used
    assert sum(hs.weights_used.values()) == pytest.approx(1.0)


def test_marine_present_but_no_tide_is_outlook() -> None:
    partial = MarineHour(
        time_utc=utc(2026, 9, 13, 0),
        swell_height_m=1.0,
        swell_period_s=12.0,
        has_fine_marine=True,
        has_tide=False,
    )
    hs = score_hour(MINDARIE, weather(), partial, None, periods(), ASTRO, 1017.0, CFG)
    assert hs.confidence is Confidence.OUTLOOK
    # swell still contributes even though the weight set is the outlook one
    assert hs.components.swell is not None


def test_all_components_missing_gives_none_score() -> None:
    blank = WeatherHour(
        time_utc=utc(2026, 9, 13, 0),
        wind_speed_kmh=None,
        wind_direction_deg=None,
        wind_gust_kmh=None,
        precip_mm_h=None,
        rain_mm_h=None,
        showers_mm_h=None,
        cloud_cover_pct=None,
        pressure_msl_hpa=None,
    )
    hs = score_hour(MINDARIE, blank, None, None, [], None, None, CFG)
    assert hs.score is None
    assert hs.rating is Rating.UNKNOWN
    assert hs.weights_used == {}
