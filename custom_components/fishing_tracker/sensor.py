from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .analytics import bite_forecast_series, current_weather_score, recommendation, stats
from .intelligence import intelligence_recommendation, smart_fishing_score
from .fish_profiles import profile_summary
from .species_ranking import rank_species
from .advanced_intelligence import advanced_analysis
from .solunar import solunar_times
from .water_temperature import WaterTemperatureEngine, estimate_oxygen, oxygen_level_label
from .water_level import WaterLevelEngine, turbidity_score_modifier
from .nlwkn_water_temp import NlwknWaterTempEngine
from .spawning import spawning_status
from .bait_advisor import full_bait_recommendation, wettermethode_color
from .forecast_aggregator import get_consolidated_forecast
from .const import (
    CONF_MOON_ENTITY, CONF_PERSON_ENTITY, CONF_USE_ONLINE_WEATHER,
    CONF_WEATHER_ENTITY, CONF_WATER_TEMP_URL, CONF_LATITUDE, CONF_LONGITUDE,
    CONF_PEGEL_UUID, CONF_PEGEL_NAME,
    DOMAIN, SIGNAL_UPDATED,
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    store = hass.data[DOMAIN][entry.entry_id]["store"]

    async_add_entities([
        BiteChanceSensor(hass, entry, store),
        BestTimeSensor(hass, entry, store),
        DayForecastSensor(hass, entry, store),
        WeekForecastSensor(hass, entry, store),
        DailyForecastSensor(hass, entry, store),
        StatsSensor(entry, store),
        RecommendationSensor(entry, store),
        IntelligenceSensor(hass, entry, store),
        WaterTemperatureSensor(hass, entry),
        MapDataSensor(entry, store),
        HistorySensor(entry, store),
        SpotAnalysisSensor(entry, store),
        BaitAnalysisSensor(entry, store),
        TimeAnalysisSensor(entry, store),
        LastCatchSensor(entry, store),
        SpeciesRankingSensor(hass, entry, store),
        OnlineWeatherStatusSensor(hass, entry, store),
        AdvancedIntelligenceSensor(entry, store),
        # Neue Sensoren v2.8
        SolunarSensor(hass, entry),
        WaterTempDetailSensor(hass, entry),
        SpawningSensor(hass, entry),
        # Neue Sensoren v2.9
        WaterLevelSensor(hass, entry),
        BaitAdvisorSensor(hass, entry),
        AngelwetterIndexSensor(hass, entry, store),
        ConsolidatedForecastSensor(hass, entry),
        ForecastAccuracySensor(entry, store),
        # v2.35: echte Wassertemperatur via NLWKN Gewässergüte (Laar/Vechte)
        NlwknWaterTempSensor(hass, entry),
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
        # Entity-ID explizit setzen → Panel liest immer sensor.fishing_tracker_{key}
        self.entity_id = f"sensor.fishing_tracker_{key.replace('-', '_')}"  

    @property
    def native_value(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attrs

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_UPDATED, self._handle_update))

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
        result = await _calculate_best_time(self.hass, self.entry, self.store.entries)
        self._state = result["zeitfenster"]
        self._attrs = result


class DayForecastSensor(FishingBaseSensor):
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:chart-line"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, store) -> None:
        super().__init__(entry, store, "bite_forecast_day", "Beißprognose Tag")
        self.hass = hass

    async def async_update(self) -> None:
        result = await _forecast(self.hass, self.entry, self.store.entries, 24)
        self._state = result["current"]
        self._attrs = result


class WeekForecastSensor(FishingBaseSensor):
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:calendar-week"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, store) -> None:
        super().__init__(entry, store, "bite_forecast_week", "Beißprognose Woche")
        self.hass = hass

    async def async_update(self) -> None:
        result = await _forecast(self.hass, self.entry, self.store.entries, 168)
        self._state = result["average"]
        self._attrs = result



class DailyForecastSensor(FishingBaseSensor):
    """7-Tage Prognose als tägliche Durchschnittswerte für das Panel."""
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:calendar-week"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, store) -> None:
        super().__init__(entry, store, "daily_forecast", "Tagesprognose 7 Tage")
        self.hass = hass

    async def async_update(self) -> None:
        result = await _forecast(self.hass, self.entry, self.store.entries, 168)
        points = result.get("points", [])

        # Gruppiere nach Tag und berechne Durchschnitt
        from collections import defaultdict
        daily: dict = defaultdict(list)
        for p in points:
            try:
                dt = datetime.fromisoformat(p["timestamp"])
                day_key = dt.strftime("%Y-%m-%d")
                daily[day_key].append(p["score"])
            except Exception:
                continue

        today = datetime.now().astimezone().strftime("%Y-%m-%d")
        days = []
        for day_key in sorted(daily.keys()):
            scores = daily[day_key]
            avg = round(sum(scores) / len(scores), 1)
            peak = round(max(scores), 1)
            try:
                dt = datetime.fromisoformat(day_key)
                weekday = ["Mo","Di","Mi","Do","Fr","Sa","So"][dt.weekday()]
                date_str = dt.strftime("%d.%m.")
            except Exception:
                weekday = "?"
                date_str = day_key
            days.append({
                "date": day_key,
                "date_str": date_str,
                "weekday": weekday,
                "avg_score": avg,
                "peak_score": peak,
                "is_today": day_key == today,
            })

        self._state = days[0]["avg_score"] if days else 50
        self._attrs = {
            "days": days[:7],
            "best_day": max(days, key=lambda d: d["avg_score"])["date"] if days else None,
        }

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



class IntelligenceSensor(FishingBaseSensor):
    _attr_icon = "mdi:brain"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, store) -> None:
        super().__init__(entry, store, "fishing_intelligence", "Fishing Intelligence")
        self.hass = hass

    async def async_update(self) -> None:
        weather_entity = self.entry.options.get(CONF_WEATHER_ENTITY) or self.entry.data.get(CONF_WEATHER_ENTITY)
        weather = self.hass.states.get(weather_entity)
        attrs = weather.attributes if weather else {}
        moon = _get_moon_state(self.hass, self.entry)
        s = stats(self.store.entries)
        fish_type = self.store.settings.get("fish_type", "Weißfisch")

        score, explanation = smart_fishing_score(
            fish_type=fish_type,
            temperature=_float(attrs.get("temperature"), 12),
            pressure=_float(attrs.get("pressure"), 1015),
            pressure_trend=_float(attrs.get("pressure_trend"), 0),
            wind_speed=_float(attrs.get("wind_speed"), 10),
            wind_bearing=_float(attrs.get("wind_bearing"), None),
            precipitation=_float(attrs.get("precipitation"), 0),
            cloud_coverage=_float(attrs.get("cloud_coverage"), 50),
            humidity=_float(attrs.get("humidity"), None),
            dew_point=_float(attrs.get("dew_point"), None),
            apparent_temperature=_float(attrs.get("apparent_temperature"), None),
            uv_index=_float(attrs.get("uv_index"), None),
            moon_phase=moon.state if moon else None,
            history_score=s.get("history_score", 50),
        )

        self._state = intelligence_recommendation(score, explanation)
        self._attrs = {
            "score": score,
            **explanation,
            "history": s,
        }


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

            if lat is not None and lon is not None:
                catch = {
                    "lat":              lat,
                    "lon":              lon,
                    "timestamp":        item.get("timestamp"),
                    "fish_type":        item.get("fish_type"),
                    "spot":             item.get("spot"),
                    "bait":             item.get("bait"),
                    "length_cm":        item.get("length_cm"),
                    "weight_kg":        item.get("weight_kg"),
                    "water_temp":       item.get("water_temp"),
                    "angelwetter_index":item.get("angelwetter_index"),
                    "photo_url":        item.get("photo_url"),
                    "caught":           item.get("caught", 0),
                    "chance":           item.get("chance"),
                }
                catches.append(catch)

                if int(item.get("caught", 0)) >= 1:
                    # Gewicht proportional zu Fischlänge (größerer Fisch = stärkerer Hotspot)
                    length = float(item.get("length_cm") or 40)
                    weight = min(1.0, max(0.3, length / 80))
                    heatmap.append([lat, lon, weight])

            spot = item.get("spot") or "Unbekannt"
            group = spot_groups.setdefault(spot, {
                "spot": spot, "total": 0, "catches": 0,
                "fish_types": {}, "best_bait": {},
                "lats": [], "lons": [],
            })
            group["total"] += 1
            if item.get("latitude") and item.get("longitude"):
                group["lats"].append(float(item["latitude"]))
                group["lons"].append(float(item["longitude"]))
            if int(item.get("caught", 0)) >= 1:
                group["catches"] += 1
                ft = item.get("fish_type") or "Unbekannt"
                group["fish_types"][ft] = group["fish_types"].get(ft, 0) + 1
                bait = item.get("bait") or "Unbekannt"
                group["best_bait"][bait] = group["best_bait"].get(bait, 0) + 1

        spots = []
        for group in spot_groups.values():
            total    = group["total"]
            catches_count = group["catches"]
            group["success_rate"] = round(catches_count / total * 100, 1) if total else 0
            # GPS-Mittelpunkt des Spots (Median – robuster gegen Ausreißer auf Land)
            if group["lats"]:
                s_lats = sorted(group["lats"])
                s_lons = sorted(group["lons"])
                mid = len(s_lats) // 2
                if len(s_lats) % 2 == 1:
                    group["lat"] = round(s_lats[mid], 6)
                    group["lon"] = round(s_lons[mid], 6)
                else:
                    group["lat"] = round((s_lats[mid-1] + s_lats[mid]) / 2, 6)
                    group["lon"] = round((s_lons[mid-1] + s_lons[mid]) / 2, 6)
            # Top-Fischart und Top-Köder
            if group["fish_types"]:
                group["top_fish"] = max(group["fish_types"], key=group["fish_types"].get)
            if group["best_bait"]:
                group["top_bait"] = max(group["best_bait"], key=group["best_bait"].get)
            # Aufräumen (große Listen nicht in HA-Attrs)
            del group["lats"], group["lons"], group["fish_types"], group["best_bait"]
            spots.append(group)
        spots.sort(key=lambda x: x["catches"], reverse=True)

        self._state = len(self.store.entries)
        # Deeper: direkt aus FishingStore lesen (persistent)
        deeper = None
        deeper_scans = []
        try:
            domain_data = self.hass.data.get("fishing_tracker", {})
            for entry_data in domain_data.values():
                if isinstance(entry_data, dict):
                    if "deeper_result" in entry_data:
                        deeper = entry_data["deeper_result"]
                    # Aus persistentem Store lesen
                    store = entry_data.get("store")
                    if store and hasattr(store, "deeper_scans"):
                        deeper_scans = store.deeper_scans
                    elif "deeper_scans" in entry_data:
                        deeper_scans = entry_data["deeper_scans"]
                    break
        except Exception:
            pass

        # ── Persönliche Lernmuster aus Fang-/Schneider-Historie ──────────────
        personal = {}
        try:
            from . import personal_learning as _pl
            patterns = _pl.compute_personal_patterns(self.store.entries)
            personal = _pl.summarize_for_sensor(patterns)
            # Vollständige Patterns für Frontend-Scoring (kompakt)
            self._full_patterns = patterns
        except Exception:
            self._full_patterns = {}

        self._attrs = {
            "catches": catches[-300:],
            "heatmap": heatmap[-300:],
            "spots": spots,
            "total_entries": len(self.store.entries),
            "deeper_last_result": deeper,
            "deeper_scans": deeper_scans,
            "personal_patterns": personal,
            "personal_full": self._full_patterns,
        }


class AngelwetterIndexSensor(FishingBaseSensor):
    """Allgemeiner Tagesindex – NICHT fischart- oder uhrzeitspezifisch.
    Spiegelt exakt die calcAngelwetterIndex()-Logik aus dem Frontend wider.
    Gewichtung nach IGB Berlin / Guidesly / LAVB Brandenburg:
      35% Wassertemperatur · 30% Wetter · 20% Saison · 10% Mond · 5% Luftdrucktrend
    """
    _attr_icon = "mdi:weather-sunny-alert"
    _attr_native_unit_of_measurement = "%"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, store) -> None:
        super().__init__(entry, store, "angelwetter_index", "Angelwetter Index")
        self.hass = hass

    def _get(self, entity_id: str, default=None):
        s = self.hass.states.get(entity_id)
        if not s or s.state in ("unknown", "unavailable", "None"):
            return default
        try:
            return float(s.state)
        except (ValueError, TypeError):
            return default

    async def async_update(self) -> None:
        from datetime import datetime
        now = datetime.now()
        month = now.month

        # ── 35% Wassertemperatur ─────────────────────────────────────────────
        water_t = (
            self._get("sensor.wassertemperatur_gewaesser")
            or self._get("sensor.haftenkamp_temperatur")
        )
        if water_t is not None:
            wt = water_t
            if 15 <= wt <= 19:   water_score = 100
            elif 13 <= wt <= 21: water_score = 85
            elif 11 <= wt <= 23: water_score = 70
            elif 8 <= wt <= 26:  water_score = 50
            elif 5 <= wt <= 28:  water_score = 30
            else:                water_score = 12
        else:
            water_score = 55  # kein Sensor → neutral

        # ── 30% Wetter ───────────────────────────────────────────────────────
        # Lokale Station hat Priorität
        cloud = (self._get("sensor.haftenkamp_bewolkungsgrad")
                 or self._get("weather.home", None) and None)  # via attributes unten
        wind  = (self._get("sensor.haftenkamp_windgeschwindigkeit")
                 or None)
        rain  = (self._get("sensor.haftenkamp_niederschlag") or 0)
        bear  = self._get("sensor.haftenkamp_windrichtung")

        # Fallback: weather.home attributes
        wa = (self.hass.states.get("weather.home") or type("x", (), {"attributes": {}})()).attributes
        if cloud is None: cloud = float(wa.get("cloud_coverage", 50) or 50)
        if wind  is None: wind  = float(wa.get("wind_speed", 10) or 10)
        if bear  is None: bear  = float(wa.get("wind_bearing", 0) or 0)

        weather_score = 40
        # Bewölkung
        if 50 <= cloud <= 80:       weather_score += 22
        elif 35 <= cloud < 50:      weather_score += 16
        elif 80 < cloud <= 95:      weather_score += 12
        elif 20 < cloud < 35:       weather_score += 5
        elif cloud > 95:            weather_score += 4
        else:                       weather_score -= 10  # Knallsonne
        # Wind
        if 8 <= wind <= 15:         weather_score += 18
        elif 15 < wind <= 22:       weather_score += 12
        elif 4 <= wind < 8:         weather_score += 8
        elif wind > 35:             weather_score -= 20
        elif wind < 3:              weather_score -= 5
        # Windrichtung SW/W günstig
        if 180 <= bear <= 270:      weather_score += 10
        elif 270 < bear <= 315:     weather_score += 6
        elif 0 <= bear <= 60:       weather_score -= 6
        # Niederschlag
        if 0.3 <= rain <= 1.5:      weather_score += 12
        elif 1.5 < rain <= 3:       weather_score += 6
        elif 0 < rain < 0.3:        weather_score += 4
        elif rain > 8:              weather_score -= 20
        elif 3 < rain <= 8:         weather_score -= 5
        # Sonneneinstrahlung
        solar = self._get("sensor.haftenkamp_sonneneinstrahlung")
        if solar is not None:
            if solar < 50:          weather_score += 8
            elif solar < 200:       weather_score += 4
            elif solar < 500:       pass
            elif solar < 800:       weather_score -= 6
            else:                   weather_score -= 12
        weather_score = max(0, min(100, weather_score))

        # ── 20% Saison ───────────────────────────────────────────────────────
        if month in (5, 6):     season_score = 100
        elif month in (9, 10):  season_score = 95
        elif month == 4:        season_score = 88
        elif month in (7, 8):   season_score = 70
        elif month in (3, 11):  season_score = 65
        elif month == 2:        season_score = 45
        else:                   season_score = 30

        # ── 10% Mondphase ─────────────────────────────────────────────────────
        moon_s = self.hass.states.get("sensor.moon")
        moon_state = (moon_s.state if moon_s else "").lower()
        if any(x in moon_state for x in ("voll", "full")):       moon_score = 100
        elif any(x in moon_state for x in ("neu", "new")):       moon_score = 95
        elif any(x in moon_state for x in ("gibbous", "dreiv")): moon_score = 75
        elif any(x in moon_state for x in ("quarter", "viert")): moon_score = 60
        else:                                                      moon_score = 50

        # ── 5% Luftdrucktrend ─────────────────────────────────────────────────
        trend = self._get("sensor.fishing_tracker_pressure_trend", 0) or 0
        if -2 <= trend < -1:       pressure_score = 100
        elif -3 <= trend < -2:     pressure_score = 90
        elif -1 <= trend < -0.3:   pressure_score = 75
        elif -0.3 <= trend <= 0.5: pressure_score = 55
        elif 0.5 < trend <= 1.5:   pressure_score = 40
        elif 1.5 < trend <= 3:     pressure_score = 25
        else:                       pressure_score = 12

        # ── Gesamtscore ───────────────────────────────────────────────────────
        total = (
            water_score   * 0.35 +
            weather_score * 0.30 +
            season_score  * 0.20 +
            moon_score    * 0.10 +
            pressure_score * 0.05
        )
        score = int(max(5, min(99, round(total))))

        if score >= 75:   level = "Sehr gut"
        elif score >= 55: level = "Gut"
        elif score >= 35: level = "Mittel"
        else:             level = "Schwach"

        self._state = score
        self._attrs = {
            "level":          level,
            "water_score":    round(water_score, 1),
            "weather_score":  round(weather_score, 1),
            "season_score":   season_score,
            "moon_score":     moon_score,
            "pressure_score": pressure_score,
            "water_temp":     water_t,
            "cloud":          round(cloud, 1),
            "wind":           round(wind, 1),
            "rain":           rain,
            "month":          month,
        }


