from __future__ import annotations

from datetime import datetime
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .analytics import current_weather_score, stats

from .storage import FishingStore
from .frontend import async_install_frontend_files
from .frontend_version import FRONTEND_VERSION
from .weather_engine import OpenMeteoWeatherEngine
from .water_temperature import WaterTemperatureEngine
from .water_level import WaterLevelEngine
from .const import (
    CONF_PERSON_ENTITY,
    CONF_WEATHER_ENTITY,
    CONF_WATER_TEMP_URL,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_PEGEL_UUID,
    CONF_PEGEL_NAME,
    DEFAULT_NAME,
    DOMAIN,
    PLATFORMS,
    SERVICE_EXPORT_CSV,
    SERVICE_EXPORT_JSON,
    SERVICE_INSTALL_DASHBOARD,
    SERVICE_IMPORT_CSV,
    SERVICE_LOG_CATCH,
    SERVICE_LOG_NO_CATCH,
    SIGNAL_UPDATED,
    PANEL_ICON,
    PANEL_NAME,
    PANEL_TITLE,
    PANEL_URL,
)


SERVICE_LOG_SCHEMA = vol.Schema({
    vol.Optional("fish_type"): cv.string,
    vol.Optional("spot"): cv.string,
    vol.Optional("bait"): cv.string,
    vol.Optional("length_cm"): vol.Any(cv.string, vol.Coerce(float)),
    vol.Optional("angler"): cv.string,
    vol.Optional("latitude"): vol.Coerce(float),
    vol.Optional("longitude"): vol.Coerce(float),
    vol.Optional("notes", default=""): cv.string,
})

SERVICE_IMPORT_SCHEMA = vol.Schema({vol.Optional("path", default="/config/www/fishing_tracker.csv"): cv.string})
SERVICE_EXPORT_SCHEMA = vol.Schema({vol.Optional("path", default="/config/www/fishing_tracker_export.csv"): cv.string})
SERVICE_EXPORT_JSON_SCHEMA = vol.Schema({vol.Optional("path", default="/config/www/fishing_tracker_data.json"): cv.string})
SERVICE_INSTALL_DASHBOARD = "install_dashboard"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    store = FishingStore(hass)
    await store.async_load()
    await async_install_frontend_files(hass)
    await async_register_lovelace_resource(hass)

    # Register own sidebar panel (moderner HA-kompatibler Weg)
    try:
        from homeassistant.components import frontend as ha_frontend
        # Cache-Buster: Version in URL → Browser lädt immer neue Version
        versioned_url = f"{PANEL_URL}?v={FRONTEND_VERSION.replace('.', '')}"
        ha_frontend.async_register_built_in_panel(
            hass,
            component_name="iframe",
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            frontend_url_path=PANEL_NAME,
            config={"url": versioned_url},
            require_admin=False,
        )
    except Exception:
        pass  # Panel-Registrierung ist optional – Card funktioniert auch ohne

    hass.data.setdefault(DOMAIN, {})

    # Water Temperature Engine aufbauen
    water_temp_engine = WaterTemperatureEngine(hass)
    water_temp_url = entry.options.get(CONF_WATER_TEMP_URL) or entry.data.get(CONF_WATER_TEMP_URL, "")
    if water_temp_url:
        water_temp_engine.set_url(water_temp_url)

    # Pegelstand Engine aufbauen
    water_level_engine = WaterLevelEngine(hass)
    pegel_uuid = entry.options.get(CONF_PEGEL_UUID) or entry.data.get(CONF_PEGEL_UUID, "")
    pegel_name = entry.options.get(CONF_PEGEL_NAME) or entry.data.get(CONF_PEGEL_NAME, "")
    if pegel_uuid:
        water_level_engine.set_station(pegel_uuid, pegel_name)

    hass.data[DOMAIN][entry.entry_id] = {
        "store": store,
        "entry": entry,
        "weather_engine": OpenMeteoWeatherEngine(hass),
        "water_temp_engine": water_temp_engine,
        "water_level_engine": water_level_engine,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_log_catch(call: ServiceCall) -> None:
        await async_log_entry(hass, entry, 1, dict(call.data))

    async def handle_log_no_catch(call: ServiceCall) -> None:
        await async_log_entry(hass, entry, 0, dict(call.data))

    async def handle_import_csv(call: ServiceCall) -> None:
        await store.async_import_csv(call.data["path"])
        async_dispatcher_send(hass, SIGNAL_UPDATED)

    async def handle_export_csv(call: ServiceCall) -> None:
        await store.async_export_csv(call.data["path"])
        async_dispatcher_send(hass, SIGNAL_UPDATED)

    async def handle_export_json(call: ServiceCall) -> None:
        await store.async_export_json(call.data["path"])
        async_dispatcher_send(hass, SIGNAL_UPDATED)

    async def handle_install_dashboard(call: ServiceCall) -> None:
        await async_install_frontend_files(hass)
        await async_register_lovelace_resource(hass)
        async_dispatcher_send(hass, SIGNAL_UPDATED)

    if not hass.services.has_service(DOMAIN, SERVICE_LOG_CATCH):
        hass.services.async_register(DOMAIN, SERVICE_LOG_CATCH, handle_log_catch, schema=SERVICE_LOG_SCHEMA)
    if not hass.services.has_service(DOMAIN, SERVICE_LOG_NO_CATCH):
        hass.services.async_register(DOMAIN, SERVICE_LOG_NO_CATCH, handle_log_no_catch, schema=SERVICE_LOG_SCHEMA)
    if not hass.services.has_service(DOMAIN, SERVICE_IMPORT_CSV):
        hass.services.async_register(DOMAIN, SERVICE_IMPORT_CSV, handle_import_csv, schema=SERVICE_IMPORT_SCHEMA)
    if not hass.services.has_service(DOMAIN, SERVICE_EXPORT_CSV):
        hass.services.async_register(DOMAIN, SERVICE_EXPORT_CSV, handle_export_csv, schema=SERVICE_EXPORT_SCHEMA)
    if not hass.services.has_service(DOMAIN, SERVICE_EXPORT_JSON):
        hass.services.async_register(DOMAIN, SERVICE_EXPORT_JSON, handle_export_json, schema=SERVICE_EXPORT_JSON_SCHEMA)
    if not hass.services.has_service(DOMAIN, SERVICE_INSTALL_DASHBOARD):
        hass.services.async_register(DOMAIN, SERVICE_INSTALL_DASHBOARD, handle_install_dashboard)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    if not hass.data.get(DOMAIN):
        for service in (SERVICE_LOG_CATCH, SERVICE_LOG_NO_CATCH, SERVICE_IMPORT_CSV, SERVICE_EXPORT_CSV, SERVICE_EXPORT_JSON):
            if hass.services.has_service(DOMAIN, service):
                hass.services.async_remove(DOMAIN, service)

    return unload_ok


async def async_log_entry(hass: HomeAssistant, entry: ConfigEntry, caught: int, data: dict[str, Any] | None = None) -> None:
    data = data or {}
    store: FishingStore = hass.data[DOMAIN][entry.entry_id]["store"]
    settings = store.settings

    weather_entity = entry.options.get(CONF_WEATHER_ENTITY) or entry.data.get(CONF_WEATHER_ENTITY)
    person_entity = entry.options.get(CONF_PERSON_ENTITY) or entry.data.get(CONF_PERSON_ENTITY)

    weather_state = hass.states.get(weather_entity) if weather_entity else None
    person_state = hass.states.get(person_entity) if person_entity else None

    weather_attrs = weather_state.attributes if weather_state else {}
    person_attrs = person_state.attributes if person_state else {}

    latitude = data.get("latitude", person_attrs.get("latitude"))
    longitude = data.get("longitude", person_attrs.get("longitude"))

    now = datetime.now().astimezone()

    pressure = _float(weather_attrs.get("pressure"), 1015)
    temperature = _float(weather_attrs.get("temperature"), 12)
    wind_speed = _float(weather_attrs.get("wind_speed"), 10)
    cloud = _float(weather_attrs.get("cloud_coverage"), 50)
    precipitation = _float(weather_attrs.get("precipitation"), 0)

    s = stats(store.entries)
    moon = hass.states.get("sensor.moon")
    chance = current_weather_score(
        temperature=temperature,
        wind_speed=wind_speed,
        pressure=pressure,
        cloud_coverage=cloud,
        precipitation=precipitation,
        pressure_trend=0,
        hour=now.hour,
        month=now.month,
        moon_phase=moon.state if moon else None,
        history_score=s.get("history_score", 50),
    )

    new_entry = {
        "timestamp": now.isoformat(),
        "angler": data.get("angler") or entry.data.get(CONF_NAME, DEFAULT_NAME),
        "latitude": latitude,
        "longitude": longitude,
        "fish_type": data.get("fish_type") or settings.get("fish_type"),
        "caught": caught,
        "spot": data.get("spot") or settings.get("spot"),
        "bait": data.get("bait") or settings.get("bait"),
        "length_cm": data.get("length_cm", settings.get("length_cm", 0)),
        "notes": data.get("notes", ""),
        "chance": chance,
        "pressure": pressure,
        "temperature": temperature,
        "wind_speed": wind_speed,
        "cloud_coverage": cloud,
        "precipitation": precipitation,
    }

    await store.async_add_entry(new_entry)
    async_dispatcher_send(hass, SIGNAL_UPDATED)


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, "", "unknown", "unavailable"):
            return default
        return float(value)
    except Exception:
        return default


