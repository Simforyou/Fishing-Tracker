
class FishingTrackerCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("hui-entities-card-editor");
  }

  static getStubConfig() {
    return {
      title: "Fishing Tracker",
      default_view: "overview",
      show_sidebar: true
    };
  }

  setConfig(config) {
    this.config = {
      title: "Fishing Tracker",
      default_view: "overview",
      show_sidebar: true,
      ...config
    };
    this.view = this.config.default_view || "overview";
    this.selectedFish = "Zander";
    this.attachShadow({ mode: "open" });
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this.shadowRoot) this.updateLive();
  }

  getCardSize() {
    return 12;
  }

  getFishes() {
    return ["Zander","Hecht","Barsch","Karpfen","Aal","Weißfisch","Brasse","Rotauge","Rotfeder","Schleie"];
  }

  getSpeciesBase(fish) {
    const data = {
      Zander:[22,28,41,55,63,72,88,91,77],
      Hecht:[31,42,62,68,74,70,66,58,39],
      Barsch:[25,35,54,68,76,72,65,55,37],
      Karpfen:[18,24,38,50,58,64,72,79,68],
      Aal:[8,10,16,20,25,39,62,80,91],
      Weißfisch:[35,44,58,70,78,74,68,55,33],
      Brasse:[22,30,46,62,71,68,64,51,29],
      Rotauge:[30,42,55,66,73,70,61,48,28],
      Rotfeder:[28,38,53,67,75,72,59,45,25],
      Schleie:[18,26,41,55,62,70,79,74,52]
    };
    return data[fish] || data.Zander;
  }

  state(id) {
    return this._hass?.states?.[id];
  }

  firstState(ids) {
    for (const id of ids) {
      if (this.state(id)) return this.state(id);
    }
    return null;
  }

  val(entity, fallback="--", suffix="") {
    if (!entity || entity.state === undefined || ["unknown","unavailable",""].includes(entity.state)) return fallback;
    return entity.state + suffix;
  }

  attr(entity, name, fallback="--", suffix="") {
    const value = entity?.attributes?.[name];
    if (value === undefined || value === null || value === "" || value === "unknown" || value === "unavailable") return fallback;
    return value + suffix;
  }

  async quickCatch(caught) {
    if (!this._hass) {
      this.showToast("Home Assistant nicht erreichbar.");
      return;
    }

    const service = caught ? "log_catch" : "log_no_catch";
    const data = {
      fish_type: this.selectedFish || "Zander",
      spot: "Auto Dash",
      bait: "Schnellaktion",
      angler: "Fishing Tracker",
      notes: caught ? "Schnellaktion: Fang" : "Schnellaktion: Kein Fang"
    };

    try {
      await this._hass.callService("fishing_tracker", service, data);
      this.showToast(caught ? "Fang gespeichert." : "Kein Fang gespeichert.");
      this.updateLive();
    } catch (err) {
      console.error(err);
      this.showToast("Aktion fehlgeschlagen. Prüfe Services/Logs.");
    }
  }

  showToast(message) {
    const toast = this.shadowRoot?.getElementById("toast");
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add("show");
    window.clearTimeout(this._toastTimer);
    this._toastTimer = window.setTimeout(() => toast.classList.remove("show"), 2600);
  }


  render() {
    const root = this.shadowRoot;
    root.innerHTML = `
      <style>${this.styles()}</style>
      <ha-card class="ft-card">
        <div class="app">
          ${this.sidebar()}
          <main class="main">
            <header class="top">
              <div>
                <h1>${this.config.title}</h1>
                <p>Native Lovelace Card · v2.7.1 · Premium Fishing Intelligence</p>
              </div>
              <div class="live"><span class="dot"></span> Live<br><small id="clock">--</small></div>
            </header>
            <section id="content"></section><div id="toast" class="toast"></div>
          </main>
        </div>
      </ha-card>
    `;
    this.renderView();
    this.updateLive();
  }

  styles() {
    return `
      :host{display:block}
      .ft-card{overflow:hidden;background:#03070d;color:#fff;border-radius:24px}
      .app{display:grid;grid-template-columns:220px 1fr;min-height:760px;background:
        radial-gradient(circle at 15% 0%,rgba(0,140,255,.18),transparent 32%),
        linear-gradient(145deg,#05101b,#020408);font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
      .sidebar{background:rgba(2,8,15,.72);border-right:1px solid rgba(100,180,255,.12);padding:18px;display:flex;flex-direction:column;gap:14px}
      .brand{display:flex;align-items:center;gap:10px;margin-bottom:8px}
      .brand img{width:46px;height:46px;border-radius:14px;box-shadow:0 0 18px rgba(46,168,255,.35)}
      .brand b{font-size:18px;line-height:1}
      .nav{display:grid;gap:6px}
      .nav button{border:0;background:transparent;color:rgba(255,255,255,.72);text-align:left;padding:12px;border-radius:14px;font-size:14px;cursor:pointer}
      .nav button.active,.nav button:hover{background:rgba(46,168,255,.16);color:white}
      .status{margin-top:auto;border:1px solid rgba(100,180,255,.14);border-radius:16px;padding:12px;background:rgba(255,255,255,.04);font-size:13px}
      .main{padding:18px;min-width:0}
      .top{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:16px}
      h1{margin:0;font-size:32px;line-height:1} p{margin:6px 0 0;color:rgba(255,255,255,.65)}
      .live{border:1px solid rgba(100,180,255,.15);border-radius:18px;background:rgba(255,255,255,.04);padding:12px 18px;min-width:130px}
      .dot{display:inline-block;width:10px;height:10px;background:#62d83e;border-radius:50%;margin-right:6px}
      .grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
      .wide{grid-column:span 2}.full{grid-column:1/-1}
      .panel{border:1px solid rgba(100,180,255,.14);border-radius:22px;padding:16px;background:linear-gradient(145deg,rgba(10,24,38,.9),rgba(4,8,14,.96));box-shadow:0 0 24px rgba(0,0,0,.22)}
      .panel.green{background:radial-gradient(circle at 0% 0%,rgba(0,255,110,.13),transparent 42%),linear-gradient(145deg,rgba(8,22,16,.96),rgba(3,7,5,.98))}
      .panel.gold{background:radial-gradient(circle at 0% 0%,rgba(255,165,40,.13),transparent 42%),linear-gradient(145deg,rgba(20,18,10,.96),rgba(5,5,4,.98))}
      .title{font-size:19px;font-weight:900;margin-bottom:12px;display:flex;gap:8px;align-items:center}
      .big{font-size:56px;font-weight:950;line-height:.9;color:#67d33f}
      .row{display:flex;justify-content:space-between;gap:10px;margin:9px 0;font-size:16px}.value{font-weight:900}.muted{color:rgba(255,255,255,.65)}
      .weather-grid,.stat-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
      .box{border-radius:16px;background:rgba(255,255,255,.045);padding:12px}.box small{color:rgba(255,255,255,.62)}.box div{font-size:18px;font-weight:900;margin-top:4px}
      .rank{display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px solid rgba(255,255,255,.06)}.rank:last-child{border-bottom:0}
.quickActions{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}.quickBtn{border:0;border-radius:22px;padding:22px 12px;color:white;font-size:22px;font-weight:950;cursor:pointer;box-shadow:0 0 22px rgba(0,0,0,.24);transition:.18s transform,.18s filter}.quickBtn small{font-size:13px;opacity:.8}.quickBtn:active{transform:scale(.96)}.quickBtn.catch{background:radial-gradient(circle at 30% 0%,rgba(120,255,170,.25),transparent 40%),linear-gradient(145deg,#07391b,#021108)}.quickBtn.noCatch{background:radial-gradient(circle at 30% 0%,rgba(255,100,100,.25),transparent 40%),linear-gradient(145deg,#3a0909,#130202)}.toast{position:fixed;left:50%;bottom:22px;transform:translateX(-50%) translateY(20px);opacity:0;pointer-events:none;background:rgba(5,12,20,.96);border:1px solid rgba(100,180,255,.25);border-radius:16px;padding:12px 18px;color:white;font-weight:800;box-shadow:0 0 24px rgba(0,0,0,.35);z-index:99;transition:.2s}.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
      .greenText{color:#67d33f}.blueText{color:#2ea8ff}.orangeText{color:#ff9d18}.yellowText{color:#ffd23f}
      .chart{height:260px}.chart svg{width:100%;height:100%}.chartLabel{font-size:12px;fill:rgba(255,255,255,.78)}.axis{stroke:rgba(255,255,255,.12)}.gridline{stroke:rgba(255,255,255,.09);stroke-dasharray:4 5}
      .lineO{fill:none;stroke:#ff9d18;stroke-width:4;stroke-linecap:round;stroke-linejoin:round}.lineB{fill:none;stroke:#2ea8ff;stroke-width:4;stroke-linecap:round;stroke-linejoin:round}.lineG{fill:none;stroke:#67d33f;stroke-width:4;stroke-linecap:round;stroke-linejoin:round}
      .areaO{fill:rgba(255,157,24,.15)}.areaB{fill:rgba(46,168,255,.14)}.areaG{fill:rgba(103,211,63,.14)}
      .dotO{fill:#ff9d18;stroke:white}.dotB{fill:#2ea8ff;stroke:white}.dotG{fill:#67d33f;stroke:white}
      .tabs{display:flex;gap:8px;flex-wrap:wrap}.tabs button,.primary{border:0;border-radius:14px;background:rgba(46,168,255,.14);color:white;padding:10px 14px;font-weight:800;cursor:pointer}.tabs button.active,.primary{background:#145da0}
      .fish-card{display:grid;grid-template-columns:1fr 1fr;gap:14px;align-items:center}.fish-emoji{font-size:92px;text-align:center}
      .spotMap{height:260px;border-radius:18px;background:
        radial-gradient(circle at 28% 65%,rgba(255,120,40,.9),rgba(255,120,40,.14) 14%,transparent 28%),
        radial-gradient(circle at 72% 35%,rgba(80,255,120,.8),rgba(80,255,120,.12) 12%,transparent 25%),
        linear-gradient(135deg,rgba(20,70,95,.95),rgba(3,15,28,.95));position:relative}
      .pin{position:absolute;right:32%;top:28%;font-size:34px;filter:drop-shadow(0 0 8px rgba(103,211,63,.9))}
      table{width:100%;border-collapse:collapse}td,th{padding:10px;border-bottom:1px solid rgba(255,255,255,.07);text-align:left}th{color:rgba(255,255,255,.7)}
      @media(max-width:900px){.app{grid-template-columns:1fr}.sidebar{position:relative;border-right:0;border-bottom:1px solid rgba(100,180,255,.12)}.nav{grid-template-columns:repeat(3,1fr)}.grid{grid-template-columns:1fr}.wide{grid-column:auto}.weather-grid,.stat-grid{grid-template-columns:1fr 1fr}.top{align-items:flex-start}h1{font-size:28px}.big{font-size:50px}.fish-card{grid-template-columns:1fr}}
    `;
  }

  sidebar() {
    const items = [
      ["overview","🏠","Übersicht"],["forecast","📈","Prognosen"],["species","🎯","Zielfische"],
      ["spots","📍","Spots"],["logbook","📘","Fangbuch"],["stats","📊","Statistiken"],
      ["bait","🪱","Köder"],["weather","🌦️","Wetter"],["settings","⚙️","Einstellungen"]
    ];
    return `
      <aside class="sidebar">
        <div class="brand"><img src="/local/fishing_tracker_icon.png" onerror="this.style.display='none'"><b>FISHING<br>TRACKER</b></div>
        <div class="nav">
          ${items.map(i=>`<button data-view="${i[0]}" class="${this.view===i[0]?'active':''}">${i[1]} ${i[2]}</button>`).join("")}
        </div>
        <div class="status"><span class="dot"></span> Live Status<br><span class="muted">Alle Systeme aktiv</span></div>
      </aside>`;
  }

  renderView() {
    const content = this.shadowRoot.getElementById("content");
    if (!content) return;
    const views = {
      overview: this.viewOverview(),
      forecast: this.viewForecast(),
      species: this.viewSpecies(),
      spots: this.viewSpots(),
      logbook: this.viewLogbook(),
      stats: this.viewStats(),
      bait: this.viewBait(),
      weather: this.viewWeather(),
      settings: this.viewSettings()
    };
    content.innerHTML = views[this.view] || views.overview;
    this.shadowRoot.querySelectorAll(".nav button").forEach(btn=>{
      btn.onclick = () => {
        this.view = btn.dataset.view;
        this.render();
      };
    });
    const quickCatchBtn = this.shadowRoot.getElementById("quickCatch");
    const quickNoCatchBtn = this.shadowRoot.getElementById("quickNoCatch");
    if (quickCatchBtn) quickCatchBtn.onclick = () => this.quickCatch(true);
    if (quickNoCatchBtn) quickNoCatchBtn.onclick = () => this.quickCatch(false);

    const select = this.shadowRoot.getElementById("fishSelect");
    if (select) {
      select.value = this.selectedFish;
      select.onchange = () => { this.selectedFish = select.value; this.renderView(); this.updateLive(); };
    }
    this.drawAllCharts();
  }

  viewOverview() {
    return `<div class="grid">
      <div class="panel green"><div class="title">🔥 Angelwetter Index</div><div class="big" id="chance">--%</div><p class="greenText">Sehr gut</p></div>
      <div class="panel"><div class="title">⏰ Beste Zeit heute</div><h2 id="bestTime">18:00 – 21:00</h2><p class="greenText">Aktivität hoch</p><div class="chart" id="miniChart"></div></div>
      <div class="panel gold"><div class="title">🌙 Mondphase</div><h2 id="moon">--</h2><p class="muted">Mondfaktor aktiv</p></div>
      <div class="panel wide"><div class="title">📈 Aktivitätsprognose Heute</div><div class="chart"><svg id="dayChart" viewBox="0 0 900 260" preserveAspectRatio="none"></svg></div></div>
      <div class="panel"><div class="title">🏆 Zielfisch Aktivität</div><div id="rankList"></div></div>
      <div class="panel wide"><div class="title">🗺️ Smart Spot Preview</div><div class="spotMap"><div class="pin">📍</div></div></div>
      <div class="panel"><div class="title">🎯 Zielfisch Prognose</div><div class="fish-card"><div class="fish-emoji">🐟</div><div><h2 id="selectedFish">${this.selectedFish}</h2><div class="big" id="speciesScore">--%</div><p class="greenText">Aktivität</p></div></div></div>
<div class="panel full"><div class="title">✅ Schnellaktion</div><p class="muted">Speichert direkt über Home Assistant Services.</p><div class="quickActions"><button class="quickBtn catch" id="quickCatch">🐟 ✓<br><small>Fang speichern</small></button><button class="quickBtn noCatch" id="quickNoCatch">🐟 ✕<br><small>Kein Fang</small></button></div></div>
    </div>`;
  }

  viewForecast() {
    return `<div class="grid">
      <div class="panel full"><div class="title">📈 Beißprognose – Heute</div><div class="chart"><svg id="dayChart" viewBox="0 0 900 260" preserveAspectRatio="none"></svg></div></div>
      <div class="panel full"><div class="title">📈 Beißprognose – Woche</div><div class="chart"><svg id="weekChart" viewBox="0 0 900 260" preserveAspectRatio="none"></svg></div></div>
      <div class="panel full"><div class="title">🎯 Zielfisch-Prognose</div><select id="fishSelect" class="primary">${this.getFishes().map(f=>`<option>${f}</option>`).join("")}</select><div class="chart"><svg id="speciesChart" viewBox="0 0 900 260" preserveAspectRatio="none"></svg></div></div>
    </div>`;
  }

  viewSpecies() {
    return `<div class="grid">
      <div class="panel wide"><div class="title">🎯 Zielfische</div><div class="tabs">${this.getFishes().slice(0,5).map(f=>`<button class="${f===this.selectedFish?'active':''}" onclick="this.getRootNode().host.selectedFish='${f}';this.getRootNode().host.renderView();">${f}</button>`).join("")}</div><div class="fish-card"><div class="fish-emoji">🐟</div><div><h2>${this.selectedFish}</h2><div class="big" id="speciesScore">--%</div><p>Beste Zeit: <span class="greenText">18:00 – 21:00</span></p><p class="muted">Köder: Gummifisch, Wobbler, Wurm</p></div></div></div>
      <div class="panel"><div class="title">🏆 Ranking</div><div id="rankList"></div></div>
      <div class="panel full"><div class="title">📈 Zielfisch Tageskurve</div><div class="chart"><svg id="speciesChart" viewBox="0 0 900 260" preserveAspectRatio="none"></svg></div></div>
    </div>`;
  }

  viewSpots() {
    return `<div class="grid"><div class="panel wide"><div class="title">📍 Spots</div><div class="spotMap"><div class="pin">📍</div></div></div><div class="panel"><div class="title">🔥 Top Spots</div><div id="spotsList"><div class="rank"><b>Geheimer Bucht</b><span class="greenText">91%</span></div><div class="rank"><b>Alte Kiesgrube</b><span class="greenText">88%</span></div><div class="rank"><b>Steinbruch See</b><span class="yellowText">74%</span></div></div></div></div>`;
  }

  viewLogbook() {
    return `<div class="grid"><div class="panel full"><div class="title">📘 Fangbuch</div><table><thead><tr><th>Fisch</th><th>Spot</th><th>Köder</th><th>Datum</th></tr></thead><tbody id="logRows"><tr><td>Zander</td><td>Kante Nord</td><td>Gummifisch</td><td>Heute</td></tr></tbody></table></div></div>`;
  }

  viewStats() {
    return `<div class="grid"><div class="panel full"><div class="title">📊 Statistiken</div><div class="stat-grid"><div class="box"><small>Gesamtfänge</small><div id="totalCatches">--</div></div><div class="box"><small>Quote</small><div id="rate">--</div></div><div class="box"><small>Top Fisch</small><div>Zander</div></div><div class="box"><small>Top Spot</small><div>Kante</div></div></div></div></div>`;
  }

  viewBait() {
    return `<div class="grid"><div class="panel full"><div class="title">🪱 Köder</div><div class="stat-grid"><div class="box"><small>Gummifisch</small><div class="greenText">Sehr gut</div></div><div class="box"><small>Wobbler</small><div class="greenText">Gut</div></div><div class="box"><small>Spinner</small><div class="yellowText">Mittel</div></div><div class="box"><small>Wurm</small><div class="greenText">Gut</div></div></div></div></div>`;
  }

  viewWeather() {
    return `<div class="grid"><div class="panel full"><div class="title">🌦️ Wetter</div><div class="weather-grid">${["Temperatur","Luftdruck","Wind","Regen","UV","Böen","Mond","Wasser"].map((x,i)=>`<div class="box"><small>${x}</small><div id="w${i}">--</div></div>`).join("")}</div></div></div>`;
  }

  viewSettings() {
    return `<div class="grid"><div class="panel full"><div class="title">⚙️ Einstellungen</div><p class="muted">Konfiguration weiterhin über Home Assistant Integration. Diese Ansicht dient als App-Platzhalter für v2.7.x.</p><button class="primary">Konfiguration öffnen</button></div></div>`;
  }

  drawAllCharts() {
    this.drawChart("dayChart", [28,34,45,62,76,82,91,85,48], "O");
    this.drawChart("weekChart", [76,81,68,84,89,72,77], "B");
    this.drawChart("speciesChart", this.getSpeciesBase(this.selectedFish), "G");
  }

  drawChart(id, points, color) {
    const svg = this.shadowRoot.getElementById(id);
    if (!svg) return;
    const w=900,h=260,pad=36,step=(w-pad*2)/(points.length-1);
    const pts=points.map((v,i)=>[pad+i*step,h-pad-v/100*(h-pad*2)]);
    const line=pts.map((p,i)=>(i?"L":"M")+p[0]+","+p[1]).join(" ");
    const area="M"+pts[0][0]+",224 "+pts.map(p=>"L"+p[0]+","+p[1]).join(" ")+" L"+pts[pts.length-1][0]+",224 Z";
    const labels=points.length===7?["Mo","Di","Mi","Do","Fr","Sa","So"]:["00","03","06","09","12","15","18","21","24"];
    svg.innerHTML=`
      <line x1="36" y1="224" x2="870" y2="224" class="axis"/><line x1="36" y1="36" x2="36" y2="224" class="axis"/>
      ${[0,25,50,75,100].map(v=>`<line x1="36" y1="${224-v/100*188}" x2="870" y2="${224-v/100*188}" class="gridline"/><text x="5" y="${229-v/100*188}" class="chartLabel">${v}%</text>`).join("")}
      <path d="${area}" class="area${color}"/><path d="${line}" class="line${color}"/>
      ${pts.map((p,i)=>`<circle cx="${p[0]}" cy="${p[1]}" r="6" class="dot${color}"/><text x="${p[0]-12}" y="${p[1]-14}" class="chartLabel">${points[i]}%</text>`).join("")}
      ${pts.map((p,i)=>`<text x="${p[0]-14}" y="250" class="chartLabel">${labels[i]}</text>`).join("")}`;
  }

  updateLive() {
    if (!this.shadowRoot) return;
    const clock = this.shadowRoot.getElementById("clock");
    if (clock) clock.textContent = new Date().toLocaleTimeString("de-DE",{hour:"2-digit",minute:"2-digit"})+" Uhr";

    const intel = this.firstState(["sensor.fishing_intelligence"]);
    const ranking = this.firstState(["sensor.fishing_tracker_species_ranking","sensor.fischarten_ranking","sensor.species_ranking"]);
    const weather = this.firstState(["sensor.fishing_tracker_online_weather_status","sensor.online_wetterstatus"]);
    const moon = this.firstState(["sensor.moon_phase","sensor.moon"]);

    const chance = this.shadowRoot.getElementById("chance");
    if (chance) chance.textContent = this.attr(intel, "score", "87", "%");

    const rankList = this.shadowRoot.getElementById("rankList");
    const ranks = ranking?.attributes?.ranking || [
      {fish_type:"Zander",score:91},{fish_type:"Barsch",score:84},{fish_type:"Hecht",score:76},{fish_type:"Karpfen",score:68}
    ];
    if (rankList) rankList.innerHTML = ranks.slice(0,5).map((r,i)=>`<div class="rank"><b>${i+1}. ${r.fish_type}</b><span class="${r.score>=80?'greenText':r.score>=65?'yellowText':'orangeText'}">${r.score}%</span></div>`).join("");

    const speciesScore = this.shadowRoot.getElementById("speciesScore");
    if (speciesScore) speciesScore.textContent = Math.max(...this.getSpeciesBase(this.selectedFish)) + "%";

    const moonEl = this.shadowRoot.getElementById("moon");
    if (moonEl) moonEl.textContent = this.val(moon, "Zunehmend");

    const vals = [
      this.attr(weather,"temperature","18.7","°C"),
      this.attr(weather,"pressure","1015"," hPa"),
      this.attr(weather,"wind_speed","12"," km/h"),
      this.attr(weather,"precipitation","0.0"," mm"),
      this.attr(weather,"uv_index","1"),
      this.attr(weather,"wind_gusts","18"," km/h"),
      this.val(moon,"Zunehmend"),
      "16.3°C"
    ];
    vals.forEach((v,i)=>{ const el=this.shadowRoot.getElementById("w"+i); if(el) el.textContent=v; });
  }
}

customElements.define("fishing-tracker-card", FishingTrackerCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "fishing-tracker-card",
  name: "Fishing Tracker Card",
  description: "Premium Fishing Intelligence Lovelace Card"
});
