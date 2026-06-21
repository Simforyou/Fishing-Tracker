"""
Wassertemperatur-Engine für Fishing Tracker
Bezieht echte Gewässertemperaturen von wassertemperatur.site.
Unterstützt Flüsse (/flusse/), Seen (/seen/) und Küstenorte (/stadt/).
Cache: 3 Stunden. Fallback: Monatstabelle + Lufttemperatur-Schätzung.
"""
from __future__ import annotations

import re
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

CACHE_TTL = timedelta(hours=3)

# Standard-Fallback Monatstabelle (Dinkel/NRW-typisch)
# Wird durch gescrapte Tabelle vom jeweiligen Gewässer ersetzt
MONTHLY_FALLBACK: dict[int, tuple[float, float, float]] = {
    1:  (2.0,  5.0,  7.0),
    2:  (2.0,  4.0,  6.0),
    3:  (3.0,  7.0, 11.0),
    4:  (7.0, 11.0, 14.0),
    5:  (11.0, 15.0, 19.0),
    6:  (14.0, 17.0, 21.0),
    7:  (17.0, 20.0, 25.0),
    8:  (15.0, 18.0, 22.0),
    9:  (12.0, 15.0, 20.0),
    10: (10.0, 12.0, 15.0),
    11: (5.0,  9.0, 12.0),
    12: (3.0,  5.0,  7.0),
}

MONTH_NAMES_DE = {
    "januar": 1, "februar": 2, "märz": 3, "april": 4,
    "mai": 5, "juni": 6, "juli": 7, "august": 8,
    "september": 9, "oktober": 10, "november": 11, "dezember": 12,
    "jan": 1, "feb": 2, "mär": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dez": 12,
}


