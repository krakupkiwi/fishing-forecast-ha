"""Config & options flow (UI only)."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.helpers import selector
import voluptuous as vol

from .const import (
    CONF_COAST_BEARING,
    CONF_FORECAST_DAYS,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MARINE_LATITUDE,
    CONF_MARINE_LONGITUDE,
    CONF_NAME,
    CONF_TIMEZONE,
    DEFAULT_FORECAST_DAYS,
    DEFAULT_UPDATE_MINUTES,
    DEFAULT_WINDOW_HOURS,
    DOMAIN,
    MAX_FORECAST_DAYS,
    MAX_UPDATE_MINUTES,
    MAX_WINDOW_HOURS,
    MIN_FORECAST_DAYS,
    MIN_UPDATE_MINUTES,
    MIN_WINDOW_HOURS,
    OPT_COAST_BEARING,
    OPT_PREFERRED_END,
    OPT_PREFERRED_START,
    OPT_UPDATE_MINUTES,
    OPT_WEIGHT_PREFIX,
    OPT_WINDOW_HOURS,
    default_scoring_config,
)
from .coordinator import FishingForecastConfigEntry
from .entry_data import slugify_id

_LOCATION = selector.LocationSelector(selector.LocationSelectorConfig(radius=False))
_BEARING = selector.NumberSelector(
    selector.NumberSelectorConfig(min=0, max=359, step=1, mode=selector.NumberSelectorMode.BOX)
)
_DAYS = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=MIN_FORECAST_DAYS,
        max=MAX_FORECAST_DAYS,
        step=1,
        mode=selector.NumberSelectorMode.SLIDER,
    )
)


class FishingForecastConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fishing Forecast."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            land = user_input["land_location"]
            sea = user_input["marine_location"]
            latitude = float(land["latitude"])
            longitude = float(land["longitude"])

            await self.async_set_unique_id(slugify_id(latitude, longitude))
            self._abort_if_unique_id_configured()

            data = {
                CONF_NAME: user_input[CONF_NAME],
                CONF_LATITUDE: latitude,
                CONF_LONGITUDE: longitude,
                CONF_MARINE_LATITUDE: float(sea["latitude"]),
                CONF_MARINE_LONGITUDE: float(sea["longitude"]),
                CONF_COAST_BEARING: float(user_input[CONF_COAST_BEARING]),
                CONF_FORECAST_DAYS: int(user_input[CONF_FORECAST_DAYS]),
                CONF_TIMEZONE: self.hass.config.time_zone,
            }
            return self.async_create_entry(title=user_input[CONF_NAME], data=data)

        home = {
            "latitude": self.hass.config.latitude,
            "longitude": self.hass.config.longitude,
        }
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): selector.TextSelector(),
                vol.Required("land_location", default=home): _LOCATION,
                vol.Required("marine_location", default=home): _LOCATION,
                vol.Required(CONF_COAST_BEARING, default=270): _BEARING,
                vol.Required(CONF_FORECAST_DAYS, default=DEFAULT_FORECAST_DAYS): _DAYS,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(
        config_entry: FishingForecastConfigEntry,
    ) -> FishingForecastOptionsFlow:
        return FishingForecastOptionsFlow()


class FishingForecastOptionsFlow(OptionsFlow):
    """Editable tuning: window, preferred hours, update interval, bearing, weights."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            cleaned = {k: v for k, v in user_input.items() if v is not None}
            return self.async_create_entry(title="", data=cleaned)

        opts = self.config_entry.options
        data = self.config_entry.data
        defaults = default_scoring_config()

        fields: dict[Any, Any] = {
            vol.Required(
                OPT_WINDOW_HOURS,
                default=opts.get(OPT_WINDOW_HOURS, DEFAULT_WINDOW_HOURS),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_WINDOW_HOURS,
                    max=MAX_WINDOW_HOURS,
                    step=1,
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Optional(
                OPT_PREFERRED_START,
                description={"suggested_value": opts.get(OPT_PREFERRED_START)},
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=23, step=1, mode="box")
            ),
            vol.Optional(
                OPT_PREFERRED_END,
                description={"suggested_value": opts.get(OPT_PREFERRED_END)},
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=23, step=1, mode="box")
            ),
            vol.Required(
                OPT_UPDATE_MINUTES,
                default=opts.get(OPT_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_UPDATE_MINUTES,
                    max=MAX_UPDATE_MINUTES,
                    step=5,
                    mode=selector.NumberSelectorMode.SLIDER,
                    unit_of_measurement="min",
                )
            ),
            vol.Required(
                OPT_COAST_BEARING,
                default=opts.get(OPT_COAST_BEARING, data[CONF_COAST_BEARING]),
            ): _BEARING,
        }

        pct = selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=60, step=1, mode="box", unit_of_measurement="%"
            )
        )
        for comp, weight in defaults.full_weights.items():
            key = f"{OPT_WEIGHT_PREFIX}{comp.value}"
            fields[vol.Required(key, default=round(opts.get(key, weight * 100)))] = pct

        return self.async_show_form(step_id="init", data_schema=vol.Schema(fields))
