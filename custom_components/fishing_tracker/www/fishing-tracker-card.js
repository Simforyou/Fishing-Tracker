
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
      /* ── OVERVIEW ──────────────────────────────────────────────────── */
      .ov-grid{display:flex;flex-direction:column;gap:14px}
      .ov-section-title{font-size:11px;font-weight:800;color:rgba(255,255,255,.4);letter-spacing:.12em;text-transform:uppercase;margin-bottom:10px}
      .kpi-row{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:12px}
      .kpi-card{background:linear-gradient(145deg,rgba(10,24,38,.9),rgba(4,8,14,.96));border:1px solid rgba(100,180,255,.13);border-radius:18px;padding:14px}
      .kpi-main{border-color:rgba(103,211,63,.25);background:radial-gradient(circle at 0 0,rgba(103,211,63,.12),transparent 50%),linear-gradient(145deg,rgba(8,22,16,.96),rgba(3,7,5,.98))}
      .kpi-label{font-size:11px;color:rgba(255,255,255,.5);margin-bottom:6px}
      .kpi-big{font-size:52px;font-weight:950;line-height:.9;margin:4px 0}
      .kpi-mid{font-size:22px;font-weight:900;margin:6px 0}
      .kpi-sub{font-size:11px;color:rgba(255,255,255,.45);margin-top:4px;line-height:1.4}
      .kpi-tag{display:inline-block;border-radius:6px;padding:3px 10px;font-size:12px;font-weight:800;margin-top:6px}
      .ov-row2{display:grid;grid-template-columns:1fr 200px;gap:12px;background:linear-gradient(145deg,rgba(10,24,38,.9),rgba(4,8,14,.96));border:1px solid rgba(100,180,255,.13);border-radius:18px;padding:14px}
      .ov-chart-box{min-width:0}
      .chart-new{height:160px}.chart-new svg{width:100%;height:100%}
      .ov-topzeiten{border-left:1px solid rgba(255,255,255,.07);padding-left:14px}
      .tz-row{display:flex;align-items:center;gap:8px;margin-bottom:7px}
      .tz-time{font-size:12px;font-weight:700;width:42px;flex-shrink:0}
      .tz-bar-wrap{flex:1;height:6px;background:rgba(255,255,255,.08);border-radius:3px;overflow:hidden}
      .tz-bar{height:100%;border-radius:3px;background:linear-gradient(to right,#2ea8ff,#67d33f)}
      .tz-val{font-size:12px;font-weight:800;width:36px;text-align:right;flex-shrink:0}
      .ov-row3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}
      .ov-spot-preview,.ov-fish-prog,.ov-last-catches{background:linear-gradient(145deg,rgba(10,24,38,.9),rgba(4,8,14,.96));border:1px solid rgba(100,180,255,.13);border-radius:18px;padding:14px}
      .spotMap{height:120px;border-radius:12px;background:radial-gradient(circle at 28% 65%,rgba(255,120,40,.9),rgba(255,120,40,.14) 14%,transparent 28%),radial-gradient(circle at 72% 35%,rgba(80,255,120,.8),rgba(80,255,120,.12) 12%,transparent 25%),linear-gradient(135deg,rgba(20,70,95,.95),rgba(3,15,28,.95));position:relative;margin-bottom:10px}
      .spot-chips{display:flex;gap:6px;flex-wrap:wrap}
      .spot-chip{font-size:11px;padding:4px 10px;border-radius:8px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);cursor:pointer}
      .spot-chip.active{background:rgba(46,168,255,.15);border-color:#2ea8ff}
      .fp-row{display:flex;align-items:center;gap:8px;margin-bottom:8px}
      .fp-fish{font-size:12px;font-weight:700;width:60px;flex-shrink:0}
      .fp-bar-wrap{flex:1;height:7px;background:rgba(255,255,255,.08);border-radius:4px;overflow:hidden}
      .fp-bar{height:100%;border-radius:4px;transition:.4s}
      .fp-score{font-size:12px;font-weight:800;width:32px;text-align:right;flex-shrink:0}
      .fp-level{font-size:11px;width:60px;text-align:right;flex-shrink:0}
      .lc-row{display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.05)}
      .lc-row:last-child{border-bottom:0}
      .lc-fish-icon{font-size:22px;flex-shrink:0}
      .lc-name{font-size:13px;font-weight:800}
      .lc-detail{font-size:12px;color:rgba(255,255,255,.7);margin-top:2px}
      .lc-spot{font-size:11px;color:rgba(255,255,255,.45);margin-top:1px}
      .ov-row4{display:flex;align-items:center;gap:14px;background:linear-gradient(145deg,rgba(10,24,38,.9),rgba(4,8,14,.96));border:1px solid rgba(100,180,255,.13);border-radius:18px;padding:14px}
      .live-status-box{display:flex;align-items:center;flex:1;font-size:13px}
      .quick-row{display:flex;gap:10px}

      /* ── FORECAST ──────────────────────────────────────────────────── */
      .fc-grid{display:flex;flex-direction:column;gap:14px}
      .fc-tabs{display:flex;gap:8px;margin-bottom:2px}
      .fc-tab{border:0;background:rgba(255,255,255,.07);color:rgba(255,255,255,.6);border-radius:10px;padding:8px 16px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;transition:.15s}
      .fc-tab.active{background:rgba(46,168,255,.2);color:#2ea8ff}
      .fc-chart-box{background:linear-gradient(145deg,rgba(10,24,38,.9),rgba(4,8,14,.96));border:1px solid rgba(100,180,255,.13);border-radius:18px;padding:14px}
      .week-labels{display:flex;justify-content:space-around;margin-top:10px}
      .wl-item{text-align:center}
      .wl-day{font-size:10px;color:rgba(255,255,255,.45)}
      .wl-val{font-size:14px;font-weight:900;margin-top:3px}
      .wl-best{background:rgba(103,211,63,.1);border-radius:8px;padding:4px 6px}
      .fc-factors{background:linear-gradient(145deg,rgba(10,24,38,.9),rgba(4,8,14,.96));border:1px solid rgba(100,180,255,.13);border-radius:18px;padding:14px}
      .factor-grid{display:flex;flex-direction:column;gap:10px}
      .factor-card{display:flex;align-items:center;gap:10px}
      .factor-icon{font-size:18px;width:26px;flex-shrink:0;text-align:center}
      .factor-label{font-size:13px;font-weight:700;width:100px;flex-shrink:0}
      .factor-bar-wrap{flex:1;height:8px;background:rgba(255,255,255,.08);border-radius:4px;overflow:hidden}
      .factor-bar{height:100%;border-radius:4px}
      .factor-val{font-size:13px;font-weight:800;width:36px;text-align:right}
      .fc-detail{background:linear-gradient(145deg,rgba(10,24,38,.9),rgba(4,8,14,.96));border:1px solid rgba(100,180,255,.13);border-radius:18px;padding:14px}
      .fc-detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
      .fc-wide{grid-column:1/-1}
      .fc-dlabel{font-size:11px;color:rgba(255,255,255,.45);margin-bottom:4px}
      .fc-dval{font-size:18px;font-weight:900}
      .fc-dval-sm{font-size:13px;line-height:1.5}
      .sol-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:8px}
      .sol-card{border-radius:12px;padding:10px;text-align:center}
      .sol-main{background:rgba(103,211,63,.1);border:1px solid rgba(103,211,63,.22)}
      .sol-minor{background:rgba(46,168,255,.08);border:1px solid rgba(46,168,255,.18)}
      .sol-lbl{font-size:10px;color:rgba(255,255,255,.45);text-transform:uppercase;letter-spacing:.06em}
      .sol-time{font-size:20px;font-weight:900;margin:4px 0}
      .sol-sub{font-size:10px;color:rgba(255,255,255,.4)}

      /* ── STATS ─────────────────────────────────────────────────────── */
      .st-grid{display:flex;flex-direction:column;gap:14px}
      .st-kpi-row{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
      .st-kpi{background:linear-gradient(145deg,rgba(10,24,38,.9),rgba(4,8,14,.96));border:1px solid rgba(100,180,255,.13);border-radius:18px;padding:16px}
      .st-kpi-val{font-size:28px;font-weight:950;color:#fff;margin-bottom:4px}
      .st-kpi-label{font-size:10px;font-weight:800;color:rgba(255,255,255,.4);text-transform:uppercase;letter-spacing:.08em}
      .st-kpi-delta{font-size:12px;font-weight:700;margin-top:4px}
      .st-chart-box{background:linear-gradient(145deg,rgba(10,24,38,.9),rgba(4,8,14,.96));border:1px solid rgba(100,180,255,.13);border-radius:18px;padding:14px;grid-column:span 2}
      .bar-chart{display:flex;align-items:flex-end;gap:6px;height:120px;padding-bottom:20px;position:relative}
      .bc-col{flex:1;display:flex;flex-direction:column;align-items:center;height:100%}
      .bc-bar-wrap{flex:1;width:100%;display:flex;align-items:flex-end}
      .bc-bar{width:100%;border-radius:4px 4px 0 0;position:relative;min-height:4px;transition:.4s}
      .bc-val{position:absolute;top:-18px;left:50%;transform:translateX(-50%);font-size:9px;font-weight:800;white-space:nowrap}
      .bc-label{font-size:10px;color:rgba(255,255,255,.45);margin-top:6px}
      .st-donut-box{background:linear-gradient(145deg,rgba(10,24,38,.9),rgba(4,8,14,.96));border:1px solid rgba(100,180,255,.13);border-radius:18px;padding:14px}
      .st-two-col{display:grid;grid-template-columns:1fr 1fr;gap:12px}
      .donut-legend{display:flex;align-items:center;font-size:12px;margin-bottom:6px}
      .donut-legend b{margin-left:auto}

      /* ── WEATHER ───────────────────────────────────────────────────── */
      .wt-grid{display:flex;flex-direction:column;gap:14px}
      .wt-current{display:grid;grid-template-columns:auto 1fr 1fr;gap:14px;background:linear-gradient(145deg,rgba(10,24,38,.9),rgba(4,8,14,.96));border:1px solid rgba(100,180,255,.13);border-radius:18px;padding:16px;align-items:start}
      .wt-main{text-align:center;padding-right:14px;border-right:1px solid rgba(255,255,255,.07)}
      .wt-icon{font-size:52px;margin-bottom:8px}
      .wt-temp{font-size:38px;font-weight:950;color:#2ea8ff}
      .wt-cond{font-size:13px;margin-top:4px}
      .wt-details{display:grid;gap:6px;padding:0 14px}
      .wt-detail-row{display:flex;justify-content:space-between;font-size:13px;padding:4px 0;border-bottom:1px solid rgba(255,255,255,.04)}
      .wt-detail-row:last-child{border-bottom:0}
      .wt-impact{}
      .wt-big-val{font-size:32px;font-weight:950;color:#67d33f;margin-bottom:10px}
      .wi-row{display:flex;align-items:center;gap:8px;margin-bottom:8px}
      .wi-label{font-size:12px;width:100px;flex-shrink:0}
      .wi-bar-wrap{flex:1;height:7px;background:rgba(255,255,255,.08);border-radius:4px;overflow:hidden}
      .wi-bar{height:100%;border-radius:4px}
      .wi-val{font-size:12px;font-weight:800;width:32px;text-align:right}
      .wt-forecast{background:linear-gradient(145deg,rgba(10,24,38,.9),rgba(4,8,14,.96));border:1px solid rgba(100,180,255,.13);border-radius:18px;padding:14px}
      .wt-fc-row{display:flex;justify-content:space-around}
      .wt-fc-day{text-align:center}
      .wt-fc-d{font-size:10px;color:rgba(255,255,255,.45);margin-bottom:6px}
      .wt-fc-icon{font-size:22px;margin-bottom:6px}
      .wt-fc-hi{font-size:15px;font-weight:800}
      .wt-fc-lo{font-size:12px;margin-top:2px}

      /* ── LOGBOOK ───────────────────────────────────────────────────── */
      .lb-grid{display:flex;flex-direction:column;gap:12px}
      .lb-filters{display:flex;gap:10px;align-items:center}
      .lb-select{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);border-radius:10px;color:#fff;padding:8px 12px;font-size:13px;font-family:inherit;cursor:pointer}
      .lb-add-btn{margin-left:auto;border:0;border-radius:10px;background:#145da0;color:#fff;padding:9px 16px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit}
      .lb-layout{display:grid;grid-template-columns:280px 1fr;gap:12px}
      .lb-list{background:linear-gradient(145deg,rgba(10,24,38,.9),rgba(4,8,14,.96));border:1px solid rgba(100,180,255,.13);border-radius:18px;overflow:hidden}
      .lb-entry{display:flex;align-items:center;gap:10px;padding:12px 14px;border-bottom:1px solid rgba(255,255,255,.05);cursor:pointer;transition:.15s}
      .lb-entry:last-child{border-bottom:0}
      .lb-entry:hover,.lb-entry-active{background:rgba(46,168,255,.1)}
      .lb-entry-icon{font-size:22px;flex-shrink:0}
      .lb-entry-fish{font-size:14px;font-weight:800}
      .lb-entry-size{font-size:12px;color:rgba(255,255,255,.7);margin-top:2px}
      .lb-entry-spot{font-size:11px;margin-top:2px}
      .lb-entry-bait{font-size:11px;margin-left:auto;flex-shrink:0}
      .lb-detail{background:linear-gradient(145deg,rgba(10,24,38,.9),rgba(4,8,14,.96));border:1px solid rgba(100,180,255,.13);border-radius:18px;padding:16px;display:flex;flex-direction:column}
      .lb-detail-placeholder{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:40px;color:rgba(255,255,255,.4)}

      /* ── SPOTS ─────────────────────────────────────────────────────── */
      .sp-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
      .sp-map-col,.sp-list-col{background:linear-gradient(145deg,rgba(10,24,38,.9),rgba(4,8,14,.96));border:1px solid rgba(100,180,255,.13);border-radius:18px;padding:14px}
      .sp-detail{margin-top:12px;padding-top:12px;border-top:1px solid rgba(255,255,255,.07)}
      .sp-detail-name{font-size:15px;font-weight:900;margin-bottom:4px}
      .sp-detail-score{font-size:20px;font-weight:950;margin-bottom:10px}
      .sp-detail-row{display:flex;justify-content:space-between;font-size:13px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.05)}
      .sp-detail-btn{margin-top:12px;border:1px solid rgba(46,168,255,.3);background:rgba(46,168,255,.12);color:#2ea8ff;border-radius:10px;padding:9px 18px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;width:100%}
      .sp-row{display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.05)}
      .sp-row:last-child{border-bottom:0}
      .sp-row-icon{font-size:18px;flex-shrink:0}
      .sp-row-info{flex:1;min-width:0}
      .sp-row-name{font-size:13px;font-weight:800}
      .sp-row-fishes{font-size:11px;margin-top:2px}
      .sp-row-score{font-size:16px;font-weight:900;flex-shrink:0}
      .sp-row-label{font-size:11px;font-weight:700;flex-shrink:0;width:52px;text-align:right}

      /* ── SETTINGS ──────────────────────────────────────────────────── */
      .set-grid{display:flex;flex-direction:column;gap:14px}
      .set-layout{background:linear-gradient(145deg,rgba(10,24,38,.9),rgba(4,8,14,.96));border:1px solid rgba(100,180,255,.13);border-radius:18px;padding:18px}
      .set-row{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.05);font-size:14px}
      .set-code{background:rgba(255,255,255,.07);border-radius:6px;padding:3px 8px;font-size:12px;color:#2ea8ff;font-family:monospace}
      .set-toggle-row{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.05);font-size:14px}
      .set-toggle{width:42px;height:24px;border-radius:12px;background:rgba(255,255,255,.12);display:flex;align-items:center;justify-content:flex-end;padding:3px;font-size:16px;transition:.2s}
      .set-toggle.on{background:#145da0;justify-content:flex-end}

      /* ── STATS 2-col layout ────────────────────────────────────────── */
      .st-bottom{display:grid;grid-template-columns:1fr 220px;gap:12px}

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
    // Angelwetter Index: neuer allgemeiner Sensor hat Priorität
    const awIdx = this.firstState(['sensor.fishing_tracker_angelwetter_index']);
    const chance = awIdx ? (awIdx.state + '%') : this.val(this.firstState(['sensor.fishing_tracker_bite_chance']),'–','%');
    const awLevel = awIdx?.attributes?.level || '';
    const bestTime = this.val(this.firstState(['sensor.fishing_tracker_best_time','sensor.beste_angelzeit']),'–');
    // Mond: verschiedene Entity-Namen probieren
    const moonState = this.firstState(['sensor.moon','sensor.moon_phase','sensor.mondphase']);
    const moon = moonState ? moonState.state : '–';
    const waterTemp = this.val(this.firstState(['sensor.wassertemperatur_gewaesser','sensor.water_temp']),'–','°C');
    // Wetter: Haftenkamp-Station hat Priorität über weather.home
    const hkTemp  = this.firstState(['sensor.haftenkamp_temperatur']);
    const hkWind  = this.firstState(['sensor.haftenkamp_windgeschwindigkeit']);
    const hkPress = this.firstState(['sensor.haftenkamp_druck']);
    const hkCloud = this.firstState(['sensor.haftenkamp_bewolkungsgrad']);
    const hkRain  = this.firstState(['sensor.haftenkamp_niederschlag']);
    const hkBear  = this.firstState(['sensor.haftenkamp_windrichtung']);
    const wa = this.firstState(['weather.home'])?.attributes || {};
    const airTemp  = hkTemp  ? hkTemp.state  + '°C' : (wa.temperature  || '–') + '°C';
    const wind     = hkWind  ? hkWind.state  + ' km/h' : (wa.wind_speed  || '–') + ' km/h';
    const pressure = hkPress ? hkPress.state + ' hPa' : (wa.pressure    || '–') + ' hPa';
    const cloud    = hkCloud ? Math.round(hkCloud.state) + '%' : (wa.cloud_coverage || '–') + '%';
    const rain     = hkRain  ? hkRain.state  + ' mm' : '–';
    // Windrichtung
    const bearDeg  = hkBear ? parseFloat(hkBear.state) : (wa.wind_bearing || 0);
    const dirs = ['N','NO','O','SO','S','SW','W','NW'];
    const windDir = dirs[Math.round(bearDeg / 45) % 8];
    const solunarMaj = this.attr(this.firstState(['sensor.solunar_beisszeiten']),'major1','–');
    const solunarMin = this.attr(this.firstState(['sensor.solunar_beisszeiten']),'minor1','–');
    const ranking = this.firstState(['sensor.fishing_tracker_species_ranking','sensor.fischarten_ranking']);
    const ranks = ranking?.attributes?.ranking || [{fish_type:'Zander',score:91},{fish_type:'Barsch',score:84},{fish_type:'Hecht',score:76},{fish_type:'Karpfen',score:68}];
    const top4 = ranks.slice(0,4);
    const scoreColor = s => s>=80?'#67d33f':s>=60?'#ffd23f':'#ff9d18';
    const intScore = parseInt(chance)||87;
    const scoreLevel = intScore>=85?'Sehr gut':intScore>=70?'Gut':intScore>=50?'Mittel':'Gering';
    const lastCatches = [
      {fish:'Zander',size:'68 cm',weight:'3.2 kg',spot:'Geheim.Bucht',bait:'Gummifisch'},
      {fish:'Barsch',size:'38 cm',weight:'0.6 kg',spot:'Alte Kiesgr.',bait:'Spinner'},
      {fish:'Hecht',size:'71 cm',weight:'4.1 kg',spot:'Geheim.Bucht',bait:'Wobbler'},
    ];
    const topTimes = [{h:'18:00',v:91},{h:'19:00',v:88},{h:'20:00',v:84},{h:'07:00',v:79},{h:'08:00',v:74},{h:'06:00',v:68}];
    return `
    <div class="ov-grid">
      <!-- Row 1: KPI Cards -->
      <div class="kpi-row">
        <div class="kpi-card kpi-main">
          <div class="kpi-label">Dein Angelwetter Index ist</div>
          <div class="kpi-big" style="color:#67d33f">${chance}</div>
          <div class="kpi-tag" style="background:rgba(103,211,63,.18);color:#67d33f">${scoreLevel}</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Beste Zeit heute</div>
          <div class="kpi-mid">${bestTime}</div>
          <div class="kpi-sub">91% Aktivität</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Aktuelles Wetter</div>
          <div class="kpi-mid" style="color:#2ea8ff">${airTemp}</div>
          <div class="kpi-sub">Wind ${wind} km/h · Luftdruck ${pressure} hPa · Bewölkt</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Mondphase</div>
          <div class="kpi-mid">🌔 ${moon}</div>
          <div class="kpi-sub">${parseInt(intScore)}% Selektion</div>
        </div>
      </div>

      <!-- Row 2: Chart + Top Zeiten -->
      <div class="ov-row2">
        <div class="ov-chart-box">
          <div class="ov-section-title">AKTIVITÄTSPROGNOSE HEUTE</div>
          <div class="chart-new"><svg id="dayChart" viewBox="0 0 900 200" preserveAspectRatio="none" style="width:100%;height:100%"></svg></div>
        </div>
        <div class="ov-topzeiten">
          <div class="ov-section-title">TOP ZEITEN</div>
          ${topTimes.map(t=>`<div class="tz-row"><span class="tz-time">${t.h}</span><div class="tz-bar-wrap"><div class="tz-bar" style="width:${t.v}%"></div></div><span class="tz-val" style="color:${scoreColor(t.v)}">${t.v}%</span></div>`).join('')}
        </div>
      </div>

      <!-- Row 3: Spot Preview + Zielfisch-Prognose + Letzte Fänge -->
      <div class="ov-row3">
        <div class="ov-spot-preview">
          <div class="ov-section-title">SMART SPOT PREVIEW</div>
          <div class="spotMap"><div class="pin">📍</div></div>
          <div class="spot-chips">
            <div class="spot-chip active">Geheimer Bucht <span class="greenText">91%</span></div>
            <div class="spot-chip">Alte Kiesgrube <span class="yellowText">88%</span></div>
          </div>
        </div>
        <div class="ov-fish-prog">
          <div class="ov-section-title">ZIELFISCHPROGNOSE</div>
          ${top4.map(r=>`<div class="fp-row"><span class="fp-fish">${r.fish_type||r.name||'?'}</span><div class="fp-bar-wrap"><div class="fp-bar" style="width:${r.score}%;background:${scoreColor(r.score)}"></div></div><span class="fp-score" style="color:${scoreColor(r.score)}">${r.score}%</span><span class="fp-level" style="color:${scoreColor(r.score)}">${r.score>=80?'Sehr hoch':r.score>=65?'Hoch':'Mittel'}</span></div>`).join('')}
        </div>
        <div class="ov-last-catches">
          <div class="ov-section-title">LETZTE FÄNGE</div>
          ${lastCatches.map(c=>`<div class="lc-row"><div class="lc-fish-icon">${{Zander:'🟡',Barsch:'🔴',Hecht:'🟢',Karpfen:'🟤'}[c.fish]||'🐟'}</div><div class="lc-info"><div class="lc-name">${c.fish}</div><div class="lc-detail">${c.size} · ${c.weight}</div><div class="lc-spot">${c.spot} · ${c.bait}</div></div></div>`).join('')}
        </div>
      </div>

      <!-- Row 4: Live Status + Schnellaktion -->
      <div class="ov-row4">
        <div class="live-status-box">
          <span class="dot"></span> <b>LIVE STATUS</b>
          <span class="muted" style="margin-left:8px">Alle Systeme aktiv</span>
          <span class="muted" style="margin-left:16px;font-size:12px" id="clock">--:-- Uhr</span>
        </div>
        <div class="quick-row">
          <button class="quickBtn catch" id="quickCatch">🐟 ✓<small>Fang speichern</small></button>
          <button class="quickBtn noCatch" id="quickNoCatch">🐟 ✕<small>Kein Fang</small></button>
        </div>
      </div>
    </div>`;
  }

  viewForecast() {
    const ranking = this.firstState(['sensor.fishing_tracker_species_ranking']);
    const ranks = ranking?.attributes?.ranking || [];
    const solunar = this.firstState(['sensor.solunar_beisszeiten']);
    const sol = solunar?.attributes || {};
    const scoreColor = s => parseInt(s)>=80?'#67d33f':parseInt(s)>=60?'#ffd23f':'#ff9d18';
    const factors = [
      {label:'Wetter',val:87,icon:'🌦️'},
      {label:'Mondphase',val:91,icon:'🌙'},
      {label:'Luftdruck',val:78,icon:'📊'},
      {label:'Wind',val:68,icon:'💨'},
      {label:'Wassertemp.',val:84,icon:'💧'},
    ];
    const weekDays = [
      {d:'Fr 23.05',v:87},{d:'Sa 24.05',v:91},{d:'So 25.05',v:68},{d:'Mo 26.05',v:85},{d:'Di 27.05',v:83},{d:'Mi 28.05',v:72},{d:'Do 29.05',v:71}
    ];
    const topDay = weekDays.reduce((a,b)=>a.v>b.v?a:b);
    return `
    <div class="fc-grid">
      <!-- Tabs -->
      <div class="fc-tabs">
        <button class="fc-tab active">Übersicht</button>
        <button class="fc-tab">24 Stunden</button>
        <button class="fc-tab">7 Tage</button>
        <button class="fc-tab">14 Tage</button>
      </div>

      <!-- 7-Tage Chart -->
      <div class="fc-chart-box">
        <div class="ov-section-title">AKTIVITÄTSPROGNOSE – 7 TAGE</div>
        <div class="chart-new" style="height:180px"><svg id="weekChart" viewBox="0 0 900 180" preserveAspectRatio="none" style="width:100%;height:100%"></svg></div>
        <div class="week-labels">
          ${weekDays.map(w=>`<div class="wl-item ${w.d===topDay.d?'wl-best':''}"><div class="wl-day">${w.d}</div><div class="wl-val" style="color:${scoreColor(w.v)}">${w.v}%</div></div>`).join('')}
        </div>
      </div>

      <!-- Einflussfaktoren -->
      <div class="fc-factors">
        <div class="ov-section-title">EINFLUSSFAKTOREN</div>
        <div class="factor-grid">
          ${factors.map(f=>`<div class="factor-card"><div class="factor-icon">${f.icon}</div><div class="factor-label">${f.label}</div><div class="factor-bar-wrap"><div class="factor-bar" style="width:${f.val}%;background:${scoreColor(f.val)}"></div></div><div class="factor-val" style="color:${scoreColor(f.val)}">${f.val}%</div></div>`).join('')}
        </div>
      </div>

      <!-- Detail Box -->
      <div class="fc-detail">
        <div class="ov-section-title">DETAILS FÜR ${new Date().toLocaleDateString('de-DE',{weekday:'long',day:'2-digit',month:'2-digit',year:'numeric'}).toUpperCase()}</div>
        <div class="fc-detail-grid">
          <div><div class="fc-dlabel">Beste Zeit</div><div class="fc-dval">${this.val(this.firstState(['sensor.fishing_tracker_best_time']),'18:00 – 21:00')}</div></div>
          <div><div class="fc-dlabel">Aktivität</div><div class="fc-dval greenText">91%</div></div>
          <div class="fc-wide"><div class="fc-dlabel">Begründung</div><div class="fc-dval-sm muted">Stabiler Hochdruck, zunehmender Mond und angenehme Wassertemperaturen sorgen für sehr hohe Aktivität.</div></div>
        </div>
        <!-- Solunar -->
        <div class="ov-section-title" style="margin-top:14px">SOLUNAR BEISSZEITEN</div>
        <div class="sol-grid">
          <div class="sol-card sol-main"><div class="sol-lbl">Hauptzeit 1</div><div class="sol-time greenText">${sol.major1||'06:18'}</div><div class="sol-sub">~2h Fenster</div></div>
          <div class="sol-card sol-main"><div class="sol-lbl">Hauptzeit 2</div><div class="sol-time greenText">${sol.major2||'18:42'}</div><div class="sol-sub">~2h Fenster</div></div>
          <div class="sol-card sol-minor"><div class="sol-lbl">Nebenzeit 1</div><div class="sol-time blueText">${sol.minor1||'12:28'}</div><div class="sol-sub">~1h Fenster</div></div>
          <div class="sol-card sol-minor"><div class="sol-lbl">Nebenzeit 2</div><div class="sol-time blueText">${sol.minor2||'00:52'}</div><div class="sol-sub">~1h Fenster</div></div>
        </div>
      </div>
    </div>`;
  }

  viewStats() {
    const totalCatches = this.val(this.firstState(['sensor.fishing_tracker_stats']),'120');
    const stats = this.firstState(['sensor.fishing_tracker_stats']);
    const a = stats?.attributes || {};
    const byFish = [
      {f:'Zander',n:45,pct:37,color:'#2ea8ff'},
      {f:'Barsch',n:38,pct:32,color:'#67d33f'},
      {f:'Hecht',n:22,pct:18,color:'#ff9d18'},
      {f:'Karpfen',n:15,pct:13,color:'#ffd23f'},
    ];
    const byMonth = [
      {m:'Jan',v:2},{m:'Feb',v:3},{m:'Mär',v:8},{m:'Apr',v:14},{m:'Mai',v:22},{m:'Jun',v:18},
      {m:'Jul',v:12},{m:'Aug',v:15},{m:'Sep',v:28},{m:'Okt',v:35},{m:'Nov',v:24},{m:'Dez',v:8},
    ];
    const maxM = Math.max(...byMonth.map(b=>b.v));
    return `
    <div class="st-grid">
      <!-- KPI Row -->
      <div class="st-kpi-row">
        <div class="st-kpi"><div class="st-kpi-val">120</div><div class="st-kpi-label">GESAMTFÄNGE</div><div class="st-kpi-delta greenText">+23% vs. 2024</div></div>
        <div class="st-kpi"><div class="st-kpi-val">45.7 kg</div><div class="st-kpi-label">GESAMTGEWICHT</div><div class="st-kpi-delta greenText">+18% vs. 2024</div></div>
        <div class="st-kpi"><div class="st-kpi-val">0.38 kg</div><div class="st-kpi-label">DURCHSCHNITT</div><div class="st-kpi-delta greenText">+12% vs. 2024</div></div>
        <div class="st-kpi"><div class="st-kpi-val">28</div><div class="st-kpi-label">ANGELTAGE</div><div class="st-kpi-delta greenText">+8% vs. 2024</div></div>
      </div>

      <!-- Tabs -->
      <div class="fc-tabs"><button class="fc-tab active">Übersicht</button><button class="fc-tab">Fische</button><button class="fc-tab">Spots</button><button class="fc-tab">Köder</button><button class="fc-tab">Zeiträume</button></div>

      <!-- Balkendiagramm Monat -->
      <div class="st-chart-box">
        <div class="ov-section-title">FÄNGE PRO MONAT</div>
        <div class="bar-chart">
          ${byMonth.map(b=>`<div class="bc-col"><div class="bc-bar-wrap"><div class="bc-bar" style="height:${Math.round(b.v/maxM*100)}%;background:linear-gradient(to top,#2ea8ff,#67d33f)"><span class="bc-val">${b.v}</span></div></div><div class="bc-label">${b.m}</div></div>`).join('')}
        </div>
      </div>

      <!-- Donut -->
      <div class="st-donut-box">
        <div class="ov-section-title">FÄNGE NACH ART</div>
        <svg viewBox="0 0 120 120" style="width:120px;height:120px;display:block;margin:0 auto 12px">
          ${(() => {
            let off = -25; const r=42,cx=60,cy=60,circ=2*Math.PI*r;
            return byFish.map(f=>{
              const dash = f.pct/100*circ;
              const el = `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${f.color}" stroke-width="16" stroke-dasharray="${dash} ${circ}" stroke-dashoffset="${-off/100*circ}" style="transform-origin:center;transform:rotate(-90deg)"/>`;
              off += f.pct; return el;
            }).join('');
          })()}
          <text x="60" y="56" text-anchor="middle" fill="white" font-size="14" font-weight="900">120</text>
          <text x="60" y="70" text-anchor="middle" fill="rgba(255,255,255,.5)" font-size="8">Fänge</text>
        </svg>
        ${byFish.map(f=>`<div class="donut-legend"><span style="display:inline-block;width:10px;height:10px;border-radius:3px;background:${f.color};margin-right:7px"></span>${f.f} <b style="margin-left:auto">${f.n} (${f.pct}%)</b></div>`).join('')}
      </div>
    </div>`;
  }

  viewWeather() {
    // Haftenkamp-Station primär, weather.home als Fallback
    const hk = {
      temp:    this.firstState(['sensor.haftenkamp_temperatur']),
      wind:    this.firstState(['sensor.haftenkamp_windgeschwindigkeit']),
      gusts:   this.firstState(['sensor.haftenkamp_windboen']),
      bearing: this.firstState(['sensor.haftenkamp_windrichtung']),
      press:   this.firstState(['sensor.haftenkamp_druck']),
      rain:    this.firstState(['sensor.haftenkamp_niederschlag']),
      cloud:   this.firstState(['sensor.haftenkamp_bewolkungsgrad']),
      humid:   this.firstState(['sensor.haftenkamp_relative_luftfeuchtigkeit']),
      solar:   this.firstState(['sensor.haftenkamp_sonneneinstrahlung']),
    };
    const ws = this.firstState(['weather.home']);
    const a = ws?.attributes || {};
    const airTemp    = hk.temp    ? hk.temp.state    : (a.temperature  || '–');
    const windSpeed  = hk.wind    ? hk.wind.state    : (a.wind_speed   || '–');
    const windGusts  = hk.gusts   ? hk.gusts.state   : '–';
    const pressure   = hk.press   ? hk.press.state   : (a.pressure     || '–');
    const humidity   = hk.humid   ? hk.humid.state   : (a.humidity     || '–');
    const cloud      = hk.cloud   ? Math.round(hk.cloud.state) + '%' : (a.cloud_coverage || '–') + '%';
    const rain       = hk.rain    ? hk.rain.state + ' mm' : '–';
    const solar      = hk.solar   ? Math.round(hk.solar.state) + ' W/m²' : '–';
    const bearDeg    = hk.bearing ? parseFloat(hk.bearing.state) : (a.wind_bearing || 0);
    const dirs       = ['Nord','Nordost','Ost','Südost','Süd','Südwest','West','Nordwest'];
    const windDir    = dirs[Math.round(bearDeg / 45) % 8];
    const waterTemp  = this.val(this.firstState(['sensor.wassertemperatur_gewaesser']), '–');
    const o2         = this.attr(this.firstState(['sensor.wassertemperatur_gewaesser']),'oxygen_mg_l','–');
    const pegel      = this.val(this.firstState(['sensor.pegelstand']),'–');
    const scoreColor = v => v>=80?'#67d33f':v>=60?'#ffd23f':'#ff9d18';
    // Wettereinfluss aus echtem Sensor
    const awSensor = this.firstState(['sensor.fishing_tracker_angelwetter_index']);
    const awScore  = awSensor ? parseInt(awSensor.state) : null;
    const awAttrs  = awSensor?.attributes || {};
    const impacts  = awAttrs.water_score != null ? [
      {label:'Wassertemp.',  val: Math.round(awAttrs.water_score   / 0.35)},
      {label:'Wetter',       val: Math.round(awAttrs.weather_score / 0.30)},
      {label:'Saison',       val: awAttrs.season_score   || 70},
      {label:'Mondphase',    val: awAttrs.moon_score     || 50},
    ] : [
      {label:'Wassertemp.',val:70},{label:'Wetter',val:75},{label:'Saison',val:80},{label:'Mondphase',val:50},
    ];
    // Echter Forecast aus weather.home
    const fcRaw = (a.forecast || []).slice(0,7);
    const condIcon = c => {
      if (!c) return '⛅';
      c = c.toLowerCase();
      if (c.includes('sunny') || c.includes('clear')) return '☀️';
      if (c.includes('rain') || c.includes('regen')) return '🌧️';
      if (c.includes('storm') || c.includes('thunder')) return '⛈️';
      if (c.includes('snow') || c.includes('schnee')) return '❄️';
      if (c.includes('fog') || c.includes('nebel')) return '🌫️';
      if (c.includes('partly') || c.includes('teil')) return '⛅';
      if (c.includes('cloud') || c.includes('bewölkt')) return '☁️';
      return '⛅';
    };
    const forecast = fcRaw.length > 0 ? fcRaw.map(f => {
      const d = new Date(f.datetime);
      const dn = ['So','Mo','Di','Mi','Do','Fr','Sa'][d.getDay()];
      const dd = String(d.getDate()).padStart(2,'0') + '.' + String(d.getMonth()+1).padStart(2,'0');
      return {d: dn + ' ' + dd, icon: condIcon(f.condition), hi: Math.round(f.temperature||0), lo: Math.round(f.templow||f.temperature-6||0)};
    }) : [];
    return `
    <div class="wt-grid">
      <!-- Tabs -->
      <div class="fc-tabs"><button class="fc-tab active">Aktuell</button><button class="fc-tab">24 Stunden</button><button class="fc-tab">7 Tage</button><button class="fc-tab">14 Tage</button></div>

      <!-- Aktuell -->
      <div class="wt-current">
        <div class="wt-main">
          <div class="wt-icon">⛅</div>
          <div class="wt-temp">${airTemp}°C</div>
          <div class="wt-cond muted">Teilweise bewölkt</div>
        </div>
        <div class="wt-details">
          ${[['Wind','💨',windSpeed+' km/h '+windDir],['Böen','💨',windGusts+' km/h'],['Luftdruck','📊',pressure+' hPa'],['Bewölkung','☁️',cloud],['Luftfeuchtigkeit','💧',humidity+'%'],['Niederschlag','🌧️',rain],['Sonneneinstrahlung','☀️',solar],['Wassertemp.','🌊',waterTemp+'°C'],['O₂-Gehalt','🫧',o2+' mg/l'],['Pegelstand','📏',pegel]].map(([l,i,v])=>`<div class="wt-detail-row"><span class="muted">${i} ${l}</span><b>${v}</b></div>`).join('')}
        </div>
        <div class="wt-impact">
          <div class="ov-section-title">WETTEREINFLUSS</div>
          <div class="wt-big-val">${awScore !== null ? awScore+'%' : '–'}<span class="muted" style="font-size:14px"> ${awAttrs.level || ''}</span></div>
          ${impacts.map(f=>`<div class="wi-row"><span class="wi-label">${f.label}</span><div class="wi-bar-wrap"><div class="wi-bar" style="width:${f.val}%;background:${scoreColor(f.val)}"></div></div><span class="wi-val" style="color:${scoreColor(f.val)}">${f.val}%</span></div>`).join('')}
        </div>
      </div>

      <!-- 7-Tage Vorschau -->
      <div class="wt-forecast">
        <div class="ov-section-title">WETTERVORSCHAU – 7 TAGE</div>
        <div class="wt-fc-row">
          ${forecast.length > 0 ? forecast.map(f=>`<div class="wt-fc-day"><div class="wt-fc-d">${f.d}</div><div class="wt-fc-icon">${f.icon}</div><div class="wt-fc-hi">${f.hi}°C</div><div class="wt-fc-lo muted">${f.lo}°C</div></div>`).join('') : '<div class="muted" style="padding:20px">Keine Forecast-Daten in weather.home verfügbar</div>'}
        </div>
      </div>
    </div>`;
  }

  viewLogbook() {
    const entries = [
      {fish:'Zander',size:'68 cm',weight:'3.2 kg',spot:'Geheimer Bucht',bait:'Gummifisch',date:'22.05.2026',time:'07:15',note:'Perfekter Morgen!'},
      {fish:'Barsch',size:'34 cm',weight:'0.6 kg',spot:'Alte Kiesgrube',bait:'Spinner',date:'18.05.2026',time:'18:30',note:''},
      {fish:'Hecht',size:'71 cm',weight:'4.1 kg',spot:'Geheimer Bucht',bait:'Wobbler',date:'15.05.2026',time:'06:45',note:'Biss kurz nach Sonnenaufgang'},
      {fish:'Karpfen',size:'54 cm',weight:'2.7 kg',spot:'Alte Kiesgrube',bait:'Boilie',date:'10.05.2026',time:'05:20',note:''},
      {fish:'Zander',size:'62 cm',weight:'2.4 kg',spot:'Geheimer Bucht',bait:'Gummifisch',date:'02.05.2026',time:'19:50',note:''},
    ];
    const icons = {Zander:'🟡',Barsch:'🔴',Hecht:'🟢',Karpfen:'🟤',Aal:'⚫',Schleie:'🟠'};
    return `
    <div class="lb-grid">
      <!-- Filter Row -->
      <div class="lb-filters">
        <select class="lb-select"><option>Alle Fische</option><option>Zander</option><option>Hecht</option><option>Barsch</option></select>
        <select class="lb-select"><option>Alle Spots</option><option>Geheimer Bucht</option><option>Alte Kiesgrube</option></select>
        <select class="lb-select"><option>Alle Zeiten</option><option>Diese Woche</option><option>Diesen Monat</option></select>
        <button class="lb-add-btn">+ Neuen Fang eintragen</button>
      </div>

      <!-- List + Placeholder Detail -->
      <div class="lb-layout">
        <div class="lb-list">
          ${entries.map((e,i)=>`<div class="lb-entry ${i===0?'lb-entry-active':''}" onclick="this.parentNode.querySelectorAll('.lb-entry').forEach(x=>x.classList.remove('lb-entry-active'));this.classList.add('lb-entry-active')">
            <div class="lb-entry-icon">${icons[e.fish]||'🐟'}</div>
            <div class="lb-entry-info">
              <div class="lb-entry-fish">${e.fish}</div>
              <div class="lb-entry-size">${e.size} · ${e.weight}</div>
              <div class="lb-entry-spot muted">${e.spot}, ${e.date}</div>
            </div>
            <div class="lb-entry-bait muted">${e.bait}</div>
          </div>`).join('')}
        </div>
        <!-- Detail placeholder -->
        <div class="lb-detail">
          <div class="ov-section-title">FANGDETAILS</div>
          <div class="lb-detail-placeholder">
            <div style="font-size:48px;margin-bottom:12px">🐟</div>
            <div style="font-size:16px;font-weight:800;color:rgba(255,255,255,.6)">Fangdetails mit Fotos</div>
            <div class="muted" style="font-size:13px;margin-top:6px">Kommt in einem nächsten Update –<br>Foto-Upload wird noch eingebaut.</div>
          </div>
        </div>
      </div>
    </div>`;
  }

  viewSpots() {
    const spots = [
      {name:'Geheimer Bucht',score:91,label:'Sehr gut',fishes:['Zander','Hecht'],catches:12,dist:'2.3 km',depth:'6–12 m'},
      {name:'Alte Kiesgrube',score:88,label:'Sehr gut',fishes:['Barsch','Zander'],catches:8,dist:'1.8 km',depth:'4–8 m'},
      {name:'Steinbruch See',score:84,label:'Gut',fishes:['Karpfen','Hecht'],catches:5,dist:'4.1 km',depth:'8–15 m'},
      {name:'Flussbiegung',score:76,label:'Gut',fishes:['Zander','Aal'],catches:3,dist:'3.7 km',depth:'3–6 m'},
      {name:'Karpfenteich',score:68,label:'Mittel',fishes:['Karpfen'],catches:6,dist:'5.2 km',depth:'2–4 m'},
    ];
    const scoreColor = s => s>=80?'#67d33f':s>=65?'#ffd23f':'#ff9d18';
    return `
    <div class="sp-grid">
      <div class="sp-map-col">
        <div class="ov-section-title">SPOT-KARTE</div>
        <div class="spotMap" style="height:320px">
          <div class="pin" style="font-size:30px;filter:drop-shadow(0 0 10px rgba(103,211,63,.9))">📍</div>
          <div style="position:absolute;left:38%;top:55%;font-size:24px;filter:drop-shadow(0 0 8px rgba(255,160,40,.9))">📍</div>
          <div style="position:absolute;right:18%;bottom:25%;font-size:20px;filter:drop-shadow(0 0 8px rgba(255,215,0,.8))">📍</div>
        </div>
        <!-- Aktiver Spot Detail -->
        <div class="sp-detail">
          <div class="sp-detail-name">GEHEIMER BUCHT</div>
          <div class="sp-detail-score greenText">91% Aktivität</div>
          <div class="sp-detail-row"><span class="muted">Tiefe</span><span>6–12 m</span></div>
          <div class="sp-detail-row"><span class="muted">Entfernung</span><span>2.3 km</span></div>
          <div class="sp-detail-row"><span class="muted">Fänge (30 Tage)</span><span>12</span></div>
          <button class="sp-detail-btn">Details anzeigen</button>
        </div>
      </div>
      <div class="sp-list-col">
        <div class="ov-section-title">SPOT LISTE</div>
        ${spots.map(s=>`<div class="sp-row">
          <div class="sp-row-icon">📍</div>
          <div class="sp-row-info">
            <div class="sp-row-name">${s.name}</div>
            <div class="sp-row-fishes muted">${s.fishes.join(' · ')} · ${s.catches} Fänge diese Woche</div>
          </div>
          <div class="sp-row-score" style="color:${scoreColor(s.score)}">${s.score}%</div>
          <div class="sp-row-label" style="color:${scoreColor(s.score)}">${s.label}</div>
        </div>`).join('')}
      </div>
    </div>`;
  }

  viewWeather_old() { return this.viewWeather(); }

  viewSettings() {
    const weatherEntity = this.config.weather_entity || 'weather.home';
    return `
    <div class="set-grid">
      <div class="set-tabs">
        <button class="fc-tab active">Allgemein</button>
        <button class="fc-tab">Benachrichtigungen</button>
        <button class="fc-tab">Einheiten</button>
        <button class="fc-tab">Spots</button>
        <button class="fc-tab">Prognosen</button>
        <button class="fc-tab">Datensschutz</button>
        <button class="fc-tab">Über</button>
      </div>
      <div class="set-layout">
        <div class="set-content">
          <div class="ov-section-title">ALLGEMEIN</div>
          ${[['Standort','Mein Angelplatz'],['Zeitzone','Europe/Berlin'],['Sprache','Deutsch'],['Startseite','Übersicht']].map(([l,v])=>`<div class="set-row"><span>${l}</span><span class="muted">${v}</span></div>`).join('')}
          <div class="ov-section-title" style="margin-top:20px">BENACHRICHTIGUNGEN</div>
          ${[['Beste Zeiten (täglich)',true],['Wetterwarnungen',true],['Fang-Erinnerungen',false],['System Updates',true]].map(([l,v])=>`<div class="set-toggle-row"><span>${l}</span><div class="set-toggle ${v?'on':''}">${v?'●':''}</div></div>`).join('')}
          <div class="ov-section-title" style="margin-top:20px">DATENQUELLEN</div>
          ${[['Wetter Entity',weatherEntity],['Wassertemp.','wassertemperatur.site'],['Pegelstand','Pegelonline WSV'],['Version','v2.11.1']].map(([l,v])=>`<div class="set-row"><span>${l}</span><code class="set-code">${v}</code></div>`).join('')}
        </div>
      </div>
    </div>`;
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
