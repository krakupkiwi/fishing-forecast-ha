"""Sensor platform — Phase 3 (not implemented).

Small entity set only (spec / docs/research.md §5.5). Full hourly data is served
via a websocket command, not entity attributes.

    sensor.fishing_score_<location>        state = today/next best score (0-100)
                                           attrs = rating, best_start, best_end,
                                                   confidence, highlights
    sensor.fishing_best_window_<location>  state = "17:00-20:00"
    sensor.fishing_best_day_<location>     state = date of best upcoming day
                                           attrs = per-day [{date, score, rating,
                                                   confidence, best_window}] (<= 14)

All backed by CoordinatorEntity[FishingForecastCoordinator].
"""

from __future__ import annotations
