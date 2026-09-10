"""Weighted aggregate engine. See docs/scoring.md §1, §10.

An hour is scored ``full`` iff it has fine marine data *and* modelled tide, else
``outlook`` (which selects the outlook weight set). Whatever components are
actually present are renormalised to sum 1.0. If every component is missing the
hour's score is ``None`` and its rating ``UNKNOWN`` — never a number built from
nothing.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta

from ..models import (
    AstroDay,
    Component,
    ComponentScores,
    Confidence,
    HourlyScore,
    LocationConfig,
    MarineHour,
    ScoringConfig,
    SolunarPeriod,
    TideState,
    WeatherHour,
    rating_for,
)
from ..util import local_date_of
from . import pressure as pressure_mod
from . import rain as rain_mod
from . import solunar as solunar_mod
from . import sunlight as sun_mod
from . import swell as swell_mod
from . import tide as tide_mod
from . import wind as wind_mod


def renormalise(
    weights: Mapping[Component, float], present: set[Component]
) -> dict[Component, float]:
    """Drop components not in ``present`` and rescale the rest to sum 1.0."""

    kept = {c: float(w) for c, w in weights.items() if c in present and w > 0}
    total = sum(kept.values())
    if total <= 0:
        return {}
    return {c: w / total for c, w in kept.items()}


def _confidence(marine: MarineHour | None) -> Confidence:
    if marine is not None and marine.has_fine_marine and marine.has_tide:
        return Confidence.FULL
    return Confidence.OUTLOOK


def score_hour(
    location: LocationConfig,
    weather: WeatherHour,
    marine: MarineHour | None,
    tide_state: TideState | None,
    periods: Sequence[SolunarPeriod],
    astro_day: AstroDay | None,
    prev_pressure_hpa: float | None,
    cfg: ScoringConfig,
) -> HourlyScore:
    wind_value = wind_mod.score(
        weather.wind_speed_kmh,
        weather.wind_direction_deg,
        weather.wind_gust_kmh,
        location.coast_bearing,
        cfg,
    )
    wind_class = (
        wind_mod.classify(weather.wind_direction_deg, location.coast_bearing)[0]
        if weather.wind_direction_deg is not None
        else None
    )

    swell_value = (
        swell_mod.score(
            marine.swell_height_m, marine.swell_period_s, marine.swell_direction_deg, location, cfg
        )
        if marine is not None
        else None
    )
    tide_value = tide_mod.score(tide_state, cfg) if tide_state is not None else None

    if astro_day is not None:
        solunar_value, inside_major, inside_minor = solunar_mod.score(
            weather.time_utc, periods, astro_day, cfg
        )
        sun_value = sun_mod.score(weather.time_utc, astro_day, cfg)
    else:
        solunar_value = None
        sun_value = None
        inside_major = inside_minor = False

    rain_value = rain_mod.score(weather.precip_mm_h, cfg)
    pressure_value, pressure_trend = pressure_mod.score(
        weather.pressure_msl_hpa, prev_pressure_hpa, cfg
    )

    components = ComponentScores(
        wind=wind_value,
        swell=swell_value,
        tide=tide_value,
        solunar=solunar_value,
        sun=sun_value,
        rain=rain_value,
        pressure=pressure_value,
    )

    confidence = _confidence(marine)
    weights = cfg.full_weights if confidence is Confidence.FULL else cfg.outlook_weights
    present = set(components.present())
    used = renormalise(weights, present)

    if used:
        values = components.present()
        total = sum(used[c] * values[c] for c in used)
    else:
        total = None

    return HourlyScore(
        time_utc=weather.time_utc,
        components=components,
        weights_used=used,
        score=total,
        rating=rating_for(total),
        confidence=confidence,
        wind_class=wind_class,
        pressure_trend=pressure_trend,
        inside_major=inside_major,
        inside_minor=inside_minor,
        weather=weather,
        marine=marine,
        tide=tide_state,
    )


def score_series(
    location: LocationConfig,
    weather: Sequence[WeatherHour],
    marine_by_time: Mapping[datetime, MarineHour],
    tide_by_time: Mapping[datetime, TideState],
    periods: Sequence[SolunarPeriod],
    astro_by_date: Mapping[date, AstroDay],
    cfg: ScoringConfig,
) -> list[HourlyScore]:
    weather_by_time = {w.time_utc: w for w in weather}
    lookback = timedelta(hours=float(cfg.pressure.get("lookback_hours", 3)))
    astro_days = sorted(astro_by_date)

    out: list[HourlyScore] = []
    for hour in weather:
        local_day = local_date_of(hour.time_utc, location.timezone)
        astro_day = astro_by_date.get(local_day)
        if astro_day is None and astro_days:
            nearest = min(astro_days, key=lambda d: abs((d - local_day).days))
            astro_day = astro_by_date[nearest]
        prev = weather_by_time.get(hour.time_utc - lookback)
        prev_pressure = prev.pressure_msl_hpa if prev is not None else None
        out.append(
            score_hour(
                location,
                hour,
                marine_by_time.get(hour.time_utc),
                tide_by_time.get(hour.time_utc),
                periods,
                astro_day,
                prev_pressure,
                cfg,
            )
        )
    return out
