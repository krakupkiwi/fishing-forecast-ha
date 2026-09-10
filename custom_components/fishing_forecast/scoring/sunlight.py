"""Dawn / dusk score. See docs/scoring.md §7.

A smooth (cosine) bump around sunrise and sunset: peak at the event, tapering to a
non-zero base in the middle of the day / night. You can still catch fish at noon.
"""

from __future__ import annotations

from datetime import datetime
import math

from ..models import AstroDay, ScoringConfig
from ..util import clamp


def _bump(delta_min: float, before_min: float, after_min: float, base: float, peak: float) -> float:
    """Cosine bump: ``base`` outside ``[-before, after]``, ``peak`` at ``delta=0``."""

    if delta_min < -before_min or delta_min > after_min:
        return base
    half = before_min if delta_min <= 0 else after_min
    x = 1.0 - abs(delta_min) / half  # 0 at the edge, 1 at the event
    shape = 0.5 - 0.5 * math.cos(math.pi * x)
    return base + (peak - base) * shape


def score(time_utc: datetime, astro_day: AstroDay, cfg: ScoringConfig) -> float | None:
    base = float(cfg.sun["base"])
    peak = float(cfg.sun["peak"])
    sr_before, sr_after = (float(x) for x in cfg.sun["sunrise_window_min"])
    ss_before, ss_after = (float(x) for x in cfg.sun["sunset_window_min"])

    best = base
    if astro_day.sunrise_utc is not None:
        delta = (time_utc - astro_day.sunrise_utc).total_seconds() / 60.0
        best = max(best, _bump(delta, -sr_before, sr_after, base, peak))
    if astro_day.sunset_utc is not None:
        delta = (time_utc - astro_day.sunset_utc).total_seconds() / 60.0
        best = max(best, _bump(delta, -ss_before, ss_after, base, peak))

    if astro_day.sunrise_utc is None and astro_day.sunset_utc is None:
        return None
    return clamp(best, 0.0, 100.0)
