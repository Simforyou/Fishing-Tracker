from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import json as _json
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


SERVICE_DELETE_CATCH    = "delete_catch"
SERVICE_ANALYZE_DEEPER  = "analyze_deeper_image"

SERVICE_ANALYZE_SCHEMA = vol.Schema({
    vol.Required("image_data"):      cv.string,
    vol.Required("api_key"):         cv.string,
    vol.Optional("image_type",       default="image/jpeg"): cv.string,
    vol.Optional("scan_name",        default="Scan"): cv.string,
    # Neue corner-basierte Georeferenzierung
    vol.Optional("corner_tl_lat",    default=0.0): vol.Coerce(float),
    vol.Optional("corner_tl_lon",    default=0.0): vol.Coerce(float),
    vol.Optional("corner_br_lat",    default=0.0): vol.Coerce(float),
    vol.Optional("corner_br_lon",    default=0.0): vol.Coerce(float),
    vol.Optional("image_data_url",   default=""): cv.string,
    vol.Optional("image_bounds",     default=""): cv.string,
    # Alt (rückwärtskompatibel)
    vol.Optional("ref_blue_xp",      default=0.0): vol.Coerce(float),
    vol.Optional("ref_blue_yp",      default=0.0): vol.Coerce(float),
    vol.Optional("ref_red_xp",       default=100.0): vol.Coerce(float),
    vol.Optional("ref_red_yp",       default=0.0): vol.Coerce(float),
    vol.Optional("ref_blue_lat",     default=0.0): vol.Coerce(float),
    vol.Optional("ref_blue_lon",     default=0.0): vol.Coerce(float),
    vol.Optional("ref_red_lat",      default=0.0): vol.Coerce(float),
    vol.Optional("ref_red_lon",      default=0.0): vol.Coerce(float),
})
SERVICE_DELETE_SCHEMA = vol.Schema({
    vol.Required("timestamp"): cv.string,
})

