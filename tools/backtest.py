"""Historical backtest: run the scoring engine over Open-Meteo's archive.

    python tools/backtest.py --start 2024-01-01 --end 2025-12-31 --profile beach_sport

Pulls ERA5 weather + the marine archive for a location, scores every hour with the
core engine, and prints a score distribution + the best windows it found, plus a
CSV. This validates that the model produces a *sensible* response to real
conditions; it is not catch-record calibration (there is no free daily catch log
for a beach). See docs/fishing-knowledge.md.

Historical data availability (Mindarie, checked 2026-09):
  weather (wind/gust/rain/pressure/cloud)  1940+   (ERA5)
  swell height/period/direction, waves     ~2022+
  modelled tide (sea_level_height_msl)      ~2024+  (older years: tide scoring off)
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import date
import json
from pathlib import Path
import sys
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from custom_components.fishing_forecast.api.open_meteo_marine import parse_marine  # noqa: E402
from custom_components.fishing_forecast.api.open_meteo_weather import parse_weather  # noqa: E402
from custom_components.fishing_forecast.astronomy import ephemeris, solunar  # noqa: E402
from custom_components.fishing_forecast.models import (  # noqa: E402
    LocationConfig,
    TideSample,
)
from custom_components.fishing_forecast.profiles import scoring_config_for  # noqa: E402
from custom_components.fishing_forecast.scoring import engine  # noqa: E402
from custom_components.fishing_forecast.scoring import tide as tide_mod  # noqa: E402
from custom_components.fishing_forecast.scoring import windows as windows_mod  # noqa: E402
from custom_components.fishing_forecast.util import local_date_of, zone  # noqa: E402

ARCHIVE_WX = "https://archive-api.open-meteo.com/v1/archive"
MARINE = "https://marine-api.open-meteo.com/v1/marine"

MINDARIE = LocationConfig(
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


def _get(url: str, params: dict[str, str]) -> dict:
    full = f"{url}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(full, timeout=120) as resp:
        return json.load(resp)


def fetch(loc: LocationConfig, start: str, end: str) -> tuple[dict, dict]:
    weather = _get(
        ARCHIVE_WX,
        {
            "latitude": str(loc.latitude),
            "longitude": str(loc.longitude),
            "start_date": start,
            "end_date": end,
            "hourly": "temperature_2m,precipitation,rain,showers,cloud_cover,"
            "surface_pressure,pressure_msl,wind_speed_10m,wind_direction_10m,"
            "wind_gusts_10m,weather_code",
            "timezone": loc.timezone,
            "wind_speed_unit": "kmh",
        },
    )
    marine = _get(
        MARINE,
        {
            "latitude": str(loc.marine_latitude),
            "longitude": str(loc.marine_longitude),
            "start_date": start,
            "end_date": end,
            "hourly": "wave_height,wave_period,swell_wave_height,swell_wave_direction,"
            "swell_wave_period,wind_wave_height,wind_wave_period,sea_surface_temperature,"
            "sea_level_height_msl",
            "timezone": loc.timezone,
            "cell_selection": "sea",
        },
    )
    return weather, marine


def score_range(loc: LocationConfig, weather_payload: dict, marine_payload: dict, profile: str):
    cfg = scoring_config_for(profile)
    weather_hours = parse_weather(weather_payload)
    marine_hours = parse_marine(marine_payload, None)
    marine_by_time = {m.time_utc: m for m in marine_hours}

    tide_samples = [TideSample(m.time_utc, m.sea_level_m) for m in marine_hours]
    tide_by_time = {t.time_utc: t for t in tide_mod.derive(tide_samples, cfg)}
    tide_extremes = tide_mod.find_extrema(tide_samples, cfg)

    first = local_date_of(weather_hours[0].time_utc, loc.timezone)
    last = local_date_of(weather_hours[-1].time_utc, loc.timezone)
    astro = ephemeris.compute(loc, first, (last - first).days + 2)
    astro_by_date = {a.date_local: a for a in astro}
    periods = solunar.periods(astro, cfg)

    hourly = engine.score_series(
        loc, weather_hours, marine_by_time, tide_by_time, periods, astro_by_date, cfg
    )
    win = windows_mod.best_windows(loc, hourly, cfg)
    daily = windows_mod.summarise_days(loc, hourly, win, astro_by_date, cfg)
    return hourly, daily, tide_extremes


def histogram(values: list[float], width: int = 40) -> str:
    buckets = Counter(min(9, int(v // 10)) for v in values)
    peak = max(buckets.values()) if buckets else 1
    lines = []
    for b in range(9, -1, -1):
        bar = "#" * round(width * buckets.get(b, 0) / peak)
        lines.append(f"  {b * 10:3d}-{b * 10 + 9:<3d} | {bar} {buckets.get(b, 0)}")
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--profile", default="beach_sport")
    p.add_argument("--csv", default=str(ROOT / "backtest.csv"))
    p.add_argument("--top", type=int, default=25)
    args = p.parse_args()

    loc = MINDARIE
    print(f"Fetching {loc.name} {args.start}..{args.end} ...")
    weather, marine = fetch(loc, args.start, args.end)

    hourly, daily, extremes = score_range(loc, weather, marine, args.profile)
    scored_days = [d for d in daily if d.score is not None]
    scores = [d.score for d in scored_days]

    print(f"\nProfile: {args.profile}   days: {len(scored_days)}   tide extremes: {len(extremes)}")
    print(
        f"daily score  mean {sum(scores) / len(scores):.1f}  "
        f"min {min(scores):.0f}  max {max(scores):.0f}"
    )
    print("\nDaily best-window score distribution:")
    print(histogram(scores))

    by_month: dict[int, list[float]] = defaultdict(list)
    for d in scored_days:
        by_month[d.date_local.month].append(d.score)
    print("\nMean daily score by month:")
    for m in range(1, 13):
        v = by_month.get(m, [])
        if v:
            print(f"  {date(2000, m, 1):%b}: {sum(v) / len(v):5.1f}  (n={len(v)})")

    tz = zone(loc.timezone)
    by_hour: dict[int, list[float]] = defaultdict(list)
    for h in hourly:
        if h.score is not None:
            by_hour[h.time_utc.astimezone(tz).hour].append(h.score)
    print("\nMean hourly score by local hour:")
    for hr in range(24):
        v = by_hour.get(hr, [])
        if v:
            print(f"  {hr:02d}: {sum(v) / len(v):5.1f}")

    top = sorted(scored_days, key=lambda d: d.score, reverse=True)[: args.top]
    print(f"\nTop {args.top} days:")
    for d in top:
        w = d.best_window
        span = (
            f"{w.start_utc.astimezone(tz):%a %d %b %Y %H:%M}-{w.end_utc.astimezone(tz):%H:%M}"
            if w
            else "-"
        )
        print(
            f"  {d.score:5.1f} {d.rating.value:11} {d.confidence.value:7} {span}  "
            f"{', '.join(d.highlights)}"
        )

    with open(args.csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "date",
                "score",
                "rating",
                "confidence",
                "window_start",
                "window_end",
                "sunrise",
                "sunset",
                "highlights",
            ]
        )
        for d in scored_days:
            bw = d.best_window
            w.writerow(
                [
                    d.date_local.isoformat(),
                    round(d.score, 1),
                    d.rating.value,
                    d.confidence.value,
                    bw.start_utc.isoformat() if bw else "",
                    bw.end_utc.isoformat() if bw else "",
                    d.sunrise_local or "",
                    d.sunset_local or "",
                    " | ".join(d.highlights),
                ]
            )
    print(f"\nWrote {args.csv}")


if __name__ == "__main__":
    main()
