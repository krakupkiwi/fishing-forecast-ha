"""Dawn / dusk score — Phase 2 (not implemented). See docs/scoring.md §7.

    score(time_utc, astro_day: AstroDay, cfg) -> float 0..100

Smooth (cosine-tapered) bonus around sunrise and sunset, peak 100 at the event,
base 40 in the middle of the day/night (never 0).
"""

from __future__ import annotations

from datetime import datetime

from ..models import AstroDay, ScoringConfig


def score(time_utc: datetime, astro_day: AstroDay, cfg: ScoringConfig) -> float | None:
    raise NotImplementedError("Phase 2")
