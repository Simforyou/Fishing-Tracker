from __future__ import annotations

from datetime import datetime
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .analytics import current_weather_score
from .const import (
    CONF_PERSON_ENTITY,
    CONF_WEATHER_ENTITY,
    DEFAULT_NAME,
    DOMAIN,
    PLATFORMS,
    SERVICE_EXPORT_CSV,
    SERVICE_IMPORT_CSV,
    SERVICE_LOG_CATCH,
    SERVICE_LOG_NO_CATCH,
    SIGNAL_UPDATED,
)
from .storage import FishingStore

SERVICE_LOG_SCHEMA = vol.Schema({
    vol.Optional("fish_type", default="Weißfisch"): cv.string,
    vol.Optional("spot", default="Windkante"): cv.string,
    vol.Optional("bait", default="Made"): cv.string,
    vol.Optional("length_cm", default="Unbekannt"): cv.string,
    vol.Optional("angler", default=""): cv.string,
    vol.Optional("latitude"): vol.Coerce(float),
    vol.Optional("longitude"): vol.Coerce(float),
    vol.Optional("notes", default=""): cv.string,
})

SERVICE_IMPORT_SCHEMA = vol.Schema({
    vol.Optional("path", default="/config/www/fishing_tracker.csv"): cv.string,
})

SERVICE_EXPORT_SCHEMA = vol.Schema({
    vol.Optional("path", default="/config/www/fishing_tracker_export.csv"): cv.string,
})


async def async_setup_entry(hass: HomeAssistant, entry: FishingConfigEntry) -> bool:
    store = FishingStore(hass)
    await store.async_load()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "store": store,
        "entry": entry,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _build_entry(call: ServiceCall, caught: int) -> dict[str, Any]:
        weather_entity = entry.data.get(CONF_WEATHER_ENTITY)
        person_entity = entry.data.get(CONF_PERSON_ENTITY)
        weather_state = hass.states.get(weather_entity) if weather_entity else None
        person_state = hass.states.get(person_entity) if person_entity else None

        attrs = weather_state.attributes if weather_state else {}
        person_attrs = person_state.attributes if person_state else {}

        latitude = call.data.get("latitude", person_attrs.get("latitude"))
        longitude = call.data.get("longitude", person_attrs.get("longitude"))

        now = datetime.now().astimezone()
        pressure = _float(attrs.get("pressure"), 1015)
        temperature = _float(attrs.get("temperature"), 12)
        wind_speed = _float(attrs.get("wind_speed"), 10)
        cloud = _float(attrs.get("cloud_coverage"), 50)
        precipitation = _float(attrs.get("precipitation"), 0)

        entries = store.entries
        from .analytics import stats
        history = stats(entries).get("history_score", 50)

        chance = current_weather_score(
            temperature=temperature,
            wind_speed=wind_speed,
            pressure=pressure,
            cloud_coverage=cloud,
            precipitation=precipitation,
            pressure_trend=0,
            hour=now.hour,
            month=now.month,
            moon_phase=(hass.states.get("sensor.moon").state if hass.states.get("sensor.moon") else None),
            history_score=history,
        )

        return {
            "timestamp": now.isoformat(),
            "angler": call.data.get("angler") or entry.data.get(CONF_NAME, DEFAULT_NAME),
            "latitude": latitude,
            "longitude": longitude,
            "fish_type": call.data.get("fish_type"),
            "caught": caught,
            "spot": call.data.get("spot"),
            "bait": call.data.get("bait"),
            "length_cm": call.data.get("length_cm"),
            "notes": call.data.get("notes"),
            "chance": chance,
            "pressure": pressure,
            "temperature": temperature,
            "wind_speed": wind_speed,
            "cloud_coverage": cloud,
            "precipitation": precipitation,
        }

    async def handle_log_catch(call: ServiceCall) -> None:
        new_entry = await _build_entry(call, 1)
        await store.async_add_entry(new_entry)
        async_dispatcher_send(hass, SIGNAL_UPDATED)

    async def handle_log_no_catch(call: ServiceCall) -> None:
        new_entry = await _build_entry(call, 0)
        await store.async_add_entry(new_entry)
        async_dispatcher_send(hass, SIGNAL_UPDATED)

    async def handle_import_csv(call: ServiceCall) -> None:
        await store.async_import_csv(call.data["path"])
        async_dispatcher_send(hass, SIGNAL_UPDATED)

    async def handle_export_csv(call: ServiceCall) -> None:
        await store.async_export_csv(call.data["path"])
        async_dispatcher_send(hass, SIGNAL_UPDATED)

    hass.services.async_register(DOMAIN, SERVICE_LOG_CATCH, handle_log_catch, schema=SERVICE_LOG_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_LOG_NO_CATCH, handle_log_no_catch, schema=SERVICE_LOG_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_IMPORT_CSV, handle_import_csv, schema=SERVICE_IMPORT_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_EXPORT_CSV, handle_export_csv, schema=SERVICE_EXPORT_SCHEMA)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: FishingConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    # Keep services registered if another instance exists.
    if not hass.data.get(DOMAIN):
        for service in (SERVICE_LOG_CATCH, SERVICE_LOG_NO_CATCH, SERVICE_IMPORT_CSV, SERVICE_EXPORT_CSV):
            hass.services.async_remove(DOMAIN, service)

    return unload_ok


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, "", "unknown", "unavailable"):
            return default
        return float(value)
    except Exception:
        return default
