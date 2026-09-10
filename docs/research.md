# Phase 1 — Research & API Validation

Status: **complete**. Date of investigation: 2026-09-10 (`Australia/Perth`).
All API findings below were verified with live requests; the captured responses are
in [`tests/fixtures/`](../tests/fixtures/).

This document records what was verified, what differs from the assumptions in
[`project-spec.md`](project-spec.md), the open questions, and the proposed data
models + test strategy.

> **Phase 2 update (2026-09-10):** the core models, Open-Meteo parsers, `ephem`
> astronomy, solunar periods and the full scoring engine are now implemented in
> `custom_components/fishing_forecast/` and tested (102 tests). Deviations found
> during implementation are noted inline below and in `docs/scoring.md`.
>
> **Phase 3 update (2026-09-10):** the Home Assistant integration is wired up —
> config/options flow, `DataUpdateCoordinator`, four sensors, diagnostics, and a
> `fishing_forecast/hourly` websocket command. `__init__.py` lazy-imports Home
> Assistant so the scoring core stays importable without it. Integration tests
> (`tests/integration/`) use `pytest-homeassistant-custom-component` and run on
> Linux/macOS only (HA's test harness needs a POSIX event loop). See §11.

---

## 1. Summary of decisions

| Area | Decision | Confidence |
|---|---|---|
| Architecture | Custom integration + custom card, everything in HA Core. No add-on, no external service for V1. | High |
| Weather source | Open-Meteo `/v1/forecast`, **default `best_match` model**, `forecast_days=16`. | High |
| Marine source | Open-Meteo `/v1/marine`, **two model requests**: `best_match` (full fields incl. modelled tide, ~9.5 days) + `ncep_gfswave025` (waves/swell only, full 16 days). | High |
| BOM ACCESS-G | **Do not use.** Endpoint exists but currently returns all-`null` for Mindarie (see §3.3). `best_match` already blends ECMWF/GFS and covers the full horizon. | High |
| Tide (V1) | `sea_level_height_msl` from marine `best_match`. Modelled only, ~9.5-day horizon, label "Modelled tide". | High |
| Astronomy / solunar | **`ephem==4.2.1`** as the integration requirement, wrapped behind a thin interface. Cross-check against Open-Meteo daily `moonrise`/`moonset`/`moon_phase`. | High |
| Timezone | Store everything as timezone-aware UTC internally; request Open-Meteo with `timezone=Australia/Perth` (or the location tz) and parse local wall-times against that fixed offset. | High |
| Forecast horizon | 16 days weather, ~9.5 days full marine, 16 days waves-only. "Full" vs "Outlook" split is driven by **modelled-tide availability**, not a fixed day count. | High |

---

## 2. Open-Meteo Weather API — `GET https://api.open-meteo.com/v1/forecast`

Docs: <https://open-meteo.com/en/docs>. Fixture: `tests/fixtures/weather_mindarie.json`.

### 2.1 Request used

```
https://api.open-meteo.com/v1/forecast
  ?latitude=-31.69&longitude=115.70
  &hourly=temperature_2m,precipitation,rain,showers,cloud_cover,
          surface_pressure,pressure_msl,wind_speed_10m,wind_direction_10m,
          wind_gusts_10m,weather_code
  &daily=sunrise,sunset,daylight_duration,moonrise,moonset,moon_phase
  &timezone=Australia/Perth
  &forecast_days=16
  &wind_speed_unit=kmh
```

### 2.2 Verified facts

- **`forecast_days` accepts `0`–`16`** (documented and confirmed). `17` → HTTP 400
  `{"error": true, "reason": "Forecast days is invalid. Allowed range 0 to 16..."}`.
- With `forecast_days=16` we get **384 hourly rows, every requested field 100 % non-null**
  for Mindarie. So the full 16-day weather horizon is real, not padded.
- Hourly timestamps are **local wall-time, no offset suffix** (`"2026-09-10T00:00"`),
  and the series **starts at 00:00 local on "today"**. `utc_offset_seconds: 28800`,
  `timezone_abbreviation: "GMT+8"` are returned alongside. `Australia/Perth` has no DST,
  so the offset is a constant +08:00 — but the parser must still not assume that for
  other locations.
- Grid cell returned is **not** the requested point: request `(-31.69, 115.70)` →
  response `latitude: -31.599, longitude: 115.653, elevation: 6.0`. `cell_selection`
  defaults to `land`. Acceptable for weather; document it.
- Units (from `hourly_units`): wind `km/h` (with `wind_speed_unit=kmh`), pressure `hPa`,
  precip `mm`, temp `°C`, directions `°`, cloud `%`.
- **Valid-time semantics matter for scoring:**
  - `wind_speed_10m`, `wind_direction_10m`, `pressure_msl`, `surface_pressure`,
    `cloud_cover`, `temperature_2m`, `weather_code` → **instantaneous** at the stamped hour.
  - `wind_gusts_10m` → **max of the preceding hour**.
  - `precipitation`, `rain`, `showers` → **sum over the preceding hour**.
- `precipitation` = `rain` + `showers` + snow. `rain` is large-scale only; `showers`
  is convective. Fixture maxima over 16 days: `precipitation` 2.3 mm/h, `rain` 0.9,
  `showers` 1.4. **Use `precipitation` as the rain-score input**; keep `rain`/`showers`
  split for the future "showers vs persistent rain" refinement.
- `pressure_msl` vs `surface_pressure`: both returned, differ by ~0.7 hPa at 6 m
  elevation. Use `pressure_msl` for the trend calc (standard meteorological practice,
  elevation-independent).

### 2.3 Daily block — sun & moon

- `sunrise`, `sunset` → local ISO wall-time (`"2026-09-10T06:23"`). 16 rows.
- `daylight_duration` → seconds.
- **`moonrise`, `moonset`, `moon_phase` are available and return data.**
  - `moon_phase` unit is `"fraction"`: `0.0` = new, `0.25` = first quarter, `0.5` = full,
    `0.75` = last quarter. Fixture: `0.965` (2026-09-10, waning crescent) → `0.001`
    (2026-09-11, new moon) → `0.036` … So Perth sees a **new moon ~2026-09-11**.
  - `moonrise`/`moonset` can be `null` on days where the event doesn't occur in the
    local calendar day (must handle).
  - **Not provided: lunar meridian transit / anti-transit**, which is what solunar
    *major* periods are centred on. So the API alone cannot drive solunar — we still
    need a local ephemeris. Treat these daily fields as a **cross-check + fallback**.

### 2.4 Not usable / rejected

- **BOM ACCESS-G** (`models=bom_access_global` or the `/v1/bom` endpoint): documented
  as global, 15 km, 10-day, updated 6-hourly — but every hourly value comes back
  `null` for Mindarie right now (tried `/v1/bom` and `models=bom_access_global`,
  `forecast_days` 7/10/14, minimal and full variable sets — all `null`). Looks like a
  current model-availability gap on Open-Meteo's side, not a request error (HTTP 200,
  correct grid cell `-31.699, 115.752`). **Action:** stick with `best_match`; add a
  config option later to prefer a named model, and revisit BOM then.

