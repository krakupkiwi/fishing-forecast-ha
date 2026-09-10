"""JSON serialisation of a ForecastBundle (used by the websocket command + card)."""

from __future__ import annotations

from datetime import UTC, datetime
import json

from custom_components.fishing_forecast.const import default_scoring_config
from custom_components.fishing_forecast.core import build_forecast
from custom_components.fishing_forecast.entry_data import location_from_entry
from custom_components.fishing_forecast.serialize import bundle_full, bundle_summary

CFG = default_scoring_config()
NOW = datetime(2026, 9, 10, 2, tzinfo=UTC)
DATA = {
    "name": "Mindarie",
    "latitude": -31.69,
    "longitude": 115.70,
    "marine_latitude": -31.72,
    "marine_longitude": 115.55,
    "coast_bearing": 270.0,
    "timezone": "Australia/Perth",
}


def _bundle(weather_payload, marine_fine_payload, marine_extended_payload):
    loc = location_from_entry(DATA, {})
    return build_forecast(
        loc,
        weather_payload,
        marine_fine_payload,
        marine_extended_payload,
        CFG,
        days=14,
        now_utc=NOW,
    )


def test_bundle_summary_is_json_native(
    weather_payload, marine_fine_payload, marine_extended_payload
):
    summary = bundle_summary(_bundle(weather_payload, marine_fine_payload, marine_extended_payload))
    json.dumps(summary)  # must not raise
    assert len(summary["days"]) == 14
    assert summary["best_day"] is not None
    assert set(summary["health"]) == {"weather", "marine_fine", "marine_extended", "astronomy"}
    day = summary["days"][0]
    assert set(day) >= {"date", "score", "rating", "confidence", "best_window", "highlights"}


def test_bundle_full_has_hourly_raw_and_markers(
    weather_payload, marine_fine_payload, marine_extended_payload
):
    full = bundle_full(_bundle(weather_payload, marine_fine_payload, marine_extended_payload))
    json.dumps(full)

    assert len(full["hourly"]) == 14 * 24
    hour = full["hourly"][24]
    assert set(hour) >= {
        "time",
        "score",
        "wind_speed_kmh",
        "wind_direction_deg",
        "swell_height_m",
        "swell_period_s",
        "tide_state",
        "components",
    }

    assert full["solunar_periods"]
    assert {p["kind"] for p in full["solunar_periods"]} <= {"major", "minor"}
    assert full["tide_extremes"]
    assert {e["kind"] for e in full["tide_extremes"]} <= {"high", "low"}


def test_outlook_days_have_no_marine_raw_but_keep_harmonic_tide(weather_payload):
    full = bundle_full(_bundle(weather_payload, None, None))
    for hour in full["hourly"]:
        assert hour["swell_height_m"] is None
    # harmonic tide (Mindarie -> Fremantle) still fills the tide fields + markers
    assert any(h["tide_state"] is not None for h in full["hourly"])
    assert full["tide_extremes"]