class HistorySensor(FishingBaseSensor):
    _attr_icon = "mdi:format-list-bulleted"

    def __init__(self, entry: ConfigEntry, store) -> None:
        super().__init__(entry, store, "history", "Fanghistorie")

    async def async_update(self) -> None:
        try:
          entries = list(self.store.entries)
        except Exception:
          entries = []
        latest = list(reversed(entries))[:20]
        s = stats(entries)

        def _caught(e):
            try: return int(e.get("caught") or 0) >= 1
            except (ValueError, TypeError): return False

        # Echte Fänge (caught=1)
        real_catches = [e for e in entries if _caught(e)]

        # Fänge nach Art
        by_fish: dict[str, int] = {}
        for e in real_catches:
            ft = e.get("fish_type") or "Unbekannt"
            by_fish[ft] = by_fish.get(ft, 0) + 1
        fish_ranking = sorted(by_fish.items(), key=lambda x: x[1], reverse=True)

        # Fänge pro Monat (laufendes Jahr)
        monthly = [0] * 12
        for e in real_catches:
            try:
                m = int(e.get("timestamp", "")[:7].split("-")[1]) - 1
                monthly[m] += 1
            except Exception:
                pass

        # Gesamtgewicht
        total_weight = sum(
            float(e.get("weight_kg") or 0) for e in real_catches if e.get("weight_kg")
        )
        avg_weight = total_weight / len(real_catches) if real_catches else 0

        # Schlanke Einträge fürs Fangbuch (nur Display-Felder → HA 16KB Limit)
        display_fields = ["timestamp","fish_type","caught","spot","bait",
                          "length_cm","weight_kg","photo_url","latitude","longitude",
                          "angelwetter_index","water_temp","notes","angler"]
        try:
            catches_display = [
                {k: e.get(k) for k in display_fields}
                for e in reversed(list(entries))
                if _caught(e)
            ][:50]
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("catches_display Fehler: %s", exc)
            catches_display = []

        self._state = f"{len(entries)} Einträge"
        self._attrs = {
            "entries":       catches_display,   # nur Fänge, schlanke Felder
            "latest":        latest,
            "total":         len(entries),
            "total_catches": len(real_catches),
            "total_weight_kg": round(total_weight, 2),
            "avg_weight_kg":   round(avg_weight, 2),
            "fish_ranking":  [{"fish": f, "count": c} for f, c in fish_ranking],
            "monthly":       monthly,
            "success_rate":  s.get("success_rate"),
            "avg_length_cm": s.get("avg_length_cm"),
            "max_length_cm": s.get("max_length_cm"),
            "daily_chart":   s.get("daily_chart"),
        }


