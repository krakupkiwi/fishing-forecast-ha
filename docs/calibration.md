# Phase 5 — calibration

## The problem

The scoring weights and curves are heuristics from `docs/project-spec.md`, refined
with WA land-based fishing knowledge (`docs/fishing-knowledge.md`). True
calibration needs ground truth — "on this date/time, fishing was actually good
here." There is **no free daily catch record** for a specific beach, and the user
does not fish often enough to log constant feedback. So Phase 5 is three things:

1. **Fishing-style profiles** — the biggest finding from the local knowledge.
2. **Historical backtest** — validate the model against the environmental record.
3. **Opportunistic feedback** — a one-tap service for the sessions you *do* fish.

## 1. Fishing-style profiles (`custom_components/fishing_forecast/profiles.py`)

The generic V1 curve assumes calm-water comfort fishing. WA sources are emphatic
that pink snapper and tailor off Mindarie's rock wall / beach want the **rough,
post-front, dirty-water** conditions that curve penalises. So a `profile` (set in
the config flow, changeable in options) reshapes swell, wind, tide and
time-of-day scoring:

| Profile | Swell sweet spot | Onshore wind | Night | Tide |
|---|---|---|---|---|
| `calm_water` (herring, whiting, squid) | 0.5–1.5 m | penalised (V1) | base | V1 |
| `beach_sport` (tailor, salmon) — **default** | 1.0–3.0 m | softened (×0.6) | 55 | V1 |
| `rock_snapper` (pink snapper, mulloway, storms) | 1.5–3.5 m, bigger is better | barely penalised (×0.8) | 65 | + low turn |
| `estuary_marina` (marina/river mulloway, bream) | irrelevant | irrelevant (sheltered) | 78 | run-in heavily favoured |

Each is a partial override on `default_scoring_config()`; weights are
re-normalised. `test_profiles.py` checks a 2.5 m swell scores 30+ points higher
for `rock_snapper` than `calm_water`, and the reverse for a 0.5 m swell.

## 2. Historical backtest (`tools/backtest.py`)

```
python tools/backtest.py --start 2024-01-01 --end 2025-08-31 --profile beach_sport
```

Pulls the ERA5 weather archive + the marine archive (Open-Meteo) and scores every
hour with the real engine. Data availability for Mindarie:

| | back to |
|---|---|
| wind / gust / rain / pressure / cloud | 1940 (ERA5) |
| swell height / period / direction, waves | ~2022 |
| modelled tide (`sea_level_height_msl`) | ~2024 |

### What the 20-month backtest (609 days) showed

**Good:**
- **Diurnal pattern is right** — mean hourly score peaks at 07:00 (≈70), a second
  bump at 18:00 (≈66), trough 13:00–15:00 (≈58). Dawn > dusk > sea-breeze
  afternoon, exactly as anglers describe.
- **Top-ranked days are sensible** — dominated by autumn (Feb–Apr) dawn sessions
  with a light easterly, a solunar major and a clean 1–2 m swell: the classic
  Perth glass-off morning.
- The model **responds to conditions** — it is not flat, and it is not scoring
  everything 90.

**Limitations (documented, not "fixed" by fitting):**
- **The scale is narrow** — daily best-window scores sit in ~42–88, mean ~73;
  a genuine 90+ (all seven factors aligned) did not occur once in 20 months, and
  sub-40 days are rare. Treat the score as a **ranking of days/hours**, not an
  absolute "quality percentage". The `beach_sport` and `rock_snapper` profiles
  produce near-identical daily *distributions* even though they differ sharply per
  hour — swell is only ~20 % of the weight and most days it is "fine" for both.
- **Season** — the model has no month input. It rates July–August lowest (more
  wind, bigger swell, more rain), which is only half right for `beach_sport`:
  winter storms fire up salmon and tailor, but they also make the rock walls
  genuinely dangerous. A per-profile monthly multiplier from
  `docs/fishing-knowledge.md` is the smallest useful season input — deferred.

### Calibration changes made (evidence-based, conservative)

- `solunar.baseline` 50 → **42**, `sun.base` 40 → **36**: a truly dead hour was
  scoring half marks and inflating every day's floor. Also nudged
  `near_major`/`inside_minor`/`near_minor` down a couple of points.
- `daily_second_window_weight` added to `ScoringConfig` (spec §12's
  `best*0.8 + second*0.2` idea) but left at **0** by default — the backtest showed
  a non-zero weight compresses the top of the scale without improving day
  ranking, because every 24 h span has *some* second window.

Nothing else was changed. Chasing a prettier histogram without ground truth would
be fitting to aesthetics.

## 3. Opportunistic feedback (`fishing_forecast.log_session` service)

```yaml
service: fishing_forecast.log_session
data:
  result: good        # poor | average | good | excellent
  species: tailor     # optional
  at: "2026-04-06 06:30:00"   # optional, defaults to now
```

Appends to `.storage/fishing_forecast_sessions` a record of your result **plus the
model's hourly score and raw conditions for that hour**. Over a season that is
20–40 real prediction-vs-outcome pairs — enough for a future calibration pass to
adjust weights per profile. Not required, not constant: one call when you get home.

## Next

- Re-run the backtest per profile after a season of `log_session` data and compare
  the model's score at each logged time to the logged result.
- If a per-profile monthly multiplier proves worth it, add it.
- Phase 6: a real tide model (EOT20) if it demonstrably beats the modelled
  `sea_level_height_msl` near shore.
