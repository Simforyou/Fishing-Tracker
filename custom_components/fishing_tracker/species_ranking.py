from __future__ import annotations

from datetime import datetime
from typing import Any

from .fish_profiles import FISH_PROFILES
from .intelligence import smart_fishing_score


def rank_species(
    *,
    weather: dict[str, Any],
    history_score: float = 50,
    moon_phase: str | None = None,
    hour: int | None = None,
    month: int | None = None,
) -> list[dict[str, Any]]:
    now = datetime.now().astimezone()
    hour = now.hour if hour is None else hour
    month = now.month if month is None else month

    ranking: list[dict[str, Any]] = []

    for fish_type, profile in FISH_PROFILES.items():
        score, explanation = smart_fishing_score(
            fish_type=fish_type,
            temperature=_num(weather.get("temperature"), 12),
            pressure=_num(weather.get("pressure"), 1015),
            pressure_trend=_num(weather.get("pressure_trend"), 0),
            wind_speed=_num(weather.get("wind_speed"), 10),
            wind_bearing=_maybe_num(weather.get("wind_bearing")),
            precipitation=_num(weather.get("precipitation"), 0),
            cloud_coverage=_num(weather.get("cloud_coverage"), 50),
            humidity=_maybe_num(weather.get("humidity")),
            dew_point=_maybe_num(weather.get("dew_point")),
            apparent_temperature=_maybe_num(weather.get("apparent_temperature")),
            uv_index=_maybe_num(weather.get("uv_index")),
            moon_phase=moon_phase,
            hour=hour,
            month=month,
            history_score=history_score,
        )

        best_window = _best_window(profile.preferred_hours)
        ranking.append({
            "fish_type": fish_type,
            "score": score,
            "level": explanation.get("level"),
            "best_time": best_window,
            "reasons": explanation.get("reasons", [])[:4],
            "warnings": explanation.get("warnings", [])[:3],
            "recommended_baits": list(profile.recommended_baits[:4]),
            "ideal_temperature": list(profile.temp_range),
        })

    ranking.sort(key=lambda x: x["score"], reverse=True)
    return ranking


def _best_window(windows) -> str:
    if not windows:
        return "--"
    start, end = windows[0]
    return f"{start:02d}:00–{end:02d}:00"


def _num(value: Any, default: float) -> float:
    try:
        if value in (None, "", "unknown", "unavailable"):
            return default
        return float(value)
    except Exception:
        return default


def _maybe_num(value: Any) -> float | None:
    try:
        if value in (None, "", "unknown", "unavailable"):
            return None
        return float(value)
    except Exception:
        return None
