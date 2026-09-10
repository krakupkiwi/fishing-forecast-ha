"""Swell score. See docs/scoring.md §4.

Longer period at the same height carries more energy, so period inflates an
"effective height" that is then read off the height curve. Above the location's
safe swell the sub-score is forced down regardless of the curve.
"""

from __future__ import annotations

from ..models import LocationConfig, ScoringConfig
from ..util import angular_gap, clamp, interpolate


def effective_height(height_m: float, period_s: float | None, cfg: ScoringConfig) -> float:
    if period_s is None or period_s <= 0:
        return height_m
    ref = float(cfg.swell["period_ref_s"])
    exponent = float(cfg.swell["period_exponent"])
    lo, hi = (float(x) for x in cfg.swell["period_clamp"])
    factor = clamp((period_s / ref) ** exponent, lo, hi)
    return height_m * factor


def score(
    swell_height_m: float | None,
    swell_period_s: float | None,
    swell_direction_deg: float | None,
    location: LocationConfig,
    cfg: ScoringConfig,
) -> float | None:
    """0–100, or ``None`` when swell height is missing (no fallback to wave height)."""

    if swell_height_m is None:
        return None

    eff = effective_height(swell_height_m, swell_period_s, cfg)
    value = interpolate(cfg.swell["height_m_curve"], eff)

    max_safe = location.max_safe_swell or float(cfg.swell["max_safe_swell_m"])
    if swell_height_m > max_safe:
        value = min(value, float(cfg.swell["over_safe_cap"]))

    # Oblique swell is partly shadowed at many land marks -> small bonus.
    if swell_direction_deg is not None:
        obliquity = angular_gap(swell_direction_deg, location.coast_bearing)
        if obliquity > 60.0:
            value += 5.0

    return clamp(value, 0.0, 100.0)
