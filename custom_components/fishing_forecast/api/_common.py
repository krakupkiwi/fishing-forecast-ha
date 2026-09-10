"""Shared Open-Meteo response helpers (no network)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Any

from ..util import to_utc


class OpenMeteoError(RuntimeError):
    """Raised for an Open-Meteo ``{"error": true, "reason": ...}`` body."""


def raise_for_error(payload: dict[str, Any]) -> None:
    if payload.get("error"):
        raise OpenMeteoError(str(payload.get("reason", "unknown Open-Meteo error")))


def hourly_rows(payload: dict[str, Any]) -> Iterator[tuple[datetime, dict[str, Any]]]:
    """Yield ``(utc_instant, {field: value})`` for each hourly timestamp.

    Timestamps are the naive local strings Open-Meteo returns; they are combined
    with ``utc_offset_seconds`` from the payload and converted to aware UTC.
    """

    raise_for_error(payload)
    hourly = payload.get("hourly")
    if not hourly:
        return
    offset = int(payload.get("utc_offset_seconds", 0))
    times = hourly["time"]
    fields = [k for k in hourly if k != "time"]
    for i, stamp in enumerate(times):
        instant = to_utc(datetime.fromisoformat(stamp), offset)
        yield instant, {f: hourly[f][i] for f in fields}


def daily_rows(payload: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield ``(date_str, {field: value})`` for each daily entry."""

    raise_for_error(payload)
    daily = payload.get("daily")
    if not daily:
        return
    times = daily["time"]
    fields = [k for k in daily if k != "time"]
    for i, day in enumerate(times):
        yield day, {f: daily[f][i] for f in fields}


def opt_float(value: Any) -> float | None:
    return None if value is None else float(value)


def opt_int(value: Any) -> int | None:
    return None if value is None else int(value)
