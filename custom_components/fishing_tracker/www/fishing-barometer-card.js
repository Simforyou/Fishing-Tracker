// Fishing Barometer Card v1.0.0
// Lovelace Custom Card für Home Assistant
class FishingBarometerCard extends HTMLElement {
  set hass(hass) {
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
    this._hass = hass;
    this.render();
  }

  setConfig(config) {
    this.config = config || {};
  }

  static getConfigElement() { return document.createElement('div'); }

  getCardSize() { return 3; }

  val(entity, fallback = '--') {
    const s = this._hass?.states?.[entity];
    return s ? s.state : fallback;
  }
  attr(entity, attr, fallback = '--') {
    const s = this._hass?.states?.[entity];
    return s?.attributes?.[attr] ?? fallback;
  }

  render() {
    const hass = this._hass;
    if (!hass) return;

    const chance = parseFloat(this.val('sensor.fishing_tracker_bite_chance', '70')) || 70;
    const pressure = parseFloat(this.attr('weather.home', 'pressure', 1015)) || 1015;
    const bestTime = this.val('sensor.fishing_tracker_best_time', '--:--');
    const waterTemp = this.val('sensor.wassertemperatur_gewaesser', '--');
    const sol = hass.states['sensor.solunar_beisszeiten']?.attributes || {};

    // Barometer Bewertung
    const zone = chance >= 80 ? 'GREAT' : chance >= 60 ? 'GOOD' : 'POOR';
    const zoneColor = zone === 'GREAT' ? '#67d33f' : zone === 'GOOD' ? '#ffd23f' : '#ff6b6b';
    const zoneBg = zone === 'GREAT' ? 'rgba(103,211,63,.15)' : zone === 'GOOD' ? 'rgba(255,210,63,.12)' : 'rgba(255,107,107,.12)';

    // Zeiger-Winkel: 0% = -130°, 100% = +130°
    const angle = -130 + (chance / 100) * 260;

    // Begründung
    const trend = pressure > 1015 ? '↗ Steigender Druck' : pressure < 1010 ? '↘ Fallender Druck' : '→ Stabiler Druck';
    const reason = chance >= 80
      ? `${trend} · Optimale Bedingungen`
      : chance >= 60
      ? `${trend} · Gute Bedingungen`
      : `${trend} · Schwierige Bedingungen`;

    this.shadowRoot.innerHTML = `
    <style>
      :host { display: block; font-family: 'DM Sans', system-ui, sans-serif; }
      .card {
        background: linear-gradient(145deg, rgba(8,18,34,.97), rgba(3,7,14,.99));
        border: 1px solid rgba(46,168,255,.18);
        border-radius: 20px;
        padding: 16px;
        color: #fff;
        box-shadow: 0 4px 24px rgba(0,0,0,.4);
      }
      .header { display:flex; align-items:center; gap:10px; margin-bottom:14px }
      .header-icon { font-size:22px }
      .header-title { font-size:14px; font-weight:800; letter-spacing:.05em; color:rgba(255,255,255,.8) }
      .header-sub { font-size:11px; color:rgba(255,255,255,.45); margin-top:2px }

      /* Barometer */
      .baro-wrap { display:flex; flex-direction:column; align-items:center; margin:8px 0 14px }
      .baro-svg { width:200px; height:120px }

      /* Zone Badge */
      .zone-badge {
        display:inline-block;
        border-radius:8px;
        padding:5px 16px;
        font-size:14px;
        font-weight:900;
        letter-spacing:.08em;
        margin-top:8px;
        background:${zoneBg};
        color:${zoneColor};
        border:1px solid ${zoneColor}44;
      }
      .zone-reason { font-size:12px; color:rgba(255,255,255,.5); margin-top:6px; text-align:center }

      /* Stats */
      .stats { display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-top:12px }
      .stat { background:rgba(255,255,255,.05); border-radius:12px; padding:10px; text-align:center }
      .stat-val { font-size:18px; font-weight:900 }
      .stat-label { font-size:10px; color:rgba(255,255,255,.45); font-weight:700; text-transform:uppercase; letter-spacing:.06em; margin-top:3px }

      /* Solunar */
      .sol-row { display:flex; gap:6px; margin-top:10px }
      .sol-box { flex:1; border-radius:10px; padding:8px; text-align:center }
      .sol-main { background:rgba(103,211,63,.08); border:1px solid rgba(103,211,63,.2) }
      .sol-minor { background:rgba(46,168,255,.07); border:1px solid rgba(46,168,255,.15) }
      .sol-time { font-size:16px; font-weight:900; margin:2px 0 }
      .sol-label { font-size:9px; color:rgba(255,255,255,.45); text-transform:uppercase; letter-spacing:.06em }
    </style>

    <div class="card">
      <div class="header">
        <div class="header-icon">🎣</div>
        <div>
          <div class="header-title">FISHING BAROMETER</div>
          <div class="header-sub">Angelwetter-Bewertung · Live</div>
        </div>
      </div>

      <!-- SVG Barometer -->
      <div class="baro-wrap">
        <svg class="baro-svg" viewBox="0 0 200 120">
          <defs>
            <linearGradient id="poorGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stop-color="#ff6b6b" stop-opacity=".7"/>
              <stop offset="100%" stop-color="#ff9d18" stop-opacity=".5"/>
            </linearGradient>
            <linearGradient id="goodGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stop-color="#ffd23f" stop-opacity=".6"/>
              <stop offset="100%" stop-color="#a8e063" stop-opacity=".5"/>
            </linearGradient>
            <linearGradient id="greatGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stop-color="#67d33f" stop-opacity=".7"/>
              <stop offset="100%" stop-color="#2ea8ff" stop-opacity=".5"/>
            </linearGradient>
          </defs>

          <!-- Hintergrund-Bögen -->
          <!-- Zonen exakt: POOR<60%, GOOD 60-80%, GREAT>80% -->
          <path d="M 22 100 A 78 78 0 0 1 124.1 25.8" fill="none" stroke="url(#poorGrad)" stroke-width="13" stroke-linecap="round" opacity=".75"/>
          <path d="M 124.1 25.8 A 78 78 0 0 1 163.1 54.2" fill="none" stroke="url(#goodGrad)" stroke-width="13" stroke-linecap="round" opacity=".75"/>
          <path d="M 163.1 54.2 A 78 78 0 0 1 178 100" fill="none" stroke="url(#greatGrad)" stroke-width="13" stroke-linecap="round" opacity=".75"/>

          <!-- Skalen-Markierungen -->
          ${[0,25,50,75,100].map(v => {
            const a = Math.PI * (1 - v / 100);
            const x1 = 100 + 68 * Math.cos(a), y1 = 100 - 68 * Math.sin(a);
            const x2 = 100 + 78 * Math.cos(a), y2 = 100 - 78 * Math.sin(a);
            return `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="rgba(255,255,255,.3)" stroke-width="1.5"/>`;
          }).join('')}

          <!-- Labels -->
          <text x="9.0" y="104.0" fill="rgba(255,107,107,.8)" font-size="8.5" text-anchor="middle" font-weight="700">POOR</text>
          <text x="100" y="14" fill="rgba(255,210,63,.8)" font-size="8.5" text-anchor="middle" font-weight="700">GOOD</text>
          <text x="191.0" y="104.0" fill="rgba(103,211,63,.8)" font-size="8.5" text-anchor="middle" font-weight="700">GREAT</text>

          <!-- Mittelpunkt -->
          <circle cx="100" cy="100" r="8" fill="#1a2a3a" stroke="rgba(255,255,255,.2)" stroke-width="1.5"/>

          <!-- Zeiger -->
          <line
            x1="100" y1="100"
            x2="${(100 + 65 * Math.cos(angle * Math.PI / 180)).toFixed(1)}"
            y2="${(100 + 65 * Math.sin(angle * Math.PI / 180)).toFixed(1)}"
            stroke="${zoneColor}"
            stroke-width="3"
            stroke-linecap="round"
          />
          <circle cx="100" cy="100" r="5" fill="${zoneColor}"/>

          <!-- Score im Zentrum -->
          <text x="100" y="85" fill="white" font-size="16" font-weight="900" text-anchor="middle">${Math.round(chance)}%</text>
        </svg>

        <div class="zone-badge">${zone}</div>
        <div class="zone-reason">${reason}</div>
      </div>

      <!-- Stats -->
      <div class="stats">
        <div class="stat">
          <div class="stat-val" style="color:#67d33f">${Math.round(chance)}%</div>
          <div class="stat-label">Beißchance</div>
        </div>
        <div class="stat">
          <div class="stat-val" style="color:#2ea8ff; font-size:14px">${bestTime}</div>
          <div class="stat-label">Beste Zeit</div>
        </div>
        <div class="stat">
          <div class="stat-val" style="color:#2ea8ff">${waterTemp}°C</div>
          <div class="stat-label">Wassertemp</div>
        </div>
      </div>

      <!-- Solunar -->
      <div class="sol-row">
        <div class="sol-box sol-main">
          <div class="sol-label">Hauptbeißzeit 1</div>
          <div class="sol-time" style="color:#67d33f">${sol.major1 || '--:--'}</div>
        </div>
        <div class="sol-box sol-main">
          <div class="sol-label">Hauptbeißzeit 2</div>
          <div class="sol-time" style="color:#67d33f">${sol.major2 || '--:--'}</div>
        </div>
        <div class="sol-box sol-minor">
          <div class="sol-label">Nebenzeit</div>
          <div class="sol-time" style="color:#2ea8ff">${sol.minor1 || '--:--'}</div>
        </div>
      </div>
    </div>`;
  }
}

customElements.define('fishing-barometer-card', FishingBarometerCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'fishing-barometer-card',
  name: 'Fishing Barometer',
  description: 'Angelwetter-Barometer mit Beißchance, Solunar-Zeiten und Wassertemperatur',
  preview: true,
});
