"""Consolidated weather forecast aggregator.

Calls weather.get_forecasts service for all available weather entities and
aggregates the responses to a single mean forecast.

Replaces the deprecated `weather.xxx.attributes.forecast` reading that no longer
works since HA Core 2024.x removed forecast arrays from weather entity attributes.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Numeric forecast fields we aggregate (mean across sources)
NUMERIC_FIELDS = (
    "temperature", "templow",
    "pressure", "pressure_msl", "air_pressure",
    "wind_speed", "wind_bearing", "wind_gust_speed",
    "precipitation", "precipitation_probability",
    "cloud_coverage", "humidity", "uv_index",
    "dew_point",
)


async def _list_weather_entities(hass: HomeAssistant) -> list[str]:
    """Find every weather.* entity that supports get_forecasts."""
    entities = []
    for state in hass.states.async_all("weather"):
        # supported_features bit 1=daily, 2=hourly, 4=twice_daily (HA Core constants)
        features = state.attributes.get("supported_features", 0)
        if features and (features & 0b011):  # supports daily or hourly
            entities.append(state.entity_id)
    return entities


async def _fetch_forecast(hass: HomeAssistant, entity_id: str, forecast_type: str) -> list[dict[str, Any]]:
    """Call weather.get_forecasts service for one entity. Returns list of forecast dicts."""
    try:
        resp = await hass.services.async_call(
            "weather",
            "get_forecasts",
            {"entity_id": entity_id, "type": forecast_type},
            blocking=True,
            return_response=True,
        )
        # Response shape: {entity_id: {forecast: [...]}}
        entry = (resp or {}).get(entity_id) or {}
        forecast = entry.get("forecast") or []
        return forecast
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("get_forecasts failed for %s (%s): %s", entity_id, forecast_type, err)
        return []


def _normalize_dt(value: Any) -> str | None:
    """Normalize a forecast timestamp to a stable bucket key (ISO with hour or day)."""
    if not value:
        return None
    try:
        if isinstance(value, str):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        elif isinstance(value, datetime):
            dt = value
        else:
            return None
        # Anchor to UTC, hourly granularity
        dt_utc = dt.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
        return dt_utc.isoformat()
    except Exception:  # noqa: BLE001
        return None


def _aggregate(per_entity_forecasts: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], float]:
    """Aggregate forecasts from multiple sources.

    Returns (aggregated_list, agreement_score).
    agreement_score = 0..100 — how tightly the sources agree (100 = perfect, 0 = wildly different).
    """
    # Group forecast entries by hourly UTC timestamp
    by_time: dict[str, dict[str, list[float]]] = {}
    # Pass-through: keep one example dict per time for non-numeric fields (condition)
    sample_at_time: dict[str, dict[str, Any]] = {}

    for entity_id, forecasts in per_entity_forecasts.items():
        for f in forecasts:
            ts_raw = f.get("datetime") or f.get("forecast_time") or f.get("time")
            ts = _normalize_dt(ts_raw)
            if not ts:
                continue
            bucket = by_time.setdefault(ts, {})
            for field in NUMERIC_FIELDS:
                v = f.get(field)
                if v is None:
                    continue
                try:
                    bucket.setdefault(field, []).append(float(v))
                except (TypeError, ValueError):
                    continue
            # remember original datetime + condition (first source wins for non-numeric)
            if ts not in sample_at_time:
                sample_at_time[ts] = {
                    "datetime": ts_raw,
                    "condition": f.get("condition"),
                }

    # Build mean-per-time output
    out: list[dict[str, Any]] = []
    agreement_samples: list[float] = []  # CV (coefficient of variation) for pressure across sources

    for ts in sorted(by_time.keys()):
        entry = dict(sample_at_time[ts])
        bucket = by_time[ts]
        for field, values in bucket.items():
            if not values:
                continue
            avg = mean(values)
            entry[field] = round(avg, 2)
            # agreement metric from pressure variance (key indicator)
            if field == "pressure" and len(values) >= 2:
                spread = max(values) - min(values)  # hPa
                # 0 hPa spread = 100% agreement, 5+ hPa spread = 0%
                agreement_samples.append(max(0.0, min(100.0, 100.0 - spread * 20.0)))
        out.append(entry)

    agreement = round(mean(agreement_samples), 1) if agreement_samples else 100.0
    return out, agreement


async def get_consolidated_forecast(
    hass: HomeAssistant,
    entity_ids: list[str] | None = None,
    forecast_type: str = "hourly",
) -> dict[str, Any]:
    """Public entry: aggregate forecasts from given (or auto-discovered) entities.

    Returns:
        {
            "forecast": [...],             # aggregated, hourly, sorted by time
            "sources_active": [entity_ids that returned data],
            "sources_attempted": [entity_ids tried],
            "agreement_score": 0..100,     # how consistent the sources are
            "last_update": iso_utc,
        }
    """
    if entity_ids is None:
        entity_ids = await _list_weather_entities(hass)

    per_entity: dict[str, list[dict[str, Any]]] = {}
    for ent in entity_ids:
        forecasts = await _fetch_forecast(hass, ent, forecast_type)
        if forecasts:
            per_entity[ent] = forecasts

    forecast, agreement = _aggregate(per_entity)

    return {
        "forecast": forecast,
        "sources_active": list(per_entity.keys()),
        "sources_attempted": entity_ids,
        "agreement_score": agreement,
        "forecast_type": forecast_type,
        "last_update": datetime.now(timezone.utc).isoformat(),
    }
