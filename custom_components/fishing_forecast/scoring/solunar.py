"""Solunar score. See docs/scoring.md §6.

inside major -> 100; within the grace window of a major edge -> 90; inside minor
-> 80; near minor -> 70; else baseline 50. A tiny bonus near new / full moon.
The 0.15 / 0.20 weight cap (not this function) is what stops a solunar period
overriding bad wind or dangerous swell.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from ..models import AstroDay, ScoringConfig, SolunarKind, SolunarPeriod
from ..util import clamp

# ~2 days as a fraction of the synodic month.
_PHASE_BONUS_FRACTION = 2.0 / 29.53


def _relation(instant: datetime, period: SolunarPeriod, grace: timedelta) -> str:
    if period.start_utc <= instant <= period.end_utc:
        return "inside"
    if period.start_utc - grace <= instant <= period.end_utc + grace:
        return "near"
    return "outside"


def score(
    time_utc: datetime,
    periods: Sequence[SolunarPeriod],
    astro_day: AstroDay,
    cfg: ScoringConfig,
) -> tuple[float, bool, bool]:
    """Return ``(score, inside_major, inside_minor)``."""

    s = cfg.solunar
    grace = timedelta(minutes=float(s.get("edge_grace_minutes", 30)))

    value = float(s["baseline"])
    inside_major = inside_minor = False
    near_major = near_minor = False

    for period in periods:
        rel = _relation(time_utc, period, grace)
        if rel == "outside":
            continue
        if period.kind is SolunarKind.MAJOR:
            inside_major = inside_major or rel == "inside"
            near_major = near_major or rel == "near"
        else:
            inside_minor = inside_minor or rel == "inside"
            near_minor = near_minor or rel == "near"

    if inside_major:
        value = float(s["inside_major"])
    elif near_major:
        value = float(s["near_major"])
    elif inside_minor:
        value = float(s["inside_minor"])
    elif near_minor:
        value = float(s["near_minor"])

    frac = astro_day.moon_phase_fraction
    if frac is not None:
        near_new = frac < _PHASE_BONUS_FRACTION or frac > 1.0 - _PHASE_BONUS_FRACTION
        near_full = abs(frac - 0.5) < _PHASE_BONUS_FRACTION
        if near_new or near_full:
            value += float(s.get("phase_bonus", 0))

    return clamp(value, 0.0, 100.0), inside_major, inside_minor
