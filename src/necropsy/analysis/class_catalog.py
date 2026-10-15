"""Verified Classic Era ranking categories; ranking labels are not talent trees."""

CLASS_NAMES = {
    2: "Druid",
    3: "Hunter",
    4: "Mage",
    6: "Paladin",
    7: "Priest",
    8: "Rogue",
    9: "Shaman",
    10: "Warlock",
    11: "Warrior",
}

CATEGORIES = {
    4: {"Fire": ("dps", "dps"), "Frost": ("dps", "dps")},
    6: {"Holy": ("hps", "healer"), "Protection": ("dps", "tank"), "Retribution": ("dps", "dps")},
    7: {"Holy": ("hps", "healer"), "Shadow": ("dps", "dps")},
    8: {"Assassination": ("dps", "dps")},
    9: {
        "Elemental": ("dps", "dps"),
        "Enhancement": ("dps", "dps"),
        "Restoration": ("hps", "healer"),
    },
    10: {"Destruction": ("dps", "dps")},
    11: {"Fury": ("dps", "dps"), "Protection": ("dps", "tank")},
}


def category_for(class_id: int, category: str | None) -> str | None:
    """Resolve role aliases only after the character's class is known."""
    aliases = {
        6: {"Healer": "Holy", "Guardian": "Protection", "DPS": "Retribution"},
        7: {"Healer": "Holy", "DPS": "Shadow"},
        8: {"DPS": "Assassination"},
        9: {"Healer": "Restoration"},
        10: {"DPS": "Destruction"},
        11: {"DPS": "Fury", "Guardian": "Protection"},
    }
    return aliases.get(class_id, {}).get(category or "", category)
