"""Wind classification + score. docs/scoring.md §3."""

from __future__ import annotations

import pytest

from custom_components.fishing_forecast.const import default_scoring_config
from custom_components.fishing_forecast.models import WindClass
from custom_components.fishing_forecast.scoring.wind import classify, offshore_alignment, score

CFG = default_scoring_config()
COAST = 270.0  # Mindarie: sea is due west


def test_offshore_alignment() -> None:
    # coast_bearing 270 -> offshore wind comes from 90 (east)
    assert offshore_alignment(90, COAST) == pytest.approx(0)
    assert offshore_alignment(270, COAST) == pytest.approx(180)
    assert offshore_alignment(180, COAST) == pytest.approx(90)


@pytest.mark.parametrize(
    ("wind_from", "expected"),
    [
        (90, WindClass.OFFSHORE),
        (120, WindClass.CROSS_OFFSHORE),
        (180, WindClass.CROSS_SHORE),
        (240, WindClass.CROSS_ONSHORE),
        (270, WindClass.ONSHORE),
    ],
)
def test_classify(wind_from: float, expected: WindClass) -> None:
    assert classify(wind_from, COAST)[0] is expected


@pytest.mark.parametrize(
    ("speed", "wind_from", "lo", "hi"),
    [
        (8, 90, 95, 100),  # light offshore easterly -> near perfect
        (30, 270, 0, 12),  # 30 km/h onshore westerly -> very poor (spec: ~5)
        (35, 90, 0, 8),  # offshore gale still not fishable
        (12, 270, 38, 58),  # light onshore -> marginal
        (0, 270, 90, 100),  # dead calm regardless of direction
    ],
)
def test_score_ranges(speed: float, wind_from: float, lo: float, hi: float) -> None:
    value = score(speed, wind_from, speed * 1.3, COAST, CFG)
    assert value is not None
    assert lo <= value <= hi


def test_offshore_beats_onshore_at_equal_speed() -> None:
    off = score(15, 90, 20, COAST, CFG)
    on = score(15, 270, 20, COAST, CFG)
    assert off is not None and on is not None
    assert off > on + 20


def test_gust_penalty_applies() -> None:
    steady = score(18, 90, 20, COAST, CFG)
    gusty = score(18, 90, 40, COAST, CFG)  # gust 2.2x, > 25
    assert gusty is not None and steady is not None
    assert gusty < steady


def test_none_when_missing() -> None:
    assert score(None, 90, 10, COAST, CFG) is None
    assert score(10, None, 10, COAST, CFG) is None
