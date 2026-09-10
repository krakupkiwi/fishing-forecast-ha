"""Swell score — Phase 2 (not implemented). See docs/scoring.md §4.

    score(swell_height_m, swell_period_s, swell_dir_deg, location, cfg) -> float | None

Period adjusts effective height:
    effective_height = height * clamp((period / 10) ** 0.5, 0.8, 1.4)
Above location.max_safe_swell the sub-score is forced <= 10.
Returns None if swell_height_m is None (no fallback to total wave_height in V1).
"""

from __future__ import annotations

from ..models import LocationConfig, ScoringConfig


def score(
    swell_height_m: float | None,
    swell_period_s: float | None,
    swell_direction_deg: float | None,
    location: LocationConfig,
    cfg: ScoringConfig,
) -> float | None:
    raise NotImplementedError("Phase 2")
