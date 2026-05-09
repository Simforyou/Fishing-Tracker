# Fishing Tracker Home Assistant Integration

Custom Integration für Fangtagebuch, Weißfisch-Prognose, Historienanalyse und vorbereitete ML-Auswertung.

## Installation

1. ZIP entpacken.
2. Ordner `custom_components/fishing_tracker` nach `/config/custom_components/fishing_tracker` kopieren.
3. Home Assistant neu starten.
4. Einstellungen → Geräte & Dienste → Integration hinzufügen → `Fishing Tracker`.
5. Wetter-Entity eintragen, z. B. `weather.home`.
6. Optional Person-Entity eintragen, z. B. `person.xyz`.

## Services

- `fishing_tracker.log_catch`
- `fishing_tracker.log_no_catch`
- `fishing_tracker.import_csv`
- `fishing_tracker.export_csv`

## CSV-Import

Nach dem Einrichten:

Entwicklerwerkzeuge → Aktionen → `fishing_tracker.import_csv`

Standardpfad:

`/config/www/fishing_tracker.csv`

Unterstützt alte CSV mit 13 Spalten und neue CSV mit 14 Spalten inklusive Länge.

## Enthaltene Sensoren

- Beißchance Weißfisch
- Beste Angelzeit heute
- Fishing Tracker Statistik
- Angel KI Empfehlung
- Wassertemperatur geschätzt

## Roadmap

### v1
UI-Setup, Services, interne Speicherung, CSV-Import, Sensoren, Basis-Prognose.

### v2
Spot-/Köder-/Fischgrößenanalyse, bessere Wetter-/Zeitmuster, Heatmap-Daten.

### v3
ML-Modul, mehrere Gewässer, automatische Empfehlungen, HACS-ready Repository.
