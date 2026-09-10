"""Config & options flow — Phase 3 (not implemented).

Setup step collects (see docs/research.md §5.4):
    name, latitude, longitude, marine_latitude, marine_longitude,
    coast_bearing, timezone, forecast_days
using HA selectors (LocationSelector, NumberSelector, TextSelector). Unique id is
f"{latitude:.4f}_{longitude:.4f}" with _abort_if_unique_id_configured().

Options flow edits: window_hours, preferred_hours, full/outlook weights,
coast_bearing, swell thresholds.
"""

from __future__ import annotations
