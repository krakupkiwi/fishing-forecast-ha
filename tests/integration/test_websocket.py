"""The fishing_forecast/hourly websocket command."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from tests.integration.conftest import setup_integration


async def test_ws_hourly_returns_full_series(
    hass: HomeAssistant, config_entry, mock_open_meteo, hass_ws_client
) -> None:
    await setup_integration(hass, config_entry)
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {"type": "fishing_forecast/hourly", "entry_id": config_entry.entry_id}
    )
    response = await client.receive_json()

    assert response["success"]
    result = response["result"]
    assert len(result["hourly"]) == 14 * 24
    assert len(result["days"]) == 14
    first = result["hourly"][0]
    assert set(first) >= {"time", "score", "rating", "confidence", "components", "weights"}


async def test_ws_hourly_unknown_entry(
    hass: HomeAssistant, config_entry, mock_open_meteo, hass_ws_client
) -> None:
    await setup_integration(hass, config_entry)
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {"type": "fishing_forecast/hourly", "entry_id": "does-not-exist"}
    )
    response = await client.receive_json()
    assert not response["success"]
    assert response["error"]["code"] == "not_found"
