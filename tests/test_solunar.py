"""Solunar period derivation (astronomy/solunar.py) + score (scoring/solunar.py).
docs/scoring.md §6.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from custom_components.fishing_forecast.astronomy.solunar import periods
from custom_components.fishing_forecast.const import default_scoring_config
from custom_components.fishing_forecast.models import AstroDay, SolunarKind
from custom_components.fishing_forecast.scoring.solunar import score
from tests.conftest import utc

CFG = default_scoring_config()

_DAY = AstroDay(
    date_local=utc(2026, 9, 13).date(),
    sunrise_utc=utc(2026, 9, 12, 22, 20),
    sunset_utc=utc(2026, 9, 13, 10, 5),
    moonrise_utc=utc(2026, 9, 13, 2, 0),
    moonset_utc=utc(2026, 9, 13, 14, 0),
    moon_upper_transit_utc=utc(2026, 9, 13, 8, 0),
    moon_lower_transit_utc=utc(2026, 9, 13, 20, 0),
    moon_phase_fraction=0.5,  # full -> phase bonus
    moon_illumination=1.0,
)


def test_periods_widths_and_centres() -> None:
    result = periods([_DAY], CFG)
    majors = [p for p in result if p.kind is SolunarKind.MAJOR]
    minors = [p for p in result if p.kind is SolunarKind.MINOR]
    assert len(majors) == 2
    assert len(minors) == 2
    for p in majors:
        assert (p.end_utc - p.start_utc) == timedelta(minutes=120)
        assert p.centre_utc == p.start_utc + timedelta(minutes=60)
    for p in minors:
        assert (p.end_utc - p.start_utc) == timedelta(minutes=60)


def test_periods_dedupe_across_days() -> None:
    result = periods([_DAY, _DAY], CFG)
    assert len(result) == 4  # not 8


def test_score_inside_major_is_100_minus_bonus_clamp() -> None:
    result = periods([_DAY], CFG)
    value, inside_major, inside_minor = score(utc(2026, 9, 13, 8, 0), result, _DAY, CFG)
    assert inside_major and not inside_minor
    assert value == pytest.approx(100)  # 100 + phase bonus, clamped


def test_score_near_major_edge() -> None:
    result = periods([_DAY], CFG)
    # major is 07:00-09:00; 09:20 is within the 30-min grace
    value, _, _ = score(utc(2026, 9, 13, 9, 20), result, _DAY, CFG)
    assert value == pytest.approx(
        float(CFG.solunar["near_major"]) + float(CFG.solunar["phase_bonus"])
    )


def test_score_baseline_far_from_everything() -> None:
    quarter_day = AstroDay(
        date_local=_DAY.date_local,
        sunrise_utc=_DAY.sunrise_utc,
        sunset_utc=_DAY.sunset_utc,
        moon_upper_transit_utc=utc(2026, 9, 13, 8, 0),
        moon_lower_transit_utc=utc(2026, 9, 13, 20, 0),
        moonrise_utc=utc(2026, 9, 13, 2, 0),
        moonset_utc=utc(2026, 9, 13, 14, 0),
        moon_phase_fraction=0.25,  # no phase bonus
    )
    result = periods([quarter_day], CFG)
    value, _, _ = score(utc(2026, 9, 13, 17, 0), result, quarter_day, CFG)
    assert value == pytest.approx(float(CFG.solunar["baseline"]))
