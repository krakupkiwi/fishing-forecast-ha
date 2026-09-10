/**
 * Fishing Forecast Card
 *
 *   type: custom:fishing-forecast-card
 *   entity: sensor.mindarie_best_fishing_day
 *
 * Reads the daily summary from the entity's attributes (`days`, `health`,
 * `entry_id`, `friendly_name`) and pulls the full hourly series on demand through
 * the `fishing_forecast/hourly` websocket command when a day is opened.
 *
 * Plain custom element, no build step. Written to run equally as an ES module or
 * a classic <script> (no import/export) so `fishing-forecast-loader.js` can pull
 * it in as a classic script on browsers where HA's dynamic import() of the card
 * module leaves the element unregistered (seen on Firefox). Guards against
 * defining itself twice.
 *
 * Rendering: real DOM nodes only — no innerHTML string assembly, no outerHTML
 * round-trip of the SVG chart. The card re-renders only when the entity's data,
 * the open day, or the "show all" toggle actually change, not on every `hass`.
 */

const CARD_VERSION = "0.2.0";

const RATING_CLASS = {
  exceptional: "r-exceptional",
  excellent: "r-excellent",
  good: "r-good",
  fair: "r-fair",
  marginal: "r-marginal",
  poor: "r-poor",
  unknown: "r-unknown",
};

const RATING_LABEL = {
  exceptional: "Exceptional",
  excellent: "Excellent",
  good: "Good",
  fair: "Fair",
  marginal: "Marginal",
  poor: "Poor",
  unknown: "No data",
};

const DAY_SHORT = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const DAY_LONG = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const DAY_INITIAL = ["S", "M", "T", "W", "T", "F", "S"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const SVG_NS = "http://www.w3.org/2000/svg";

// ---- tiny DOM builders ---------------------------------------------------

function h(tag, props, ...kids) {
  const el = document.createElement(tag);
  if (props) {
    for (const [k, v] of Object.entries(props)) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") el.className = v;
      else if (k === "text") el.textContent = v;
      else if (k === "dataset") Object.assign(el.dataset, v);
      else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : String(v));
    }
  }
  appendKids(el, kids);
  return el;
}

function svgEl(tag, attrs, ...kids) {
  const el = document.createElementNS(SVG_NS, tag);
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "text") el.textContent = v;
      else el.setAttribute(k, String(v)); // setAttribute keeps case: viewBox, preserveAspectRatio
    }
  }
  appendKids(el, kids);
  return el;
}

