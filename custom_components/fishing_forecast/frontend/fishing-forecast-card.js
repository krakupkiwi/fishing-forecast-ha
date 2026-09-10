/**
 * Fishing Forecast Card
 *
 *   type: custom:fishing-forecast-card
 *   entity: sensor.mindarie_best_fishing_day
 *
 * Reads the daily summary from the entity's attributes (`days`, `best_*`,
 * `health`, `entry_id`) and pulls the full hourly series on demand through the
 * `fishing_forecast/hourly` websocket command when a day is opened.
 *
 * Plain custom element, no build step — drop into `config/www/` and add a
 * Lovelace resource.
 */

const CARD_VERSION = "0.1.0";

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

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const svgNS = "http://www.w3.org/2000/svg";

function parseISO(s) {
  return s ? new Date(s) : null;
}

function localDate(dateStr) {
  // "2026-09-21" -> Date at local midnight
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function dayLabel(dateStr) {
  const d = localDate(dateStr);
  return DAY_NAMES[d.getDay()];
}

function longDayLabel(dateStr) {
  const d = localDate(dateStr);
  const full = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  return `${full[d.getDay()]} ${d.getDate()} ${MONTHS[d.getMonth()]}`;
}

function fmtClock(date) {
  if (!date) return "";
  let h = date.getHours();
  const m = date.getMinutes().toString().padStart(2, "0");
  const ampm = h >= 12 ? "PM" : "AM";
  h = h % 12 || 12;
  return `${h}:${m} ${ampm}`;
}

function fmtRange(startISO, endISO) {
  const s = parseISO(startISO);
  const e = parseISO(endISO);
  if (!s || !e) return "";
  return `${fmtClock(s)} – ${fmtClock(e)}`;
}

function round(v, d = 0) {
  if (v === null || v === undefined) return null;
  const f = 10 ** d;
  return Math.round(v * f) / f;
}

function compass(deg) {
  if (deg === null || deg === undefined) return "";
  const dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  return dirs[Math.round(deg / 45) % 8];
}

class FishingForecastCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._openDate = null;
    this._hourlyCache = null;
    this._hourlyPromise = null;
    this._built = false;
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("fishing-forecast-card: `entity` is required (the …_best_fishing_day sensor)");
    }
    this._config = {
      collapsed_days: 7,
      detail_start_hour: 4,
      detail_end_hour: 22,
      ...config,
    };
    this._built = false;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) this._build();
    this._render();
  }

  getCardSize() {
    return this._openDate ? 9 : 6;
  }

  static getStubConfig(hass) {
    const match = Object.keys(hass.states).find((e) => e.endsWith("_best_fishing_day"));
    return { entity: match || "sensor.fishing_best_fishing_day" };
  }

  get _state() {
    return this._hass && this._config.entity ? this._hass.states[this._config.entity] : null;
  }

  get _attrs() {
    return this._state ? this._state.attributes : {};
  }

  // ---- data --------------------------------------------------------------

  async _loadHourly() {
    const entryId = this._attrs.entry_id;
    if (!entryId || !this._hass) return;
    if (this._hourlyPromise) return this._hourlyPromise;
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
    return this._hourlyPromise;
  }

  _toggleDay(dateStr) {
    if (this._openDate === dateStr) {
      this._openDate = null;
    } else {
      this._openDate = dateStr;
      if (!this._hourlyCache) {
        this._hourlyError = null;
        this._loadHourly();
      }
    }
    this._render();
  }

  // ---- rendering --------------------------------------------------------

  _build() {
    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <ha-card>
        <div class="root"></div>
      </ha-card>
    `;
    this._root = this.shadowRoot.querySelector(".root");
    this._built = true;
  }

  _render() {
    if (!this._root) return;
    const st = this._state;
    if (!st) {
      this._root.innerHTML = `<div class="warn">Entity <code>${
        this._config.entity || "?"
      }</code> not found.</div>`;
      return;
    }
    const a = this._attrs;
    const days = Array.isArray(a.days) ? a.days : [];
    const name = a.friendly_name ? a.friendly_name.replace(/\s*Best fishing day$/i, "") : "";

    this._root.innerHTML = `
      <div class="head">
        <div class="title"><ha-icon icon="mdi:fish"></ha-icon>${this._config.title || "Fishing Forecast"}</div>
        <div class="loc">${name}</div>
      </div>
      ${this._nextBest(days)}
      ${this._strip(days)}
      ${this._windows(days)}
      ${this._openDate ? this._detail(this._openDate) : ""}
      ${this._healthLine(a.health)}
    `;

    this._root.querySelectorAll("[data-day]").forEach((el) => {
      el.addEventListener("click", () => this._toggleDay(el.getAttribute("data-day")));
    });
  }

  _nextBest(days) {
    const best = days.reduce(
      (acc, d) => (d.score !== null && (!acc || d.score > acc.score) ? d : acc),
      null
    );
    if (!best) return `<div class="panel muted">No scoreable days in range.</div>`;
    const w = best.best_window;
    const cls = RATING_CLASS[best.rating] || "r-unknown";
    const chips = (best.highlights || [])
      .slice(0, 4)
      .map((h) => `<span class="chip">${h}</span>`)
      .join("");
    return `
      <div class="panel next ${cls}" data-day="${best.date}">
        <div class="next-top">
          <div>
            <div class="next-when">${longDayLabel(best.date)}</div>
            <div class="next-window">${w ? fmtRange(w.start, w.end) : "—"}</div>
          </div>
          <div class="next-score">
            <span class="score">${round(best.score)}</span><span class="outof">/100</span>
            <div class="rating">${RATING_LABEL[best.rating] || ""}${
              best.confidence === "outlook" ? " · outlook" : ""
            }</div>
          </div>
        </div>
        ${chips ? `<div class="chips">${chips}</div>` : ""}
      </div>
    `;
  }

  _bestIndex(days) {
    let bi = -1;
    days.forEach((d, i) => {
      if (d.score !== null && (bi < 0 || d.score > days[bi].score)) bi = i;
    });
    return bi;
  }

  _visibleCount(days) {
    return this._showAll ? days.length : Math.min(this._config.collapsed_days, days.length);
  }

  _strip(days) {
    const bi = this._bestIndex(days);
    const shown = days.slice(0, this._visibleCount(days));
    const max = Math.max(60, ...shown.map((d) => d.score || 0));
    const firstOutlook = shown.findIndex((d) => d.confidence === "outlook");

    const cells = shown
      .map((d, i) => {
        const h = d.score !== null ? Math.max(6, Math.round((d.score / max) * 44)) : 4;
        const cls = RATING_CLASS[d.rating] || "r-unknown";
        const boundary = i === firstOutlook && firstOutlook > 0 ? " boundary" : "";
        const star = i === bi ? '<span class="star">★</span>' : "";
        return `
          <button class="cell${boundary}${i === bi ? " is-best" : ""}" data-day="${d.date}" title="${longDayLabel(d.date)}">
            ${star}
            <span class="bar-wrap"><span class="bar ${cls}" style="height:${h}px"></span></span>
            <span class="cell-score ${cls}">${d.score === null ? "–" : round(d.score)}</span>
            <span class="cell-day">${dayLabel(d.date)}</span>
          </button>`;
      })
      .join("");

    const outlookHint =
      firstOutlook > 0
        ? `<div class="legend"><span class="dot full"></span>full forecast<span class="dot outlook"></span>outlook from ${dayLabel(
            shown[firstOutlook].date
          )} ${localDate(shown[firstOutlook].date).getDate()}</div>`
        : "";
    const more =
      days.length > this._config.collapsed_days
        ? `<button class="more">${this._showAll ? "Show less" : `Show all ${days.length} days`}</button>`
        : "";

    return `
      <div class="strip">
        <div class="cells">${cells}</div>
        ${outlookHint}
        ${more}
      </div>
    `;
  }

  _windows(days) {
    const bi = this._bestIndex(days);
    const shown = days.slice(0, this._visibleCount(days));
    const rows = shown
      .filter((d) => d.best_window)
      .map((d) => {
        const idx = days.indexOf(d);
        const cls = RATING_CLASS[d.rating] || "r-unknown";
        const isBest = idx === bi;
        return `
          <button class="wrow ${cls} ${isBest ? "is-best" : ""}" data-day="${d.date}">
            <span class="wrow-day">${dayLabel(d.date)} ${localDate(d.date).getDate()}</span>
            <span class="wrow-time">${fmtRange(d.best_window.start, d.best_window.end)}</span>
            <span class="wrow-score">${round(d.score)}${isBest ? " ★" : ""}</span>
          </button>`;
      })
      .join("");
    if (!rows) return "";
    return `<div class="windows"><div class="windows-h">Best windows</div>${rows}</div>`;
  }

  _detail(dateStr) {
    const day = (this._attrs.days || []).find((d) => d.date === dateStr);
    if (!day) return "";
    const hourly = this._hourlyCache;
    let chart;
    if (hourly) {
      chart = this._chart(dateStr, hourly);
    } else if (this._hourlyError) {
      chart = `<div class="loading">Couldn't load the hourly detail (${this._hourlyError}).</div>`;
    } else {
      chart = `<div class="loading">Loading hourly…</div>`;
    }
    const w = day.best_window;
    return `
      <div class="detail">
        <div class="detail-head">
          <span>${longDayLabel(dateStr)}</span>
          <span class="detail-meta">${
            w ? `best ${fmtRange(w.start, w.end)} · ${round(day.score)}` : "no viable window"
          }${day.confidence === "outlook" ? " · outlook" : ""}</span>
        </div>
        ${chart}
      </div>
    `;
  }

  _chart(dateStr, hourly) {
    const start = this._config.detail_start_hour;
    const end = this._config.detail_end_hour;
    const day = localDate(dateStr);
    const inDay = (iso) => {
      const t = new Date(iso);
      return t.getFullYear() === day.getFullYear() &&
        t.getMonth() === day.getMonth() &&
        t.getDate() === day.getDate();
    };

    const hours = (hourly.hourly || []).filter((h) => {
      const t = new Date(h.time);
      return inDay(h.time) && t.getHours() >= start && t.getHours() <= end;
    });
    if (!hours.length) return `<div class="loading">No hourly detail for this day.</div>`;

    const W = 340;
    const H = 132;
    const padL = 22;
    const padR = 8;
    const padT = 10;
    const padB = 18;
    const x = (t) => {
      const d = new Date(t);
      const hr = d.getHours() + d.getMinutes() / 60;
      return padL + ((hr - start) / (end - start)) * (W - padL - padR);
    };
    const yScore = (s) => padT + (1 - s / 100) * (H - padT - padB);
    const yWind = (kmh) => padT + (1 - Math.min(kmh, 40) / 40) * (H - padT - padB);

    const ns = (tag, attrs, kids) => {
      const el = document.createElementNS(svgNS, tag);
      for (const k in attrs) el.setAttribute(k, attrs[k]);
      (kids || []).forEach((c) => el.appendChild(c));
      return el;
    };

    const svg = ns("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart", preserveAspectRatio: "none" });

    // gridlines
    [25, 50, 75].forEach((g) =>
      svg.appendChild(ns("line", { x1: padL, x2: W - padR, y1: yScore(g), y2: yScore(g), class: "grid" }))
    );

    // solunar bands
    (hourly.solunar_periods || []).forEach((p) => {
      const s = new Date(p.start);
      const e = new Date(p.end);
      if (!inDay(p.centre) && !inDay(p.start) && !inDay(p.end)) return;
      const x1 = Math.max(padL, x(p.start));
      const x2 = Math.min(W - padR, x(p.end));
      if (x2 <= x1) return;
      svg.appendChild(
        ns("rect", {
          x: x1,
          y: padT,
          width: x2 - x1,
          height: H - padT - padB,
          class: p.kind === "major" ? "band major" : "band minor",
        })
      );
    });

    // sunrise / sunset
    const dayMeta = (this._attrs.days || []).find((d) => d.date === dateStr) || {};
    ["sunrise", "sunset"].forEach((k) => {
      const hm = dayMeta[k];
      if (!hm) return;
      const [hh, mm] = hm.split(":").map(Number);
      if (hh < start || hh > end) return;
      const px = padL + ((hh + mm / 60 - start) / (end - start)) * (W - padL - padR);
      svg.appendChild(ns("line", { x1: px, x2: px, y1: padT, y2: H - padB, class: "sun-line" }));
      svg.appendChild(ns("text", { x: px, y: padT + 8, class: "sun-text" })).textContent =
        k === "sunrise" ? "☀" : "☾";
    });

    // score area + line
    const pts = hours.map((h) => `${x(h.time).toFixed(1)},${yScore(h.score ?? 0).toFixed(1)}`);
    const area = ns("polygon", {
      points: `${padL},${H - padB} ${pts.join(" ")} ${W - padR},${H - padB}`,
      class: "score-area",
    });
    svg.appendChild(area);
    svg.appendChild(ns("polyline", { points: pts.join(" "), class: "score-line" }));

    // wind line
    const windPts = hours
      .filter((h) => h.wind_speed_kmh !== null)
      .map((h) => `${x(h.time).toFixed(1)},${yWind(h.wind_speed_kmh).toFixed(1)}`);
    if (windPts.length > 1) {
      svg.appendChild(ns("polyline", { points: windPts.join(" "), class: "wind-line" }));
    }

    // tide extremes — little triangle + time just below the score baseline
    (hourly.tide_extremes || []).forEach((e) => {
      if (!inDay(e.time)) return;
      const t = new Date(e.time);
      const hr = t.getHours() + t.getMinutes() / 60;
      if (hr < start || hr > end) return;
      const px = x(e.time);
      const y0 = H - padB;
      const tri =
        e.kind === "high"
          ? `${px - 3},${y0} ${px + 3},${y0} ${px},${y0 - 5}`
          : `${px - 3},${y0 - 5} ${px + 3},${y0 - 5} ${px},${y0}`;
      svg.appendChild(ns("polygon", { points: tri, class: `tide-mark ${e.kind}` }));
      svg.appendChild(ns("text", { x: px, y: y0 - 8, class: "tide-text" })).textContent = fmtClock(t)
        .replace(":00", "")
        .replace(/\s/g, "");
    });

    // x labels
    for (let hr = start; hr <= end; hr += 3) {
      const px = padL + ((hr - start) / (end - start)) * (W - padL - padR);
      svg.appendChild(ns("text", { x: px, y: H - 4, class: "axis" })).textContent =
        hr === 12 ? "12p" : hr < 12 ? `${hr}a` : `${hr - 12}p`;
    }

    // stat readout
    const peakWind = Math.max(...hours.map((h) => h.wind_speed_kmh || 0));
    const peakHour = hours.reduce((a, b) => ((b.score ?? 0) > (a.score ?? -1) ? b : a), hours[0]);
    const swell = peakHour.swell_height_m;
    const wrap = document.createElement("div");
    wrap.className = "chart-wrap";
    wrap.appendChild(svg);
    const stats = document.createElement("div");
    stats.className = "stats";
    stats.innerHTML = `
      <span><ha-icon icon="mdi:weather-windy"></ha-icon> ${round(peakWind)} km/h peak${
        peakHour.wind_direction_deg !== null ? ` ${compass(peakHour.wind_direction_deg)}` : ""
      }</span>
      ${
        swell !== null && swell !== undefined
          ? `<span><ha-icon icon="mdi:waves"></ha-icon> ${round(swell, 1)} m${
              peakHour.swell_period_s ? ` @ ${round(peakHour.swell_period_s)} s` : ""
            }</span>`
          : ""
      }
      <span class="lg"><i class="k score"></i>score <i class="k wind"></i>wind <i class="k major"></i>major <i class="k minor"></i>minor</span>
    `;
    wrap.appendChild(stats);
    return wrap.outerHTML;
  }

  _healthLine(health) {
    if (!health) return "";
    const bad = Object.entries(health).filter(([, v]) => v !== "ok");
    if (!bad.length) return "";
    const label = { marine_fine: "fine marine", marine_extended: "extended marine" };
    return `<div class="health"><ha-icon icon="mdi:alert-outline"></ha-icon>${bad
      .map(([k, v]) => `${label[k] || k} ${v}`)
      .join(", ")}</div>`;
  }

  connectedCallback() {
    this.shadowRoot.addEventListener("click", (ev) => {
      if (ev.target.closest(".more")) {
        this._showAll = !this._showAll;
        this._render();
      }
    });
  }
}

