"""Dawn / dusk score. docs/scoring.md §7."""

from __future__ import annotations

from datetime import timedelta

import pytest

from custom_components.fishing_forecast.const import default_scoring_config
from custom_components.fishing_forecast.models import AstroDay
from custom_components.fishing_forecast.scoring.sunlight import score
from tests.conftest import utc

CFG = default_scoring_config()

_DAY = AstroDay(
    date_local=utc(2026, 9, 13).date(),
    sunrise_utc=utc(2026, 9, 12, 22, 20),  # ~06:20 Perth
    sunset_utc=utc(2026, 9, 13, 10, 5),  # ~18:05 Perth
    dawn_utc=None,
    dusk_utc=None,
)


def test_peak_at_events() -> None:
    assert score(_DAY.sunrise_utc, _DAY, CFG) == pytest.approx(100)
    assert score(_DAY.sunset_utc, _DAY, CFG) == pytest.approx(100)


def test_base_in_the_middle_of_the_day() -> None:
    midday = _DAY.sunrise_utc + timedelta(hours=6)
    assert score(midday, _DAY, CFG) == pytest.approx(float(CFG.sun["base"]))


def test_taper_is_monotonic_away_from_sunrise() -> None:
    at = _DAY.sunrise_utc
    a = score(at + timedelta(minutes=30), _DAY, CFG)
    b = score(at + timedelta(minutes=90), _DAY, CFG)
    c = score(at + timedelta(minutes=140), _DAY, CFG)
    assert a > b > c


def test_none_without_sun_times() -> None:
    empty = AstroDay(date_local=_DAY.date_local, sunrise_utc=None, sunset_utc=None)
    assert score(_DAY.sunrise_utc, empty, CFG) is None