class SpotAnalysisSensor(FishingBaseSensor):
    _attr_icon = "mdi:map-marker-star"

    def __init__(self, entry: ConfigEntry, store) -> None:
        super().__init__(entry, store, "spot_analysis", "Spot Analyse")

    async def async_update(self) -> None:
        s = stats(self.store.entries)
        top = s.get("top_spot", {})
        self._state = top.get("name", "Keine Daten")
        self._attrs = {"top_spot": top, "ranking": s.get("spot_ranking", [])}


class BaitAnalysisSensor(FishingBaseSensor):
    _attr_icon = "mdi:hook"

    def __init__(self, entry: ConfigEntry, store) -> None:
        super().__init__(entry, store, "bait_analysis", "Köder Analyse")

    async def async_update(self) -> None:
        s = stats(self.store.entries)
        top = s.get("top_bait", {})
        self._state = top.get("name", "Keine Daten")
        self._attrs = {"top_bait": top, "ranking": s.get("bait_ranking", [])}


class TimeAnalysisSensor(FishingBaseSensor):
    _attr_icon = "mdi:clock-star-four-points-outline"

    def __init__(self, entry: ConfigEntry, store) -> None:
        super().__init__(entry, store, "time_analysis", "Zeit Analyse")

    async def async_update(self) -> None:
        s = stats(self.store.entries)
        top = s.get("top_hour", {})
        name = top.get("name", "Keine Daten")
        if name not in ("Keine Daten", "Unbekannt", None):
            try:
                name = f"{int(name):02d}:00"
            except Exception:
                pass
        self._state = name
        self._attrs = {"top_hour": top, "time_chart": s.get("time_chart", [])}


