"""Rain score — Phase 2 (not implemented). See docs/scoring.md §8.

    score(precip_mm_h, cfg) -> float | None

Input is total precipitation (rain + showers + snow), preceding-hour sum.
Interpolate the mm/h curve: 0->100, 0.5->90, 1->75, 2->55, 5->30, >=10->5.
"""

from __future__ import annotations

from ..models import ScoringConfig


def score(precip_mm_h: float | None, cfg: ScoringConfig) -> float | None:
    raise NotImplementedError("Phase 2")
