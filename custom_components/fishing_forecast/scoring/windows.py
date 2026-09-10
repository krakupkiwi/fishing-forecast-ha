"""Rolling best-window selection + daily aggregation. See docs/scoring.md §11-§13.

The daily score is the best window's score, not the 24-hour mean, so a day with
one great session surrounded by junk is not punished.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, timedelta

from ..models import (
    AstroDay,
    Confidence,
    DailyForecast,
    FishingWindow,
    HourlyScore,
    LocationConfig,
    ScoringConfig,
    rating_for,
)
from ..util import hhmm_local, local_date_of, local_hour_of

_HOUR = timedelta(hours=1)
_CENTRE_BOOST = 0.3


def triangular_weights(n: int, boost: float = _CENTRE_BOOST) -> list[float]:
    if n <= 1:
        return [1.0] * max(n, 0)
    mid = (n - 1) / 2
    return [1.0 + boost * (1.0 - abs(i - mid) / mid) for i in range(n)]


def _runs(hourly: Sequence[HourlyScore]) -> list[list[HourlyScore]]:
    """Maximal runs of consecutive (1 h apart) hours with a non-None score."""

    runs: list[list[HourlyScore]] = []
    current: list[HourlyScore] = []
    for h in hourly:
        if h.score is None:
            if current:
                runs.append(current)
                current = []
            continue
        if current and h.time_utc - current[-1].time_utc != _HOUR:
            runs.append(current)
            current = []
        current.append(h)
    if current:
        runs.append(current)
    return runs


def best_windows(
    location: LocationConfig, hourly: Sequence[HourlyScore], cfg: ScoringConfig
) -> list[FishingWindow]:
    """All valid rolling windows, best score first."""

    n = max(1, int(cfg.window_hours))
    weights = triangular_weights(n)
    wsum = sum(weights)
    pref = cfg.preferred_hours

    windows: list[FishingWindow] = []
    for run in _runs(hourly):
        for i in range(len(run) - n + 1):
            block = run[i : i + n]
            if pref is not None and not all(
                pref[0] <= local_hour_of(h.time_utc, location.timezone) <= pref[1] for h in block
            ):
                continue
            # _runs() guarantees every block hour has a non-None score.
            block_scores: list[float] = [h.score for h in block if h.score is not None]
            score = sum(w * s for w, s in zip(weights, block_scores, strict=True)) / wsum
            windows.append(
                FishingWindow(
                    start_utc=block[0].time_utc,
                    end_utc=block[-1].time_utc + _HOUR,
                    score=score,
                )
            )
    windows.sort(key=lambda w: w.score, reverse=True)
    return windows


def _overlaps(a: FishingWindow, b: FishingWindow) -> bool:
    return a.start_utc < b.end_utc and b.start_utc < a.end_utc


def _highlights(block: Sequence[HourlyScore], tz: str) -> tuple[str, ...]:
    out: list[str] = []
    winds = [h.components.wind for h in block if h.components.wind is not None]
    if (
        winds
        and sum(winds) / len(winds) >= 80
        and any(h.wind_class is not None and "offshore" in h.wind_class.value for h in block)
    ):
        out.append("Light offshore wind")
    if any(h.inside_major for h in block):
        out.append("Major solunar period")
    elif any(h.inside_minor for h in block):
        out.append("Minor solunar period")
    tides = [h.components.tide for h in block if h.components.tide is not None]
    if tides and sum(tides) / len(tides) >= 80:
        out.append("Strong tide through the window")
    suns = [(h.components.sun or 0.0, local_hour_of(h.time_utc, tz)) for h in block]
    if any(v >= 90 for v, _ in suns):
        hour = next(hr for v, hr in suns if v >= 90)
        out.append("Overlaps sunrise" if hour < 12 else "Overlaps sunset")
    swells = [h.components.swell for h in block if h.components.swell is not None]
    if swells and sum(swells) / len(swells) >= 85:
        out.append("Clean swell")
    return tuple(out[:4])


def summarise_days(
    location: LocationConfig,
    hourly: Sequence[HourlyScore],
    windows: Sequence[FishingWindow],
    astro_by_date: Mapping[date, AstroDay],
    cfg: ScoringConfig,
) -> list[DailyForecast]:
    tz = location.timezone
    by_day: dict[date, list[HourlyScore]] = {}
    for h in hourly:
        by_day.setdefault(local_date_of(h.time_utc, tz), []).append(h)

    hour_by_time = {h.time_utc: h for h in hourly}
    days: list[DailyForecast] = []
    for day in sorted(by_day):
        day_windows = [w for w in windows if local_date_of(w.start_utc, tz) == day]
        best = day_windows[0] if day_windows else None
        second = next((w for w in day_windows[1:] if best and not _overlaps(w, best)), None)

        prime = [h for h in by_day[day] if 6 <= local_hour_of(h.time_utc, tz) <= 21]
        full = sum(1 for h in prime if h.confidence is Confidence.FULL)
        confidence = (
            Confidence.FULL
            if prime and full / len(prime) >= cfg.day_full_hours_fraction
            else Confidence.OUTLOOK
        )

        score = best.score if best else None
        highlights: tuple[str, ...] = ()
        if best is not None:
            block = [
                hour_by_time[best.start_utc + i * _HOUR]
                for i in range(int((best.end_utc - best.start_utc) / _HOUR))
                if best.start_utc + i * _HOUR in hour_by_time
            ]
            highlights = _highlights(block, tz)

        astro = astro_by_date.get(day)
        days.append(
            DailyForecast(
                date_local=day,
                score=score,
                rating=rating_for(score),
                confidence=confidence,
                best_window=best,
                second_window=second,
                sunrise_local=hhmm_local(astro.sunrise_utc if astro else None, tz),
                sunset_local=hhmm_local(astro.sunset_utc if astro else None, tz),
                highlights=highlights,
            )
        )
    return days
