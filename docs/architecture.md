# Architecture

## Decision: everything inside Home Assistant for V1

```
┌────────────────────────── Home Assistant Core ──────────────────────────┐
│                                                                         │
│  custom_components/fishing_forecast/                                     │
│                                                                         │
│   config_flow.py ──> ConfigEntry (one per location)                     │
│        │                                                                │
│        ▼                                                                │
│   __init__.py  async_setup_entry                                        │
│        │   builds OpenMeteoClient (shared aiohttp session)              │
│        ▼                                                                │
│   coordinator.py  FishingForecastCoordinator(DataUpdateCoordinator)     │
│        │   every 30 min:                                                │
│        │     1. weather  = OpenMeteoWeatherClient.fetch()   ─┐          │
│        │     2. marine   = OpenMeteoMarineClient.fetch()     │ aiohttp  │
│        │        (best_match + ncep_gfswave025, merged)       │          │
│        │     3. astro    = ephemeris.compute()   (executor) ─┘          │
│        │     4. tide     = tide.derive(marine.sea_level)                │
│        │     5. solunar  = solunar.periods(astro)                       │
│        │     6. engine.score_hours(weather, marine, tide,               │
│        │                           solunar, astro, ScoringConfig)       │
│        │     7. windows.best(hourly, window_hours)                      │
│        │     8. daily summaries + best_day + data_health                │
│        ▼                                                                │
│   ForecastBundle  ── stored on entry.runtime_data & coordinator.data    │
│        │                                                                │
│        ├──> sensor.py    3–5 small sensors (state + daily-summary attrs) │
│        ├──> diagnostics.py   redacted dump of last bundle + config      │
│        └──> websocket_api   "fishing_forecast/hourly" → full hourly[]   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                  │  HA websocket
                                  ▼
                    www/fishing-forecast-card.js  (Phase 4)
```

Nothing here needs a container, a database, or a second process. The scoring core
(`models.py`, `scoring/`, `astronomy/`) has **zero** `homeassistant` imports and is
unit-tested stand-alone.

## Module boundaries

| Package | Depends on | Must NOT import | Responsibility |
|---|---|---|---|
| `models.py` | stdlib only | anything | typed dataclasses, enums, `rating_for(score)` |
| `const.py` | `models` | `homeassistant` (values only, no HA types) | `DOMAIN`, defaults, `ScoringConfig()` factory |
| `astronomy/` | `ephem`, `models` | `homeassistant` | sun/moon events, solunar periods |
| `scoring/` | `models`, `const` | `homeassistant`, `ephem`, `aiohttp` | pure functions, window + daily logic |
| `api/` | `aiohttp`, `models` | `homeassistant.components.*`, `scoring` | HTTP + parse JSON → `WeatherHour`/`MarineHour` |
| `coordinator.py` | all of the above + `homeassistant` | — | orchestration, caching, graceful degradation |
| `sensor.py`, `diagnostics.py`, `config_flow.py` | `homeassistant`, `coordinator`, `models` | `api` internals, `ephem` | HA surface |
| `frontend/` | — | — | Lovelace card (reads entities + websocket) |

`api/` is allowed to import `homeassistant.helpers.aiohttp_client` only from the
factory that the coordinator calls — the parsing functions themselves take a plain
`aiohttp.ClientSession`.

## Data flow for "confidence"

`confidence` starts at the **hour** level and bubbles up:

1. `MarineHour` carries `has_fine_marine` (from `best_match`) and `has_tide`
   (`sea_level_height_msl` present).
2. `engine.score_hour` sets `HourlyScore.confidence = full` iff `has_tide` **and**
   `has_fine_marine`, else `outlook`, and picks the matching weight set.
3. `daily.summarise` marks the day `full` iff ≥ 60 % of its 06:00–21:00 local hours
   are `full`.
4. The card badges any non-`full` day and shows the `FULL FORECAST` / `OUTLOOK`
   boundary date.

## Graceful degradation (coordinator)

| Failure | Behaviour |
|---|---|
| Weather request fails | Keep previous `ForecastBundle`; `data_health.weather = "failed"`; raise `UpdateFailed` so HA shows the entity as unavailable-ish but retains attrs. |
| Marine both models fail | Produce a full bundle from weather + astro only; **every** day `confidence = outlook`; `data_health.marine = "failed"`. |
| Marine `best_match` ok, `gfswave` fails | Days ≤ ~9 `full`, days > 9 have no marine at all. |
| One marine field missing for some hours | Component `None` → renormalise (§10 of scoring.md). |
| `ephem` import/calc fails | No solunar + no sun component; renormalise; `data_health.astronomy = "failed"`. Log once. |
| First 3 h of series | Pressure component `None` (no `t−3h`). Expected, not an error. |

## Future escape hatches (not V1)

- **EOT20 / better tide**: `scoring/tide.py` takes a `height series` interface;
  swapping the provider is one new `api/` module + a coordinator wiring change.
  If EOT20's deps are too heavy for Core, move *only* tide into a HA add-on that
  exposes `GET /tide?lat=&lon=&from=&to=` over local HTTP.
- **Multi-location "best place"**: a second coordinator-of-coordinators that reads
  each location's `ForecastBundle`. Deferred until single-location scoring is stable.
- **Skyfield**: drop-in replacement for `astronomy/ephemeris.py` if `ephem`
  accuracy is ever shown lacking; costs a bundled `.bsp` file.
