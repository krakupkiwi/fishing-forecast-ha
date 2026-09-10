"""DataUpdateCoordinator — Phase 3 (not implemented).

Planned shape (verified against the current HA dev "Fetching data" docs, 2026-09):

    class FishingForecastCoordinator(DataUpdateCoordinator[ForecastBundle]):
        def __init__(self, hass, config_entry, client):
            super().__init__(
                hass,
                _LOGGER,
                name=f"Fishing Forecast {config_entry.title}",
                config_entry=config_entry,
                update_interval=timedelta(minutes=DEFAULT_UPDATE_MINUTES),
                always_update=False,   # ForecastBundle is a frozen dataclass
            )

        async def _async_setup(self) -> None:
            # resolve tz, validate coordinates once
            ...

        async def _async_update_data(self) -> ForecastBundle:
            # 1 weather  2 marine (best_match + gfswave, merged)
            # 3 astro via hass.async_add_executor_job(ephemeris.compute, ...)
            # 4 tide.derive  5 solunar.periods
            # 6 engine.score_hours  7 windows.best  8 daily summaries
            # raise UpdateFailed(...) on transient errors; keep last good bundle
            ...

See docs/architecture.md "Graceful degradation".
"""

from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)
