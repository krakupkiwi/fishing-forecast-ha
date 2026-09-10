"""Home Assistant integration-test fixtures.

Requires `pytest-homeassistant-custom-component` (the `ha` optional-dependency
group). ``tests/conftest.py`` skips this whole directory when Home Assistant is
not importable.
"""

from __future__ import annotations

from collections.abc import Iterator
import json
from pathlib import Path
import sys
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

# Home Assistant's test suite needs a POSIX event loop; its Windows
# ProactorEventLoop trips pytest-socket during fixture setup. CI runs these on
# Linux (see .github/workflows/ci.yml, the `integration` job).
if sys.platform == "win32":  # pragma: no cover
    collect_ignore_glob = ["*"]

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fishing_forecast.const import (
    CONF_COAST_BEARING,
    CONF_FORECAST_DAYS,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MARINE_LATITUDE,
    CONF_MARINE_LONGITUDE,
    CONF_NAME,
    CONF_PROFILE,
    CONF_TIMEZONE,
    DOMAIN,
)

_FIXTURES = Path(__file__).parents[1] / "fixtures"


def _load(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _auto_enable_custom_integrations(
    enable_custom_integrations: Any,
) -> Iterator[None]:
    yield


@pytest.fixture
def mock_open_meteo() -> Iterator[dict[str, AsyncMock]]:
    """Patch the HTTP client so no network is touched; returns the fixture JSON."""

    weather = _load("weather_mindarie.json")
    fine = _load("marine_mindarie.json")
    ext = _load("marine_mindarie_gfswave.json")

    async def get_weather(_self: Any, *_a: Any, **_k: Any) -> dict[str, Any]:
        return weather

    async def get_marine(_self: Any, *_a: Any, extended: bool = False, **_k: Any) -> dict[str, Any]:
        return ext if extended else fine

    target = "custom_components.fishing_forecast.api.client.OpenMeteoClient"
    with (
        patch(f"{target}.async_get_weather", autospec=True, side_effect=get_weather) as w,
        patch(f"{target}.async_get_marine", autospec=True, side_effect=get_marine) as m,
    ):
        yield {"weather": w, "marine": m}


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Mindarie",
        unique_id="m31_6900_115_7000",
        data={
            CONF_NAME: "Mindarie",
            CONF_LATITUDE: -31.69,
            CONF_LONGITUDE: 115.70,
            CONF_MARINE_LATITUDE: -31.72,
            CONF_MARINE_LONGITUDE: 115.55,
            CONF_COAST_BEARING: 270.0,
            CONF_FORECAST_DAYS: 14,
            CONF_PROFILE: "beach_sport",
            CONF_TIMEZONE: "Australia/Perth",
        },
    )
    entry.add_to_hass(hass)
    return entry


async def setup_integration(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
