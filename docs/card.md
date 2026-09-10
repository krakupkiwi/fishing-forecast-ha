# Fishing Forecast Card

A Lovelace card that renders the forecast produced by the integration. It ships
inside the integration (`custom_components/fishing_forecast/frontend/fishing-forecast-card.js`)
and is registered automatically on setup — no manual resource entry needed in the
common case.

## Usage

```yaml
type: custom:fishing-forecast-card
entity: sensor.mindarie_best_fishing_day
```

| Option | Default | Description |
|---|---|---|
| `entity` | — (required) | The `…_best_fishing_day` sensor for the location. It carries the 14-day summary, `health` and `entry_id` in its attributes. |
| `title` | `Fishing Forecast` | Card header text. |
| `collapsed_days` | `7` | Days shown in the strip before "Show all". |
| `detail_start_hour` / `detail_end_hour` | `4` / `22` | Local-hour span of the day-detail chart. |

## What it shows

- **Next best** — the highest-scoring day in range: date, best 2–3 h window,
  score / rating, `outlook` flag, and up to four condition highlights.
- **Score strip** — a coloured bar per day (rating colour), the best day starred,
  a dashed marker + "outlook from …" where the modelled-tide horizon ends.
  "Show all N days" expands to the full range.
- **Best windows** — the window time + score for each visible day.
- **Day detail** — tap any day. Loads the full hourly series once via the
  `fishing_forecast/hourly` websocket command and draws: the hourly score curve,
  a wind overlay, solunar major/minor bands, sunrise/sunset markers, tide
  high/low markers with times, and a peak-wind / swell readout.
- **Data health** — a small warning line if a source (fine marine, extended
  marine, astronomy) failed on the last update.

## Manual install (if auto-registration is disabled or fails)

The card file is served at `/fishing_forecast/fishing-forecast-card.js`. Add it
under **Settings → Dashboards → Resources**:

```
URL:  /fishing_forecast/fishing-forecast-card.js
Type: JavaScript Module
```

## Notes

- Plain custom element, no build step.
- Uses Home Assistant theme variables, so it follows light/dark and custom themes.
- The ~340 px-wide day-detail chart favours a few clear layers over a dense
  multi-axis plot; the numeric readout below it covers gust / swell period.
