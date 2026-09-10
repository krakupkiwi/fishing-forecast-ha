"""Solunar major/minor period derivation.

  * major: centred on the Moon's upper transit (overhead) and lower transit
    (underfoot), width ``solunar.major_minutes`` (default 120)
  * minor: centred on moonrise and moonset, width ``solunar.minor_minutes``
    (default 60; the bite-times reference uses 120 — configurable, calibrate later)

Periods carry full UTC start/end datetimes so a midnight-spanning period is
unambiguous. Days where the Moon does not rise or set simply contribute no minor
for that event; the two majors still appear (transits happen every day).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from ..models import AstroDay, ScoringConfig, SolunarKind, SolunarPeriod

_MAJOR_EVENTS = (
    ("moon_upper_transit_utc", "moon_upper_transit"),
    ("moon_lower_transit_utc", "moon_lower_transit"),
)
_MINOR_EVENTS = (
    ("moonrise_utc", "moonrise"),
    ("moonset_utc", "moonset"),
)


def periods(days: Sequence[AstroDay], config: ScoringConfig) -> list[SolunarPeriod]:
    """Solunar periods across ``days``, sorted by start, de-duplicated."""

    major_half = timedelta(minutes=float(config.solunar.get("major_minutes", 120)) / 2)
    minor_half = timedelta(minutes=float(config.solunar.get("minor_minutes", 60)) / 2)

    seen: set[tuple[str, int]] = set()
    out: list[SolunarPeriod] = []

    for day in days:
        for attr, label in _MAJOR_EVENTS:
            _add(out, seen, getattr(day, attr), label, SolunarKind.MAJOR, major_half)
        for attr, label in _MINOR_EVENTS:
            _add(out, seen, getattr(day, attr), label, SolunarKind.MINOR, minor_half)

    out.sort(key=lambda p: p.start_utc)
    return out


def _add(
    out: list[SolunarPeriod],
    seen: set[tuple[str, int]],
    centre: datetime | None,
    label: str,
    kind: SolunarKind,
    half: timedelta,
) -> None:
    if centre is None:
        return
    key = (label, int(centre.timestamp()) // 300)  # collapse duplicates within 5 min
    if key in seen:
        return
    seen.add(key)
    out.append(
        SolunarPeriod(
            kind=kind,
            start_utc=centre - half,
            end_utc=centre + half,
            centre_utc=centre,
            centre_event=label,
        )
    )
