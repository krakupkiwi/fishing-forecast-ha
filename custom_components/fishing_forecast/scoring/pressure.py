"""Pressure-trend score — Phase 2 (not implemented). See docs/scoring.md §9.

    trend(delta_hpa_3h, cfg) -> PressureTrend
    score(pressure_now_hpa, pressure_3h_ago_hpa, cfg) -> (float | None, PressureTrend | None)

Uses the 3-hour delta of pressure_msl, not absolute pressure. Returns None for the
first ``lookback_hours`` of the series (no t-3h sample). Low weight until Phase 5.
"""

from __future__ import annotations

from ..models import PressureTrend, ScoringConfig


def trend(delta_hpa_3h: float, cfg: ScoringConfig) -> PressureTrend:
    raise NotImplementedError("Phase 2")


def score(
    pressure_now_hpa: float | None,
    pressure_3h_ago_hpa: float | None,
    cfg: ScoringConfig,
) -> tuple[float | None, PressureTrend | None]:
    raise NotImplementedError("Phase 2")
