"""``ephem`` wrapper — Phase 2 (not implemented).

The ONLY module that imports ``ephem``. Exposes:

    sun_events(lat, lon, elevation_m, local_date, tz) -> AstroDay(partial: sun only)
    moon_events(lat, lon, elevation_m, local_date, tz) -> fills moon fields
    compute(location, start_date, days) -> list[AstroDay]

Notes (docs/research.md §4.3):
  * ephem is deterministic given (lat, lon, elevation, UTC instant).
  * All calls are pure CPU but MUST run in the executor from the coordinator.
  * Moon meridian transits come from Observer.next_transit(ephem.Moon()) /
    next_antitransit(); phase from ephem.Moon(observer).phase (0-100 %).
  * Cross-check moonrise/moonset/moon_phase against the Open-Meteo daily fields.
"""

from __future__ import annotations

from datetime import date

from ..models import AstroDay, LocationConfig


def compute(location: LocationConfig, start: date, days: int) -> list[AstroDay]:
    """Return one :class:`AstroDay` per local calendar day. Not implemented (Phase 2)."""

    raise NotImplementedError("Phase 2: ephem sun/moon events + transits")
