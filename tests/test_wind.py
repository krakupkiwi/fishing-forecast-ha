"""Wind classification + score — Phase 2 skeleton (see docs/scoring.md §3)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Phase 2: scoring/wind.py not implemented")


@pytest.mark.parametrize(
    ("speed", "wind_from", "expected_min", "expected_max"),
    [
        (8, 90, 95, 100),  # light easterly = offshore on a 270 coast -> near perfect
        (30, 270, 0, 15),  # 30 km/h onshore westerly -> very poor
        (35, 90, 0, 10),  # offshore gale still not fishable
        (12, 270, 25, 45),  # moderate onshore -> marginal
    ],
)
def test_wind_score_ranges(
    speed: float, wind_from: float, expected_min: float, expected_max: float
) -> None:
    from custom_components.fishing_forecast.const import default_scoring_config
    from custom_components.fishing_forecast.scoring.wind import score

    value = score(
        speed, wind_from, speed * 1.3, coast_bearing_deg=270, cfg=default_scoring_config()
    )
    assert value is not None
    assert expected_min <= value <= expected_max


def test_wind_score_none_when_speed_missing() -> None:
    from custom_components.fishing_forecast.const import default_scoring_config
    from custom_components.fishing_forecast.scoring.wind import score

    assert score(None, 90, None, 270, default_scoring_config()) is None
