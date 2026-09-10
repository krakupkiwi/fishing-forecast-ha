# Scoring model & assumptions

This is the **authoritative reference** for every constant in the scoring engine.
Code in `custom_components/fishing_forecast/scoring/` must read these values from
`ScoringConfig` (defaults defined in `const.py`), never hard-code them inline.

Everything here is an **initial, configurable default** — a heuristic in the
tradition of published fishing/solunar tables, calibrated later against real
sessions (Phase 5). It is not claimed to be scientifically validated.

Conventions:

- Every component function returns a float in **`[0, 100]`**, or **`None`** if its
  required input is missing. `None` is *not* `0` — see §10.
- All angles are degrees, meteorological "coming from" convention (0° = N, 90° = E),
  **except** ocean current direction (heading-toward), which V1 does not score.
- Wind speed in km/h, heights in m, periods in s, pressure in hPa, rain in mm/h.
- "Smooth" means linear interpolation between the tabulated breakpoints unless a
  curve is specified.

---

## 1. Component weights

### Full forecast (tide + fine marine available)

| Component | Weight |
|---|---:|
| wind | 0.30 |
| swell | 0.20 |
| tide | 0.15 |
| solunar | 0.15 |
| sun (dawn/dusk) | 0.10 |
| rain | 0.05 |
| pressure | 0.05 |

### Outlook (no modelled tide / coarse or no marine)

| Component | Weight |
|---|---:|
| wind | 0.50 |
| solunar | 0.20 |
| sun (dawn/dusk) | 0.12 |
| rain | 0.09 |
| pressure | 0.09 |

Swell is **absent** from the outlook set even though `ncep_gfswave025` often supplies
swell to day 16 — because at 0.25° the near-shore exposure is unreliable. If Phase 5
shows coarse swell adds value, add it back at ~0.10 and rescale.

### Renormalisation (§10)

When any component is `None` for a given hour, drop it and divide the remaining
weights by their sum so they total 1.0. The engine records the resulting weights on
`HourlyScore.weights_used`.

---

## 2. Score categories

| Score | Rating (semantic key) |
|---|---|
| 90–100 | `exceptional` |
| 80–89 | `excellent` |
| 70–79 | `good` |
| 60–69 | `fair` |
| 50–59 | `marginal` |
| 0–49 | `poor` |

Backend emits `{ "score": int, "rating": str }`. **No colours in the backend** — the
card maps ratings to colour.

---

## 3. Wind

### 3.1 Speed sub-score (direction-independent), km/h

Smooth interpolation through:

| Speed | Sub-score |
|---:|---:|
| 0 | 100 |
| 8 | 100 |
| 15 | 80 |
| 20 | 55 |
| 25 | 30 |
| 30 | 10 |
| 40 | 0 |
| ≥ 50 | 0 |

(0–8 "excellent", 8–15 "very good", 15–20 "usable", 20–25 "marginal",
25–30 "poor", 30+ "very poor" — the table above is the continuous form.)

### 3.2 Relative wind angle

`rel = wrap180(wind_from_deg − coast_bearing_deg)`, then `a = abs(rel)` in [0, 180].
`coast_bearing` points **from shore out to sea** (Mindarie = 270°, i.e. sea is due
west). So a wind blowing *toward* bearing (offshore, from land to sea) has
`wind_from ≈ coast_bearing + 180`.

Let `offshore_alignment = abs(wrap180(wind_from_deg − (coast_bearing + 180)))`
(0° = pure offshore, 180° = pure onshore).

| `offshore_alignment` | Class | Direction multiplier |
|---:|---|---:|
| 0°–22.5° | offshore | 1.00 |
| 22.5°–67.5° | cross-offshore | 0.90 |
| 67.5°–112.5° | cross-shore | 0.75 |
| 112.5°–157.5° | cross-onshore | 0.55 |
| 157.5°–180° | onshore | 0.35 |

Multiplier is **interpolated** across the band centres (0/45/90/135/180°), not stepped.

Optional per-location override: `preferred_wind_directions` / `exposed_wind_directions`
are intended to nudge the multiplier ±`directional_hint_nudge` (default 0.1, clamped
to [0, 1]) when the wind sits in those sectors. **Not wired up in the core yet** —
deferred to Phase 5 calibration; the fields exist on `LocationConfig`.

### 3.3 Combine — direction only bites once there is wind

```
dir_weight = clamp(wind_speed_kmh / direction_full_effect_kmh, 0, 1)   # 0..1
wind_score = speed_subscore * (1 - dir_weight * (1 - dir_multiplier))
```

with `direction_full_effect_kmh = 18` (config).

- At **dead calm** `dir_weight = 0` → `wind_score = speed_subscore` (~100): the
  coastline is irrelevant when nothing is blowing.