class WaterTemperatureEngine:
    """
    Holt Wassertemperaturen von wassertemperatur.site.
    Unterstützt alle Gewässertypen: Flüsse, Seen, Küstenorte.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._cache: dict[str, Any] = {}
        self._url: str | None = None
        self._monthly_table: dict[int, tuple[float, float, float]] = dict(MONTHLY_FALLBACK)

    def set_url(self, url: str) -> None:
        """Setzt die URL des Gewässers (wassertemperatur.site)."""
        self._url = url.strip().rstrip("/")

    async def async_get_water_temperature(
        self,
        air_temp: float | None = None,
        month: int | None = None,
    ) -> dict[str, Any]:
        """
        Gibt Wassertemperatur + Metadaten zurück:
        {temp, source, monthly_avg, monthly_min, monthly_max,
         forecast, trend, oxygen_mg_l, oxygen_level}
        """
        now = datetime.now().astimezone()
        month = month or now.month

        cache_key = self._url or "fallback"
        cached = self._cache.get(cache_key)
        if cached:
            age = now - cached.get("fetched", now - CACHE_TTL - timedelta(seconds=1))
            if age < CACHE_TTL:
                return cached["data"]

        result = None
        if self._url:
            result = await self._scrape(self._url, month, air_temp)

        if result is None:
            result = self._build_fallback(month, air_temp)

        self._cache[cache_key] = {"fetched": now, "data": result}
        return result

    async def _scrape(self, url: str, month: int, air_temp: float | None) -> dict[str, Any] | None:
        try:
            session = async_get_clientsession(self.hass)
            headers = {"User-Agent": "Mozilla/5.0 (compatible; FishingTracker/2.8)"}
            async with session.get(url, timeout=12, headers=headers) as resp:
                if resp.status != 200:
                    _LOGGER.warning("WaterTemp: HTTP %s für %s", resp.status, url)
                    return None
                html = await resp.text(encoding="utf-8", errors="replace")
        except Exception as err:
            _LOGGER.warning("WaterTemp: Fetch-Fehler: %s", err)
            return None
        return self._parse(html, month, air_temp)

    def _parse(self, html: str, month: int, air_temp: float | None) -> dict[str, Any] | None:
        try:
            current = self._extract_current_temp(html)
            if current is None:
                _LOGGER.debug("WaterTemp: Keine aktuelle Temperatur gefunden")
                return None

            monthly = self._extract_monthly_table(html)
            if monthly:
                self._monthly_table = monthly

            lo, mid, hi = self._monthly_table.get(month, (10.0, 14.0, 18.0))
            forecast = self._extract_forecast(html)
            daily_history = self._extract_daily_history(html)

            return {
                "temp": round(current, 1),
                "source": "wassertemperatur.site",
                "source_url": url,
                "monthly_avg": mid,
                "monthly_min": lo,
                "monthly_max": hi,
                "forecast": forecast,
                "daily_history": daily_history,
                "trend": _trend_label(current, mid),
                "oxygen_mg_l": estimate_oxygen(current),
                "oxygen_level": oxygen_level_label(current),
            }
        except Exception as err:
            _LOGGER.warning("WaterTemp: Parse-Fehler: %s", err)
            return None

    def _extract_current_temp(self, html: str) -> float | None:
        patterns = [
            # Bestes Muster (Stadt-Seiten): "beträgt heute 18.1°C"
            r"beträgt heute\s+(\d+[.,]\d+)\s*°?C",
            r"betragt heute\s+(\d+[.,]\d+)\s*°?C",
            # "Der aktuelle Wert beträgt 18.1 Grad"
            r"aktuelle Wert beträgt\s+(\d+[.,]?\d*)\s*Grad",
            r"current.{0,15}is\s+(\d+[.,]\d+)\s*°?C",
            # Überschrift "Aktuelle Wassertemperatur" gefolgt von "18.1°C ... Heute"
            r"Aktuelle Wassertemperatur[^0-9]{0,120}?(\d+[.,]\d+)\s*°?C\s*\n?\s*Heute",
            r"Aktuelle Wassertemperatur[^<]{0,80}?(\d+[.,]\d+)\s*°?C",
            r"Heute\s*\n?\s*(\d+[.,]\d+)\s*°?C",
            r"(?<!\d)(\d{1,2}[.,]\d)\s*°C",
        ]
        for pattern in patterns:
            m = re.search(pattern, html, re.IGNORECASE)
            if m:
                try:
                    val = float(m.group(1).replace(",", "."))
                    if -2 < val < 40:  # Plausibilität
                        return val
                except Exception:
                    continue
        return None

    def _extract_monthly_table(self, html: str) -> dict[int, tuple[float, float, float]] | None:
        table: dict[int, tuple[float, float, float]] = {}
        rows = re.findall(r"<tr[^>]*>.*?</tr>", html, re.DOTALL | re.IGNORECASE)
        for row in rows:
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.DOTALL | re.IGNORECASE)
            cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
            if len(cells) < 4:
                continue
            month_num = MONTH_NAMES_DE.get(cells[0].lower().strip())
            if month_num is None:
                continue
            try:
                nums = [float(c.replace("°C", "").replace(",", ".").strip()) for c in cells[1:4]]
                if len(nums) == 3:
                    table[month_num] = (nums[0], nums[1], nums[2])
            except Exception:
                continue
        return table if len(table) >= 6 else None

    def _extract_daily_history(self, html: str) -> list[dict]:
        """Extrahiert tägliche Wassertemperaturen der letzten ~30 Tage aus der Tabelle."""
        history = []
        try:
            rows = re.findall(r"<tr[^>]*>.*?</tr>", html, re.DOTALL | re.IGNORECASE)
            month_map = {
                "jan": 1, "feb": 2, "mär": 3, "mar": 3, "apr": 4,
                "mai": 5, "may": 5, "jun": 6, "jul": 7, "aug": 8,
                "sep": 9, "okt": 10, "oct": 10, "nov": 11, "dez": 12, "dec": 12,
            }
            current_year = datetime.now().year
            current_month = datetime.now().month
            for row in rows:
                cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.DOTALL | re.IGNORECASE)
                cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
                if len(cells) < 2:
                    continue
                # Format: "JUN 3" oder "JUN 3" → Datum parsen
                date_match = re.match(r"([A-Za-zÄÖÜäöü]+)\s+(\d{1,2})", cells[0])
                if not date_match:
                    continue
                mon_str = date_match.group(1)[:3].lower()
                day = int(date_match.group(2))
                mon_num = month_map.get(mon_str)
                if not mon_num:
                    continue
                # Jahr bestimmen (könnte Vorjahr sein)
                year = current_year
                if mon_num > current_month + 1:
                    year = current_year - 1
                # Temperaturwert aus zweiter Spalte (Aktuell)
                temp_str = cells[1].replace("°C", "").replace(",", ".").strip()
                try:
                    temp = float(temp_str)
                    if 0.0 < temp < 35.0:
                        date_str = f"{year}-{mon_num:02d}-{day:02d}"
                        history.append({"date": date_str, "temp": round(temp, 1)})
                except (ValueError, TypeError):
                    continue
        except Exception as err:
            _LOGGER.debug("WaterTemp: daily_history Parse-Fehler: %s", err)
        return history

    def _extract_forecast(self, html: str) -> list[float]:
        lower = html.lower()
        idx = lower.find("prognose")
        if idx == -1:
            return []
        section = html[idx:idx + 3000]
        temps: list[float] = []
        for m in re.finditer(r"(\d+[.,]\d+)\s*°C", section):
            try:
                t = float(m.group(1).replace(",", "."))
                if 0.0 < t < 35.0:
                    temps.append(round(t, 1))
            except Exception:
                pass
        return temps[:7]

    def _build_fallback(self, month: int, air_temp: float | None) -> dict[str, Any]:
        lo, mid, hi = self._monthly_table.get(month, (10.0, 14.0, 18.0))
        estimated = _estimate_from_monthly(mid, lo, hi, air_temp)
        return {
            "temp": estimated,
            "source": "Monatstabelle (Schätzung)",
            "monthly_avg": mid,
            "monthly_min": lo,
            "monthly_max": hi,
            "forecast": [],
            "trend": _trend_label(estimated, mid),
            "oxygen_mg_l": estimate_oxygen(estimated),
            "oxygen_level": oxygen_level_label(estimated),
        }


# ── O₂-Sättigung ─────────────────────────────────────────────────────────────

def estimate_oxygen(water_temp: float) -> float:
    """O₂-Sättigungsgehalt in mg/l nach Benson & Krause (Süßwasser, 1 atm)."""
    T = max(0.0, min(35.0, water_temp))
    o2 = 14.62 - 0.3898 * T + 0.006969 * T ** 2 - 0.00005896 * T ** 3
    return round(max(4.0, min(14.5, o2)), 1)


def oxygen_level_label(water_temp: float) -> str:
    o2 = estimate_oxygen(water_temp)
    if o2 >= 10.0:
        return "Sehr gut (>10 mg/l)"
    if o2 >= 8.0:
        return "Gut (8–10 mg/l)"
    if o2 >= 6.0:
        return "Ausreichend (6–8 mg/l)"
    if o2 >= 4.0:
        return "Kritisch (4–6 mg/l)"
    return "Gefährlich (<4 mg/l)"


def oxygen_score_modifier(water_temp: float, fish_type: str = "") -> float:
    """Score-Modifier (-22 bis +4) basierend auf O₂. Raubfische reagieren empfindlicher."""
    o2 = estimate_oxygen(water_temp)
    sensitive = fish_type.lower() in ("hecht", "zander", "barsch", "forelle", "äsche")
    if o2 >= 9.0:
        return 4.0
    if o2 >= 7.5:
        return 1.0
    if o2 >= 6.0:
        return -4.0 if not sensitive else -8.0
    if o2 >= 4.5:
        return -12.0 if not sensitive else -20.0
    return -22.0


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

def _estimate_from_monthly(mid: float, lo: float, hi: float, air_temp: float | None) -> float:
    if air_temp is None:
        return mid
    air_deviation = (air_temp - 10.0) * 0.20
    return round(max(lo - 0.5, min(hi + 0.5, mid + air_deviation)), 1)


def _trend_label(current: float, monthly_avg: float) -> str:
    diff = current - monthly_avg
    if diff > 3.0:
        return "deutlich wärmer als Durchschnitt"
    if diff > 1.0:
        return "etwas wärmer als Durchschnitt"
    if diff < -3.0:
        return "deutlich kälter als Durchschnitt"
    if diff < -1.0:
        return "etwas kälter als Durchschnitt"
    return "im saisonalen Durchschnitt"
