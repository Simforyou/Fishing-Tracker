from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any


def advanced_analysis(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Build advanced learning, water profiles, patterns, spots and strategy.

    This is intentionally deterministic and explainable.
    It does not use black-box ML yet, but converts the user's own data into
    ranked and explainable fishing intelligence.
    """
    clean = [_normalize(e) for e in entries]
    total = len(clean)
    catches = [e for e in clean if e["caught"] >= 1]

    if not total:
        return _empty()

    return {
        "learning": _learning_summary(clean),
        "water_profiles": _water_profiles(clean),
        "patterns": _pattern_detection(clean),
        "spot_scoring": _spot_scoring(clean),
        "map_analysis": _map_analysis(clean),
        "strategy": _strategy(clean),
        "meta": {
            "total_entries": total,
            "total_catches": len(catches),
            "success_rate": round(len(catches) / total * 100, 1) if total else 0,
            "confidence": _confidence(total),
        },
    }


def _normalize(e: dict[str, Any]) -> dict[str, Any]:
    timestamp = e.get("timestamp") or ""
    dt = _parse_dt(timestamp)
    return {
        "timestamp": timestamp,
        "dt": dt,
        "hour": dt.hour if dt else None,
        "month": dt.month if dt else None,
        "day": dt.strftime("%Y-%m-%d") if dt else "",
        "fish_type": _text(e.get("fish_type") or e.get("fischart") or "Unbekannt"),
        "spot": _text(e.get("spot") or "Unbekannt"),
        "bait": _text(e.get("bait") or e.get("koeder") or "Unbekannt"),
        "caught": _int(e.get("caught", 0)),
        "length_cm": _float(e.get("length_cm"), 0),
        "chance": _float(e.get("chance"), 0),
        "temperature": _float(e.get("temperature"), None),
        "pressure": _float(e.get("pressure"), None),
        "pressure_trend": _float(e.get("pressure_trend"), None),
        "wind_speed": _float(e.get("wind_speed"), None),
        "cloud_coverage": _float(e.get("cloud_coverage"), None),
        "precipitation": _float(e.get("precipitation"), None),
        "latitude": _float(e.get("latitude"), None),
        "longitude": _float(e.get("longitude"), None),
    }


def _learning_summary(entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "best_fish": _rank_key(entries, "fish_type")[:5],
        "best_baits": _rank_key(entries, "bait")[:8],
        "best_spots": _rank_key(entries, "spot")[:8],
        "best_hours": _rank_key(entries, "hour")[:8],
        "best_months": _rank_key(entries, "month")[:8],
        "message": _learning_message(entries),
    }


def _water_profiles(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_spot: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in entries:
        by_spot[e["spot"]].append(e)

    profiles = []
    for spot, rows in by_spot.items():
        catches = [r for r in rows if r["caught"] >= 1]
        fish = _rank_key(rows, "fish_type")[:3]
        baits = _rank_key(rows, "bait")[:3]
        hours = _rank_key(rows, "hour")[:3]
        avg_temp = _avg([r["temperature"] for r in rows if r["temperature"] is not None])
        profiles.append({
            "spot": spot,
            "sessions": len(rows),
            "catches": len(catches),
            "success_rate": round(len(catches) / len(rows) * 100, 1) if rows else 0,
            "dominant_fish": fish,
            "top_baits": baits,
            "top_hours": hours,
            "avg_temperature": avg_temp,
            "profile": _spot_profile_text(spot, rows),
        })

    return sorted(profiles, key=lambda p: (p["success_rate"], p["sessions"]), reverse=True)


def _pattern_detection(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    patterns = []

    for key, label in [
        ("hour", "Uhrzeit"),
        ("bait", "Köder"),
        ("spot", "Spot"),
        ("fish_type", "Fischart"),
        ("month", "Monat"),
    ]:
        ranking = _rank_key(entries, key)
        if ranking:
            top = ranking[0]
            if top["sessions"] >= 2:
                patterns.append({
                    "type": key,
                    "title": f"Starkes Muster: {label}",
                    "value": top["name"],
                    "success_rate": top["success_rate"],
                    "sessions": top["sessions"],
                    "summary": f"{label} {top['name']} liegt aktuell bei {top['success_rate']}% Fangquote über {top['sessions']} Sessions.",
                })

    # Weather patterns
    weather_patterns = _weather_patterns(entries)
    patterns.extend(weather_patterns)

    return sorted(patterns, key=lambda p: (p.get("success_rate", 0), p.get("sessions", 0)), reverse=True)[:12]


def _spot_scoring(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    profiles = _water_profiles(entries)
    scored = []

    for p in profiles:
        sessions = p["sessions"]
        rate = p["success_rate"]
        confidence = min(100, sessions * 12)
        score = round(rate * 0.65 + confidence * 0.25 + min(10, p["catches"]) * 1.0, 1)

        if score >= 75:
            level = "Hotspot"
        elif score >= 55:
            level = "Gut"
        elif score >= 35:
            level = "Beobachten"
        else:
            level = "Schwach"

        scored.append({
            **p,
            "spot_score": min(99, score),
            "level": level,
            "recommendation": _spot_recommendation(p, level),
        })

    return sorted(scored, key=lambda x: x["spot_score"], reverse=True)


def _map_analysis(entries: list[dict[str, Any]]) -> dict[str, Any]:
    gps_rows = [e for e in entries if e["latitude"] is not None and e["longitude"] is not None]
    catch_gps = [e for e in gps_rows if e["caught"] >= 1]

    zones = []
    by_spot = defaultdict(list)
    for e in gps_rows:
        by_spot[e["spot"]].append(e)

    for spot, rows in by_spot.items():
        catches = [r for r in rows if r["caught"] >= 1]
        lat = _avg([r["latitude"] for r in rows if r["latitude"] is not None])
        lon = _avg([r["longitude"] for r in rows if r["longitude"] is not None])
        zones.append({
            "spot": spot,
            "lat": lat,
            "lon": lon,
            "sessions": len(rows),
            "catches": len(catches),
            "success_rate": round(len(catches) / len(rows) * 100, 1) if rows else 0,
            "zone_type": "hotspot" if catches else "test_area",
        })

    return {
        "gps_entries": len(gps_rows),
        "gps_catches": len(catch_gps),
        "zones": sorted(zones, key=lambda z: (z["success_rate"], z["sessions"]), reverse=True),
        "summary": _map_summary(gps_rows, catch_gps),
    }


def _strategy(entries: list[dict[str, Any]]) -> dict[str, Any]:
    spots = _spot_scoring(entries)
    patterns = _pattern_detection(entries)
    baits = _rank_key(entries, "bait")
    fish = _rank_key(entries, "fish_type")
    hours = _rank_key(entries, "hour")

    best_spot = spots[0] if spots else None
    best_bait = baits[0] if baits else None
    best_fish = fish[0] if fish else None
    best_hour = hours[0] if hours else None

    plan = []
    if best_fish:
        plan.append(f"Zielfisch zuerst: {best_fish['name']} ({best_fish['success_rate']}% Quote).")
    if best_spot:
        plan.append(f"Startspot: {best_spot['spot']} ({best_spot['level']}, Score {best_spot['spot_score']}).")
    if best_bait:
        plan.append(f"Köder/Methode: {best_bait['name']} priorisieren.")
    if best_hour and best_hour["name"] not in (None, "None"):
        plan.append(f"Zeitfenster: Schwerpunkt um {int(best_hour['name']):02d}:00 Uhr.")
    if not plan:
        plan.append("Noch zu wenig Daten. Erst 10–20 Sessions sammeln, dann wird die Strategie deutlich präziser.")

    return {
        "primary_plan": plan,
        "patterns_used": patterns[:5],
        "confidence": _confidence(len(entries)),
        "next_learning_goal": _next_goal(entries),
    }


def _rank_key(entries: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for e in entries:
        value = e.get(key)
        if value in (None, "", "Unbekannt"):
            continue
        groups[value].append(e)

    ranked = []
    for value, rows in groups.items():
        catches = [r for r in rows if r["caught"] >= 1]
        ranked.append({
            "name": str(value),
            "sessions": len(rows),
            "catches": len(catches),
            "success_rate": round(len(catches) / len(rows) * 100, 1) if rows else 0,
            "avg_length_cm": _avg([r["length_cm"] for r in catches if r["length_cm"]]),
        })

    return sorted(ranked, key=lambda x: (x["success_rate"], x["sessions"]), reverse=True)


def _weather_patterns(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    patterns = []
    caught = [e for e in entries if e["caught"] >= 1]

    if len(caught) < 2:
        return patterns

    avg_wind = _avg([e["wind_speed"] for e in caught if e["wind_speed"] is not None])
    avg_pressure = _avg([e["pressure"] for e in caught if e["pressure"] is not None])
    avg_temp = _avg([e["temperature"] for e in caught if e["temperature"] is not None])

    if avg_wind is not None:
        patterns.append({
            "type": "weather",
            "title": "Windmuster",
            "value": round(avg_wind, 1),
            "success_rate": 50,
            "sessions": len(caught),
            "summary": f"Deine Fänge lagen im Schnitt bei {round(avg_wind,1)} Windgeschwindigkeit.",
        })
    if avg_pressure is not None:
        patterns.append({
            "type": "weather",
            "title": "Luftdruckmuster",
            "value": round(avg_pressure, 1),
            "success_rate": 50,
            "sessions": len(caught),
            "summary": f"Deine Fänge lagen im Schnitt bei {round(avg_pressure,1)} hPa.",
        })
    if avg_temp is not None:
        patterns.append({
            "type": "weather",
            "title": "Temperaturmuster",
            "value": round(avg_temp, 1),
            "success_rate": 50,
            "sessions": len(caught),
            "summary": f"Deine Fänge lagen im Schnitt bei {round(avg_temp,1)} °C.",
        })

    return patterns


def _spot_profile_text(spot: str, rows: list[dict[str, Any]]) -> str:
    rate = round(sum(1 for r in rows if r["caught"] >= 1) / len(rows) * 100, 1) if rows else 0
    if rate >= 70:
        return f"{spot} ist aktuell ein starker Spot mit hoher Fangquote."
    if rate >= 40:
        return f"{spot} zeigt brauchbares Potenzial, braucht aber weitere Daten."
    return f"{spot} ist aktuell eher ein Testspot oder benötigt andere Bedingungen."


def _spot_recommendation(profile: dict[str, Any], level: str) -> str:
    if level == "Hotspot":
        return "Bei passenden Bedingungen zuerst antesten und längere Session einplanen."
    if level == "Gut":
        return "Als Startspot geeignet, aber nach 30–45 Minuten ohne Aktivität wechseln."
    if level == "Beobachten":
        return "Weitere Daten sammeln und gezielt Wetter-/Zeitfenster testen."
    return "Nur als Ausweichspot nutzen oder Strategie/Köder ändern."


def _learning_message(entries: list[dict[str, Any]]) -> str:
    n = len(entries)
    if n < 10:
        return "Datenbasis noch klein. Ab etwa 20 Sessions werden Muster deutlich stabiler."
    if n < 30:
        return "Erste Muster sind sichtbar. Weitere Sessions verbessern Spot- und Köderbewertung."
    return "Gute Datenbasis. Personalisierte Muster können zuverlässig genutzt werden."


def _next_goal(entries: list[dict[str, Any]]) -> str:
    if len(entries) < 20:
        return "Sammle mindestens 20 Sessions mit Spot, Köder, Fischart und Wetterdaten."
    gps = sum(1 for e in entries if e.get("latitude") is not None and e.get("longitude") is not None)
    if gps < len(entries) * 0.7:
        return "Mehr Sessions mit GPS speichern, damit die Kartenanalyse stärker wird."
    return "Gezielt neue Köder/Spots testen, um Empfehlungen breiter abzusichern."


def _map_summary(gps_rows, catch_gps) -> str:
    if not gps_rows:
        return "Keine GPS-Daten für Kartenanalyse vorhanden."
    if not catch_gps:
        return "GPS-Daten vorhanden, aber noch keine GPS-Fänge."
    return f"{len(catch_gps)} GPS-Fänge aus {len(gps_rows)} GPS-Sessions erkannt."


def _confidence(total: int) -> str:
    if total < 10:
        return "niedrig"
    if total < 30:
        return "mittel"
    return "hoch"


def _empty() -> dict[str, Any]:
    return {
        "learning": {"message": "Noch keine Daten vorhanden."},
        "water_profiles": [],
        "patterns": [],
        "spot_scoring": [],
        "map_analysis": {"summary": "Keine Daten vorhanden.", "zones": []},
        "strategy": {
            "primary_plan": ["Noch keine Daten vorhanden. Erste Sessions speichern."],
            "confidence": "niedrig",
            "next_learning_goal": "Erste Fang- und Kein-Fang-Sessions speichern.",
        },
        "meta": {"total_entries": 0, "total_catches": 0, "success_rate": 0, "confidence": "niedrig"},
    }


def _parse_dt(value: str):
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


def _text(value: Any) -> str:
    s = str(value or "Unbekannt")
    return s.replace("ÃŸ", "ß").replace("Ã¤", "ä").replace("Ã¶", "ö").replace("Ã¼", "ü")


def _int(value: Any) -> int:
    try:
        return int(float(value))
    except Exception:
        return 0


def _float(value: Any, default=None):
    try:
        if value in (None, "", "unknown", "unavailable"):
            return default
        return float(value)
    except Exception:
        return default


def _avg(values: list[Any]):
    nums = [v for v in values if isinstance(v, (int, float))]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 1)