const STYLE = `
  :host { --ffc-radius: 10px; }
  ha-card { padding: 12px 14px 14px; }
  .warn, .health { color: var(--warning-color); font-size: 0.85rem; padding: 6px 0; }
  .health ha-icon, .warn ha-icon { --mdc-icon-size: 16px; margin-right: 4px; vertical-align: -3px; }
  .head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px; }
  .title { font-weight: 600; font-size: 1.05rem; display: flex; align-items: center; gap: 6px; }
  .title ha-icon { --mdc-icon-size: 20px; color: var(--state-icon-color, var(--primary-color)); }
  .loc { color: var(--secondary-text-color); font-size: 0.9rem; }

  .panel { border-radius: var(--ffc-radius); padding: 12px; margin-bottom: 12px; }
  .muted, .panel.muted { color: var(--secondary-text-color); }

  .next { border: 1px solid var(--divider-color); position: relative; overflow: hidden; cursor: pointer; }
  .next:hover { border-color: var(--rc, var(--primary-color)); }
  .next::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--rc, var(--divider-color)); }
  .next-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
  .next-when { font-weight: 600; }
  .next-window { color: var(--secondary-text-color); font-size: 0.92rem; margin-top: 2px; }
  .next-score { text-align: right; line-height: 1.05; }
  .next-score .score { font-size: 2rem; font-weight: 700; color: var(--rc, var(--primary-text-color)); }
  .next-score .outof { color: var(--secondary-text-color); font-size: 0.8rem; }
  .next-score .rating { font-size: 0.78rem; color: var(--secondary-text-color); margin-top: 2px; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
  .chip { font-size: 0.74rem; padding: 2px 8px; border-radius: 999px;
          background: var(--secondary-background-color); color: var(--primary-text-color); }

  .strip { margin: 4px 0 12px; }
  .cells { display: flex; gap: 3px; align-items: flex-end; }
  .cell { flex: 1; background: none; border: 0; padding: 12px 0 2px; cursor: pointer; position: relative;
          display: flex; flex-direction: column; align-items: center; gap: 3px;
          border-radius: 6px; color: var(--primary-text-color); min-width: 0; }
  .cell:hover { background: var(--secondary-background-color); }
  .cell.boundary { border-left: 1px dashed var(--secondary-text-color); }
  .cell .star { position: absolute; top: 0; font-size: 0.7rem; color: var(--rc, var(--primary-color)); }
  .cell.is-best .cell-day { color: var(--primary-text-color); font-weight: 700; }
  .bar-wrap { height: 44px; display: flex; align-items: flex-end;
              border-bottom: 1px solid var(--divider-color); width: 100%; justify-content: center; }
  .bar { width: 60%; max-width: 16px; border-radius: 3px 3px 0 0; display: block; background: var(--divider-color); }
  .cell-score { font-size: 0.8rem; font-weight: 600; }
  .cell-day { font-size: 0.72rem; color: var(--secondary-text-color); white-space: nowrap; }
  .legend { font-size: 0.72rem; color: var(--secondary-text-color); margin-top: 8px; display: flex; align-items: center; gap: 5px; }
  .legend .dot { width: 8px; height: 8px; border-radius: 2px; display: inline-block; }
  .legend .dot.full { background: var(--success-color, #4caf50); }
  .legend .dot.outlook { background: var(--divider-color); margin-left: 6px; }
  .more { margin-top: 8px; background: none; border: 0; color: var(--primary-color);
          cursor: pointer; font-size: 0.82rem; padding: 2px 0; }

  .windows { margin-bottom: 8px; }
  .windows-h { font-size: 0.74rem; letter-spacing: 0.04em; text-transform: uppercase;
               color: var(--secondary-text-color); margin: 2px 0 4px; }
  .wrow { width: 100%; display: grid; grid-template-columns: 3.6em 1fr auto; align-items: center;
          gap: 10px; background: none; border: 0; padding: 7px 4px; cursor: pointer;
          color: var(--primary-text-color); border-radius: 6px; font-size: 0.86rem;
          border-bottom: 1px solid var(--divider-color); }
  .wrow.is-best { --hl: 1; }
  .wrow.is-best .wrow-day, .wrow.is-best .wrow-time { color: var(--primary-text-color); font-weight: 600; }
  .wrow:last-child { border-bottom: 0; }
  .wrow:hover { background: var(--secondary-background-color); }
  .wrow-day { color: var(--secondary-text-color); text-align: left; }
  .wrow-time { text-align: left; }
  .wrow-score { font-weight: 600; text-align: right; }

  .detail { margin-top: 10px; border-top: 1px solid var(--divider-color); padding-top: 10px; }
  .detail-head { display: flex; justify-content: space-between; align-items: baseline; font-size: 0.9rem; }
  .detail-head span:first-child { font-weight: 600; }
  .detail-meta { color: var(--secondary-text-color); font-size: 0.82rem; }
  .loading { color: var(--secondary-text-color); font-size: 0.85rem; padding: 16px 0; text-align: center; }
  .chart-wrap { margin-top: 8px; }
  .chart { width: 100%; height: 132px; display: block; }
  .chart .grid { stroke: var(--divider-color); stroke-width: 1; opacity: 0.5; }
  .chart .band.major { fill: var(--primary-color); opacity: 0.14; }
  .chart .band.minor { fill: var(--primary-color); opacity: 0.07; }
  .chart .sun-line { stroke: var(--warning-color, #ffb300); stroke-width: 1; stroke-dasharray: 2 2; opacity: 0.8; }
  .chart .sun-text { fill: var(--warning-color, #ffb300); font-size: 8px; text-anchor: middle; }
  .chart .score-area { fill: var(--primary-color); opacity: 0.16; }
  .chart .score-line { fill: none; stroke: var(--primary-color); stroke-width: 2; }
  .chart .wind-line { fill: none; stroke: var(--secondary-text-color); stroke-width: 1.2; stroke-dasharray: 3 2; opacity: 0.7; }
  .chart .tide-mark { fill: var(--info-color, #0288d1); }
  .chart .tide-mark.low { fill: var(--secondary-text-color); }
  .chart .tide-text { fill: var(--info-color, #0288d1); font-size: 7px; text-anchor: middle; }
  .chart .axis { fill: var(--secondary-text-color); font-size: 8px; text-anchor: middle; }
  .stats { display: flex; flex-wrap: wrap; gap: 12px; font-size: 0.78rem; color: var(--secondary-text-color); margin-top: 4px; }
  .stats ha-icon { --mdc-icon-size: 14px; vertical-align: -2px; }
  .stats .lg { display: flex; align-items: center; gap: 4px; margin-left: auto; }
  .stats .k { width: 10px; height: 3px; border-radius: 2px; display: inline-block; }
  .stats .k.score { background: var(--primary-color); }
  .stats .k.wind { background: var(--secondary-text-color); }
  .stats .k.major { background: var(--primary-color); opacity: 0.4; height: 8px; }
  .stats .k.minor { background: var(--primary-color); opacity: 0.2; height: 8px; }

  .r-exceptional { --rc: var(--success-color, #2e7d32); }
  .r-excellent   { --rc: var(--success-color, #43a047); }
  .r-good        { --rc: #7cb342; }
  .r-fair        { --rc: var(--warning-color, #f9a825); }
  .r-marginal    { --rc: #fb8c00; }
  .r-poor        { --rc: var(--error-color, #e53935); }
  .r-unknown     { --rc: var(--disabled-text-color, #9e9e9e); }
  .bar { background: var(--rc, var(--divider-color)); }
  .cell-score { color: var(--rc, var(--primary-text-color)); }
  .wrow-score { color: var(--rc, var(--primary-text-color)); }
  .r-unknown .bar, .bar.r-unknown { background: var(--divider-color); }
`;

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
console.info(`%c fishing-forecast-card %c v${CARD_VERSION} `, "background:#03a9f4;color:#fff;border-radius:3px 0 0 3px;padding:1px 4px", "background:#555;color:#fff;border-radius:0 3px 3px 0;padding:1px 4px");
