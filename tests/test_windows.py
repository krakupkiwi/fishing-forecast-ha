"""Rolling best-window selection — Phase 2 skeleton (see docs/scoring.md §11).

The spec worked example, which must pass once scoring/windows.py is implemented:

    15:00 72  16:00 81  17:00 91  18:00 94  19:00 88  20:00 73
    -> best window 17:00-20:00 @ 91  (triangular centre weighting [1, 1.3, 1])
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Phase 2: scoring/windows.py not implemented")


def test_spec_worked_example() -> None:
    from custom_components.fishing_forecast.const import default_scoring_config
    from custom_components.fishing_forecast.scoring.windows import best_windows

    cfg = default_scoring_config()
    windows = best_windows(_hourly([72, 81, 91, 94, 88, 73], start_hour=15), cfg)
    best = windows[0]
    assert best.start_utc.hour == 17
    assert best.end_utc.hour == 20  # exclusive boundary
    assert round(best.score) == 91


def _hourly(scores: list[float], start_hour: int):
    raise NotImplementedError("Phase 2 helper")
