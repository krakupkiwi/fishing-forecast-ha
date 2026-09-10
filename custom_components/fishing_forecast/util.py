"""Small shared helpers: angle math, breakpoint interpolation, timezone handling.

Stdlib only. Used by ``scoring/``, ``astronomy/`` and ``api/``.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta, timezone
from itertools import pairwise
from zoneinfo import ZoneInfo

Number = float | int


def clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` into ``[low, high]``."""

    return max(low, min(high, value))


def wrap360(deg: float) -> float:
    """Normalise an angle to ``[0, 360)``."""

    return deg % 360.0


def wrap180(deg: float) -> float:
    """Normalise an angular *difference* to ``(-180, 180]``."""

    d = (deg + 180.0) % 360.0 - 180.0
    return d + 360.0 if d <= -180.0 else d


def angular_gap(a_deg: float, b_deg: float) -> float:
    """Smallest absolute angle between two bearings, in ``[0, 180]``."""

    return abs(wrap180(a_deg - b_deg))


def interpolate(curve: Sequence[tuple[Number, Number]], x: float) -> float:
    """Piecewise-linear interpolation over ``curve`` (sorted ascending by x).

    Clamps to the first/last y outside the domain. ``curve`` must have >= 1 point.
    """

    pts = [(float(px), float(py)) for px, py in curve]
    if not pts:
        raise ValueError("interpolate() needs at least one point")
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in pairwise(pts):
        if x0 <= x <= x1:
            if x1 == x0:
                return y1
            frac = (x - x0) / (x1 - x0)
            return y0 + frac * (y1 - y0)
    return pts[-1][1]  # unreachable, keeps type-checkers happy


def zone(tz_name: str) -> ZoneInfo:
    return ZoneInfo(tz_name)


def to_utc(naive_local: datetime, utc_offset_seconds: int) -> datetime:
    """Attach a fixed offset to a naive API timestamp and convert to aware UTC."""

    tz = timezone(timedelta(seconds=utc_offset_seconds))
    return naive_local.replace(tzinfo=tz).astimezone(UTC)


def local_date_of(instant_utc: datetime, tz_name: str) -> date:
    """Local calendar date that ``instant_utc`` falls on for ``tz_name``."""

    return instant_utc.astimezone(zone(tz_name)).date()


def local_hour_of(instant_utc: datetime, tz_name: str) -> int:
    return instant_utc.astimezone(zone(tz_name)).hour


def local_noon_utc(local_day: date, tz_name: str) -> datetime:
    """UTC instant of 12:00 local on ``local_day``."""

    return datetime.combine(local_day, time(12), tzinfo=zone(tz_name)).astimezone(UTC)


def local_midnight_utc(local_day: date, tz_name: str) -> datetime:
    """UTC instant of 00:00 local on ``local_day``."""

    return datetime.combine(local_day, time(0), tzinfo=zone(tz_name)).astimezone(UTC)


def hhmm_local(instant_utc: datetime | None, tz_name: str) -> str | None:
    if instant_utc is None:
        return None
    return instant_utc.astimezone(zone(tz_name)).strftime("%H:%M")
