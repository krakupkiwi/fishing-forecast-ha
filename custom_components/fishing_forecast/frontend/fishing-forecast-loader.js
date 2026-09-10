/**
 * Fishing Forecast Card — loader
 *
 * Home Assistant loads an integration's frontend resource with a single
 * `import("<url>")`. On some Firefox builds that dynamic import of the card
 * module does not register the custom element (and Firefox caches the failure
 * for the rest of the page's life), so the card renders blank.
 *
 * This tiny module is what the integration hands to `add_extra_js_url`. Its only
 * job is to pull the real card in as a **classic `<script>`**, which is not
 * subject to module-load failure caching and behaves identically on every
 * browser. `fishing-forecast-card.js` has no import/export, so it runs fine as a
 * classic script and guards against defining itself twice.
 */

const CARD_VERSION = "0.2.1";
const CARD_SRC = "/fishing_forecast/fishing-forecast-card.js";
const TAG = "fishing-forecast-card";
const MAX_ATTEMPTS = 3;

function inject(attempt) {
  if (customElements.get(TAG)) return;
  if (attempt >= MAX_ATTEMPTS) {
    // eslint-disable-next-line no-console
    console.error(`${TAG}: could not load ${CARD_SRC} after ${MAX_ATTEMPTS} attempts`);
    return;
  }

  const bust = attempt === 0 ? CARD_VERSION : `${CARD_VERSION}-r${attempt}`;
  const script = document.createElement("script");
  script.src = `${CARD_SRC}?v=${bust}`;

  let settled = false;
  const next = () => {
    if (settled) return;
    settled = true;
    if (!customElements.get(TAG)) inject(attempt + 1);
  };
  script.addEventListener("error", next);
  // A classic <script> that loads but somehow doesn't define the element: retry.
  script.addEventListener("load", () => window.setTimeout(next, 200));

  (document.head || document.documentElement).appendChild(script);
}

if (!window.__fishingForecastCardLoader) {
  window.__fishingForecastCardLoader = true;
  inject(0);
}
