from __future__ import annotations

from typing import Any

from .analytics import success, weighted_rate


def feature_bucket(entry: dict[str, Any]) -> tuple[str, ...]:
    def bucket_num(value: Any, step: int, default: int = 0) -> str:
        try:
            v = float(value)
        except Exception:
            v = default
        return str(int(v // step * step))

    return (
        str(entry.get("fish_type") or "any"),
        str(entry.get("spot") or "any"),
        str(entry.get("bait") or "any"),
        bucket_num(entry.get("temperature"), 5, 15),
        bucket_num(entry.get("wind_speed"), 5, 10),
        bucket_num(entry.get("pressure"), 10, 1010),
    )


def similar_history_score(entries: list[dict[str, Any]], target: dict[str, Any]) -> dict[str, Any]:
    if not entries:
        return {"score": 50.0, "matches": 0, "note": "Keine historischen Daten"}

    target_bucket = feature_bucket(target)
    matches = [e for e in entries if feature_bucket(e) == target_bucket]

    if len(matches) < 3:
        matches = [
            e for e in entries
            if e.get("spot") == target.get("spot")
            or e.get("bait") == target.get("bait")
        ]

    if not matches:
        return {"score": 50.0, "matches": 0, "note": "Keine ähnlichen Bedingungen"}

    caught = sum(1 for e in matches if success(e))
    score = weighted_rate(caught, len(matches))
    return {
        "score": score,
        "matches": len(matches),
        "note": f"{caught} Fänge bei {len(matches)} ähnlichen Einträgen",
    }
