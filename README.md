# Fishing Forecast for Home Assistant

A Home Assistant custom integration + Lovelace card that predicts the best
**land-based** fishing days and the best **2–3 hour fishing windows** for the next
7–16 days, using free, no-key data sources.

First target location: **Mindarie, Western Australia**. The design supports multiple
configurable locations (Two Rocks, Lancelin, Hillarys, North Mole, Fremantle, …).

> **Status: Phase 1 (research) complete.** No integration or scoring logic is
> implemented yet. See [`docs/research.md`](docs/research.md) for findings and
> [`docs/project-spec.md`](docs/project-spec.md) for the full specification.

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
custom_components/fishing_forecast/   the Home Assistant integration (Phase 3)
  api/           Open-Meteo clients + JSON→dataclass parsing
  astronomy/     ephem wrapper + solunar period calculation
  scoring/       pure scoring functions, rolling windows, daily summaries
  models.py      typed dataclasses (the internal data model)
  const.py       DOMAIN + configurable scoring defaults
frontend/        Lovelace card (Phase 4)
docs/            research.md, scoring.md, architecture.md, project-spec.md
tests/           pytest suite + committed Open-Meteo fixtures
```

## Development

```bash
python -m venv .venv && . .venv/bin/activate      # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
ruff check . && ruff format --check .
mypy custom_components
pytest
```

The core scoring library (`scoring/`, `astronomy/`, `models.py`) imports nothing from
Home Assistant and is tested against stored API fixtures in `tests/fixtures/`.

## Roadmap

1. ✅ **Phase 1** — research & API validation (`docs/research.md`)
2. **Phase 2** — framework-independent models + scoring engine + tests
3. **Phase 3** — Home Assistant integration (config flow, coordinator, sensors, diagnostics)
4. **Phase 4** — Lovelace card
5. **Phase 5** — calibration against real fishing sessions
6. **Phase 6** — tide upgrade (EOT20 / official source), if demonstrably better

## Data licence / attribution

Weather & marine data © Open-Meteo (CC-BY 4.0), derived from Météo-France, NOAA/NCEP,
DWD and ECMWF models. Non-commercial use, < 10 000 API calls/day. This project is not
affiliated with Open-Meteo or any weather service. Modelled tide is **not** an
official tide table.

## Licence

MIT — see [`LICENSE`](LICENSE).
