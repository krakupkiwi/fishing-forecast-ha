"""Shared test fixtures.

The core scoring tests import only ``custom_components.fishing_forecast`` +
stdlib; no Home Assistant. Live API captures live in ``tests/fixtures/``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

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
