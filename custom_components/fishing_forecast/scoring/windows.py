"""Rolling best-window + daily aggregation — Phase 2 (not implemented).
See docs/scoring.md §11-§13.

    best_windows(hourly: list[HourlyScore], cfg) -> list[FishingWindow]  (sorted desc)
        rolling window of cfg.window_hours consecutive *scored* hours, triangular
        centre weighting ([1, 1.3, 1] for 3h), optional cfg.preferred_hours filter.
        end_utc is the exclusive boundary; is_end_inclusive_sample=False.

    summarise_day(local_date, hourly, windows, astro_day, cfg) -> DailyForecast
        daily score = best_window.score (not the 24h mean). confidence=full iff
        >= cfg.day_full_hours_fraction of 06:00-21:00 local hours are full.
"""

from __future__ import annotations

from datetime import date

from ..models import AstroDay, DailyForecast, FishingWindow, HourlyScore, ScoringConfig


def best_windows(hourly: list[HourlyScore], cfg: ScoringConfig) -> list[FishingWindow]:
    raise NotImplementedError("Phase 2")


def summarise_day(
    local_date: date,
    hourly: list[HourlyScore],
    windows: list[FishingWindow],
    astro_day: AstroDay,
    cfg: ScoringConfig,
) -> DailyForecast:
    raise NotImplementedError("Phase 2")
