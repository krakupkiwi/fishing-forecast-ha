"""Solunar major/minor period derivation — Phase 2 (not implemented).

From a list of :class:`AstroDay` produce :class:`SolunarPeriod` objects:
  * major: centred on moon_upper_transit and moon_lower_transit, width
    ``solunar.major_minutes`` (default 120)
  * minor: centred on moonrise and moonset, width ``solunar.minor_minutes``
    (default 60; bite-times uses 120 — configurable, calibrate in Phase 5)

Periods may span midnight -> full start/end datetimes (UTC). When the moon does not
rise/set on a day, still emit the two majors (transits exist every day) and skip the
missing minor.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..models import AstroDay, ScoringConfig, SolunarPeriod


def periods(days: Sequence[AstroDay], config: ScoringConfig) -> list[SolunarPeriod]:
    """Compute solunar periods for the given days. Not implemented (Phase 2)."""

    raise NotImplementedError("Phase 2: solunar major/minor intervals")
