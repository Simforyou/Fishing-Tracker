
from __future__ import annotations

PREDATOR_KNOWLEDGE = {
    "Zander": {
        "conditions": [
            "Dämmerung und Nacht oft stark",
            "fallender Luftdruck positiv",
            "trübes Wasser häufig gut",
        ],
        "lures": ["Gummifisch", "Jigkopf", "Dropshot", "Twitchbait"],
        "rods": ["Zanderrute", "Spinnrute", "Dropshot-Rute"],
    },
    "Hecht": {
        "conditions": [
            "Windkanten interessant",
            "Wetterwechsel oft aktiv",
            "größere Köder häufig besser",
        ],
        "lures": ["Gummifisch", "Spinner", "Wobbler", "Chatterbait"],
        "rods": ["Hechtrute", "Baitcaster", "Spinnrute"],
    },
    "Barsch": {
        "conditions": [
            "aktive Jagdfenster",
            "Schwarmverhalten",
            "kleine Köder/Finesse",
        ],
        "lures": ["Creature Bait", "Dropshot", "Spinner", "Wobbler"],
        "rods": ["Barschrute", "Finesse-Rute", "Spinnrute"],
    },
}

WHITEFISH_KNOWLEDGE = {
    "Brasse": {
        "methods": ["Feeder", "Method Feeder", "Posenfischen"],
        "rods": ["Feederrute", "Matchrute", "Posenrute"],
    },
    "Rotauge": {
        "methods": ["Stippen", "Match", "Pose"],
        "rods": ["Kopfrute", "Matchrute", "Stipprute"],
    },
    "Karpfen": {
        "methods": ["Method Feeder", "Ansitz", "Boilie"],
        "rods": ["Stellfischrute", "Feederrute", "Karpfenrute"],
    },
}
