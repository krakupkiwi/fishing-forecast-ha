"""Pressure-trend score. See docs/scoring.md §9.

Uses the 3-hour delta of ``pressure_msl``, not the absolute value. Returns
``None`` for the first ``lookback_hours`` of the series (no t-3h sample).
Low weight until Phase 5 calibration.
"""

from __future__ import annotations

from ..models import PressureTrend, ScoringConfig

_TREND_BY_KEY = {t.value: t for t in PressureTrend}


def classify(delta_hpa_3h: float, cfg: ScoringConfig) -> tuple[PressureTrend, float]:
    for upper, trend_key, trend_score in cfg.pressure["bins"]:
        if delta_hpa_3h < float(upper):
            return _TREND_BY_KEY[trend_key], float(trend_score)
    # last bin is the catch-all
    _, trend_key, trend_score = cfg.pressure["bins"][-1]
    return _TREND_BY_KEY[trend_key], float(trend_score)


def score(
    pressure_now_hpa: float | None,
    pressure_3h_ago_hpa: float | None,
    cfg: ScoringConfig,
) -> tuple[float | None, PressureTrend | None]:
    if pressure_now_hpa is None or pressure_3h_ago_hpa is None:
        return None, None
    trend, value = classify(pressure_now_hpa - pressure_3h_ago_hpa, cfg)
    return value, trend
