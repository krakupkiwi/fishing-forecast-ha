"""Regenerate the committed Open-Meteo fixtures.

    python tests/fixtures/_capture.py

Uses only the stdlib. Overwrites weather_mindarie.json, marine_mindarie.json and
marine_mindarie_gfswave.json in place, and refreshes manifest.json with the
capture timestamp. Keep the request parameters in sync with
custom_components/fishing_forecast/const.py.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import urllib.parse
import urllib.request

HERE = Path(__file__).parent
LAT, LON = -31.69, 115.70
MLAT, MLON = -31.72, 115.55
TZ = "Australia/Perth"

REQUESTS: dict[str, tuple[str, dict[str, str]]] = {
    "weather_mindarie.json": (
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": str(LAT),
            "longitude": str(LON),
            "hourly": "temperature_2m,precipitation,rain,showers,cloud_cover,"
            "surface_pressure,pressure_msl,wind_speed_10m,wind_direction_10m,"
            "wind_gusts_10m,weather_code",
            "daily": "sunrise,sunset,daylight_duration,moonrise,moonset,moon_phase",
            "timezone": TZ,
            "forecast_days": "16",
            "wind_speed_unit": "kmh",
        },
    ),
    "marine_mindarie.json": (
        "https://marine-api.open-meteo.com/v1/marine",
        {
            "latitude": str(MLAT),
            "longitude": str(MLON),
            "hourly": "wave_height,wave_direction,wave_period,swell_wave_height,"
            "swell_wave_direction,swell_wave_period,wind_wave_height,"
            "wind_wave_direction,wind_wave_period,sea_surface_temperature,"
            "ocean_current_velocity,ocean_current_direction,sea_level_height_msl",
            "timezone": TZ,
            "forecast_days": "16",
            "cell_selection": "sea",
        },
    ),
    "marine_mindarie_gfswave.json": (
        "https://marine-api.open-meteo.com/v1/marine",
        {
            "latitude": str(MLAT),
            "longitude": str(MLON),
            "hourly": "wave_height,wave_period,swell_wave_height,swell_wave_direction,"
            "swell_wave_period,wind_wave_height,wind_wave_period",
            "models": "ncep_gfswave025",
            "timezone": TZ,
            "forecast_days": "16",
        },
    ),
}


def main() -> None:
    manifest: dict[str, object] = {
        "captured_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "note": "Live Open-Meteo captures for research + scoring tests. Mindarie WA.",
        "requests": {},
    }
    for name, (url, params) in REQUESTS.items():
        full = f"{url}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(full, timeout=60) as resp:
            data = json.load(resp)
        (HERE / name).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        manifest["requests"][name] = full  # type: ignore[index]
        print(f"wrote {name} ({(HERE / name).stat().st_size} bytes)")
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("wrote manifest.json")


if __name__ == "__main__":
    main()
