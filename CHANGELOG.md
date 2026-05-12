# Changelog

Alle wesentlichen Änderungen am Fishing Tracker werden in dieser Datei dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

---

## [2.11.1] – 2026-05-11

### Fixed
- **HACS-Installation vollständig repariert**
  - `hacs.json` korrigiert: `content_in_root: false`, kein `filename`-Feld
  - Lovelace-Ressource wird bei jedem HA-Start automatisch auf neue Cache-URL aktualisiert
  - Kein manuelles Eintragen der JS-Ressource mehr nötig nach HACS-Update
- **Cache-Busting**: Version jetzt dynamisch aus `frontend_version.py` gezogen
  - `FRONTEND_VERSION = "2.11.0"` → URL `/local/fishing-tracker-card.js?v=2110`
  - Bei jedem Release wird die Version automatisch erhöht → Browser lädt neue JS
- **www-Dateien**: werden beim HA-Start automatisch nach `/config/www/` kopiert
  - `fishing-tracker-card.js` (Custom Card)
  - `fishing_tracker_dashboard.html` (Auto-Dashboard)
  - `fishing_tracker_map.html` (Heatmap)
  - `fishing_tracker_log.html` (Fangbuch)
  - `fishing_tracker_icon.png`


## [2.11.0] – 2026-05-11

### Added
- **SVG Köder-Icons** in der Zielfisch-Datenbank (Lovelace Card)
  - 15 handgezeichnete SVG-Icons: Gummifisch, Micro Shad, Swimbaits, Wobbler, Spinner,
    Drop-Shot, Micro-Jig, Jig (vertikal), Deadbait, Wurm, Made, Mais, Boilie,
    Brot, Popper, Creature Bait (Krebs), Kombi
  - Farblich passend zum dunklen Theme, mit Haken und realistischen Details
  - Alias-Map: Varianten wie "Gummifisch 7–12cm" → Gummifisch-Icon
  - Bait-Grid: 2-spaltiges Layout mit Icon + Name + Untertitel
- **Zielfisch-Datenbank** (komplett neuer Species-View)
  - Fischart-Tabs mit Emoji (Zander, Hecht, Barsch, Karpfen, Aal, Schleie)
  - Jagdfrequenz-Tabelle je Fischart und Wassertemperatur (Fischfindertest-Studie)
  - Aktuelle Wassertemperatur wird in der Tabelle markiert
  - Beste Beißzeiten je Fischart UND Jahreszeit (4 Saisons)
  - Laich-/Saison-Badges: Laichzeit / Vor-Laich / Post-Laich Fresswelle / Beste Saison
  - Wissenschaftliche Fakten: Farbsehen, Köderfarbe, Schwimmblase je Fischart
  - Hecht Juli-Warnung (Überfütterung – schlechteste Fangquoten)
  - Wetter-Vorlieben und -Abneigungen als Tags
  - Top Spots als blaue Tags
  - Aktivitätskurve mit aktuellem Zeitpunkt-Marker

### Changed
- `fishing-tracker-card.js` – Köder-View mit echten SVG-Icons und Bait-Cards
- `manifest.json` – Version 2.11.0


## [2.10.0] – 2026-05-11

### Added
- **Köder-Wizard** – interaktiver Vor-Ort-Köderfarben-Assistent in der Lovelace Card
  - 4 Tap-Fragen (Fischart, Trübung, Licht, Tiefe) – keine Tastatur nötig
  - Fortschrittsanzeige (4 blaue Balken)
  - Präzise Empfehlung mit Top / Gut / OK Ranking
  - Wissenschaftliche Begründung je Empfehlung
- Farbsehen je Fischart (PCR-Studien Jokela-Määttä et al. 2019)
  - Hecht + Barsch: kein Blau, kein UV (gelbe Hornhaut) → Warnung wenn Blau/UV gewählt
  - Zander: Hell-Dunkel-Kontrast (Restlichtverstärker)
  - Forelle: Breites Spektrum inkl. UV
