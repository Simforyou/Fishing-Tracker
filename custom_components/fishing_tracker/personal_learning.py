"""
Personal Learning Engine für Fishing Tracker.

Lernt aus der persönlichen Fang- und Schneider-Historie präzise Muster:
- Welche Bedingungen führen bei welcher Fischart zum Erfolg?
- Erfolgsrate je (Art × Tageszeit × Druck × Solar × Mond × Temperatur)
- Beste Spots und Köder je Art

Erzeugt einen personalisierten Bonus der in die Score-Engine einfließt.
Confidence wächst mit Datenmenge → bei wenig Daten geringer Einfluss.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any


# ── Bucketing-Funktionen ────────────────────────────────────────────────────

def _hour_bucket(hour: int) -> str:
    if hour < 5:   return "nacht"
    if hour < 9:   return "morgen"
    if hour < 12:  return "vormittag"
    if hour < 15:  return "mittag"
    if hour < 18:  return "nachmittag"
    if hour < 22:  return "abend"
    return "nacht"


def _pressure_bucket(pressure: float, trend: float = 0.0) -> str:
    if trend < -1.5:  return "fallend"
    if trend > 1.5:   return "steigend"
    if pressure >= 1020: return "hoch_stabil"
    if pressure <= 1005: return "tief_stabil"
    return "normal"


def _solar_bucket(solar: float) -> str:
    if solar < 30:   return "dunkel"
    if solar < 150:  return "daemmrig"
    if solar < 400:  return "mittel"
    if solar < 700:  return "hell"
    return "intensiv"


def _temp_bucket(temp: float) -> str:
    if temp < 5:   return "kalt"
    if temp < 12:  return "kuehl"
    if temp < 20:  return "mild"
    if temp < 26:  return "warm"
    return "heiss"


def _water_temp_bucket(wt: float | None) -> str:
    if wt is None: return "unbekannt"
    if wt < 6:   return "sehr_kalt"
    if wt < 12:  return "kalt"
    if wt < 18:  return "mild"
    if wt < 23:  return "warm"
    return "heiss"


def _cloud_bucket(cloud: float) -> str:
    if cloud < 25:  return "klar"
    if cloud < 60:  return "leicht_bewoelkt"
    if cloud < 85:  return "bewoelkt"
    return "bedeckt"


def _wind_bucket(wind: float) -> str:
    if wind < 8:   return "windstill"
    if wind < 18:  return "maessig"
    if wind < 30:  return "frisch"
    return "stark"


def moon_phase_value(date: datetime) -> float:
    """0=Neumond, 14.76=Vollmond, Zyklus 29.53 Tage."""
    ref = datetime(2000, 1, 6)
    diff = (date - ref).total_seconds() / 86400.0
    return (diff % 29.53059 + 29.53059) % 29.53059


def _moon_bucket(date: datetime) -> str:
    phase = moon_phase_value(date)
    if phase < 3.7 or phase > 25.8:  return "neumond"
    if 11 < phase < 18.5:            return "vollmond"
    if phase <= 11:                  return "zunehmend"
    return "abnehmend"


# Welche Felder werden gelernt + wie stark sie gewichtet werden
_DIMENSIONS = {
    "hour":      (lambda e, dt: _hour_bucket(dt.hour),                        1.4),
    "pressure":  (lambda e, dt: _pressure_bucket(e.get("pressure", 1013),
                                                 e.get("pressure_trend", 0)), 1.2),
    "solar":     (lambda e, dt: _solar_bucket(e.get("solar_radiation") or 0), 1.1),
    "temp":      (lambda e, dt: _temp_bucket(e.get("temperature", 12)),       0.8),
    "water":     (lambda e, dt: _water_temp_bucket(e.get("water_temp")),      1.0),
    "cloud":     (lambda e, dt: _cloud_bucket(e.get("cloud_coverage", 50)),   0.7),
    "wind":      (lambda e, dt: _wind_bucket(e.get("wind_speed", 10)),        0.6),
    "moon":      (lambda e, dt: _moon_bucket(dt),                             0.9),
}


def _parse_dt(entry: dict) -> datetime | None:
    ts = entry.get("timestamp")
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def compute_personal_patterns(entries: list[dict]) -> dict[str, Any]:
    """
    Analysiert alle Einträge und baut pro Fischart eine Erfolgsmatrix.

    Rückgabe:
    {
      "Rotauge": {
        "total_catches": 8, "total_attempts": 11, "base_rate": 0.73,
        "dimensions": {
          "hour": {"morgen": {"c": 5, "n": 1, "rate": 0.83}, ...},
          "pressure": {...}, ...
        },
        "best_spots": [["Vechte", 5], ["Dinkel", 3]],
        "best_baits": [["Made", 4], ["Mais", 2]],
        "confidence": 0.55
      },
      ...
    }
    """
    by_fish: dict[str, dict] = {}

    for e in entries:
        fish = e.get("fish_type")
        if not fish:
            continue
        dt = _parse_dt(e)
        if dt is None:
            continue
        caught = int(e.get("caught", 0) or 0)
        is_catch = caught > 0

        fd = by_fish.setdefault(fish, {
            "total_catches": 0, "total_attempts": 0,
            "dimensions": {dim: {} for dim in _DIMENSIONS},
            "spots": {}, "baits": {},
            "spot_stats": {}, "bait_conditions": {}, "size_data": [],
        })
        fd["total_attempts"] += 1
        if is_catch:
            fd["total_catches"] += 1

        # Dimensionen bucketen
        for dim, (fn, _w) in _DIMENSIONS.items():
            try:
                bucket = fn(e, dt)
            except Exception:
                continue
            slot = fd["dimensions"][dim].setdefault(bucket, {"c": 0, "n": 0})
            if is_catch:
                slot["c"] += 1
            else:
                slot["n"] += 1

        # Spot-spezifische Erfolgsrate (Fänge UND Versuche je Spot)
        spot = e.get("spot")
        if spot:
            sp = fd.setdefault("spot_stats", {}).setdefault(spot, {"c": 0, "n": 0})
            if is_catch: sp["c"] += 1
            else: sp["n"] += 1

        # Köder × Wassertemperatur lernen
        bait = e.get("bait")
        if bait and is_catch:
            wt = e.get("water_temp")
            wt_bucket = _water_temp_bucket(wt)
            bc = fd.setdefault("bait_conditions", {}).setdefault(bait, {})
            bc[wt_bucket] = bc.get(wt_bucket, 0) + 1

        # Spots & Köder (nur Fänge zählen)
        if is_catch:
            if spot:
                fd["spots"][spot] = fd["spots"].get(spot, 0) + 1
            if bait:
                fd["baits"][bait] = fd["baits"].get(bait, 0) + 1
            # Fanggrößen-Korrelation: bei welchen Bedingungen große Fische?
            length = e.get("length_cm")
            try:
                length = float(length) if length else 0
            except Exception:
                length = 0
            if length > 0:
                sz = fd.setdefault("size_data", [])
                sz.append({
                    "length": length,
                    "hour_bucket": _hour_bucket(dt.hour),
                    "pressure_bucket": _pressure_bucket(e.get("pressure", 1013), e.get("pressure_trend", 0)),
                    "moon_bucket": _moon_bucket(dt),
                    "water_bucket": _water_temp_bucket(e.get("water_temp")),
                })

    # Raten + Confidence berechnen
    result: dict[str, Any] = {}
    for fish, fd in by_fish.items():
        attempts = fd["total_attempts"]
        catches = fd["total_catches"]
        base_rate = catches / attempts if attempts else 0.0

        dims_out = {}
        for dim, buckets in fd["dimensions"].items():
            dims_out[dim] = {}
            for bucket, sl in buckets.items():
                tot = sl["c"] + sl["n"]
                dims_out[dim][bucket] = {
                    "c": sl["c"], "n": sl["n"],
                    "rate": round(sl["c"] / tot, 3) if tot else 0.0,
                }

        # Confidence: 0 bei <3 Einträgen, 1.0 bei >=25
        confidence = max(0.0, min(1.0, (attempts - 3) / 22)) if attempts >= 3 else 0.0

        # Spot-Erfolgsraten
        spot_rates = {}
        for sp_name, sp in fd.get("spot_stats", {}).items():
            tot = sp["c"] + sp["n"]
            if tot >= 2:
                spot_rates[sp_name] = {"rate": round(sp["c"]/tot, 2), "catches": sp["c"], "attempts": tot}

        # Köder × Wassertemperatur (bester Köder je Temperaturbereich)
        bait_by_temp = {}
        for bait_name, conds in fd.get("bait_conditions", {}).items():
            for wt_bucket, cnt in conds.items():
                slot = bait_by_temp.setdefault(wt_bucket, {})
                slot[bait_name] = slot.get(bait_name, 0) + cnt
        bait_recommendations = {}
        for wt_bucket, baits in bait_by_temp.items():
            top = max(baits.items(), key=lambda x: x[1])
            bait_recommendations[wt_bucket] = {"bait": top[0], "count": top[1]}

        # Fanggrößen-Muster: bei welchen Bedingungen die größten Fische?
        size_insights = {}
        sizes = fd.get("size_data", [])
        if len(sizes) >= 3:
            avg_len = sum(s["length"] for s in sizes) / len(sizes)
            big_fish = [s for s in sizes if s["length"] > avg_len * 1.15]
            if big_fish:
                from collections import Counter
                for dim_key in ["hour_bucket", "pressure_bucket", "moon_bucket", "water_bucket"]:
                    cnt = Counter(s[dim_key] for s in big_fish)
                    if cnt:
                        top = cnt.most_common(1)[0]
                        if top[1] >= 2:
                            size_insights[dim_key] = {"bucket": top[0], "count": top[1]}
                size_insights["avg_length"] = round(avg_len, 1)
                size_insights["max_length"] = round(max(s["length"] for s in sizes), 1)

        result[fish] = {
            "total_catches": catches,
            "total_attempts": attempts,
            "base_rate": round(base_rate, 3),
            "dimensions": dims_out,
            "best_spots": sorted(fd["spots"].items(), key=lambda x: -x[1])[:5],
            "best_baits": sorted(fd["baits"].items(), key=lambda x: -x[1])[:5],
            "spot_rates": spot_rates,
            "bait_by_temp": bait_recommendations,
            "size_insights": size_insights,
            "confidence": round(confidence, 2),
        }

    return result


def get_personal_bonus(
    patterns: dict[str, Any],
    fish: str,
    conditions: dict[str, Any],
    date: datetime | None = None,
) -> dict[str, Any]:
    """
    Berechnet den persönlichen Bonus für aktuelle Bedingungen.

    conditions: {pressure, pressure_trend, solar_radiation, temperature,
                 water_temp, cloud_coverage, wind_speed, hour}
    Rückgabe: {"bonus": float, "confidence": float, "matches": [...], "reason": str}
    """
    fp = patterns.get(fish)
    if not fp or fp.get("total_attempts", 0) < 3:
        return {"bonus": 0.0, "confidence": 0.0, "matches": [], "reason": "Zu wenig Daten"}

    date = date or datetime.now()
    base_rate = fp["base_rate"]
    confidence = fp["confidence"]

    # Synthetisches Entry-Objekt für Bucketing
    synth = {
        "pressure": conditions.get("pressure", 1013),
        "pressure_trend": conditions.get("pressure_trend", 0),
        "solar_radiation": conditions.get("solar_radiation", 0),
        "temperature": conditions.get("temperature", 12),
        "water_temp": conditions.get("water_temp"),
        "cloud_coverage": conditions.get("cloud_coverage", 50),
        "wind_speed": conditions.get("wind_speed", 10),
    }
    hour = conditions.get("hour", date.hour)
    synth_dt = date.replace(hour=int(hour)) if 0 <= int(hour) <= 23 else date

    total_weighted_delta = 0.0
    total_weight = 0.0
    matches = []

    for dim, (fn, weight) in _DIMENSIONS.items():
        try:
            bucket = fn(synth, synth_dt)
        except Exception:
            continue
        dim_data = fp["dimensions"].get(dim, {})
        slot = dim_data.get(bucket)
        if not slot:
            continue
        tot = slot["c"] + slot["n"]
        if tot < 1:
            continue
        # Wie weicht die Bucket-Rate von der Basis-Rate ab?
        delta = slot["rate"] - base_rate
        # Sample-Gewicht: mehr Daten = mehr Vertrauen
        sample_weight = min(1.0, tot / 5.0)
        eff_weight = weight * sample_weight
        total_weighted_delta += delta * eff_weight
        total_weight += eff_weight
        if abs(delta) > 0.1 and tot >= 2:
            matches.append({
                "dim": dim, "bucket": bucket,
                "rate": slot["rate"], "samples": tot,
                "positive": delta > 0,
            })

    if total_weight == 0:
        return {"bonus": 0.0, "confidence": confidence, "matches": [], "reason": "Keine passenden Muster"}

    avg_delta = total_weighted_delta / total_weight
    # Bonus skaliert: delta von +0.3 (30% über Schnitt) → +18 Punkte bei voller Confidence
    raw_bonus = avg_delta * 60.0
    bonus = raw_bonus * confidence
    bonus = max(-20.0, min(20.0, bonus))

    matches.sort(key=lambda m: -abs(m["rate"] - base_rate))

    return {
        "bonus": round(bonus, 1),
        "confidence": confidence,
        "base_rate": base_rate,
        "matches": matches[:4],
        "reason": f"{fp['total_catches']}/{fp['total_attempts']} Fänge analysiert",
    }


def summarize_for_sensor(patterns: dict[str, Any]) -> dict[str, Any]:
    """Kompakte Zusammenfassung für Sensor-Attribute (klein halten)."""
    out = {}
    for fish, fp in patterns.items():
        if fp["total_attempts"] < 3:
            continue
        # Beste Bedingung je Dimension finden
        best = {}
        for dim, buckets in fp["dimensions"].items():
            scored = [(b, d["rate"], d["c"] + d["n"]) for b, d in buckets.items() if (d["c"] + d["n"]) >= 2]
            if scored:
                top = max(scored, key=lambda x: x[1])
                if top[1] > fp["base_rate"]:
                    best[dim] = {"bucket": top[0], "rate": top[1]}
        out[fish] = {
            "catches": fp["total_catches"],
            "attempts": fp["total_attempts"],
            "rate": fp["base_rate"],
            "confidence": fp["confidence"],
            "best_conditions": best,
            "best_spots": fp["best_spots"][:3],
            "best_baits": fp["best_baits"][:3],
            "spot_rates": fp.get("spot_rates", {}),
            "bait_by_temp": fp.get("bait_by_temp", {}),
            "size_insights": fp.get("size_insights", {}),
        }
    return out
