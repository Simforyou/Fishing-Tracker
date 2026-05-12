"""
Köder-Berater für Fishing Tracker
Implementiert die Wettermethode © (Lieblingsköder) + erweiterte Praxistipps.
Gibt Köderfarbe, Ködertyp, Tiefe und Führungsstil je Situation zurück.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


# ── Wettermethode (Lieblingsköder) ───────────────────────────────────────────

def wettermethode_color(
    cloud_coverage: float,
    turbidity_level: str,  # "klar" | "leicht_trüb" | "trüb" | "sehr_trüb"
    hour: int,
    uv_index: float | None = None,
) -> dict[str, str]:
    """
    Bestimmt Köderfarbe nach der Wettermethode © (Lieblingsköder).
    4 Grundzustände × Tageszeit-Modifikation.
    """
    sunny = cloud_coverage < 40
    dusk = hour <= 7 or hour >= 20
    bright_midday = 10 <= hour <= 15 and (uv_index or 0) >= 5

    if turbidity_level in ("sehr_trüb", "trüb"):
        if dusk:
            return {
                "farbe": "UV-aktiv / Leuchtfarben",
                "beispiele": "Sheriff, Neo, Sherriff Orange",
                "grund": "Trübes Wasser + Dämmerung: maximale Sichtbarkeit nötig",
            }
        return {
            "farbe": "Schockfarben / Kontraste",
            "beispiele": "Pinky, Mr. White, Firetiger",
            "grund": "Trübes Wasser: auffällige Köder erhöhen Auffindbarkeit",
        }

    if turbidity_level == "leicht_trüb":
        if sunny:
            return {
                "farbe": "Semi-natürlich / Kontraste",
                "beispiele": "Firetiger, Captain, Whisky Orange",
                "grund": "Leicht trüb + Sonne: optimal für Spinnfischer (Fisch sieht Köder, aber nicht die Montage)",
            }
        return {
            "farbe": "Kontraste / dezente Schockfarben",
            "beispiele": "Firetiger, Pinky, Captain",
            "grund": "Leicht trüb + Wolken: kontrastreiche Köder bevorzugt",
        }

    # Klares Wasser
    if dusk:
        return {
            "farbe": "UV-aktiv oder Naturfarben",
            "beispiele": "Sheriff (Dämmerung), Sunny, Whisky",
            "grund": "Klares Wasser + Dämmerung: UV-aktive Köder oder natürliche Imitate",
        }
    if bright_midday:
        return {
            "farbe": "Naturfarben (sehr dezent)",
            "beispiele": "Sunny, Whisky",
            "grund": "Klares Wasser + grelles Mittagslicht: Fische sehr misstrauisch",
        }
    if sunny:
        return {
            "farbe": "Naturfarben",
            "beispiele": "Sunny, Whisky, Naturdekor",
            "grund": "Klares Wasser + Sonne: natürliche Imitate am fängigsten",
        }
    return {
        "farbe": "Naturfarben / leichte Kontraste",
        "beispiele": "Whisky, Captain, Sunny Lemon",
        "grund": "Klares Wasser + Wolken: natürlich mit leichtem Kontrast",
    }


# ── Saisonal-Tageszeit-Fenster (Barsch-Alarm + Lieblingsköder) ───────────────

SEASONAL_TIME_WINDOWS: dict[str, dict[str, list[tuple[int, int]]]] = {
    # Format: Fischart → Saison → [(von_Stunde, bis_Stunde), ...]
    "Hecht": {
        "frühling":  [(5, 10), (18, 22)],
        "sommer":    [(5, 9),  (19, 23)],   # Nur Dämmerung!
        "herbst":    [(6, 11), (15, 20)],   # Beste Jahreszeit, längere Fenster
        "winter":    [(9, 14)],              # Mittag wenn etwas Sonne
    },
    "Zander": {
        "frühling":  [(5, 9),  (19, 23)],
        "sommer":    [(19, 24), (0, 3)],    # Fast nur Nacht/Abend
        "herbst":    [(6, 10), (17, 22)],
        "winter":    [(10, 15), (18, 21)],
    },
    "Barsch": {
        "frühling":  [(6, 11), (16, 20)],
        "sommer":    [(5, 9),  (18, 22)],
        "herbst":    [(7, 12), (15, 19)],
        "winter":    [(10, 15)],            # Mittag (Barsch-Alarm-Erkenntnis!)
    },
    "Karpfen": {
        "frühling":  [(5, 9),  (18, 22)],
        "sommer":    [(4, 8),  (20, 24)],
        "herbst":    [(7, 12), (16, 20)],
        "winter":    [(10, 15)],
    },
    "Schleie": {
        "frühling":  [(7, 12), (17, 21)],
        "sommer":    [(5, 9),  (18, 22)],
        "herbst":    [(8, 13)],
        "winter":    [],
    },
    "Aal": {
        "frühling":  [(20, 24), (0, 4)],
        "sommer":    [(20, 24), (0, 5)],
        "herbst":    [(18, 24), (0, 4)],
        "winter":    [(19, 23)],
    },
}

DEFAULT_WINDOWS = {
    "frühling": [(6, 11), (16, 20)],
    "sommer":   [(5, 9),  (18, 22)],
    "herbst":   [(7, 12), (15, 19)],
    "winter":   [(9, 14)],
}


def _season(month: int) -> str:
    if month in (3, 4, 5):
        return "frühling"
    if month in (6, 7, 8):
        return "sommer"
    if month in (9, 10, 11):
        return "herbst"
    return "winter"


def seasonal_time_score(fish_type: str, hour: int, month: int) -> tuple[float, str]:
    """
    Berechnet zeitlichen Score-Bonus basierend auf Fischart + Jahreszeit.
    Ersetzt/ergänzt die bisherigen fixen Stundenfenster.
    Gibt (Bonus, Beschreibung) zurück.
    """
    season = _season(month)
    windows = SEASONAL_TIME_WINDOWS.get(fish_type, {}).get(season, DEFAULT_WINDOWS.get(season, []))

    for (start, end) in windows:
        if start <= end:
            if start <= hour <= end:
                return 12.0, f"{fish_type} im {season.capitalize()}: aktives Zeitfenster ({start}–{end} Uhr)"
        else:  # Über Mitternacht
            if hour >= start or hour <= end:
                return 12.0, f"{fish_type} im {season.capitalize()}: aktives Nachtfenster"

    # Nahe am Fenster (±1h): kleiner Bonus
    for (start, end) in windows:
        near_start = (start - 1) % 24
        near_end = (end + 1) % 24
        if near_start == hour or near_end == hour:
            return 4.0, f"{fish_type}: kurz vor/nach aktivem Fenster"

    return -3.0, f"{fish_type} im {season.capitalize()}: kein aktives Zeitfenster gerade"


# ── Herbst-Fresswelle ─────────────────────────────────────────────────────────

def autumn_feeding_bonus(fish_type: str, month: int) -> float:
    """
    Herbst-Fresswelle: Raubfische fressen sich Winterreserven an.
    Oktober + November = erhöhte Aggressivität bei Hecht, Zander, Barsch.
    """
    if month not in (9, 10, 11):
        return 0.0
    bonuses = {"Hecht": 9.0, "Zander": 7.0, "Barsch": 6.0, "Schleie": 0.0}
    return bonuses.get(fish_type, 2.0)


# ── Temperaturwechsel-Geschwindigkeit ─────────────────────────────────────────

def temp_change_score(
    water_temp_now: float | None,
    water_temp_yesterday: float | None,
    fish_type: str,
    month: int,
) -> tuple[float, str]:
    """
    Bewertet die Änderungsrate der Wassertemperatur.
    Steigende Temperatur im Frühjahr = positiv für Karpfen, Schleie.
    Fallende Temperatur im Herbst = positiv für Hecht.
    Schnelle Änderungen (>3°C/Tag) = Schock, negativ für alle.
    """
    if water_temp_now is None or water_temp_yesterday is None:
        return 0.0, ""

    delta = water_temp_now - water_temp_yesterday
    season = _season(month)

    if abs(delta) >= 4.0:
        return -10.0, f"Starker Temperaturwechsel ({delta:+.1f}°C/Tag) – Fische desorganisiert"

    if abs(delta) >= 2.0:
        return -4.0, f"Merklicher Temperaturwechsel ({delta:+.1f}°C/Tag)"

    # Saisonale Bewertung
    warming = delta > 0.5
    cooling = delta < -0.5

    if season == "herbst" and cooling:
        if fish_type in ("Hecht", "Barsch"):
            return 6.0, f"Herbst-Abkühlung ({delta:+.1f}°C) – {fish_type} wird aktiver"
        return 2.0, f"Herbst-Abkühlung – Fische suchen wärmere Zonen"

    if season == "frühling" and warming:
        if fish_type in ("Karpfen", "Schleie", "Brasse"):
            return 7.0, f"Frühjahrs-Erwärmung ({delta:+.1f}°C) – {fish_type} wird aktiver"
        return 3.0, "Frühjahrs-Erwärmung belebt die Gewässer"

    if season == "sommer" and warming and water_temp_now and water_temp_now > 22:
        return -5.0, f"Sommerliche Erwärmung auf {water_temp_now}°C – O₂-kritisch für Raubfische"

    return 0.0, ""


# ── Lichtintensitätswechsel ───────────────────────────────────────────────────

def light_change_score(
    cloud_now: float,
    cloud_prev_hour: float | None,
) -> tuple[float, str]:
    """
    Plötzlicher Wechsel von bewölkt→Sonne oder umgekehrt triggert kurze Beißphase.
    (Barsch-Alarm + Lieblingsköder Beobachtung)
    """
    if cloud_prev_hour is None:
        return 0.0, ""

    change = cloud_now - cloud_prev_hour

    # Bewölkung bricht auf (Wolken → Sonne)
    if change < -25:
        return 6.0, "Sonne bricht durch Wolken: kurzes Beißfenster möglich!"

    # Plötzliche Eintrübung (Sonne → Wolken)
    if change > 25:
        return 5.0, "Plötzliche Eintrübung: Raubfische werden aktiver"

    return 0.0, ""


# ── Gesamtempfehlung ──────────────────────────────────────────────────────────

def full_bait_recommendation(
    fish_type: str,
    cloud_coverage: float,
    turbidity_level: str,
    hour: int,
    month: int,
    water_temp: float | None = None,
    uv_index: float | None = None,
) -> dict[str, Any]:
    """
    Gibt vollständige Köderempfehlung für eine Situation zurück.
    """
    color = wettermethode_color(cloud_coverage, turbidity_level, hour, uv_index)
    season = _season(month)

    # Ködertyp je Fischart + Saison
    bait_types = _bait_types(fish_type, season, water_temp)

    # Führungsstil
    style = _fishing_style(fish_type, season, water_temp, hour)

    return {
        "farbe": color["farbe"],
        "farbe_beispiele": color["beispiele"],
        "farbe_grund": color["grund"],
        "ködertypen": bait_types,
        "führungsstil": style,
        "saison": season,
        "trübung": turbidity_level,
    }


def _bait_types(fish_type: str, season: str, water_temp: float | None) -> list[str]:
    cold = water_temp is not None and water_temp < 8
    hot = water_temp is not None and water_temp > 20

    profiles: dict[str, dict] = {
        "Hecht": {
            "frühling": ["Gummifisch 15cm", "Wobbler", "Spinner"],
            "sommer":   ["Gummifisch 15cm (langsam)", "Popper (Dämmerung)"],
            "herbst":   ["Gummifisch 15–20cm", "Swimbaits", "Wobbler"],
            "winter":   ["Gummifisch 10–15cm (sehr langsam)", "Deadbait"],
        },
        "Zander": {
            "frühling": ["Gummifisch 7–10cm", "Twister", "Jig"],
            "sommer":   ["Gummifisch 10cm (Nacht)", "Twister"],
            "herbst":   ["Gummifisch 10–12cm", "Shad", "Jig"],
            "winter":   ["Gummifisch 7cm (langsam)", "Vertikalfischen"],
        },
        "Barsch": {
            "frühling": ["Gummifisch 5–8cm", "Drop-Shot", "Spinner"],
            "sommer":   ["Micro-Jig", "Drop-Shot", "Spinner"],
            "herbst":   ["Gummifisch 8cm", "Chatterbait", "Jig"],
            "winter":   ["Micro-Jig 3–5cm", "Drop-Shot", "Creature Bait"],
        },
    }

    types = profiles.get(fish_type, {}).get(season, ["Gummifisch", "Wobbler"])
    if cold:
        types = [t + " (sehr langsam führen)" for t in types[:2]]
    elif hot:
        types = [t + " (früh/abends, tief)" for t in types[:2]]
    return types


def _fishing_style(fish_type: str, season: str, water_temp: float | None, hour: int) -> str:
    cold = water_temp is not None and water_temp < 8
    hot = water_temp is not None and water_temp > 20
    night = hour >= 21 or hour <= 5

    if cold:
        return "Sehr langsam führen, lange Pausen, Köder tief halten"
    if hot and fish_type in ("Hecht", "Zander"):
        return "Tief angeln, kurze Aktivphasen in der Dämmerung nutzen"
    if night and fish_type == "Zander":
        return "Langsam jiggen, dunkle Spots mit Strömung befischen"
    if season == "herbst" and fish_type == "Hecht":
        return "Aggressiv führen, größere Köder, Kanten und Strukturen"
    if season == "winter":
        return "Sehr langsam, Pausen, Vertikalfischen wenn möglich"
    return "Mittleres Tempo, Strukturen absuchen, variieren"
