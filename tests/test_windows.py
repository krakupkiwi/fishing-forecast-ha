"""Rolling best-window selection + daily aggregation. docs/scoring.md §11-§13."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from custom_components.fishing_forecast.const import default_scoring_config
from custom_components.fishing_forecast.models import (
    AstroDay,
    ComponentScores,
    Confidence,
    HourlyScore,
    Rating,
    rating_for,
)
from custom_components.fishing_forecast.scoring.windows import (
    best_windows,
    summarise_days,
    triangular_weights,
)
from tests.conftest import utc

CFG = default_scoring_config()


def _series(scores: list[float | None], start: datetime) -> list[HourlyScore]:
    out = []
    for i, s in enumerate(scores):
        t = start + timedelta(hours=i)
        out.append(
            HourlyScore(
                time_utc=t,
                components=ComponentScores(),
                weights_used={},
                score=s,
                rating=rating_for(s),
                confidence=Confidence.FULL,
            )
        )
    return out


def test_triangular_weights() -> None:
    assert triangular_weights(1) == [1.0]
    assert triangular_weights(3) == pytest.approx([1.0, 1.3, 1.0])
    w = triangular_weights(5)
    assert w[2] == max(w) and w[0] == w[-1]


def test_spec_worked_example(mindarie) -> None:
    # 15:00..20:00 local -> best window 17:00-20:00 @ ~91
    start = utc(2026, 9, 13, 7)  # 15:00 Perth
    hourly = _series([72, 81, 91, 94, 88, 73], start)
    windows = best_windows(mindarie, hourly, CFG)
    best = windows[0]
    assert best.start_utc == utc(2026, 9, 13, 9)  # 17:00 Perth
    assert best.end_utc == utc(2026, 9, 13, 12)  # exclusive boundary = 20:00 Perth
    assert round(best.score) == 91


def test_windows_never_span_a_scoreless_gap(mindarie) -> None:
    start = utc(2026, 9, 13, 0)
    hourly = _series([90, 90, None, 90, 90, 90], start)
    windows = best_windows(mindarie, hourly, CFG)
    # only one run of >=3 consecutive scored hours (indices 3,4,5)
    assert len(windows) == 1
    assert windows[0].start_utc == start + timedelta(hours=3)


def test_preferred_hours_filter(mindarie) -> None:
    from dataclasses import replace

    cfg = replace(CFG, preferred_hours=(5, 21))
    # 02:00..07:00 Perth == 18:00..23:00 UTC the previous day
    hourly = _series([95] * 6, utc(2026, 9, 12, 18))
    windows = best_windows(mindarie, hourly, cfg)
    # only the 05:00-07:00 block sits entirely inside 05..21 local
    assert len(windows) == 1
    assert windows[0].start_utc == utc(2026, 9, 12, 21)  # 05:00 Perth


def test_daily_score_is_best_window_not_mean(mindarie) -> None:
    # one excellent 3 h block, rest poor -> day should score ~ the block, not the mean
    scores = [20] * 6 + [92, 95, 90] + [15] * 15
    hourly = _series(scores, utc(2026, 9, 12, 16))  # starts 00:00 Perth on the 13th
    windows = best_windows(mindarie, hourly, CFG)
    astro = {utc(2026, 9, 13).date(): AstroDay(utc(2026, 9, 13).date(), None, None)}
    days = summarise_days(mindarie, hourly, windows, astro, CFG)
    day = next(d for d in days if d.date_local.isoformat() == "2026-09-13")
    assert day.score is not None
    assert day.score > 85
    assert day.rating in {Rating.EXCELLENT, Rating.EXCEPTIONAL}


def test_day_with_no_scored_hours_is_unknown(mindarie) -> None:
    hourly = _series([None] * 24, utc(2026, 9, 12, 16))
    days = summarise_days(mindarie, hourly, [], {}, CFG)
    assert days[0].score is None
    assert days[0].rating is Rating.UNKNOWN