---

## 3. Open-Meteo Marine API — `GET https://marine-api.open-meteo.com/v1/marine`

Docs: <https://open-meteo.com/en/docs/marine-weather-api>.
Fixtures: `marine_mindarie.json` (best_match), `marine_mindarie_gfswave.json` (GFS-Wave).

### 3.1 The horizon problem is per-model, and the spec's "8 days" is stale

The docs page still says `forecast_days` is `0`–`8` (default 5) for marine. **In
practice the endpoint accepts `forecast_days=16`** and returns whatever each
underlying wave model supports. Measured non-null horizons for Mindarie:

| `models=` | Fields returned | Grid res | Non-null horizon (measured) | Notes |
|---|---|---|---:|---|
| *(default)* `best_match` → MeteoFrance MFWAM + SMOC | waves, **swell partition**, wind-wave, SST, **currents**, **`sea_level_height_msl`** | 0.08° (~8 km) | **~9.3–9.6 days** (224–230 h) | Best near-shore resolution. The only source of modelled tide + currents. |
| `ncep_gfswave025` | waves, **swell partition**, wind-wave (+ period) | 0.25° (~25 km) | **16 days** (384 h, 100 %) | No SST, no currents, **no tide**. |
| `ecmwf_wam025` | total `wave_height/direction/period` **only** | 0.25° | ~14.8 days | No swell partition — not enough on its own. |
| `gwam` (DWD) | waves + swell | 0.25° | ~7 days | Docs say 4-day; skip. |
| `ewam` (DWD) | — | — | `{"error": true, "reason": "No data is available for this location"}` | Europe-only. |

**Key finding:** `sea_level_height_msl` is only populated when `models` is *not*
restricted (i.e. `best_match`, which pulls the MeteoFrance SMOC tide/current model).
Requesting any single wave model explicitly returns `sea_level_height_msl: null`.
Its horizon is the SMOC 10-day limit (~9.5 days measured).

### 3.2 Chosen marine strategy for V1

Make **two** marine requests per update and merge them by timestamp:

1. **`best_match`** — everything, authoritative for the ~9.5 days it covers
   (fine grid, swell partition, SST, currents, modelled tide).
2. **`ncep_gfswave025`** — waves + swell partition only, fills days ~10–16.