class LastCatchSensor(FishingBaseSensor):
    _attr_icon = "mdi:fishbowl"

    def __init__(self, entry: ConfigEntry, store) -> None:
        super().__init__(entry, store, "last_catch", "Letzter Fang")

    async def async_update(self) -> None:
        entries = [e for e in self.store.entries if int(e.get("caught", 0)) >= 1]
        if not entries:
            self._state = "Keine Daten"
            self._attrs = {}
            return

        last = entries[-1]
        text = f"{last.get('fish_type', 'Fisch')} · {last.get('spot', '-')}"
        self._state = text[:255]
        self._attrs = last



class SpeciesRankingSensor(FishingBaseSensor):
    _attr_icon = "mdi:podium-gold"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, store) -> None:
        super().__init__(entry, store, "species_ranking", "Fischarten Ranking")
        self.hass = hass

    async def async_update(self) -> None:
        weather_entity = self.entry.options.get(CONF_WEATHER_ENTITY) or self.entry.data.get(CONF_WEATHER_ENTITY)
        weather = self.hass.states.get(weather_entity)
        attrs = weather.attributes if weather else {}
        attrs = await _async_weather_context(self.hass, self.entry, attrs)

        moon = _get_moon_state(self.hass, self.entry)
        s = stats(self.store.entries)

        ranking = rank_species(
            weather=attrs,
            history_score=s.get("history_score", 50),
            moon_phase=moon.state if moon else None,
        )

        best = ranking[0] if ranking else {}
        self._state = f"{best.get('fish_type', 'Keine Daten')} · {best.get('score', '--')}%"
        self._attrs = {
            "ranking": ranking,
            "best": best,
            "weather_source": attrs.get("weather_source", "home_assistant"),
            "fetched_at": attrs.get("fetched_at"),
        }


