from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_TTL = timedelta(minutes=30)


@dataclass
class FishingWeather:
    latitude: float
    longitude: float
    source: str = "open-meteo"
    fetched_at: str | None = None
    temperature: float | None = None
    pressure: float | None = None
    pressure_trend: float | None = None
    wind_speed: float | None = None
    wind_bearing: float | None = None
    wind_gusts: float | None = None
    precipitation: float | None = None
    precipitation_probability: float | None = None
    cloud_coverage: float | None = None
    humidity: float | None = None
    dew_point: float | None = None
    uv_index: float | None = None
    sunrise: str | None = None
    sunset: str | None = None
    hourly: list[dict[str, Any]] | None = None
    daily: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_open_meteo_url(latitude: float, longitude: float) -> str:
    return (
        f"{OPEN_METEO_URL}"
        f"?latitude={latitude}"
        f"&longitude={longitude}"
        f"&current=temperature_2m,relative_humidity_2m,precipitation,"
        f"surface_pressure,cloud_cover,wind_speed_10m,wind_direction_10m,wind_gusts_10m"
        f"&hourly=temperature_2m,relative_humidity_2m,dew_point_2m,precipitation,"
        f"precipitation_probability,surface_pressure,cloud_cover,wind_speed_10m,"
        f"wind_direction_10m,wind_gusts_10m,uv_index"
        f"&daily=sunrise,sunset"
        f"&forecast_days=7"
        f"&timezone=auto"
    )


class OpenMeteoWeatherEngine:
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._cache: dict[str, Any] = {}

    async def async_get_weather(self, latitude: float, longitude: float) -> FishingWeather | None:
        key = f"{round(latitude, 4)}:{round(longitude, 4)}"
        now = datetime.now().astimezone()

        cached = self._cache.get(key)
        if cached:
            fetched = cached.get("fetched")
            if fetched and now - fetched < CACHE_TTL:
                return cached.get("weather")

        session = async_get_clientsession(self.hass)
        url = build_open_meteo_url(latitude, longitude)

        try:
            async with session.get(url, timeout=15) as response:
                if response.status != 200:
                    return None
                data = await response.json()
        except Exception:
            return None

        weather = normalize_weather_payload(data, latitude, longitude)
        self._cache[key] = {"fetched": now, "weather": weather}
        return weather


def normalize_weather_payload(data: dict[str, Any], latitude: float, longitude: float) -> FishingWeather:
    now_iso = datetime.now().astimezone().isoformat()
    current = data.get("current", {}) or {}
    hourly = data.get("hourly", {}) or {}
    daily = data.get("daily", {}) or {}

    hourly_points = _build_hourly_points(hourly)
    pressure_trend = _pressure_trend(hourly_points)

    first = hourly_points[0] if hourly_points else {}

    return FishingWeather(
        latitude=latitude,
        longitude=longitude,
        source="open-meteo",
        fetched_at=now_iso,
        temperature=_num(current.get("temperature_2m")),
        pressure=_num(current.get("surface_pressure")),
        pressure_trend=pressure_trend,
        wind_speed=_num(current.get("wind_speed_10m")),
        wind_bearing=_num(current.get("wind_direction_10m")),
        wind_gusts=_num(current.get("wind_gusts_10m")),
        precipitation=_num(current.get("precipitation")),
        precipitation_probability=_num(first.get("precipitation_probability")),
        cloud_coverage=_num(current.get("cloud_cover")),
        humidity=_num(current.get("relative_humidity_2m")),
        dew_point=_num(first.get("dew_point")),
        uv_index=_num(first.get("uv_index")),
        sunrise=(daily.get("sunrise") or [None])[0],
        sunset=(daily.get("sunset") or [None])[0],
        hourly=hourly_points,
        daily=daily,
    )


def _build_hourly_points(hourly: dict[str, Any]) -> list[dict[str, Any]]:
    times = hourly.get("time") or []
    points: list[dict[str, Any]] = []

    for idx, ts in enumerate(times[:168]):
        points.append({
            "timestamp": ts,
            "temperature": _from_list(hourly.get("temperature_2m"), idx),
            "humidity": _from_list(hourly.get("relative_humidity_2m"), idx),
            "dew_point": _from_list(hourly.get("dew_point_2m"), idx),
            "precipitation": _from_list(hourly.get("precipitation"), idx),
            "precipitation_probability": _from_list(hourly.get("precipitation_probability"), idx),
            "pressure": _from_list(hourly.get("surface_pressure"), idx),
            "cloud_coverage": _from_list(hourly.get("cloud_cover"), idx),
            "wind_speed": _from_list(hourly.get("wind_speed_10m"), idx),
            "wind_bearing": _from_list(hourly.get("wind_direction_10m"), idx),
            "wind_gusts": _from_list(hourly.get("wind_gusts_10m"), idx),
            "uv_index": _from_list(hourly.get("uv_index"), idx),
        })

    return points


def _pressure_trend(points: list[dict[str, Any]]) -> float | None:
    values = [_num(p.get("pressure")) for p in points[:4]]
    values = [v for v in values if v is not None]

    if len(values) < 2:
        return None

    return round(values[-1] - values[0], 2)


def _from_list(values: list[Any] | None, idx: int) -> Any:
    if not values or idx >= len(values):
        return None
    return values[idx]


def _num(value: Any) -> float | None:
    try:
        if value in (None, "", "unknown", "unavailable"):
            return None
        return float(value)
    except Exception:
        return None