Merge rule: for each hour, prefer `best_match` fields; where `best_match` is `null`
and GFS-Wave has a value, use GFS-Wave and drop the per-hour grid resolution claim.
`sea_level_height_msl` is never back-filled — tide scoring simply switches off past
the SMOC horizon.

### 3.3 Verified field facts

- `cell_selection` **defaults to `sea`** on the marine endpoint (opposite of weather).
  Explicit `cell_selection=sea` is harmless and worth setting.
- Requesting an on-land coordinate still resolves to a sea grid cell, but the further
  offshore the request, the more exposed the result: at `115.55` (offshore)
  `wave_height` first sample 1.9 m vs `115.70` (marina) 1.56 m. **Confirms the spec's
  call for separate `marine_latitude` / `marine_longitude`.** Chosen research coord:
  `(-31.72, 115.55)` → grid `(-31.708, 115.542)`.
- Direction conventions (from docs):
  - `wave_direction`, `swell_wave_direction`, `wind_wave_direction` → direction waves
    **come from** (0° = from N, 90° = from E). Same convention as wind.
  - `ocean_current_direction` → direction the current is **heading toward**
    (0° = going N, 90° = toward E). **Opposite convention.** Not used in V1 scoring
    but note it if currents are added.
- `swell_wave_peak_period` requested but returned **all `null`** from MFWAM. Use
  `swell_wave_period` (mean) for the swell-energy calc; treat peak period as optional.
- Units: heights `m`, periods `s`, directions `°`, SST `°C`, current `km/h`,
  `sea_level_height_msl` `m` (datum = global mean sea level, **not** LAT — so values
  are small and can be negative; fixture range roughly −0.1…+0.7 m).
- Error shape identical to weather: HTTP 400 `{"error": true, "reason": "..."}`.
- `sea_level_height_msl` doc caveat (quote): *"Accuracy is limited in coastal areas …
  This data is not suitable for coastal navigation."* → UI must say **"Modelled tide"**.

### 3.4 Model provenance / attribution (for the card + docs)

MFWAM & SMOC → Météo-France; GFS-Wave → NOAA/NCEP; all via Open-Meteo (CC-BY 4.0,
non-commercial, <10 000 calls/day). Attribution string must credit both the model
provider and Open-Meteo.

---

## 4. Astronomy / solunar library

### 4.1 Requirement: local, deterministic, offline, gives lunar transits

Needed calculations: sunrise/sunset, moonrise/moonset, **moon upper transit
(overhead) & lower transit (underfoot)**, moon phase, illumination. The transits are
the hard requirement — they define the solunar *major* periods and no free API gives
them.

### 4.2 Candidates evaluated

| Library | Version (2026-09) | Deps | Wheels for HA arches | Gives transits? | Verdict |
|---|---|---|---|---|---|
| **`astral`** | 2.2 (**this is what HA Core pins**; 3.x exists but HA has not moved) | none (pure Python, stdlib only) | n/a | **No.** 2.2's `astral.moon` only has `phase()` (0–27.99). `moonrise`/`moonset` were added in 3.x, still no meridian transit. | Use for sun events / as a zero-cost fallback only. Not sufficient for solunar. |
| **`ephem`** (PyEphem) | **4.2.1** (released 2026-02-28, actively maintained) | none (self-contained C extension, no data files) | **Yes** — PyPI ships `musllinux_1_2` wheels for `x86_64`, `aarch64`, `i686`, `s390x` and matching `manylinux`, incl. **CPython 3.14** (`cp314`). Covers HA OS/Container on amd64 + arm64. | **Yes** — `Observer.next_transit(Moon())`, `next_antitransit()`, `previous_*`, plus `next_rising`/`next_setting`. `Moon.phase` = % illuminated (0–100). | **Chosen.** Smallest footprint that does the job. |
| **`skyfield`** | 1.5x (2026-08) | **`numpy`** (already in HA Core: `numpy==2.3.2`), `jplephem`, `sgp4` | pure-Python wheels; numpy already present | **Yes** — `almanac.meridian_transits`, `almanac.risings_and_settings`, `fraction_illuminated`. Highest accuracy. | Rejected for V1: needs a JPL ephemeris (`de421.bsp`, ~17 MB) bundled in the component or downloaded at runtime — awkward over HACS, and blocking I/O to load. Overkill for feeding-time windows. Revisit only if `ephem` accuracy proves inadequate. |

### 4.3 `ephem` integration notes

