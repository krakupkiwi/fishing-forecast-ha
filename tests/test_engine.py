"""Weight renormalisation + aggregate score — Phase 2 skeleton (docs/scoring.md §1, §10)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Phase 2: scoring/engine.py not implemented")


def test_renormalise_drops_missing_and_sums_to_one() -> None:
    from custom_components.fishing_forecast.const import default_scoring_config
    from custom_components.fishing_forecast.models import Component
    from custom_components.fishing_forecast.scoring.engine import renormalise

    cfg = default_scoring_config()
    present = {Component.WIND, Component.SOLUNAR, Component.SUN, Component.RAIN, Component.PRESSURE}
    used = renormalise(cfg.full_weights, present)
    assert set(used) == present
    assert abs(sum(used.values()) - 1.0) < 1e-9
    # wind keeps its share of the surviving weight
    assert used[Component.WIND] == pytest.approx(0.30 / 0.65, rel=1e-6)


def test_all_components_missing_gives_none_score() -> None:
    # HourlyScore.score must be None, rating UNKNOWN, and the hour excluded from
    # window / daily calculations. Implemented in Phase 2.
    pytest.skip("Phase 2")
