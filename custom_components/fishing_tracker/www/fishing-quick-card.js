/**
 * Fishing Tracker – Quick Entry Card
 * Zwei große Buttons für schnelle Fang-/Schneider-Erfassung direkt vom Dashboard.
 *
 * Lovelace-Konfiguration:
 *   type: custom:fishing-quick-card
 *   panel_path: fishing-tracker        # optional, Standard: fishing-tracker
 */
class FishingQuickCard extends HTMLElement {
  setConfig(config) {
    this.config = {
      panel_path: "fishing-tracker",
      ...config,
    };
    this.attachShadow({ mode: "open" });
    this._rendered = false;
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    // Letzte Beißchance der Top-Art anzeigen
    this.updateInfo();
  }

  getCardSize() { return 3; }

  // Schneider direkt über HA-Service loggen
  async _logNoCatch() {
    if (!this._hass) return;
    const btn = this.shadowRoot.getElementById("noCatchBtn");
    if (btn) { btn.style.opacity = "0.6"; btn.querySelector(".lbl").textContent = "Speichere…"; }
    try {
      await this._hass.callService("fishing_tracker", "log_no_catch", {});
      if (btn) {
        btn.querySelector(".lbl").textContent = "✓ Gespeichert";
        btn.style.background = "rgba(63,185,80,.25)";
        setTimeout(() => {
          btn.style.opacity = "1";
          btn.style.background = "";
          btn.querySelector(".lbl").textContent = "Kein Fang";
        }, 2000);
      }
    } catch (e) {
      if (btn) { btn.querySelector(".lbl").textContent = "Fehler"; btn.style.opacity = "1"; }
    }
  }

  // Zum Fang-Formular im Panel navigieren
  _openCatchForm() {
    const path = this.config.panel_path || "fishing-tracker";
    // Panel-URL mit Deep-Link Parameter
    window.location.href = `/${path}?action=catch`;
  }

  updateInfo() {
    if (!this.shadowRoot) return;
    const el = this.shadowRoot.getElementById("info");
    if (!el || !this._hass) return;
    const rank = this._hass.states["sensor.fishing_tracker_species_ranking"];
    if (rank && rank.attributes) {
      const fish = rank.attributes.top_fish || rank.attributes.best_fish;
      const score = rank.attributes.top_score || rank.attributes.best_score;
      if (fish && score != null) {
        el.textContent = `🎯 ${fish} · ${score}% Beißchance jetzt`;
        return;
      }
    }
    const bite = this._hass.states["sensor.fishing_tracker_bite_chance"];
    if (bite) el.textContent = `🎣 Beißchance: ${bite.state}%`;
  }

  render() {
    if (this._rendered) return;
    this._rendered = true;
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        .card {
          background: var(--ha-card-background, var(--card-background-color, #1c1c1e));
          border-radius: var(--ha-card-border-radius, 16px);
          padding: 16px;
          box-shadow: var(--ha-card-box-shadow, none);
          font-family: var(--paper-font-body1_-_font-family, -apple-system, sans-serif);
        }
        .header {
          display: flex; align-items: center; gap: 8px;
          font-size: 15px; font-weight: 800;
          color: var(--primary-text-color, #fff);
          margin-bottom: 4px;
        }
        #info {
          font-size: 12px; color: var(--secondary-text-color, #8b949e);
          margin-bottom: 14px; min-height: 16px;
        }
        .btns { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .qbtn {
          border: none; border-radius: 14px; padding: 20px 12px;
          cursor: pointer; font-family: inherit; transition: transform .1s, opacity .2s;
          display: flex; flex-direction: column; align-items: center; gap: 6px;
        }
        .qbtn:active { transform: scale(0.96); }
        .qbtn .emoji { font-size: 32px; line-height: 1; }
        .qbtn .lbl { font-size: 14px; font-weight: 800; }
        .catch {
          background: linear-gradient(145deg, #0a3d2e, #0d5540);
          color: #4ade80; border: 1px solid rgba(63,185,80,.4);
        }
        .nocatch {
          background: linear-gradient(145deg, #3d1a1a, #552020);
          color: #ff8080; border: 1px solid rgba(255,107,107,.4);
        }
      </style>
      <div class="card">
        <div class="header">🎣 Schnell-Erfassung</div>
        <div id="info">Lade…</div>
        <div class="btns">
          <button class="qbtn catch" id="catchBtn">
            <span class="emoji">🐟</span>
            <span class="lbl">Fang</span>
          </button>
          <button class="qbtn nocatch" id="noCatchBtn">
            <span class="emoji">🚫</span>
            <span class="lbl">Kein Fang</span>
          </button>
        </div>
      </div>
    `;
    this.shadowRoot.getElementById("catchBtn").addEventListener("click", () => this._openCatchForm());
    this.shadowRoot.getElementById("noCatchBtn").addEventListener("click", () => this._logNoCatch());
    this.updateInfo();
  }
}

customElements.define("fishing-quick-card", FishingQuickCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "fishing-quick-card",
  name: "Fishing Tracker – Schnell-Erfassung",
  description: "Zwei Buttons für schnelle Fang-/Schneider-Erfassung",
});
