"""Wind score — Phase 2 (not implemented). See docs/scoring.md §3.

    classify(wind_from_deg, coast_bearing_deg) -> (WindClass, offshore_alignment_deg)
    score(wind_speed_kmh, wind_from_deg, gust_kmh, coast_bearing_deg, cfg) -> float 0..100

Strong wind progressively dominates the directional benefit:
    wind = raw * strength + speed_subscore * (1 - strength)
so an offshore 35 km/h still scores ~3.
"""

from __future__ import annotations

from ..models import ScoringConfig, WindClass


def classify(wind_from_deg: float, coast_bearing_deg: float) -> tuple[WindClass, float]:
    raise NotImplementedError("Phase 2")


def score(
    wind_speed_kmh: float | None,
    wind_from_deg: float | None,
    gust_kmh: float | None,
    coast_bearing_deg: float,
    cfg: ScoringConfig,
) -> float | None:
    raise NotImplementedError("Phase 2")
