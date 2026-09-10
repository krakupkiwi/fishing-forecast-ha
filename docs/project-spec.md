# Home Assistant Fishing Forecast Project

## Project Goal

Build a Home Assistant-native fishing forecast system that shows the next **7–14 days**, identifies the **best fishing days**, and calculates the **best 2–3 hour fishing windows** for each day.

The initial target location is **Mindarie, Western Australia**, with the design allowing additional locations such as:

- Two Rocks
- Lancelin
- Hillarys
- North Mole
- Fremantle

The system is intended primarily for **land-based fishing**, so wind direction, swell exposure, tide state, dawn/dusk and location-specific coastal orientation should matter more than they would in a generic fishing forecast.

The system should use **free data sources**, preferably with **no API keys**, and avoid ongoing subscriptions.

---

# Recommended Architecture

## Can everything live inside Home Assistant?

**Yes — the first version can live entirely inside Home Assistant and does not require a separate Docker/FastAPI service.**

The recommended V1 architecture is:

```text
Home Assistant
│
├── custom_components/fishing_forecast/
│   ├── __init__.py
│   ├── manifest.json
│   ├── config_flow.py
│   ├── coordinator.py
│   ├── sensor.py
│   ├── api/
│   │   ├── open_meteo.py
│   │   └── astronomy.py
│   ├── scoring/
│   │   ├── engine.py
│   │   ├── wind.py
│   │   ├── swell.py
│   │   ├── tide.py
│   │   ├── solunar.py
│   │   └── windows.py
│   └── models.py
│
└── www/
    └── fishing-forecast-card.js
```

The custom integration performs the API calls, calculations, caching and creation of Home Assistant entities.

The Lovelace card reads those entities and renders the 7–14 day fishing forecast.

### Why this is preferable to an external service initially

A separate service would add:

- another Docker container
- another REST endpoint
- another service to monitor
- another update/deployment mechanism
- networking between Home Assistant and the service
- duplicated configuration

None of that is necessary for the first version.

Home Assistant custom integrations are Python code and can declare Python package requirements in `manifest.json`. They can poll cloud APIs asynchronously, maintain a `DataUpdateCoordinator`, expose sensors, and provide configuration through the Home Assistant UI.

Therefore the recommended starting point is:

> **Home Assistant custom integration + custom Lovelace card**

---

# When an External Service May Become Useful

An external service may become useful later if we implement a large local harmonic tide model such as EOT20.

A global tide model can contain substantial model/grid data and may introduce scientific Python/native dependencies that are undesirable inside the Home Assistant Core environment.

At that point there are three options:

### Option A — remain entirely inside Home Assistant

Use the Open-Meteo modelled sea-level field as the tide input.

Simplest architecture.

### Option B — Home Assistant Add-on

Run a dedicated tide/scoring engine as a Home Assistant add-on.

This still keeps the application operationally "inside Home Assistant", while isolating dependencies from Home Assistant Core.

```text
Home Assistant
      │
      │ local HTTP
      ▼
Fishing Forecast Add-on
      │
      ├── EOT20 model
      ├── tide calculations
      └── optional scoring
```

### Option C — separate Unraid Docker service

Run the forecasting service directly on Unraid.

This is the most flexible option if the project grows into a standalone application.

For now, **do not start with Option C**.

---

# Data Sources

## 1. Weather — Open-Meteo

Use Open-Meteo for hourly weather forecasts.

No API key is required for normal non-commercial usage.

Desired hourly fields include:

```text
temperature_2m
precipitation
rain
cloud_cover
surface_pressure
wind_speed_10m
wind_direction_10m
wind_gusts_10m
```

Daily astronomy fields:

```text
sunrise
sunset
```

The weather forecast can cover approximately 14–16 days depending on requested configuration/model.

For Australia, investigate Open-Meteo's BOM model support, including ACCESS-G, and prefer an appropriate Australian model where practical.

Documentation:

https://open-meteo.com/en/docs

BOM API documentation:

https://open-meteo.com/en/docs/bom-api

---

# 2. Marine Conditions — Open-Meteo Marine API

Use Open-Meteo Marine for the detailed near-term forecast.

Desired fields:

```text
wave_height
wave_direction
wave_period

swell_wave_height
swell_wave_direction
swell_wave_period

wind_wave_height
wind_wave_direction
wind_wave_period

sea_surface_temperature

ocean_current_velocity
ocean_current_direction

sea_level_height_msl
```

Documentation:

https://open-meteo.com/en/docs/marine-weather-api

## Important limitation

The marine endpoint currently has a shorter documented forecast horizon than the main weather endpoint.

Therefore the UI must distinguish:

### Full forecast

Approximately days 1–8.

Uses:

- weather
- wind
- waves
- swell
- tide approximation
- solunar
- dawn/dusk

### Outlook

Approximately days 9–14.

Uses:

- weather
- wind
- solunar
- dawn/dusk

The UI must **not imply marine precision when marine forecast data is unavailable**.

Each day should therefore contain:

```json
{
  "confidence": "full"
}
```

or:

```json
{
  "confidence": "outlook"
}
```

---

# 3. Solunar Calculations — Local

Do not depend on a paid solunar API.

Calculate solar/lunar information locally.

Required calculations:

- sunrise
- sunset
- moonrise
- moonset
- moon transit / overhead
- moon anti-transit / underfoot
- moon phase
- moon illumination
- major feeding periods
- minor feeding periods

Typical solunar interpretation:

## Major periods

Approximately centred around:

- moon overhead
- moon underfoot

Typical duration:

~2 hours

## Minor periods

Approximately centred around:

- moonrise
- moonset

Typical duration:

~1 hour

The exact implementation should be deterministic and testable.

A prior reference implementation worth examining is:

https://github.com/benpaternostro/bite-times

Do not blindly copy its implementation. Use it to understand expected calculations and output.

For a Python Home Assistant integration, investigate appropriate astronomy libraries such as:

- `astral`
- `skyfield`
- `ephem`

Prefer a lightweight pure-Python or well-supported dependency suitable for Home Assistant.

---

# 4. Tides

## V1

Use:

```text
sea_level_height_msl
```

from Open-Meteo Marine as an approximate tide signal.

Derive:

- rising
- falling
- approximate high tide
- approximate low tide
- time to next turning point
- rate of change

### Important

Do not claim this is an official tide table.

Open-Meteo's marine model is suitable for a **forecast/scoring input**, but coastal model resolution limits accuracy near shore.

The UI should label the value appropriately, for example:

> Modelled tide

instead of:

> Official tide

---

# Future Tide Upgrade

Investigate running a local harmonic tide model, potentially EOT20.

Possible reference:

https://github.com/ngs/tides-api

This should be treated as a later enhancement and **must not block V1**.

If the model or dependencies are too heavy for a Home Assistant custom integration, isolate it in a Home Assistant add-on.

---

# Locations

The system must support multiple fishing locations.

Initial configuration:

```yaml
locations:
  - id: mindarie
    name: Mindarie
    latitude: -31.69
    longitude: 115.70
    coast_bearing: 270
```

Coordinates should be configurable rather than hard-coded.

Each fishing location should support:

```yaml
id:
name:
latitude:
longitude:

marine_latitude:
marine_longitude:

coast_bearing:

preferred_wind_directions:
exposed_wind_directions:

max_safe_swell:
ideal_swell_min:
ideal_swell_max:

enabled:
```

Separate marine coordinates are useful because requesting marine conditions at an on-land coordinate can resolve to an unsuitable model grid cell.

---

# Location-Aware Wind Scoring

Wind direction must not be treated generically.

For a broadly west-facing Perth coastline:

- easterly = offshore
- westerly = onshore

A light offshore wind can be excellent even if another location would consider that same direction poor.

Calculate the relative wind angle against the configured coast bearing.

Suggested classifications:

```text
offshore
cross-offshore
cross-shore
cross-onshore
onshore
```

Then combine direction with velocity.

Example:

```text
8 km/h offshore
```

may receive:

```text
100 / 100
```

while:

```text
30 km/h onshore
```

may receive:

```text
5 / 100
```

The algorithm should use continuous interpolation where practical rather than abrupt thresholds.

---

# Fishing Score

Calculate the fishing score **hour by hour**.

Do not simply assign one score to the entire day.

Each hourly forecast record should contain the component scores and the final weighted score.

---

# Full Forecast Scoring — Days 1–8

Initial weighting:

| Factor | Weight |
|---|---:|
| Wind speed + direction | 30% |
| Swell | 20% |
| Tide | 15% |
| Solunar | 15% |
| Dawn / dusk | 10% |
| Rain | 5% |
| Pressure / pressure trend | 5% |

Total:

```text
100%
```

Treat these as initial configurable defaults, not immutable scientific truth.

---

# Outlook Scoring — Days 9–14

When reliable marine data is unavailable:

| Factor | Weight |
|---|---:|
| Wind | 50% |
| Solunar | 20% |
| Dawn / dusk | 12% |
| Rain | 9% |
| Pressure | 9% |

Total:

```text
100%
```

The scoring engine must automatically re-normalise weights when optional data is missing.

---

# Score Categories

Suggested categories:

```text
90–100  Exceptional
80–89   Excellent
70–79   Good
60–69   Fair
50–59   Marginal
0–49    Poor
```

Do not embed presentation colours in the backend.

Expose semantic values such as:

```json
{
  "score": 87,
  "rating": "excellent"
}
```

The frontend decides how to colour them.

---

# Wind Score

Start with approximately:

```text
0–8 km/h      excellent
8–15 km/h     very good
15–20 km/h    usable
20–25 km/h    marginal
25–30 km/h    poor
30+ km/h      very poor
```

Then apply a directional multiplier.

For example:

```text
offshore        1.00
cross-offshore  0.90
cross-shore     0.75
cross-onshore   0.55
onshore         0.35
```

Strong winds should progressively dominate the direction benefit.

An offshore 35 km/h wind is still not excellent fishing weather.

---

# Swell Score

Initial generic land-based values:

```text
<0.5 m       potentially too flat
0.5–1.5 m    favourable
1.5–2.0 m    moderate
2.0–2.5 m    increasingly difficult
>2.5 m       poor / potentially unsafe depending on location
```

Also consider:

```text
swell period
swell direction
```

A longer-period swell carries more energy than the same height at a short period.

Eventually calculate a simple swell energy/exposure metric rather than using height alone.

Each location should have its own exposure and safe thresholds.

---

# Tide Score

Initial logic:

Prefer:

- rising water
- approximately 1–2 hours before high
- approximately 1 hour after high

Possible starting score:

```text
2h before high       90
1h before high       100
at high              95
1h after high        85
mid falling tide     60
around low           50
early rising tide    70
```

This should eventually be configurable by:

- location
- target species
- fishing style

---

# Solunar Score

Initial:

```text
inside major period        100
within 30 min of major      90
inside minor period         80
within 30 min of minor      70
otherwise                   50
```

Solunar must remain only one component of the overall system.

Do not allow a major solunar period to override genuinely poor wind or dangerous swell.

---

# Dawn / Dusk Score

Give a bonus around:

```text
sunrise - 60 min
sunrise + 90 min

sunset - 90 min
sunset + 60 min
```

Peak approximately around sunrise/sunset.

Use a smooth time-distance curve rather than binary true/false where possible.

---

# Rain Score

Initial:

```text
0 mm/h             100
0–0.5 mm/h          90
0.5–1 mm/h          75
1–2 mm/h            55
2–5 mm/h            30
>5 mm/h              5
```

Future work may distinguish showers from persistent rain.

---

# Pressure Score

Absolute pressure alone is not particularly useful.

Prefer:

```text
pressure trend
```

Calculate approximately:

```text
pressure_now - pressure_3_hours_ago
```

Store:

```text
rapidly_rising
rising
steady
falling
rapidly_falling
```

Keep pressure weighting modest until evidence supports more aggressive weighting.

---

# Best Fishing Window Algorithm

Do not choose only the highest-scoring hour.

Generate an hourly score array:

```text
15:00  72
16:00  81
17:00  91
18:00  94
19:00  88
20:00  73
```

Run rolling windows.

Initial target:

```text
3 hours
```

Calculate:

```text
window_score = weighted/mean score across consecutive hours
```

Potentially give the centre hour slightly more weight.

Example:

```text
16:00–18:00 = 88.7
17:00–19:00 = 91.0
18:00–20:00 = 85.0
```

Return:

```json
{
  "start": "17:00",
  "end": "20:00",
  "score": 91
}
```

Be explicit whether `end` represents the end boundary or the final included hourly sample.

---

# Daily Score

Do not use the average of all 24 hourly values.

