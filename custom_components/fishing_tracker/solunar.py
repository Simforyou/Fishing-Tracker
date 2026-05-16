"""
Solunar Engine für Fishing Tracker
Berechnet Mondstand-Uhrzeiten (Haupt- + Nebenbeißzeiten) nach J.A. Knight.
Kein API-Aufruf – reine Astronomie. Genauigkeit: ~5-10 Minuten.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any


def _rad(d: float) -> float:
    return d * math.pi / 180.0

def _norm(v: float) -> float:
    return v % 360.0

def _jd(dt: datetime) -> float:
    """Julianisches Datum."""
    u = dt.astimezone(timezone.utc)
    a = (14 - u.month) // 12
    y = u.year + 4800 - a
    m = u.month + 12 * a - 3
    jdn = u.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    return jdn + (u.hour + u.minute / 60.0 + u.second / 3600.0 - 12.0) / 24.0


def _moon_ra(jd: float) -> float:
    """Mondposition: Rektaszension in Stunden (Genauigkeit ~1°)."""
    D = jd - 2451545.0
    L = _norm(218.316 + 13.176396 * D)
    M = _norm(134.963 + 13.064993 * D)
    F = _norm(93.272  + 13.229350 * D)
    lon = (L
           + 6.289 * math.sin(_rad(M))
           - 1.274 * math.sin(_rad(2 * L - M))
           + 0.658 * math.sin(_rad(2 * L))
           - 0.214 * math.sin(_rad(2 * M))
           - 0.110 * math.sin(_rad(D / 365.25 * 360.0)))
    lon = _norm(lon)
    lat = 5.128 * math.sin(_rad(F))
    eps = 23.439
    ra = math.degrees(math.atan2(
        math.cos(_rad(lat)) * math.sin(_rad(lon)) * math.cos(_rad(eps))
        - math.sin(_rad(lat)) * math.sin(_rad(eps)),
        math.cos(_rad(lat)) * math.cos(_rad(lon))
    )) / 15.0
    return ra % 24.0


def _gmst(jd: float) -> float:
    """Greenwich Mean Sidereal Time in Stunden."""
    T = (jd - 2451545.0) / 36525.0
    g = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * T * T
    return _norm(g) / 15.0


def _lst(jd: float, lon: float) -> float:
    """Local Sidereal Time in Stunden."""
    return (_gmst(jd) + lon / 15.0) % 24.0


def solunar_times(
    date: datetime,
    latitude: float,
    longitude: float,
) -> dict[str, Any]:
    """
    Berechnet Solunar-Zeiten für einen Tag.

    Rückgabe:
      major1/major2 : Hauptbeißzeiten (Mondtransit oben/unten), Dauer ~2h
      minor1/minor2 : Nebenbeißzeiten (90° versetzt), Dauer ~1h
      moon_phase_factor: 1.0 (Voll/Neumond) .. 0.5 (Viertel)
      quality: "Sehr gut" / "Gut" / "Mittel" / "Schwach"
      score_bonus: 0..18 (Punkte für den Beißchancen-Score)
    """
    midnight_utc = datetime(date.year, date.month, date.day, 0, 0, 0, tzinfo=timezone.utc)
    jd0 = _jd(midnight_utc)

    ra = _moon_ra(jd0)
    lst0 = _lst(jd0, longitude)

    # Stunden bis Mondtransit (HA = 0 → LST = RA)
    dt_transit = (ra - lst0) % 24.0

    # Zeitzone-Offset des Users
    tz_off = date.utcoffset() or timedelta(0)

    def _local(dt_hours: float) -> str:
        t = midnight_utc + timedelta(hours=dt_hours) + tz_off
        return t.strftime("%H:%M")

    def _dt(dt_hours: float) -> datetime:
        return midnight_utc + timedelta(hours=dt_hours) + tz_off

    major1_h  = dt_transit
    major2_h  = (dt_transit + 12.417) % 24.0   # ~12h 25min später (Nadir)
    minor1_h  = (dt_transit + 6.208)  % 24.0
    minor2_h  = (dt_transit + 18.625) % 24.0

    # Mondphasenfaktor (Neumond/Vollmond = 1.0, Viertel = 0.6)
    moon_age = (jd0 - 2451550.1) % 29.53       # Tage seit bekanntem Neumond
    phase_angle = abs(moon_age - 14.765)        # 0=Vollmond, 14.76=Neumond
    if phase_angle <= 2.0:                      # Vollmond ±2 Tage
        factor = 1.0
        phase_label = "Vollmond"
    elif phase_angle >= 12.5:                   # Neumond ±2 Tage
        factor = 0.95
        phase_label = "Neumond"
    elif 5.5 <= phase_angle <= 9.0:             # Viertel
        factor = 0.60
        phase_label = "Viertelmond"
    else:
        factor = 0.80
        phase_label = "Zunehmend/Abnehmend"

    # Score-Bonus: 0–18 Punkte
    # Maximaler Bonus wenn aktuelle Stunde in Haupt- oder Nebenzeit liegt
    now_h = (datetime.now().astimezone() - midnight_utc.replace(tzinfo=timezone.utc) - tz_off).total_seconds() / 3600.0 % 24.0

    def _in_window(center: float, half_width: float) -> bool:
        diff = abs((now_h - center + 12) % 24 - 12)
        return diff <= half_width

    in_major = _in_window(major1_h, 1.0) or _in_window(major2_h, 1.0)
    in_minor = _in_window(minor1_h, 0.5) or _in_window(minor2_h, 0.5)

    if in_major:
        score_bonus = round(14 * factor)
    elif in_minor:
        score_bonus = round(7 * factor)
    else:
        score_bonus = 0

    if score_bonus >= 12:
        quality = "Sehr gut"
    elif score_bonus >= 7:
        quality = "Gut"
    elif score_bonus >= 3:
        quality = "Mittel"
    else:
        quality = "Kein aktives Fenster"

    return {
        "major1": _local(major1_h),
        "major2": _local(major2_h),
        "minor1": _local(minor1_h),
        "minor2": _local(minor2_h),
        "major1_dt": _dt(major1_h).isoformat(),
        "major2_dt": _dt(major2_h).isoformat(),
        "minor1_dt": _dt(minor1_h).isoformat(),
        "minor2_dt": _dt(minor2_h).isoformat(),
        "moon_phase_factor": round(factor, 2),
        "moon_phase_label": phase_label,
        "in_major_window": in_major,
        "in_minor_window": in_minor,
        "quality": quality,
        "score_bonus": score_bonus,
    }
