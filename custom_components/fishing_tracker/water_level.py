"""
Pegelstand-Engine für Fishing Tracker
Bezieht Wasserstand, Trend und Trübung von PEGELONLINE (WSV).
Kostenlos, kein API-Key, 660+ Stationen an deutschen Bundeswasserstraßen.
Cache: 1 Stunde. Minutenaktuelle Daten.

Stationen finden: https://pegelonline.wsv.de/webservices/rest-api/v2/stations.json
UUID des eigenen Pegels suchen und in der HA-Konfiguration eintragen.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://www.pegelonline.wsv.de/webservices/rest-api/v2"
CACHE_TTL = timedelta(hours=1)
STATIONS_URL = f"{BASE_URL}/stations.json"


class WaterLevelEngine:
    """
    Holt Wasserstand + Trend von PEGELONLINE.
    Optional: Trübung und Wassertemperatur wenn Pegel diese misst.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._cache: dict[str, Any] = {}
        self._station_uuid: str | None = None
        self._station_name: str | None = None
        # Kennzeichnende Wasserstände (MNW, MW, MHW) für Normalbewertung
        self._char_values: dict[str, float] = {}

    def set_station(self, uuid: str, name: str = "") -> None:
        """Setzt die PEGELONLINE-Station UUID."""
        self._station_uuid = uuid.strip()
        self._station_name = name

    async def async_get_water_level(self) -> dict[str, Any]:
        """
        Gibt aktuellen Pegelstand + Bewertung zurück:
        {value_cm, trend, level_label, score_modifier, turbidity, station_name, source}
        """
        if not self._station_uuid:
            return _empty_result()

        now = datetime.now().astimezone()
        cached = self._cache.get("level")
        if cached:
            if now - cached.get("fetched", now - CACHE_TTL) < CACHE_TTL:
                return cached["data"]

        data = await self._fetch(self._station_uuid)
        self._cache["level"] = {"fetched": now, "data": data}
        return data

    async def _fetch(self, uuid: str) -> dict[str, Any]:
        session = async_get_clientsession(self.hass)

        # Aktueller Wasserstand
        url_w = f"{BASE_URL}/stations/{uuid}/W/currentmeasurement.json"
        try:
            async with session.get(url_w, timeout=10) as resp:
                if resp.status != 200:
                    _LOGGER.warning("Pegelonline: HTTP %s für %s", resp.status, url_w)
                    return _empty_result()
                w_data = await resp.json()
        except Exception as err:
            _LOGGER.warning("Pegelonline: Fetch-Fehler: %s", err)
            return _empty_result()

        value_cm = _num(w_data.get("value"))
        timestamp = w_data.get("timestamp", "")
        trend_raw = _num(w_data.get("trend"))  # -1, 0, 1

        # Kennzeichnende Wasserstände nachladen (einmalig, für Normalbewertung)
        if not self._char_values:
            await self._fetch_char_values(uuid, session)

        level_label, score_mod = _evaluate_level(value_cm, self._char_values)
        trend_label = _trend_str(trend_raw)

        # Optionale Trübung (nicht alle Pegel messen diese)
        turbidity = await self._fetch_optional(uuid, "TRB", session)
        water_temp_pegel = await self._fetch_optional(uuid, "WT", session)

        return {
            "value_cm": value_cm,
            "trend": trend_label,
            "trend_raw": trend_raw,
            "level_label": level_label,
            "score_modifier": score_mod,
            "turbidity_ntu": turbidity,
            "water_temp_pegel": water_temp_pegel,
            "station_name": self._station_name or uuid[:8],
            "timestamp": timestamp,
            "source": "pegelonline.wsv.de",
            "mnw": self._char_values.get("MNW"),
            "mw":  self._char_values.get("MW"),
            "mhw": self._char_values.get("MHW"),
        }

    async def _fetch_char_values(self, uuid: str, session: Any) -> None:
        """Lädt MNW/MW/MHW für Normalbewertung."""
        url = f"{BASE_URL}/stations/{uuid}/W.json?includeCurrentMeasurement=false"
        try:
            async with session.get(url, timeout=8) as resp:
                if resp.status != 200:
                    return
                data = await resp.json()
            for cv in data.get("characteristicValues") or []:
                name = cv.get("shortname", "")
                val = _num(cv.get("value"))
                if name and val is not None:
                    self._char_values[name] = val
        except Exception:
            pass

    async def _fetch_optional(self, uuid: str, param: str, session: Any) -> float | None:
        """Versucht optionalen Parameter zu laden (z.B. Trübung, Wassertemp)."""
        url = f"{BASE_URL}/stations/{uuid}/{param}/currentmeasurement.json"
        try:
            async with session.get(url, timeout=6) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return _num(data.get("value"))
        except Exception:
            return None


async def search_stations(hass: HomeAssistant, query: str) -> list[dict[str, Any]]:
    """
    Sucht PEGELONLINE-Stationen nach Name/Gewässer.
    Hilfreich zur Konfiguration: liefert UUID + Gewässer.
    """
    session = async_get_clientsession(hass)
    try:
        url = f"{STATIONS_URL}?waters={query.upper()}"
        async with session.get(url, timeout=12) as resp:
            if resp.status != 200:
                return []
            stations = await resp.json()
        return [
            {
                "uuid": s.get("uuid", ""),
                "name": s.get("longname", s.get("shortname", "")),
                "water": s.get("water", {}).get("longname", ""),
                "km": s.get("km"),
            }
            for s in (stations or [])
        ][:20]
    except Exception:
        return []


# ── Bewertungslogik ───────────────────────────────────────────────────────────