That would penalise a day that has one excellent fishing session surrounded by poor conditions.

Instead calculate the daily score from the best viable fishing window.

For example:

```text
daily_score = best_3_hour_window_score
```

Potential later refinement:

```text
daily_score =
    best_window * 0.8
  + second_best_window * 0.2
```

---

# Data Model

Example hourly object:

```json
{
  "time": "2026-09-13T17:00:00+08:00",

  "score": 91,
  "rating": "exceptional",

  "components": {
    "wind": 94,
    "swell": 88,
    "tide": 92,
    "solunar": 100,
    "sun": 95,
    "rain": 100,
    "pressure": 70
  },

  "weather": {
    "wind_speed_kmh": 9,
    "wind_direction_deg": 105,
    "wind_gust_kmh": 14,
    "rain_mm": 0,
    "pressure_hpa": 1018
  },

  "marine": {
    "wave_height_m": 1.2,
    "wave_period_s": 11,
    "wave_direction_deg": 245,

    "swell_height_m": 0.9,
    "swell_period_s": 13,
    "swell_direction_deg": 235
  },

  "tide": {
    "height_modelled_m": 0.58,
    "state": "rising",
    "next_turn": "high",
    "next_turn_time": "2026-09-13T18:20:00+08:00"
  },

  "solunar": {
    "major": true,
    "minor": false,
    "moon_phase": "waxing_gibbous",
    "moon_illumination": 0.72
  }
}
```

---

# Daily Object

```json
{
  "date": "2026-09-13",

  "score": 91,
  "rating": "exceptional",
  "confidence": "full",

  "best_window": {
    "start": "2026-09-13T17:00:00+08:00",
    "end": "2026-09-13T20:00:00+08:00",
    "score": 91
  },

  "sunrise": "06:10",
  "sunset": "18:03",

  "highlights": [
    "Light offshore wind",
    "Major solunar period",
    "Rising tide",
    "Best period overlaps sunset"
  ]
}
```

---

# Home Assistant Entities

Avoid creating hundreds of entities for every hourly value.

Expose a small useful entity set and keep detailed forecast data in attributes or integration-managed data.

Potential entities:

```text
sensor.fishing_forecast_mindarie
sensor.fishing_score_mindarie
sensor.fishing_best_window_mindarie
sensor.fishing_best_day_mindarie
sensor.fishing_conditions_mindarie
```

Example primary sensor:

```text
sensor.fishing_forecast_mindarie
```

State:

```text
91
```

Attributes:

```yaml
rating: exceptional
best_day: 2026-09-13
best_start: 17:00
best_end: 20:00
confidence: full
days: [...]
```

Be mindful of Home Assistant state attribute size.

If the complete hourly dataset is too large for state attributes, store it in coordinator memory and have the custom card retrieve it through a Home Assistant websocket/API endpoint instead of forcing 336 hourly records into entity attributes.

This is likely the better long-term design.

---

# DataUpdateCoordinator

Use Home Assistant's `DataUpdateCoordinator`.

Suggested update interval:

```text
30 minutes
```

There is no value hammering weather APIs every minute.

Responsibilities:

1. request weather data
2. request marine data
3. calculate astronomy
4. derive tide turning points
5. calculate hourly component scores
6. calculate final hourly scores
7. calculate rolling windows
8. create daily summaries
9. determine overall best upcoming trip
10. update HA entities

Use one shared coordinator per configured location where practical.

Avoid duplicate API calls for multiple entities.

---

# Error Handling

The integration must degrade gracefully.

Examples:

### Weather API unavailable

Retain previous successful forecast where possible.

Expose:

```text
available = false
```

or a diagnostic state.

### Marine API unavailable

Continue producing a weather/solunar outlook.

Mark:

```text
confidence = outlook
```

### One marine variable missing

Re-normalise scoring weights among available components.

### Astronomy calculation failure

Continue without solunar contribution.

Never return a falsely precise score from missing data.

---

# Caching

Cache API results in memory through the coordinator.

Consider persisted storage only if needed later.

The integration should avoid duplicate calls after a Home Assistant restart if reasonable, but complexity should remain low for V1.

---

# Configuration Flow

The custom integration should be installable/configurable from the Home Assistant UI.

Initial setup fields:

```text
Location name
Latitude
Longitude
Marine latitude
Marine longitude
Coast bearing
Forecast length
```

