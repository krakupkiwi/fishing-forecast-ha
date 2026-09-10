"""Harmonic tide model (Phase 6, docs/tide.md)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from custom_components.fishing_forecast.models import TideSample
from custom_components.fishing_forecast.tide_harmonic import (
    FREMANTLE,
    extend_tide_samples,
    resolve_station,
)
from tests.conftest import utc


def test_perth_is_diurnal_dominant() -> None:
    amps = {c.name: c.amp_m for c in FREMANTLE.constituents}
    assert amps["K1"] + amps["O1"] > 2 * (amps["M2"] + amps["S2"])


def test_prediction_has_realistic_range_and_period() -> None:
    start = utc(2026, 3, 1)
    heights = [FREMANTLE.height(start + timedelta(hours=h)) for h in range(24 * 30)]
    span = max(heights) - min(heights)
    assert 0.3 < span < 1.6  # Perth micro-tidal, plus the seasonal term
    # at least ~25 turning points over 30 days (roughly diurnal)
    turns = sum(
        1
        for a, b, c in zip(heights, heights[1:], heights[2:], strict=False)
        if (b - a) * (c - b) < 0
    )
    assert 25 <= turns <= 90


def test_resolve_station() -> None:
    assert resolve_station(None, -31.69, 115.70) is FREMANTLE  # Mindarie -> Fremantle
    assert resolve_station("fremantle", 0, 0) is FREMANTLE  # explicit key
    assert resolve_station("none", -31.69, 115.70) is None  # disabled
    assert resolve_station(None, -12.46, 130.84) is None  # Darwin -> out of range


def test_extend_fills_only_the_gaps_and_joins_continuously() -> None:
    start = utc(2026, 9, 10)
    real = [TideSample(start + timedelta(hours=h), 0.5 + 0.01 * h) for h in range(6)]
    gap = [TideSample(start + timedelta(hours=6 + h), None) for h in range(6)]
    out = extend_tide_samples([*real, *gap], FREMANTLE)

    assert [s.height_m for s in out[:6]] == [s.height_m for s in real]  # untouched
    assert all(s.height_m is not None for s in out)  # gaps filled
    # continuity at the seam: no big jump between the last real and first filled
    assert abs(out[6].height_m - out[5].height_m) < 0.25


def test_extend_is_a_noop_without_a_station() -> None:
    samples = [TideSample(utc(2026, 9, 10, h), None) for h in range(4)]
    assert extend_tide_samples(samples, None) is samples


def test_predicts_far_into_the_future() -> None:
    # harmonic model has no horizon, unlike the modelled tide
    near = FREMANTLE.height(utc(2026, 9, 10, 12))
    far = FREMANTLE.height(utc(2030, 9, 10, 12))
    assert isinstance(near, float) and isinstance(far, float)
    assert near != pytest.approx(far)
