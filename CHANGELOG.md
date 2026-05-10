# Changelog


## v2.2.1
### Added
- Release-Notes-Konzept eingeführt
- CHANGELOG.md eingeführt
- Vorbereitung für Online-Wetterengine
- Vorbereitung für automatische Cache-Versionierung

### Changed
- Versionsverwaltung verbessert
- Release-Dokumentation standardisiert

### Planned
- Open-Meteo Integration
- Person-Entity basierte Wetterdaten
- automatische Dashboard-Cache-Versionierung
- fundierte Fish-Behavior-Engine


## v2.3.0
### Added
- weather_engine.py
- Open-Meteo Architektur
- FishingWeather Dataclass
- Frontend-Versionierungsstruktur
- Release Notes für v2.3.0

### Improved
- Vorbereitung für Online-Wetterdaten
- Grundlage für automatische Cache-Versionierung
- Projektstruktur erweitert

### Planned
- Live Open-Meteo Integration
- automatische GPS-Wetterdaten
- vollständige Echtzeit-Prognoseengine

## v2.4.0
### Added
- Open-Meteo Live-Wetterengine
- Standortbasierte Wetterdaten über Person-Entity
- 30-Minuten Wettercache
- Luftdrucktrend aus Forecastdaten
- Windrichtung, Böen, UV, Taupunkt, Luftfeuchtigkeit, Niederschlagswahrscheinlichkeit
- Fallback auf lokale Wetterintegration

### Fixed
- frontend_version.py korrigiert

### Changed
- Tages-/Wochenprognosen nutzen bevorzugt Online-Wetterdaten

## v2.5.0
### Added
- Species Ranking Engine
- New sensor: Fischarten Ranking
- New sensor: Online Wetterstatus
- Auto-dashboard section for target species ranking
- Auto-dashboard live weather data section

### Changed
- Auto-dashboard updated to v2.5.0
- Forecast/Ranking modules prepared for Open-Meteo weather context


## v2.6.0
### Added
- fishing_knowledge.py
- Predator Intelligence Basis
- Köder- und Ruten-Wissensbasis
- Auto-Dashboard Strategie-/Gerätebereich

### Changed
- Dashboard auf v2.6.0 aktualisiert
- Auto-Dashboard als Hauptoberfläche empfohlen

## v2.6.1
### Added
- advanced_intelligence.py
- Advanced Intelligence sensor
- Lernende Auswertung aus Fangdaten
- Gewässerprofile / Spotprofile
- automatische Mustererkennung
- Spot-Scoring / Hotspot-Erkennung
- Kartenanalyse mit GPS-Zonen
- persönliche Angelstrategie
- Dashboard-Bereich „Lernende Strategie“

### Excluded
- Fangfoto-System bewusst nicht enthalten.
