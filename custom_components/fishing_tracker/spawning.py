"""
Laichzeiten-Kalender für Fishing Tracker.
Gibt für jeden Monat/Tag Laichstatus und Score-Penalty je Fischart zurück.

Phasen:
  pre   = 2 Wochen vor Laichzeit  → mäßige Aktivität, Penalty leicht
  main  = Hauptlaichzeit           → kaum Beißen, hohe Penalty
  post  = 1 Woche nach Laichzeit  → Erholung, Penalty mittel
  none  = keine Laichzeit
"""
from __future__ import annotations

from typing import Any


# Laichkalender: (Fischart, Hauptlaich-Start-Monat, Start-Tag, End-Monat, End-Tag)
# Quellen: LAVB, DWV, Anglerpraxis
SPAWNING_CALENDAR: list[dict[str, Any]] = [
    # Raubfische
    {"fish": "Hecht",    "start_m": 2, "start_d": 15, "end_m": 4, "end_d": 30, "penalty_main": 25, "penalty_pre": 8},
    {"fish": "Zander",   "start_m": 4, "start_d":  1, "end_m": 5, "end_d": 31, "penalty_main": 28, "penalty_pre": 10},
    {"fish": "Barsch",   "start_m": 3, "start_d": 15, "end_m": 5, "end_d": 15, "penalty_main": 18, "penalty_pre": 6},
    # Friedfische
    {"fish": "Karpfen",  "start_m": 5, "start_d": 15, "end_m": 6, "end_d": 30, "penalty_main": 22, "penalty_pre": 8},
    {"fish": "Schleie",  "start_m": 5, "start_d":  1, "end_m": 7, "end_d": 15, "penalty_main": 20, "penalty_pre": 7},
    {"fish": "Brasse",   "start_m": 5, "start_d": 15, "end_m": 6, "end_d": 30, "penalty_main": 18, "penalty_pre": 6},
    {"fish": "Rotauge",  "start_m": 4, "start_d": 15, "end_m": 6, "end_d":  1, "penalty_main": 15, "penalty_pre": 5},
    {"fish": "Rotfeder", "start_m": 5, "start_d":  1, "end_m": 6, "end_d": 30, "penalty_main": 15, "penalty_pre": 5},
    {"fish": "Weißfisch","start_m": 4, "start_d":  1, "end_m": 6, "end_d": 15, "penalty_main": 12, "penalty_pre": 4},
    # Aal laicht nicht in Binnengewässern (wandert zum Sargasso-Meer)
    {"fish": "Aal",      "start_m": 10,"start_d":  1, "end_m": 11,"end_d": 30, "penalty_main": 10, "penalty_pre": 3},
]

_PRE_DAYS  = 14   # Tage vor Laichbeginn = Pre-Laichphase
_POST_DAYS = 10   # Tage nach Laichende  = Post-Laichphase


def _day_of_year(month: int, day: int) -> int:
    """Vereinfachte Tagnummer im Jahr (ignoriert Schaltjahr)."""
    days_before = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    return days_before[month - 1] + day


def spawning_penalty(fish_type: str, month: int, day: int = 15) -> float:
    """
    Gibt den Laich-Penalty für eine Fischart und einen Zeitpunkt zurück.
    0.0 = keine Einschränkung, bis 28.0 = Hauptlaichzeit.
    """
    fish_lower = fish_type.lower()
    doy = _day_of_year(month, day)

    for entry in SPAWNING_CALENDAR:
        if entry["fish"].lower() != fish_lower:
            continue

        start = _day_of_year(entry["start_m"], entry["start_d"])
        end   = _day_of_year(entry["end_m"],   entry["end_d"])

        # Pre-Laich
        pre_start = start - _PRE_DAYS
        if pre_start <= doy < start:
            return float(entry["penalty_pre"])

        # Hauptlaichzeit
        if start <= doy <= end:
            return float(entry["penalty_main"])

        # Post-Laich
        post_end = end + _POST_DAYS
        if end < doy <= post_end:
            return float(entry["penalty_pre"]) * 0.6

    return 0.0


def spawning_status(month: int, day: int = 15) -> list[dict[str, Any]]:
    """
    Gibt für alle Fischarten den aktuellen Laichstatus zurück.
    Rückgabe: [{fish, phase, penalty, note}]
    """
    doy = _day_of_year(month, day)
    result: list[dict[str, Any]] = []

    for entry in SPAWNING_CALENDAR:
        start = _day_of_year(entry["start_m"], entry["start_d"])
        end   = _day_of_year(entry["end_m"],   entry["end_d"])
        pre_start = start - _PRE_DAYS
        post_end  = end   + _POST_DAYS

        if pre_start <= doy < start:
            phase = "pre"
            penalty = float(entry["penalty_pre"])
            note = f"Vor-Laichphase – {start - doy} Tage bis Laichbeginn"
        elif start <= doy <= end:
            phase = "main"
            penalty = float(entry["penalty_main"])
            note = f"Hauptlaichzeit ({entry['start_m']:02d}/{entry['start_d']:02d}–{entry['end_m']:02d}/{entry['end_d']:02d})"
        elif end < doy <= post_end:
            phase = "post"
            penalty = float(entry["penalty_pre"]) * 0.6
            note = f"Nach-Laichphase – Erholung ({doy - end} Tage nach Ende)"
        else:
            phase = "none"
            penalty = 0.0
            note = "Keine Laichzeit"

        result.append({
            "fish": entry["fish"],
            "phase": phase,
            "penalty": round(penalty, 1),
            "note": note,
        })

    return result