- As wind builds toward ~18 km/h the directional multiplier reaches full weight.
- A **strong** wind can't be rescued by a good direction, because `speed_subscore`
  is already near zero: 35 km/h offshore → `speed_subscore ≈ 3` → `wind_score ≈ 3`.

Worked values (Mindarie, coast 270°):

| wind | `speed_sub` | `dir_weight` | `mult` | score |
|---|---:|---:|---:|---:|
| 0 km/h any | 100 | 0.00 | – | ~100 |
| 8 km/h offshore (E) | 100 | 0.44 | 1.00 | ~100 |
| 8 km/h onshore (W) | 100 | 0.44 | 0.35 | ~71 |
| 15 km/h onshore | 80 | 0.83 | 0.35 | ~37 |
| 30 km/h onshore | 10 | 1.00 | 0.35 | ~3.5 |
| 35 km/h offshore | 3 | 1.00 | 1.00 | ~3 |

Then use `wind_gust_kmh` as a secondary cap: if `gust ≥ 1.6 × speed` **and**
`gust > 25`, multiply by 0.85 (gusty is harder to fish than steady).

---

## 4. Swell

### 4.1 Height sub-score (m), smooth

| Height | Sub-score | Rationale |
|---:|---:|---|
| 0.0 | 55 | glass-off, bait presentation poor for some land styles |
| 0.3 | 70 |  |
| 0.5 | 90 |  |
| 0.8 | 100 | favourable band |
| 1.5 | 100 |  |
| 2.0 | 70 | moderate, getting messy off the rocks |
| 2.5 | 40 | increasingly difficult |
| 3.0 | 10 | poor / unsafe at exposed marks |
| ≥ 4.0 | 0 |  |

Per-location overrides: `ideal_swell_min`, `ideal_swell_max`, `max_safe_swell`
shift/clip this curve. Above `max_safe_swell` the swell sub-score is forced to ≤ 10
regardless of the table.

### 4.2 Period / energy adjustment

Longer period at the same height = more energy = treat as "bigger":

```
effective_height = swell_height * clamp( (swell_period / 10) ** 0.5 , 0.8, 1.4 )
```

Feed `effective_height` into §4.1. (10 s is the neutral reference; a 1.0 m @ 16 s
groundswell scores like ~1.26 m, a 1.0 m @ 6 s windswell like ~0.8 m.)

### 4.3 Direction (optional, when `swell_wave_direction` present)

If swell arrives within ±30° of `coast_bearing` (straight in), keep score.
If it's > 60° oblique to the coast normal, add +5 (shadowed marks fish better).
Small effect in V1; refine per-location later.

### 4.4 Missing data

`swell_height is None` → swell component `None` (renormalise). Do **not** fall back to
total `wave_height` in V1 (different quantity); revisit in Phase 2 if the field split
proves unreliable.

---

## 5. Tide

Input: modelled `sea_level_height_msl` series → `TideState` (see `scoring/tide.py`),
giving `state ∈ {rising, falling}`, `minutes_to_next_extreme`, `next_extreme_kind`.

Score table (land-based default; interpolate on "hours relative to next/last high"):

| Situation | Score |
|---|---:|
| 2.0 h before high | 90 |
| 1.0 h before high | 100 |
| at high (±15 min) | 95 |
| 1.0 h after high | 85 |
| 2.5 h after high (mid-fall) | 60 |
| at low (±15 min) | 50 |
| 1.5 h after low (early rise) | 70 |
| otherwise rising | 65 |
| otherwise falling | 55 |

Rising water is preferred; the run 2 h-before to 1 h-after high is the peak. All of
this is `location` / `species` / `style` configurable later (Phase 5).

**Caveats:** Perth is micro-tidal (~0.6 m range) and diurnal-dominant. The modelled
series may not have crisp turning points — the extrema detector uses a minimum
prominence (`tide.min_prominence_m`, default 0.05 m) and a minimum spacing
(`tide.min_extreme_spacing_h`, default 4 h) and returns `state=None` (→ component
`None`) when it can't decide.

---

## 6. Solunar

Periods from `astronomy/solunar.py`:

- **Major**: centred on lunar upper transit (overhead) and lower transit (underfoot).
  Width `solunar.major_minutes` (default **120**).
- **Minor**: centred on moonrise and moonset. Width `solunar.minor_minutes`
  (default **60**; `bite-times` uses 120 — calibrate later).

Score for an hour (take the best applicable):

| Condition | Score |
|---|---:|
| inside a major period | 100 |
| within 30 min of a major edge | 90 |
| inside a minor period | 80 |
| within 30 min of a minor edge | 70 |
| otherwise | 50 |

Optional phase bonus: within 2 days of new or full moon, `+5` (clamped to 100).
Kept tiny on purpose.

**Hard rule:** solunar is one input among seven. A major period never lifts a day
whose wind or swell component is "poor"/dangerous — enforced structurally by the
0.15 (full) / 0.20 (outlook) weight cap, not by special-casing.

