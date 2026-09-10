"""Tide extrema detection + score. docs/scoring.md §5."""

from __future__ import annotations

from datetime import timedelta
import itertools
import math

import pytest

from custom_components.fishing_forecast.const import default_scoring_config
from custom_components.fishing_forecast.models import (
    TideDirection,
    TideExtreme,
    TideExtremePoint,
    TideSample,
    TideState,
)
from custom_components.fishing_forecast.scoring.tide import derive, find_extrema, score
from tests.conftest import utc

CFG = default_scoring_config()


def _sine_series(hours: int, period_h: float = 12.4, amp: float = 0.4) -> list[TideSample]:
    start = utc(2026, 9, 13, 0)
    return [
        TideSample(start + timedelta(hours=i), amp * math.sin(2 * math.pi * i / period_h))
        for i in range(hours)
    ]


def test_find_extrema_on_clean_semidiurnal() -> None:
    extrema = find_extrema(_sine_series(48), CFG)
    # ~2 highs + ~2 lows per 24 h over 48 h -> 7-8 turning points
    assert 6 <= len(extrema) <= 9
    kinds = [e.kind for e in extrema]
    # strictly alternating
    assert all(a is not b for a, b in itertools.pairwise(kinds))


def test_flat_series_yields_no_extrema() -> None:
    flat = [TideSample(utc(2026, 9, 13, i), 0.5) for i in range(24)]
    assert find_extrema(flat, CFG) == []


def test_low_prominence_noise_is_rejected() -> None:
    # semidiurnal + tiny 1 cm ripple -> ripple must not create extra turning points
    base = _sine_series(48)
    noisy = [
        TideSample(s.time_utc, s.height_m + 0.01 * math.sin(2 * math.pi * i / 3))
        for i, s in enumerate(base)
    ]
    assert len(find_extrema(noisy, CFG)) <= len(find_extrema(base, CFG)) + 1


def test_derive_direction_matches_slope() -> None:
    states = derive(_sine_series(48), CFG)
    rising = [s for s in states if s.direction is TideDirection.RISING and s.rate_m_per_h]
    assert all(s.rate_m_per_h > -0.02 for s in rising)


def test_derive_none_when_height_missing() -> None:
    samples = _sine_series(12) + [TideSample(utc(2026, 9, 13, 12 + i), None) for i in range(6)]
    states = derive(samples, CFG)
    assert states[-1].direction is None
    assert states[-1].height_m is None


def _high() -> TideExtremePoint:
    return TideExtremePoint(utc(2026, 9, 13, 12), TideExtreme.HIGH, 0.5)


def _low() -> TideExtremePoint:
    return TideExtremePoint(utc(2026, 9, 13, 12), TideExtreme.LOW, -0.5)


def _state(
    direction: TideDirection,
    *,
    next_pt: TideExtremePoint | None = None,
    mins_to: float | None = None,
    last_pt: TideExtremePoint | None = None,
    mins_since: float | None = None,
) -> TideState:
    return TideState(
        time_utc=utc(2026, 9, 13, 9),
        height_m=0.1,
        direction=direction,
        next_extreme=next_pt,
        minutes_to_next_extreme=mins_to,
        last_extreme=last_pt,
        minutes_since_last_extreme=mins_since,
        rate_m_per_h=0.05,
    )


def test_score_peaks_one_hour_before_high() -> None:
    one_before = score(_state(TideDirection.RISING, next_pt=_high(), mins_to=60), CFG)
    two_before = score(_state(TideDirection.RISING, next_pt=_high(), mins_to=120), CFG)
    assert one_before == pytest.approx(100)
    assert two_before == pytest.approx(90)


def test_score_low_and_generic() -> None:
    at_low = _state(TideDirection.FALLING, next_pt=_low(), mins_to=20)
    assert score(at_low, CFG) == pytest.approx(float(CFG.tide["at_low_score"]))

    early_rise = _state(
        TideDirection.RISING,
        last_pt=TideExtremePoint(utc(2026, 9, 13, 8), TideExtreme.LOW, -0.5),
        mins_since=45,
    )
    assert score(early_rise, CFG) == pytest.approx(float(CFG.tide["early_rise_score"]))


def test_score_none_when_unscoreable() -> None:
    unknown = TideState(utc(2026, 9, 13, 9), 0.1, None, None, None, None, None, None)
    assert score(unknown, CFG) is None
