"""End-to-end forecast build: Open-Meteo payloads -> ForecastBundle.

Pure and synchronous. The Home Assistant coordinator does the HTTP I/O and runs
the ``ephem`` astronomy step in the executor, then calls :func:`build_forecast`
with the raw JSON. Nothing here imports Home Assistant.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
import logging
from typing import Any

from .api._common import OpenMeteoError
from .api.open_meteo_marine import parse_marine
from .api.open_meteo_weather import parse_weather
from .astronomy import ephemeris, solunar
from .models import (
    AstroDay,
    DataHealth,
    ForecastBundle,
    LocationConfig,
    ScoringConfig,
    SourceHealth,
    TideSample,
)
from .scoring import engine
from .scoring import tide as tide_mod
from .scoring import windows as windows_mod
from .tide_harmonic import extend_tide_samples, resolve_station
from .util import local_date_of

_LOGGER = logging.getLogger(__name__)

_ASTRO_PAD_DAYS = 2


def _compute_astro(
    location: LocationConfig, first_local_day: date, days: int
) -> tuple[list[AstroDay], SourceHealth]:
    try:
        astro = ephemeris.compute(location, first_local_day, days + _ASTRO_PAD_DAYS)
        return astro, SourceHealth.OK
    except Exception:
        _LOGGER.exception("astronomy computation failed; continuing without solunar/sun")
        return [], SourceHealth.FAILED


def build_forecast(
    location: LocationConfig,
    weather_payload: dict[str, Any],
    marine_fine_payload: dict[str, Any] | None,
    marine_extended_payload: dict[str, Any] | None,
    cfg: ScoringConfig,
    *,
    days: int = 14,
    now_utc: datetime | None = None,
) -> ForecastBundle:
    now = now_utc or datetime.now(UTC)
    tz = location.timezone

    weather_hours = parse_weather(weather_payload)
    if not weather_hours:
        raise OpenMeteoError("weather payload contained no hourly data")

    marine_health_fine = SourceHealth.OK
    marine_health_ext = SourceHealth.OK
    try:
        marine_hours = parse_marine(marine_fine_payload, marine_extended_payload)
    except OpenMeteoError:
        _LOGGER.warning("marine payload error; producing a weather/solunar outlook only")
        marine_hours = []
        marine_health_fine = marine_health_ext = SourceHealth.FAILED
    if marine_fine_payload is None or not any(m.has_fine_marine for m in marine_hours):
        marine_health_fine = SourceHealth.FAILED
    if marine_extended_payload is None:
        marine_health_ext = SourceHealth.FAILED

    first_day = local_date_of(weather_hours[0].time_utc, tz)
    astro, astro_health = _compute_astro(location, first_day, days)
    astro_by_date = {a.date_local: a for a in astro}
    periods = solunar.periods(astro, cfg)

    marine_by_time = {m.time_utc: m for m in marine_hours}

    # Modelled tide where Open-Meteo has it; harmonic prediction past its horizon
    # so tide scoring covers the whole forecast, not just the first ~9.5 days.
    sea_by_time = {m.time_utc: m.sea_level_m for m in marine_hours}
    station = resolve_station(location.tide_station, location.latitude, location.longitude)
    tide_samples = extend_tide_samples(
        [TideSample(w.time_utc, sea_by_time.get(w.time_utc)) for w in weather_hours],
        station,
    )
    tide_states = tide_mod.derive(tide_samples, cfg)
    tide_by_time = {t.time_utc: t for t in tide_states}
    all_extremes = tide_mod.find_extrema(tide_samples, cfg)

    hourly = engine.score_series(
        location, weather_hours, marine_by_time, tide_by_time, periods, astro_by_date, cfg
    )

    cutoff = first_day + timedelta(days=days)
    hourly = [h for h in hourly if local_date_of(h.time_utc, tz) < cutoff]
    solunar_periods = tuple(p for p in periods if local_date_of(p.centre_utc, tz) < cutoff)
    tide_extremes = tuple(e for e in all_extremes if local_date_of(e.time_utc, tz) < cutoff)

    windows = windows_mod.best_windows(location, hourly, cfg)
    daily = windows_mod.summarise_days(location, hourly, windows, astro_by_date, cfg)

    scored_days = [d for d in daily if d.score is not None]
    best_day = max(scored_days, key=lambda d: d.score or 0.0) if scored_days else None

    health = DataHealth(
        weather=SourceHealth.OK,
        marine_fine=marine_health_fine,
        marine_extended=marine_health_ext,
        astronomy=astro_health,
        generated_utc=now,
    )

    return ForecastBundle(
        location=location,
        generated_utc=now,
        hourly=tuple(hourly),
        daily=tuple(daily),
        best_day=best_day,
        health=health,
        solunar_periods=solunar_periods,
        tide_extremes=tide_extremes,
    )
