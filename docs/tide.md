# Phase 6 — tide

The spec: *"Only replace the existing modelled tide input if the alternative is
demonstrably better and maintainable."* So this phase was an investigation first.

## Is Open-Meteo's modelled tide any good?

Validated `sea_level_height_msl` against the **Fremantle tide gauge** (UHSLC
station #175 — the Perth-metro reference port, ~20 km south of Mindarie, same
tidal regime), 2023–2024, **13,090 aligned hours**:

| metric | result |
|---|---|
| correlation *r* | **0.977** (0.984 at +1 h lag) |
| amplitude ratio (OM / gauge) | **0.97** |
| RMS difference (de-meaned) | **0.050 m** — on a tide that swings ~0.6–0.9 m |
| turning-point timing | within ~1 h (hourly sampling limits precision) |

**Open-Meteo's modelled tide is excellent** for the ~9.5 days it covers. It even
beats a pure harmonic model there, because it includes a real storm-surge
estimate. No reason to replace it.

## Rejected: EOT20 / FES via pyTMD

The "proper" global tide models (EOT20, FES2022, TPXO) via `pyTMD` need
`scipy` + `netCDF4` + `pyproj` and hundreds of MB to GB of constituent grid
files. **Not maintainable inside a Home Assistant custom integration** — it would
have to be a separate add-on, per the spec's own escape hatch. The accuracy gain
over Open-Meteo's already-r=0.98 tide does not justify that.

## Rejected: harmonic fit to Open-Meteo's own series

Fitting constituents to the ~230 h of `sea_level_height_msl` we already fetch, to
extend it forward: tested at 140–270 mm RMS 5 days out, and >5 constituents
overfit catastrophically (a 9.5-day window can't separate them). Open-Meteo's
series also carries a large **non-tidal** component (inverted barometer, steric,
mass) that no harmonic model can predict.

## Done: a small harmonic model for the *outlook gap*

The one real problem: Open-Meteo's tide stops at ~9.5 days, so tide scoring
switched off for forecast days ~10–14. `tide_harmonic.py` fixes that:

- **21 constituents** (K1, O1, P1, M2, S2, Q1, …) derived by least-squares fit to
  **6 years (46,093 h)** of the actual Fremantle gauge record. Perth is
  diurnal-dominant: K1 (180 mm) + O1 (132 mm) ≫ M2 (51 mm) + S2 (47 mm).
- Held-out 2025 validation: **151 mm RMS** — essentially the irreducible
  non-tidal residual (a harmonic model is astronomical-only). Fine for the tide
  *score*, which cares about phase ("rising, N hours to high"), not height.
- **Numpy-free** — 21 × `amp·cos(speed·t − phase)`, ~40 lines, no new dependency.
- **One station covers the whole Perth-metro coast** (Two Rocks → Fremantle):
  the tidal-wave phase difference over ~60 km of straight open coast is a few
  minutes; amplitudes are near-identical. It auto-resolves for any location
  within 1.5° of Fremantle.

### Wiring (`core.build_forecast`)

Tide samples come from Open-Meteo where it has them; past its horizon (or when
marine is down entirely) the harmonic model fills in, **offset to join the last
real value continuously** (the gauge datum ≠ Open-Meteo's MSL datum, and only the
shape matters). Result: tide scoring and high/low markers now span the full
14-day forecast. Confidence stays `full`/`outlook` as before — harmonic tide does
not upgrade a day to `full`.

### Config

Options → **Tide station**: `Auto (nearest)` (default), `Fremantle (Perth metro)`,
or `Off — modelled tide only` (the pre-Phase-6 behaviour).

## Reproducing the constituents

`tools/derive_tide_constituents.py` downloads the UHSLC gauge CSV and re-runs the
least-squares fit. Adding another WA port (Geraldton, Bunbury, Esperance, Broome —
all have UHSLC/BOM gauges) is: fetch its record, fit, paste the constituent block
into `STATIONS`.

## Sources

- UHSLC (University of Hawaii Sea Level Center) fast-delivery hourly, Fremantle
  station #175: <https://uhslc.soest.hawaii.edu/data/>
- Open-Meteo Marine archive (`sea_level_height_msl`):
  <https://open-meteo.com/en/docs/marine-weather-api>
- Standard tidal constituent speeds: Doodson / IHO tables.