async def _async_weather_context(hass: HomeAssistant, entry: ConfigEntry, fallback_attrs: dict[str, Any] | None = None) -> dict[str, Any]:
    fallback_attrs = fallback_attrs or {}
    use_online = entry.options.get(CONF_USE_ONLINE_WEATHER, entry.data.get(CONF_USE_ONLINE_WEATHER, True))

    if not use_online:
        return fallback_attrs

    person_entity = entry.options.get(CONF_PERSON_ENTITY) or entry.data.get(CONF_PERSON_ENTITY)
    person_state = hass.states.get(person_entity) if person_entity else None
    person_attrs = person_state.attributes if person_state else {}

    lat = person_attrs.get("latitude")
    lon = person_attrs.get("longitude")

    if lat is None or lon is None:
        return fallback_attrs

    try:
        engine = hass.data[DOMAIN][entry.entry_id].get("weather_engine")
        if engine is None:
            return fallback_attrs
        weather = await engine.async_get_weather(float(lat), float(lon))
        if weather is None:
            return fallback_attrs

        data = weather.as_dict()
        return {
            "temperature": data.get("temperature", fallback_attrs.get("temperature")),
            "pressure": data.get("pressure", fallback_attrs.get("pressure")),
            "pressure_trend": data.get("pressure_trend", fallback_attrs.get("pressure_trend", 0)),
            "wind_speed": data.get("wind_speed", fallback_attrs.get("wind_speed")),
            "wind_bearing": data.get("wind_bearing", fallback_attrs.get("wind_bearing")),
            "wind_gusts": data.get("wind_gusts"),
            "precipitation": data.get("precipitation", fallback_attrs.get("precipitation")),
            "precipitation_probability": data.get("precipitation_probability"),
            "cloud_coverage": data.get("cloud_coverage", fallback_attrs.get("cloud_coverage")),
            "humidity": data.get("humidity", fallback_attrs.get("humidity")),
            "dew_point": data.get("dew_point", fallback_attrs.get("dew_point")),
            "uv_index": data.get("uv_index", fallback_attrs.get("uv_index")),
            "sunrise": data.get("sunrise"),
            "sunset": data.get("sunset"),
            "hourly": data.get("hourly"),
            "weather_source": data.get("source"),
            "fetched_at": data.get("fetched_at"),
        }
    except Exception:
        return fallback_attrs




class AdvancedIntelligenceSensor(FishingBaseSensor):
    _attr_icon = "mdi:brain"

    def __init__(self, entry: ConfigEntry, store) -> None:
        super().__init__(entry, store, "advanced_intelligence", "Advanced Intelligence")

    async def async_update(self) -> None:
        analysis = advanced_analysis(self.store.entries)
        strategy = analysis.get("strategy", {})
        plan = strategy.get("primary_plan", [])
        self._state = plan[0][:255] if plan else "Keine Daten"
        self._attrs = analysis


class OnlineWeatherStatusSensor(FishingBaseSensor):
    _attr_icon = "mdi:weather-cloudy-clock"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, store) -> None:
        super().__init__(entry, store, "online_weather_status", "Online Wetterstatus")
        self.hass = hass

    async def async_update(self) -> None:
        weather_entity = self.entry.options.get(CONF_WEATHER_ENTITY) or self.entry.data.get(CONF_WEATHER_ENTITY)
        weather = self.hass.states.get(weather_entity)
        attrs = weather.attributes if weather else {}
        attrs = await _async_weather_context(self.hass, self.entry, attrs)

        self._state = attrs.get("weather_source", "home_assistant")
        self._attrs = {
            "source": attrs.get("weather_source", "home_assistant"),
            "fetched_at": attrs.get("fetched_at"),
            "temperature": attrs.get("temperature"),
            "pressure": attrs.get("pressure"),
            "pressure_trend": attrs.get("pressure_trend"),
            "wind_speed": attrs.get("wind_speed"),
            "wind_bearing": attrs.get("wind_bearing"),
            "wind_gusts": attrs.get("wind_gusts"),
            "precipitation": attrs.get("precipitation"),
            "precipitation_probability": attrs.get("precipitation_probability"),
            "cloud_coverage": attrs.get("cloud_coverage"),
            "humidity": attrs.get("humidity"),
            "dew_point": attrs.get("dew_point"),
            "uv_index": attrs.get("uv_index"),
            "sunrise": attrs.get("sunrise"),
            "sunset": attrs.get("sunset"),
        }


def self_or_entry_fish_type(entry: ConfigEntry, entries: list[dict[str, Any]]) -> str:
    # Fallback for forecasts before store context is available here.
    if entries:
        last = entries[-1].get("fish_type")
        if last:
            return last
    return "Weißfisch"