- `ephem` is **not** in HA Core `requirements.txt`, so it is a legitimate custom
  requirement: `manifest.json` → `"requirements": ["ephem==4.2.1"]`,
  `"loggers": []` (ephem doesn't log).
- C extension: HA installs it from the PyPI wheel at first setup. If a wheel is
  missing for an exotic arch (e.g. 32-bit armv7/musl — no wheel), setup fails loudly;
  document that 64-bit HA OS is required, which matches HA's own 2025+ direction.
- All `ephem` calls are pure CPU, sub-millisecond, but they **must run in the
  executor** (`hass.async_add_executor_job`) or be batched in the coordinator's
  worker — never inline in the event loop for a 16-day × N-location sweep.
- Determinism: `ephem` is fully deterministic given (lat, lon, elevation, UTC
  instant). Perfect for fixture-free unit tests with hard-coded expected values.
- Wrap it: `astronomy/ephemeris.py` exposes
  `sun_events(...)`, `moon_events(...)`, `moon_phase(...)` returning our own
  dataclasses. Nothing outside that module imports `ephem`. A future swap to
  `skyfield` or an add-on touches one file.

### 4.4 Solunar behaviour (from the `bite-times` reference — observed, not ported)

Ref: <https://github.com/benpaternostro/bite-times> (README only; MIT; TS).

- **Major periods**: centred on lunar **upper and lower meridian transit**
  (overhead / underfoot). `bite-times` uses **2 h** total width.
- **Minor periods**: centred on **moonrise and moonset**. `bite-times` uses **2 h**;
  our spec says **~1 h**. → Make width configurable; default **major 2 h / minor 1 h**
  per the spec, note the divergence.
- Periods can **span midnight** → store full start/end *datetimes*, not clock strings.
- When the moon doesn't rise/set on a given local day, `bite-times` falls back to
  **estimated transit times**. We do the same (ephem still gives transits every day).
- `bite-times` is explicit that solunar scoring is *"a heuristic in the tradition of
  published solunar tables, not science"* — our `docs/scoring.md` adopts the same
  framing, and the spec's rule stands: **solunar can never override dangerous wind/swell.**

---

## 5. Home Assistant integration conventions (verified against current dev docs)

Sources: developers.home-assistant.io (Manifest, Fetching data / `DataUpdateCoordinator`,
Config entries), and `home-assistant/core@dev` (`pyproject.toml`,
`package_constraints.txt`). Checked 2026-09-10.

### 5.1 Runtime / dependency facts

- **HA Core `dev` now requires Python `>=3.14.2`.** Current stable still runs on 3.13.
  Target **3.13+** for the core library, keep it 3.14-clean. `ruff target-version` 313.
- HA pins **`astral==2.2`**, **`aiohttp==3.14.3`**, **`numpy==2.3.2`** (constraints file).
- Custom integrations must only add requirements **not** already in Core → add
  `ephem==4.2.1`, do **not** pin `astral`/`aiohttp` (use what Core provides).

### 5.2 `manifest.json` (required keys for a custom integration)

```json
{
  "domain": "fishing_forecast",
  "name": "Fishing Forecast",
  "version": "0.1.0",
  "codeowners": ["@Sam"],
  "config_flow": true,
  "dependencies": [],
  "documentation": "https://github.com/Sam/fishing-forecast-ha",
  "issue_tracker": "https://github.com/Sam/fishing-forecast-ha/issues",
  "integration_type": "service",
  "iot_class": "cloud_polling",
  "loggers": [],
  "requirements": ["ephem==4.2.1"]
}
```

- `version` is **required** for custom integrations (AwesomeVersion-valid; SemVer here).
- `integration_type: "service"` — one fishing-forecast service per config entry
  (one entry per location). Not `hub` (no child devices).
- `iot_class: "cloud_polling"` — polling Open-Meteo over the internet.
- `quality_scale` is optional for custom integrations; aim for **bronze**-tier
  conventions (config-flow only, `runtime_data`, unique IDs, diagnostics, tests)
  without formally declaring it.

### 5.3 Coordinator pattern (current, from the dev "Fetching data" page)

- `DataUpdateCoordinator[ForecastBundle]` — **typed** with our result dataclass.
- Constructor now takes **`config_entry=config_entry`** explicitly, plus `name`,
  `update_interval`, `always_update`.
- Use **`always_update=False`** and make the result dataclass comparable
  (`@dataclass(frozen=True)` / `eq=True`) so unchanged 30-min polls don't spam writes.
- Override **`_async_setup()`** for one-time init (validate coords, resolve tz);
  called automatically by `async_config_entry_first_refresh()`.
- **`_async_update_data()`** raises `UpdateFailed` (transient) or `ConfigEntryError`/
  `ConfigEntryAuthFailed` (fatal). `asyncio.TimeoutError` and `aiohttp.ClientError`
  are already caught by the base class. `UpdateFailed(retry_after=…)` for backoff.
- Store the API client / config on **`config_entry.runtime_data`**, not
  `hass.data[DOMAIN]` (current guidance).
- `__init__.py`: `async_setup_entry` → build client → create coordinator →
  `await coordinator.async_config_entry_first_refresh()` → set `runtime_data` →
  `await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)`.
  `async_unload_entry` → `async_unload_platforms`.
- HTTP: use **`homeassistant.helpers.aiohttp_client.async_get_clientsession(hass)`** —
  never create our own session, never a blocking call.

### 5.4 Config flow

- `config_flow.py` with `class FishingForecastConfigFlow(ConfigFlow, domain=DOMAIN)`,
  `async_step_user` presenting a `vol.Schema` built with HA **selectors**
  (`selector.LocationSelector` for lat/lon, `NumberSelector` for bearing/among/length,
  `TextSelector` for name).
- `async_set_unique_id(f"{lat:.4f}_{lon:.4f}")` + `_abort_if_unique_id_configured()`
  to stop duplicate locations.
- `OptionsFlow` for the tunables (weights, thresholds, window length, preferred hours) —
  read via `entry.options` with `{**DEFAULTS, **entry.options}` merge.
- Translations in `translations/en.json` (`config` + `options` + `selector` sections).

### 5.5 Detailed forecast payload — entities vs. websocket

- 16 days × 24 h × ~2 locations ≈ 768 hourly records with ~15 fields each → far too
  large for entity state attributes (HA soft-caps attributes and logs a warning
  ~16 KB).
- **V1:** expose small sensors (state = headline number, attributes = daily summaries
  only, ≤ 14 rows). Keep the full hourly dataset in **coordinator memory**.
- **Card access to hourly detail:** register a small **websocket command**
  (`fishing_forecast/hourly`, param = entry_id or location id) that returns the
  cached hourly list from `runtime_data`. No extra polling, no attribute bloat.
  This is the "better long-term design" the spec anticipates.

---

## 6. Timezone handling

- Request Open-Meteo with `timezone=<location tz>` (Mindarie → `Australia/Perth`).
  Responses are then local wall-time starting 00:00 local, with `utc_offset_seconds`.
- **Parsing:** `datetime.fromisoformat(stamp).replace(tzinfo=timezone(timedelta(seconds=utc_offset_seconds)))`
  then `.astimezone(timezone.utc)`. Do **not** use `dateutil`/`zoneinfo` name lookups
  on the API strings — trust the returned offset.
- **Internal representation:** every datetime in the models is timezone-aware **UTC**.
- **Presentation:** the card and any "05:00 PM" strings convert back using the
  location tz (`zoneinfo.ZoneInfo`), stored on the location config.
- `Australia/Perth` = UTC+8, **no DST** — but the East-coast locations the spec hints
  at later (none currently) would have DST, so the code must not hard-code +8.
- Solunar / ephem work entirely in UTC instants; only the day-bucketing for "which
  calendar day is this window" uses local tz.
- Tests: freeze time with `freezegun`, pin fixtures to `Australia/Perth`, assert the
  UTC conversion of a known row.

---

## 7. Proposed internal data models

Implemented as frozen dataclasses in
[`custom_components/fishing_forecast/models.py`](../custom_components/fishing_forecast/models.py)
(committed in this phase as the concrete proposal). Summary:

```
LocationConfig          id, name, latitude, longitude, marine_latitude,
                        marine_longitude, coast_bearing, timezone,
                        swell thresholds, preferred/exposed wind dirs, enabled

ScoringConfig           full_weights: dict[Component, float]
                        outlook_weights: dict[Component, float]
                        wind/swell/tide/solunar/sun/rain/pressure tunables
                        window_hours (default 3), preferred_hours (optional)

WeatherHour             time_utc, wind_speed_kmh, wind_dir_deg, wind_gust_kmh,
                        precip_mm_h, rain_mm_h, showers_mm_h, cloud_pct,
                        pressure_hpa (msl), weather_code, air_temp_c
MarineHour              time_utc, confidence source flags, wave_* , swell_*,
                        wind_wave_*, sst_c, sea_level_m  (every field Optional)
AstroDay                date_local, sunrise/sunset/…(utc), moonrise, moonset,
                        moon_upper_transit, moon_lower_transit,
                        moon_phase_fraction, moon_illumination
SolunarPeriod          kind (major|minor), start_utc, end_utc, centre_event
TidePoint / TideState   modelled height series → rising|falling,
                        next_extreme (high|low) + time, rate_m_per_h

ComponentScores        wind, swell, tide, solunar, sun, rain, pressure
                        (each Optional[float] 0–100; None = data missing)
HourlyScore            time_utc, components, weights_used, score, rating,
                        confidence (full|outlook), + refs to source hours
FishingWindow          start_utc, end_utc, score, is_end_inclusive_sample=False
DailyForecast          date_local, score, rating, confidence, best_window,
                        second_window, sunrise, sunset, highlights[]
ForecastBundle         location, generated_utc, hourly[], daily[],
                        best_day, data_health (per-source ok/stale/failed)
                        ← this is the coordinator's return type
```

Design rules baked in:

- **Missing ≠ zero.** Every optional metric is `Optional[float]`. A `None` component
  is dropped and the remaining weights are renormalised (`scoring/engine.py`).
- `HourlyScore.weights_used` records the actual renormalised weights for that hour —
  makes the score explainable and testable.
- `confidence` is **per hour** (derived from whether tide/fine-marine data existed),
  then a day is `full` only if a configurable fraction of its fishing-relevant hours
  are `full`.
- `FishingWindow.is_end_inclusive_sample` makes the spec's "is `end` the boundary or
  the last sample?" explicit — we store `end_utc` as the **exclusive boundary**
  (start of hour after the last included sample), flag `False`.
- Everything is `frozen=True` so the `ForecastBundle` supports `__eq__` for
  `always_update=False`.

---

## 8. Proposed test strategy

Framework: `pytest` + `pytest-asyncio` (`asyncio_mode=auto`), `syrupy` for snapshot
tests of whole `ForecastBundle`s, `freezegun` for time, `aioresponses` for the HTTP
client layer. Core scoring tests import **nothing** from `homeassistant`.

### 8.1 Layers

| Layer | Files | Style | Network |
|---|---|---|---|
| Pure scoring functions | `test_wind.py`, `test_swell.py`, `test_tide.py`, `test_solunar_score.py`, `test_sun.py`, `test_rain.py`, `test_pressure.py` | table-driven: `(inputs) -> expected 0–100`, exact values from `docs/scoring.md` | none |
| Weight engine | `test_engine.py` | renormalisation when components `None`; full vs outlook weight sets; aggregate bounds | none |
| Windows / daily | `test_windows.py`, `test_daily.py` | the spec's worked example (15:00–20:00 → 17:00–20:00 @ 91); daily = best window not mean | none |
| Astronomy | `test_ephemeris.py`, `test_solunar_intervals.py` | hard-coded expected sun/moon times for Mindarie on fixed dates (±1 min tol), cross-checked vs the Open-Meteo daily fields in the weather fixture | none |
| API parsing | `test_parse_weather.py`, `test_parse_marine.py` | load `tests/fixtures/*.json` → typed `WeatherHour`/`MarineHour`; assert tz conversion, null handling, the merge of `best_match` + `gfswave` | none (fixtures) |
| HTTP clients | `test_open_meteo_client.py` | `aioresponses` for: happy path, HTTP 400 error body, timeout, partial fields | mocked |
| Coordinator | `test_coordinator.py` | `pytest-homeassistant-custom-component`: full refresh from fixtures, marine-down → `confidence=outlook`, weather-down → keep last good + `UpdateFailed` | mocked |
| Config/options flow | `test_config_flow.py` | user step, duplicate-location abort, options round-trip | mocked |
| End-to-end snapshot | `test_bundle_snapshot.py` | fixtures → full `ForecastBundle` → `syrupy` snapshot; guards against silent scoring drift | none |

### 8.2 Fixtures (committed, in `tests/fixtures/`)

- `weather_mindarie.json` — `best_match`, 16 d, all fields non-null. Primary weather input.
- `marine_mindarie.json` — `best_match`, 16 d requested; **~9.5 d real then `null`** —
  doubles as the "missing marine data" case.
- `marine_mindarie_gfswave.json` — `ncep_gfswave025`, waves/swell 16 d — the
  outlook-with-swell case and the merge test.
- `manifest.json` / `README.md` — capture date + exact request URLs, regen script.
- Later: hand-authored **tiny** synthetic fixtures (6–12 h) for razor-sharp scoring
  edge cases (e.g. a single perfect sunset window), kept separate from the live captures.

### 8.3 CI

`ruff check` + `ruff format --check` + `mypy` + `pytest --cov` (target ≥ 90 % on
`scoring/` and `astronomy/`). GitHub Actions matrix on Python 3.13 and 3.14.
`hassfest` + `hacs/action` for manifest/HACS validation once the integration lands.

---

## 9. Open questions / risks carried into Phase 2

1. **Marine merge seam.** `best_match` (0.08°) and `ncep_gfswave025` (0.25°) will
   disagree at the ~day-9 boundary. Plan: linear cross-fade of overlapping hours, and
   flag `confidence=outlook` from the first GFS-only hour regardless of swell presence.
2. **BOM outage permanence.** If BOM never returns, no action needed. If it comes
   back, decide whether a BOM-preferring option is worth the code.
3. **Modelled tide realism at Mindarie.** SMOC at 0.08° over Perth's low
   (~0.6 m) micro-tidal range may be too smooth to locate turning points cleanly.
   Phase 6 (EOT20 / official source) is the hedge. Phase 2 tide code must not assume
   a clean sinusoid — use robust local-extrema detection with a min-prominence.
4. **`moon_phase` "fraction" exact convention** at quarters — verified new/full ends,
   assume monotonic 0→1 over the synodic month; add a test against a known first-quarter
   date before trusting illumination derived from it.
5. **Solunar minor width** — spec says 1 h, `bite-times` 2 h. Ship configurable,
   default 1 h; calibrate in Phase 5.
6. **`ephem` on unusual arches** — no musl armv7 wheel. Acceptable (64-bit HA only);
   document as a requirement.
7. **Rate / fair-use** — 30-min interval × 3 requests × N locations is trivially
   under 10 000/day, but add jitter and honour `Retry-After`.

---

## 10. Phase 2 outcome (built)

Framework-independent `models.py` + `util.py` + `api/` + `astronomy/` + `scoring/`
+ `core.py`, 102 tests, ~96% coverage on the core, `ruff` + `mypy --strict` clean.
`docs/scoring.md` is the authoritative constants source; code reads them from the
`ScoringConfig` defaults in `const.py`. No Home Assistant imports, no card.

What changed from the §9 plan during implementation:

1. **Marine merge seam** — implemented as a per-field preference (fine wins, else
   extended), not a cross-fade. `has_fine_marine` / `has_tide` flags drive the
   per-hour `full`/`outlook` decision. The cross-fade idea is deferred; the hard
   switch at the fine-model horizon is currently sharp but honest.
2. **`moon_phase` fraction** — `test_ephemeris.py` now checks ephem's synodic
   fraction against Open-Meteo's daily `moon_phase` across 12 days (< 0.05, wrapped
   at the new-moon boundary). Illumination comes straight from `ephem.Moon().phase`.
