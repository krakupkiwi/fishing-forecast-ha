"""Angle math, interpolation and timezone helpers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from custom_components.fishing_forecast.util import (
    angular_gap,
    clamp,
    interpolate,
    local_date_of,
    local_hour_of,
    to_utc,
    wrap180,
)
from tests.conftest import utc


@pytest.mark.parametrize(
    ("deg", "expected"),
    [(0, 0), (10, 10), (190, -170), (350, -10), (-350, 10), (180, 180), (-180, 180)],
)
def test_wrap180(deg: float, expected: float) -> None:
    assert wrap180(deg) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [(10, 350, 20), (0, 180, 180), (90, 95, 5), (359, 1, 2)],
)
def test_angular_gap(a: float, b: float, expected: float) -> None:
    assert angular_gap(a, b) == pytest.approx(expected)


def test_clamp() -> None:
    assert clamp(5, 0, 10) == 5
    assert clamp(-1, 0, 10) == 0
    assert clamp(11, 0, 10) == 10


def test_interpolate_linear_and_clamped() -> None:
    curve = [(0, 100), (10, 0)]
    assert interpolate(curve, -5) == 100  # clamped low
    assert interpolate(curve, 0) == 100
    assert interpolate(curve, 5) == pytest.approx(50)
    assert interpolate(curve, 10) == 0
    assert interpolate(curve, 99) == 0  # clamped high


def test_interpolate_multi_segment() -> None:
    curve = [(0, 0), (8, 100), (15, 80), (30, 10)]
    assert interpolate(curve, 4) == pytest.approx(50)
    assert interpolate(curve, 11.5) == pytest.approx(90)


def test_to_utc_from_perth_offset() -> None:
    # 00:00 local at +08:00 == previous day 16:00 UTC
    got = to_utc(datetime(2026, 9, 13, 0, 0), 28800)  # noqa: DTZ001 - API returns naive
    assert got == utc(2026, 9, 12, 16, 0)
    assert got.tzinfo is UTC


def test_local_date_and_hour_perth() -> None:
    instant = utc(2026, 9, 12, 16, 0)  # 00:00 Perth on the 13th
    assert local_date_of(instant, "Australia/Perth").isoformat() == "2026-09-13"
    assert local_hour_of(instant, "Australia/Perth") == 0