async def async_register_lovelace_resource(hass: HomeAssistant) -> None:
    """Register/update Lovelace custom card resource.

    Aktualisiert die Cache-URL bei jedem HA-Start automatisch,
    damit nach HACS-Updates die neue JS-Version geladen wird.
    """
    url = f"/local/fishing-tracker-card.js?v={FRONTEND_VERSION.replace('.', '')}"
    try:
        storage = hass.helpers.storage.Store(1, "lovelace_resources")
        data = await storage.async_load() or {"items": []}
        items = data.get("items", [])
        existing = next(
            (i for i in items if i.get("url", "").startswith("/local/fishing-tracker-card.js")),
            None,
        )
        if existing:
            if existing.get("url") != url:
                existing["url"] = url
                data["items"] = items
                await storage.async_save(data)
        else:
            items.append({"id": "fishing-tracker-card", "type": "module", "url": url})
            data["items"] = items
            await storage.async_save(data)
    except Exception:
        pass  # Fallback: manuell /local/fishing-tracker-card.js?v=2110 eintragen

    # Barometer Card registrieren
    baro_url = f"/local/fishing-barometer-card.js?v={FRONTEND_VERSION.replace('.', '')}"""
    try:
        storage2 = hass.helpers.storage.Store(1, "lovelace_resources")
        data2 = await storage2.async_load() or {"items": []}
        items2 = data2.get("items", [])
        existing2 = next(
            (i for i in items2 if i.get("url", "").startswith("/local/fishing-barometer-card.js")),
            None,
        )
        if existing2:
            if existing2.get("url") != baro_url:
                existing2["url"] = baro_url
                data2["items"] = items2
                await storage2.async_save(data2)
        else:
            items2.append({"id": "fishing-barometer-card", "type": "module", "url": baro_url})
            data2["items"] = items2
            await storage2.async_save(data2)
    except Exception:
        pass