3. **Wind combine** — the "raw × strength" blend from an earlier draft mis-scored
   dead calm as poor when onshore. Replaced with
   `speed_sub × (1 − dir_weight × (1 − mult))` where
   `dir_weight = clamp(speed / 18, 0, 1)`. See `docs/scoring.md` §3.3.
4. **`preferred/exposed_wind_directions` nudge** — fields exist on `LocationConfig`
   but the ±0.1 multiplier nudge is **not** wired into `scoring/wind.py` yet
   (deferred to Phase 5 calibration).
5. **Tide extrema** — `scoring/tide.py` does discrete turning-point detection with
   parabolic sub-sample refinement, then min-spacing + min-prominence filtering,
   and returns `direction=None` (component dropped) when it can't decide. Verified
   on synthetic semidiurnal series with and without ripple noise.
6. **Windows** — triangular centre weighting `[1, 1.3, 1]` for a 3 h window; the
   spec's worked example (`17:00–20:00 @ 91`) is a passing test. `end_utc` is the
   exclusive boundary. Daily score = best window (not the 24 h mean) — tested.
7. **Dev env** — Windows needs `tzdata` for `zoneinfo` (added to dev extras, HA
   bundles it in production).

Deferred to later phases: `freezegun`-based time-freezing tests, `syrupy` snapshot
of a whole `ForecastBundle`.

