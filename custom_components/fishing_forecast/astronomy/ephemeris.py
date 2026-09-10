"""``ephem`` wrapper — the ONLY module that imports ``ephem``.

Everything else goes through the dataclasses returned here so a later swap to
``skyfield`` or a Home Assistant add-on touches just this file
(see ``docs/research.md`` §4.3).

All returned datetimes are timezone-aware UTC. ``ephem`` itself works in UTC and
its ``Date`` objects convert to *naive* UTC datetimes, which we localise here.

These calls are pure CPU and sub-millisecond, but the coordinator must still run
them via ``hass.async_add_executor_job`` — never inline on the event loop.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any

import ephem

from ..models import AstroDay, LocationConfig
from ..util import local_midnight_utc, local_noon_utc

# Sun center depression angles for twilight (degrees, negative = below horizon).
_CIVIL_TWILIGHT = "-6"


def _as_utc(value: Any) -> datetime | None:
    if value is None:
        return None
    naive: datetime = value.datetime()
    return naive.replace(tzinfo=UTC)


def _observer(location: LocationConfig, when: datetime) -> ephem.Observer:
    obs = ephem.Observer()
    obs.lat = str(location.latitude)
    obs.lon = str(location.longitude)
    obs.elevation = float(location.elevation_m)
    obs.date = ephem.Date(when.astimezone(UTC).replace(tzinfo=None))
    return obs


def _event(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Call an ``ephem`` rising/setting/transit function, swallowing polar errors."""

    try:
        return func(*args, **kwargs)
    except (ephem.AlwaysUpError, ephem.NeverUpError, ValueError):
        return None


def _event_in_day(
    obs: ephem.Observer,
    body: ephem.Body,
    day_start: datetime,
    day_end: datetime,
    prev_func: str,
    next_func: str,
    **kwargs: object,
) -> datetime | None:
    """Return the single rise/set/transit of ``body`` that falls within
    ``[day_start, day_end)`` local-calendar-day window, or ``None``.
    """

    noon = day_start + (day_end - day_start) / 2
    obs.date = ephem.Date(noon.replace(tzinfo=None))
    candidates: list[datetime] = []
    for name in (prev_func, next_func):
        result = _as_utc(_event(getattr(obs, name), body, **kwargs))
        if result is not None:
            candidates.append(result)
    for when in sorted(candidates):
        if day_start <= when < day_end:
            return when
    return None


def _moon_phase_fraction(when: datetime) -> float:
    """Position through the synodic month: 0.0 = new, 0.5 = full, ->1.0 = next new.

    Matches Open-Meteo's daily ``moon_phase`` ("fraction") convention.
    """

    d = ephem.Date(when.replace(tzinfo=None))
    prev_new = ephem.previous_new_moon(d)
    next_new = ephem.next_new_moon(d)
    span = float(next_new) - float(prev_new)
    return (float(d) - float(prev_new)) / span if span else 0.0


def astro_day(location: LocationConfig, local_day: date) -> AstroDay:
    """Compute all sun & moon quantities for one local calendar day."""

    tz = location.timezone
    day_start = local_midnight_utc(local_day, tz)
    day_end = local_midnight_utc(local_day + timedelta(days=1), tz)
    noon = local_noon_utc(local_day, tz)

    sun = ephem.Sun()
    moon = ephem.Moon()

    obs = _observer(location, noon)
    sunrise = _as_utc(_event(obs.previous_rising, sun))
    sunset = _as_utc(_event(obs.next_setting, sun))

    twilight_obs = _observer(location, noon)
    twilight_obs.horizon = _CIVIL_TWILIGHT
    twilight_obs.pressure = 0
    dawn = _as_utc(_event(twilight_obs.previous_rising, sun, use_center=True))
    dusk = _as_utc(_event(twilight_obs.next_setting, sun, use_center=True))

    moon_obs = _observer(location, noon)
    moonrise = _event_in_day(moon_obs, moon, day_start, day_end, "previous_rising", "next_rising")
    moonset = _event_in_day(moon_obs, moon, day_start, day_end, "previous_setting", "next_setting")
    upper = _event_in_day(moon_obs, moon, day_start, day_end, "previous_transit", "next_transit")
    lower = _event_in_day(
        moon_obs, moon, day_start, day_end, "previous_antitransit", "next_antitransit"
    )

    moon_obs.date = ephem.Date(noon.replace(tzinfo=None))
    moon.compute(moon_obs)

    return AstroDay(
        date_local=local_day,
        sunrise_utc=sunrise,
        sunset_utc=sunset,
        dawn_utc=dawn,
        dusk_utc=dusk,
        moonrise_utc=moonrise,
        moonset_utc=moonset,
        moon_upper_transit_utc=upper,
        moon_lower_transit_utc=lower,
        moon_phase_fraction=_moon_phase_fraction(noon),
        moon_illumination=float(moon.phase) / 100.0,
    )


def compute(location: LocationConfig, start: date, days: int) -> list[AstroDay]:
    """One :class:`AstroDay` per local calendar day, ``start`` inclusive."""

    return [astro_day(location, start + timedelta(days=offset)) for offset in range(days)]
