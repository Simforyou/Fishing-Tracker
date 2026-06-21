DOMAIN = "fishing_tracker"

CONF_WEATHER_ENTITY = "weather_entity"
CONF_PERSON_ENTITY = "person_entity"
CONF_MOON_ENTITY = "moon_entity"
CONF_USE_ONLINE_WEATHER = "use_online_weather"
CONF_NAME = "name"

# Wassertemperatur von wassertemperatur.site
# Beispiel: https://wassertemperatur.site/flusse/water-temp-in-dinkel
CONF_WATER_TEMP_URL = "water_temp_url"

# Pegelonline WSV – UUID der nächsten Pegelstation (kostenlos, kein API-Key)
# Stationen: https://pegelonline.wsv.de/webservices/rest-api/v2/stations.json
CONF_PEGEL_UUID = "pegel_uuid"
CONF_PEGEL_NAME = "pegel_name"

# Koordinaten des Angelplatzes (für Solunar-Berechnung)
CONF_LATITUDE = "fishing_latitude"
CONF_LONGITUDE = "fishing_longitude"

DEFAULT_NAME = "Fishing Tracker"

PLATFORMS = ["sensor", "select", "number", "button"]

SERVICE_LOG_CATCH = "log_catch"
SERVICE_LOG_NO_CATCH = "log_no_catch"
SERVICE_IMPORT_CSV = "import_csv"
SERVICE_EXPORT_CSV = "export_csv"
SERVICE_EXPORT_JSON = "export_json"

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.data"
SIGNAL_UPDATED = f"{DOMAIN}_updated"

DATA_DIR = "fishing_tracker"
JSON_FILE = "fangdaten.json"
WWW_JSON_FILE = "fishing_tracker_data.json"

FISH_TYPES = [
    "Weißfisch", "Brasse", "Rotauge", "Rotfeder", "Karpfen",
    "Schleie", "Barsch", "Zander", "Hecht", "Aal",
]

SPOTS = [
    "Windkante", "Schilfkante", "Kraut", "Flachwasser",
    "Tiefe Kante", "Steg", "Hafenecke",
]

BAITS = [
    "Made", "Pinkies", "Caster", "Mais", "Brot", "Wurm", "Kombi", "Boilie",
]

DEFAULT_SETTINGS = {
    "fish_type": "Weißfisch",
    "spot": "Windkante",
    "bait": "Made",
    "length_cm": 0,
}

WWW_FILES = [
    "fishing_tracker_map.html",
    "fishing_tracker_log.html",
    "fishing_tracker_dashboard.html",
    "fishing_tracker_panel.html",
    "fishing-barometer-card.js",
    "fishing_tracker_map_engine.js",
    "fishing_tracker_icon.png",
    "fishing-tracker-card.js",
    "fishing-quick-card.js",
    "fishing_tracker_quick.html",
    "fish_fallback.jpg",
]

SERVICE_INSTALL_DASHBOARD = "install_dashboard"

PANEL_URL = "/local/fishing_tracker_panel.html"
PANEL_TITLE = "Fishing Tracker"
PANEL_ICON = "mdi:fish"
PANEL_NAME = "fishing_tracker"
