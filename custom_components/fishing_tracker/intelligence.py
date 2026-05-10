from __future__ import annotations

from datetime import datetime
from typing import Any

from .fish_profiles import get_fish_profile, is_hour_in_windows, moon_key, normalize_fish_name, profile_summary


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

    fish_type = normalize_fish_name(fish_type)
    profile = get_fish_profile(fish_type)

    score = 42.0
    reasons: list[str] = []
    warnings: list[str] = []

    # Personalized learning basis
    history_factor = (history_score - 50) * 0.38
    score += history_factor
    if history_score >= 65:
        reasons.append(f"Eigene Fanghistorie ist für ähnliche Bedingungen positiv (+{round(history_factor, 1)})")
    elif history_score <= 40:
        warnings.append("Eigene Fanghistorie war unter ähnlichen Bedingungen bisher schwächer")

    # Time behavior
    if is_hour_in_windows(hour, profile.preferred_hours):
        score += 11
        reasons.append(f"{profile.name}: aktuelle Uhrzeit liegt in einem typischen Aktivitätsfenster")
    else:
        score -= 4
        warnings.append(f"{profile.name}: aktuelle Uhrzeit ist kein Hauptfenster")

    # Low light / night / dusk
    if hour <= 7 or hour >= 19:
        score += profile.low_light_weight
        if profile.low_light_weight >= 6:
            reasons.append(f"{profile.name} profitiert häufig von Dämmerung/Nacht")
        else:
            reasons.append("Wenig Licht reduziert Scheuchwirkung")
    elif uv_index is not None and uv_index >= 6:
        score -= 4
        warnings.append("Hohes Licht/UV kann vorsichtige Fische bremsen")

    # Season profile
    if month in profile.season_months:
        score += 7
        reasons.append(f"Saison passt gut zu {profile.name}")
    else:
        score -= 6
        warnings.append(f"Saison ist für {profile.name} nicht optimal")

    # Temperature range
    tmin, tmax = profile.temp_range
    if tmin <= temperature <= tmax:
        score += 10
        reasons.append(f"Temperatur liegt im Idealbereich für {profile.name}")
    else:
        distance = min(abs(temperature - tmin), abs(temperature - tmax))
        penalty = min(16, distance * 1.7)
        score -= penalty
        warnings.append(f"Temperatur liegt außerhalb des Idealbereichs für {profile.name}")

    # Pressure and trend
    if pressure_trend < -1.5:
        score += profile.pressure_falling_weight
        reasons.append("Fallender Luftdruck kann ein Fressfenster auslösen")
    elif pressure_trend > 2.0:
        score -= profile.pressure_rising_penalty
        warnings.append("Stark steigender Luftdruck kann Aktivität bremsen")
    elif -1.0 <= pressure_trend <= 1.0:
        score += 2
        reasons.append("Stabiler Luftdruck wirkt berechenbar")

    if 1008 <= pressure <= 1022:
        score += 4
        reasons.append("Luftdruck liegt im nutzbaren Normalbereich")
    elif pressure < 995 or pressure > 1032:
        score -= 7
        warnings.append("Extremer Luftdruck ist eher ungünstig")

    # Wind
    if 5 <= wind_speed <= 22:
        score += profile.wind_weight
        reasons.append("Wind bringt Sauerstoff, Bewegung und Nahrungskette in Gang")
    elif wind_speed > 35:
        score -= 12
        warnings.append("Sehr starker Wind erschwert Fischen und Standplätze")
    elif wind_speed < 2:
        score -= 3
        warnings.append("Sehr wenig Wind kann das Wasser träge machen")

    # Direction is not universally good/bad; add small stability context
    if wind_bearing is not None:
        if 180 <= wind_bearing <= 270:
            score += 2
            reasons.append("Süd-/Westwind kann aktive Uferkanten begünstigen")

    # Cloud / rain / light
    if 45 <= cloud_coverage <= 90:
        score += profile.cloud_weight
        reasons.append("Bewölkung reduziert Lichtdruck und erhöht Deckung")
    elif cloud_coverage < 15 and 10 <= hour <= 16:
        score -= 5
        warnings.append("Sehr helles Tageslicht kann vorsichtige Fische bremsen")

    if 0.1 <= precipitation <= 2.5:
        score += profile.rain_light_weight
        reasons.append("Leichter Regen kann Nahrungseintrag und Aktivität erhöhen")
    elif precipitation > 6:
        score -= profile.rain_heavy_penalty
        warnings.append("Starker Regen kann Wasser/Sicht/Standplätze negativ verändern")

    # Humidity and dew point
    if humidity is not None:
        if 60 <= humidity <= 95:
            score += 2
        elif humidity < 35:
            score -= 2

    if dew_point is not None and temperature is not None:
        # Small comfort/atmosphere indicator for humid evenings
        try:
            if abs(float(temperature) - float(dew_point)) <= 4 and hour >= 18:
                score += 2
                reasons.append("Feuchte Abendluft spricht für aktive Uferzonen")
        except Exception:
            pass

    # Moon phase by fish profile
    mk = moon_key(moon_phase)
    moon_bonus = profile.moon_weights.get(mk, 0)
    score += moon_bonus
    if moon_bonus > 0:
        reasons.append(f"Mondphase wirkt für {profile.name} leicht positiv")
    elif moon_bonus < 0:
        warnings.append(f"Mondphase wirkt für {profile.name} eher ungünstig")

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
        "fish_type": profile.name,
        "profile": profile_summary(profile.name),
        "reasons": reasons[:9],
        "warnings": warnings[:7],
        "recommended_baits": profile.recommended_baits,
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
    baits = explanation.get("recommended_baits", [])

    if score >= 85:
        intro = f"Sehr gute Bedingungen für {fish}."
    elif score >= 70:
        intro = f"Gute Bedingungen für {fish}."
    elif score >= 50:
        intro = f"Durchschnittliche Bedingungen für {fish}."
    else:
        intro = f"Eher schwierige Bedingungen für {fish}."

    text = intro

    if reasons:
        text += " " + " ".join(reasons[:2])

    if baits:
        text += f" Geeignete Köder: {', '.join(baits[:3])}."

    if warnings:
        text += " Achtung: " + " ".join(warnings[:1])

    return text[:255]
