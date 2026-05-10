from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DATA_DIR, DEFAULT_SETTINGS, JSON_FILE, STORAGE_KEY, STORAGE_VERSION, WWW_JSON_FILE


class FishingStore:
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.data: dict[str, Any] = {"entries": [], "settings": dict(DEFAULT_SETTINGS)}

    async def async_load(self) -> None:
        data = await self._store.async_load()
        if isinstance(data, dict):
            self.data = data
        self.data.setdefault("entries", [])
        self.data.setdefault("settings", {})
        for key, value in DEFAULT_SETTINGS.items():
            self.data["settings"].setdefault(key, value)
        await self.async_save()

    async def async_save(self) -> None:
        await self._store.async_save(self.data)
        await self.async_export_json_files()

    @property
    def entries(self) -> list[dict[str, Any]]:
        return self.data.setdefault("entries", [])

    @property
    def settings(self) -> dict[str, Any]:
        self.data.setdefault("settings", {})
        for key, value in DEFAULT_SETTINGS.items():
            self.data["settings"].setdefault(key, value)
        return self.data["settings"]

    async def async_set_setting(self, key: str, value: Any) -> None:
        self.settings[key] = value
        await self.async_save()

    async def async_add_entry(self, entry: dict[str, Any]) -> None:
        self.entries.append(entry)
        await self.async_save()

    async def async_export_json_files(self) -> None:
        payload = {"version": 1, "entries": _fix_payload(self.entries), "settings": _fix_payload(self.settings)}
        config_path = Path(self.hass.config.path())

        data_dir = config_path / DATA_DIR
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / JSON_FILE).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        www_dir = config_path / "www"
        www_dir.mkdir(parents=True, exist_ok=True)
        (www_dir / WWW_JSON_FILE).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    async def async_export_json(self, path: str) -> int:
        payload = {"version": 1, "entries": _fix_payload(self.entries), "settings": _fix_payload(self.settings)}
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return len(self.entries)

    async def async_import_csv(self, path: str) -> int:
        file_path = Path(path)
        if not file_path.exists():
            return 0
        imported = 0
        with file_path.open(newline="", encoding="utf-8") as f:
            for row in csv.reader(f):
                if len(row) < 13:
                    continue
                self.entries.append({
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
                    "length_cm": row[13] if len(row) >= 14 else 0,
                    "source": "csv_import",
                })
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
                    e.get("timestamp", ""), e.get("angler", ""), e.get("latitude", ""),
                    e.get("longitude", ""), e.get("fish_type", ""), e.get("caught", 0),
                    e.get("spot", ""), e.get("bait", ""), e.get("chance", ""),
                    e.get("pressure", ""), e.get("pressure_trend", ""),
                    e.get("wind_speed", ""), e.get("temperature", ""), e.get("length_cm", 0),
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


def _fix_payload(value):
    if isinstance(value, list):
        return [_fix_payload(v) for v in value]
    if isinstance(value, dict):
        return {k: _fix_payload(v) for k, v in value.items()}
    if isinstance(value, str):
        return _fix_text_encoding(value)
    return value


def _fix_text_encoding(value: str) -> str:
    replacements = {
        "ÃŸ": "ß", "Ã¤": "ä", "Ã¶": "ö", "Ã¼": "ü",
        "Ã„": "Ä", "Ã–": "Ö", "Ãœ": "Ü",
        "WeiÃŸfisch": "Weißfisch",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value
