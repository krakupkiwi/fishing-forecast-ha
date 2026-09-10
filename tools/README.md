# tools/

Standalone scripts. They import the scoring core (`custom_components.fishing_forecast`)
but not Home Assistant, and use only the stdlib otherwise. Run from the repo root.

## `backtest.py`

Run the scoring engine over the Open-Meteo historical archive to sanity-check the
model against real conditions (not catch data — see `docs/calibration.md`).

```
python tools/backtest.py --start 2024-01-01 --end 2025-08-31 --profile beach_sport
```

Prints a score distribution, monthly + hourly means, and the top-N days; writes a
per-day CSV. `--profile` = any of the fishing-style profiles.

## `derive_tide_constituents.py`

Fit tidal constituents for a station from a UHSLC tide-gauge record, to build the
tables in `custom_components/fishing_forecast/tide_harmonic.py` (see `docs/tide.md`).

```
python tools/derive_tide_constituents.py --uhslc 175 --name fremantle --lat -32.065 --lon 115.747
```

Prints a `TideStation(...)` block ready to paste. WA ports with UHSLC gauges:
Fremantle (175), Hillarys, Geraldton, Esperance, Broome, Port Hedland — look up
the station number at <https://uhslc.soest.hawaii.edu/stations/>.
