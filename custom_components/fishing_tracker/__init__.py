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
from .const import (
    CONF_PERSON_ENTITY,
    CONF_WEATHER_ENTITY,
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
)
from .storage import FishingStore
from .frontend import async_install_frontend_files


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

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"store": store, "entry": entry}

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
        hass.services.async_register(DOMAIN, SERVICE_EXPORT_JSON,
            SERVICE_INSTALL_DASHBOARD, handle_export_json, schema=SERVICE_EXPORT_JSON_SCHEMA)
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
