# Local fishing knowledge — Perth northern beaches (Mindarie / Two Rocks / Quinns)

Compiled from public WA fishing sources (see bottom) as calibration input for
Phase 5. This is angler consensus and published guidance, **not** catch-record
data — there is no free daily catch log for a specific beach. Treat every number
below as a starting hypothesis for `docs/scoring.md`, to be refined with
opportunistic session feedback.

## The headline finding: conditions depend on the target

The generic V1 scoring assumes a *calm-water, comfort-first* angler (swell
0.5–1.5 m ideal, light offshore wind, clean water). That is correct for herring,
whiting, garfish and squid. It is **wrong** for the species that draw people to
Mindarie's rock wall and the Quinns groynes:

| Target | Wants | Generic V1 scores this |
|---|---|---|
| **Pink snapper** (rock wall, groynes, beach) | swell **2–3 m**, dirty/turbid water, drifting weed, **after winter storms**, first light | poorly (>2.5 m = "poor / unsafe") |
| **Tailor** (beach, groynes) | dawn & **dusk into dark**, some wash; **winter: rough, a NW blow before/after a cold front** | mixed — penalises the wind and swell that fire them up |
| **Australian salmon** (autumn–winter run) | "rough, overcast days fish better than calm sunny ones" | penalises the swell/wind/cloud |
| **Mulloway** (marina, groynes, gutters) | **night**, incoming tide, berley soak; "after storms can also fire" | no night awareness |
| **Herring / whiting / squid / garfish** | calmer, cleaner water, morning glass-off, dawn; squid = **rising tide**, dawn/dusk/night under lights | correctly (this is the V1 curve) |

→ **Phase 5 adds a "fishing style" profile** that reshapes the swell, wind and
tide scoring. See `docs/scoring.md` §14.

## Conditions (angler consensus)

**Tide**
- "Rising tide is generally best from shore" (squid, and broadly).
- Marina / estuary mulloway: **incoming tide**, berley up the back.
- "Tide changes" (the slack around high *and* low) called out for skippy, snapper,
  and generally.
- The V1 "rising, 1–2 h before high → 1 h after" curve is a reasonable default;
  the `estuary_marina` profile should weight the run-up more and the `rock_*`
  profiles should add value around the low turn too.

**Time of day**
- Dawn and dusk confirmed everywhere. Tailor: "an hour before dark through to
  10 pm". Mulloway & squid: night is often the best of all.
- → keep the dawn/dusk component; add an optional **night bonus** for the
  mulloway / squid styles rather than the flat `base` after dark.

**Wind**
- Calm-water species: light **easterly (offshore)** morning before the sea breeze
  — the classic Perth window. V1 already captures this.
- Tailor / salmon / snapper: an **onshore NW blow around a cold front** is a
  *positive*, not a negative — it pushes bait into the shallows and dirties the
  water. The `beach_sport` and `rock_snapper` profiles soften the onshore penalty
  and can even reward a moderate onshore when paired with a falling barometer.
- A strong wind (25 km/h+) is still hard work regardless of style — keep the
  speed sub-score dominating at the top end.

**Swell / surf**
- `calm_water`: 0.3–1.2 m ideal, drops off fast above ~1.8 m.
- `beach_sport` (tailor / salmon): 1.0–3.0 m favourable, some wash wanted.
- `rock_snapper`: 1.5–3.5 m favourable, "bigger is better" toward a
  location safety cap; dirty water and weed are fine.
- Safety: `max_safe_swell` per location still hard-caps the score — a person on
  a rock wall in 4 m of swell is in danger, not fishing.

**Weather change / pressure**
- "Before or after a cold front", "after storms" recur constantly for snapper,
  tailor, salmon, mulloway.
- → a **falling barometer** (front approaching) and the **24–48 h after a
  storm** both deserve a bonus for the storm-chasing profiles. V1's pressure
  component is directionally right (falling > rising); bump its weight for
  `beach_sport` / `rock_snapper` and add a short post-low-pressure window.

**Moon / solunar**
- No strong WA-specific signal beyond the general solunar tradition already
  modelled. Snapper anglers often mention bigger tides (spring, near new/full)
  for the rock walls — the existing new/full phase bonus covers this loosely.

## Seasonality (the model has no month input yet)

| Species | Peak around Mindarie |
|---|---|
| Pink snapper | Autumn (Mar–May) inshore; winter storms off the rock walls |
| Tailor | All year; summer beaches, bigger fish winter reefs |
| Australian salmon | Autumn–winter run, **Mar–May peak** |
| Herring | Summer best; winter spawning = concentrated on structure |
| Whiting | Year round, better in the warmer months |
| Mulloway | Spring–early summer beaches; groynes & marina at night year round |
| Squid | Cooler months, night, jetty lights |
| Skippy (silver trevally) | Winter for bigger fish |
| Samson fish | Dec–Mar, best March |

The model captures *conditions* (winter → more storms/swell/fronts) but not the
calendar. A per-profile **monthly multiplier** (from this table) is the smallest
useful season input — deferred, noted in `docs/scoring.md` §14.

## Spot notes (Mindarie / Quinns)

- **Mindarie Keys rock wall (outside)**: pink snapper after storms, tailor &
  herring around the rocks, first light best. Blowfish inside the entrance.
- **Inside the marina (back / near the restaurant, deep sections)**: big live or
  cube bait on the **incoming tide**, berley → mulloway ("sambo"), plus snook,
  skippy, tailor, bream, undersize pinkies.
- **Quinns Beach, 3rd–4th groyne north of Mindarie Keys**: herring (pollard
  berley + prawn / baitchaser rigs), tailor at sun-up / sun-down (mulies), whiting
  in the clean deep gutters with no weed, chance of mulloway; rays, gummy sharks
  and post-storm pink snapper off the beach in front of Portofino's.
- Deep, clean, weed-free **gutters** = structure = productive. Heavy drifting
  weed shuts down the bait-fishing styles but *helps* snapper.

## Sources

- Recfishwest — "Abundant fish stocks prompt metro land-based fishers to think
  pink" (land-based pink snapper, swell 2–3 m, dirty water, after winter storms):
  <https://recfishwest.org.au/news/abundant-fish-stocks-prompt-metro-land-based-fishers-to-think-pink/>
- Fishwrecked.com forum — "Mindarie Marina/Quinns Beach" thread (spot-by-spot
  local knowledge, groynes, gutters, marina mulloway, post-storm snapper):
  <http://fishwrecked.com/forum/mindarie-marinaquinns-beach>
- Wiki Fishing Spots — "When to catch fish around Perth – the seasonal calendar":
  <https://www.wikifishingspots.com.au/perth-wa-fishing-seasons/>
- Compleat Angler Nedlands — "Winter Fishing in Perth" (tide/time/weather by
  species, "tailor best in rough conditions", "rough overcast > calm sunny"):
  <https://compleatanglernedlands.com.au/blogs/news/winter-fishing-in-perth-your-complete-guide-to-the-cooler-months>
- Fishbrain — Mindarie Marina catch reports (species mix):
  <https://fishbrain.com/fishing-waters/zyySHrfH/mindarie-marina>

No dated catch-quality series was found in public sources — only anecdotal trip
reports (survivorship-biased toward good days). The backtest tool
(`tools/backtest.py`) validates the model against the *environmental* record
instead.
