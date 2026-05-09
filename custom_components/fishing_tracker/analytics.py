from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def parse_hour(value: Any) -> int | None:
    try:
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00")).hour
    except Exception:
        return None
    return None


def normalize_length(value: Any) -> int | None:
    if value in (None, "", "Unbekannt", "unknown", "unavailable"):
        return None
    text = str(value).replace("cm", "").strip()
    try:
        return int(float(text))
    except Exception:
        return None


def success(entry: dict[str, Any]) -> bool:
    return _safe_int(entry.get("caught", 0)) >= 1


def calculate_rate(entries: list[dict[str, Any]]) -> float:
    if not entries:
        return 0.0
    return round(sum(1 for e in entries if success(e)) / len(entries) * 100, 1)


def confidence_label(total: int) -> str:
    if total >= 100:
        return "sehr hoch"
    if total >= 50:
        return "hoch"
    if total >= 20:
        return "mittel"
    if total >= 5:
        return "niedrig"
    return "sehr niedrig"


def weighted_rate(fang: int, total: int, prior: float = 50.0, strength: int = 8) -> float:
    if total <= 0:
        return prior
    return round(((fang * 100) + (prior * strength)) / (total + strength), 1)


def best_by(entries: list[dict[str, Any]], key: str, minimum: int = 2) -> dict[str, Any]:
    groups: dict[str, dict[str, int]] = defaultdict(lambda: {"fang": 0, "gesamt": 0})

    for entry in entries:
        value = entry.get(key) or "Unbekannt"
        groups[str(value)]["gesamt"] += 1
        if success(entry):
            groups[str(value)]["fang"] += 1

    best = {"name": "Keine Daten", "rate": 0.0, "raw_rate": 0.0, "count": 0}

    for name, item in groups.items():
        if item["gesamt"] < minimum:
            continue

        raw = round(item["fang"] / item["gesamt"] * 100, 1)
        smoothed = weighted_rate(item["fang"], item["gesamt"])
        rank_score = smoothed * min(1.0, item["gesamt"] / 12)
        current_rank = best["rate"] * min(1.0, max(best["count"], 1) / 12)

        if rank_score > current_rank:
            best = {
                "name": name,
                "rate": smoothed,
                "raw_rate": raw,
                "count": item["gesamt"],
            }

    return best


def combo_key(entry: dict[str, Any]) -> str:
    return f"{entry.get('spot') or 'Unbekannt'} + {entry.get('bait') or 'Unbekannt'}"


def stats(entries: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(entries)
    caught = sum(1 for e in entries if success(e))
    no_catch = total - caught
    rate = calculate_rate(entries)

    normalized = []
    for e in entries:
        n = dict(e)
        n["hour"] = parse_hour(n.get("timestamp"))
        n["combo"] = combo_key(n)
        normalized.append(n)

    lengths = [normalize_length(e.get("length_cm")) for e in normalized if success(e)]
    lengths = [x for x in lengths if x is not None]

    if total < 5:
        history_score = 50.0
    elif total < 20:
        history_score = round((rate * 0.5) + 25, 1)
    else:
        history_score = rate

    return {
        "total": total,
        "total_catches": caught,
        "total_no_catch": no_catch,
        "success_rate": rate,
        "history_score": history_score,
        "confidence": confidence_label(total),
        "top_spot": best_by(normalized, "spot"),
        "top_bait": best_by(normalized, "bait"),
        "top_fish": best_by(normalized, "fish_type"),
        "top_hour": best_by(normalized, "hour"),
        "top_combo": best_by(normalized, "combo"),
        "avg_length_cm": round(sum(lengths) / len(lengths), 1) if lengths else None,
        "max_length_cm": max(lengths) if lengths else None,
    }


def current_weather_score(
    temperature: float,
    wind_speed: float,
    pressure: float,
    cloud_coverage: float,
    precipitation: float,
    pressure_trend: float,
    hour: int,
    month: int,
    moon_phase: str | None = None,
    history_score: float = 50.0,
) -> int:
    water = temperature * 0.65 + 5
    score = 45.0

    if 5 <= hour <= 9:
        score += 14
    elif 18 <= hour <= 22:
        score += 18
    elif 11 <= hour <= 15 and month in [6, 7, 8]:
        score -= 14
    elif 11 <= hour <= 15:
        score -= 5
    else:
        score += 2

    if 12 <= water <= 19:
        score += 18
    elif 8 <= water < 12:
        score += 8
    elif 19 < water <= 23:
        score += 5
    elif water < 6 or water > 25:
        score -= 18
    else:
        score -= 6

    if 5 <= wind_speed <= 18:
        score += 12
    elif 18 < wind_speed <= 28:
        score += 4
    elif wind_speed < 3:
        score -= 10
    else:
        score -= 16

    if 1008 <= pressure <= 1022:
        score += 9
    elif 1000 <= pressure < 1008 or 1022 < pressure <= 1030:
        score += 2
    else:
        score -= 10

    if -3 <= pressure_trend <= -0.5:
        score += 10
    elif -0.5 < pressure_trend <= 1.5:
        score += 5
    elif pressure_trend < -6 or pressure_trend > 5:
        score -= 15
    else:
        score -= 5

    if 40 <= cloud_coverage <= 85:
        score += 8
    elif cloud_coverage < 20 and 11 <= hour <= 16:
        score -= 10
    elif cloud_coverage > 95:
        score -= 3

    if 0.1 <= precipitation <= 2:
        score += 6
    elif precipitation > 8:
        score -= 14
    elif precipitation > 3:
        score -= 5

    if moon_phase in ("new_moon", "full_moon"):
        score += 3
    elif moon_phase in ("first_quarter", "last_quarter"):
        score -= 1

    if month in [5, 6, 7, 8, 9]:
        score += 6
    elif month in [3, 4, 10]:
        score += 2
    else:
        score -= 8

    mixed = (score * 0.75) + (history_score * 0.25)
    return int(max(10, min(96, round(mixed))))


def recommendation(entries: list[dict[str, Any]]) -> str:
    s = stats(entries)
    if s["total"] < 5:
        return "Noch zu wenig Daten. Speichere Fang und Kein-Fang konsequent, damit die Analyse lernen kann."

    combo = s["top_combo"]
    spot = s["top_spot"]
    bait = s["top_bait"]

    return (
        f"Beste Kombi bisher: {combo['name']} "
        f"({combo['raw_rate']} %, {combo['count']} Versuche). "
        f"Top Spot: {spot['name']}. Top Köder: {bait['name']}. "
        f"Sicherheit: {s['confidence']}."
    )
