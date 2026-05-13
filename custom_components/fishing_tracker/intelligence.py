from __future__ import annotations

from datetime import datetime
from typing import Any

from .fish_profiles import get_fish_profile, moon_key, normalize_fish_name, profile_summary
from .solunar import solunar_times
from .water_temperature import oxygen_score_modifier, estimate_oxygen
from .bait_advisor import (
    autumn_feeding_bonus,
    temp_change_score,
    full_bait_recommendation,
)
from .water_level import water_level_score_modifier, turbidity_score_modifier


# ══════════════════════════════════════════════════════════════════════════════
# Wissenschaftlich fundiertes Scoring-Modell v3.0
# Quellen: IGB Berlin (Arlinghaus), Guidesly Feeding Science, LAVB Brandenburg
#
# Gewichtung basiert auf Forschungslage:
#   35% Wassertemperatur    – größter Einzelfaktor (Metabolismus, O2)
#   30% Biologischer Rhythmus – Tageszeit + Dämmerung (IGB Chronotypen-Studie)
#   20% Wetter               – Licht, Wind, Regen (messbar, direkt)
#   10% Solunar / Mondphase  – Praxiserfahrung, anekdotisch belegt
#    5% Luftdrucktrend        – wissenschaftlich umstritten, nur Trend relevant
# ══════════════════════════════════════════════════════════════════════════════


def _water_temp_score(water_temp: float | None, air_temp: float, profile) -> float:
    """
    Wassertemperatur-Score (0-100).
    Direkte Wassertemp bevorzugt, Lufttemp nur als Fallback.
    Fische sind wechselblütig → Wassertemp bestimmt Stoffwechsel direkt.
    """
    # Sensorwert bevorzugen
    wt = water_temp if water_temp is not None else (air_temp * 0.7 + 4)  # grobe Schätzung
    tmin, tmax = profile.temp_range

    if tmin <= wt <= tmax:
        # Im Idealbereich: linear von 80-100%
        center = (tmin + tmax) / 2
        deviation = abs(wt - center) / ((tmax - tmin) / 2)
        return 100 - deviation * 20  # 80-100

    elif wt < tmin:
        dist = tmin - wt
        if dist <= 2:
            return 65  # leicht kalt
        elif dist <= 5:
            return 45
        elif dist <= 10:
            return 25
        else:
            return 10  # Winterlethargie

    else:  # wt > tmax
        dist = wt - tmax
        if dist <= 2:
            return 60
        elif dist <= 5:
            return 40
        elif dist <= 8:
            return 22
        else:
            return 8  # Hitzestress


