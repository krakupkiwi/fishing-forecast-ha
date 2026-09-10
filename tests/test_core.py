"""End-to-end: Open-Meteo payloads -> ForecastBundle (custom_components/.../core.py)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from custom_components.fishing_forecast.const import default_scoring_config
from custom_components.fishing_forecast.core import build_forecast
from custom_components.fishing_forecast.models import Confidence, SourceHealth

CFG = default_scoring_config()
NOW = datetime(2026, 9, 10, 2, 0, tzinfo=UTC)


def test_full_bundle_shape(mindarie, weather_payload, marine_fine_payload, marine_extended_payload):
    bundle = build_forecast(
        mindarie,
        weather_payload,
        marine_fine_payload,
        marine_extended_payload,
        CFG,
        days=14,
        now_utc=NOW,
    )
    assert len(bundle.daily) == 14
    assert len(bundle.hourly) == 14 * 24
    assert bundle.health.weather is SourceHealth.OK
    assert bundle.health.marine_fine is SourceHealth.OK
    assert bundle.health.astronomy is SourceHealth.OK
    assert bundle.best_day is not None
    assert bundle.best_day.score == max(d.score for d in bundle.daily if d.score is not None)


def test_every_hourly_score_is_bounded_or_none(
    mindarie, weather_payload, marine_fine_payload, marine_extended_payload
):
    bundle = build_forecast(
        mindarie, weather_payload, marine_fine_payload, marine_extended_payload, CFG, now_utc=NOW
    )
    for h in bundle.hourly:
        assert h.score is None or 0.0 <= h.score <= 100.0
        assert abs(sum(h.weights_used.values()) - 1.0) < 1e-9 or h.weights_used == {}


def test_confidence_switches_to_outlook_when_tide_runs_out(
    mindarie, weather_payload, marine_fine_payload, marine_extended_payload
):
    bundle = build_forecast(
        mindarie,
        weather_payload,
        marine_fine_payload,
        marine_extended_payload,
        CFG,
        days=14,
        now_utc=NOW,
    )
    confidences = [d.confidence for d in bundle.daily]
    # early days full, later days outlook, and it only transitions once
    assert confidences[0] is Confidence.FULL
    assert confidences[-1] is Confidence.OUTLOOK
    first_outlook = confidences.index(Confidence.OUTLOOK)
    assert 7 <= first_outlook <= 11
    assert all(c is Confidence.OUTLOOK for c in confidences[first_outlook:])


def test_marine_completely_missing_still_produces_outlook(mindarie, weather_payload):
    bundle = build_forecast(mindarie, weather_payload, None, None, CFG, days=10, now_utc=NOW)
    assert len(bundle.daily) == 10
    assert all(d.confidence is Confidence.OUTLOOK for d in bundle.daily)
    assert bundle.health.marine_fine is SourceHealth.FAILED
    assert bundle.health.marine_extended is SourceHealth.FAILED
    # wind/solunar/sun still drive a usable score
    assert any(d.score is not None for d in bundle.daily)
    for h in bundle.hourly:
        assert h.components.swell is None
        assert h.components.tide is None


def test_weather_error_propagates(mindarie):
    from custom_components.fishing_forecast.api._common import OpenMeteoError

    with pytest.raises(OpenMeteoError):
        build_forecast(mindarie, {"error": True, "reason": "boom"}, None, None, CFG)


def test_marine_error_body_degrades_to_outlook(mindarie, weather_payload):
    bundle = build_forecast(
        mindarie,
        weather_payload,
        {"error": True, "reason": "marine boom"},
        None,
        CFG,
        days=8,
        now_utc=NOW,
    )
    assert bundle.health.marine_fine is SourceHealth.FAILED
    assert bundle.health.marine_extended is SourceHealth.FAILED
    assert all(d.confidence is Confidence.OUTLOOK for d in bundle.daily)


def test_astronomy_failure_drops_solunar_and_sun(
    monkeypatch, mindarie, weather_payload, marine_fine_payload, marine_extended_payload
):
    from custom_components.fishing_forecast import core as core_mod

    def _boom(*_a, **_k):
        raise RuntimeError("ephem exploded")

    monkeypatch.setattr(core_mod.ephemeris, "compute", _boom)
    bundle = build_forecast(
        mindarie,
        weather_payload,
        marine_fine_payload,
        marine_extended_payload,
        CFG,
        days=6,
        now_utc=NOW,
    )
    assert bundle.health.astronomy is SourceHealth.FAILED
    for h in bundle.hourly:
        assert h.components.solunar is None
        assert h.components.sun is None
    # wind / swell / tide / rain / pressure still drive a score
    assert any(d.score is not None for d in bundle.daily)


def test_daily_summary_has_local_sun_times(
    mindarie, weather_payload, marine_fine_payload, marine_extended_payload
):
    bundle = build_forecast(
        mindarie, weather_payload, marine_fine_payload, marine_extended_payload, CFG, now_utc=NOW
    )
    day = bundle.daily[0]
    assert day.sunrise_local and ":" in day.sunrise_local
    assert day.sunset_local and ":" in day.sunset_local