def _evaluate_level(
    value_cm: float | None,
    char: dict[str, float],
) -> tuple[str, float]:
    """
    Bewertet Pegelstand relativ zu MW/MNW/MHW.
    Gibt (Label, Score-Modifier) zurück.

    Angeloptimal: Normalpegel bis leicht erhöht (Regen spült Nahrung ein).
    Hochwasser: stark negativ (Trübung, Standort weg, Fische desorganisiert).
    Niedrigwasser: mäßig negativ (Fische scheu, wenig Deckung).
    """
    if value_cm is None:
        return "Unbekannt", 0.0

    mw  = char.get("MW")
    mnw = char.get("MNW")
    mhw = char.get("MHW")

    # Ohne Referenzwerte: vereinfachte absolute Bewertung
    if mw is None:
        return "Messwert vorhanden", 0.0

    deviation = value_cm - mw  # Abweichung vom Mittelwasser

    if mhw and value_cm >= mhw:
        return "Hochwasser", -18.0
    if mhw and value_cm >= mhw * 0.85:
        return "Erhöht (Vor-Hochwasser)", -8.0
    if deviation > 40:
        return "Deutlich erhöht", -4.0
    if 10 <= deviation <= 40:
        return "Leicht erhöht (gut für Friedfisch)", +5.0
    if -20 <= deviation <= 10:
        return "Normalpegel", +3.0
    if mnw and value_cm <= mnw:
        return "Niedrigwasser", -10.0
    if deviation < -20:
        return "Leicht niedrig", -5.0

    return "Normal", 0.0


def water_level_score_modifier(level_data: dict[str, Any], fish_type: str = "") -> float:
    """
    Gibt den Score-Modifier aus den Pegeldaten zurück.
    Raubfische (Hecht, Zander) reagieren empfindlicher auf Hochwasser.
    Friedfische profitieren etwas von leicht erhöhtem Wasserstand.
    """
    base = level_data.get("score_modifier", 0.0)
    sensitive = fish_type.lower() in ("hecht", "zander", "barsch")
    if base < -5 and sensitive:
        return base * 1.4
    return base


def turbidity_score_modifier(
    turbidity_ntu: float | None,
    cloud_coverage: float,
    precipitation_24h: float,
    fish_type: str = "",
) -> tuple[float, str]:
    """
    Berechnet Trübungs-Score + Köderfarben-Empfehlung.
    Nutzt Pegelonline-Trübung (NTU) wenn vorhanden,
    sonst Schätzung aus Niederschlag + Bewölkung.

    Wettermethode (Lieblingsköder):
    - Klares Wasser + Sonne  → Naturfarben
    - Klares Wasser + Wolken → Naturfarben / dezente Kontraste
    - Trübes Wasser + Sonne  → Kontrast-/Schockfarben
    - Trübes Wasser + Wolken → Schockfarben, UV-aktiv
    """
    # Trübung bestimmen
    if turbidity_ntu is not None:
        # NTU-Skala: <5 = klar, 5-20 = leicht trüb, 20-100 = trüb, >100 = sehr trüb
        if turbidity_ntu < 5:
            turbidity_level = "klar"
        elif turbidity_ntu < 20:
            turbidity_level = "leicht_trüb"
        elif turbidity_ntu < 100:
            turbidity_level = "trüb"
        else:
            turbidity_level = "sehr_trüb"
    else:
        # Schätzung aus Niederschlag der letzten 24h + Bewölkung
        if precipitation_24h > 15:
            turbidity_level = "sehr_trüb"
        elif precipitation_24h > 5:
            turbidity_level = "trüb"
        elif precipitation_24h > 1:
            turbidity_level = "leicht_trüb"
        else:
            turbidity_level = "klar"

    sunny = cloud_coverage < 40
    is_predator = fish_type.lower() in ("hecht", "zander", "barsch", "forelle")

    # Wettermethode-Matrix
    if turbidity_level == "klar" and sunny:
        bait_color = "Naturfarben (Sunny, Whisky)"
        score_mod = +2.0 if is_predator else +1.0
    elif turbidity_level == "klar" and not sunny:
        bait_color = "Naturfarben / dezente Kontraste (Whisky, Captain)"
        score_mod = +3.0
    elif turbidity_level == "leicht_trüb" and sunny:
        bait_color = "Kontraste / semi-natürlich (Firetiger, Captain)"
        score_mod = +5.0  # Leicht trüb = optimal fürs Spinnfischen!
    elif turbidity_level == "leicht_trüb" and not sunny:
        bait_color = "Kontraste (Firetiger, Pinky)"
        score_mod = +4.0
    elif turbidity_level == "trüb":
        bait_color = "Schockfarben / UV-aktiv (Sheriff, Pinky, Mr. White)"
        score_mod = -2.0 if is_predator else -4.0
    else:  # sehr_trüb
        bait_color = "UV-aktiv / Leuchtfarben (Sheriff, Neo)"
        score_mod = -8.0

    return score_mod, bait_color


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

def _num(v: Any) -> float | None:
    try:
        if v in (None, "", "unknown"):
            return None
        return float(v)
    except Exception:
        return None


def _trend_str(trend: float | None) -> str:
    if trend is None:
        return "unbekannt"
    if trend > 0:
        return "steigend"
    if trend < 0:
        return "fallend"
    return "stabil"


def _empty_result() -> dict[str, Any]:
    return {
        "value_cm": None,
        "trend": "unbekannt",
        "trend_raw": None,
        "level_label": "Keine Pegeldaten",
        "score_modifier": 0.0,
        "turbidity_ntu": None,
        "water_temp_pegel": None,
        "station_name": "–",
        "timestamp": None,
        "source": "–",
        "mnw": None,
        "mw": None,
        "mhw": None,
    }