---

## 11. Phase 3 outcome (Home Assistant integration)

Built in `custom_components/fishing_forecast/`:

| File | Role |
|---|---|
| `__init__.py` | `async_setup_entry` / `async_unload_entry`. **Lazy-imports HA** inside the functions so the pure core stays importable without HA installed. |
| `api/client.py` | `OpenMeteoClient` over HA's shared `aiohttp` session; 30 s timeout; `OpenMeteoError` on failure. |
| `coordinator.py` | `FishingForecastCoordinator(DataUpdateCoordinator[ForecastBundle])`. Three `asyncio.gather` fetches (weather + fine marine + gfswave), `build_forecast` in the executor (ephem hop), `always_update=False`, `UpdateFailed` on weather loss. `type FishingForecastConfigEntry = ConfigEntry[…]`. |
| `entry_data.py` | `ConfigEntry.data`/`.options` → `LocationConfig` / `ScoringConfig`. HA-free, unit-testable. |
| `config_flow.py` | UI setup (name, two `LocationSelector`s, coast bearing, forecast days) with unique-id de-dup; options flow (window, preferred hours, update interval, bearing, 7 weight %s renormalised on save). |
| `sensor.py` | Four `CoordinatorEntity` sensors: `fishing_score` (next best day, 0–100), `fishing_conditions_today`, `best_fishing_window` (`"HH:MM-HH:MM"` local), `best_fishing_day` (`DATE`, carries the 14-row `days` array + `health`). |
| `serialize.py` | Dataclasses → JSON-native dicts for the websocket + diagnostics. |
| `websocket.py` | `fishing_forecast/hourly` command → full hourly series (kept out of entity attributes). |
| `diagnostics.py` | Redacted entry dump + full bundle. |

