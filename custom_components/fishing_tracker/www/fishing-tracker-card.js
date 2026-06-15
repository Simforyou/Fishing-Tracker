/**
 * Fishing Tracker – Dashboard Card v2.36
 * FANGFAKTOR™-Style: 24h-Balken + Fisch-Filter, sonst Layout wie zuvor.
 *
 * Lovelace:
 *   type: custom:fishing-tracker-card
 *   title: Fishing Tracker          # optional
 *   prefix: fishing_tracker         # optional, Entity-Präfix
 *   panel_path: fishing-tracker     # optional, Pfad zur vollen App
 */
class FishingTrackerCard extends HTMLElement {
  static getStubConfig() { return { title: "Fishing Tracker" }; }

  setConfig(config) {
    this.config = {
      title: "Fishing Tracker",
      prefix: "fishing_tracker",
      panel_path: "fishing-tracker",
      ...config,
    };
    this.selectedFish = "alle";
    this.attachShadow({ mode: "open" });
    this._built = false;
    this.build();
  }

  set hass(hass) { this._hass = hass; this.update(); }
  getCardSize() { return 7; }

  _s(suffix) { return this._hass?.states?.[`sensor.${this.config.prefix}_${suffix}`]; }
  _num(v, f = null) { const n = parseFloat(v); return isNaN(n) ? f : n; }
  _colorFor(v) {
    return v >= 75 ? "#4ade80" : v >= 60 ? "#a3e635" : v >= 45 ? "#fde047" : v >= 30 ? "#fb923c" : "#ef4444";
  }
  _qualText(v) {
    return v >= 75 ? "sehr gute Fangchancen" : v >= 60 ? "gute Fangchancen" : v >= 45 ? "mittlere Fangchancen" : v >= 30 ? "schlechte Fangchancen" : "sehr schlechte Fangchancen";
  }
  _fishEmoji(name) {
    const m = { Zander:"🟢",Hecht:"🐊",Barsch:"🔴",Karpfen:"🟠",Aal:"🟤",Wels:"⚫",Rotauge:"🩶",Rotfeder:"🟡",Brasse:"⚪",Schleie:"🟩",Döbel:"🔵",Rapfen:"⬜",Barbe:"🟫",Forelle:"🌸",Ukelei:"🩵",Weißfisch:"⚪" };
    return m[name] || "🐟";
  }

  async _quick(caught) {
    if (!this._hass) return;
    const btn = this.shadowRoot.getElementById(caught ? "catchBtn" : "noCatchBtn");
    if (caught) { window.location.href = `/${this.config.panel_path}?action=catch`; return; }
    if (btn) { btn.style.opacity = ".6"; btn.querySelector(".lbl").textContent = "Speichere…"; }
    try {
      await this._hass.callService("fishing_tracker", "log_no_catch", {});
      if (btn) {
        btn.querySelector(".lbl").textContent = "✓ Gespeichert";
        setTimeout(() => { btn.style.opacity = "1"; btn.querySelector(".lbl").textContent = "🚫 Kein Fang"; }, 2000);
      }
    } catch (e) {
      if (btn) { btn.style.opacity = "1"; btn.querySelector(".lbl").textContent = "Fehler"; }
    }
  }

