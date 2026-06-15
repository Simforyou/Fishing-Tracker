"""
NLWKN Gewässergüte Wassertemperatur-Scraper für Fishing Tracker.

Bezieht echte Wassertemperaturen von:
https://www.gewaessergueteonline.nlwkn.niedersachsen.de/Station/ID/{station_id}

Default-Station: 2004 (Laar / Vechte) — die einzige kontinuierlich überwachte
Gewässergüte-Messstation an der Vechte. Andere Stationen lassen sich über
config_entry.options.PEGEL_NLWKN_STATION_ID konfigurieren.

Cache: 15 Minuten. Update-Intervall sollte ≥ 15 Minuten sein, da NLWKN
intern alle 15 Minuten misst.
"""
from __future__ import annotations

import re
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

CACHE_TTL = timedelta(minutes=15)
BASE_URL = "https://www.gewaessergueteonline.nlwkn.niedersachsen.de/Station/ID/{station_id}"

# Bekannte NLWKN-Stationen für die Region Grafschaft Bentheim (Vechte/Dinkel)
# IDs aus der NLWKN Gewässergüte-Karte
KNOWN_STATIONS = {
    "2004": {"name": "Laar", "river": "Vechte", "lat": 52.620, "lon": 6.764},
    # Weitere Stationen können hier ergänzt werden, wenn sie identifiziert sind
}

DEFAULT_STATION_ID = "2004"


class NlwknWaterTempEngine:
    """Holt Wassertemperatur von NLWKN Gewässergüte-Messstationen via HTML-Scraping."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._station_id: str = DEFAULT_STATION_ID
        self._cache: dict[str, Any] = {}

    def set_station(self, station_id: str | None) -> None:
        """Setzt die NLWKN-Stations-ID."""
        if station_id:
            self._station_id = str(station_id).strip()
            self._cache = {}  # Cache invalidieren bei Wechsel

    @property
    def station_id(self) -> str:
        return self._station_id

    @property
    def station_info(self) -> dict[str, Any]:
        return KNOWN_STATIONS.get(self._station_id, {"name": f"Station {self._station_id}", "river": "?", "lat": None, "lon": None})

    async def async_get(self) -> dict[str, Any] | None:
        """
        Gibt aktuelle Wassertemperatur + Zeitpunkt zurück.

        Returns:
            {
                "temp": float,         # °C
                "timestamp": str,      # "DD.MM.YYYY HH:MM"
                "station_id": str,
                "station_name": str,
                "river": str,
                "source": "NLWKN Gewässergüte",
                "url": str
            }
            oder None bei Fehler.
        """
        # Cache prüfen
        now = datetime.now()
        cached = self._cache.get(self._station_id)
        if cached and (now - cached["fetched_at"]) < CACHE_TTL:
            return cached["data"]

        url = BASE_URL.format(station_id=self._station_id)
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(url, timeout=15) as resp:
                if resp.status != 200:
                    _LOGGER.warning("NLWKN Gewässergüte returned status %s for station %s", resp.status, self._station_id)
                    return None
                html = await resp.text()
        except Exception as e:  # noqa: BLE001
            _LOGGER.warning("NLWKN fetch failed for station %s: %s", self._station_id, e)
            return None

        parsed = self._parse_water_temp(html)
        if not parsed:
            _LOGGER.warning("NLWKN response: could not parse water temperature from station %s", self._station_id)
            return None

        info = self.station_info
        data = {
            "temp": parsed["temp"],
            "timestamp": parsed["timestamp"],
            "station_id": self._station_id,
            "station_name": info.get("name", "?"),
            "river": info.get("river", "?"),
            "source": "NLWKN Gewässergüte",
            "url": url,
        }
        self._cache[self._station_id] = {"fetched_at": now, "data": data}
        return data

    def _parse_water_temp(self, html: str) -> dict[str, Any] | None:
        """
        Parst die Wassertemperatur aus der NLWKN-Gewässergüte-HTML-Seite.

        Die Seite hat mehrere "Aktuelle Messdaten"-Blöcke (Wasserstand,
        Wassertemperatur, Lufttemperatur, Sauerstoff, pH, Leitfähigkeit).
        Wir grenzen STRENG auf die Wassertemperatur-Sektion ein (Anchor #45)
        und stoppen vor der nächsten Sektion (Lufttemperatur ist #204).

        Wenn der Wassertemperatur-Block "Keine Daten" enthält, return None —
        sonst würden wir versehentlich den Lufttemperatur-Wert nehmen.
        """
        # 1) Section-Start finden: "Wassertemperatur" als Heading
        #    Mehrere mögliche HTML-Formate abdecken
        start_patterns = [
            r'<a[^>]*name=["\']?45["\']?[^>]*>',
            r'<[^>]+id=["\']?45["\']?[^>]*>',
            r'<a[^>]*href=["\']#45["\']?[^>]*>',
            r'>\s*Wassertemperatur\s*<',
            r'Wassertemperatur',
        ]
        start_idx = -1
        for pat in start_patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                start_idx = m.end()
                break
        if start_idx < 0:
            return None

        # 2) Section-Ende: nächste Parameter-Sektion (Lufttemperatur, Sauerstoff,
        #    pH, Leitfähigkeit) ODER nächster Anchor mit ID
        end_patterns = [
            r'<a[^>]*name=["\']?204["\']?[^>]*>',         # Lufttemperatur
            r'<a[^>]*name=["\']?301["\']?[^>]*>',         # Sauerstoff
            r'<[^>]+id=["\']?204["\']?[^>]*>',
            r'Lufttemperatur',
            r'Sauerstoff',
            r'pH-Wert',
        ]
        end_idx = len(html)
        for pat in end_patterns:
            m = re.search(pat, html[start_idx:], re.IGNORECASE)
            if m:
                end_idx = min(end_idx, start_idx + m.start())

        # Section ist garantiert nur der Wassertemperatur-Bereich
        section = html[start_idx:end_idx]

        # 3) "Keine Daten" → Station liefert keine Wassertemperatur (defekt o. abgeschaltet)
        if re.search(r'Keine\s+Daten', section, re.IGNORECASE):
            _LOGGER.debug("NLWKN: Wassertemperatur-Sektion enthält 'Keine Daten' — Sensor inaktiv")
            return None

        # 4) Messwert parsen (deutsches Dezimalkomma)
        m = re.search(r'Messwert[^0-9\-]*(-?[\d]+[,.]\d+)\s*°?\s*C', section, re.IGNORECASE | re.DOTALL)
        if not m:
            # Ganzzahlige Werte auch akzeptieren
            m = re.search(r'Messwert[^0-9\-]*(-?[\d]+)\s*°?\s*C', section, re.IGNORECASE | re.DOTALL)
            if not m:
                return None

        try:
            temp_str = m.group(1).replace(',', '.')
            temp = float(temp_str)
        except (ValueError, IndexError):
            return None

        # Plausibilität: Wassertemperatur im realistischen Bereich
        if temp < -2 or temp > 35:
            _LOGGER.debug("NLWKN parse: implausible water temp %s, rejecting", temp)
            return None

        # 5) Zeitstempel finden
        ts_match = re.search(r'Zeitpunkt[^0-9]*(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})', section, re.IGNORECASE)
        timestamp = ts_match.group(1) if ts_match else now_str()

        return {"temp": temp, "timestamp": timestamp}


def now_str() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M")
