"""Wind score. See docs/scoring.md §3.

Speed sub-score (direction-independent) times a directional multiplier, then a
blend so that strong wind progressively dominates the directional benefit:

    wind = raw * strength + speed_subscore * (1 - strength)

so an offshore 35 km/h still scores ~3, not "great because it's offshore".
"""

from __future__ import annotations

from ..models import ScoringConfig, WindClass
from ..util import clamp, interpolate, wrap180

# offshore alignment (deg from pure-offshore) -> class
_CLASS_BANDS: tuple[tuple[float, WindClass], ...] = (
    (22.5, WindClass.OFFSHORE),
    (67.5, WindClass.CROSS_OFFSHORE),
    (112.5, WindClass.CROSS_SHORE),
    (157.5, WindClass.CROSS_ONSHORE),
    (180.1, WindClass.ONSHORE),
)


def offshore_alignment(wind_from_deg: float, coast_bearing_deg: float) -> float:
    """Angle between the wind's source direction and 'straight offshore'.

    ``coast_bearing`` points from shore out to sea, so a wind blowing *off the
    land* (offshore) comes from ``coast_bearing + 180``. Returns ``[0, 180]``
    where 0 = pure offshore, 180 = pure onshore.
    """

    return abs(wrap180(wind_from_deg - (coast_bearing_deg + 180.0)))


def classify(wind_from_deg: float, coast_bearing_deg: float) -> tuple[WindClass, float]:
    align = offshore_alignment(wind_from_deg, coast_bearing_deg)
    for limit, wind_class in _CLASS_BANDS:
        if align <= limit:
            return wind_class, align
    return WindClass.ONSHORE, align


def _direction_multiplier(align_deg: float, cfg: ScoringConfig) -> float:
    table = cfg.wind["direction_multiplier"]
    curve = sorted((float(k), float(v)) for k, v in table.items())
    return interpolate(curve, align_deg)


def _speed_subscore(speed_kmh: float, cfg: ScoringConfig) -> float:
    return interpolate(cfg.wind["speed_kmh_curve"], speed_kmh)


def score(
    wind_speed_kmh: float | None,
    wind_from_deg: float | None,
    gust_kmh: float | None,
    coast_bearing_deg: float,
    cfg: ScoringConfig,
) -> float | None:
    """0–100, or ``None`` when speed or direction is missing."""

    if wind_speed_kmh is None or wind_from_deg is None:
        return None

    speed_sub = _speed_subscore(wind_speed_kmh, cfg)
    _, align = classify(wind_from_deg, coast_bearing_deg)
    multiplier = _direction_multiplier(align, cfg)

    # Direction only bites once there is meaningful wind: at dead calm the
    # coastline is irrelevant, and a strong wind's low speed sub-score already
    # dominates, so an offshore gale still can't score well.
    full = float(cfg.wind.get("direction_full_effect_kmh", 18.0))
    dir_weight = clamp(wind_speed_kmh / full, 0.0, 1.0) if full > 0 else 1.0
    value = speed_sub * (1.0 - dir_weight * (1.0 - multiplier))

    penalty = cfg.wind.get("gust_ratio_penalty")
    if penalty and gust_kmh is not None and wind_speed_kmh > 0:
        ratio = gust_kmh / wind_speed_kmh
        if ratio >= float(penalty["ratio"]) and gust_kmh > float(penalty["min_gust_kmh"]):
            value *= float(penalty["factor"])

    return clamp(value, 0.0, 100.0)
