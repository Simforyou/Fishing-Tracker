/**
 * Fishing Tracker – Dashboard Card (schlank, v2.27)
 * Zeigt Live-Beißchance, Fischarten-Ranking und Schnellaktionen.
 * Liest echte Sensorwerte – identisch zur App, kein eigenes Rechensystem.
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
    this.selectedFish = null;
    this.attachShadow({ mode: "open" });
    this._built = false;
    this.build();
  }

  set hass(hass) {
    this._hass = hass;
    this.update();
  }

  getCardSize() { return 8; }

  // ── Helfer ────────────────────────────────────────────────────────────────
  _s(suffix) { return this._hass?.states?.[`sensor.${this.config.prefix}_${suffix}`]; }
  _num(v, f = null) { const n = parseFloat(v); return isNaN(n) ? f : n; }
  _scoreColor(v) { return v >= 75 ? "#5ee6a8" : v >= 55 ? "#ffd23f" : v >= 35 ? "#ff9d4a" : "#ff7a7a"; }

  _fishEmoji(name) {
    const m = {
      Zander:"🟢",Hecht:"🐊",Barsch:"🔴",Karpfen:"🟠",Aal:"🟤",Wels:"⚫",
      Rotauge:"🩶",Rotfeder:"🟡",Brasse:"⚪",Schleie:"🟩",Döbel:"🔵",
      Rapfen:"⬜",Barbe:"🟫",Forelle:"🌸",Ukelei:"🩵",Weißfisch:"⚪",
    };
    return m[name] || "🐟";
  }

  async _quick(caught) {
    if (!this._hass) return;
    const btn = this.shadowRoot.getElementById(caught ? "catchBtn" : "noCatchBtn");
    // Fang → volle App mit Formular; Kein Fang → direkt loggen
    if (caught) {
      window.location.href = `/${this.config.panel_path}?action=catch`;
      return;
    }
    if (btn) { btn.style.opacity = ".6"; btn.querySelector(".lbl").textContent = "Speichere…"; }
    try {
      await this._hass.callService("fishing_tracker", "log_no_catch", {});
      if (btn) {
        btn.querySelector(".lbl").textContent = "✓ Gespeichert";
        setTimeout(() => { btn.style.opacity = "1"; btn.querySelector(".lbl").textContent = "Kein Fang"; }, 2000);
      }
    } catch (e) {
      if (btn) { btn.style.opacity = "1"; btn.querySelector(".lbl").textContent = "Fehler"; }
    }
  }

  // ── Aufbau (einmalig) ───────────────────────────────────────────────────────
  build() {
    if (this._built) return;
    this._built = true;
    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; }
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,900&family=Outfit:wght@400;500;600;700;800&display=swap');
        .card {
          position:relative; overflow:hidden; border-radius:24px;
          font-family:'Outfit',system-ui,sans-serif; color:#e8f1f2;
          background:radial-gradient(120% 80% at 50% -10%, #0a3a44 0%, #052029 38%, #021015 68%, #01080b 100%);
          box-shadow:0 12px 40px rgba(0,0,0,.4);
        }
        .caustic { position:absolute; inset:0; opacity:.5; pointer-events:none; mix-blend-mode:screen;
          background:radial-gradient(40% 20% at 30% 12%, rgba(64,200,224,.2), transparent 70%),
                     radial-gradient(50% 24% at 75% 16%, rgba(40,160,190,.14), transparent 70%);
          animation:drift 9s ease-in-out infinite alternate; }
        @keyframes drift { 0%{transform:translateY(0)} 100%{transform:translateY(12px) scale(1.04)} }
        .grain { position:absolute; inset:0; pointer-events:none; opacity:.045;
          background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E"); }
        .inner { position:relative; z-index:1; padding:22px; }

        .head { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:18px; }
        .kicker { font-size:10px; letter-spacing:2.5px; text-transform:uppercase; color:#5fb8c9; font-weight:700; }
        .title { font-family:'Fraunces',serif; font-size:26px; font-weight:900; line-height:1.05; margin-top:2px;
          background:linear-gradient(180deg,#fff,#9fd9e3); -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }
        .live { display:flex; align-items:center; gap:6px; font-size:11px; color:#7aa0a8; font-weight:600; }
        .dot { width:8px; height:8px; border-radius:50%; background:#5ee6a8; box-shadow:0 0 8px #5ee6a8; }

        .gauge { display:flex; align-items:center; gap:16px; padding:16px; margin-bottom:16px;
          background:linear-gradient(145deg, rgba(255,255,255,.05), rgba(255,255,255,.01));
          border:1px solid rgba(95,184,201,.18); border-radius:18px; }
        .ring { position:relative; width:72px; height:72px; flex-shrink:0; }
        .ring svg { transform:rotate(-90deg); }
        .ring .val { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:18px; }
        .gauge .lbl2 { font-size:10px; letter-spacing:1.5px; text-transform:uppercase; color:#7aa0a8; font-weight:700; }
        .gauge .fish { font-family:'Fraunces',serif; font-size:21px; font-weight:600; color:#eaf6f8; margin:2px 0; }
        .gauge .meta { font-size:12px; color:#7aa0a8; }

        .chips { display:flex; gap:8px; margin-bottom:18px; flex-wrap:wrap; }
        .chip { flex:1; min-width:72px; background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.07);
          border-radius:14px; padding:10px 12px; }
        .chip .cl { font-size:10px; color:#7aa0a8; text-transform:uppercase; letter-spacing:.5px; }
        .chip .cv { font-size:17px; font-weight:800; margin-top:2px; }

        .sec { font-size:10px; font-weight:800; color:#5a7177; letter-spacing:2px; text-transform:uppercase; margin:0 0 10px 2px; }
        .rank { margin-bottom:18px; display:flex; flex-direction:column; gap:7px; }
        .rrow { display:flex; align-items:center; gap:10px; cursor:pointer; padding:7px 10px; border-radius:12px; transition:background .15s; }
        .rrow:hover { background:rgba(255,255,255,.04); }
        .rrow .em { font-size:16px; width:20px; text-align:center; }
        .rrow .nm { flex:1; font-size:14px; font-weight:600; }
        .rrow .bar { width:80px; height:6px; border-radius:3px; background:rgba(255,255,255,.08); overflow:hidden; }
        .rrow .barfill { height:100%; border-radius:3px; }
        .rrow .sc { width:38px; text-align:right; font-size:14px; font-weight:800; font-variant-numeric:tabular-nums; }

        .btns { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:12px; }
        .qbtn { border:none; border-radius:18px; padding:18px 12px; cursor:pointer; font-family:inherit;
          display:flex; flex-direction:column; align-items:center; gap:5px; position:relative; overflow:hidden;
          transition:transform .12s; }
        .qbtn:active { transform:scale(.96); }
        .qbtn::before { content:''; position:absolute; top:0; left:0; right:0; height:50%;
          background:linear-gradient(180deg,rgba(255,255,255,.07),transparent); }
        .qbtn .em { font-size:26px; }
        .qbtn .lbl { font-size:15px; font-weight:800; }
        .catch { background:linear-gradient(150deg,#0c5a42,#0a3d2e); color:#7ff0c0;
          box-shadow:inset 0 1px 0 rgba(120,255,200,.18); }
        .nocatch { background:linear-gradient(150deg,#5a2424,#3d1a1a); color:#ffa0a0;
          box-shadow:inset 0 1px 0 rgba(255,150,150,.16); }

        .applink { display:flex; align-items:center; justify-content:center; gap:6px;
          width:100%; padding:14px; border-radius:16px; cursor:pointer; text-decoration:none;
          background:rgba(95,184,201,.1); border:1px solid rgba(95,184,201,.25);
          color:#5fb8c9; font-size:14px; font-weight:700; font-family:inherit; }
        .applink:active { transform:scale(.98); }
        .empty { text-align:center; color:#5a7177; font-size:13px; padding:14px; }
      </style>
      <ha-card>
        <div class="card">
          <div class="caustic"></div>
          <div class="grain"></div>
          <div class="inner">
            <div class="head">
              <div>
                <div class="kicker">Fishing Tracker</div>
                <div class="title" id="ttl">${this.config.title}</div>
              </div>
              <div class="live"><span class="dot"></span> Live</div>
            </div>

            <div class="gauge">
              <div class="ring">
                <svg width="72" height="72">
                  <circle cx="36" cy="36" r="30" fill="none" stroke="rgba(255,255,255,.08)" stroke-width="6"/>
                  <circle cx="36" cy="36" r="30" fill="none" stroke="#5ee6a8" stroke-width="6" stroke-linecap="round"
                          stroke-dasharray="188.5" stroke-dashoffset="188.5" id="gring"/>
                </svg>
                <div class="val" id="gval">–</div>
              </div>
              <div>
                <div class="lbl2">Beste Beißchance jetzt</div>
                <div class="fish" id="gfish">Lade…</div>
                <div class="meta" id="gmeta"></div>
              </div>
            </div>

            <div class="chips" id="chips"></div>

            <div class="sec">Fischarten-Ranking</div>
            <div class="rank" id="rank"><div class="empty">Lade Ranking…</div></div>

            <div class="btns">
              <button class="qbtn catch" id="catchBtn"><span class="em">🐟</span><span class="lbl">Fang</span></button>
              <button class="qbtn nocatch" id="noCatchBtn"><span class="em">🚫</span><span class="lbl">Kein Fang</span></button>
            </div>

            <a class="applink" id="appLink">🗺️ Zur vollen App ›</a>
          </div>
        </div>
      </ha-card>
    `;
    this.shadowRoot.getElementById("catchBtn").addEventListener("click", () => this._quick(true));
    this.shadowRoot.getElementById("noCatchBtn").addEventListener("click", () => this._quick(false));
    this.shadowRoot.getElementById("appLink").addEventListener("click", () => {
      window.location.href = `/${this.config.panel_path}`;
    });
  }

  // ── Live-Update (bei jedem hass) ──────────────────────────────────────────
  update() {
    if (!this._built || !this._hass) return;
    const root = this.shadowRoot;

    // Ranking-Sensor (autoritative Backend-Scores)
    const rankS = this._s("species_ranking");
    const ranking = rankS?.attributes?.ranking || [];
    const best = rankS?.attributes?.best || ranking[0] || {};

    // Beißchance-Ring
    const topScore = this._num(best.score, 0);
    const topFish = best.fish_type || "—";
    const col = this._scoreColor(topScore);
    const circ = 188.5;
    const gring = root.getElementById("gring");
    gring.style.transition = "stroke-dashoffset 1s cubic-bezier(.2,.8,.3,1), stroke .4s";
    gring.style.strokeDashoffset = circ - (circ * topScore / 100);
    gring.style.stroke = col;
    const gval = root.getElementById("gval"); gval.textContent = topScore ? topScore + "%" : "–"; gval.style.color = col;
    root.getElementById("gfish").textContent = topFish;
    root.getElementById("gmeta").textContent = best.best_time ? "🕐 " + best.best_time : (best.level || "");

    // Live-Conditions aus angelwetter_index
    const awi = this._s("angelwetter_index");
    const a = awi?.attributes || {};
    const bestTime = this._s("best_time_today");
    const chips = [
      { l: "Wassertemp", v: a.water_temp != null ? Math.round(a.water_temp) + "°" : "–" },
      { l: "Wind", v: a.wind != null ? Math.round(a.wind) + "" : "–" },
      { l: "Bewölkung", v: a.cloud != null ? Math.round(a.cloud) + "%" : "–" },
      { l: "Beste Zeit", v: bestTime?.state && bestTime.state !== "unknown" ? bestTime.state : "–" },
    ];
    root.getElementById("chips").innerHTML = chips.map(c =>
      `<div class="chip"><div class="cl">${c.l}</div><div class="cv">${c.v}</div></div>`
    ).join("");

    // Ranking-Liste (Top 6)
    const rankEl = root.getElementById("rank");
    if (ranking.length) {
      rankEl.innerHTML = ranking.slice(0, 6).map(r => {
        const sc = this._num(r.score, 0);
        const rc = this._scoreColor(sc);
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
  description: "Live-Beißchance, Fischarten-Ranking und Schnellaktionen",
  preview: true,
});