  build() {
    if (this._built) return;
    this._built = true;
    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; }
        .card { position:relative; overflow:hidden; border-radius:18px; font-family:system-ui,-apple-system,'SF Pro Display',sans-serif; color:#e8f1f2; background:linear-gradient(135deg,rgba(15,32,52,.97),rgba(8,15,28,.99)); padding:16px; }
        .head { display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; }
        .head .title { font-size:11px; font-weight:850; letter-spacing:1.5px; color:rgba(255,255,255,.55); text-transform:uppercase; }
        .head .live { font-size:10px; color:#4ade80; display:flex; align-items:center; gap:6px; }
        .head .live::before { content:""; width:7px; height:7px; border-radius:50%; background:#4ade80; box-shadow:0 0 6px #4ade80; }

        .ff-chips { display:flex; gap:6px; overflow-x:auto; padding-bottom:8px; margin-bottom:10px; }
        .ff-chips::-webkit-scrollbar { display:none; }
        .ff-chip { background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.1); color:rgba(255,255,255,.7); padding:5px 12px; border-radius:16px; font-size:11px; font-weight:700; cursor:pointer; white-space:nowrap; flex-shrink:0; -webkit-tap-highlight-color:transparent; font-family:inherit; }
        .ff-chip.sel { background:rgba(74,222,128,.15); border-color:rgba(74,222,128,.45); color:#4ade80; }

        .ff-score { display:flex; align-items:center; gap:14px; margin-bottom:14px; }
        .ff-big { font-size:46px; font-weight:950; line-height:1; letter-spacing:-1px; }
        .ff-qual { font-size:13px; font-weight:850; color:#fff; }
        .ff-meta { font-size:11px; color:rgba(255,255,255,.55); margin-top:4px; }

        .ff-bars { display:flex; align-items:flex-end; gap:1px; padding:0 2px; margin-bottom:14px; }
        .bcol { flex:1; display:flex; flex-direction:column; align-items:center; justify-content:flex-end; min-width:0; height:96px; }
        .bbar { width:78%; border-radius:3px 3px 1px 1px; }
        .blbl { font-size:9px; margin-top:3px; line-height:1; }

        .chips { display:grid; grid-template-columns:repeat(3,1fr); gap:6px; margin-bottom:10px; }
        .chip { background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.07); border-radius:10px; padding:8px 6px; text-align:center; }
        .cl { font-size:9px; color:rgba(255,255,255,.5); font-weight:700; letter-spacing:.5px; text-transform:uppercase; }
        .cv { font-size:14px; font-weight:850; margin-top:2px; }

        .bt { background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.07); border-radius:10px; padding:10px 12px; margin-bottom:12px; }
        .btl { font-size:9px; color:rgba(255,255,255,.5); font-weight:700; letter-spacing:.5px; text-transform:uppercase; }
        .btv { font-size:14px; font-weight:850; margin-top:2px; }

        .sec-title { font-size:10px; color:rgba(255,255,255,.5); font-weight:800; letter-spacing:1px; text-transform:uppercase; margin:8px 0; }
        .rank { display:flex; flex-direction:column; gap:4px; margin-bottom:12px; }
        .rrow { display:grid; grid-template-columns:24px 1fr 80px 30px; align-items:center; gap:8px; padding:6px 8px; background:rgba(255,255,255,.03); border-radius:8px; cursor:pointer; }
        .rrow:hover { background:rgba(255,255,255,.06); }
        .em { font-size:14px; }
        .nm { font-size:12px; font-weight:600; }
        .bar { height:6px; background:rgba(255,255,255,.08); border-radius:3px; overflow:hidden; }
        .barfill { height:100%; }
        .sc { font-size:11px; font-weight:800; text-align:right; }
        .empty { padding:14px; text-align:center; color:rgba(255,255,255,.4); font-size:11px; border:1px dashed rgba(255,255,255,.1); border-radius:8px; }

        .actions { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:10px; }
        .act { padding:14px 12px; border-radius:12px; font-weight:850; font-size:14px; cursor:pointer; border:none; font-family:inherit; transition:opacity .2s; -webkit-tap-highlight-color:transparent; }
        .act.green { background:linear-gradient(180deg,rgba(74,222,128,.25),rgba(74,222,128,.1)); border:1px solid rgba(74,222,128,.4); color:#4ade80; }
        .act.red { background:linear-gradient(180deg,rgba(239,68,68,.22),rgba(239,68,68,.1)); border:1px solid rgba(239,68,68,.4); color:#ff8585; }
        .act:active { transform:scale(.97); }

        .appBtn { display:block; padding:11px; text-align:center; text-decoration:none; background:rgba(46,168,255,.08); border:1px solid rgba(46,168,255,.25); border-radius:10px; color:#2ea8ff; font-weight:700; font-size:13px; }
        .appBtn:hover { background:rgba(46,168,255,.14); }
      </style>

      <div class="card">
        <div class="head">
          <span class="title">📊 Fangfaktor</span>
          <span class="live">Live</span>
        </div>

        <div class="ff-chips" id="chips"></div>

        <div class="ff-score">
          <div class="ff-big" id="bigScore">–</div>
          <div style="flex:1">
            <div class="ff-qual" id="qual">–</div>
            <div class="ff-meta" id="meta">–</div>
          </div>
        </div>

        <div class="ff-bars" id="bars"></div>

        <div class="chips" id="condChips"></div>
        <div class="bt"><div class="btl">⏰ Beste Zeit heute</div><div class="btv" id="bestTimeText">–</div></div>

        <div class="sec-title">Fischarten-Ranking</div>
        <div class="rank" id="rank"></div>

        <div class="actions">
          <button class="act green" id="catchBtn"><span class="lbl">🐟 Fang</span></button>
          <button class="act red"   id="noCatchBtn"><span class="lbl">🚫 Kein Fang</span></button>
        </div>
        <a class="appBtn" id="appLink" href="/${this.config.panel_path}">🗺️ Zur vollen App ›</a>
      </div>
    `;
    this.shadowRoot.getElementById("catchBtn").addEventListener("click", () => this._quick(true));
    this.shadowRoot.getElementById("noCatchBtn").addEventListener("click", () => this._quick(false));
  }

  update() {
    if (!this._built || !this._hass) return;
    const root = this.shadowRoot;

    const fcDay = this._s("bite_forecast_day");
    const points = fcDay?.attributes?.points || [];
    const rankS = this._s("species_ranking");
    const ranking = rankS?.attributes?.ranking || [];
    const awi = this._s("angelwetter_index");
    const a = awi?.attributes || {};
    const bestTime = this._s("best_time_today");

    const topFish = ranking.slice(0, 5).map(r => r.fish_type);
    const chipKeys = ["alle", ...topFish];
    const validKeys = new Set(chipKeys);
    if (!validKeys.has(this.selectedFish)) this.selectedFish = "alle";

    const chipsEl = root.getElementById("chips");
    chipsEl.innerHTML = chipKeys.map(k => {
      const sel = (k === this.selectedFish);
      const lbl = k === "alle" ? "Alle Fischarten" : k;
      return `<button class="ff-chip${sel ? " sel" : ""}" data-fish="${k}">${lbl}</button>`;
    }).join("");
    chipsEl.querySelectorAll("[data-fish]").forEach(el => {
      el.addEventListener("click", () => { this.selectedFish = el.dataset.fish; this.update(); });
    });

    let currentScore = 0;
    let bestTopScore = 0;
    let bestTopTime = "";
    if (this.selectedFish === "alle") {
      currentScore = this._num(awi?.state, this._num(points[0]?.score, 0));
      const now = new Date();
      const curH = now.getHours();
      const future = points.filter(p => {
        try { return new Date(p.timestamp).getHours() >= curH; } catch(e) { return true; }
      });
      const pool = future.length ? future : points;
      const best = pool.reduce((m,p) => (this._num(p.score,0) > (m?.s||0)) ? { s: this._num(p.score,0), t: p.timestamp } : m, null);
      if (best) {
        bestTopScore = best.s;
        try { bestTopTime = new Date(best.t).toLocaleTimeString("de-DE",{hour:"2-digit",minute:"2-digit"}); } catch(e) {}
      }
    } else {
      const fishEntry = ranking.find(r => r.fish_type === this.selectedFish);
      currentScore = this._num(fishEntry?.score, 0);
      bestTopScore = currentScore;
      bestTopTime = fishEntry?.best_time || "";
    }
    const col = this._colorFor(currentScore);
    const big = root.getElementById("bigScore");
    big.textContent = (currentScore / 10).toFixed(1);
    big.style.color = col;
    root.getElementById("qual").textContent = this._qualText(currentScore);
    root.getElementById("meta").textContent = bestTopTime
      ? `Beste Zeit: ${bestTopTime} · ${(bestTopScore/10).toFixed(1)}`
      : `Skala 0–10`;

    const BAR_AREA_PX = 76;
    const now = new Date();
    const curH = now.getHours();
    let hours24 = new Array(24).fill(0);
    if (points && points.length > 0) {
      for (const p of points.slice(0, 24)) {
        try {
          const h = new Date(p.timestamp).getHours();
          hours24[h] = this._num(p.score, 0);
        } catch(e) {}
      }
    }
    const isFishMode = this.selectedFish !== "alle";
    const barsEl = root.getElementById("bars");
    barsEl.innerHTML = hours24.map((v, h) => {
      const heightPx = Math.max(3, Math.round((Math.max(0, Math.min(100, v)) / 100) * BAR_AREA_PX));
      const isCur = h === curH;
      const clr = this._colorFor(v);
      const op = isCur ? 1 : isFishMode ? 0.35 : 0.75;
      const border = isCur ? "box-shadow:0 0 0 1.5px #fff inset;" : "";
      return `<div class="bcol">
        <div class="bbar" style="height:${heightPx}px;background:${clr};opacity:${op};${border}"></div>
        <div class="blbl" style="color:${isCur?'#fff':'rgba(255,255,255,.4)'};font-weight:${isCur?'850':'400'}">${h}</div>
      </div>`;
    }).join("");

    const wtSensor = this._hass?.states?.["sensor.wassertemperatur_gewaesser"];
    const wtVal = this._num(wtSensor?.state, this._num(a.water_temp));
    const chipsDef = [
      { l: "Wassertemp", v: wtVal != null ? wtVal.toFixed(1) + "°" : "–" },
      { l: "Wind",       v: a.wind != null ? Math.round(a.wind) + " km/h" : "–" },
      { l: "Bewölkung",  v: a.cloud != null ? Math.round(a.cloud) + "%" : "–" },
    ];
    root.getElementById("condChips").innerHTML = chipsDef.map(c =>
      `<div class="chip"><div class="cl">${c.l}</div><div class="cv">${c.v}</div></div>`
    ).join("");

    const btState = bestTime?.state;
    root.getElementById("bestTimeText").textContent =
      (btState && btState !== "unknown" && btState !== "unavailable") ? btState : "–";

    const rankEl = root.getElementById("rank");
    if (ranking.length) {
      rankEl.innerHTML = ranking.slice(0, 6).map(r => {
        const sc = this._num(r.score, 0);
        const rc = this._colorFor(sc);
        return `<div class="rrow" data-fish="${r.fish_type}">
          <span class="em">${this._fishEmoji(r.fish_type)}</span>
          <span class="nm">${r.fish_type}</span>
          <span class="bar"><span class="barfill" style="width:${sc}%;background:${rc}"></span></span>
          <span class="sc" style="color:${rc}">${sc}</span>
        </div>`;
      }).join("");
      rankEl.querySelectorAll(".rrow").forEach(row => {
        row.addEventListener("click", () => {
          window.location.href = `/${this.config.panel_path}?fish=${encodeURIComponent(row.dataset.fish)}`;
        });
      });
    } else {
      rankEl.innerHTML = `<div class="empty">Noch kein Ranking verfügbar.<br>Sensor: sensor.${this.config.prefix}_species_ranking</div>`;
    }
  }
}

customElements.define("fishing-tracker-card", FishingTrackerCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "fishing-tracker-card",
  name: "Fishing Tracker Card",
  preview: false,
  description: "Live-Beißchance, FANGFAKTOR-Balken, Fisch-Filter und Schnellaktionen",
});
