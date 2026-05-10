from __future__ import annotations

from datetime import datetime
from typing import Any


FISH_BEHAVIOR = {
    "Hecht": {
        "preferred_hours": [(6, 10), (17, 21)],
        "wind_bonus": 8,
        "pressure_falling_bonus": 10,
        "low_light_bonus": 7,
        "rain_bonus": 4,
        "temp_range": (8, 18),
        "moon_full_bonus": 3,
        "moon_new_bonus": 2,
    },
    "Zander": {
        "preferred_hours": [(18, 23), (0, 3)],
        "wind_bonus": 4,
        "pressure_falling_bonus": 8,
        "low_light_bonus": 12,
        "rain_bonus": 6,
        "temp_range": (7, 20),
        "moon_full_bonus": 7,
        "moon_new_bonus": 4,
    },
    "Barsch": {
        "preferred_hours": [(7, 11), (16, 20)],
        "wind_bonus": 5,
        "pressure_falling_bonus": 4,
        "low_light_bonus": 4,
        "rain_bonus": 2,
        "temp_range": (10, 22),
        "moon_full_bonus": 2,
        "moon_new_bonus": 2,
    },
    "Karpfen": {
        "preferred_hours": [(5, 9), (18, 23)],
        "wind_bonus": 3,
        "pressure_falling_bonus": 5,
        "low_light_bonus": 5,
        "rain_bonus": 5,
        "temp_range": (14, 26),
        "moon_full_bonus": 5,
        "moon_new_bonus": 3,
    },
    "Weißfisch": {
        "preferred_hours": [(8, 13), (15, 19)],
        "wind_bonus": 2,
        "pressure_falling_bonus": 3,
        "low_light_bonus": 2,
        "rain_bonus": 1,
        "temp_range": (10, 24),
        "moon_full_bonus": 1,
        "moon_new_bonus": 1,
    },
}


