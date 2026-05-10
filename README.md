# Fishing Tracker Home Assistant Integration

Version 2.6.2

## Neu in 1.3.0
- Natürlichere Tages- und Wochen-Beißprognose
- Weniger regelmäßiges künstliches Muster
- Wetterdrift-Simulation für Temperatur, Wind, Luftdruck, Bewölkung und Regen
- Mondphase wird in Prognose berücksichtigt
- Fanghistorie fließt weiter in die Gewichtung ein
- Unregelmäßige Bite-Windows statt starrer Kurve
- JSON Storage und Heatmap aus v1.2.0 bleiben erhalten

## Fix in 1.3.1
- Options-/Konfigurationsdialog für neuere Home-Assistant-Versionen repariert.

## Fix in 1.3.2
- Markeranzeige in Leaflet repariert.
- Fanghistorie repariert.
- Statistik zählt JSON-Einträge.
- UTF-8 Fix für Umlaute.
- Robuster JSON-Parser.

## Fix in 1.3.3
- Stabiler Abschlussstand nach Karten-/Heatmap-Fix.
- Leaflet-Karte mit JSON-Daten repariert.
- Fanghistorie mit JSON-Daten repariert.
- UTF-8/Mojibake-Fix für Umlaute konsolidiert.
- HACS-Struktur geprüft.
- manifest.json auf 1.3.3 gesetzt.
- hacs.json korrekt mit domains: ["fishing_tracker"].
- Dashboard-kompatibel mit Cache-Busting URLs wie ?v=20.

## Neu in 1.4.0
- Echte Heatmap-Intensität nach Spot-Fangquote.
- Spot-Intelligenz-Panel in der Karte.
- Spot-Ranking mit Sessions, Fängen, Fangquote, Top-Köder und KI-Chance.
- Spot-Labels direkt auf der Karte.
- bessere Filter- und Kartenlogik für viele Einträge.

## Neu in 2.0.0
- Erste Fishing Intelligence Engine.
- Fischarten-Verhalten für Hecht, Zander, Barsch, Karpfen und Weißfisch.
- Wetterfaktoren: Luftdruck, Luftdrucktrend, Wind, Bewölkung, Regen, Temperatur, Feuchte/Taupunkt/UV soweit verfügbar.
- Mondphase wird im Score berücksichtigt.
- Erklärbarer Smart Score mit Gründen und Warnungen.
- Neuer Sensor: Fishing Intelligence.
- Tages-/Wochenprognose nutzt die neue Intelligence Engine.

## Fix in 2.0.1
- Automatischer www-Installer: HTML-Dateien werden beim Start nach /config/www kopiert.
- Neue Option: Mondphasen-Entity konfigurierbar.
- Fallback auf sensor.moon_phase und sensor.moon.
- KI nutzt die konfigurierte Mond-Entity.
- Karten-Popup/Tooltip-Design repariert.
- Schwarzer Balken/kaputte Spot-Label-Darstellung behoben.

## Neu in 2.1.0
- Automatische Dashboard-App: `/local/fishing_tracker_dashboard.html`
- Dashboard-Datei wird automatisch nach `/config/www` installiert.
- Service `fishing_tracker.install_dashboard` zum erneuten Kopieren der Dashboard-Dateien.
- Heatmap und Fanghistorie werden in der Dashboard-App eingebettet.

## Neu in 2.2.0
- Fish Behavior Knowledge Base (`fish_profiles.py`).
- Fischartspezifische Profile für Weißfisch, Brasse, Rotauge, Rotfeder, Karpfen, Schleie, Barsch, Zander, Hecht und Aal.
- Prognose nutzt je Fischart eigene Temperaturbereiche, Aktivitätsfenster, Saison, Wetter- und Mondgewichtung.
- Smart Score erklärt bessere Gründe/Warnungen je Fischart.
- Köderempfehlungen je Fischart in der Intelligence-Auswertung.
- Tages-/Wochenprognose realistischer durch Artprofile.

## Neu in 2.5.0
- Fischarten-Ranking
- Online Wetterstatus Sensor
- Auto-Dashboard mit Zielfisch-Ranking und Wetterdaten

## Neu in 2.6.1
- Advanced Intelligence
- Spot-Scoring
- Mustererkennung
- Gewässerprofile
- persönliche Angelstrategie

## Fix in 2.6.2
- Startfehler wegen fehlender SERVICE_INSTALL_DASHBOARD-Konstante behoben.
