from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FishProfile:
    name: str
    aliases: tuple[str, ...]
    temp_range: tuple[float, float]
    preferred_hours: tuple[tuple[int, int], ...]
    season_months: tuple[int, ...]
    low_light_weight: float
    wind_weight: float
    pressure_falling_weight: float
    pressure_rising_penalty: float
    cloud_weight: float
    rain_light_weight: float
    rain_heavy_penalty: float
    moon_weights: dict[str, float] = field(default_factory=dict)
    behavior_notes: tuple[str, ...] = ()
    recommended_baits: tuple[str, ...] = ()


FISH_PROFILES: dict[str, FishProfile] = {
    "Weißfisch": FishProfile(
        name="Weißfisch",
        aliases=("weissfisch", "weißfisch", "whitefish"),
        temp_range=(9, 24),
        preferred_hours=((8, 13), (15, 20)),
        season_months=(4, 5, 6, 7, 8, 9, 10),
        low_light_weight=2,
        wind_weight=2,
        pressure_falling_weight=3,
        pressure_rising_penalty=3,
        cloud_weight=2,
        rain_light_weight=1,
        rain_heavy_penalty=5,
        moon_weights={"full_moon": 1, "new_moon": 1, "waxing": 1},
        behavior_notes=(
            "Weißfische reagieren stark auf Temperatur, Futterplatz und ruhige Bedingungen.",
            "Konstante Bedingungen und moderate Wärme sind oft wichtiger als extreme Wetterwechsel.",
        ),
        recommended_baits=("Made", "Pinkies", "Mais", "Brot", "Wurm"),
    ),
    "Brasse": FishProfile(
        name="Brasse",
        aliases=("brasse", "blei", "bream"),
        temp_range=(12, 24),
        preferred_hours=((6, 11), (17, 22)),
        season_months=(5, 6, 7, 8, 9),
        low_light_weight=4,
        wind_weight=2,
        pressure_falling_weight=3,
        pressure_rising_penalty=4,
        cloud_weight=3,
        rain_light_weight=2,
        rain_heavy_penalty=6,
        moon_weights={"full_moon": 2, "new_moon": 1, "waxing": 1},
        behavior_notes=(
            "Brassen ziehen oft in Trupps und profitieren von Futterplätzen.",
            "Warme Abendphasen und leicht trübes Wetter können hilfreich sein.",
        ),
        recommended_baits=("Made", "Mais", "Wurm", "Brot", "Kombi"),
    ),
    "Rotauge": FishProfile(
        name="Rotauge",
        aliases=("rotauge", "roach"),
        temp_range=(8, 22),
        preferred_hours=((8, 12), (15, 19)),
        season_months=(3, 4, 5, 6, 7, 8, 9, 10),
        low_light_weight=2,
        wind_weight=2,
        pressure_falling_weight=2,
        pressure_rising_penalty=3,
        cloud_weight=3,
        rain_light_weight=1,
        rain_heavy_penalty=5,
        moon_weights={"full_moon": 1, "new_moon": 1},
        behavior_notes=(
            "Rotaugen mögen moderate Temperaturen und reagieren gut auf feines Futter.",
            "Zu grelles Licht und sehr klares Wasser können vorsichtig machen.",
        ),
        recommended_baits=("Made", "Pinkies", "Brot", "Mais"),
    ),
    "Rotfeder": FishProfile(
        name="Rotfeder",
        aliases=("rotfeder", "rudd"),
        temp_range=(12, 26),
        preferred_hours=((9, 14), (16, 20)),
        season_months=(5, 6, 7, 8, 9),
        low_light_weight=2,
        wind_weight=1,
        pressure_falling_weight=2,
        pressure_rising_penalty=3,
        cloud_weight=2,
        rain_light_weight=1,
        rain_heavy_penalty=5,
        moon_weights={"full_moon": 1, "waxing": 1},
        behavior_notes=(
            "Rotfedern stehen oft krautnah und oberflächennah.",
            "Warme, ruhige Phasen sind häufig besser als harte Wetterwechsel.",
        ),
        recommended_baits=("Brot", "Made", "Mais", "Pinkies"),
    ),
    "Karpfen": FishProfile(
        name="Karpfen",
        aliases=("karpfen", "carp"),
        temp_range=(14, 27),
        preferred_hours=((5, 9), (18, 23)),
        season_months=(5, 6, 7, 8, 9, 10),
        low_light_weight=6,
        wind_weight=4,
        pressure_falling_weight=5,
        pressure_rising_penalty=4,
        cloud_weight=4,
        rain_light_weight=5,
        rain_heavy_penalty=7,
        moon_weights={"full_moon": 5, "new_moon": 3, "waxing": 2},
        behavior_notes=(
            "Karpfen profitieren von wärmerem Wasser und längeren Fressphasen.",
            "Warme Nächte, leichter Regen und Wind auf eine Uferkante können positiv sein.",
        ),
        recommended_baits=("Boilie", "Mais", "Wurm", "Kombi"),
    ),
    "Schleie": FishProfile(
        name="Schleie",
        aliases=("schleie", "tench"),
        temp_range=(13, 24),
        preferred_hours=((5, 9), (18, 22)),
        season_months=(5, 6, 7, 8, 9),
        low_light_weight=6,
        wind_weight=2,
        pressure_falling_weight=3,
        pressure_rising_penalty=4,
        cloud_weight=4,
        rain_light_weight=3,
        rain_heavy_penalty=6,
        moon_weights={"full_moon": 3, "new_moon": 2, "waxing": 2},
        behavior_notes=(
            "Schleien sind oft dämmerungsaktiv und mögen krautige, ruhigere Bereiche.",
            "Stabile warme Phasen sind meist besser als plötzliche Kälteeinbrüche.",
        ),
        recommended_baits=("Wurm", "Mais", "Made", "Kombi"),
    ),
    "Barsch": FishProfile(
        name="Barsch",
        aliases=("barsch", "perch"),
        temp_range=(9, 22),
        preferred_hours=((7, 11), (16, 20)),
        season_months=(4, 5, 6, 7, 8, 9, 10),
        low_light_weight=4,
        wind_weight=5,
        pressure_falling_weight=4,
        pressure_rising_penalty=4,
        cloud_weight=3,
        rain_light_weight=2,
        rain_heavy_penalty=5,
        moon_weights={"full_moon": 2, "new_moon": 2, "waxing": 1},
        behavior_notes=(
            "Barsche jagen oft in Aktivitätsfenstern und reagieren auf Beutefischbewegung.",
            "Wind, Kanten und trüberes Licht können Jagdphasen auslösen.",
        ),
        recommended_baits=("Wurm", "Made", "Kombi"),
    ),
    "Zander": FishProfile(
        name="Zander",
        aliases=("zander", "pikeperch", "walleye"),
        temp_range=(7, 21),
        preferred_hours=((18, 23), (0, 3)),
        season_months=(4, 5, 6, 9, 10, 11),
        low_light_weight=13,
        wind_weight=4,
        pressure_falling_weight=9,
        pressure_rising_penalty=7,
        cloud_weight=7,
        rain_light_weight=6,
        rain_heavy_penalty=6,
        moon_weights={"full_moon": 7, "new_moon": 5, "waxing": 3, "waning": 2},
        behavior_notes=(
            "Zander profitieren oft von Dämmerung, Nacht, trübem Wasser und fallendem Luftdruck.",
            "Grelles Licht und sehr klares Wasser können die Aktivität reduzieren.",
        ),
        recommended_baits=("Wurm", "Kombi"),
    ),
    "Hecht": FishProfile(
        name="Hecht",
        aliases=("hecht", "pike"),
        temp_range=(6, 19),
        preferred_hours=((6, 10), (16, 21)),
        season_months=(3, 4, 5, 9, 10, 11),
        low_light_weight=8,
        wind_weight=8,
        pressure_falling_weight=11,
        pressure_rising_penalty=7,
        cloud_weight=5,
        rain_light_weight=4,
        rain_heavy_penalty=6,
        moon_weights={"full_moon": 3, "new_moon": 2, "waxing": 2},
        behavior_notes=(
            "Hechte reagieren oft auf Wetterwechsel, Wind und fallenden Luftdruck.",
            "Dämmerung, strukturreiche Bereiche und bewegtes Wasser sind häufig interessant.",
        ),
        recommended_baits=("Wurm", "Kombi"),
    ),
    "Aal": FishProfile(
        name="Aal",
        aliases=("aal", "eel"),
        temp_range=(14, 25),
        preferred_hours=((20, 23), (0, 4)),
        season_months=(5, 6, 7, 8, 9),
        low_light_weight=15,
        wind_weight=2,
        pressure_falling_weight=5,
        pressure_rising_penalty=5,
        cloud_weight=6,
        rain_light_weight=9,
        rain_heavy_penalty=4,
        moon_weights={"new_moon": 8, "waning": 4, "full_moon": -3},
        behavior_notes=(
            "Aale sind stark nachtaktiv und profitieren häufig von warmen, dunklen, feuchten Nächten.",
            "Regen und wenig Licht sind oft wichtiger als perfekte Sichtbedingungen.",
        ),
        recommended_baits=("Wurm", "Kombi"),
    ),
    "Wels": FishProfile(
        name="Wels",
        aliases=("wels", "waller", "silurus"),
        temp_range=(18, 26),
        preferred_hours=((21, 3),),
        season_months=(6, 7, 8, 9),
        low_light_weight=1.8,
        wind_weight=-0.4,
        pressure_falling_weight=0.3,
        pressure_rising_penalty=-0.1,
        cloud_weight=0.5,
        rain_light_weight=0.4,
        rain_heavy_penalty=-0.3,
        moon_weights={"full_moon": 0.8, "new_moon": 1.2},
        behavior_notes=("Nachtaktiv", "Wärmeliebend", "Bodennähe", "Vibrationssensor"),
        recommended_baits=("Großer Gummifisch", "Froschköder", "Tauwurm-Bündel", "Fischfilet"),
    ),
    "Güster": FishProfile(
        name="Güster",
        aliases=("güster", "guester", "blicca", "blei"),
        temp_range=(14, 22),
        preferred_hours=((7, 12), (15, 19)),
        season_months=(4, 5, 6, 7, 8, 9, 10),
        low_light_weight=0.3,
        wind_weight=-0.3,
        pressure_falling_weight=0.2,
        pressure_rising_penalty=-0.1,
        cloud_weight=0.2,
        rain_light_weight=0.1,
        rain_heavy_penalty=-0.5,
        moon_weights={"full_moon": 0.5},
        behavior_notes=("Tagaktiv", "Schwarmfisch", "Bodenfresser"),
        recommended_baits=("Made", "Tauwurm", "Mais", "Pellets", "Brot"),
    ),
    "Grundel": FishProfile(
        name="Grundel",
        aliases=("grundel", "gudgeon", "gobio"),
        temp_range=(10, 18),
        preferred_hours=((7, 15),),
        season_months=(3, 4, 5, 6, 7, 8, 9, 10),
        low_light_weight=0.2,
        wind_weight=-0.2,
        pressure_falling_weight=0.1,
        pressure_rising_penalty=0.0,
        cloud_weight=0.1,
        rain_light_weight=-0.1,
        rain_heavy_penalty=-0.6,
        moon_weights={},
        behavior_notes=("Tagaktiv", "Bodenfisch", "Fließgewässer", "Schwarmfisch"),
        recommended_baits=("Rotwurm", "Made", "Kleiner Tauwurm", "Pinkies"),
    ),

}


