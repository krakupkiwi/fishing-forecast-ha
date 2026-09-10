"""Config + options flow."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.fishing_forecast.const import (
    CONF_MARINE_LATITUDE,
    CONF_NAME,
    DOMAIN,
    OPT_WINDOW_HOURS,
)

_USER_INPUT = {
    CONF_NAME: "Mindarie",
    "land_location": {"latitude": -31.69, "longitude": 115.70},
    "marine_location": {"latitude": -31.72, "longitude": 115.55},
    "coast_bearing": 270,
    "forecast_days": 14,
}


async def test_user_flow_creates_entry(hass: HomeAssistant, mock_open_meteo) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(result["flow_id"], _USER_INPUT)
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Mindarie"
    assert result["data"][CONF_MARINE_LATITUDE] == -31.72
    assert result["data"]["coast_bearing"] == 270


async def test_duplicate_location_aborts(hass: HomeAssistant, mock_open_meteo) -> None:
    first = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    await hass.config_entries.flow.async_configure(first["flow_id"], _USER_INPUT)
    await hass.async_block_till_done()

    second = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(second["flow_id"], _USER_INPUT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow_round_trip(hass: HomeAssistant, config_entry, mock_open_meteo) -> None:
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    submit = {
        OPT_WINDOW_HOURS: 4,
        "update_interval_minutes": 45,
        "coast_bearing": 260,
        "weight_wind": 40,
        "weight_swell": 20,
        "weight_tide": 15,
        "weight_solunar": 15,
        "weight_sun": 10,
        "weight_rain": 5,
        "weight_pressure": 5,
    }
    result = await hass.config_entries.options.async_configure(result["flow_id"], submit)
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options[OPT_WINDOW_HOURS] == 4
    assert config_entry.options["coast_bearing"] == 260