**`ForecastBundle.generated_utc` is now `field(compare=False)`** so an unchanged
forecast compares equal (required for `always_update=False`).

### Testing constraint

`pytest-homeassistant-custom-component` needs a POSIX event loop; HA's Windows
`ProactorEventLoop` trips `pytest-socket` during fixture setup, so the integration
tests **cannot run on Windows**. They run in CI on Linux (`ci.yml` → `integration`
job) and were validated locally via a Linux (WSL) venv. The pure-core suite
(`tests/`, 104 tests) has no such constraint. `tests/conftest.py` skips
`tests/integration/` when `homeassistant` is not importable.

mypy `--strict` covers the framework-independent modules; the HA surface is
followed silently locally and type-checked with HA present in the `integration` CI
job.

---

## 12. Phase 4 outcome (Lovelace card)

`custom_components/fishing_forecast/frontend/fishing-forecast-card.js` — plain
custom element, no build step, ~500 lines incl. CSS. Ships inside the integration
and auto-registers on setup (`__init__._async_register_card` → static path +
`frontend.add_extra_js_url`; best-effort, never blocks setup). `docs/card.md` has
the config.

- Reads the daily summary (`days[]`, `best_*`, `health`, `entry_id`) from the
  `…_best_fishing_day` sensor's attributes; pulls the ~336-row hourly series on
  demand via the `fishing_forecast/hourly` websocket command when a day is opened.