SERVICE_LOG_SCHEMA = vol.Schema({
    vol.Optional("fish_type"): cv.string,
    vol.Optional("spot"): cv.string,
    vol.Optional("bait"): cv.string,
    vol.Optional("method"): cv.string,
    vol.Optional("target_fish"): vol.Any([cv.string], cv.string),
    vol.Optional("length_cm"): vol.Any(cv.string, vol.Coerce(float)),
    vol.Optional("weight_kg"): vol.Any(cv.string, vol.Coerce(float)),
    vol.Optional("angler"): cv.string,
    vol.Optional("latitude"): vol.Coerce(float),
    vol.Optional("longitude"): vol.Coerce(float),
    vol.Optional("notes", default=""): cv.string,
    vol.Optional("photo_data"): cv.string,       # base64 JPEG
    vol.Optional("water_temp"): vol.Coerce(float),
    vol.Optional("temperature"): vol.Coerce(float),
    vol.Optional("wind_speed"): vol.Coerce(float),
    vol.Optional("wind_gusts"): vol.Coerce(float),
    vol.Optional("wind_bearing"): vol.Coerce(float),
    vol.Optional("pressure"): vol.Coerce(float),
    vol.Optional("cloud_coverage"): vol.Coerce(float),
    vol.Optional("humidity"): vol.Coerce(float),
    vol.Optional("solar_radiation"): vol.Coerce(float),
    vol.Optional("angelwetter_index"): vol.Coerce(int),
    vol.Optional("catch_datetime"): cv.string,  # ISO: "2026-05-16T11:30"
}, extra=vol.ALLOW_EXTRA)

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
    # Default: Vechte (für User in Grafschaft Bentheim / Niedergrafschaft).
    # Lässt sich über das Config-Flow überschreiben (jedes Gewässer auf wassertemperatur.site).
    if not water_temp_url:
        water_temp_url = "https://wassertemperatur.site/flusse/water-temp-in-vechte"
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
        "deeper_scans": store.deeper_scans,  # aus persistentem Store geladen
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_log_catch(call: ServiceCall) -> None:
        await async_log_entry(hass, entry, 1, dict(call.data))

    async def handle_analyze_deeper(call: ServiceCall) -> None:
        """Anthropic Vision API vom HA-Server aufrufen (umgeht iOS CORS-Blocks)."""
        import aiohttp
        image_data = call.data["image_data"]
        api_key    = call.data["api_key"]
        img_type   = call.data.get("image_type", "image/jpeg")

        prompt = (
            "Du analysierst einen Fish Deeper Echolot-Screenshot einer Gewässertiefenkarte.\n\n"

            "Die Karte zeigt Tiefenzonen durch Farben.\n"
            "Die Deeper App nutzt typisch diese Farbskala (von flach → tief):\n"
            "Weiß/sehr hell → Hellblau → Mittelblau → Blau-lila → Lila/Violett → Pink/Rosa → Rot/Dunkelrot\n"
            "Die tiefsten Stellen sind oft PINK oder ROT, nicht dunkelblau!\n"
            "Konturlinien trennen die Zonen. Sichtbare Tiefenzahlen beschriften jede Zone.\n\n"
            "WICHTIG: Extrahiere NUR Tiefenzahlen die INNERHALB der Wasserfläche stehen.\n""Ignoriere: Zahlen in der App-UI (Buttons, Legende, Skala), Zahlen am Bildrand,\n""Koordinatenangaben, Maßstabsbalken und Zahlen außerhalb des blauen Gewässerbereichs.\n"
            "Identifiziere dann welche Farbe zu welcher Zahl gehört.\n"
            "Nutze die Zahlen – nicht die Farbbeschreibungen – als Grundlage.\n\n"

            "AUFGABE 1 – Tiefenzonen nach Farbe:\n"
            "Erkenne JEDE farblich unterschiedliche Fläche als eigene Tiefenzone.\n"
            "Zeichne den VOLLSTÄNDIGEN Umriss jeder Zone als Polygon.\n"
            "Nutze 10-15 Punkte pro Zone (mehr nur bei sehr komplexen Formen).\n"
            "Koordinaten: [x%, y%] von oben-links (0,0) bis unten-rechts (100,100).\n"
            "Decke die gesamte Wasserfläche lückenlos mit Polygonen ab.\n\n"

            "AUFGABE 2 – Tiefenpunkte:\n"
            "Extrahiere alle sichtbaren Tiefenzahlen mit ihrer Position.\n\n"

            "Antworte NUR mit validem JSON (kein Markdown):\n"
            '{"zones":['
            '{"depth_m":0.6,"label":"0.6","color":"hellblau",'
            '"outline":[[20,5],[80,5],[82,15],[78,30],[75,45],[78,60],[80,75],[82,90],[20,90],[18,75],[15,60],[18,45],[15,30],[18,15]]},'
            '{"depth_m":1.3,"label":"1.3","color":"mittelblau",'
            '"outline":[[35,20],[65,20],[67,40],[65,60],[35,60],[33,40]]}'
            '],'
            '"depths":[{"value":1.6,"x_pct":45,"y_pct":30,"label":"1.6"}],'
            '"max_depth":2.0,"min_depth":0.6,"depth_unit":"m",'
            '"coverage":"Beschreibung der Gewässerform"}'
        )

        payload = {
            "model": "claude-sonnet-4-5",
            "max_tokens": 4096,
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": img_type,
                            "data": image_data,
                        }
                    },
                    {"type": "text", "text": prompt}
                ]
            }]
        }

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }

        result = {"success": False, "error": "Unbekannter Fehler", "data": None}

        if api_key == "OVERLAY_ONLY":
            # Nur Overlay speichern, kein API-Aufruf
            result = {"success": True, "data": {"depths": [], "zones": []}, "error": None}
        else:
         try:
            session = aiohttp.ClientSession()
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                body = await resp.json()
                if resp.status == 200:
                    raw = "".join(
                        c.get("text", "") for c in body.get("content", [])
                        if c.get("type") == "text"
                    )
                    clean = raw.replace("```json", "").replace("```", "").strip()
                    try:
                        parsed = _json.loads(clean)
                    except Exception:
                        # JSON abgeschnitten → Reparaturversuch
                        try:
                            d = clean.count('{') - clean.count('}')
                            a = clean.count('[') - clean.count(']')
                            fixed = clean + ']' * max(0, a) + '}' * max(0, d)
                            parsed = _json.loads(fixed)
                        except Exception:
                            parsed = {"depths": [], "zones": [], "max_depth": 0, "min_depth": 0}
                    result = {"success": True, "data": parsed, "error": None}
                else:
                    result["error"] = f"API Fehler {resp.status}: {body.get('error', {}).get('message', '')}"
            await session.close()
         except Exception as exc:
            result["error"] = str(exc)

        # Georeferenzierung berechnen wenn Referenzpunkte vorhanden
        # Corner-basierte Georeferenzierung (neue Methode)
        if result["success"] and call.data.get("corner_tl_lat", 0) != 0:
            tl_lat = call.data["corner_tl_lat"]; tl_lon = call.data["corner_tl_lon"]
            br_lat = call.data["corner_br_lat"]; br_lon = call.data["corner_br_lon"]
            dLat = br_lat - tl_lat; dLon = br_lon - tl_lon
            depth_pts = []
            for d in result["data"].get("depths", []):
                px, py = d.get("x_pct", 50) / 100, d.get("y_pct", 50) / 100
                lat = round(tl_lat + py * dLat, 6)
                lon = round(tl_lon + px * dLon, 6)
                depth_pts.append({"depth_m": d.get("value"), "label": d.get("label"), "lat": lat, "lon": lon})
            min_d = min((p["depth_m"] for p in depth_pts), default=0)
            max_d = max((p["depth_m"] for p in depth_pts), default=0)
            scan_name = call.data.get("scan_name", "Scan")
            ts = datetime.now().isoformat()
            result["depth_points"] = depth_pts
            result["min_depth"] = min_d; result["max_depth"] = max_d
            result["scan_name"] = scan_name; result["timestamp"] = ts
            geo_zones_list = result.get("zones", [])
            # Bild nach Vektorisierung entfernen → spart ~100KB Storage
            has_zones = len(geo_zones_list) > 0
            new_scan = {
                "scan_name": scan_name, "timestamp": ts,
                "depth_count": len(depth_pts), "min_depth": min_d, "max_depth": max_d,
                "depth_points": depth_pts,
                "zones": geo_zones_list,
                "image_bounds": call.data.get("image_bounds", ""),
                "image_data_url": "" if has_zones else call.data.get("image_data_url", ""),
            }
            await store.async_save_deeper_scan(new_scan)
            entry_data = hass.data[DOMAIN][entry.entry_id]
            entry_data["deeper_scans"] = store.deeper_scans
            result["all_scans"] = [{"scan_name": s["scan_name"], "timestamp": s["timestamp"],
                                     "depth_count": s["depth_count"], "min_depth": s["min_depth"],
                                     "max_depth": s["max_depth"]} for s in store.deeper_scans]

        # Alt: Referenzpunkt-basierte Georeferenzierung (rückwärtskompatibel)
        elif result["success"] and call.data.get("ref_blue_lat", 0) != 0:
            import math as _math
            bx = call.data["ref_blue_xp"]; by = call.data["ref_blue_yp"]
            rx = call.data["ref_red_xp"];  ry = call.data["ref_red_yp"]
            gB_lat = call.data["ref_blue_lat"]; gB_lon = call.data["ref_blue_lon"]
            gR_lat = call.data["ref_red_lat"];  gR_lon = call.data["ref_red_lon"]
            dLat = gR_lat - gB_lat; dLon = gR_lon - gB_lon
            vx = rx - bx; vy = ry - by
            lat_rad = _math.radians((gB_lat + gR_lat) / 2)
            dN = dLat * 111320; dE = dLon * 111320 * _math.cos(lat_rad)
            perp_Lat = -dE / 111320
            perp_Lon = dN / (111320 * _math.cos(lat_rad))
            px_perp = -vy; py_perp = vx
            def solve2x2(a, b, c, d, e, f):
                det = a*d - b*c
                return (e*d - b*f)/det, (a*f - e*c)/det
            try:
                a1, a2 = solve2x2(vx, vy, px_perp, py_perp, dLat, perp_Lat)
                b1, b2 = solve2x2(vx, vy, px_perp, py_perp, dLon, perp_Lon)
                a0 = gB_lat - a1*bx - a2*by
                b0 = gB_lon - b1*bx - b2*by
                depth_pts = []
                depths = result["data"].get("depths", [])
                for d in depths:
                    px, py = d.get("x_pct", 50), d.get("y_pct", 50)
                    lat = round(a0 + a1*px + a2*py, 6)
                    lon = round(b0 + b1*px + b2*py, 6)
                    depth_pts.append({"depth_m": d.get("value"), "label": d.get("label"), "lat": lat, "lon": lon})
                min_d = min((d["depth_m"] for d in depth_pts), default=0)
                max_d = max((d["depth_m"] for d in depth_pts), default=0)
                scan_name = call.data.get("scan_name", "Scan")
                ts = datetime.now().isoformat()
                # Outlier-Filter: Punkte die >2σ vom Cluster-Zentrum entfernt sind entfernen
                if len(depth_pts) >= 4:
                    import math as _m
                    lats = [p["lat"] for p in depth_pts]
                    lons = [p["lon"] for p in depth_pts]
                    avg_lat = sum(lats) / len(lats)
                    avg_lon = sum(lons) / len(lons)
                    # Standardabweichung
                    std_lat = _m.sqrt(sum((x - avg_lat)**2 for x in lats) / len(lats))
                    std_lon = _m.sqrt(sum((x - avg_lon)**2 for x in lons) / len(lons))
                    # Mindest-Schwellwert um echte Cluster nicht zu aggressiv zu filtern
                    thr_lat = max(std_lat * 2.5, 0.0005)
                    thr_lon = max(std_lon * 2.5, 0.0005)
                    depth_pts = [p for p in depth_pts
                                 if abs(p["lat"] - avg_lat) <= thr_lat
                                 and abs(p["lon"] - avg_lon) <= thr_lon]
                    min_d = min((p["depth_m"] for p in depth_pts), default=0)
                    max_d = max((p["depth_m"] for p in depth_pts), default=0)

                result["depth_points"] = depth_pts
                result["min_depth"] = min_d
                result["max_depth"] = max_d
                result["scan_name"] = scan_name
                result["timestamp"] = ts
                # Scan dauerhaft in hass.data akkumulieren (direkte Referenz!)
                new_scan = {
                    "scan_name": scan_name,
                    "timestamp": ts,
                    "depth_count": len(depth_pts),
                    "min_depth": min_d,
                    "max_depth": max_d,
                    "depth_points": depth_pts,
                }
                # Dauerhaft in FishingStore speichern (überlebt HA-Neustart)
                await store.async_save_deeper_scan(new_scan)
                # Auch in hass.data für Sensor-Zugriff
                entry_data = hass.data[DOMAIN][entry.entry_id]
                entry_data["deeper_scans"] = store.deeper_scans
                # Scan-Liste im result für sofortige Panel-Anzeige
                result["all_scans"] = [{"scan_name": s["scan_name"],
                                         "timestamp": s["timestamp"],
                                         "depth_count": s["depth_count"],
                                         "min_depth": s["min_depth"],
                                         "max_depth": s["max_depth"]}
                                        for s in store.deeper_scans]
            except Exception as geo_exc:
                result["geo_error"] = str(geo_exc)

        # Ergebnis in hass.data speichern → Sensor-Update triggern
        if entry.entry_id in hass.data.get(DOMAIN, {}):
            hass.data[DOMAIN][entry.entry_id]["deeper_result"] = result
        async_dispatcher_send(hass, SIGNAL_UPDATED)

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

    async def handle_delete_catch(call: ServiceCall) -> None:
        store: FishingStore = hass.data[DOMAIN][entry.entry_id]["store"]
        removed = await store.async_remove_entry(call.data["timestamp"])
        if removed:
            async_dispatcher_send(hass, SIGNAL_UPDATED)

    if not hass.services.has_service(DOMAIN, SERVICE_DELETE_CATCH):
        hass.services.async_register(DOMAIN, SERVICE_DELETE_CATCH, handle_delete_catch, schema=SERVICE_DELETE_SCHEMA)

    if not hass.services.has_service(DOMAIN, SERVICE_ANALYZE_DEEPER):
        hass.services.async_register(DOMAIN, SERVICE_ANALYZE_DEEPER, handle_analyze_deeper, schema=SERVICE_ANALYZE_SCHEMA)

    # Gewässer-URL wechseln (von wassertemperatur.site) — für Gewässerauswahl im Panel
    async def handle_set_water_url(call: ServiceCall) -> None:
        new_url = (call.data.get("url") or "").strip().rstrip("/")
        if not new_url or "wassertemperatur.site" not in new_url:
            return
        eng = hass.data[DOMAIN][entry.entry_id].get("water_temp_engine")
        if eng:
            eng.set_url(new_url)
            eng._cache.clear()  # Cache leeren damit sofort neu gescrapt wird
        # In Options persistieren (überlebt Neustart)
        new_options = dict(entry.options)
        new_options[CONF_WATER_TEMP_URL] = new_url
        hass.config_entries.async_update_entry(entry, options=new_options)
        # Sofortiges Update auslösen
        async_dispatcher_send(hass, SIGNAL_UPDATED)

    if not hass.services.has_service(DOMAIN, "set_water_url"):
        hass.services.async_register(DOMAIN, "set_water_url", handle_set_water_url,
            schema=vol.Schema({vol.Required("url"): cv.string}))

    # Fang aktualisieren (Bearbeiten + Wetter-Abgleich)
    async def handle_update_catch(call: ServiceCall) -> None:
        store: FishingStore = hass.data[DOMAIN][entry.entry_id]["store"]
        ts = call.data.get("timestamp")
        if not ts:
            return
        # Alle Felder außer timestamp als Updates übernehmen
        updates = {k: v for k, v in call.data.items() if k != "timestamp"}
        if await store.async_update_entry(ts, updates):
            async_dispatcher_send(hass, SIGNAL_UPDATED)

    if not hass.services.has_service(DOMAIN, "update_catch"):
        hass.services.async_register(DOMAIN, "update_catch", handle_update_catch,
            schema=vol.Schema({
                vol.Required("timestamp"): cv.string,
                vol.Optional("fish_type"): cv.string,
                vol.Optional("length_cm"): vol.Coerce(float),
                vol.Optional("weight_kg"): vol.Coerce(float),
                vol.Optional("bait"): cv.string,
                vol.Optional("spot"): cv.string,
                vol.Optional("notes"): cv.string,
                vol.Optional("water_temp"): vol.Coerce(float),
                vol.Optional("temperature"): vol.Coerce(float),
                vol.Optional("wind_speed"): vol.Coerce(float),
                vol.Optional("wind_gusts"): vol.Coerce(float),
                vol.Optional("wind_bearing"): vol.Coerce(float),
                vol.Optional("pressure"): vol.Coerce(float),
                vol.Optional("cloud_coverage"): vol.Coerce(float),
                vol.Optional("precipitation"): vol.Coerce(float),
                vol.Optional("humidity"): vol.Coerce(float),
                vol.Optional("solar_radiation"): vol.Coerce(float),
                vol.Optional("angelwetter_index"): vol.Coerce(int),
            }, extra=vol.ALLOW_EXTRA))

    # Scan löschen
    async def handle_delete_deeper_scan(call: ServiceCall) -> None:
        scan_name = call.data.get("scan_name", "")
        if not scan_name: return
        if await store.async_delete_deeper_scan(scan_name):
            if entry.entry_id in hass.data.get(DOMAIN, {}):
                hass.data[DOMAIN][entry.entry_id]["deeper_scans"] = store.deeper_scans
            async_dispatcher_send(hass, SIGNAL_UPDATED)

    if not hass.services.has_service(DOMAIN, "delete_deeper_scan"):
        hass.services.async_register(DOMAIN, "delete_deeper_scan", handle_delete_deeper_scan,
            schema=vol.Schema({vol.Required("scan_name"): cv.string}))

    async def handle_vectorize_deeper_scan(call: ServiceCall) -> None:
        """Liest Bild direkt aus Store und vektorisiert ohne Browser-Transfer."""
        scan_name = call.data.get("scan_name", "")
        api_key   = call.data.get("api_key", "")
        if not scan_name or not api_key:
            return

        # Scan aus Store lesen
        scan = next((s for s in store.deeper_scans if s.get("scan_name") == scan_name), None)
        if not scan:
            if entry.entry_id in hass.data.get(DOMAIN, {}):
                hass.data[DOMAIN][entry.entry_id]["deeper_result"] = {
                    "success": False, "error": f"Scan '{scan_name}' nicht gefunden", "data": None}
            return

        img_url = scan.get("image_data_url", "")
        if not img_url:
            if entry.entry_id in hass.data.get(DOMAIN, {}):
                hass.data[DOMAIN][entry.entry_id]["deeper_result"] = {
                    "success": False, "error": "Kein Bild im Scan gespeichert", "data": None}
            return

        # base64 extrahieren
        if "," in img_url:
            img_b64 = img_url.split(",")[1]
        else:
            img_b64 = img_url

        # Bounds aus Scan lesen
        bounds_str = scan.get("image_bounds", "{}")
        try:
            bounds = json.loads(bounds_str) if bounds_str else {}
        except Exception:
            bounds = {}

        tl_lat = (bounds.get("tl") or {}).get("lat") or bounds.get("maxLat", 0)
        tl_lon = (bounds.get("tl") or {}).get("lon") or bounds.get("minLon", 0)
        br_lat = (bounds.get("br") or {}).get("lat") or bounds.get("minLat", 0)
        br_lon = (bounds.get("br") or {}).get("lon") or bounds.get("maxLon", 0)

        # Synthetic call.data für handle_analyze_deeper
        import types
        fake_data = {
            "image_data": img_b64,
            "api_key": api_key,
            "image_type": "image/jpeg",
            "scan_name": scan_name,
            "corner_tl_lat": tl_lat, "corner_tl_lon": tl_lon,
            "corner_br_lat": br_lat, "corner_br_lon": br_lon,
            "image_data_url": img_url,
            "image_bounds": bounds_str,
            "ref_blue_lat": 0.0, "ref_blue_lon": 0.0,
            "ref_red_lat": 0.0, "ref_red_lon": 0.0,
            "ref_blue_xp": 0.0, "ref_blue_yp": 0.0,
            "ref_red_xp": 100.0, "ref_red_yp": 0.0,
        }
        fake_call = types.SimpleNamespace(data=fake_data)
        await handle_analyze_deeper(fake_call)

    if not hass.services.has_service(DOMAIN, "vectorize_deeper_scan"):
        hass.services.async_register(DOMAIN, "vectorize_deeper_scan", handle_vectorize_deeper_scan,
            schema=vol.Schema({
                vol.Required("scan_name"): cv.string,
                vol.Required("api_key"):   cv.string,
            }))

    async def handle_store_image_chunk(call: ServiceCall) -> None:
        """Speichert Bild-Chunk in hass.data (umgeht HA-Größenlimit)."""
        scan_name = call.data.get("scan_name", "")
        chunk     = call.data.get("chunk", "")
        chunk_idx = call.data.get("chunk_idx", 0)
        total     = call.data.get("total_chunks", 1)
        bounds    = call.data.get("image_bounds", "")
        img_type  = call.data.get("image_type", "image/jpeg")

        entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
        if "img_chunks" not in entry_data:
            entry_data["img_chunks"] = {}
        if scan_name not in entry_data["img_chunks"]:
            entry_data["img_chunks"][scan_name] = {"chunks": {}, "total": total, "bounds": bounds, "type": img_type}

        entry_data["img_chunks"][scan_name]["chunks"][chunk_idx] = chunk

        # Alle Chunks da? → zusammenbauen und in Store speichern
        sc = entry_data["img_chunks"][scan_name]
        if len(sc["chunks"]) >= sc["total"]:
            full_b64 = "".join(sc["chunks"][i] for i in range(sc["total"]))
            img_url  = f"data:{sc['type']};base64,{full_b64}"
            # Bestehenden Scan updaten oder neu anlegen
            existing = next((s for s in store.deeper_scans if s.get("scan_name") == scan_name), None)
            if existing:
                existing["image_data_url"] = img_url
                existing["image_bounds"]   = sc["bounds"]
                await store.async_save()
            else:
                await store.async_save_deeper_scan({
                    "scan_name": scan_name, "timestamp": datetime.now().isoformat(),
                    "depth_count": 0, "min_depth": 0, "max_depth": 0,
                    "depth_points": [], "zones": [],
                    "image_data_url": img_url, "image_bounds": sc["bounds"],
                })
            del entry_data["img_chunks"][scan_name]
            entry_data["deeper_scans"] = store.deeper_scans
            async_dispatcher_send(hass, SIGNAL_UPDATED)

    if not hass.services.has_service(DOMAIN, "store_image_chunk"):
        hass.services.async_register(DOMAIN, "store_image_chunk", handle_store_image_chunk,
            schema=vol.Schema({
                vol.Required("scan_name"):    cv.string,
                vol.Required("chunk"):        cv.string,
                vol.Required("chunk_idx"):    vol.Coerce(int),
                vol.Optional("total_chunks",  default=1): vol.Coerce(int),
                vol.Optional("image_bounds",  default=""): cv.string,
                vol.Optional("image_type",    default="image/jpeg"): cv.string,
            }))
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
        for service in (SERVICE_LOG_CATCH, SERVICE_LOG_NO_CATCH, SERVICE_DELETE_CATCH, SERVICE_IMPORT_CSV, SERVICE_EXPORT_CSV, SERVICE_EXPORT_JSON):
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

    # Datum: aus Formular (nachträgliche Einträge) oder jetzt
    _dt_str = data.get("catch_datetime")
    if _dt_str:
        try:
            from datetime import datetime as _dt
            now = _dt.fromisoformat(_dt_str).astimezone()
        except Exception:
            now = datetime.now().astimezone()
    else:
        now = datetime.now().astimezone()

    pressure = _float(weather_attrs.get("pressure"), 1015)
    temperature = _float(weather_attrs.get("temperature"), 12)
    wind_speed = _float(weather_attrs.get("wind_speed"), 10)
    cloud = _float(weather_attrs.get("cloud_coverage"), 50)
    precipitation = _float(weather_attrs.get("precipitation"), 0)

    # Lokale Wetterstation Haftenkamp (Priorität über weather entity)
    def _hs(entity_id, default=None):
        s = hass.states.get(entity_id)
        return _float(s.state, default) if s and s.state not in ("unknown","unavailable") else default

    hs_temp    = _hs("sensor.haftenkamp_temperatur")
    hs_wind    = _hs("sensor.haftenkamp_windgeschwindigkeit")
    hs_gusts   = _hs("sensor.haftenkamp_windboen")
    hs_bearing = _hs("sensor.haftenkamp_windrichtung")
    hs_press   = _hs("sensor.haftenkamp_druck")
    hs_rain    = _hs("sensor.haftenkamp_niederschlag")
    hs_cloud   = _hs("sensor.haftenkamp_bewolkungsgrad")
    hs_solar   = _hs("sensor.haftenkamp_sonneneinstrahlung")
    hs_humid   = _hs("sensor.haftenkamp_relative_luftfeuchtigkeit")

    if hs_temp  is not None: temperature   = hs_temp
    if hs_wind  is not None: wind_speed     = hs_wind
    if hs_press is not None: pressure       = hs_press
    if hs_rain  is not None: precipitation  = hs_rain
    if hs_cloud is not None: cloud          = hs_cloud

    # Wassertemperatur
    water_temp_sensor = hass.states.get("sensor.wassertemperatur_gewaesser")
    water_temp = data.get("water_temp") or (
        _float(water_temp_sensor.state)
        if water_temp_sensor and water_temp_sensor.state not in ("unknown","unavailable")
        else None
    )

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

    # Foto speichern
    photo_url = None
    photo_data = data.get("photo_data")
    if photo_data and len(photo_data) > 100:
        import base64, uuid as _uuid
        photo_dir = Path(hass.config.path()) / "www" / "fishing_tracker" / "photos"
        photo_dir.mkdir(parents=True, exist_ok=True)
        photo_id = _uuid.uuid4().hex[:12]
        photo_filename = f"catch_{photo_id}.jpg"
        photo_path = photo_dir / photo_filename
        try:
            raw = photo_data.split(",", 1)[-1]
            await hass.async_add_executor_job(
                lambda: photo_path.write_bytes(base64.b64decode(raw))
            )
            photo_url = f"/local/fishing_tracker/photos/{photo_filename}"
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Foto konnte nicht gespeichert werden: %s", exc)

    new_entry = {
        "timestamp": now.isoformat(),
        "angler": data.get("angler") or entry.data.get(CONF_NAME, DEFAULT_NAME),
        "latitude": latitude,
        "longitude": longitude,
        "fish_type": data.get("fish_type") or settings.get("fish_type"),
        "caught": caught,
        "spot": data.get("spot") or settings.get("spot"),
        "bait": data.get("bait") or settings.get("bait"),
        "method": data.get("method"),
        "target_fish": data.get("target_fish"),
        "length_cm": (lambda v: float(v) if v else 0)(data.get("length_cm") or settings.get("length_cm") or 0),
        "weight_kg": (lambda v: float(v) if v else None)(data.get("weight_kg") or None),
        "notes": data.get("notes", ""),
        "photo_url": photo_url,
        "chance": chance,
        "angelwetter_index": data.get("angelwetter_index"),
        "pressure": pressure,
        "temperature": temperature,
        "wind_speed": wind_speed,
        "wind_bearing": hs_bearing,
        "wind_gusts": hs_gusts,
        "cloud_coverage": cloud,
        "precipitation": precipitation,
        "solar_radiation": hs_solar,
        "humidity": hs_humid,
        "water_temp": water_temp,
        "catch_datetime": data.get("catch_datetime"),
        "session_blank": data.get("session_blank", False),
        "session_start": data.get("session_start"),
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

    # Quick-Entry Card registrieren
    quick_url = f"/local/fishing-quick-card.js?v={FRONTEND_VERSION.replace('.', '')}"
    try:
        storage3 = hass.helpers.storage.Store(1, "lovelace_resources")
        data3 = await storage3.async_load() or {"items": []}
        items3 = data3.get("items", [])
        existing3 = next(
            (i for i in items3 if i.get("url", "").startswith("/local/fishing-quick-card.js")),
            None,
        )
        if existing3:
            if existing3.get("url") != quick_url:
                existing3["url"] = quick_url
                data3["items"] = items3
                await storage3.async_save(data3)
        else:
            items3.append({"id": "fishing-quick-card", "type": "module", "url": quick_url})
            data3["items"] = items3
            await storage3.async_save(data3)
    except Exception:
        pass
