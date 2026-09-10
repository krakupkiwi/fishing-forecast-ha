"""Numpy-free harmonic tide prediction — fills the outlook-period gap.

Open-Meteo's modelled ``sea_level_height_msl`` is excellent for the ~9.5 days it
covers (validated at r = 0.98, 5 cm RMS against the Fremantle gauge — see
``docs/tide.md``) but runs out before the 14-day forecast does, so tide scoring
switched off for days ~10-14. A small harmonic model covers the rest.

This is astronomical tide only (no storm surge), which is exactly what the tide
*score* needs — it cares about "rising, N hours to high", not absolute height.
Constituent amplitudes/phases were derived by least-squares fit to 6 years of the
UHSLC Fremantle tide-gauge record; Perth is diurnal-dominant (K1 + O1 >> M2 + S2).
One station covers the whole Perth metro coast (Two Rocks → Fremantle): the tidal
wave phase difference over that ~60 km is a few minutes and amplitudes are
near-identical.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import math

from .models import TideSample

_EPOCH = datetime(2024, 1, 1, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class _Constituent:
    name: str
    speed_deg_per_h: float
    amp_m: float
    phase_deg: float


@dataclass(frozen=True, slots=True)
class TideStation:
    key: str
    name: str
    latitude: float
    longitude: float
    mean_m: float
    source: str
    constituents: tuple[_Constituent, ...]

    def height(self, when: datetime) -> float:
        hrs = (when.astimezone(UTC) - _EPOCH).total_seconds() / 3600.0
        total = self.mean_m
        for c in self.constituents:
            total += c.amp_m * math.cos(
                math.radians(c.speed_deg_per_h) * hrs - math.radians(c.phase_deg)
            )
        return total


def _c(name: str, speed: float, amp: float, phase: float) -> _Constituent:
    return _Constituent(name, speed, amp, phase)


# Fit to UHSLC hourly gauge #175 (Fremantle), 2020-2025, constituents with
# amplitude >= 3 mm. Self-check RMS ~110 mm = the irreducible non-tidal residual.
FREMANTLE = TideStation(
    key="fremantle",
    name="Fremantle",
    latitude=-32.065,
    longitude=115.747,
    mean_m=0.901,
    source="least-squares fit to UHSLC hourly gauge #175, 2020-2025",
    constituents=(
        _c("K1", 15.0410686, 0.1799, 178.6),
        _c("O1", 13.9430356, 0.1323, 293.6),
        _c("SA", 0.0410686, 0.0918, 138.8),  # seasonal MSL cycle, not a tide
        _c("P1", 14.9589314, 0.0548, 187.5),
        _c("M2", 28.9841042, 0.0513, 171.1),
        _c("S2", 30.0000000, 0.0469, 61.1),
        _c("Q1", 13.3986609, 0.0329, 103.3),
        _c("SSA", 0.0821373, 0.0180, 326.8),
        _c("K2", 30.0821373, 0.0164, 226.5),
        _c("N2", 28.4397295, 0.0152, 37.0),
        _c("J1", 15.5854433, 0.0095, 20.4),
        _c("M1", 14.4966939, 0.0080, 352.7),
        _c("OO1", 16.1391017, 0.0078, 284.3),
        _c("MU2", 27.9682084, 0.0069, 319.9),
        _c("M4", 57.9682084, 0.0049, 35.8),
        _c("2N2", 27.8953548, 0.0043, 195.0),
        _c("T2", 29.9589333, 0.0043, 60.8),
        _c("MF", 1.0980331, 0.0041, 72.2),
        _c("MM", 0.5443747, 0.0038, 259.5),
        _c("MS4", 58.9841042, 0.0037, 351.6),
        _c("L2", 29.5284789, 0.0032, 154.7),
    ),
)

STATIONS: dict[str, TideStation] = {FREMANTLE.key: FREMANTLE}

# A single WA-metro station covers a wide arc of near-identical coast.
_MAX_STATION_DEG = 1.5


def resolve_station(name: str | None, latitude: float, longitude: float) -> TideStation | None:
    """Explicit station key, else the nearest one within range, else ``None``."""

    if name:
        if name.lower() in ("none", "off", ""):
            return None
        station = STATIONS.get(name.lower())
        if station is not None:
            return station
    best: tuple[float, TideStation] | None = None
    for station in STATIONS.values():
        d = math.hypot(station.latitude - latitude, station.longitude - longitude)
        if d <= _MAX_STATION_DEG and (best is None or d < best[0]):
            best = (d, station)
    return best[1] if best else None


def extend_tide_samples(samples: list[TideSample], station: TideStation | None) -> list[TideSample]:
    """Replace trailing ``None`` samples with harmonic predictions.

    The harmonic series is offset so it joins the last real Open-Meteo value
    continuously (the gauge datum differs from Open-Meteo's MSL datum, and only
    the *shape* matters for scoring).
    """

    if station is None:
        return samples

    offset = 0.0
    for s in reversed(samples):
        if s.height_m is not None:
            offset = s.height_m - station.height(s.time_utc)
            break

    out: list[TideSample] = []
    for s in samples:
        if s.height_m is not None:
            out.append(s)
        else:
            out.append(TideSample(s.time_utc, station.height(s.time_utc) + offset))
    return out
