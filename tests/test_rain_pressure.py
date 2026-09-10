"""Rain score (§8) and pressure trend/score (§9)."""

from __future__ import annotations

import pytest

from custom_components.fishing_forecast.const import default_scoring_config
from custom_components.fishing_forecast.models import PressureTrend
from custom_components.fishing_forecast.scoring.pressure import classify
from custom_components.fishing_forecast.scoring.pressure import score as pressure_score
from custom_components.fishing_forecast.scoring.rain import score as rain_score

CFG = default_scoring_config()


@pytest.mark.parametrize(
    ("mm_h", "expected"),
    [(0.0, 100), (0.5, 90), (1.0, 75), (2.0, 55), (5.0, 30), (10.0, 5), (25.0, 5)],
)
def test_rain_curve(mm_h: float, expected: float) -> None:
    assert rain_score(mm_h, CFG) == pytest.approx(expected)


def test_rain_none() -> None:
    assert rain_score(None, CFG) is None


@pytest.mark.parametrize(
    ("delta", "trend"),
    [
        (-5.0, PressureTrend.RAPIDLY_FALLING),
        (-2.0, PressureTrend.FALLING),
        (0.0, PressureTrend.STEADY),
        (2.0, PressureTrend.RISING),
        (5.0, PressureTrend.RAPIDLY_RISING),
    ],
)
def test_pressure_classify(delta: float, trend: PressureTrend) -> None:
    assert classify(delta, CFG)[0] is trend


def test_pressure_score_needs_both_samples() -> None:
    assert pressure_score(1015.0, None, CFG) == (None, None)
    value, trend = pressure_score(1012.0, 1015.0, CFG)
    assert trend is PressureTrend.FALLING
    assert value == pytest.approx(70)