- Tiefenabsorption: Wellenlängen-basierte Farbempfehlung
  - Flach (<2m): Alle Farben
  - Mittel (2–6m): Kein Rot, Orange wird bräunlich → Gelb/Grün/Orange
  - Tief (>6m): Nur Grün/Chartreuse/Schwarz/UV-aktiv
- UV-aktiv nur bei Tiefe + Trübung empfohlen (nicht pauschal)
- Schwarz bei Nacht als Top-Empfehlung (Silhouette gegen Mondlicht)
- Leicht trüb als "OPTIMALE" Situation markiert (Köderwissen-Erkenntnis)

### Changed
- `fishing-tracker-card.js` – Köder-View komplett ersetzt durch interaktiven Wizard
- `manifest.json` – Version 2.10.0


## [2.9.0] – 2026-05-11

### Added
- `water_level.py` – Pegelstand-Engine via PEGELONLINE WSV REST-API
  - Kostenlos, kein API-Key, 660+ Stationen an deutschen Bundeswasserstraßen
  - Wasserstand (cm), Trend (steigend/fallend/stabil), Bewertung vs. MNW/MW/MHW
  - Optional: Wassertrübung (NTU) + Wassertemperatur wo von Pegel gemessen
  - Neuer Sensor: `sensor.pegelstand`
- `bait_advisor.py` – Köder-Berater (Wettermethode + Praxiswissen)
  - Wettermethode: 4-Zustands-Matrix Klares/Trübes Wasser × Sonne/Wolken
  - Saisonal-Tageszeit-Fenster je Fischart (Hecht/Zander/Barsch/Karpfen/Aal/Schleie)
  - Herbst-Fresswelle Oktober/November: Hecht +9, Zander +7, Barsch +6 Punkte
  - Temperaturwechsel-Geschwindigkeit: Δ>4°C/Tag = -10 Punkte
  - Lichtintensitätswechsel als Trigger: Wolken→Sonne = +6 Punkte
  - Führungsstil-Empfehlung je Situation (kalt/warm/Nacht/Herbst/Winter)
  - Neuer Sensor: `sensor.koderempfehlung`
- Score-Engine: 6 neue Faktoren (jetzt 22 gesamt)
- Konfiguration: Pegelstation UUID + Name im Options-Dialog

### Changed
- `manifest.json` – Version 2.9.0
- `intelligence.py` – 6 neue Scoring-Blöcke
- `sensor.py` – WaterLevelSensor + BaitAdvisorSensor
- `__init__.py` – WaterLevelEngine initialisiert
- `const.py` – CONF_PEGEL_UUID, CONF_PEGEL_NAME
- `config_flow.py` – Pegelstation-Felder im Options-Dialog

---

## [2.8.0] – 2026-05-11

### Added
- `water_temperature.py` – Wassertemperatur von wassertemperatur.site
  - Live-Abruf: 787 Flüsse, 744 Seen, 9.800+ Küstenorte
  - Monatstabelle als Fallback (automatisch gelernt)
  - O2-Sättigungsgehalt nach Benson & Krause (mg/l)
  - Cache 3 Stunden
  - Neuer Sensor: `sensor.wassertemperatur_gewaesser`
- `solunar.py` – Solunar Mondtransit-Berechnung (reine Astronomie, kein API)
  - Hauptbeißzeiten (Mondtransit oben/unten), Nebenbeißzeiten (90° versetzt)
  - Mondphasen-Faktor, Score-Bonus bis +14 Punkte
  - Neuer Sensor: `sensor.solunar_beisszeiten`
- `spawning.py` – Laichzeiten-Kalender für 10 Fischarten
  - Pre-Laich, Hauptlaich, Post-Laich mit artspezifischen Penalties
  - Neuer Sensor: `sensor.laichzeiten_status`
