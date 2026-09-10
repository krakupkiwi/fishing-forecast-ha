# 🎣 Fishing Forecast for Home Assistant

Know which days — and which two-to-three-hour windows — are worth taking the rod
out from the shore.

Fishing Forecast rates every hour for the next 1–2 weeks from the conditions that
matter for **land-based** fishing: wind, swell, tide, sun and moon, air pressure
and rain. It finds each day's best session, highlights the standout day, and puts
it all on a dashboard card.

Tuned for the Perth metro coast (first location: **Mindarie, WA**), but it works
anywhere you can give it a latitude and longitude.

![The Fishing Forecast card](https://raw.githubusercontent.com/krakupkiwi/fishing-forecast-ha/main/screenshots/card-overview.png)

## What you get

- **A next-best-day headline** — the top day in range with its best window, a
  0–100 rating, and the reasons behind it (offshore wind, solunar period, clean
  swell…).
- **A score for every day** at a glance, with the best day starred.
- **The best 2–3 hour window for each day**, so you know *when* to go, not just
  whether.
- **Tap any day** for an hourly chart: the score curve, wind, solunar feeding
  periods, sunrise/sunset, and tide highs and lows with their times.
- **Sensors** for the best day and next window — use them in automations and
  notifications.
- **Fishing-style profiles** — tell it what you target and the scoring adapts.

Everything runs on free, no-key data from [Open-Meteo](https://open-meteo.com)
plus offline sun/moon calculations. No account, no API key.

## Screenshots

| Best windows per day | Tap a day for detail |
|---|---|
| ![Best windows list](https://raw.githubusercontent.com/krakupkiwi/fishing-forecast-ha/main/screenshots/card-best-windows.png) | ![Hourly day-detail chart](https://raw.githubusercontent.com/krakupkiwi/fishing-forecast-ha/main/screenshots/card-day-detail.png) |

## Install

### HACS

1. HACS → **⋮** → **Custom repositories**. Add
   `https://github.com/krakupkiwi/fishing-forecast-ha` with category
   **Integration**.
2. Search HACS for **Fishing Forecast**, **Download** it, then **restart Home
   Assistant**.
3. **Settings → Devices & Services → Add Integration → Fishing Forecast**. Enter
   your location and pick a fishing style.

### Manual

Copy `custom_components/fishing_forecast/` into your `config/custom_components/`
folder, restart Home Assistant, then add the integration as in step 3 above.

## Add the card

The card ships with the integration and registers itself — no resource setup
needed. Add it to any dashboard:

```yaml
type: custom:fishing-forecast-card
entity: sensor.mindarie_best_fishing_day
```

Use the **Best fishing day** sensor for your location. Card options (title, how
many window rows to show before "show all", chart hours) are in
[`docs/card.md`](docs/card.md).

## Fishing style

Pick this when you add the integration; change it any time in its options. It
reshapes how much wind, swell, tide and darkness count.

| Profile | Target |
|---|---|
| **Calm water** | herring, whiting, squid, garfish — calm, clean water |
| **Beach sport** *(default)* | tailor, Australian salmon — some wash, dawn/dusk, weather fronts |
| **Rock wall / groyne** | pink snapper, mulloway off the walls — swell, after storms |
| **Estuary / marina** | mulloway, bream inside the marina — run-in tide, night |

## Good to know

- Days inside the modelled-tide horizon (~9 days) are marked **full forecast**.
  Further out is **outlook** and shown as less certain — it never implies marine
  precision it doesn't have.
- The modelled tide is validated against the Fremantle gauge (r = 0.98) but is
  **not** an official tide table.
- The 0–100 score **ranks the days against each other**. It is not a probability
  of catching fish.

## Under the hood

Design notes, every scoring constant, and the calibration work live in
[`docs/`](docs/): [architecture](docs/architecture.md) ·
[scoring](docs/scoring.md) · [research](docs/research.md) ·
[calibration](docs/calibration.md) · [tide](docs/tide.md) ·
[local fishing knowledge](docs/fishing-knowledge.md).

The scoring core imports nothing from Home Assistant and is tested against stored
API fixtures. To work on it: `pip install -e ".[dev]"`, then `ruff check .`,
`mypy`, and `pytest`. Integration tests need Linux or macOS.

## Credits & licence

Weather and marine data © [Open-Meteo](https://open-meteo.com) (CC-BY 4.0),
derived from Météo-France, NOAA/NCEP, DWD and ECMWF models. Sun and moon
positions via [ephem](https://pypi.org/project/ephem/). This project is not
affiliated with Open-Meteo or any weather service.

MIT — see [`LICENSE`](LICENSE).