def _time_score(
    hour: int,
    profile,
    sunrise_hour: float | None,
    sunset_hour: float | None,
    month: int,
) -> float:
    """
    Biologischer Rhythmus Score (0-100).
    Basiert auf artspezifischen Aktivitätskurven + Dämmerungszeit.
    IGB-Studie: Fast alle Fischarten zeigen klare Chronotypen.
    """
    # Dämmerungsfenster berechnen
    if sunrise_hour is not None and sunset_hour is not None:
        dawn_start = sunrise_hour - 0.5
        dawn_end   = sunrise_hour + 1.5
        dusk_start = sunset_hour - 1.5
        dusk_end   = sunset_hour + 0.75
        in_dawn = dawn_start <= hour <= dawn_end
        in_dusk = dusk_start <= hour <= dusk_end
    else:
        in_dawn = 5 <= hour <= 7
        in_dusk = 18 <= hour <= 21

    in_twilight = in_dawn or in_dusk
    is_night = hour < 5 or hour >= 22
    is_midday = 11 <= hour <= 14

    # Artspezifische Aktivitätsfenster
    in_window = False
    if hasattr(profile, 'preferred_hours') and profile.preferred_hours:
        for window in profile.preferred_hours:
            if len(window) == 2:
                s, e = window
                if s <= e:
                    in_window = in_window or (s <= hour <= e)
                else:
                    in_window = in_window or (hour >= s or hour <= e)

    # Basis je nach Fischart-Typ
    fish_name = profile.name.lower()

    # Nachtfische (Zander, Aal, Brasse): Nacht hoch, Tag niedrig
    if any(f in fish_name for f in ['zander', 'aal', 'brasse']):
        if is_night or in_dusk:
            base = 85
        elif in_dawn:
            base = 60
        elif is_midday:
            base = 20
        else:
            base = 35

    # Dämmerungsfische (Hecht, Karpfen, Schleie):
    elif any(f in fish_name for f in ['hecht', 'karpfen', 'schleie']):
        if in_twilight:
            base = 90
        elif is_night:
            base = 55
        elif is_midday:
            base = 30
        else:
            base = 55

    # Tagfische (Barsch, Rotauge, Rotfeder, Döbel, Rapfen, Forelle):
    else:
        if 7 <= hour <= 11:
            base = 85
        elif 15 <= hour <= 19:
            base = 72
        elif is_midday:
            base = 58
        elif is_night:
            base = 18
        else:
            base = 45

    # Bonus wenn in definiertem Aktivitätsfenster
    if in_window:
        base = min(100, base + 10)

    # Saisonaler Einfluss auf Tagesaktivität (Mai: Morgendämmerung besser)
    if month in [4, 5, 6] and in_dawn:
        base = min(100, base + 8)
    elif month in [11, 12, 1, 2] and is_midday:
        base = min(100, base + 10)  # Winter: mittags wärmer = besser

    return float(base)


def _weather_score(
    cloud_coverage: float,
    wind_speed: float,
    precipitation: float,
    wind_bearing: float | None,
    temperature: float,
    hour: int,
) -> float:
    """
    Wetterfaktoren Score (0-100).
    Licht, Wind, Regen – direkte messbare Einflüsse.
    Bewölkung bei Tagfischen wichtig (reduziert Lichtdruck).
    """
    score = 50.0  # Neutral-Basis

    # ── Bewölkung / Licht ──────────────────────────────────
    # Überbedeckter Tag: reduziert Lichtdruck → viele Arten aktiver
    if 40 <= cloud_coverage <= 85:
        score += 18  # Ideal: bedeckt ohne Starkregen
    elif cloud_coverage > 85:
        score += 8   # Sehr bedeckt: ok
    elif cloud_coverage < 20 and 9 <= hour <= 17:
        score -= 12  # Praller Sonnenschein: ungünstig
    elif cloud_coverage < 20:
        score += 5   # Klare Nacht: Mond sichtbar, gut für Nachtfische

    # ── Wind ──────────────────────────────────────────────
    # Moderater Wind: bringt O2, Nahrungseintrag, Wellenbewegung
    if 8 <= wind_speed <= 18:
        score += 12
    elif 18 < wind_speed <= 28:
        score += 4
    elif wind_speed > 35:
        score -= 20  # Sturm: sehr ungünstig
    elif wind_speed < 3:
        score -= 5   # Totale Windstille: O2-arm, träges Wasser

    # Windrichtung: SW/W günstig, N/O ungünstig (klassische Angelregel)
    if wind_bearing is not None:
        if 180 <= wind_bearing <= 270:
            score += 8   # Südwest/West: günstig
        elif 270 < wind_bearing <= 315:
            score += 4   # West/Nordwest: neutral-gut
        elif 0 <= wind_bearing <= 90:
            score -= 8   # Nord/Ost: ungünstig

    # ── Niederschlag ──────────────────────────────────────
    # Leichter Regen: erhöht Nahrungseintrag, reduziert Lichtdruck
    if 0.1 <= precipitation <= 2.0:
        score += 10
    elif 2.0 < precipitation <= 5.0:
        score += 2
    elif precipitation > 8.0:
        score -= 18  # Starkregen: Trübung, Strömung, unangenehm

    # Normiere auf 0-100
    return max(0, min(100, score))


