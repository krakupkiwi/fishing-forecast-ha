"""Tide derivation + score. See docs/scoring.md §5.

Provider-independent: ``derive`` takes a plain height series (currently Open-Meteo
``sea_level_height_msl``) so a harmonic model (EOT20 / official source) can replace
it later without touching the score.

The extrema detector is deliberately conservative for Perth's ~0.6 m micro-tidal,
diurnal-dominant range: it requires a minimum prominence and a minimum spacing and
reports ``direction=None`` (unscoreable) when it cannot decide.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from ..models import (
    ScoringConfig,
    TideDirection,
    TideExtreme,
    TideExtremePoint,
    TideSample,
    TideState,
)
from ..util import interpolate

_HOUR = 3600.0

# Internal working representation: (epoch seconds, height metres), non-null only.
_Point = tuple[float, float]


def _refine(points: list[_Point], idx: int) -> _Point:
    """Parabolic sub-sample refinement of an extremum at ``idx``.

    Returns ``(epoch_seconds, height)`` of the fitted vertex.
    """

    if idx <= 0 or idx >= len(points) - 1:
        return points[idx]
    (t0, y0), (t1, y1), (t2, y2) = points[idx - 1], points[idx], points[idx + 1]
    denom = y0 - 2 * y1 + y2
    if denom == 0 or t1 - t0 != t2 - t1:
        return t1, y1
    offset = max(-1.0, min(1.0, 0.5 * (y0 - y2) / denom))
    step = t1 - t0
    return t1 + offset * step, y1 - 0.25 * (y0 - y2) * offset


def _raw_extrema(points: list[_Point]) -> list[TideExtremePoint]:
    out: list[TideExtremePoint] = []
    for i in range(1, len(points) - 1):
        prev_h, h, next_h = points[i - 1][1], points[i][1], points[i + 1][1]
        is_max = h >= prev_h and h >= next_h and (h > prev_h or h > next_h)
        is_min = h <= prev_h and h <= next_h and (h < prev_h or h < next_h)
        if not (is_max or is_min):
            continue
        vt, vy = _refine(points, i)
        out.append(
            TideExtremePoint(
                time_utc=datetime.fromtimestamp(vt, tz=UTC),
                kind=TideExtreme.HIGH if is_max else TideExtreme.LOW,
                height_m=vy,
            )
        )
    return out


def _dedupe_alternating(extrema: list[TideExtremePoint]) -> list[TideExtremePoint]:
    """Collapse runs of same-kind extrema, keeping the most extreme of each run."""

    result: list[TideExtremePoint] = []
    for point in extrema:
        if result and result[-1].kind is point.kind:
            keep_new = (
                point.height_m > result[-1].height_m
                if point.kind is TideExtreme.HIGH
                else point.height_m < result[-1].height_m
            )
            if keep_new:
                result[-1] = point
            continue
        result.append(point)
    return result


def _enforce_spacing(
    extrema: list[TideExtremePoint], min_spacing: timedelta
) -> list[TideExtremePoint]:
    result: list[TideExtremePoint] = []
    for point in extrema:
        if result and (point.time_utc - result[-1].time_utc) < min_spacing:
            # keep whichever is the more pronounced extreme of the pair
            prev = result[-1]
            if prev.kind is point.kind:
                continue
            drop_prev = abs(point.height_m) >= abs(prev.height_m)
            if drop_prev:
                result[-1] = point
            continue
        result.append(point)
    return _dedupe_alternating(result)


def _enforce_prominence(
    extrema: list[TideExtremePoint], min_prominence: float
) -> list[TideExtremePoint]:
    changed = True
    points = list(extrema)
    while changed and len(points) > 2:
        changed = False
        for i in range(1, len(points) - 1):
            prom = min(
                abs(points[i].height_m - points[i - 1].height_m),
                abs(points[i].height_m - points[i + 1].height_m),
            )
            if prom < min_prominence:
                del points[i]
                points = _dedupe_alternating(points)
                changed = True
                break
    return points


def find_extrema(samples: list[TideSample], cfg: ScoringConfig) -> list[TideExtremePoint]:
    """Locate reliable tide highs/lows in a height series (nulls are skipped)."""

    pts: list[_Point] = [
        (s.time_utc.timestamp(), s.height_m) for s in samples if s.height_m is not None
    ]
    if len(pts) < 3:
        return []
    min_spacing = timedelta(hours=float(cfg.tide["min_extreme_spacing_h"]))
    min_prom = float(cfg.tide["min_prominence_m"])
    extrema = _dedupe_alternating(_raw_extrema(pts))
    extrema = _enforce_spacing(extrema, min_spacing)
    extrema = _enforce_prominence(extrema, min_prom)
    return extrema


def derive(samples: list[TideSample], cfg: ScoringConfig) -> list[TideState]:
    """One :class:`TideState` per input sample."""

    valid = [s for s in samples if s.height_m is not None]
    extrema = find_extrema(valid, cfg)

    states: list[TideState] = []
    for i, sample in enumerate(samples):
        if sample.height_m is None or not extrema:
            states.append(
                TideState(sample.time_utc, sample.height_m, None, None, None, None, None, None)
            )
            continue

        prev_pts = [p for p in extrema if p.time_utc <= sample.time_utc]
        next_pts = [p for p in extrema if p.time_utc > sample.time_utc]
        last = prev_pts[-1] if prev_pts else None
        nxt = next_pts[0] if next_pts else None

        if nxt is not None:
            direction = (
                TideDirection.RISING if nxt.kind is TideExtreme.HIGH else TideDirection.FALLING
            )
        elif last is not None:
            direction = (
                TideDirection.RISING if last.kind is TideExtreme.LOW else TideDirection.FALLING
            )
        else:
            direction = None

        mins_to = (
            (nxt.time_utc - sample.time_utc).total_seconds() / 60.0 if nxt is not None else None
        )
        mins_since = (
            (sample.time_utc - last.time_utc).total_seconds() / 60.0 if last is not None else None
        )

        rate = None
        if 0 < i < len(samples) - 1:
            a, b = samples[i - 1], samples[i + 1]
            if a.height_m is not None and b.height_m is not None:
                hours = (b.time_utc - a.time_utc).total_seconds() / _HOUR
                if hours:
                    rate = (b.height_m - a.height_m) / hours

        states.append(
            TideState(
                time_utc=sample.time_utc,
                height_m=sample.height_m,
                direction=direction,
                next_extreme=nxt,
                minutes_to_next_extreme=mins_to,
                last_extreme=last,
                minutes_since_last_extreme=mins_since,
                rate_m_per_h=rate,
            )
        )
    return states


def _hours_relative_to_high(state: TideState) -> float | None:
    if state.next_extreme is not None and state.next_extreme.kind is TideExtreme.HIGH:
        return -(state.minutes_to_next_extreme or 0.0) / 60.0
    if state.last_extreme is not None and state.last_extreme.kind is TideExtreme.HIGH:
        return (state.minutes_since_last_extreme or 0.0) / 60.0
    return None


def score(state: TideState, cfg: ScoringConfig) -> float | None:
    if state.direction is None:
        return None
    t = cfg.tide
    curve = t["relative_to_high_curve"]
    lo, hi = float(curve[0][0]), float(curve[-1][0])

    rel = _hours_relative_to_high(state)
    if rel is not None and lo <= rel <= hi:
        return float(interpolate(curve, rel))

    near_low_mins = None
    if state.next_extreme is not None and state.next_extreme.kind is TideExtreme.LOW:
        near_low_mins = state.minutes_to_next_extreme
    elif state.last_extreme is not None and state.last_extreme.kind is TideExtreme.LOW:
        near_low_mins = state.minutes_since_last_extreme

    if near_low_mins is not None and near_low_mins <= 30.0:
        return float(t["at_low_score"])
    if (
        state.direction is TideDirection.RISING
        and state.last_extreme is not None
        and state.last_extreme.kind is TideExtreme.LOW
        and (state.minutes_since_last_extreme or 0.0) <= 90.0
    ):
        return float(t["early_rise_score"])
    return float(
        t["generic_rising_score"]
        if state.direction is TideDirection.RISING
        else t["generic_falling_score"]
    )
