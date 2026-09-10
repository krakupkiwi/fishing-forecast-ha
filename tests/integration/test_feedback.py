"""The fishing_forecast.log_session feedback service."""

from __future__ import annotations

from datetime import UTC, datetime

from homeassistant.core import HomeAssistant

from custom_components.fishing_forecast.feedback import _STORE_KEY
from tests.integration.conftest import setup_integration


async def test_log_session_stores_result_with_model_snapshot(
    hass: HomeAssistant, config_entry, mock_open_meteo, hass_storage
) -> None:
    await setup_integration(hass, config_entry)
    assert hass.services.has_service("fishing_forecast", "log_session")

    bundle = config_entry.runtime_data.data
    when = bundle.hourly[30].time_utc  # a real forecast hour

    await hass.services.async_call(
        "fishing_forecast",
        "log_session",
        {"result": "good", "species": "tailor", "at": when.isoformat()},
        blocking=True,
    )

    stored = hass_storage[_STORE_KEY]["data"]
    assert len(stored) == 1
    rec = stored[0]
    assert rec["result"] == "good"
    assert rec["species"] == "tailor"
    assert rec["location"] == "Mindarie"
    assert rec["profile"] == "beach_sport"
    assert rec["model"]["score"] is not None
    assert "wind_speed_kmh" in rec["model"]


async def test_log_session_without_forecast_still_records(
    hass: HomeAssistant, config_entry, mock_open_meteo, hass_storage
) -> None:
    await setup_integration(hass, config_entry)
    await hass.services.async_call(
        "fishing_forecast",
        "log_session",
        {"result": "poor", "at": datetime(2019, 1, 1, tzinfo=UTC).isoformat()},
        blocking=True,
    )
    rec = hass_storage[_STORE_KEY]["data"][0]
    assert rec["result"] == "poor"
    assert "model" not in rec  # 2019 is nowhere near the forecast window
