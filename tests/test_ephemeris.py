"""ephem-based astronomy, cross-checked against Open-Meteo's own daily fields.

These assert agreement within a tolerance, not equality: Open-Meteo and ephem use
different algorithms/refraction. If ephem drifts far from a second independent
source, that is the signal to investigate (see docs/research.md §9 item 4).
"""

from __future__ import annotations

from datetime import date, timedelta

from custom_components.fishing_forecast.api.open_meteo_weather import parse_daily_astro
from custom_components.fishing_forecast.astronomy.ephemeris import astro_day, compute
from custom_components.fishing_forecast.models import LocationConfig


def _loc_from_payload(payload: dict) -> LocationConfig:
    lat, lon = payload["latitude"], payload["longitude"]
    return LocationConfig(
        id="grid",
        name="grid",
        latitude=lat,
        longitude=lon,
        marine_latitude=lat,
        marine_longitude=lon,
        coast_bearing=270.0,
        timezone=payload["timezone"],
        elevation_m=float(payload.get("elevation", 0.0)),
    )


def test_sun_times_match_open_meteo(weather_payload: dict) -> None:
    loc = _loc_from_payload(weather_payload)
    api_days = parse_daily_astro(weather_payload)
    for api in api_days[:10]:
        got = astro_day(loc, api.date_local)
        assert abs(got.sunrise_utc - api.sunrise_utc) < timedelta(minutes=4)
        assert abs(got.sunset_utc - api.sunset_utc) < timedelta(minutes=4)


def test_moon_rise_set_roughly_match_open_meteo(weather_payload: dict) -> None:
    loc = _loc_from_payload(weather_payload)
    close = 0
    total = 0
    for api in parse_daily_astro(weather_payload)[:10]:
        got = astro_day(loc, api.date_local)
        for mine, theirs in (
            (got.moonrise_utc, api.moonrise_utc),
            (got.moonset_utc, api.moonset_utc),
        ):
            if mine is None or theirs is None:
                continue
            total += 1
            if abs(mine - theirs) < timedelta(minutes=25):
                close += 1
    assert total >= 12
    assert close / total >= 0.8


def test_moon_phase_fraction_matches(weather_payload: dict) -> None:
    loc = _loc_from_payload(weather_payload)
    for api in parse_daily_astro(weather_payload)[:12]:
        got = astro_day(loc, api.date_local)
        diff = abs(got.moon_phase_fraction - api.moon_phase_fraction)
        diff = min(diff, 1.0 - diff)  # wrap at the new-moon boundary
        assert diff < 0.05


def test_transits_present_and_ordered(mindarie: LocationConfig) -> None:
    days = compute(mindarie, date(2026, 9, 13), 5)
    for d in days:
        assert d.moon_upper_transit_utc is not None
        assert d.moon_lower_transit_utc is not None


def test_illumination_tracks_phase(mindarie: LocationConfig) -> None:
    days = compute(mindarie, date(2026, 9, 10), 20)
    # 2026-09-11 is a new moon (fixture) -> illumination near 0 then rising
    new_moon = min(days, key=lambda d: d.moon_phase_fraction)
    assert new_moon.moon_illumination < 0.05
