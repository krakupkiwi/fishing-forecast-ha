"""Config-entry diagnostics — Phase 3 (not implemented).

Dumps the last ForecastBundle (hourly + daily), the resolved ScoringConfig, and
DataHealth. Redacts nothing sensitive (no credentials exist) except the precise
home coordinates if they match the HA home location.
"""

from __future__ import annotations