Defaults:

```text
Forecast length: 14
Fishing window: 3 hours
Update interval: 30 minutes
```

Use Home Assistant selectors where appropriate.

---

# Integration Options

After setup, allow editing:

```text
wind thresholds
swell thresholds
component weights
coast bearing
window length
preferred fishing time range
```

Eventually:

```text
target species
fishing method
```

but these are not required for V1.

---

# Dashboard Card

Build a custom Lovelace card.

Proposed name:

```text
Fishing Forecast Card
```

Potential card type:

```yaml
type: custom:fishing-forecast-card
entity: sensor.fishing_forecast_mindarie
```

The card should fit Home Assistant's visual conventions.

Do not build a generic web-app-looking dashboard embedded in HA.

---

# Main Card Layout

Concept:

```text
┌──────────────────────────────────────────────┐
│ 🎣 FISHING FORECAST               Mindarie  │
│                                              │
│ NEXT BEST                                    │
│ Sunday 13 Sep                 91/100         │
│ 5:00 PM – 8:00 PM              Exceptional  │
│                                              │
│ ↑ Rising tide    ◐ Major      ☀ Sunset      │
│ 💨 9 km/h E      🌊 0.9 m @ 13 sec          │
├──────────────────────────────────────────────┤
│ Thu  Fri  Sat  Sun  Mon  Tue  Wed            │
│ 82   61   42   91   76   54   71             │
│                                              │
│ Thu 17 Sep → Wed 23 Sep  [Outlook]           │
├──────────────────────────────────────────────┤
│ BEST WINDOWS                                 │
│ Thu  4:45–7:30 PM        82                  │
│ Fri  5:10–7:00 AM        61                  │
│ Sat  6:00–7:30 AM        42                  │
│ Sun  5:00–8:00 PM        91 ★                │
└──────────────────────────────────────────────┘
```

---

# Day Detail

Clicking/tapping a day should open more detail.

Potential graph:

```text
100 ┤                       ╭──╮
 80 ┤       ╭──╮           │  ╰─╮
 60 ┤   ╭───╯  ╰╮      ╭───╯    │
 40 ┤───╯       ╰──────╯         ╰──
    └────────────────────────────────
      6a  9a  12p  3p  6p  9p

                   ▲
             High tide 6:20 PM

            ═══════════
             Major
            5:10–7:10
```

Display:

- hourly fishing score
- wind
- gust
- swell
- swell period
- tide trend
- high/low markers
- major solunar windows
- minor solunar windows
- sunrise
- sunset

---

# Full Forecast vs Outlook UI

Days without marine data must be visually differentiated.

Example:

```text
FULL FORECAST
Thu – Thu

OUTLOOK
Fri – Wed
```

or use an icon/badge.

The user should be able to understand immediately that days 9–14 have lower forecast confidence.

---

# Multi-Location Support

Eventually allow:

```text
Mindarie
Two Rocks
Lancelin
Hillarys
North Mole
```

Potential dashboard selector:

```text
Location: [ Mindarie ▼ ]
```

Long-term feature:

## Best place to fish

Compare configured locations:

```text
1. Two Rocks      91
   5:00–8:00 PM

2. Mindarie       84
   4:45–7:30 PM

3. Hillarys       73
   5:20–7:15 PM
```

Do not implement location comparison before the single-location scoring engine is stable.

---

# Notifications

Potential future Home Assistant automations:

```text
Notify when a fishing day becomes >= 85
```

Example:

```text
🎣 Great fishing conditions coming up

Mindarie
Sunday 13 September
5:00 PM – 8:00 PM
91/100 — Exceptional

Light easterly
0.9 m swell @ 13 sec
Rising tide
Major solunar period
Sunset overlap
```

This is not required for MVP, but the entity design should make it easy.

---

# Project Phases

## Phase 1 — Research and API validation

- Validate Open-Meteo weather fields for Mindarie.
- Validate Open-Meteo marine fields for an offshore Mindarie coordinate.
- Confirm actual forecast horizons.
- Verify local time handling for `Australia/Perth`.
- Select astronomy library.
- Write sample API fixtures.
- Do not build UI yet.

Deliverable:

```text
docs/research.md
```

---

## Phase 2 — Core Python scoring library

