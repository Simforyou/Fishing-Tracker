from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, "", "unknown", "unavailable", "None"):
            return default
        return float(value)
    except Exception:
        return default


def parse_datetime(value: Any) -> datetime | None:
    try:
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None
    return None


def parse_hour(value: Any) -> int | None:
    dt = parse_datetime(value)
    return dt.hour if dt else None


def parse_day(value: Any) -> str:
    dt = parse_datetime(value)
    if not dt:
        return "Unbekannt"
    return dt.strftime("%Y-%m-%d")


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


def best_by(entries: list[dict[str, Any]], key: str, minimum: int = 1) -> dict[str, Any]:
    groups: dict[str, dict[str, int]] = defaultdict(lambda: {"fang": 0, "gesamt": 0})

    for entry in entries:
        value = entry.get(key) or "Unbekannt"
        groups[str(value)]["gesamt"] += 1
        if success(entry):
            groups[str(value)]["fang"] += 1

    best = {"name": "Keine Daten", "rate": 0.0, "raw_rate": 0.0, "count": 0, "catches": 0}

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
                "catches": item["fang"],
            }

    return best


def ranking(entries: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, int]] = defaultdict(lambda: {"fang": 0, "gesamt": 0})

    for entry in entries:
        value = entry.get(key) or "Unbekannt"
        groups[str(value)]["gesamt"] += 1
        if success(entry):
            groups[str(value)]["fang"] += 1

    rows = []
    for name, item in groups.items():
        total = item["gesamt"]
        catches = item["fang"]
        rows.append({
            "name": name,
            "total": total,
            "catches": catches,
            "success_rate": round(catches / total * 100, 1) if total else 0,
            "weighted_rate": weighted_rate(catches, total),
        })

    return sorted(rows, key=lambda x: (x["weighted_rate"], x["total"]), reverse=True)


def combo_key(entry: dict[str, Any]) -> str:
    return f"{entry.get('spot') or 'Unbekannt'} + {entry.get('bait') or 'Unbekannt'}"


def prepared_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for e in entries:
        n = dict(e)
        n["hour"] = parse_hour(n.get("timestamp"))
        n["day"] = parse_day(n.get("timestamp"))
        n["combo"] = combo_key(n)
        normalized.append(n)
    return normalized


