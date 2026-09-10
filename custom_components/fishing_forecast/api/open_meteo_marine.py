"""Open-Meteo marine client + parser — Phase 3 (parsing lands in Phase 2/3).

Two requests per update (verified 2026-09-10, see docs/research.md §3):

    A. GET https://marine-api.open-meteo.com/v1/marine
         hourly   = const.MARINE_HOURLY_FIELDS_FINE     # incl. sea_level_height_msl
         timezone = <location tz>
         forecast_days = 16                              # real data ~9.5 days
         cell_selection = sea
       -> best_match model (MeteoFrance MFWAM 0.08° + SMOC tide/currents)

    B. GET https://marine-api.open-meteo.com/v1/marine
         hourly   = const.MARINE_HOURLY_FIELDS_EXTENDED  # waves/swell only, no tide
         models   = ncep_gfswave025
         forecast_days = 16                              # real data full 16 days

Merge by timestamp: prefer A's fields; where A is null and B has a value use B and
set ``has_fine_marine=False``. ``sea_level_m`` is never back-filled from B.
``has_tide`` = ``sea_level_m is not None``.
"""

from __future__ import annotations

from typing import Any

from ..models import MarineHour


def parse_marine(
    fine_payload: dict[str, Any] | None,
    extended_payload: dict[str, Any] | None,
) -> list[MarineHour]:
    """Parse + merge the two marine payloads into typed rows. Not implemented (Phase 2)."""

    raise NotImplementedError("Phase 2: marine parsing + best_match/gfswave merge")
