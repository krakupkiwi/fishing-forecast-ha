"""Rain score. See docs/scoring.md §8.

Input is total precipitation (rain + showers + snow), preceding-hour sum.
"""

from __future__ import annotations

from ..models import ScoringConfig
from ..util import clamp, interpolate


def score(precip_mm_h: float | None, cfg: ScoringConfig) -> float | None:
    if precip_mm_h is None:
        return None
    return clamp(interpolate(cfg.rain["mm_h_curve"], max(0.0, precip_mm_h)), 0.0, 100.0)