def smart_fishing_score(
    *,
    fish_type: str = "Weißfisch",
    temperature: float = 12,
    pressure: float = 1015,
    pressure_trend: float = 0,
    wind_speed: float = 10,
    wind_bearing: float | None = None,
    precipitation: float = 0,
    cloud_coverage: float = 50,
    humidity: float | None = None,
    dew_point: float | None = None,
    apparent_temperature: float | None = None,
    uv_index: float | None = None,
    moon_phase: str | None = None,
    hour: int | None = None,
    month: int | None = None,
    history_score: float = 50,
) -> tuple[int, dict[str, Any]]:
    now = datetime.now().astimezone()
    hour = now.hour if hour is None else hour
    month = now.month if month is None else month

    behavior = FISH_BEHAVIOR.get(fish_type, FISH_BEHAVIOR.get("Weißfisch"))

    score = 45.0
    reasons: list[str] = []
    warnings: list[str] = []

    # Personal history
    history_factor = (history_score - 50) * 0.35
    score += history_factor
    if history_score >= 65:
        reasons.append(f"Eigene Fanghistorie unterstützt die Prognose (+{round(history_factor,1)})")
    elif history_score <= 40:
        warnings.append("Eigene Fanghistorie ist für diese Bedingungen eher schwach")

    # Fish specific time windows
    in_window = any(start <= hour <= end if start <= end else (hour >= start or hour <= end) for start, end in behavior["preferred_hours"])
    if in_window:
        score += 10
        reasons.append(f"{fish_type}: gute typische Aktivitätszeit")
    else:
        score -= 4

    # Low light / dusk-ish heuristic
    if hour <= 7 or hour >= 19:
        score += behavior["low_light_bonus"]
        reasons.append("Dämmerung / wenig Licht begünstigt Aktivität")

    # Season factor
    if month in (4, 5, 6, 9, 10):
        score += 6
        reasons.append("Saisonfenster ist grundsätzlich gut")
    elif month in (12, 1, 2):
        score -= 7
        warnings.append("Winterphase reduziert Aktivität")

    # Temperature species range
    tmin, tmax = behavior["temp_range"]
    if tmin <= temperature <= tmax:
        score += 9
        reasons.append(f"Temperatur passt gut zu {fish_type}")
    else:
        distance = min(abs(temperature - tmin), abs(temperature - tmax))
        penalty = min(14, distance * 1.6)
        score -= penalty
        warnings.append("Temperatur liegt außerhalb des Idealbereichs")

    # Pressure absolute and trend
    if pressure_trend < -1.5:
        score += behavior["pressure_falling_bonus"]
        reasons.append("Fallender Luftdruck kann Fressfenster auslösen")
    elif pressure_trend > 2.0:
        score -= 6
        warnings.append("Stark steigender Luftdruck kann Aktivität bremsen")

    if 1008 <= pressure <= 1022:
        score += 4
        reasons.append("Luftdruck liegt im stabil nutzbaren Bereich")
    elif pressure < 995 or pressure > 1032:
        score -= 6
        warnings.append("Extremer Luftdruck wirkt eher schwierig")

    # Wind
    if 5 <= wind_speed <= 22:
        score += behavior["wind_bonus"]
        reasons.append("Wind bringt Bewegung/Sauerstoff ins Wasser")
    elif wind_speed > 35:
        score -= 12
        warnings.append("Sehr starker Wind erschwert Bedingungen")
    elif wind_speed < 2:
        score -= 3
        warnings.append("Sehr wenig Wind kann das Wasser träge machen")

    # Cloud/rain
    if 45 <= cloud_coverage <= 90:
        score += 5
        reasons.append("Bewölkung reduziert Scheuchwirkung")
    elif cloud_coverage < 15 and 10 <= hour <= 16:
        score -= 5
        warnings.append("Sehr helles Tageslicht kann vorsichtige Fische bremsen")

    if 0.1 <= precipitation <= 2.5:
        score += behavior["rain_bonus"]
        reasons.append("Leichter Regen kann Fische aktivieren")
    elif precipitation > 6:
        score -= 8
        warnings.append("Starker Regen kann Wasser und Sicht stark verändern")

    # Humidity/dew point if available
    if humidity is not None:
        if 60 <= humidity <= 90:
            score += 2
        elif humidity < 35:
            score -= 2

    # UV if available
    if uv_index is not None and uv_index >= 6 and 10 <= hour <= 16:
        score -= 4
        warnings.append("Hoher UV-Wert zur Mittagszeit ist eher ungünstig")

    # Moon
    moon = (moon_phase or "").lower()
    if "full" in moon or "voll" in moon:
        score += behavior["moon_full_bonus"]
        reasons.append("Mondphase: Vollmond-Faktor berücksichtigt")
    elif "new" in moon or "neu" in moon:
        score += behavior["moon_new_bonus"]
        reasons.append("Mondphase: Neumond-Faktor berücksichtigt")
    elif "wax" in moon or "zunehm" in moon:
        score += 2
        reasons.append("Zunehmender Mond leicht positiv")
    elif "wan" in moon or "abnehm" in moon:
        score += 1

    # Smooth bounds
    final = int(max(5, min(99, round(score))))

    if final >= 85:
        level = "Sehr gut"
    elif final >= 70:
        level = "Gut"
    elif final >= 50:
        level = "Mittel"
    else:
        level = "Schwach"

    explanation = {
        "level": level,
        "fish_type": fish_type,
        "reasons": reasons[:8],
        "warnings": warnings[:6],
        "weather_factors": {
            "temperature": temperature,
            "pressure": pressure,
            "pressure_trend": pressure_trend,
            "wind_speed": wind_speed,
            "wind_bearing": wind_bearing,
            "precipitation": precipitation,
            "cloud_coverage": cloud_coverage,
            "humidity": humidity,
            "dew_point": dew_point,
            "apparent_temperature": apparent_temperature,
            "uv_index": uv_index,
            "moon_phase": moon_phase,
        },
    }

    return final, explanation


def intelligence_recommendation(score: int, explanation: dict[str, Any]) -> str:
    fish = explanation.get("fish_type", "Fisch")
    level = explanation.get("level", "Mittel")
    reasons = explanation.get("reasons", [])
    warnings = explanation.get("warnings", [])

    if score >= 85:
        intro = f"Sehr gute Bedingungen für {fish}."
    elif score >= 70:
        intro = f"Gute Bedingungen für {fish}."
    elif score >= 50:
        intro = f"Durchschnittliche Bedingungen für {fish}."
    else:
        intro = f"Eher schwierige Bedingungen für {fish}."

    reason_text = " ".join(reasons[:3])
    warning_text = " ".join(warnings[:2])

    text = intro
    if reason_text:
        text += " " + reason_text
    if warning_text:
        text += " Achtung: " + warning_text

    return text[:255]
