"""Swell score. docs/scoring.md §4."""

from __future__ import annotations

import pytest

from custom_components.fishing_forecast.const import default_scoring_config
from custom_components.fishing_forecast.scoring.swell import effective_height, score

CFG = default_scoring_config()


def test_effective_height_period_scaling() -> None:
    # 10 s is neutral; long period inflates, short period deflates.
    assert effective_height(1.0, 10, CFG) == pytest.approx(1.0)
    assert effective_height(1.0, 16, CFG) > 1.0
    assert effective_height(1.0, 6, CFG) < 1.0
    # clamped
    assert effective_height(1.0, 100, CFG) == pytest.approx(1.4)


def test_favourable_band_scores_high(mindarie) -> None:
    assert score(0.9, 13, 245, mindarie, CFG) >= 95


def test_flat_is_penalised_but_not_zero(mindarie) -> None:
    value = score(0.1, 12, 245, mindarie, CFG)
    assert 50 <= value <= 75


def test_big_dangerous_swell_capped(mindarie) -> None:
    value = score(3.5, 14, 245, mindarie, CFG)
    assert value <= float(CFG.swell["over_safe_cap"])


def test_location_max_safe_override(mindarie) -> None:
    from dataclasses import replace

    strict = replace(mindarie, max_safe_swell=1.0)
    assert score(1.6, 13, 245, strict, CFG) <= float(CFG.swell["over_safe_cap"])


def test_none_when_height_missing(mindarie) -> None:
    assert score(None, 13, 245, mindarie, CFG) is None


def test_no_period_still_scores(mindarie) -> None:
    assert score(1.0, None, None, mindarie, CFG) == pytest.approx(100, abs=1)