def time_chart(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = prepared_entries(entries)
    groups: dict[str, dict[str, int]] = defaultdict(lambda: {"fang": 0, "gesamt": 0})

    for e in normalized:
        h = e.get("hour")
        if h is None:
            continue
        key = f"{int(h):02d}:00"
        groups[key]["gesamt"] += 1
        if success(e):
            groups[key]["fang"] += 1

    out = []
    for hour in range(24):
        key = f"{hour:02d}:00"
        g = groups.get(key, {"fang": 0, "gesamt": 0})
        total = g["gesamt"]
        out.append({
            "hour": key,
            "total": total,
            "catches": g["fang"],
            "success_rate": round(g["fang"] / total * 100, 1) if total else 0,
        })
    return out


def daily_chart(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = prepared_entries(entries)
    groups: dict[str, dict[str, int]] = defaultdict(lambda: {"fang": 0, "gesamt": 0})

    for e in normalized:
        day = e.get("day") or "Unbekannt"
        groups[day]["gesamt"] += 1
        if success(e):
            groups[day]["fang"] += 1

    out = []
    for day, g in sorted(groups.items()):
        total = g["gesamt"]
        out.append({
            "day": day,
            "total": total,
            "catches": g["fang"],
            "success_rate": round(g["fang"] / total * 100, 1) if total else 0,
        })
    return out[-30:]


def stats(entries: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(entries)
    caught = sum(1 for e in entries if success(e))
    no_catch = total - caught
    rate = calculate_rate(entries)

    normalized = prepared_entries(entries)

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
        "spot_ranking": ranking(normalized, "spot"),
        "bait_ranking": ranking(normalized, "bait"),
        "fish_ranking": ranking(normalized, "fish_type"),
        "time_chart": time_chart(normalized),
        "daily_chart": daily_chart(normalized),
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

def bite_forecast_series(
    temperature: float,
    wind_speed: float,
    pressure: float,
    cloud_coverage: float,
    precipitation: float,
    history_score: float,
    hours: int = 24,
    moon_phase: str | None = None,
    entries: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    from datetime import datetime, timedelta
    import math
    import random

    entries = entries or []
    now = datetime.now().astimezone().replace(minute=0, second=0, microsecond=0)
    points: list[dict[str, Any]] = []

    seed_base = int(now.strftime("%Y%m%d")) + int(temperature * 10) + int(pressure) + len(entries) * 17
    rng = random.Random(seed_base)

    daily_temp_shift = {}
    daily_pressure_shift = {}
    daily_wind_shift = {}
    daily_cloud_shift = {}
    daily_rain_shift = {}

    for i in range(hours):
        ts = now + timedelta(hours=i)
        day_key = ts.strftime("%Y-%m-%d")

        if day_key not in daily_temp_shift:
            day_rng = random.Random(seed_base + int(ts.strftime("%j")) * 31)
            daily_temp_shift[day_key] = day_rng.uniform(-2.2, 2.2)
            daily_pressure_shift[day_key] = day_rng.uniform(-7.5, 7.5)
            daily_wind_shift[day_key] = day_rng.uniform(-4.0, 4.5)
            daily_cloud_shift[day_key] = day_rng.uniform(-22, 22)
            daily_rain_shift[day_key] = day_rng.uniform(-0.7, 1.4)

        hour_angle = 2 * math.pi * (ts.hour / 24)
        slow_angle = 2 * math.pi * (i / 53.0)
        micro_angle = 2 * math.pi * (i / 11.0)

        temp_sim = temperature + daily_temp_shift[day_key] + math.sin(hour_angle - 1.2) * 2.4 + math.sin(slow_angle) * 0.8
        pressure_sim = pressure + daily_pressure_shift[day_key] + math.sin(slow_angle + 1.1) * 4.8 + math.sin(micro_angle) * 1.1
        wind_sim = max(0, wind_speed + daily_wind_shift[day_key] + math.sin(hour_angle + 0.7) * 3.2 + math.sin(micro_angle + 2.2) * 1.4)
        cloud_sim = min(100, max(0, cloud_coverage + daily_cloud_shift[day_key] + math.sin(slow_angle - 0.4) * 18 + math.sin(hour_angle * 2) * 9))
        rain_sim = max(0, precipitation + daily_rain_shift[day_key] + max(0, math.sin(slow_angle + 2.8)) * 1.1 - max(0, math.sin(hour_angle - 0.6)) * 0.4)
        pressure_trend = math.cos(slow_angle + 1.1) * 2.8 + math.cos(micro_angle) * 0.6 + daily_pressure_shift[day_key] * 0.10

        base_score = current_weather_score(
            temperature=temp_sim,
            wind_speed=wind_sim,
            pressure=pressure_sim,
            cloud_coverage=cloud_sim,
            precipitation=rain_sim,
            pressure_trend=pressure_trend,
            hour=ts.hour,
            month=ts.month,
            moon_phase=moon_phase,
            history_score=history_score,
        )

        morning_peak = math.exp(-((ts.hour - 7.0) ** 2) / 10.0) * rng.uniform(3.0, 8.5)
        evening_peak = math.exp(-((ts.hour - 19.0) ** 2) / 12.0) * rng.uniform(4.0, 10.0)
        midday_penalty = math.exp(-((ts.hour - 13.0) ** 2) / 18.0) * rng.uniform(0.5, 5.0)

        short_window = math.sin((i + rng.uniform(-2, 2)) / rng.uniform(3.5, 7.5))
        if short_window > 0.68:
            bite_pulse = rng.uniform(2.5, 7.5)
        elif short_window < -0.78:
            bite_pulse = -rng.uniform(2.0, 6.0)
        else:
            bite_pulse = 0

        score = base_score + morning_peak + evening_peak - midday_penalty + bite_pulse + rng.uniform(-2.2, 2.2)
        score = int(max(5, min(99, round(score))))

        points.append({
            "timestamp": ts.isoformat(),
            "x": int(ts.timestamp() * 1000),
            "y": score,
            "score": score,
            "hour": ts.strftime("%H:%M"),
            "day": ts.strftime("%Y-%m-%d"),
            "temperature": round(temp_sim, 1),
            "pressure": round(pressure_sim, 1),
            "wind_speed": round(wind_sim, 1),
            "cloud_coverage": round(cloud_sim, 0),
            "precipitation": round(rain_sim, 1),
            "pressure_trend": round(pressure_trend, 2),
        })

    if len(points) >= 3:
        smoothed = []
        for idx, p in enumerate(points):
            prev_score = points[idx - 1]["score"] if idx > 0 else p["score"]
            next_score = points[idx + 1]["score"] if idx < len(points) - 1 else p["score"]
            smooth_score = round((prev_score * 0.22) + (p["score"] * 0.56) + (next_score * 0.22))
            q = dict(p)
            q["score"] = int(max(5, min(99, smooth_score)))
            q["y"] = q["score"]
            smoothed.append(q)
        points = smoothed

    return points