async def _forecast(hass: HomeAssistant, entry: ConfigEntry, entries: list[dict[str, Any]], hours: int) -> dict[str, Any]:
    weather_entity = entry.options.get(CONF_WEATHER_ENTITY) or entry.data.get(CONF_WEATHER_ENTITY)
    weather = hass.states.get(weather_entity)
    attrs = weather.attributes if weather else {}
    attrs = await _async_weather_context(hass, entry, attrs)
    s = stats(entries)

    # Stündliche Wettervorhersage aus HA
    hourly_forecast = attrs.get("forecast") or (weather.attributes.get("forecast") if weather else None) or []

    moon = _get_moon_state(hass, entry)
    points = bite_forecast_series(
        temperature=_float(attrs.get("temperature"), 12),
        wind_speed=_float(attrs.get("wind_speed"), 10),
        pressure=_float(attrs.get("pressure"), 1015),
        cloud_coverage=_float(attrs.get("cloud_coverage"), 50),
        precipitation=_float(attrs.get("precipitation"), 0),
        history_score=s.get("history_score", 50),
        hours=hours,
        moon_phase=moon.state if moon else None,
        entries=entries,
        fish_type=self_or_entry_fish_type(entry, entries),
        humidity=_float(attrs.get("humidity"), None),
        dew_point=_float(attrs.get("dew_point"), None),
        apparent_temperature=_float(attrs.get("apparent_temperature"), None),
        uv_index=_float(attrs.get("uv_index"), None),
        wind_bearing=_float(attrs.get("wind_bearing"), None),
        hourly_forecast=hourly_forecast,
    )

    values = [p["score"] for p in points]
    best = max(points, key=lambda p: p["score"]) if points else {}
    return {
        "current": values[0] if values else 50,
        "average": round(sum(values) / len(values), 1) if values else 50,
        "best_score": best.get("score"),
        "best_time": best.get("timestamp"),
        "points": points,
        "note": "v2.5.0 nutzt Live-Wetterdaten, Fischprofile, Fischarten-Ranking, Mondphase, Fanghistorie und unregelmäßige Bite-Windows.",
    }


async def _calculate_best_time(hass: HomeAssistant, entry: ConfigEntry, entries: list[dict[str, Any]]) -> dict[str, Any]:
    result = await _forecast(hass, entry, entries, 24)
    best_time = "--:--"
    best_dt = datetime.now().astimezone()
    best_score = result.get("best_score", 50)

    if result.get("best_time"):
        try:
            best_dt = datetime.fromisoformat(result["best_time"])
            best_time = best_dt.strftime("%H:%M")
        except Exception:
            pass

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
        "tagesprognose": result.get("points", []),
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


def _score_for_hour(hass: HomeAssistant, entry: ConfigEntry, entries: list[dict[str, Any]], attrs: dict[str, Any], ts: datetime) -> int:
    s = stats(entries)
    moon = _get_moon_state(hass, entry)
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


def _get_moon_state(hass: HomeAssistant, entry: ConfigEntry):
    moon_entity = (
        entry.options.get(CONF_MOON_ENTITY)
        or entry.data.get(CONF_MOON_ENTITY)
        or "sensor.moon_phase"
    )

    moon = hass.states.get(moon_entity)
    if moon is not None:
        return moon

    # Fallbacks for common Home Assistant installations.
    return hass.states.get("sensor.moon") or hass.states.get("sensor.moon_phase")


def _float(value: Any, default: Any = 0.0) -> Any:
    try:
        if value in (None, "", "unknown", "unavailable"):
            return default
        return float(value)
    except Exception:
        return default


# ── Solunar Sensor ────────────────────────────────────────────────────────────

class SolunarSensor(SensorEntity):
    """Berechnet Solunar-Haupt- und Nebenbeißzeiten für heute."""

    _attr_icon = "mdi:moon-waxing-crescent"
    _attr_has_entity_name = True
    _attr_name = "Solunar Beißzeiten"
    _attr_should_poll = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_solunar"
        self._state: str = "Berechnung..."
        self._attrs: dict[str, Any] = {}

    @property
    def native_value(self) -> str:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attrs

    async def async_update(self) -> None:
        lat = (
            entry_val(self.entry, CONF_LATITUDE)
            or self.hass.config.latitude
        )
        lon = (
            entry_val(self.entry, CONF_LONGITUDE)
            or self.hass.config.longitude
        )

        try:
            now = datetime.now().astimezone()
            sol = solunar_times(now, float(lat), float(lon))
            self._state = sol.get("quality", "–")
            self._attrs = sol
        except Exception:
            self._state = "Fehler"
            self._attrs = {}


# ── Water Temperature Detail Sensor ──────────────────────────────────────────

class WaterTempDetailSensor(SensorEntity):
    """Wassertemperatur von wassertemperatur.site mit O₂-Wert."""

    _attr_icon = "mdi:thermometer-water"
    _attr_has_entity_name = True
    _attr_name = "Wassertemperatur (Gewässer)"
    _attr_native_unit_of_measurement = "°C"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_should_poll = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_water_temp_detail"
        self._state: float | None = None
        self._attrs: dict[str, Any] = {}

    @property
    def native_value(self) -> float | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attrs

    async def async_update(self) -> None:
        engine: WaterTemperatureEngine | None = (
            self.hass.data.get(DOMAIN, {})
            .get(self.entry.entry_id, {})
            .get("water_temp_engine")
        )
        if engine is None:
            return

        # Lufttemperatur für Schätzung holen
        weather_entity = entry_val(self.entry, CONF_WEATHER_ENTITY) or "weather.home"
        ws = self.hass.states.get(weather_entity)
        air_temp = _float(ws.attributes.get("temperature"), None) if ws else None

        now = datetime.now().astimezone()
        data = await engine.async_get_water_temperature(
            air_temp=air_temp, month=now.month
        )

        self._state = data.get("temp")
        self._attrs = data


# ── Spawning Sensor ───────────────────────────────────────────────────────────

class SpawningSensor(SensorEntity):
    """Zeigt aktuelle Laichstatus aller Fischarten an."""

    _attr_icon = "mdi:fish"
    _attr_has_entity_name = True
    _attr_name = "Laichzeiten Status"
    _attr_should_poll = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_spawning"
        self._state: str = "–"
        self._attrs: dict[str, Any] = {}

    @property
    def native_value(self) -> str:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attrs

    async def async_update(self) -> None:
        now = datetime.now().astimezone()
        try:
            status = spawning_status(now.month, now.day)
            spawning_now = [s["fish"] for s in status if s["phase"] == "main"]
            pre_post = [s["fish"] for s in status if s["phase"] in ("pre", "post")]
            self._state = (
                f"Laichzeit: {', '.join(spawning_now)}" if spawning_now
                else "Keine Hauptlaichzeit"
            )
            self._attrs = {
                "month": now.month,
                "spawning_main": spawning_now,
                "spawning_pre_post": pre_post,
                "all_species": status,
            }
        except Exception:
            self._state = "Fehler"
            self._attrs = {}