- Score-Engine: 7 neue Faktoren (v2.8 gesamt 16)
  - Wassertemperatur direkt, O2, Solunar, Laichzeit, Sonnenauf/-untergang
  - Windrichtung vollständig, Wetterfront-Erkennung

### Changed
- `manifest.json` – Version 2.8.0
- `const.py` – CONF_WATER_TEMP_URL, CONF_LATITUDE, CONF_LONGITUDE
- `config_flow.py` – URL + Koordinaten im Options-Dialog
- `intelligence.py` – Neue Parameter + Scoring-Blöcke
- `analytics.py` – Parameter-Durchreichung erweitert
- `sensor.py` – 3 neue Sensor-Klassen

---

## [2.7.1] – 2026-05-11

### Fixed
- Schnellaktion-Buttons in der Lovelace Card funktionieren
- `log_catch`/`log_no_catch` per `hass.callService`
- Toast-Bestätigung nach Aktion

---

## [2.7.0] – 2026-05-11

### Added
- Native Lovelace Custom Card `custom:fishing-tracker-card`
- Sidebar-Navigation (9 Views)
- Live HA State Binding, Premium Dark UI
- `LOVELACE_CARD.md`

---

## [2.6.9] – 2026-05-11

### Fixed
- Startfehler durch Panel-Registrierung auf neueren HA-Versionen
- `DASHBOARD_CARD.md` Hilfsdatei hinzugefügt

---

## [2.6.7] – 2026-05-11

### Added
- Home Assistant Sidebar Panel (Fishing Tracker direkt im Menü)

---

## [2.6.6] – 2026-05-11

### Added
- Premium Auto-Dashboard Redesign mit SVG-Graphen
- Tages-/Wochenprognose, Zielfisch-Kurve, Smart Spot Preview

---

## [2.6.5] – 2026-05-11

### Added
- Responsive Fullscreen Dashboard, Live Binding, Auto-Refresh 3s

---

## [2.6.4] – 2026-05-11

### Added
- Integration Icon/Logo Assets (icon.png, logo.png)

---

## [2.6.3] – 2026-05-11

### Fixed
- Service-Registrierung für `export_json` und `install_dashboard`

---

## [2.6.2] – 2026-05-11

### Fixed
- Fehlende Konstante `SERVICE_INSTALL_DASHBOARD` in `const.py`

---

## [2.6.1] – 2026-05-11

### Added
- `advanced_intelligence.py` – Lernende KI-Engine
- Spot-Scoring, Mustererkennung, Gewässerprofile, persönliche Strategie

---

## [2.6.0] – 2026-05-11

### Added
- `fishing_knowledge.py` – Köder- und Ruten-Wissensbasis

---

## [2.5.0] – 2026-05-11

### Added
- Species Ranking Engine, Fischarten-Ranking Sensor, Online Wetterstatus Sensor

---

## [2.4.0] – 2026-05-11

### Added
- Open-Meteo Live-Wetterengine, Standortbasierte Wetterdaten, 30-Min-Cache

---

## [2.3.0] – 2026-05-11

### Added
- `weather_engine.py` – Open-Meteo Architektur + FishingWeather Dataclass

---

## [2.2.1] – 2026-05-11

### Added
- CHANGELOG.md eingeführt, Release-Notes-Konzept etabliert

---

## [2.2.0] – 2026-05-11

### Added
- `fish_profiles.py` – 10 Fischarten-Profile mit Temperatur, Saison, Mondgewichtung, Köder

---

## [2.1.0] – 2026-05-11

### Added
- Automatisches Dashboard-Installer, Service `install_dashboard`

---

## [2.0.1] – 2026-05-11

### Fixed
- www-Installer, konfigurierbare Mondphasen-Entity, Karten-Fixes

---

## [2.0.0] – 2026-05-11

### Added
- Erste Fishing Intelligence Engine mit erklärbarem Smart Score
- Wetterfaktoren: Luftdruck, Wind, Bewölkung, Regen, Temperatur, Feuchte, UV, Mondphase
