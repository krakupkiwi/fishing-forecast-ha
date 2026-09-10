"""Weighted aggregate engine — Phase 2 (not implemented). See docs/scoring.md §1, §10.

    renormalise(weights: dict[Component, float], present: set[Component])
        -> dict[Component, float]           # drops missing, rescales to sum 1.0

    score_hour(weather: WeatherHour, marine: MarineHour | None,
               tide: TideState | None, periods, astro_day, prev_pressure_hpa, cfg)
        -> HourlyScore

    score_series(weather[], marine[], tide[], periods, astro[], cfg) -> list[HourlyScore]

An hour is `full` iff marine.has_fine_marine and marine.has_tide, else `outlook`
(selects full_weights vs outlook_weights). If every component is None the hour's
score is None and rating is UNKNOWN — never a number built from nothing.
"""

from __future__ import annotations

from ..models import (
    AstroDay,
    Component,
    HourlyScore,
    MarineHour,
    ScoringConfig,
    SolunarPeriod,
    TideState,
    WeatherHour,
)


def renormalise(weights: dict[Component, float], present: set[Component]) -> dict[Component, float]:
    raise NotImplementedError("Phase 2")


def score_hour(
    weather: WeatherHour,
    marine: MarineHour | None,
    tide: TideState | None,
    periods: list[SolunarPeriod],
    astro_day: AstroDay,
    prev_pressure_hpa: float | None,
    cfg: ScoringConfig,
) -> HourlyScore:
    raise NotImplementedError("Phase 2")