Build framework-independent modules for:

```text
models
weather parsing
marine parsing
astronomy
tide derivation
wind scoring
swell scoring
solunar scoring
sun scoring
rain scoring
pressure scoring
weighted aggregate scoring
rolling window calculation
daily summaries
```

Every scoring function must have unit tests.

The core scoring logic should not depend directly on Home Assistant APIs.

This allows it to be tested easily.

---

## Phase 3 — Home Assistant Custom Integration

Create:

```text
custom_components/fishing_forecast
```

Implement:

- manifest
- config flow
- options flow
- coordinator
- sensors
- diagnostics
- translations
- proper async HTTP through Home Assistant's shared aiohttp session

Initial entity set:

```text
sensor.fishing_score_<location>
sensor.fishing_best_window_<location>
sensor.fishing_best_day_<location>
```

---

## Phase 4 — Home Assistant Card

Create:

```text
www/fishing-forecast-card.js
```

Start with:

- current/next best session
- 7-day score strip
- optional 14-day expansion
- best window per day
- full/outlook indicator

Then add detailed day display.

---

## Phase 5 — Calibration

Compare forecasts against actual fishing sessions.

Add an optional feedback mechanism:

```text
Fishing result:
Poor
Average
Good
Excellent
```

Potentially also:

```text
species
number caught
```

Use this later to adjust scoring weights empirically.

Do not introduce machine learning initially.

---

## Phase 6 — Tide Upgrade

Investigate:

- EOT20
- official Australian sources
- other genuinely free tide sources

Only replace the existing modelled tide input if the alternative is demonstrably better and maintainable.

---

# Coding Standards

Use:

```text
Python 3
asyncio
aiohttp
Home Assistant DataUpdateCoordinator
pytest
type hints
dataclasses or typed models where appropriate
ruff
```

Do not perform blocking HTTP calls.

Do not scatter constants throughout files.

Create central configurable scoring defaults.

Scoring functions should be pure wherever possible.

Avoid premature abstraction.

---

# Repository Structure

Recommended:

```text
fishing-forecast-ha/
│
├── README.md
├── LICENSE
├── pyproject.toml
│
├── docs/
│   ├── research.md
│   ├── scoring.md
│   └── architecture.md
│
├── custom_components/
│   └── fishing_forecast/
│       ├── __init__.py
│       ├── manifest.json
│       ├── const.py
│       ├── config_flow.py
│       ├── coordinator.py
│       ├── sensor.py
│       ├── diagnostics.py
│       ├── models.py
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── open_meteo_weather.py
│       │   └── open_meteo_marine.py
│       │
│       ├── astronomy/
│       │   ├── __init__.py
│       │   └── solunar.py
│       │
│       ├── scoring/
│       │   ├── __init__.py
│       │   ├── engine.py
│       │   ├── wind.py
│       │   ├── swell.py
│       │   ├── tide.py
│       │   ├── solunar.py
│       │   ├── sunlight.py
│       │   ├── rain.py
│       │   ├── pressure.py
│       │   └── windows.py
│       │
│       └── translations/
│           └── en.json
│
├── frontend/
│   └── fishing-forecast-card.js
│
└── tests/
    ├── fixtures/
    ├── test_wind.py
    ├── test_swell.py
    ├── test_tide.py
    ├── test_solunar.py
    ├── test_scoring.py
    └── test_windows.py
```

---

# MVP Definition

The MVP is complete when:

1. Home Assistant can install the custom integration.
2. The user can configure Mindarie through the UI.
3. Open-Meteo weather and marine data are retrieved.
4. Solunar information is calculated locally.
5. Hourly scores are generated.
6. A best 3-hour window is generated for every forecast day.
7. Days are marked `full` or `outlook`.
8. Home Assistant exposes useful fishing forecast sensors.
9. A Lovelace card displays the next seven days.
10. The system works without paid APIs or API keys.

---

# What Is Explicitly Out of Scope for MVP

Do not initially build:

- AI/ML prediction
- catch database
- social features
- mobile app
- separate FastAPI service
- separate Node service
- external database
- official tide-table scraper
- EOT20 tide server
- species-specific prediction
- 20 fishing locations
- map interface

Build the scoring engine correctly first.

---

# Claude Code Development Prompt

Copy everything below into Claude Code.

---

## Prompt

