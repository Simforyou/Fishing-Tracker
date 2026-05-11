from __future__ import annotations

from datetime import datetime
from typing import Any

from .fish_profiles import get_fish_profile, is_hour_in_windows, moon_key, normalize_fish_name, profile_summary
from .solunar import solunar_times
from .water_temperature import oxygen_score_modifier, estimate_oxygen, oxygen_level_label
from .bait_advisor import (
    seasonal_time_score, autumn_feeding_bonus,
    temp_change_score, light_change_score,
    turbidity_score_modifier, full_bait_recommendation,
    wettermethode_color,
)
from .water_level import water_level_score_modifier


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
    # v2.8 Parameter
    water_temp: float | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    spawning_penalty: float = 0.0,
    sunrise_hour: float | None = None,
    sunset_hour: float | None = None,
    # v2.9 Parameter
    water_temp_yesterday: float | None = None,
    water_level_data: dict | None = None,
    precipitation_24h: float = 0.0,
    turbidity_ntu: float | None = None,
    cloud_prev_hour: float | None = None,
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

    # ── Solunar-Zeiten ────────────────────────────────────────────────────────
    if latitude is not None and longitude is not None:
        try:
            now_dt = datetime.now().astimezone()
            sol = solunar_times(now_dt, latitude, longitude)
            bonus = sol.get("score_bonus", 0)
            score += bonus
            if sol.get("in_major_window"):
                reasons.append(
                    f"Solunar: Aktive Hauptbeißzeit ({sol['major1']} / {sol['major2']} Uhr) – {sol['moon_phase_label']}"
                )
            elif sol.get("in_minor_window"):
                reasons.append(
                    f"Solunar: Nebenbeißzeit aktiv ({sol['minor1']} / {sol['minor2']} Uhr)"
                )
            elif bonus == 0:
                warnings.append(
                    f"Solunar: Kein aktives Fenster. Hauptzeiten: {sol['major1']} / {sol['major2']} Uhr"
                )
        except Exception:
            pass

    # ── Echter Sonnenauf-/untergang (statt fixer Stunden) ────────────────────
    if sunrise_hour is not None and sunset_hour is not None:
        dawn_start = sunrise_hour - 0.75
        dawn_end   = sunrise_hour + 1.5
        dusk_start = sunset_hour - 1.5
        dusk_end   = sunset_hour + 0.75
        in_dawn = dawn_start <= hour <= dawn_end
        in_dusk = dusk_start <= hour <= dusk_end
        if in_dawn or in_dusk:
            score += profile.low_light_weight
            reasons.append("Dämmerungszeit: erhöhte Aktivität an Uferzonen")
    # Fallback wenn keine Sonnenzeiten bekannt: bisherige Festwerte bleiben aus
    # dem vorhandenen Block (hour <= 7 or hour >= 19) erhalten

    # ── Sauerstoffgehalt aus Wassertemperatur ─────────────────────────────────
    if water_temp is not None:
        o2_mod = oxygen_score_modifier(water_temp, fish_type)
        score += o2_mod
        o2_val = estimate_oxygen(water_temp)
        if o2_mod >= 3:
            reasons.append(f"Sauerstoffgehalt sehr gut ({o2_val} mg/l bei {water_temp}°C Wassertemp.)")
        elif o2_mod < -5:
            warnings.append(f"Sauerstoffgehalt kritisch ({o2_val} mg/l) – Fische stehen tiefer/träger")
        elif o2_mod < 0:
            warnings.append(f"Sauerstoffgehalt leicht eingeschränkt ({o2_val} mg/l)")

        # Artspezifischer Wassertemperatur-Check (präziser als Lufttemp-Schätzung)
        tmin, tmax = profile.temp_range
        if tmin <= water_temp <= tmax:
            score += 6
            reasons.append(f"Wassertemperatur ({water_temp}°C) liegt im Idealbereich für {profile.name}")
        else:
            dist = min(abs(water_temp - tmin), abs(water_temp - tmax))
            pen = min(14, dist * 1.8)
            score -= pen
            warnings.append(f"Wassertemperatur ({water_temp}°C) außerhalb des Idealbereichs für {profile.name}")

    # ── Laichzeit-Penalty ─────────────────────────────────────────────────────
    if spawning_penalty > 0:
        score -= spawning_penalty
        if spawning_penalty >= 20:
            warnings.append(f"{profile.name} befindet sich in der Hauptlaichzeit – sehr wenig Beißaktivität")
        elif spawning_penalty >= 10:
            warnings.append(f"{profile.name} in Vor-/Nachlaichphase – Aktivität reduziert")

    # ── Wetterfront-Erkennung (kombinierter Faktor) ───────────────────────────
    # Schneller Druckabfall + Wind + steigende Bewölkung = kommende Front
    front_score = 0.0
    if pressure_trend < -2.5:
        front_score += 1
    if wind_speed > 20:
        front_score += 1
    if cloud_coverage > 70:
        front_score += 1
    if front_score >= 2:
        score += 6
        reasons.append("Wetterfront im Anzug: kurzes Fressfenster vor dem Schlechtwetter")
    elif pressure_trend > 4.0 and cloud_coverage < 20:
        score -= 8
        warnings.append("Stabiles Hochdruckwetter mit klarem Himmel – oft ruhige Phase")

    # ── Windrichtung (vollständig) ────────────────────────────────────────────
    if wind_bearing is not None:
        if 180 <= wind_bearing <= 270:
            score += 4
            reasons.append("Süd-/Westwind: klassisch günstiger Angelwind")
        elif 0 <= wind_bearing <= 90:
            score -= 4
            warnings.append("Nord-/Ostwind gilt als ungünstig für viele Fischarten")

    # ── Saisonal-Tageszeit (Lieblingsköder + Barsch-Alarm) ────────────────────
    try:
        time_bonus, time_desc = seasonal_time_score(profile.name, hour, month)
        score += time_bonus
        if time_bonus >= 8:
            reasons.append(time_desc)
        elif time_bonus <= -2:
            warnings.append(time_desc)
    except Exception:
        pass

    # ── Herbst-Fresswelle (Oktober/November Raubfisch-Bonus) ─────────────────
    autumn_bonus = autumn_feeding_bonus(profile.name, month)
    if autumn_bonus > 0:
        score += autumn_bonus
        reasons.append(f"Herbst-Fresswelle: {profile.name} jagt aggressiv (+{autumn_bonus:.0f})")

    # ── Temperaturwechsel-Geschwindigkeit ─────────────────────────────────────
    try:
        tc_bonus, tc_desc = temp_change_score(water_temp, water_temp_yesterday, profile.name, month)
        if tc_bonus != 0.0:
            score += tc_bonus
            if tc_bonus > 0:
                reasons.append(tc_desc)
            else:
                warnings.append(tc_desc)
    except Exception:
        pass

    # ── Pegelstand ────────────────────────────────────────────────────────────
    if water_level_data:
        level_mod = water_level_score_modifier(water_level_data, profile.name)
        score += level_mod
        label = water_level_data.get("level_label", "")
        if level_mod >= 4:
            reasons.append(f"Pegelstand günstig: {label}")
        elif level_mod <= -6:
            warnings.append(f"Pegelstand ungünstig: {label} ({water_level_data.get('value_cm', '?')} cm)")

    # ── Wassertrübung + Wettermethode Köderfarbe ──────────────────────────────
    turb_ntu = turbidity_ntu or (water_level_data or {}).get("turbidity_ntu")
    try:
        turb_mod, bait_color = turbidity_score_modifier(
            turb_ntu, cloud_coverage, precipitation_24h, profile.name
        )
        score += turb_mod
        if turb_mod >= 3:
            reasons.append(f"Trübung optimal – Wettermethode: {bait_color}")
        elif turb_mod <= -4:
            warnings.append(f"Starke Trübung – Wettermethode: {bait_color}")
    except Exception:
        bait_color = "Naturfarben"

    # ── Lichtintensitätswechsel ───────────────────────────────────────────────
    try:
        light_bonus, light_desc = light_change_score(cloud_coverage, cloud_prev_hour)
        if light_bonus > 0:
            score += light_bonus
            reasons.append(light_desc)
    except Exception:
        pass

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
            "water_temp": water_temp,
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
            "spawning_penalty": spawning_penalty,
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
