"""Shared test fixtures and builders.

Core tests import only ``custom_components.fishing_forecast`` + stdlib + ``ephem``;
no Home Assistant. Live Open-Meteo captures live in ``tests/fixtures/``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from typing import Any

import pytest

from custom_components.fishing_forecast.models import LocationConfig

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def weather_payload() -> dict[str, Any]:
    """Open-Meteo /v1/forecast best_match, Mindarie, 16 days (all fields non-null)."""

    return _load("weather_mindarie.json")


@pytest.fixture
def marine_fine_payload() -> dict[str, Any]:
    """Open-Meteo /v1/marine best_match — ~9.5 days of data then null (tide included)."""

    return _load("marine_mindarie.json")


@pytest.fixture
def marine_extended_payload() -> dict[str, Any]:
    """Open-Meteo /v1/marine ncep_gfswave025 — waves/swell for the full 16 days."""

    return _load("marine_mindarie_gfswave.json")


@pytest.fixture
def mindarie() -> LocationConfig:
    return LocationConfig(
        id="mindarie",
        name="Mindarie",
        latitude=-31.69,
        longitude=115.70,
        marine_latitude=-31.72,
        marine_longitude=115.55,
        coast_bearing=270.0,
        timezone="Australia/Perth",
        elevation_m=6.0,
    )


def utc(y: int, m: int, d: int, h: int = 0, minute: int = 0) -> datetime:
    return datetime(y, m, d, h, minute, tzinfo=UTC)


def hours(start: datetime, count: int) -> list[datetime]:
    return [start + timedelta(hours=i) for i in range(count)]
