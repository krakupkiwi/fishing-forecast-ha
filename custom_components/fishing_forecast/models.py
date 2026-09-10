"""Typed data model for the fishing forecast core.

Stdlib only. This module must not import Home Assistant, aiohttp, or ephem so the
scoring engine and its tests stay framework-independent.

All datetimes are timezone-aware and stored in **UTC**. Local wall-time is only
reconstructed for presentation using ``LocationConfig.timezone``.

Every optional metric is ``float | None``. ``None`` means "not available" and is
never treated as ``0`` — see ``docs/scoring.md`` §10.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any

# Component sub-tables (wind/swell/tide/...) are dynamic JSON-ish config blobs that
# round-trip through the Home Assistant options flow. They are intentionally loose.
ComponentTable = dict[str, Any]

# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #


class Component(StrEnum):
    """Scoring components. Values are the keys used in configs and JSON output."""

    WIND = "wind"
    SWELL = "swell"
    TIDE = "tide"
    SOLUNAR = "solunar"
    SUN = "sun"
    RAIN = "rain"
    PRESSURE = "pressure"


class Rating(StrEnum):
    """Semantic score bands. The frontend maps these to colours, not the backend."""

    EXCEPTIONAL = "exceptional"
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    MARGINAL = "marginal"
    POOR = "poor"
    UNKNOWN = "unknown"


class Confidence(StrEnum):
    FULL = "full"
    OUTLOOK = "outlook"


class TideDirection(StrEnum):
    RISING = "rising"
    FALLING = "falling"


class TideExtreme(StrEnum):
    HIGH = "high"
    LOW = "low"


class PressureTrend(StrEnum):
    RAPIDLY_RISING = "rapidly_rising"
    RISING = "rising"
    STEADY = "steady"
    FALLING = "falling"
    RAPIDLY_FALLING = "rapidly_falling"


class WindClass(StrEnum):
    OFFSHORE = "offshore"
    CROSS_OFFSHORE = "cross-offshore"
    CROSS_SHORE = "cross-shore"
    CROSS_ONSHORE = "cross-onshore"
    ONSHORE = "onshore"


class SolunarKind(StrEnum):
    MAJOR = "major"
    MINOR = "minor"


class SourceHealth(StrEnum):
    OK = "ok"
    STALE = "stale"
    FAILED = "failed"


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class LocationConfig:
    """A configured fishing location. One Home Assistant config entry per instance."""

    id: str
    name: str
    latitude: float
    longitude: float
    # Marine grid is requested at a separate, offshore coordinate so the wave model
    # does not resolve to an unsuitable near-shore / land cell.
    marine_latitude: float
    marine_longitude: float
    # Bearing (deg) pointing from the shore straight out to sea. Mindarie ≈ 270.
    coast_bearing: float
    # IANA tz name, e.g. "Australia/Perth". Used only for local-day bucketing + display.
    timezone: str = "Australia/Perth"
    # Ground elevation (m) at the land coordinate; used for sun/moon rise-set refraction.
    elevation_m: float = 0.0

    # Location-specific swell tuning (metres). None => use ScoringConfig defaults.
    ideal_swell_min: float | None = None
    ideal_swell_max: float | None = None
    max_safe_swell: float | None = None

    # Optional directional hints (deg, "coming from"); each entry is a (min, max) arc.
    preferred_wind_directions: tuple[tuple[float, float], ...] = ()
    exposed_wind_directions: tuple[tuple[float, float], ...] = ()

    enabled: bool = True


@dataclass(frozen=True, slots=True)
class ScoringConfig:
    """All tunable scoring constants. Defaults live in ``const.py``.

    ``full_weights`` / ``outlook_weights`` map every :class:`Component` to a weight;
    the engine renormalises whatever subset is actually present for an hour.
    """

    full_weights: dict[Component, float]
    outlook_weights: dict[Component, float]

    window_hours: int = 3
    # Optional inclusive local-hour range a valid window must sit within, e.g. (4, 21).
    preferred_hours: tuple[int, int] | None = None

    # Component sub-tables are stored as plain dicts/tuples of breakpoints so they
    # round-trip through the Home Assistant options flow as JSON. See docs/scoring.md.
    wind: ComponentTable = field(default_factory=dict)
    swell: ComponentTable = field(default_factory=dict)
    tide: ComponentTable = field(default_factory=dict)
    solunar: ComponentTable = field(default_factory=dict)
    sun: ComponentTable = field(default_factory=dict)
    rain: ComponentTable = field(default_factory=dict)
    pressure: ComponentTable = field(default_factory=dict)

    day_full_hours_fraction: float = 0.6


# --------------------------------------------------------------------------- #
# Raw parsed inputs (one row per forecast hour / day)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class WeatherHour:
    """One hour of parsed Open-Meteo weather data."""

    time_utc: datetime
    wind_speed_kmh: float | None
    wind_direction_deg: float | None  # "coming from"
    wind_gust_kmh: float | None
    precip_mm_h: float | None  # total: rain + showers + snow, preceding hour
    rain_mm_h: float | None  # large-scale only
    showers_mm_h: float | None  # convective only
    cloud_cover_pct: float | None
    pressure_msl_hpa: float | None
    air_temp_c: float | None = None
    weather_code: int | None = None


@dataclass(frozen=True, slots=True)
class MarineHour:
    """One hour of parsed Open-Meteo marine data. Every field may be ``None``."""

    time_utc: datetime
    wave_height_m: float | None = None
    wave_period_s: float | None = None
    wave_direction_deg: float | None = None
    swell_height_m: float | None = None
    swell_period_s: float | None = None
    swell_direction_deg: float | None = None
    wind_wave_height_m: float | None = None
    wind_wave_period_s: float | None = None
    sst_c: float | None = None
    sea_level_m: float | None = None  # sea_level_height_msl, datum = global MSL

    # Provenance, set by the merge step.
    has_fine_marine: bool = False  # came from best_match (MeteoFrance MFWAM 0.08°)
    has_tide: bool = False  # sea_level_m is present


@dataclass(frozen=True, slots=True)
class AstroDay:
    """Sun & moon events for one local calendar day. Event times are UTC."""

    date_local: date
    sunrise_utc: datetime | None
    sunset_utc: datetime | None
    dawn_utc: datetime | None = None
    dusk_utc: datetime | None = None
    moonrise_utc: datetime | None = None
    moonset_utc: datetime | None = None
    moon_upper_transit_utc: datetime | None = None  # overhead
    moon_lower_transit_utc: datetime | None = None  # underfoot
    moon_phase_fraction: float | None = None  # 0=new, 0.5=full
    moon_illumination: float | None = None  # 0..1


@dataclass(frozen=True, slots=True)
class SolunarPeriod:
    kind: SolunarKind
    start_utc: datetime
    end_utc: datetime
    centre_utc: datetime
    centre_event: str  # "moon_upper_transit" | "moon_lower_transit" | "moonrise" | "moonset"


@dataclass(frozen=True, slots=True)
class TideSample:
    time_utc: datetime
    height_m: float | None


@dataclass(frozen=True, slots=True)
class TideExtremePoint:
    time_utc: datetime
    kind: TideExtreme
    height_m: float


@dataclass(frozen=True, slots=True)
class TideState:
    """Derived tide condition at one instant. ``direction is None`` => unscoreable."""

    time_utc: datetime
    height_m: float | None
    direction: TideDirection | None
    next_extreme: TideExtremePoint | None
    minutes_to_next_extreme: float | None
    last_extreme: TideExtremePoint | None
    minutes_since_last_extreme: float | None
    rate_m_per_h: float | None


# --------------------------------------------------------------------------- #
# Scored outputs
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class ComponentScores:
    """Per-component sub-scores in [0, 100]; ``None`` where input was missing."""

    wind: float | None = None
    swell: float | None = None
    tide: float | None = None
    solunar: float | None = None
    sun: float | None = None
    rain: float | None = None
    pressure: float | None = None

    def present(self) -> dict[Component, float]:
        out: dict[Component, float] = {}
        for comp in Component:
            value = getattr(self, comp.value)
            if value is not None:
                out[comp] = float(value)
        return out


@dataclass(frozen=True, slots=True)
class HourlyScore:
    time_utc: datetime
    components: ComponentScores
    weights_used: dict[Component, float]
    score: float | None
    rating: Rating
    confidence: Confidence
    wind_class: WindClass | None = None
    pressure_trend: PressureTrend | None = None
    inside_major: bool = False
    inside_minor: bool = False
    # References to the raw inputs, so the card's day-detail view can show the
    # actual conditions (wind km/h, swell m @ s, tide state) behind the score.
    weather: WeatherHour | None = None
    marine: MarineHour | None = None
    tide: TideState | None = None


@dataclass(frozen=True, slots=True)
class FishingWindow:
    start_utc: datetime
    end_utc: datetime  # exclusive boundary (start of hour after last included sample)
    score: float
    is_end_inclusive_sample: bool = False


@dataclass(frozen=True, slots=True)
class DailyForecast:
    date_local: date
    score: float | None
    rating: Rating
    confidence: Confidence
    best_window: FishingWindow | None
    second_window: FishingWindow | None
    sunrise_local: str | None  # "HH:MM"
    sunset_local: str | None
    highlights: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DataHealth:
    weather: SourceHealth = SourceHealth.OK
    marine_fine: SourceHealth = SourceHealth.OK
    marine_extended: SourceHealth = SourceHealth.OK
    astronomy: SourceHealth = SourceHealth.OK
    # Wall-clock of the build; excluded from equality so an unchanged forecast
    # compares equal (lets the coordinator use always_update=False).
    generated_utc: datetime | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class ForecastBundle:
    """The coordinator's return value. Comparable so ``always_update=False`` works."""

    location: LocationConfig
    hourly: tuple[HourlyScore, ...]
    daily: tuple[DailyForecast, ...]
    best_day: DailyForecast | None
    health: DataHealth
    generated_utc: datetime = field(compare=False)
    solunar_periods: tuple[SolunarPeriod, ...] = ()
    tide_extremes: tuple[TideExtremePoint, ...] = ()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

_RATING_BANDS: tuple[tuple[float, Rating], ...] = (
    (90.0, Rating.EXCEPTIONAL),
    (80.0, Rating.EXCELLENT),
    (70.0, Rating.GOOD),
    (60.0, Rating.FAIR),
    (50.0, Rating.MARGINAL),
    (0.0, Rating.POOR),
)


def rating_for(score: float | None) -> Rating:
    """Map a 0–100 score to its semantic band. ``None`` -> ``UNKNOWN``."""

    if score is None:
        return Rating.UNKNOWN
    for threshold, rating in _RATING_BANDS:
        if score >= threshold:
            return rating
    return Rating.POOR