function appendKids(el, kids) {
  for (const kid of kids) {
    if (kid === null || kid === undefined || kid === false) continue;
    if (Array.isArray(kid)) appendKids(el, kid);
    else el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
}

// ---- formatting --------------------------------------------------------

function parseISO(str) {
  return str ? new Date(str) : null;
}

function localDate(dateStr) {
  // "2026-09-21" -> Date at local midnight
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function shortDay(dateStr) {
  return DAY_SHORT[localDate(dateStr).getDay()];
}

function initialDay(dateStr) {
  return DAY_INITIAL[localDate(dateStr).getDay()];
}

function longDay(dateStr) {
  const d = localDate(dateStr);
  return `${DAY_LONG[d.getDay()]} ${d.getDate()} ${MONTHS[d.getMonth()]}`;
}

function dayAndDate(dateStr) {
  const d = localDate(dateStr);
  return `${DAY_SHORT[d.getDay()]} ${d.getDate()}`;
}

function fmtClock(date) {
  if (!date) return "";
  let hr = date.getHours();
  const min = date.getMinutes().toString().padStart(2, "0");
  const ampm = hr >= 12 ? "PM" : "AM";
  hr = hr % 12 || 12;
  return `${hr}:${min} ${ampm}`;
}

function fmtRange(startISO, endISO) {
  const s = parseISO(startISO);
  const e = parseISO(endISO);
  if (!s || !e) return "";
  return `${fmtClock(s)} – ${fmtClock(e)}`;
}

function round(v, digits = 0) {
  if (v === null || v === undefined || Number.isNaN(v)) return null;
  const f = 10 ** digits;
  return Math.round(v * f) / f;
}

function compass(deg) {
  if (deg === null || deg === undefined) return "";
  return ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][Math.round(deg / 45) % 8];
}

// ---- element ----------------------------------------------------------

class FishingForecastCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._openDate = null;
    this._showAll = false;
    this._hourlyCache = null;
    this._hourlyPromise = null;
    this._hourlyError = null;
    this._built = false;
    this._sig = null;
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error(
        "fishing-forecast-card: `entity` is required (the …_best_fishing_day sensor)"
      );
    }
    this._config = {
      collapsed_days: 7,
      detail_start_hour: 4,
      detail_end_hour: 22,
      ...config,
    };
    this._sig = null;
    if (this._built) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) this._build();
    const sig = this._signature();
    if (sig === this._sig) return;
    this._render();
  }

  getCardSize() {
    return this._openDate ? 9 : 6;
  }

  static getStubConfig(hass) {
    const match = Object.keys(hass.states || {}).find((e) => e.endsWith("_best_fishing_day"));
    return { entity: match || "sensor.fishing_best_fishing_day" };
  }

  get _state() {
    return this._hass && this._config.entity ? this._hass.states[this._config.entity] : null;
  }

  get _attrs() {
    return this._state ? this._state.attributes : {};
  }

  _signature() {
    const st = this._state;
    return [
      st ? st.last_updated || st.last_changed || st.state : "none",
      this._openDate,
      this._showAll,
      this._hourlyCache ? "h" : "",
      this._hourlyError || "",
    ].join("|");
  }

  // ---- data -----------------------------------------------------------

  _loadHourly() {
    const entryId = this._attrs.entry_id;
    if (!entryId || !this._hass || this._hourlyPromise) return;
    this._hourlyPromise = this._hass
      .callWS({ type: "fishing_forecast/hourly", entry_id: entryId })
      .then((data) => {
        this._hourlyCache = data;
        this._hourlyPromise = null;
        this._render();
      })
      .catch((err) => {
        this._hourlyPromise = null;
        this._hourlyError = String(err && err.message ? err.message : err);
        // eslint-disable-next-line no-console
        console.error("fishing-forecast-card: hourly fetch failed", err);
        this._render();
      });
  }

  _toggleDay(dateStr) {
    this._openDate = this._openDate === dateStr ? null : dateStr;
    if (this._openDate && !this._hourlyCache) {
      this._hourlyError = null;
      this._loadHourly();
    }
    this._render();
  }

  _bestIndex(days) {
    let bi = -1;
    days.forEach((d, i) => {
      if (d.score !== null && d.score !== undefined && (bi < 0 || d.score > days[bi].score)) bi = i;
    });
    return bi;
  }

  _visibleWindowCount(days) {
    if (this._showAll) return days.length;
    const base = Math.min(this._config.collapsed_days, days.length);
    // Keep the starred best day in the list even if it's past the fold.
    const bi = this._bestIndex(days);
    return bi >= base ? bi + 1 : base;
  }

  // ---- rendering -----------------------------------------------------

  _build() {
    this.shadowRoot.replaceChildren(
      h("style", { text: STYLE }),
      h("ha-card", null, (this._root = h("div", { class: "root" })))
    );
    this._built = true;
  }

  _render() {
    if (!this._root) return;
    this._sig = this._signature();

    const st = this._state;
    if (!st) {
      this._root.replaceChildren(
        h(
          "div",
          { class: "warn" },
          h("ha-icon", { icon: "mdi:alert-circle-outline" }),
          h("span", null, "Entity ", h("code", { text: this._config.entity || "?" }), " not found.")
        )
      );
      return;
    }

    const a = this._attrs;
    const days = Array.isArray(a.days) ? a.days : [];
    const nodes = [this._header(a)];

    if (!days.length) {
      nodes.push(h("div", { class: "msg" }, "No forecast data yet."));
    } else {
      const bi = this._bestIndex(days);
      if (bi < 0) {
        nodes.push(h("div", { class: "msg" }, "No scoreable days in range."));
      } else {
        nodes.push(this._hero(days, bi));
        nodes.push(this._timeline(days, bi));
        const windows = this._windows(days, bi);
        if (windows) nodes.push(windows);
      }
      if (this._openDate) nodes.push(this._detail(this._openDate));
    }

    const health = this._healthNode(a.health);
    if (health) nodes.push(health);

    this._root.replaceChildren(...nodes);
  }

  _header(a) {
    const name = a.friendly_name
      ? a.friendly_name.replace(/\s*Best fishing day$/i, "").trim()
      : "";
    return h(
      "div",
      { class: "hdr" },
      h(
        "div",
        { class: "brand" },
        h("ha-icon", { icon: "mdi:fish" }),
        h("span", { text: this._config.title || "Fishing Forecast" })
      ),
      name ? h("div", { class: "loc", text: name }) : null
    );
  }

  _hero(days, bi) {
    const day = days[bi];
    const cls = RATING_CLASS[day.rating] || "r-unknown";
    const w = day.best_window;
    const isOpen = this._openDate === day.date;
    const highlights = Array.isArray(day.highlights) ? day.highlights.slice(0, 4) : [];

    const cond =
      highlights.length > 0
        ? h(
            "div",
            { class: "cond" },
            highlights.flatMap((t, i) => [
              i ? h("span", { class: "sep", text: "·" }) : null,
              document.createTextNode(t),
            ])
          )
        : null;

    return h(
      "button",
      {
        class: `hero ${cls}${isOpen ? " is-open" : ""}`,
        type: "button",
        "aria-expanded": String(isOpen),
        onclick: () => this._toggleDay(day.date),
      },
      h("div", { class: "eyebrow", text: "Next best" }),
      h("div", { class: "when", text: longDay(day.date) }),
      h("div", { class: "win", text: w ? fmtRange(w.start, w.end) : "No viable window" }),
      h(
        "div",
        { class: "rating" },
        h("span", { class: "dot" }),
        h("span", { text: RATING_LABEL[day.rating] || "" }),
        day.confidence === "outlook" ? h("span", { class: "badge", text: "outlook" }) : null
      ),
      h(
        "div",
        { class: "score" },
        h("b", { text: day.score === null ? "–" : round(day.score) }),
        h("span", { text: "/ 100" })
      ),
      cond
    );
  }

  _timeline(days, bi) {
    // The strip is compact enough to always show the full range.
    const max = Math.max(60, ...days.map((d) => d.score || 0));
    const firstOutlook = days.findIndex((d) => d.confidence === "outlook");

    const cols = days.map((d, i) => {
      const cls = RATING_CLASS[d.rating] || "r-unknown";
      const has = d.score !== null && d.score !== undefined;
      const barH = has ? Math.max(4, Math.round((d.score / max) * 44)) : 3;
      const isBest = i === bi;
      const isOpen = this._openDate === d.date;
      const boundary = i === firstOutlook && firstOutlook > 0;
      return h(
        "button",
        {
          class:
            `day ${cls}` +
            (isBest ? " is-best" : "") +
            (isOpen ? " is-open" : "") +
            (d.confidence === "outlook" ? " outlook" : "") +
            (boundary ? " boundary" : ""),
          type: "button",
          title: longDay(d.date),
          onclick: () => this._toggleDay(d.date),
        },
        isBest ? h("span", { class: "star", text: "★" }) : null,
        h("span", { class: "d-score", text: has ? round(d.score) : "–" }),
        h(
          "span",
          { class: "d-bar-wrap" },
          h("span", { class: "d-bar", style: `height:${barH}px` })
        ),
        h("span", { class: "d-name", text: initialDay(d.date) }),
        h("span", { class: "d-date", text: String(localDate(d.date).getDate()) })
      );
    });

    const children = [
      h("div", { class: "tl-h", text: "Score by day" }),
      h("div", { class: "tl-scroll" }, h("div", { class: "tl-row" }, cols)),
    ];

    if (firstOutlook > 0) {
      children.push(
        h(
          "div",
          { class: "tl-note" },
          h("span", { class: "tick" }),
          `outlook from ${dayAndDate(days[firstOutlook].date)}`
        )
      );
    }

    return h("div", { class: "tl" }, children);
  }

  _windows(days, bi) {
    const shown = days.slice(0, this._visibleWindowCount(days));
    const rows = shown
      .filter((d) => d.best_window)
      .map((d) => {
        const idx = days.indexOf(d);
        const cls = RATING_CLASS[d.rating] || "r-unknown";
        const isBest = idx === bi;
        const isOpen = this._openDate === d.date;
        return h(
          "button",
          {
            class: `wrow ${cls}${isBest ? " is-best" : ""}${isOpen ? " is-open" : ""}`,
            type: "button",
            onclick: () => this._toggleDay(d.date),
          },
          h("span", { class: "w-day", text: dayAndDate(d.date) }),
          h("span", { class: "w-time", text: fmtRange(d.best_window.start, d.best_window.end) }),
          h("span", {
            class: "w-score",
            text: `${round(d.score)}${isBest ? " ★" : ""}`,
          })
        );
      });
    if (!rows.length) return null;

    const more =
      this._showAll || shown.length < days.length
        ? h("button", {
            class: "more",
            type: "button",
            text: this._showAll ? "Show fewer" : `Show all ${days.length} days`,
            onclick: () => {
              this._showAll = !this._showAll;
              this._render();
            },
          })
        : null;

    return h(
      "div",
      { class: "win-sec" },
      h("div", { class: "win-h", text: "Best windows" }),
      rows,
      more
    );
  }

  _detail(dateStr) {
    const day = (this._attrs.days || []).find((d) => d.date === dateStr);
    if (!day) return null;
    const cls = RATING_CLASS[day.rating] || "r-unknown";
    const w = day.best_window;

    let body;
    if (this._hourlyCache) {
      body = this._chart(dateStr);
    } else if (this._hourlyError) {
      body = h("div", {
        class: "loading",
        text: `Couldn't load the hourly detail (${this._hourlyError}).`,
      });
    } else {
      body = h("div", { class: "loading", text: "Loading hourly…" });
    }

    return h(
      "div",
      { class: `detail ${cls}` },
      h(
        "div",
        { class: "detail-h" },
        h("b", { text: longDay(dateStr) }),
        h("span", {
          class: "meta",
          text:
            (w ? `best ${fmtRange(w.start, w.end)} · ${round(day.score)}` : "no viable window") +
            (day.confidence === "outlook" ? " · outlook" : ""),
        })
      ),
      body
    );
  }

  _chart(dateStr) {
    const hourly = this._hourlyCache;
    const start = this._config.detail_start_hour;
    const end = this._config.detail_end_hour;
    const day = localDate(dateStr);
    const inDay = (iso) => {
      const t = new Date(iso);
      return (
        t.getFullYear() === day.getFullYear() &&
        t.getMonth() === day.getMonth() &&
        t.getDate() === day.getDate()
      );
    };

    const hours = (hourly.hourly || []).filter((row) => {
      const t = new Date(row.time);
      return inDay(row.time) && t.getHours() >= start && t.getHours() <= end;
    });
    if (!hours.length) {
      return h("div", { class: "loading", text: "No hourly detail for this day." });
    }

    const W = 480;
    const H = 150;
    const padL = 26;
    const padR = 10;
    const padT = 12;
    const padB = 20;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;

    const x = (t) => {
      const d = new Date(t);
      const hr = d.getHours() + d.getMinutes() / 60;
      return padL + ((hr - start) / (end - start)) * innerW;
    };
    const xHour = (hr) => padL + ((hr - start) / (end - start)) * innerW;
    const yScore = (s) => padT + (1 - s / 100) * innerH;
    const yWind = (kmh) => padT + (1 - Math.min(kmh, 40) / 40) * innerH;

    const svg = svgEl("svg", {
      viewBox: `0 0 ${W} ${H}`,
      class: "chart",
      preserveAspectRatio: "none",
      role: "img",
      "aria-label": `Hourly forecast for ${longDay(dateStr)}`,
    });

    // gridlines
    for (const g of [25, 50, 75]) {
      svg.append(
        svgEl("line", { x1: padL, x2: W - padR, y1: yScore(g), y2: yScore(g), class: "grid" })
      );
    }

    // solunar bands
    for (const p of hourly.solunar_periods || []) {
      if (!inDay(p.centre) && !inDay(p.start) && !inDay(p.end)) continue;
      const x1 = Math.max(padL, x(p.start));
      const x2 = Math.min(W - padR, x(p.end));
      if (x2 <= x1) continue;
      svg.append(
        svgEl("rect", {
          x: x1,
          y: padT,
          width: x2 - x1,
          height: innerH,
          class: p.kind === "major" ? "band major" : "band minor",
        })
      );
    }

    // sunrise / sunset
    const dayMeta = (this._attrs.days || []).find((d) => d.date === dateStr) || {};
    for (const key of ["sunrise", "sunset"]) {
      const hm = dayMeta[key];
      if (!hm) continue;
      const [hh, mm] = hm.split(":").map(Number);
      if (hh < start || hh > end) continue;
      const px = xHour(hh + mm / 60);
      svg.append(svgEl("line", { x1: px, x2: px, y1: padT, y2: H - padB, class: "sun" }));
      svg.append(
        svgEl("text", { x: px, y: padT - 3, class: "sun-t", text: key === "sunrise" ? "☀" : "☾" })
      );
    }

    // score area + line
    const pts = hours.map(
      (row) => `${x(row.time).toFixed(1)},${yScore(row.score ?? 0).toFixed(1)}`
    );
    svg.append(
      svgEl("polygon", {
        points: `${padL},${H - padB} ${pts.join(" ")} ${W - padR},${H - padB}`,
        class: "area",
      })
    );
    svg.append(svgEl("polyline", { points: pts.join(" "), class: "line" }));

    // wind overlay
    const windPts = hours
      .filter((row) => row.wind_speed_kmh !== null && row.wind_speed_kmh !== undefined)
      .map((row) => `${x(row.time).toFixed(1)},${yWind(row.wind_speed_kmh).toFixed(1)}`);
    if (windPts.length > 1) {
      svg.append(svgEl("polyline", { points: windPts.join(" "), class: "wind" }));
    }

    // tide extremes
    for (const e of hourly.tide_extremes || []) {
      if (!inDay(e.time)) continue;
      const t = new Date(e.time);
      const hr = t.getHours() + t.getMinutes() / 60;
      if (hr < start || hr > end) continue;
      const px = x(e.time);
      const y0 = H - padB;
      const tri =
        e.kind === "high"
          ? `${px - 3},${y0} ${px + 3},${y0} ${px},${y0 - 5}`
          : `${px - 3},${y0 - 5} ${px + 3},${y0 - 5} ${px},${y0}`;
      svg.append(svgEl("polygon", { points: tri, class: `tide ${e.kind}` }));
      svg.append(
        svgEl("text", {
          x: px,
          y: y0 - 8,
          class: "tide-t",
          text: fmtClock(t).replace(":00", "").replace(/\s/g, ""),
        })
      );
    }

    // x axis
    for (let hr = start; hr <= end; hr += 3) {
      svg.append(
        svgEl("text", {
          x: xHour(hr),
          y: H - 5,
          class: "axis",
          text: hr === 12 ? "12p" : hr < 12 ? `${hr}a` : `${hr - 12}p`,
        })
      );
    }

    // stat readout
    const peakWind = Math.max(...hours.map((row) => row.wind_speed_kmh || 0));
    const peakHour = hours.reduce(
      (best, row) => ((row.score ?? 0) > (best.score ?? -1) ? row : best),
      hours[0]
    );
    const swell = peakHour.swell_height_m;

    const stats = h(
      "div",
      { class: "stats" },
      h(
        "span",
        null,
        h("ha-icon", { icon: "mdi:weather-windy" }),
        ` ${round(peakWind)} km/h peak` +
          (peakHour.wind_direction_deg !== null && peakHour.wind_direction_deg !== undefined
            ? ` ${compass(peakHour.wind_direction_deg)}`
            : "")
      ),
      swell !== null && swell !== undefined
        ? h(
            "span",
            null,
            h("ha-icon", { icon: "mdi:waves" }),
            ` ${round(swell, 1)} m` +
              (peakHour.swell_period_s ? ` @ ${round(peakHour.swell_period_s)} s` : "")
          )
        : null,
      h(
        "span",
        { class: "legend" },
        h("i", { class: "k-score", text: "score" }),
        h("i", { class: "k-wind", text: "wind" })
      )
    );

    return h("div", { class: "chart-wrap" }, svg, stats);
  }

  _healthNode(health) {
    if (!health) return null;
    const bad = Object.entries(health).filter(([, v]) => v && v !== "ok");
    if (!bad.length) return null;
    const label = {
      weather: "weather",
      marine_fine: "fine marine",
      marine_extended: "extended marine",
      astronomy: "astronomy",
    };
    return h(
      "div",
      { class: "warn" },
      h("ha-icon", { icon: "mdi:alert-outline" }),
      h("span", { text: bad.map(([k, v]) => `${label[k] || k} ${v}`).join(", ") })
    );
  }
}