- Layout: next-best panel · coloured day strip (best day starred, dashed
  full→outlook boundary) · best-windows list · tap-through day-detail SVG chart
  (score curve, wind overlay, solunar major/minor bands, sunrise/sunset markers,
  tide high/low markers with times, peak-wind + swell readout) · data-health line.
- Uses HA theme variables throughout — verified in light and dark, at 300–440 px.

Model changes for the card:

1. `HourlyScore` gained `weather` / `marine` / `tide` references so the day-detail
   view can show the real conditions behind each hour's score (aligns with the
   spec's hourly data-model example).
2. `ForecastBundle` gained `solunar_periods` and `tide_extremes` tuples.
3. `serialize.hour_to_dict` now emits raw wind/swell/tide fields; `bundle_full`
   adds `solunar_periods` and `tide_extremes`. Full payload ≈ 245 KB (websocket
   only, never entity attributes).
4. Each sensor's attributes carry `entry_id` so the card can address the
   websocket command.

Observed in the rendered card (real fixture data): the "best windows" for the
default config land at night / pre-dawn a lot — the solunar-major-at-night bias
noted in §10 item repeated. The `preferred_hours` option is the user-facing fix;
Phase 5 calibration is the systemic one.

---

## 13. Phase 5 outcome (calibration)

Full detail in `docs/calibration.md`; knowledge sources in
`docs/fishing-knowledge.md`.

- **No public daily catch-quality series exists** for a specific beach — checked
  Recfishwest, Fishwrecked forums, Fishbrain, seasonal guides. Only anecdotal,
  survivorship-biased trip reports. So calibration = local knowledge + an
  environmental backtest + opt-in feedback, not catch-fitting.
- **Fishing-style profiles** (`profiles.py`) — the headline finding. WA sources
  are clear that pink snapper / tailor / salmon off Mindarie want the rough,
  post-front, dirty-water conditions the generic V1 curve penalises. Four presets
  (`calm_water`, `beach_sport` [default], `rock_snapper`, `estuary_marina`)
  reshape swell / wind / tide / night scoring. Config-flow `profile` selector,
  changeable in options. The per-component weight sliders were removed from the
  options form (the profile is the weight preset).
- **`tools/backtest.py`** — pulls the ERA5 + marine archive (weather to 1940,
  swell to ~2022, modelled tide to ~2024) and scores every hour with the real
  engine. 20-month run on Mindarie: diurnal pattern spot-on (dawn > dusk >
  sea-breeze afternoon), top days sensible, but the daily-score scale is narrow
  (~42–88, mean ~73) — treat the score as a *ranking*, not an absolute %.
- **Calibration changes** (conservative, evidence-based): `solunar.baseline`
  50→42, `sun.base` 40→36; added `ScoringConfig.daily_second_window_weight`
  (spec §12's blend) but left it at 0 — the backtest showed a non-zero weight
  compresses the scale without improving ranking.
- **`fishing_forecast.log_session` service** (`feedback.py` + `services.yaml`) —
  one-tap session logging that snapshots the model's score + raw conditions for
  that hour into `.storage/fishing_forecast_sessions`, for a future calibration
  pass once a season of real data accumulates.

### Model changes this phase

- `ScoringConfig` gained `daily_second_window_weight` (default 0).
- `sun.night_score` optional key — full darkness returns it instead of `sun.base`
  for the nocturnal profiles.
- `FishingForecastCoordinator.profile` exposed for the feedback service.
