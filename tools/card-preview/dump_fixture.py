"""Emit a card fixture for tools/card-preview/preview.html.

    python tools/card-preview/dump_fixture.py

Builds a ForecastBundle from the committed Open-Meteo captures in tests/fixtures/
via the HA-free core, then writes card-fixture.json next to this script:

    {
      "state":  { ...the sensor.<loc>_best_fishing_day attributes the card reads },
      "hourly": { ...the fishing_forecast/hourly websocket payload }
    }

Runs in the plain .venv (no Home Assistant needed).
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT))

from custom_components.fishing_forecast.core import build_forecast  # noqa: E402
from custom_components.fishing_forecast.models import LocationConfig  # noqa: E402
from custom_components.fishing_forecast.profiles import scoring_config_for  # noqa: E402
from custom_components.fishing_forecast.serialize import (  # noqa: E402
    bundle_full,
    day_to_dict,
)

# Matches tests/integration/conftest.py's Mindarie config entry.
LOCATION = LocationConfig(
    id="mindarie",
    name="Mindarie",
    latitude=-31.69,
    longitude=115.70,
    marine_latitude=-31.72,
    marine_longitude=115.55,
    coast_bearing=270.0,
    timezone="Australia/Perth",
    elevation_m=6.0,
)
NOW = datetime(2026, 9, 10, 2, 0, tzinfo=UTC)


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def main() -> None:
    bundle = build_forecast(
        LOCATION,
        _load("weather_mindarie.json"),
        _load("marine_mindarie.json"),
        _load("marine_mindarie_gfswave.json"),
        scoring_config_for("beach_sport"),
        days=14,
        now_utc=NOW,
    )
    best = bundle.best_day
    state = {
        "friendly_name": f"{LOCATION.name} Best fishing day",
        "entry_id": "preview",
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
    out = HERE / "card-fixture.json"
    out.write_text(
        json.dumps({"state": state, "hourly": bundle_full(bundle)}, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {out.relative_to(ROOT)} ({len(state['days'])} days, {len(bundle.hourly)} hours)")


if __name__ == "__main__":
    main()