def normalize_fish_name(name: str | None) -> str:
    if not name:
        return "Weißfisch"

    raw = str(name).strip()
    lower = raw.lower().replace("ÃŸ", "ß")

    for profile_name, profile in FISH_PROFILES.items():
        if lower == profile_name.lower():
            return profile_name
        if lower in profile.aliases:
            return profile_name

    return raw if raw in FISH_PROFILES else "Weißfisch"


def get_fish_profile(name: str | None) -> FishProfile:
    return FISH_PROFILES[normalize_fish_name(name)]


def moon_key(moon_phase: str | None) -> str:
    moon = (moon_phase or "").lower()

    if "full" in moon or "voll" in moon:
        return "full_moon"
    if "new" in moon or "neu" in moon:
        return "new_moon"
    if "wax" in moon or "zunehm" in moon:
        return "waxing"
    if "wan" in moon or "abnehm" in moon:
        return "waning"

    return "unknown"


def is_hour_in_windows(hour: int, windows: tuple[tuple[int, int], ...]) -> bool:
    for start, end in windows:
        if start <= end:
            if start <= hour <= end:
                return True
        else:
            if hour >= start or hour <= end:
                return True
    return False


def profile_summary(name: str | None) -> dict[str, Any]:
    profile = get_fish_profile(name)
    return {
        "name": profile.name,
        "ideal_temperature": profile.temp_range,
        "preferred_hours": profile.preferred_hours,
        "season_months": profile.season_months,
        "recommended_baits": profile.recommended_baits,
        "behavior_notes": profile.behavior_notes,
    }
