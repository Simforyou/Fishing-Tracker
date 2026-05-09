from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .analytics import current_weather_score, recommendation, stats
from .const import CONF_WEATHER_ENTITY, DOMAIN, SIGNAL_UPDATED


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    store = data["store"]

    async_add_entities([
        BiteChanceSensor(hass, entry, store),
        BestTimeSensor(hass, entry, store),
        StatsSensor(entry, store),
        RecommendationSensor(entry, store),
        WaterTemperatureSensor(hass, entry),
        MapDataSensor(entry, store),
    ], True)


class FishingBaseSensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, store, key: str, name: str) -> None:
        self.entry = entry
        self.store = store
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_should_poll = True
        self._state: Any = None
        self._attrs: dict[str, Any] = {}

    @property
    def native_value(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attrs

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATED, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_schedule_update_ha_state(True)


class BiteChanceSensor(FishingBaseSensor):
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:fish"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, store) -> None:
        super().__init__(entry, store, "bite_chance", "Beißchance Weißfisch")
        self.hass = hass

    async def async_update(self) -> None:
        score, attrs = _calculate_now(self.hass, self.entry, self.store.entries)
        self._state = score
        self._attrs = attrs


class BestTimeSensor(FishingBaseSensor):
    _attr_icon = "mdi:clock-outline"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, store) -> None:
        super().__init__(entry, store, "best_time_today", "Beste Angelzeit heute")
        self.hass = hass

    async def async_update(self) -> None:
        result = _calculate_best_time(self.hass, self.entry, self.store.entries)
        self._state = result["zeitfenster"]
        self._attrs = result


class StatsSensor(FishingBaseSensor):
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:chart-box"

    def __init__(self, entry: ConfigEntry, store) -> None:
        super().__init__(entry, store, "statistics", "Statistik")

    async def async_update(self) -> None:
        s = stats(self.store.entries)
        self._state = s.get("history_score", 50)
        self._attrs = s


class RecommendationSensor(FishingBaseSensor):
    _attr_icon = "mdi:lightbulb-on-outline"

    def __init__(self, entry: ConfigEntry, store) -> None:
        super().__init__(entry, store, "recommendation", "Angel KI Empfehlung")

    async def async_update(self) -> None:
        self._state = recommendation(self.store.entries)[:255]
        self._attrs = stats(self.store.entries)


class WaterTemperatureSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Wassertemperatur geschätzt"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_icon = "mdi:thermometer-water"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_estimated_water_temperature"
        self._state = None

    @property
    def native_value(self):
        return self._state

    async def async_update(self) -> None:
        weather_entity = self.entry.options.get(CONF_WEATHER_ENTITY) or self.entry.data.get(CONF_WEATHER_ENTITY)
        weather = self.hass.states.get(weather_entity)
        temp = _float(weather.attributes.get("temperature") if weather else None, 12)
        self._state = round(temp * 0.65 + 5, 1)


class MapDataSensor(FishingBaseSensor):
    _attr_icon = "mdi:map-marker-radius"

    def __init__(self, entry: ConfigEntry, store) -> None:
        super().__init__(entry, store, "map_data", "Karten Daten")

    async def async_update(self) -> None:
        catches = []
        heatmap = []
        spot_groups: dict[str, dict[str, Any]] = {}

        for item in self.store.entries:
            lat = _float(item.get("latitude"), None)
            lon = _float(item.get("longitude"), None)
            if lat is None or lon is None:
                continue

            catch = {
                "lat": lat,
                "lon": lon,
                "timestamp": item.get("timestamp"),
                "fish_type": item.get("fish_type"),
                "spot": item.get("spot"),
                "bait": item.get("bait"),
                "length_cm": item.get("length_cm"),
                "caught": item.get("caught", 0),
                "chance": item.get("chance"),
            }
            catches.append(catch)

            if int(item.get("caught", 0)) >= 1:
                heatmap.append([lat, lon, 0.8])

            spot = item.get("spot") or "Unbekannt"
            group = spot_groups.setdefault(
                spot,
                {"spot": spot, "lat": lat, "lon": lon, "total": 0, "catches": 0},
            )
            group["total"] += 1
            if int(item.get("caught", 0)) >= 1:
                group["catches"] += 1

        spots = []
        for group in spot_groups.values():
            total = group["total"]
            catches_count = group["catches"]
            group["success_rate"] = round(catches_count / total * 100, 1) if total else 0
            spots.append(group)

        self._state = len(catches)
        self._attrs = {
            "catches": catches[-200:],
            "heatmap": heatmap[-200:],
            "spots": spots,
        }


