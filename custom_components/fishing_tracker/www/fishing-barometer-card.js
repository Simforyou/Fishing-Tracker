/**
 * Fishing Barometer Card v2.0 — TRAC-Style
 * Halbkreis-Druckanzeige 980-1050 hPa mit Fang-Bedingungs-Farbzonen.
 *
 * Lovelace:
 *   type: custom:fishing-barometer-card
 *   pressure_sensor: sensor.haftenkamp_druck      # optional
 *   title: Fishing Barometer                       # optional
 */
class FishingBarometerCard extends HTMLElement {
  setConfig(config) {
    this.config = {
      title: "Fishing Barometer",
      pressure_sensor: "sensor.haftenkamp_druck",
      ...config,
    };
    this.attachShadow({ mode: "open" });
    this._built = false;
    this.build();
  }

  set hass(hass) { this._hass = hass; this.update(); }
  getCardSize() { return 5; }

  _num(v, f = null) { const n = parseFloat(v); return isNaN(n) ? f : n; }

  // Druck → Winkel im Halbkreis (980 = links 180°, 1050 = rechts 0°)
  _pressureToAngle(p) {
    const clamped = Math.min(1050, Math.max(980, p));
    return 180 - ((clamped - 980) / 70) * 180;
  }
  // Polar → kartesisch
  _polar(cx, cy, r, angleDeg) {
    const a = angleDeg * Math.PI / 180;
    return [cx - Math.cos(a) * r, cy - Math.sin(a) * r];
  }
  // SVG arc-path zwischen zwei Winkeln auf Radius r
  _arcPath(cx, cy, r, startDeg, endDeg) {
    const [x1, y1] = this._polar(cx, cy, r, startDeg);
    const [x2, y2] = this._polar(cx, cy, r, endDeg);
    const largeArc = Math.abs(endDeg - startDeg) > 180 ? 1 : 0;
    // sweep flag: 0 wegen unserer "spiegelverkehrten" Polar (cosine subtraction)
    return `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 0 ${x2} ${y2}`;
  }

  _trend(p, m1h, m3h) {
    if (p == null || isNaN(p)) return { label: "Unbekannt", arrow: "?", quality: "POOR", advice: "—" };
    const d1 = (m1h != null && !isNaN(m1h)) ? p - m1h : 0;
    const d3 = (m3h != null && !isNaN(m3h)) ? (p - m3h) / 3 : 0;
    const rate = Math.abs(d1) > Math.abs(d3) ? d1 : d3;
    let label, arrow, quality, advice;
    if (rate > 2.0)      { label = "Schnell steigend"; arrow = "↑"; quality = "GOOD"; advice = "Gut – Druckanstieg"; }
    else if (rate > 0.4) { label = "Steigend";         arrow = "↗"; quality = "GREAT"; advice = "Beste Bedingungen"; }
    else if (rate < -2.0){ label = "Schnell fallend";  arrow = "↓"; quality = "GOOD"; advice = "Gut JETZT, dann schwach"; }
    else if (rate < -0.4){ label = "Fallend";          arrow = "↘"; quality = "GOOD"; advice = "Gut, wird schlechter"; }
    else                 { label = "Stabil";           arrow = "→"; quality = "POOR"; advice = "Schwach – kein Trend"; }
    // Override: sehr tief
    if (p < 1005) { quality = "POOR"; if (rate > -0.4 && rate < 0.4) advice = "Sehr tief – schwach"; }
    return { label, arrow, quality, advice };
  }