def _solunar_score(
    moon_phase: str | None,
    latitude: float | None,
    longitude: float | None,
    hour: int,
    profile,
) -> float:
    """
    Solunar / Mondphasen Score (0-100).
    Anekdotisch belegt, Praxiserfahrung positiv.
    Voll- und Neumond + Dämmerung = beste Kombination.
    """
    score = 50.0

    # Solunar-Fenster
    if latitude is not None and longitude is not None:
        try:
            now_dt = datetime.now().astimezone()
            sol = solunar_times(now_dt, latitude, longitude)
            bonus = sol.get("score_bonus", 0)
            # Normiere: max bonus ~8 → auf 0-100 Skala
            score += bonus * 6  # +8 → +48 Punkte auf 0-100 Skala
            score = min(100, max(0, score))
        except Exception:
            pass

    # Mondphase
    mk = moon_key(moon_phase)
    moon_bonus = profile.moon_weights.get(mk, 0)
    # moon_weights sind klein (-3 bis +5) → auf 0-100 skalieren
    score += moon_bonus * 4
    score = max(0, min(100, score))

    return score


def _pressure_score(pressure_trend: float, pressure: float) -> float:
    """
    Luftdrucktrend Score (0-100).
    Wissenschaftlich: absoluter Druck kaum relevant.
    Nur der TREND hat biologische Plausibilität (Schwimmblase-Anpassung).
    Fallender Druck → kurzes Fressfenster vor Wetterumschwung.
    Stark steigender Druck → Fische reduzieren Aktivität.
    """
    score = 50.0  # Stabiler Druck = neutral

    if pressure_trend < -3.0:
        # Stark fallend: kurzes Fressfenster VOR dem Schlechtwetter
        score = 80
    elif pressure_trend < -1.5:
        score = 68
    elif pressure_trend < -0.5:
        score = 58
    elif -0.5 <= pressure_trend <= 0.5:
        score = 50  # Stabil: neutral
    elif pressure_trend < 2.0:
        score = 42
    elif pressure_trend < 4.0:
        score = 32  # Steigend: eher ungünstig
    else:
        score = 18  # Stark steigend: ungünstig

    return score


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
    water_temp: float | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    spawning_penalty: float = 0.0,
    sunrise_hour: float | None = None,
    sunset_hour: float | None = None,
    water_temp_yesterday: float | None = None,
    water_level_data: dict | None = None,
    precipitation_24h: float = 0.0,
    turbidity_ntu: float | None = None,
    cloud_prev_hour: float | None = None,
    hourly_forecast: list[dict] | None = None,
) -> tuple[int, dict[str, Any]]:

    now = datetime.now().astimezone()
    hour = now.hour if hour is None else hour
    month = now.month if month is None else month

    fish_type = normalize_fish_name(fish_type)
    profile = get_fish_profile(fish_type)

    reasons: list[str] = []
    warnings: list[str] = []

    # ══════════════════════════════════════════════════════
    # GEWICHTETES SCORING NACH WISSENSCHAFTLICHER EVIDENZ
    # ══════════════════════════════════════════════════════

    # ── 1. WASSERTEMPERATUR (35%) ──────────────────────────────────────────────
    wt_score = _water_temp_score(water_temp, temperature, profile)
    wt_contribution = wt_score * 0.35

    wt_val = water_temp if water_temp is not None else None
    tmin, tmax = profile.temp_range
    if wt_val is not None:
        if tmin <= wt_val <= tmax:
            reasons.append(f"Wassertemp. {wt_val}°C liegt im Idealbereich ({tmin}–{tmax}°C) für {profile.name}")
        elif wt_val < tmin - 5:
            warnings.append(f"Wassertemp. {wt_val}°C deutlich zu kalt – {profile.name} in Winterlethargie")
        elif wt_val < tmin:
            warnings.append(f"Wassertemp. {wt_val}°C leicht unter Idealbereich ({tmin}°C) – reduzierte Aktivität")
        elif wt_val > tmax + 5:
            warnings.append(f"Wassertemp. {wt_val}°C zu warm – {profile.name} leidet unter Sauerstoffmangel")
        else:
            warnings.append(f"Wassertemp. {wt_val}°C über Idealbereich – {profile.name} zieht sich tiefer zurück")

    # Sauerstoff-Modifikator (über Wassertemp)
    o2_extra = 0.0
    if water_temp is not None:
        o2_mod = oxygen_score_modifier(water_temp, fish_type)
        o2_extra = o2_mod * 0.15  # kleiner Zusatz
        o2_val = estimate_oxygen(water_temp)
        if o2_mod >= 3:
            reasons.append(f"Sauerstoffgehalt gut ({o2_val} mg/l)")
        elif o2_mod < -5:
            warnings.append(f"Sauerstoffgehalt kritisch ({o2_val} mg/l) – Fische stehen tiefer")

    # Temperaturwechsel-Effekt
    tc_extra = 0.0
    try:
        tc_bonus, tc_desc = temp_change_score(water_temp, water_temp_yesterday, profile.name, month)
        tc_extra = tc_bonus * 0.3
        if tc_bonus > 1:
            reasons.append(tc_desc)
        elif tc_bonus < -1:
            warnings.append(tc_desc)
    except Exception:
        pass

    # ── 2. BIOLOGISCHER RHYTHMUS / TAGESZEIT (30%) ────────────────────────────
    time_score = _time_score(hour, profile, sunrise_hour, sunset_hour, month)
    time_contribution = time_score * 0.30

    # Saisonbonus (Laichzeit etc.)
    season_extra = 0.0
    if month in getattr(profile, 'season_months', []):
        season_extra = 3.0
        reasons.append(f"Saison optimal für {profile.name}")
    else:
        season_extra = -2.0

    # Herbst-Fresswelle
    autumn_bonus = autumn_feeding_bonus(profile.name, month)
    if autumn_bonus > 0:
        season_extra += autumn_bonus * 0.5
        reasons.append(f"Herbst-Fresswelle: {profile.name} jagt aggressiv")

    # Laichzeit-Penalty
    if spawning_penalty > 0:
        season_extra -= spawning_penalty * 0.5
        if spawning_penalty >= 20:
            warnings.append(f"{profile.name} in Hauptlaichzeit – sehr wenig Beißaktivität")
        elif spawning_penalty >= 10:
            warnings.append(f"{profile.name} in Vor-/Nachlaichphase")

    # Zeitfenster-Beschreibung
    if time_score >= 80:
        reasons.append(f"Optimale Tageszeit für {profile.name} – Aktivitätspeak")
    elif time_score >= 60:
        reasons.append(f"Tageszeit für {profile.name} günstig")
    elif time_score <= 25:
        warnings.append(f"Ungünstige Tageszeit für {profile.name} – außerhalb Aktivitätsfenster")

    # ── 3. WETTERFAKTOREN (20%) ────────────────────────────────────────────────
    weather_score = _weather_score(
        cloud_coverage, wind_speed, precipitation,
        wind_bearing, temperature, hour
    )
    weather_contribution = weather_score * 0.20

    if weather_score >= 75:
        reasons.append("Wetterbedingungen sehr angelfreundlich")
    elif weather_score >= 55:
        reasons.append("Wetterbedingungen gut")
    elif weather_score <= 30:
        warnings.append("Ungünstige Wetterbedingungen (Sturm/Starkregen/Extremlicht)")

    # Wetterfront: kurzes Fressfenster vor Schlechtwetter
    if pressure_trend < -2.5 and wind_speed > 15 and cloud_coverage > 65:
        reasons.append("Wetterfront im Anzug – oft kurzes intensives Fressfenster davor")

    # ── 4. SOLUNAR / MONDPHASE (10%) ──────────────────────────────────────────
    solunar_score = _solunar_score(moon_phase, latitude, longitude, hour, profile)
    solunar_contribution = solunar_score * 0.10

    if latitude is not None and longitude is not None:
        try:
            sol = solunar_times(datetime.now().astimezone(), latitude, longitude)
            if sol.get("in_major_window"):
                reasons.append(
                    f"Solunar Hauptbeißzeit ({sol['major1']} / {sol['major2']} Uhr)"
                )
            elif sol.get("in_minor_window"):
                reasons.append(
                    f"Solunar Nebenbeißzeit aktiv ({sol['minor1']} / {sol['minor2']} Uhr)"
                )
        except Exception:
            pass

    # ── 5. LUFTDRUCKTREND (5%) ─────────────────────────────────────────────────
    pressure_score = _pressure_score(pressure_trend, pressure)
    pressure_contribution = pressure_score * 0.05

    if pressure_trend < -1.5:
        reasons.append(f"Fallender Luftdruck ({pressure_trend:+.1f} hPa/h) – mögliches Fressfenster")
    elif pressure_trend > 3.0:
        warnings.append(f"Stark steigender Luftdruck ({pressure_trend:+.1f} hPa/h) – Fische reagieren träge")

    # ── ZUSATZFAKTOREN (Pegelstand, Trübung, History) ─────────────────────────
    extra = 0.0

    # Pegelstand
    if water_level_data:
        level_mod = water_level_score_modifier(water_level_data, profile.name)
        extra += level_mod * 0.5
        label = water_level_data.get("level_label", "")
        if level_mod >= 4:
            reasons.append(f"Pegelstand günstig: {label}")
        elif level_mod <= -6:
            warnings.append(f"Pegelstand ungünstig: {label}")

    # Wassertrübung
    turb_ntu_val = turbidity_ntu or (water_level_data or {}).get("turbidity_ntu")
    try:
        turb_mod, bait_color = turbidity_score_modifier(
            turb_ntu_val, cloud_coverage, precipitation_24h, profile.name
        )
        extra += turb_mod * 0.4
        if turb_mod >= 3:
            reasons.append(f"Trübung optimal – Köderfarbe: {bait_color}")
        elif turb_mod <= -4:
            warnings.append(f"Starke Trübung – Köderfarbe: {bait_color}")
    except Exception:
        bait_color = "Naturfarben"

    # Fanghistorie (persönliches Lernmodell)
    history_extra = (history_score - 50) * 0.15
    if history_score >= 65:
        reasons.append("Eigene Fanghistorie für ähnliche Bedingungen positiv")
    elif history_score <= 35:
        warnings.append("Eigene Fanghistorie unter ähnlichen Bedingungen bisher schwächer")

    # ══════════════════════════════════════════════════════
    # FINALE BERECHNUNG
    # ══════════════════════════════════════════════════════
    total = (
        wt_contribution          # 0–35
        + time_contribution      # 0–30
        + weather_contribution   # 0–20
        + solunar_contribution   # 0–10
        + pressure_contribution  # 0–5
        + o2_extra               # kleiner O2-Bonus
        + tc_extra               # Temp-Trend
        + season_extra           # Saison
        + extra                  # Pegel/Trübung
        + history_extra          # History
    )

    final = int(max(5, min(95, round(total))))

    if final >= 80:
        level = "Sehr gut"
    elif final >= 60:
        level = "Gut"
    elif final >= 40:
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
        "score_breakdown": {
            "wassertemperatur": round(wt_contribution, 1),
            "tageszeit_rhythmus": round(time_contribution, 1),
            "wetter": round(weather_contribution, 1),
            "solunar": round(solunar_contribution, 1),
            "luftdrucktrend": round(pressure_contribution, 1),
        },
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
            "moon_phase": moon_phase,
            "spawning_penalty": spawning_penalty,
        },
    }

    return final, explanation


def intelligence_recommendation(score: int, explanation: dict[str, Any]) -> str:
    fish = explanation.get("fish_type", "Fisch")
    reasons = explanation.get("reasons", [])
    warnings = explanation.get("warnings", [])
    baits = explanation.get("recommended_baits", [])

    if score >= 80:
        intro = f"Sehr gute Bedingungen für {fish}."
    elif score >= 60:
        intro = f"Gute Bedingungen für {fish}."
    elif score >= 40:
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