const STYLE = `
  :host { display: block; }
  ha-card { padding: 16px; overflow: hidden; }
  .root { display: flex; flex-direction: column; }

  .hdr { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 14px; }
  .brand { display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 1rem; }
  .brand ha-icon { --mdc-icon-size: 20px; color: var(--state-icon-color, var(--primary-color)); }
  .loc { color: var(--secondary-text-color); font-size: 0.85rem; text-align: right; }

  .msg { color: var(--secondary-text-color); font-size: 0.88rem; padding: 8px 0; }
  .warn { color: var(--warning-color); font-size: 0.84rem; padding: 8px 0 2px; display: flex; align-items: center; gap: 6px; }
  .warn ha-icon { --mdc-icon-size: 16px; flex: none; }
  code { background: var(--secondary-background-color); padding: 1px 4px; border-radius: 4px; }

  /* hero */
  .hero {
    position: relative; width: 100%; text-align: left; font: inherit;
    display: grid; grid-template-columns: 1fr auto; column-gap: 14px; row-gap: 2px;
    padding: 14px; border: 1px solid var(--divider-color);
    border-left: 4px solid var(--rc, var(--primary-color));
    border-radius: 12px; background: var(--card-background-color);
    color: var(--primary-text-color); cursor: pointer;
  }
  .hero:hover, .hero.is-open { background: var(--secondary-background-color); }
  .hero .eyebrow { grid-column: 1; font-size: 0.68rem; letter-spacing: 0.09em; text-transform: uppercase; color: var(--secondary-text-color); }
  .hero .when { grid-column: 1; font-size: 1.15rem; font-weight: 700; }
  .hero .win { grid-column: 1; color: var(--secondary-text-color); font-size: 0.92rem; }
  .hero .rating { grid-column: 1; display: flex; align-items: center; gap: 6px; font-size: 0.82rem; margin-top: 3px; }
  .hero .rating .dot { width: 9px; height: 9px; border-radius: 50%; background: var(--rc, var(--disabled-text-color)); flex: none; }
  .hero .badge { font-size: 0.66rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--secondary-text-color);
                 border: 1px solid var(--divider-color); border-radius: 999px; padding: 1px 6px; }
  .hero .score { grid-column: 2; grid-row: 1 / span 4; align-self: center; text-align: center; padding-left: 6px; }
  .hero .score b { display: block; font-size: 2.4rem; font-weight: 800; line-height: 1;
                   color: var(--rc, var(--primary-text-color)); font-variant-numeric: tabular-nums; }
  .hero .score span { font-size: 0.68rem; color: var(--secondary-text-color); }
  .hero .cond { grid-column: 1 / -1; margin-top: 10px; font-size: 0.82rem; line-height: 1.5; }
  .hero .cond .sep { color: var(--secondary-text-color); margin: 0 5px; }

  /* timeline */
  .tl { margin-top: 16px; }
  .tl-h, .win-h { font-size: 0.68rem; letter-spacing: 0.09em; text-transform: uppercase; color: var(--secondary-text-color); margin-bottom: 6px; }
  .tl-scroll { overflow-x: auto; overflow-y: hidden; }
  .tl-row { display: flex; gap: 3px; align-items: flex-end; }
  .day {
    flex: 1 1 0; min-width: 0; font: inherit; background: none; border: 0;
    padding: 8px 1px 4px; display: flex; flex-direction: column; align-items: center; gap: 4px;
    border-radius: 7px; cursor: pointer; color: var(--primary-text-color); position: relative;
  }
  .day:hover, .day.is-open { background: var(--secondary-background-color); }
  .day.outlook { opacity: 0.5; }
  .day.boundary { margin-left: 5px; border-left: 1px dashed var(--secondary-text-color); }
  .day .star { position: absolute; top: -3px; font-size: 0.62rem; color: var(--rc, var(--primary-color)); }
  .day .d-score { font-size: 0.72rem; font-weight: 700; font-variant-numeric: tabular-nums; color: var(--rc, var(--primary-text-color)); }
  .day .d-bar-wrap { height: 44px; width: 100%; display: flex; align-items: flex-end; justify-content: center;
                     border-bottom: 1px solid var(--divider-color); }
  .day .d-bar { width: 60%; max-width: 13px; min-height: 3px; border-radius: 3px 3px 0 0; background: var(--rc, var(--divider-color)); }
  .day .d-name { font-size: 0.68rem; color: var(--secondary-text-color); }
  .day .d-date { font-size: 0.62rem; color: var(--secondary-text-color); opacity: 0.85; }
  .day.is-best .d-name { color: var(--primary-text-color); font-weight: 700; }
  .tl-note { font-size: 0.7rem; color: var(--secondary-text-color); margin-top: 8px; display: flex; align-items: center; gap: 6px; }
  .tl-note .tick { border-left: 1px dashed var(--secondary-text-color); height: 10px; }
  .more { align-self: flex-start; margin-top: 10px; background: none; border: 0; color: var(--primary-color);
          cursor: pointer; font-size: 0.8rem; padding: 2px 0; font: inherit; }

  /* windows */
  .win-sec { margin-top: 16px; }
  .wrow {
    width: 100%; font: inherit; display: grid; grid-template-columns: 4.2em 1fr auto; gap: 10px;
    align-items: center; background: none; border: 0; border-bottom: 1px solid var(--divider-color);
    padding: 9px 2px; cursor: pointer; color: var(--primary-text-color); font-size: 0.87rem; text-align: left;
  }
  .wrow:last-child { border-bottom: 0; }
  .wrow:hover, .wrow.is-open { background: var(--secondary-background-color); }
  .wrow .w-day { color: var(--secondary-text-color); }
  .wrow .w-score { font-weight: 700; text-align: right; color: var(--rc, var(--primary-text-color)); font-variant-numeric: tabular-nums; }
  .wrow.is-best .w-day { color: var(--primary-text-color); font-weight: 600; }

  /* detail */
  .detail { margin-top: 16px; border-top: 1px solid var(--divider-color); padding-top: 12px; }
  .detail-h { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; font-size: 0.92rem; }
  .detail-h b { font-weight: 700; }
  .detail-h .meta { color: var(--secondary-text-color); font-size: 0.8rem; text-align: right; }
  .loading { color: var(--secondary-text-color); font-size: 0.85rem; text-align: center; padding: 18px 0; }
  .chart-wrap { margin-top: 8px; }
  .chart { width: 100%; height: 144px; display: block; }
  .chart .grid { stroke: var(--divider-color); stroke-width: 1; opacity: 0.5; }
  .chart .band.major { fill: var(--rc, var(--primary-color)); opacity: 0.18; }
  .chart .band.minor { fill: var(--rc, var(--primary-color)); opacity: 0.09; }
  .chart .sun { stroke: var(--warning-color, #ffb300); stroke-width: 1; stroke-dasharray: 2 2; opacity: 0.85; }
  .chart .sun-t { fill: var(--warning-color, #ffb300); font-size: 9px; text-anchor: middle; }
  .chart .area { fill: var(--rc, var(--primary-color)); opacity: 0.18; }
  .chart .line { fill: none; stroke: var(--rc, var(--primary-color)); stroke-width: 2; stroke-linejoin: round; }
  .chart .wind { fill: none; stroke: var(--secondary-text-color); stroke-width: 1.2; stroke-dasharray: 3 2; opacity: 0.75; }
  .chart .tide { fill: var(--info-color, #0288d1); }
  .chart .tide.low { fill: var(--secondary-text-color); }
  .chart .tide-t { fill: var(--secondary-text-color); font-size: 8px; text-anchor: middle; }
  .chart .axis { fill: var(--secondary-text-color); font-size: 9px; text-anchor: middle; }
  .stats { display: flex; flex-wrap: wrap; gap: 8px 14px; font-size: 0.76rem; color: var(--secondary-text-color); margin-top: 8px; align-items: center; }
  .stats ha-icon { --mdc-icon-size: 14px; vertical-align: -2px; }
  .stats .legend { display: flex; gap: 10px; margin-left: auto; }
  .stats .legend i { font-style: normal; display: inline-flex; align-items: center; gap: 4px; }
  .stats .legend i::before { content: ""; width: 12px; height: 3px; border-radius: 2px; display: inline-block; background: currentColor; }
  .stats .legend i.k-score::before { background: var(--rc, var(--primary-color)); }
  .stats .legend i.k-wind::before { background: var(--secondary-text-color); }

  /* rating -> accent colour */
  .r-exceptional { --rc: var(--success-color, #2e7d32); }
  .r-excellent   { --rc: #43a047; }
  .r-good        { --rc: #7cb342; }
  .r-fair        { --rc: var(--warning-color, #f9a825); }
  .r-marginal    { --rc: #fb8c00; }
  .r-poor        { --rc: var(--error-color, #e53935); }
  .r-unknown     { --rc: var(--disabled-text-color, #9e9e9e); }
  .day.r-unknown .d-bar { background: var(--divider-color); }
`;

// The card may be pulled in twice (module + classic script via the loader, or a
// leftover manual resource). Only define once.
if (!customElements.get("fishing-forecast-card")) {
  customElements.define("fishing-forecast-card", FishingForecastCard);

  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "fishing-forecast-card",
    name: "Fishing Forecast Card",
    description: "Best land-based fishing days and 2–3 h windows for the next 1–2 weeks.",
    preview: false,
    documentation: "https://github.com/krakupkiwi/fishing-forecast-ha",
  });

  // eslint-disable-next-line no-console
  console.info(
    `%c fishing-forecast-card %c v${CARD_VERSION} `,
    "background:#03a9f4;color:#fff;border-radius:3px 0 0 3px;padding:1px 4px",
    "background:#555;color:#fff;border-radius:0 3px 3px 0;padding:1px 4px"
  );
}