  build() {
    if (this._built) return;
    this._built = true;
    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; }
        .card { border-radius:18px; font-family:system-ui,-apple-system,sans-serif; color:#e8f1f2; background:linear-gradient(135deg,rgba(15,32,52,.97),rgba(8,15,28,.99)); padding:16px; position:relative; overflow:hidden; }
        .head { display:flex; align-items:center; justify-content:space-between; margin-bottom:8px; }
        .head .t { font-size:11px; font-weight:850; letter-spacing:1.5px; color:rgba(255,255,255,.55); text-transform:uppercase; }
        .head .live { font-size:10px; color:#4ade80; display:flex; align-items:center; gap:6px; }
        .head .live::before { content:""; width:7px; height:7px; border-radius:50%; background:#4ade80; box-shadow:0 0 6px #4ade80; }

        .dial { position:relative; width:100%; aspect-ratio:1.6/1; margin:8px 0 12px; }
        .dial svg { width:100%; height:100%; display:block; }

        .big { text-align:center; margin:4px 0 6px; }
        .pv { font-size:42px; font-weight:950; line-height:1; letter-spacing:-1px; }
        .pu { font-size:14px; font-weight:700; color:rgba(255,255,255,.5); margin-left:6px; }
        .trend { display:flex; align-items:center; justify-content:center; gap:8px; font-size:13px; font-weight:800; margin-top:4px; }

        .quality { text-align:center; margin:10px 0 12px; padding:10px 14px; border-radius:10px; font-size:12px; font-weight:850; letter-spacing:.5px; }
        .quality.GREAT { background:rgba(74,222,128,.15); border:1px solid rgba(74,222,128,.4); color:#4ade80; }
        .quality.GOOD  { background:rgba(163,230,53,.13); border:1px solid rgba(163,230,53,.35); color:#a3e635; }
        .quality.POOR  { background:rgba(239,68,68,.13); border:1px solid rgba(239,68,68,.35); color:#ff8585; }

        .legend { display:grid; grid-template-columns:1fr 1fr; gap:6px 12px; font-size:10.5px; color:rgba(255,255,255,.6); line-height:1.4; }
        .legend .row { display:flex; align-items:center; gap:6px; }
        .legend .ar { font-weight:800; width:14px; text-align:center; }
      </style>
      <div class="card">
        <div class="head">
          <span class="t">🎣 Fishing Barometer</span>
          <span class="live">Live</span>
        </div>
        <div class="dial"><svg id="svg" viewBox="0 0 360 220" preserveAspectRatio="xMidYMid meet"></svg></div>
        <div class="big">
          <span class="pv" id="pv">—</span><span class="pu">hPa</span>
        </div>
        <div class="trend" id="trend"><span>—</span></div>
        <div class="quality" id="quality">—</div>
        <div class="legend">
          <div class="row"><span class="ar" style="color:#4ade80">↗</span><span>Steigend → Beste Chancen</span></div>
          <div class="row"><span class="ar" style="color:#a3e635">↑</span><span>Schnell steigend → Gut</span></div>
          <div class="row"><span class="ar" style="color:#a3e635">↘</span><span>Fallend → Gut, wird schwächer</span></div>
          <div class="row"><span class="ar" style="color:#a3e635">↓</span><span>Schnell fallend → Beißen jetzt</span></div>
          <div class="row"><span class="ar" style="color:#ff8585">→</span><span>Stabil → Schwach</span></div>
          <div class="row"><span class="ar" style="color:#ff8585">⬇</span><span>Sehr tief (&lt;1005) → Schwach</span></div>
        </div>
      </div>
    `;
  }

  update() {
    if (!this._built || !this._hass) return;
    const root = this.shadowRoot;
    const pSens = this._hass.states[this.config.pressure_sensor];
    const pressure = this._num(pSens?.state);
    const m1h = this._num(pSens?.attributes?.mean_1h);
    const m3h = this._num(pSens?.attributes?.mean_3h);
    const trend = this._trend(pressure, m1h, m3h);

    // Zifferblatt aufbauen
    const svg = root.getElementById("svg");
    const cx = 180, cy = 200, rOuter = 150, rInner = 130, rMid = (rOuter + rInner) / 2;
    // Farbzonen: 980-1010=POOR, 1010-1025=GREAT, 1025-1040=GOOD, 1040-1050=hoch (gelb)
    const zones = [
      { from: 980,  to: 1010, color: "#ef4444", op: 0.65 },  // POOR — rot
      { from: 1010, to: 1025, color: "#4ade80", op: 0.85 },  // GREAT — grün
      { from: 1025, to: 1040, color: "#a3e635", op: 0.75 },  // GOOD — limette
      { from: 1040, to: 1050, color: "#fde047", op: 0.65 },  // zu hoch — gelb
    ];
    let zonesHtml = "";
    for (const z of zones) {
      const a1 = this._pressureToAngle(z.from);
      const a2 = this._pressureToAngle(z.to);
      const d = this._arcPath(cx, cy, rMid, a1, a2);
      zonesHtml += `<path d="${d}" fill="none" stroke="${z.color}" stroke-width="22" stroke-linecap="butt" opacity="${z.op}"/>`;
    }
    // Tick marks alle 5 hPa
    let ticksHtml = "";
    for (let v = 980; v <= 1050; v += 5) {
      const a = this._pressureToAngle(v);
      const [tx1, ty1] = this._polar(cx, cy, rInner - 2, a);
      const [tx2, ty2] = this._polar(cx, cy, rInner - 10, a);
      const isMajor = v % 10 === 0;
      ticksHtml += `<line x1="${tx1}" y1="${ty1}" x2="${tx2}" y2="${ty2}" stroke="rgba(255,255,255,${isMajor?0.85:0.4})" stroke-width="${isMajor?2:1}"/>`;
      if (isMajor) {
        const [lx, ly] = this._polar(cx, cy, rInner - 22, a);
        ticksHtml += `<text x="${lx}" y="${ly+3}" text-anchor="middle" font-size="10" font-weight="700" fill="rgba(255,255,255,.85)" font-family="system-ui">${v}</text>`;
      }
    }
    // Zeiger
    let pointerHtml = "";
    if (pressure != null && !isNaN(pressure)) {
      const a = this._pressureToAngle(pressure);
      const [px, py] = this._polar(cx, cy, rOuter - 8, a);
      pointerHtml = `
        <line x1="${cx}" y1="${cy}" x2="${px}" y2="${py}" stroke="#ff4444" stroke-width="3.5" stroke-linecap="round"/>
        <circle cx="${cx}" cy="${cy}" r="7" fill="#ffd23f" stroke="#aa8800" stroke-width="1.5"/>
      `;
    }

    svg.innerHTML = `${zonesHtml}${ticksHtml}${pointerHtml}`;

    root.getElementById("pv").textContent = pressure != null ? Math.round(pressure) : "—";
    root.getElementById("trend").innerHTML = `<span style="font-size:18px">${trend.arrow}</span> ${trend.label}`;
    const qEl = root.getElementById("quality");
    qEl.textContent = `${trend.quality} · ${trend.advice}`;
    qEl.className = `quality ${trend.quality}`;
  }
}

customElements.define("fishing-barometer-card", FishingBarometerCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "fishing-barometer-card",
  name: "Fishing Barometer Card",
  preview: false,
  description: "Luftdruck im TRAC-Style mit Trend-Interpretation und Fang-Bedingungen",
});