def entry_val(entry: ConfigEntry, key: str, default: Any = None) -> Any:
    """Liest Wert aus entry.options (bevorzugt) oder entry.data."""
    return entry.options.get(key) or entry.data.get(key) or default


# ── Water Level Sensor (Pegelonline) ─────────────────────────────────────────

class WaterLevelSensor(SensorEntity):
    """Pegelstand von PEGELONLINE (WSV) – Wasserstand + Trübung."""

    _attr_icon = "mdi:waves"
    _attr_has_entity_name = True
    _attr_name = "Pegelstand"
    _attr_native_unit_of_measurement = "cm"
    _attr_should_poll = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_water_level"
        self._state: float | None = None
        self._attrs: dict[str, Any] = {}

    @property
    def native_value(self) -> float | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attrs

    async def async_update(self) -> None:
        engine: WaterLevelEngine | None = (
            self.hass.data.get(DOMAIN, {})
            .get(self.entry.entry_id, {})
            .get("water_level_engine")
        )
        if engine is None:
            return
        data = await engine.async_get_water_level()
        self._state = data.get("value_cm")
        self._attrs = data


# ── Bait Advisor Sensor (Wettermethode + Saisonal) ───────────────────────────

class BaitAdvisorSensor(SensorEntity):
    """Köderfarben-Empfehlung basierend auf Wettermethode + aktuellen Bedingungen."""

    _attr_icon = "mdi:hook"
    _attr_has_entity_name = True
    _attr_name = "Köderempfehlung"
    _attr_should_poll = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_bait_advisor"
        self._state: str = "–"
        self._attrs: dict[str, Any] = {}

    @property
    def native_value(self) -> str:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attrs

    async def async_update(self) -> None:
        now = datetime.now().astimezone()

        # Wetterdaten holen
        weather_entity = entry_val(self.entry, CONF_WEATHER_ENTITY) or "weather.home"
        ws = self.hass.states.get(weather_entity)
        attrs = ws.attributes if ws else {}
        cloud = _float(attrs.get("cloud_coverage"), 50.0)
        precip = _float(attrs.get("precipitation"), 0.0)
        uv = _float(attrs.get("uv_index"), None)

        # Pegeltrübung (wenn vorhanden)
        level_engine: WaterLevelEngine | None = (
            self.hass.data.get(DOMAIN, {})
            .get(self.entry.entry_id, {})
            .get("water_level_engine")
        )
        turb_ntu = None
        if level_engine:
            level_data = await level_engine.async_get_water_level()
            turb_ntu = level_data.get("turbidity_ntu")

        # Trübungsstufe bestimmen
        if turb_ntu is not None:
            if turb_ntu < 5:
                turb_level = "klar"
            elif turb_ntu < 20:
                turb_level = "leicht_trüb"
            elif turb_ntu < 100:
                turb_level = "trüb"
            else:
                turb_level = "sehr_trüb"
        elif precip > 10:
            turb_level = "sehr_trüb"
        elif precip > 3:
            turb_level = "trüb"
        elif precip > 0.5:
            turb_level = "leicht_trüb"
        else:
            turb_level = "klar"

        # Zielfischart aus Settings
        data_store = self.hass.data.get(DOMAIN, {}).get(self.entry.entry_id, {})
        store = data_store.get("store")
        fish_type = "Zander"
        if store and hasattr(store, "settings"):
            fish_type = store.settings.get("fish_type", "Zander")

        try:
            rec = full_bait_recommendation(
                fish_type=fish_type,
                cloud_coverage=cloud,
                turbidity_level=turb_level,
                hour=now.hour,
                month=now.month,
                uv_index=uv,
            )
            self._state = rec.get("farbe", "Naturfarben")
            self._attrs = {
                **rec,
                "fish_type": fish_type,
                "turbidity_level": turb_level,
                "turbidity_ntu": turb_ntu,
                "cloud_coverage": cloud,
                "hour": now.hour,
                "month": now.month,
            }
        except Exception:
            self._state = "Naturfarben"
            self._attrs = {}