---

## 7. Sun (dawn / dusk)

Bonus window around each of sunrise and sunset. Piecewise-smooth, peak `100` at the
event itself, tapering to a `base` of `40` outside the windows:

| Offset from event | Score |
|---|---:|
| sunrise − 60 min | 70 |
| sunrise | 100 |
| sunrise + 90 min | 70 |
| … linear down to base by +150 min | 40 |
| sunset − 90 min | 70 |
| sunset | 100 |
| sunset + 60 min | 70 |
| … linear down to base by −150 min | 40 |

Midday / middle of night = `40` (not `0` — you can still catch fish at noon).
Use a smooth cosine taper between the breakpoints rather than straight lines where
practical.

---

## 8. Rain

Input: `precipitation` mm/h (total: rain + showers + snow), preceding-hour sum.

| mm/h | Score |
|---:|---:|
| 0 | 100 |
| 0.5 | 90 |
| 1.0 | 75 |
| 2.0 | 55 |
| 5.0 | 30 |
| ≥ 10 | 5 |

Interpolate. Future: separate `showers` (convective, brief) from `rain` (large-scale,
persistent) and penalise persistent rain more.

---

## 9. Pressure

Absolute pressure is weak signal; use the **3-hour trend**.

```
delta = pressure_msl(t) − pressure_msl(t − 3h)      # hPa
```

| `delta` (hPa / 3 h) | Category | Score |
|---:|---|---:|
| ≤ −3.0 | `rapidly_falling` | 80 |
| −3.0 … −1.0 | `falling` | 70 |
| −1.0 … +1.0 | `steady` | 60 |
| +1.0 … +3.0 | `rising` | 55 |
| ≥ +3.0 | `rapidly_rising` | 45 |

Assumption (weak, flagged): a falling barometer ahead of a change often fires fish up;
a sharp rise behind a front tends to shut them down. **Low weight (0.05 full) until
Phase 5 says otherwise.** For the first 3 hours of the series (no `t − 3h`), pressure
component is `None`.

---

## 10. Missing data → renormalisation (worked example)

Full weights, an outlook hour where `swell`, `tide` are `None`:

```
present  = {wind:0.30, solunar:0.15, sun:0.10, rain:0.05, pressure:0.05}
sum      = 0.65
used     = {wind:0.462, solunar:0.231, sun:0.154, rain:0.077, pressure:0.077}
score    = Σ used[c] * component[c]
```

If **all** components are `None` (total data loss) → `HourlyScore.score = None`,
`rating = "unknown"`, and that hour is excluded from window/daily calculations.
Never emit a numeric score built from nothing.

---

## 11. Best fishing window

- Rolling window of `window_hours` consecutive **scored** hours (default 3).
- Window score = mean of the hourly scores, with a mild centre weight:
  weights `[1, 1.3, 1]` for a 3-h window (normalised). Generalise: triangular.
- A window is only valid if **all** its hours have a non-`None` score and (optionally)
  fall within `preferred_hours` if the user set that.
- Return the highest-scoring window as `FishingWindow(start_utc, end_utc, score)`
  where `end_utc` is the **exclusive** boundary = start of the hour after the last
  included sample (`is_end_inclusive_sample = False`). So "17:00–20:00 @ 91" means
  samples 17:00, 18:00, 19:00.

Spec worked example (must be a test):

```
15:00 72   16:00 81   17:00 91   18:00 94   19:00 88   20:00 73
16:00–19:00 → (81*1 + 91*1.3 + 94*1) / 3.3 = 89.4
17:00–20:00 → (91*1 + 94*1.3 + 88*1) / 3.3 = 91.3   ← best
18:00–21:00 → (94*1 + 88*1.3 + 73*1) / 3.3 = 85.2
→ { start: 17:00, end: 20:00, score: 91 }
```

---

## 12. Daily score

```
daily_score = best_window.score                       # V1
# Phase 2+ optional:
daily_score = 0.8 * best_window.score + 0.2 * second_best_nonoverlapping_window.score
```

**Not** the 24-hour mean (that punishes a day with one great session). A day with no
valid window (all hours unscored) → `score = None`, `rating = "unknown"`.

`confidence`: day is `full` if ≥ `day.full_hours_fraction` (default 0.6) of its
**06:00–21:00 local** hours have `confidence = full`, else `outlook`.

---

## 13. Highlights (for the card / notifications)

Generated from the winning window's dominant positives, e.g.:

- wind component ≥ 85 and offshore → `"Light offshore wind"`
- inside a major solunar period → `"Major solunar period"`
- tide rising through the window → `"Rising tide"`
- window overlaps sunset ±60 min → `"Best period overlaps sunset"`
- swell 0.5–1.5 m, period ≥ 12 s → `"Clean {h:.1f} m groundswell"`

Max 4, ordered by component weight × (score − 60).
