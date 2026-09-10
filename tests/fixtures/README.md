# Test fixtures

Stored Open-Meteo API responses so parsing / scoring tests do not hit the network.
Captured for **Mindarie, Western Australia** on the date in `manifest.json`.

| File | Endpoint | Model | Notable property |
|---|---|---|---|
| `weather_mindarie.json` | `/v1/forecast` | `best_match` | 16 days, every hourly field 100% non-null; daily `sunrise/sunset/moonrise/moonset/moon_phase` |
| `marine_mindarie.json` | `/v1/marine` | `best_match` (MeteoFrance MFWAM + SMOC) | swell partition + SST + currents + **modelled tide**; real data only ~9.5 days then `null` — doubles as the "missing marine data" case |
| `marine_mindarie_gfswave.json` | `/v1/marine` | `ncep_gfswave025` | waves + swell partition for the **full 16 days**; no SST / currents / tide |

Regenerate:

```bash
python tests/fixtures/_capture.py
```

Exact request URLs (including every parameter) are recorded in `manifest.json`
after each capture. Keep the parameters in `_capture.py` aligned with
`custom_components/fishing_forecast/const.py`.

These are live forecasts, so the *values* change every regeneration; tests assert
on **shape and horizon**, not specific numbers. Deterministic scoring edge-case
tests use small hand-authored fixtures added in Phase 2, kept as separate files.