class ConsolidatedForecastSensor(SensorEntity):
    """Aggregates forecasts from all available weather entities into one consolidated forecast.

    Calls weather.get_forecasts service for each weather.* entity periodically,
    means numeric fields across sources, and exposes the result as `forecast` attribute.

    This replaces the deprecated weather.xxx.attributes.forecast pattern.
    """

    _attr_has_entity_name = False
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry
        self._attr_name = "Consolidated Forecast"
        self._attr_unique_id = f"{entry.entry_id}_consolidated_forecast"
        self._state: int = 0
        self._attrs: dict[str, Any] = {"forecast": [], "sources_active": [], "agreement_score": 100.0}
        self._unsub = None

    async def async_added_to_hass(self) -> None:
        from homeassistant.helpers.event import async_track_time_interval
        # initial fetch
        await self._async_update_now()
        # periodic refresh every 30 min
        self._unsub = async_track_time_interval(
            self.hass, self._async_periodic, timedelta(minutes=30)
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    async def _async_periodic(self, _now) -> None:
        await self._async_update_now()

    async def _async_update_now(self) -> None:
        try:
            # Configured override list (optional), else auto-discover
            cfg = self.entry.options.get("forecast_entities") or self.entry.data.get("forecast_entities")
            entity_ids = cfg if isinstance(cfg, list) and cfg else None
            result = await get_consolidated_forecast(self.hass, entity_ids, forecast_type="hourly")
            self._state = len(result.get("sources_active") or [])
            self._attrs = result
        except Exception as err:  # noqa: BLE001
            self._state = 0
            self._attrs = {"forecast": [], "sources_active": [], "error": str(err)}
        self.async_write_ha_state()

    @property
    def native_value(self) -> int:
        return self._state

    @property
    def native_unit_of_measurement(self) -> str | None:
        return "sources"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attrs

    @property
    def icon(self) -> str:
        return "mdi:weather-cloudy-arrow-right"

class ForecastAccuracySensor(FishingBaseSensor):
    """Backtest: misst Treffsicherheit der Vorhersage gegen tatsächliche Fänge.

    Aus allen gespeicherten Entries (Fang oder Schneider) wird die Kalibrierung
    der ehemaligen Vorhersage (chance) ausgewertet:
    - Buckets nach Vorhersage-Score
    - Hit-Rate pro Bucket = Anteil mit caught>=1
    - Overall Accuracy = wie gut korreliert hohe Vorhersage mit Fang
    """

    def __init__(self, entry: ConfigEntry, store):
        super().__init__(entry, store, "forecast_accuracy", "Forecast Accuracy")
        self._attr_icon = "mdi:target-arrow"
        self._attr_native_unit_of_measurement = PERCENTAGE

    def _compute(self) -> tuple[Any, dict[str, Any]]:
        entries = list(self.store.entries or [])
        # Nur Entries mit valider chance + caught-Feld
        valid = [e for e in entries if isinstance(e.get("chance"), (int, float))
                                    and isinstance(e.get("caught"), (int, float))]
        if len(valid) < 3:
            return None, {
                "status": "Zu wenig Daten — mindestens 3 Sessions nötig",
                "entries_total": len(entries),
                "entries_valid": len(valid),
                "buckets": [],
                "overall_accuracy": None,
            }
        # Buckets
        buckets = [
            {"label": "0-25%",  "range": (0, 25),  "n": 0, "hits": 0},
            {"label": "25-50%", "range": (25, 50), "n": 0, "hits": 0},
            {"label": "50-75%", "range": (50, 75), "n": 0, "hits": 0},
            {"label": "75-100%","range": (75, 101),"n": 0, "hits": 0},
        ]
        for e in valid:
            c = float(e.get("chance", 0))
            caught = float(e.get("caught", 0))
            for b in buckets:
                if b["range"][0] <= c < b["range"][1]:
                    b["n"] += 1
                    if caught >= 1:
                        b["hits"] += 1
                    break
        for b in buckets:
            b["hit_rate"] = round(100 * b["hits"] / b["n"], 1) if b["n"] > 0 else None
        # Overall: gewichtete Kalibrierungs-Score (näher an monotonem Anstieg = besser)
        # Erwartung: hit_rate steigt mit bucket — wir bewerten als Korrelation chance vs caught
        try:
            n = len(valid)
            chances = [float(e["chance"]) for e in valid]
            outcomes = [1.0 if float(e["caught"]) >= 1 else 0.0 for e in valid]
            mean_c = sum(chances) / n
            mean_o = sum(outcomes) / n
            num = sum((chances[i] - mean_c) * (outcomes[i] - mean_o) for i in range(n))
            den_c = (sum((c - mean_c) ** 2 for c in chances)) ** 0.5
            den_o = (sum((o - mean_o) ** 2 for o in outcomes)) ** 0.5
            corr = num / (den_c * den_o) if (den_c * den_o) > 0 else 0
            # Skaliere [-1, 1] auf [0, 100]
            overall = round(50 + corr * 50, 1)
        except Exception:
            overall = None
        return overall, {
            "buckets": buckets,
            "entries_valid": len(valid),
            "entries_total": len(entries),
            "overall_accuracy": overall,
            "method": "Pearson-Korrelation Vorhersage vs. tatsächlicher Fang (50=zufällig, 100=perfekt)",
            "status": "OK" if overall is not None else "Berechnung fehlgeschlagen",
        }

    def update(self) -> None:
        state, attrs = self._compute()
        self._state = state
        self._attrs = attrs


# ── NLWKN Wassertemperatur-Sensor (v2.35) ─────────────────────────────────────
# Bezieht echte Wassertemperatur von NLWKN Gewässergüte-Messstationen
# Default: Station 2004 (Laar / Vechte) - die einzige kontinuierlich überwachte
# Vechte-Station. Update alle 15min (entspricht NLWKN-Messintervall).
class NlwknWaterTempSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "NLWKN Wassertemperatur"
    _attr_icon = "mdi:water-thermometer"
    _attr_native_unit_of_measurement = "°C"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_should_poll = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_nlwkn_water_temp"
        self.entity_id = "sensor.fishing_tracker_nlwkn_water_temp"
        self._state: float | None = None
        self._attrs: dict[str, Any] = {}
        # Engine lazy initialisieren
        self._engine: NlwknWaterTempEngine | None = None
        # Update-Intervall: 15min (NLWKN misst alle 15min)
        self._last_update: datetime | None = None
        self._min_interval = timedelta(minutes=15)

    @property
    def native_value(self) -> float | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attrs

    async def async_update(self) -> None:
        # Throttle: höchstens alle 15 min wirklich abfragen
        now = datetime.now()
        if self._last_update and (now - self._last_update) < self._min_interval and self._state is not None:
            return

        if self._engine is None:
            self._engine = NlwknWaterTempEngine(self.hass)
            # Optional konfigurierbar — Default ist Laar (2004) für Vechte
            try:
                station_id = self.entry.options.get("nlwkn_station_id") or self.entry.data.get("nlwkn_station_id")
                if station_id:
                    self._engine.set_station(station_id)
            except Exception:  # noqa: BLE001
                pass

        data = await self._engine.async_get()
        if data is None:
            # Keine Daten — bisherigen State behalten, Status-Attribut setzen
            self._attrs = {
                "status": "Keine Daten von NLWKN",
                "station_id": self._engine.station_id,
                "station_name": self._engine.station_info.get("name", "?"),
                "river": self._engine.station_info.get("river", "?"),
            }
            return

        self._state = data["temp"]
        self._attrs = {
            "measurement_time": data["timestamp"],
            "station_id": data["station_id"],
            "station_name": data["station_name"],
            "river": data["river"],
            "source": data["source"],
            "url": data["url"],
            "status": "OK",
        }
        self._last_update = now
