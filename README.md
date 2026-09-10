# Fishing Forecast for Home Assistant

A Home Assistant custom integration + Lovelace card that predicts the best
**land-based** fishing days and the best **2–3 hour fishing windows** for the next
7–16 days, using free, no-key data sources.

First target location: **Mindarie, Western Australia**. The design supports multiple
configurable locations (Two Rocks, Lancelin, Hillarys, North Mole, Fremantle, …).

> **Status: Phases 1–5 complete.** The integration installs from the UI, produces
> hour-by-hour scores for the next 1–2 weeks, exposes sensors + a `fishing_forecast/hourly`
> websocket, and ships an auto-registering Lovelace card (next-best session,
> coloured day strip, best-window list, full/outlook boundary, tap-through
> day-detail chart). The forecast is shaped by a **fishing-style profile**
> (calm water / beach sport / rock snapper / marina). A historical-backtest tool
> and a `log_session` feedback service support ongoing calibration. Scoring core:
> 114 tests. See [`docs/card.md`](docs/card.md),
> [`docs/calibration.md`](docs/calibration.md),
> [`docs/fishing-knowledge.md`](docs/fishing-knowledge.md),
> [`docs/scoring.md`](docs/scoring.md), [`docs/research.md`](docs/research.md),
> [`docs/architecture.md`](docs/architecture.md).

## How it works

| Input | Source | Cost |
|---|---|---|
| Wind, gusts, rain, pressure, cloud, sun times | [Open-Meteo Weather API](https://open-meteo.com/en/docs) (`best_match`, 16 days) | free, no key |
| Waves, swell (height / period / direction), SST, currents | [Open-Meteo Marine API](https://open-meteo.com/en/docs/marine-weather-api) (`best_match` ~9.5 days + `ncep_gfswave025` to 16 days) | free, no key |
| Modelled tide (`sea_level_height_msl`) | Open-Meteo Marine (`best_match`, ~9.5 days) | free, no key |
| Sun / moon rise, set, transit; moon phase & illumination; solunar major/minor periods | Local calculation via [`ephem`](https://pypi.org/project/ephem/) | free, offline |

A weighted hour-by-hour score (0–100) is computed for every forecast hour, then a
rolling window finds each day's best session. Days with modelled tide + fine marine
data are marked **full**; longer-range days are marked **outlook** and never imply
marine precision they don't have.

See [`docs/scoring.md`](docs/scoring.md) for every constant and
[`docs/architecture.md`](docs/architecture.md) for module boundaries.

## Repository layout

```
custom_components/fishing_forecast/
  api/           Open-Meteo clients + JSON→dataclass parsing
  astronomy/     ephem wrapper + solunar period calculation
  scoring/       pure scoring functions, rolling windows, daily summaries
  frontend/      fishing-forecast-card.js  (the Lovelace card)
  models.py      typed dataclasses (the internal data model)
  core.py        build_forecast(location, payloads, cfg) -> ForecastBundle
  coordinator.py / config_flow.py / sensor.py / websocket.py / …  HA surface
docs/            research.md, scoring.md, architecture.md, card.md, project-spec.md
tests/           core suite + integration/ (HA, Linux only) + Open-Meteo fixtures
```

## Development

```bash
python -m venv .venv && . .venv/bin/activate      # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"                            # add ",ha" for the integration tests (Linux/macOS)
ruff check . && ruff format --check .
mypy
pytest                                             # core suite; skips tests/integration/ without HA
```

The scoring core (`models.py`, `util.py`, `core.py`, `scoring/`, `astronomy/`,
`api/open_meteo_*`) imports nothing from Home Assistant and is tested against
stored API fixtures in `tests/fixtures/`.

## Roadmap

1. ✅ **Phase 1** — research & API validation (`docs/research.md`)
2. ✅ **Phase 2** — framework-independent models + scoring engine + tests
3. ✅ **Phase 3** — Home Assistant integration (config flow, coordinator, sensors, diagnostics)
4. ✅ **Phase 4** — Lovelace card (`docs/card.md`)
5. ✅ **Phase 5** — fishing-style profiles, historical backtest tool, first calibration
   pass, feedback service (`docs/calibration.md`, `docs/fishing-knowledge.md`)
6. **Phase 6** — tide upgrade (EOT20 / official source), if demonstrably better

## Fishing style

The forecast is reshaped by what you target — set this in the config flow, change
it any time in the integration's options:

| Profile | For |
|---|---|
| `calm_water` | herring, whiting, squid, garfish — calm, clean water |
| `beach_sport` *(default)* | tailor, Australian salmon — some wash, dawn/dusk, fronts |
| `rock_snapper` | pink snapper, mulloway off the rock walls — swell, after storms |
| `estuary_marina` | mulloway / bream inside the marina — run-in tide, night |

`python tools/backtest.py --start 2024-01-01 --end 2025-08-31 --profile beach_sport`
runs the engine over the Open-Meteo historical archive to sanity-check the model.
`docs/calibration.md` has the findings.

### What Phase 2 delivered

`custom_components/fishing_forecast/` (all importable with **no Home Assistant**):

- `models.py` — frozen dataclasses for every input and output
- `util.py` — angle math, breakpoint interpolation, timezone conversion
- `api/open_meteo_weather.py`, `api/open_meteo_marine.py` — JSON → typed rows,
  including the `best_match` + `ncep_gfswave025` marine merge
- `astronomy/ephemeris.py` — `ephem` wrapper (sun/moon events, transits, phase)
- `astronomy/solunar.py` — major/minor feeding periods
- `scoring/` — `wind`, `swell`, `tide` (extrema detection + score), `solunar`,
  `sunlight`, `rain`, `pressure`, the weight `engine`, and rolling `windows` +
  daily summaries
- `core.py` — `build_forecast(location, payloads, cfg) -> ForecastBundle`, the
  single entry point the Phase 3 coordinator will call

## Data licence / attribution

Weather & marine data © Open-Meteo (CC-BY 4.0), derived from Météo-France, NOAA/NCEP,
DWD and ECMWF models. Non-commercial use, < 10 000 API calls/day. This project is not
affiliated with Open-Meteo or any weather service. Modelled tide is **not** an
official tide table.

## Licence

MIT — see [`LICENSE`](LICENSE).
