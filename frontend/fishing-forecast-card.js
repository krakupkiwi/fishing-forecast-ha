/**
 * Fishing Forecast Card — Phase 4 (not implemented).
 *
 * type: custom:fishing-forecast-card
 * entity: sensor.fishing_score_mindarie
 *
 * Planned:
 *   - "Next best" session (day, time window, score, rating, key conditions)
 *   - 7-day score strip, optional 14-day expansion
 *   - best window per day
 *   - FULL FORECAST / OUTLOOK boundary badge
 *   - tap a day -> detail (hourly score curve, wind/gust/swell, tide markers,
 *     major/minor solunar bands, sunrise/sunset)
 *
 * Reads daily summaries from entity attributes; pulls the full hourly series over
 * the HA websocket command `fishing_forecast/hourly` (see docs/architecture.md).
 * Must follow Home Assistant card visual conventions, not a generic web dashboard.
 */

console.info("fishing-forecast-card: placeholder, not yet implemented");
