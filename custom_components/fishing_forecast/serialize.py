"""Plain-dict serialisers for the core dataclasses (websocket + diagnostics).

Every value here is JSON-native: ISO strings, numbers, bools, None, str enums.
"""

from __future__ import annotations

from typing import Any

from .models import (
    ComponentScores,
    DailyForecast,
    FishingWindow,
    ForecastBundle,
    HourlyScore,
    SolunarPeriod,
    TideExtremePoint,
)


def _round(value: float | None, digits: int = 1) -> float | None:
    return round(value, digits) if value is not None else None


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def window_to_dict(window: FishingWindow | None) -> dict[str, Any] | None:
    if window is None:
        return None
    return {
        "start": window.start_utc.isoformat(),
        "end": window.end_utc.isoformat(),
        "end_is_inclusive_sample": window.is_end_inclusive_sample,
        "score": round(window.score, 1),
    }


def _components_to_dict(components: ComponentScores) -> dict[str, float | None]:
    return {
        comp: (round(value, 1) if value is not None else None)
        for comp, value in (
            ("wind", components.wind),
            ("swell", components.swell),
            ("tide", components.tide),
            ("solunar", components.solunar),
            ("sun", components.sun),
            ("rain", components.rain),
            ("pressure", components.pressure),
        )
    }


def hour_to_dict(hour: HourlyScore) -> dict[str, Any]:
    weather = hour.weather
    marine = hour.marine
    tide = hour.tide
    return {
        "time": hour.time_utc.isoformat(),
        "score": _round(hour.score),
        "rating": hour.rating.value,
        "confidence": hour.confidence.value,
        "components": _components_to_dict(hour.components),
        "weights": {c.value: round(w, 3) for c, w in hour.weights_used.items()},
        "wind_class": hour.wind_class.value if hour.wind_class else None,
        "pressure_trend": hour.pressure_trend.value if hour.pressure_trend else None,
        "inside_major": hour.inside_major,
        "inside_minor": hour.inside_minor,
        # raw conditions for the day-detail view
        "wind_speed_kmh": _round(weather.wind_speed_kmh) if weather else None,
        "wind_direction_deg": _round(weather.wind_direction_deg, 0) if weather else None,
        "wind_gust_kmh": _round(weather.wind_gust_kmh) if weather else None,
        "precip_mm_h": _round(weather.precip_mm_h, 2) if weather else None,
        "pressure_hpa": _round(weather.pressure_msl_hpa) if weather else None,
        "swell_height_m": _round(marine.swell_height_m, 2) if marine else None,
        "swell_period_s": _round(marine.swell_period_s) if marine else None,
        "swell_direction_deg": _round(marine.swell_direction_deg, 0) if marine else None,
        "wave_height_m": _round(marine.wave_height_m, 2) if marine else None,
        "tide_height_m": _round(tide.height_m, 2) if tide else None,
        "tide_state": tide.direction.value if tide and tide.direction else None,
    }


def day_to_dict(day: DailyForecast) -> dict[str, Any]:
    return {
        "date": day.date_local.isoformat(),
        "score": (round(day.score, 1) if day.score is not None else None),
        "rating": day.rating.value,
        "confidence": day.confidence.value,
        "best_window": window_to_dict(day.best_window),
        "second_window": window_to_dict(day.second_window),
        "sunrise": day.sunrise_local,
        "sunset": day.sunset_local,
        "highlights": list(day.highlights),
    }


def bundle_summary(bundle: ForecastBundle) -> dict[str, Any]:
    """Compact view for entity attributes: daily rows only, no hourly."""

    best = bundle.best_day
    return {
        "generated": _iso(bundle.generated_utc),
        "location": bundle.location.name,
        "best_day": best.date_local.isoformat() if best else None,
        "best_score": (round(best.score, 1) if best and best.score is not None else None),
        "best_rating": best.rating.value if best else None,
        "best_window": window_to_dict(best.best_window) if best else None,
        "health": {
            "weather": bundle.health.weather.value,
            "marine_fine": bundle.health.marine_fine.value,
            "marine_extended": bundle.health.marine_extended.value,
            "astronomy": bundle.health.astronomy.value,
        },
        "days": [day_to_dict(d) for d in bundle.daily],
    }


def period_to_dict(period: SolunarPeriod) -> dict[str, Any]:
    return {
        "kind": period.kind.value,
        "start": period.start_utc.isoformat(),
        "end": period.end_utc.isoformat(),
        "centre": period.centre_utc.isoformat(),
        "event": period.centre_event,
    }


def tide_extreme_to_dict(point: TideExtremePoint) -> dict[str, Any]:
    return {
        "time": point.time_utc.isoformat(),
        "kind": point.kind.value,
        "height_m": round(point.height_m, 2),
    }


def bundle_full(bundle: ForecastBundle) -> dict[str, Any]:
    """Everything, for the websocket command and diagnostics."""

    return {
        **bundle_summary(bundle),
        "hourly": [hour_to_dict(h) for h in bundle.hourly],
        "solunar_periods": [period_to_dict(p) for p in bundle.solunar_periods],
        "tide_extremes": [tide_extreme_to_dict(e) for e in bundle.tide_extremes],
    }