def _calculate_best_time(hass: HomeAssistant, entry: ConfigEntry, entries: list[dict[str, Any]]) -> dict[str, Any]:
    weather_entity = entry.options.get(CONF_WEATHER_ENTITY) or entry.data.get(CONF_WEATHER_ENTITY)
    weather = hass.states.get(weather_entity)
    attrs = weather.attributes if weather else {}
    now = datetime.now().astimezone()

    best_score = 0
    best_time = "--:--"
    best_dt = now
    points = []

    for i in range(0, 24):
        ts = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=i)
        score = _score_for_hour(hass, entry, entries, attrs, ts)

        points.append({"x": int(ts.timestamp() * 1000), "y": score})

        if ts.date() == now.date() and score > best_score:
            best_score = score
            best_time = ts.strftime("%H:%M")
            best_dt = ts

    start = best_dt - timedelta(hours=1)
    end = best_dt + timedelta(hours=2)
    zeitfenster = f"{start.strftime('%H:%M')} – {end.strftime('%H:%M')}"

    if best_score >= 85:
        aktivitaet = "Sehr hoch"
        empfehlung = "Top-Phase nutzen: fein fischen und regelmäßig sparsam füttern."
    elif best_score >= 70:
        aktivitaet = "Hoch"
        empfehlung = "Gute Bedingungen: Windkante, Kanten und bewährte Köder testen."
    elif best_score >= 50:
        aktivitaet = "Mittel"
        empfehlung = "Solide Phase: klein starten und bei Bedarf Spot wechseln."
    else:
        aktivitaet = "Niedrig"
        empfehlung = "Schwache Phase: sehr fein fischen oder später erneut probieren."

    s = stats(entries)

    return {
        "score": best_score,
        "beste_uhrzeit": best_time,
        "zeitfenster": zeitfenster,
        "aktivitaet": aktivitaet,
        "empfehlung": empfehlung,
        "tagesprognose": points,
        "history_score": s.get("history_score", 50),
        "confidence": s.get("confidence"),
        "total_entries": s.get("total"),
    }


def _calculate_now(hass: HomeAssistant, entry: ConfigEntry, entries: list[dict[str, Any]]) -> tuple[int, dict[str, Any]]:
    weather_entity = entry.options.get(CONF_WEATHER_ENTITY) or entry.data.get(CONF_WEATHER_ENTITY)
    weather = hass.states.get(weather_entity)
    attrs = weather.attributes if weather else {}
    now = datetime.now().astimezone()

    score = _score_for_hour(hass, entry, entries, attrs, now)
    s = stats(entries)

    return score, {
        "weather_entity": weather_entity,
        "temperature": _float(attrs.get("temperature"), 12),
        "pressure": _float(attrs.get("pressure"), 1015),
        "wind_speed": _float(attrs.get("wind_speed"), 10),
        "cloud_coverage": _float(attrs.get("cloud_coverage"), 50),
        "precipitation": _float(attrs.get("precipitation"), 0),
        "history_score": s.get("history_score", 50),
        "confidence": s.get("confidence"),
        "total_entries": s.get("total"),
        "top_combo": s.get("top_combo"),
        "recommendation": recommendation(entries),
    }


def _score_for_hour(
    hass: HomeAssistant,
    entry: ConfigEntry,
    entries: list[dict[str, Any]],
    attrs: dict[str, Any],
    ts: datetime,
) -> int:
    s = stats(entries)
    moon = hass.states.get("sensor.moon")

    return current_weather_score(
        temperature=_float(attrs.get("temperature"), 12),
        wind_speed=_float(attrs.get("wind_speed"), 10),
        pressure=_float(attrs.get("pressure"), 1015),
        cloud_coverage=_float(attrs.get("cloud_coverage"), 50),
        precipitation=_float(attrs.get("precipitation"), 0),
        pressure_trend=0,
        hour=ts.hour,
        month=ts.month,
        moon_phase=moon.state if moon else None,
        history_score=s.get("history_score", 50),
    )


def _float(value: Any, default: Any = 0.0) -> Any:
    try:
        if value in (None, "", "unknown", "unavailable"):
            return default
        return float(value)
    except Exception:
        return default
