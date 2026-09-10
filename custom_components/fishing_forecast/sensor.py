"""Sensor platform — a small, useful entity set (see docs/research.md §5.5).

The full 336-row hourly series is NOT in attributes; the card fetches it via the
``fishing_forecast/hourly`` websocket command. Only the ~14-row daily summary
rides along on the ``best_day`` sensor.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import FishingForecastConfigEntry, FishingForecastCoordinator
from .models import DailyForecast, ForecastBundle
from .serialize import day_to_dict, window_to_dict
from .util import hhmm_local, zone


@dataclass(frozen=True, kw_only=True)
class FishingSensorDescription:
    key: str
    translation_key: str
    icon: str
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    value_fn: Callable[[ForecastBundle, str], Any]
    attr_fn: Callable[[ForecastBundle, str], dict[str, Any]]


def _today(bundle: ForecastBundle, tz: str) -> DailyForecast | None:
    today = datetime.now(UTC).astimezone(zone(tz)).date()
    return next((d for d in bundle.daily if d.date_local == today), None)


def _score_value(bundle: ForecastBundle, tz: str) -> float | None:
    best = bundle.best_day
    return round(best.score, 1) if best and best.score is not None else None


def _score_attrs(bundle: ForecastBundle, tz: str) -> dict[str, Any]:
    best = bundle.best_day
    if best is None:
        return {}
    return {
        "rating": best.rating.value,
        "best_day": best.date_local.isoformat(),
        "confidence": best.confidence.value,
        "best_window": window_to_dict(best.best_window),
        "best_window_start": hhmm_local(
            best.best_window.start_utc if best.best_window else None, tz
        ),
        "best_window_end": hhmm_local(best.best_window.end_utc if best.best_window else None, tz),
        "highlights": list(best.highlights),
        "generated": bundle.generated_utc.isoformat(),
    }


def _today_value(bundle: ForecastBundle, tz: str) -> float | None:
    day = _today(bundle, tz)
    return round(day.score, 1) if day and day.score is not None else None


def _today_attrs(bundle: ForecastBundle, tz: str) -> dict[str, Any]:
    day = _today(bundle, tz)
    if day is None:
        return {}
    return {
        "rating": day.rating.value,
        "confidence": day.confidence.value,
        "best_window": window_to_dict(day.best_window),
        "highlights": list(day.highlights),
    }


def _window_value(bundle: ForecastBundle, tz: str) -> str | None:
    best = bundle.best_day
    if best is None or best.best_window is None:
        return None
    start = hhmm_local(best.best_window.start_utc, tz)
    end = hhmm_local(best.best_window.end_utc, tz)
    return f"{start}-{end}"


def _window_attrs(bundle: ForecastBundle, tz: str) -> dict[str, Any]:
    best = bundle.best_day
    if best is None or best.best_window is None:
        return {}
    return {
        "date": best.date_local.isoformat(),
        "score": round(best.best_window.score, 1),
        "start": best.best_window.start_utc.isoformat(),
        "end": best.best_window.end_utc.isoformat(),
        "rating": best.rating.value,
    }


def _best_day_value(bundle: ForecastBundle, tz: str) -> date | None:
    return bundle.best_day.date_local if bundle.best_day else None


def _best_day_attrs(bundle: ForecastBundle, tz: str) -> dict[str, Any]:
    best = bundle.best_day
    return {
        "score": round(best.score, 1) if best and best.score is not None else None,
        "rating": best.rating.value if best else None,
        "confidence": best.confidence.value if best else None,
        "days": [day_to_dict(d) for d in bundle.daily],
        "health": {
            "weather": bundle.health.weather.value,
            "marine_fine": bundle.health.marine_fine.value,
            "marine_extended": bundle.health.marine_extended.value,
            "astronomy": bundle.health.astronomy.value,
        },
    }


SENSORS: tuple[FishingSensorDescription, ...] = (
    FishingSensorDescription(
        key="score",
        translation_key="score",
        icon="mdi:fish",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_score_value,
        attr_fn=_score_attrs,
    ),
    FishingSensorDescription(
        key="today",
        translation_key="today",
        icon="mdi:hook",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_today_value,
        attr_fn=_today_attrs,
    ),
    FishingSensorDescription(
        key="best_window",
        translation_key="best_window",
        icon="mdi:clock-time-four-outline",
        value_fn=_window_value,
        attr_fn=_window_attrs,
    ),
    FishingSensorDescription(
        key="best_day",
        translation_key="best_day",
        icon="mdi:calendar-star",
        device_class=SensorDeviceClass.DATE,
        value_fn=_best_day_value,
        attr_fn=_best_day_attrs,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FishingForecastConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        FishingForecastSensor(coordinator, entry, description) for description in SENSORS
    )


class FishingForecastSensor(CoordinatorEntity[FishingForecastCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FishingForecastCoordinator,
        entry: FishingForecastConfigEntry,
        description: FishingSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self._description = description
        self._tz = coordinator.location.timezone
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_translation_key = description.translation_key
        self._attr_icon = description.icon
        if description.device_class:
            self._attr_device_class = description.device_class
        if description.state_class:
            self._attr_state_class = description.state_class
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model="Land-based fishing forecast",
        )

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        return self._description.value_fn(self.coordinator.data, self._tz)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self.coordinator.data is None:
            return {}
        return self._description.attr_fn(self.coordinator.data, self._tz)
