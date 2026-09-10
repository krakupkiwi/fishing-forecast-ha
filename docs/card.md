# Fishing Forecast Card

A Lovelace card that renders the forecast produced by the integration. It ships
inside the integration (`custom_components/fishing_forecast/frontend/`) and is
registered automatically on setup — no manual resource entry needed in the common
case.

Plain custom element, no build step. Rendered with real DOM nodes (no `innerHTML`
string assembly), and it re-renders only when the forecast data, the open day, or
the "show all" toggle change — not on every Home Assistant state event.

## Usage

```yaml
type: custom:fishing-forecast-card
entity: sensor.mindarie_best_fishing_day
```

| Option | Default | Description |
|---|---|---|
| `entity` | — (required) | The `…_best_fishing_day` sensor for the location. It carries the 14-day summary, `health` and `entry_id` in its attributes. |
| `title` | `Fishing Forecast` | Card header text. |
| `collapsed_days` | `7` | Rows shown in the **Best windows** list before "Show all" (the score strip always shows the full range). |
| `detail_start_hour` / `detail_end_hour` | `4` / `22` | Local-hour span of the day-detail chart. |

## What it shows

- **Hero** — the highest-scoring day in range: weekday + date, best 2–3 h window,
  a large score / 100 in the rating colour, an `outlook` badge, and up to four
  condition highlights. Tap it to open that day's detail.
- **Score by day** — a compact bar per day for the whole range (rating colour),
  the best day starred, a dashed divider + "outlook from …" where the
  modelled-tide horizon ends. Tap a bar for detail.
- **Best windows** — window time + score per day, `collapsed_days` rows then
  "Show all N days". Tap a row for detail.
- **Day detail** — tap any day. Loads the full hourly series once via the
  `fishing_forecast/hourly` websocket command and draws (as real SVG DOM nodes):
  the hourly score curve, a wind overlay, solunar major/minor bands,
  sunrise/sunset markers, tide high/low markers with times, and a peak-wind /
  swell readout.
- **Data health** — a small warning line if a source (weather, fine marine,
  extended marine, astronomy) failed on the last update.

## How it loads (and the Firefox workaround)

Home Assistant loads an integration's frontend resource with a single
`import("<url>")`. On some Firefox builds that dynamic import of the card module
leaves the custom element unregistered — a blank card, no error. HA does **not**
load the es5 fallback for module-capable browsers, so there is no second chance.

So the integration serves two files and hands HA the loader, not the card:

| Served at | Role |
|---|---|
| `/fishing_forecast/fishing-forecast-loader.js` | Tiny module HA `import()`s. Injects the card as a classic `<script>`. |
| `/fishing_forecast/fishing-forecast-card.js` | The card. Runs as a classic script or a module; guards against a double `define`. |

A classic `<script>` is not subject to module-load failure caching and behaves
the same in every browser.

## Manual install (if auto-registration is disabled or fails)

Add the card under **Settings → Dashboards → Resources**:

```
URL:  /fishing_forecast/fishing-forecast-card.js
Type: JavaScript Module
```

## Notes

- Uses Home Assistant theme variables, so it follows light/dark and custom themes.
- The day-detail chart favours a few clear layers over a dense multi-axis plot;
  the numeric readout below it covers gust / swell period.
- Iterate on it outside HA with `tools/card-preview/` (see `tools/README.md`).