You are beginning development of a new Home Assistant project called **Fishing Forecast**.

The goal is to build a Home Assistant custom integration and Lovelace card that predicts the best land-based fishing periods over the next 7–14 days.

The first target location is **Mindarie, Western Australia**, but the architecture must support multiple configurable fishing locations later.

Read the complete project specification in this repository before writing implementation code.

### Core architectural decision

The MVP must run **inside Home Assistant**.

Do NOT create:

- a standalone FastAPI server
- a Node backend
- a separate Docker service
- a database

Implement the backend as:

```text
custom_components/fishing_forecast/
```

and eventually implement the dashboard UI as a custom Lovelace card.

The project should only move calculation into a Home Assistant add-on later if a large local harmonic tide model proves unsuitable for a Home Assistant custom integration.

### Data sources

Use free/no-key sources wherever possible.

Primary weather source:

```text
Open-Meteo
```

Primary marine source:

```text
Open-Meteo Marine
```

Weather data should include:

```text
wind speed
wind direction
wind gusts
rain
pressure
cloud cover
sunrise
sunset
```

Marine data should include when available:

```text
wave height
wave direction
wave period
swell height
swell direction
swell period
sea-level height
```

Use `sea_level_height_msl` only as a **modelled tide input**, not an authoritative tide table.

Calculate solunar periods locally rather than depending on a commercial solunar API.

Required astronomy calculations include:

```text
moonrise
moonset
moon overhead/transit
moon underfoot/anti-transit
moon phase
moon illumination
major periods
minor periods
```

Investigate an appropriate Python astronomy library that is compatible with Home Assistant.

Look at this project only as a reference for expected solunar behaviour:

```text
https://github.com/benpaternostro/bite-times
```

Do not simply port/copy it.

### Forecast confidence

The general weather forecast has a longer horizon than the marine forecast.

Therefore distinguish:

```text
confidence = full
```

when marine information is available

and:

```text
confidence = outlook
```

when only longer-range weather/astronomy information is available.

Never fabricate missing marine information.

### Scoring

Generate scores **hour by hour**.

Initial full forecast weighting:

```text
wind       30%
swell      20%
tide       15%
solunar    15%
dawn/dusk  10%
rain        5%
pressure    5%
```

Initial outlook weighting:

```text
wind       50%
solunar    20%
dawn/dusk  12%
rain        9%
pressure    9%
```

Weights must be configurable constants and automatically re-normalised when optional data is unavailable.

Each scoring module should return a normalised:

```text
0–100
```

score.

The aggregate score should also be 0–100.

### Location-aware wind

A major requirement is that wind direction be evaluated relative to the coastline.

Each location has:

```text
latitude
longitude
marine latitude
marine longitude
coast bearing
```

Calculate whether wind is approximately:

```text
offshore
cross-offshore
cross-shore
cross-onshore
onshore
```

and combine that with wind speed.

For a broadly west-facing Perth coast, easterly winds should generally be more favourable than strong westerlies.

Do not make this Mindarie-specific in the scoring implementation.

### Best-window calculation

Do not simply choose the highest hourly score.

Run a rolling window over consecutive hours.

Start with:

```text
3-hour fishing window
```

Example:

```text
15:00 72
16:00 81
17:00 91
18:00 94
19:00 88
20:00 73
```

Calculate all valid rolling windows and return the best one.

The daily fishing score should initially equal the best fishing-window score rather than the average of the entire day.

### Code architecture

The scoring engine should be mostly independent from Home Assistant.

Keep modules separated approximately as:

```text
api/
astronomy/
scoring/
models.py
```

Scoring functions should be pure/testable wherever practical.

Use:

```text
asyncio
aiohttp
type hints
pytest
ruff
```

Home Assistant network calls must use the shared async HTTP session.

Use a `DataUpdateCoordinator` so multiple sensor entities do not trigger duplicate API requests.

### Home Assistant integration

Implement configuration via UI using `config_flow.py`.

Initial configuration:

```text
location name
latitude
longitude
marine latitude
marine longitude
coast bearing
forecast length
```

Initial defaults:

```text
forecast = 14 days
window = 3 hours
update interval = 30 minutes
```

Create only a small number of useful sensors.

Do not create hundreds of hourly entities.

Potential entities:

```text
sensor.fishing_score_mindarie
sensor.fishing_best_window_mindarie
sensor.fishing_best_day_mindarie
sensor.fishing_forecast_mindarie
```

Avoid putting an excessively large 336-hour JSON payload into entity state attributes.

If necessary, retain detailed forecast data inside coordinator memory and later expose it to the custom card through an appropriate Home Assistant API/websocket mechanism.

### Tide derivation

From modelled sea-level samples, derive:

```text
rising/falling
approximate local extrema
next high
next low
time until turning point
```

Keep tide logic independent so a more accurate tide provider can replace Open-Meteo later.

### Testing requirements

Before implementing the UI, build strong tests for:

```text
wind direction classification
wind score
swell score
tide turning-point detection
solunar intervals
sunrise/sunset proximity
rain score
pressure trend
weight normalisation
aggregate score
rolling window selection
timezone handling
missing marine data
```

Use stored Open-Meteo JSON fixtures so most tests do not depend on live network APIs.

Use timezone:

```text
Australia/Perth
```

for the initial fixtures and test cases.

### Development process

Do not try to build the complete system immediately.

Work in phases.

#### Phase 1 — research

First inspect:

- current Home Assistant custom integration requirements
- current DataUpdateCoordinator conventions
- current config-flow conventions
- Open-Meteo weather API
- Open-Meteo marine API
- available Python astronomy libraries

Verify actual field names and forecast limitations from official documentation.

Write findings to:

```text
docs/research.md
```

Do not rely on assumptions from this prompt where current API documentation says otherwise.

#### Phase 2 — core models and scoring

Implement the framework-independent data models and scoring engine.

Add tests.

Do not build Lovelace UI yet.

#### Phase 3 — API clients

Implement Open-Meteo clients and fixture-based parsing tests.

#### Phase 4 — Home Assistant coordinator/integration

Connect the tested core engine to Home Assistant.

#### Phase 5 — dashboard card

Only after the backend data model is stable, build the custom Lovelace card.

### Important engineering requirements

Do not hide questionable assumptions.

Document scoring assumptions in:

```text
docs/scoring.md
```

Keep constants configurable.

Use defensive handling of missing API fields.

Never silently turn missing data into zero, because zero could be interpreted as genuinely terrible fishing conditions.

Prefer:

```python
None
```

and re-normalise available weights.

Use structured dataclasses or typed models rather than passing arbitrary dictionaries through the scoring code.

Use explicit timezone-aware datetimes.

All dates received from APIs must be normalised carefully.

### First task

Do **Phase 1 only** first.

1. Inspect the repository.
2. Establish the project structure if required.
3. Research the current official documentation.
4. Verify Open-Meteo request formats and exact fields.
5. Investigate Home Assistant-compatible Python astronomy options.
6. Document architectural decisions and uncertainties in `docs/research.md`.
7. Propose the final internal data models.
8. Propose a test strategy.
9. Stop and summarise the findings before beginning implementation.

Do not start writing the full integration until the research phase has established that the planned APIs and libraries are appropriate.

The goal is a maintainable Home Assistant integration, not a quick script.

---

# Useful References

Home Assistant custom integrations:

https://developers.home-assistant.io/docs/creating_component_index/

Home Assistant integration manifest:

https://developers.home-assistant.io/docs/creating_integration_manifest/

Home Assistant custom cards:

https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/

Open-Meteo:

https://open-meteo.com/en/docs

Open-Meteo BOM:

https://open-meteo.com/en/docs/bom-api

Open-Meteo Marine:

https://open-meteo.com/en/docs/marine-weather-api

Public APIs directory:

https://github.com/public-apis/public-apis

Solunar reference:

https://github.com/benpaternostro/bite-times

Potential future tide work:

https://github.com/ngs/tides-api

---

# Current Recommendation

Build **V1 entirely inside Home Assistant**.

Use:

```text
Home Assistant custom integration
        │
        ├── Open-Meteo Weather
        ├── Open-Meteo Marine
        ├── local astronomy/solunar calculations
        ├── fishing scoring engine
        └── DataUpdateCoordinator
                 │
                 ▼
       Home Assistant entities
                 │
                 ▼
        Custom Lovelace card
```

Only introduce an add-on/external service if a future tide model or other scientific dependency creates a genuine reason to isolate processing from Home Assistant Core.
