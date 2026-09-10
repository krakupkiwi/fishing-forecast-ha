"""Solunar score — Phase 2 (not implemented). See docs/scoring.md §6.

    score(time_utc, periods: list[SolunarPeriod], astro_day: AstroDay, cfg)
        -> (float 0..100, inside_major: bool, inside_minor: bool)

inside major -> 100; within 30 min of a major edge -> 90; inside minor -> 80;
near minor -> 70; else 50. +5 within phase_bonus_days of new/full (clamp 100).
The 0.15 / 0.20 weight cap is what stops solunar overriding bad wind/swell.
"""

from __future__ import annotations

from datetime import datetime

from ..models import AstroDay, ScoringConfig, SolunarPeriod


def score(
    time_utc: datetime,
    periods: list[SolunarPeriod],
    astro_day: AstroDay,
    cfg: ScoringConfig,
) -> tuple[float, bool, bool]:
    raise NotImplementedError("Phase 2")
