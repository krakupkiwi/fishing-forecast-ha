"""Entry setup, coordinator, sensors, graceful degradation."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.fishing_forecast.api._common import OpenMeteoError
from tests.integration.conftest import setup_integration


async def test_setup_creates_sensors(hass: HomeAssistant, config_entry, mock_open_meteo) -> None:
    await setup_integration(hass, config_entry)

    assert config_entry.state is ConfigEntryState.LOADED

    for entity_id in (
        "sensor.mindarie_fishing_score",
        "sensor.mindarie_fishing_conditions_today",
        "sensor.mindarie_best_fishing_window",
        "sensor.mindarie_best_fishing_day",
    ):
        assert hass.states.get(entity_id) is not None, f"{entity_id} missing"

    score = hass.states.get("sensor.mindarie_fishing_score")
    assert score is not None
    assert 0 <= float(score.state) <= 100
    assert score.attributes["rating"] in {
        "exceptional",
        "excellent",
        "good",
        "fair",
        "marginal",
        "poor",
    }

    best_day = hass.states.get("sensor.mindarie_best_fishing_day")
    assert best_day is not None
    assert len(best_day.attributes["days"]) == 14
    assert best_day.attributes["entry_id"] == config_entry.entry_id


async def test_card_is_served(hass: HomeAssistant, config_entry, mock_open_meteo, hass_client):
    from custom_components.fishing_forecast import CARD_URL, LOADER_URL

    await setup_integration(hass, config_entry)
    client = await hass_client()

    resp = await client.get(CARD_URL)
    assert resp.status == 200
    assert 'customElements.define("fishing-forecast-card"' in await resp.text()

    # The loader (what HA actually imports) is served and pulls in the card as a
    # classic <script> — the workaround for Firefox's broken import() of the card.
    loader = await client.get(LOADER_URL)
    assert loader.status == 200
    assert "fishing-forecast-card.js" in await loader.text()


async def test_unload(hass: HomeAssistant, config_entry, mock_open_meteo) -> None:
    await setup_integration(hass, config_entry)
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_weather_failure_blocks_setup(hass: HomeAssistant, config_entry, mock_open_meteo):
    mock_open_meteo["weather"].side_effect = OpenMeteoError("weather down")
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_marine_failure_degrades_to_outlook(
    hass: HomeAssistant, config_entry, mock_open_meteo
):
    mock_open_meteo["marine"].side_effect = OpenMeteoError("marine down")
    await setup_integration(hass, config_entry)

    assert config_entry.state is ConfigEntryState.LOADED
    best_day = hass.states.get("sensor.mindarie_best_fishing_day")
    assert best_day is not None
    assert all(d["confidence"] == "outlook" for d in best_day.attributes["days"])
    assert best_day.attributes["health"]["marine_fine"] == "failed"


async def test_options_change_reloads(hass: HomeAssistant, config_entry, mock_open_meteo):
    await setup_integration(hass, config_entry)
    calls_before = mock_open_meteo["weather"].call_count

    hass.config_entries.async_update_entry(
        config_entry, options={**config_entry.options, "window_hours": 5}
    )
    await hass.async_block_till_done()

    assert mock_open_meteo["weather"].call_count > calls_before
