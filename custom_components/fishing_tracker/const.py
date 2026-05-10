DOMAIN = "fishing_tracker"

CONF_WEATHER_ENTITY = "weather_entity"
CONF_PERSON_ENTITY = "person_entity"
CONF_MOON_ENTITY = "moon_entity"
CONF_USE_ONLINE_WEATHER = "use_online_weather"
CONF_NAME = "name"

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
    "fishing_tracker_icon.png",
]

SERVICE_INSTALL_DASHBOARD = "install_dashboard"

PANEL_URL = "/local/fishing_tracker_dashboard.html"
PANEL_TITLE = "Fishing Tracker"
PANEL_ICON = "mdi:fish"
PANEL_NAME = "fishing_tracker"
