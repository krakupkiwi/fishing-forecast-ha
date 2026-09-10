"""Open-Meteo marine parsing + model merge (see docs/research.md §3).

Two payloads:
  * ``fine``     — best_match (MeteoFrance MFWAM 0.08° + SMOC): swell partition,
                   SST, currents and the modelled tide, ~9.5 day horizon.
  * ``extended`` — ncep_gfswave025 (0.25°): waves + swell partition only, full
                   16 day horizon, no tide.

Merge rule per timestamp: prefer a ``fine`` field; where it is ``None`` fall back
to ``extended`` and clear ``has_fine_marine``. ``sea_level_m`` is never
back-filled, so ``has_tide`` is false wherever the fine model has run out.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..models import MarineHour
from ._common import hourly_rows, opt_float

_FINE_MAP = {
    "wave_height_m": "wave_height",
    "wave_period_s": "wave_period",
    "wave_direction_deg": "wave_direction",
    "swell_height_m": "swell_wave_height",
    "swell_period_s": "swell_wave_period",
    "swell_direction_deg": "swell_wave_direction",
    "wind_wave_height_m": "wind_wave_height",
    "wind_wave_period_s": "wind_wave_period",
    "sst_c": "sea_surface_temperature",
    "sea_level_m": "sea_level_height_msl",
}
_EXTENDED_MAP = {
    "wave_height_m": "wave_height",
    "wave_period_s": "wave_period",
    "swell_height_m": "swell_wave_height",
    "swell_period_s": "swell_wave_period",
    "swell_direction_deg": "swell_wave_direction",
    "wind_wave_height_m": "wind_wave_height",
    "wind_wave_period_s": "wind_wave_period",
}
_FINE_PRESENCE = ("wave_height_m", "swell_height_m", "wave_period_s")


def _index(
    payload: dict[str, Any] | None, field_map: dict[str, str]
) -> dict[datetime, dict[str, float | None]]:
    if not payload:
        return {}
    out: dict[datetime, dict[str, float | None]] = {}
    for instant, raw in hourly_rows(payload):
        out[instant] = {
            attr: opt_float(raw.get(src))
            for attr, src in field_map.items()
            if raw.get(src) is not None
        }
    return out


def parse_marine(
    fine_payload: dict[str, Any] | None,
    extended_payload: dict[str, Any] | None,
) -> list[MarineHour]:
    fine = _index(fine_payload, _FINE_MAP)
    extended = _index(extended_payload, _EXTENDED_MAP)

    rows: list[MarineHour] = []
    for instant in sorted(fine.keys() | extended.keys()):
        f = fine.get(instant, {})
        e = extended.get(instant, {})
        merged = {**e, **f}  # fine wins
        has_fine = any(f.get(k) is not None for k in _FINE_PRESENCE)
        sea_level = f.get("sea_level_m")
        rows.append(
            MarineHour(
                time_utc=instant,
                wave_height_m=merged.get("wave_height_m"),
                wave_period_s=merged.get("wave_period_s"),
                wave_direction_deg=merged.get("wave_direction_deg"),
                swell_height_m=merged.get("swell_height_m"),
                swell_period_s=merged.get("swell_period_s"),
                swell_direction_deg=merged.get("swell_direction_deg"),
                wind_wave_height_m=merged.get("wind_wave_height_m"),
                wind_wave_period_s=merged.get("wind_wave_period_s"),
                sst_c=merged.get("sst_c"),
                sea_level_m=sea_level,
                has_fine_marine=has_fine,
                has_tide=sea_level is not None,
            )
        )
    return rows
