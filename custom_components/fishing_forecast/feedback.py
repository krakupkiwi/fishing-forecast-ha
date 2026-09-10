"""Opportunistic session feedback — the ``fishing_forecast.log_session`` service.

You are not fishing 24/7, so calibration can't depend on constant feedback. This
service is a one-tap log for the times you *do* go out: it records your result
plus a snapshot of what the model scored for that hour, so a later calibration
pass can compare prediction to outcome. Stored via Home Assistant's ``Store``
helper at ``.storage/fishing_forecast_sessions``.
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store
import voluptuous as vol

from .const import DOMAIN
from .serialize import hour_to_dict

_LOGGER = logging.getLogger(__name__)

SERVICE_LOG_SESSION = "log_session"
_STORE_KEY = f"{DOMAIN}_sessions"
_STORE_VERSION = 1
_REGISTERED = f"{DOMAIN}_feedback_registered"

RESULTS = ["poor", "average", "good", "excellent"]

_SCHEMA = vol.Schema(
    {
        vol.Optional("entry_id"): cv.string,
        vol.Optional("location"): cv.string,
        vol.Required("result"): vol.In(RESULTS),
        vol.Optional("at"): cv.datetime,
        vol.Optional("species"): cv.string,
        vol.Optional("notes"): cv.string,
    }
)


@callback
def async_register_feedback_service(hass: HomeAssistant) -> None:
    """Register the service once, for whichever config entry sets up first."""

    if hass.data.get(_REGISTERED):
        return
    hass.data[_REGISTERED] = True
    store: Store[list[dict[str, Any]]] = Store(hass, _STORE_VERSION, _STORE_KEY)

    async def _handle(call: ServiceCall) -> None:
        await _log_session(hass, store, call.data)

    hass.services.async_register(DOMAIN, SERVICE_LOG_SESSION, _handle, schema=_SCHEMA)


def _match_coordinator(hass: HomeAssistant, data: dict[str, Any]) -> Any:
    entries: list[ConfigEntry] = hass.config_entries.async_entries(DOMAIN)
    if data.get("entry_id"):
        entry = hass.config_entries.async_get_entry(data["entry_id"])
        return getattr(entry, "runtime_data", None) if entry else None
    if data.get("location"):
        wanted = data["location"].strip().lower()
        for entry in entries:
            coord = getattr(entry, "runtime_data", None)
            if coord and coord.location.name.strip().lower() == wanted:
                return coord
    if len(entries) == 1:
        return getattr(entries[0], "runtime_data", None)
    return None


async def _log_session(
    hass: HomeAssistant, store: Store[list[dict[str, Any]]], data: dict[str, Any]
) -> None:
    at: datetime = data.get("at") or datetime.now(UTC)
    at = at.astimezone(UTC)

    record: dict[str, Any] = {
        "logged_utc": datetime.now(UTC).isoformat(),
        "at_utc": at.isoformat(),
        "result": data["result"],
        "species": data.get("species"),
        "notes": data.get("notes"),
    }

    coordinator = _match_coordinator(hass, data)
    if coordinator is not None and coordinator.data is not None:
        record["location"] = coordinator.location.name
        record["profile"] = getattr(coordinator, "profile", None)
        hour = min(
            coordinator.data.hourly,
            key=lambda h: abs((h.time_utc - at).total_seconds()),
            default=None,
        )
        if hour is not None and abs((hour.time_utc - at).total_seconds()) <= 5400:
            record["model"] = hour_to_dict(hour)
    else:
        _LOGGER.warning("log_session: no matching location / forecast; logging result only")

    sessions = await store.async_load() or []
    sessions.append(record)
    await store.async_save(sessions)
    _LOGGER.info("Logged fishing session: %s at %s", data["result"], at.isoformat())
