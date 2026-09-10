"""Dawn / dusk score. See docs/scoring.md §7.

A smooth (cosine) bump around sunrise and sunset: peak at the event, tapering to a
non-zero base in the middle of the day / night. You can still catch fish at noon.

Profiles that target nocturnal species (mulloway, squid) set ``sun.night_score``
so full darkness scores above the daytime ``base`` instead of below it.
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

    night_score = cfg.sun.get("night_score")
    if night_score is not None and best <= base and _is_night(time_utc, astro_day):
        return clamp(float(night_score), 0.0, 100.0)
    return clamp(best, 0.0, 100.0)


def _is_night(time_utc: datetime, astro_day: AstroDay) -> bool:
    """True when the sun is down for ``astro_day`` at ``time_utc``."""

    sunrise = astro_day.sunrise_utc
    sunset = astro_day.sunset_utc
    if sunset is not None and time_utc >= sunset:
        return True
    return sunrise is not None and time_utc <= sunrise
