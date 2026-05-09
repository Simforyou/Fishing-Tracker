from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import csv

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION


class FishingStore:
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.data: dict[str, Any] = {"entries": []}

    async def async_load(self) -> None:
        data = await self._store.async_load()
        if isinstance(data, dict):
            self.data = data
        if "entries" not in self.data:
            self.data["entries"] = []

    async def async_save(self) -> None:
        await self._store.async_save(self.data)

    @property
    def entries(self) -> list[dict[str, Any]]:
        return self.data.setdefault("entries", [])

    async def async_add_entry(self, entry: dict[str, Any]) -> None:
        self.entries.append(entry)
        await self.async_save()

    async def async_import_csv(self, path: str) -> int:
        file_path = Path(path)
        if not file_path.exists():
            return 0

        imported = 0
        with file_path.open(newline="", encoding="utf-8") as f:
            for row in csv.reader(f):
                if len(row) < 13:
                    continue
                entry = {
                    "timestamp": row[0],
                    "angler": row[1],
                    "latitude": _none(row[2]),
                    "longitude": _none(row[3]),
                    "fish_type": row[4],
                    "caught": _to_int(row[5]),
                    "spot": row[6],
                    "bait": row[7],
                    "chance": _to_float(row[8]),
                    "pressure": _to_float(row[9], 1015),
                    "pressure_trend": _to_float(row[10]),
                    "wind_speed": _to_float(row[11]),
                    "temperature": _to_float(row[12]),
                    "length_cm": row[13] if len(row) >= 14 else "Unbekannt",
                    "source": "csv_import",
                }
                self.entries.append(entry)
                imported += 1

        await self.async_save()
        return imported

    async def async_export_csv(self, path: str) -> int:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with file_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for e in self.entries:
                writer.writerow([
                    e.get("timestamp", ""),
                    e.get("angler", ""),
                    e.get("latitude", ""),
                    e.get("longitude", ""),
                    e.get("fish_type", ""),
                    e.get("caught", 0),
                    e.get("spot", ""),
                    e.get("bait", ""),
                    e.get("chance", ""),
                    e.get("pressure", ""),
                    e.get("pressure_trend", ""),
                    e.get("wind_speed", ""),
                    e.get("temperature", ""),
                    e.get("length_cm", "Unbekannt"),
                ])
        return len(self.entries)


def _none(value: Any) -> Any:
    if value in ("None", "", None):
        return None
    return value


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("None", "", None):
            return default
        return float(value)
    except Exception:
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default
