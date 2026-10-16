"""Classic Era game catalog and separately namespaced WCL ranking categories."""

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

# These IDs belong to WCL, not Blizzard's class-ID namespace.
TALENT_TREES = {
    2: ("Balance", "Feral Combat", "Restoration"),
    3: ("Beast Mastery", "Marksmanship", "Survival"),
    4: ("Arcane", "Fire", "Frost"),
    6: ("Holy", "Protection", "Retribution"),
    7: ("Discipline", "Holy", "Shadow"),
    8: ("Assassination", "Combat", "Subtlety"),
    9: ("Elemental", "Enhancement", "Restoration"),
    10: ("Affliction", "Demonology", "Destruction"),
    11: ("Arms", "Fury", "Protection"),
}

# category slug -> (WCL category ID within class, WCL display name).
# Metadata verified against the Vanilla API on 2026-10-16.
WCL_CATEGORIES = {
    2: {
        "Balance": (1, "Balance"),
        "Feral": (2, "Feral"),
        "Guardian": (3, "Tank"),
        "Restoration": (4, "Healer"),
    },
    3: {"Marksmanship": (2, "Marksmanship")},
    4: {"Fire": (2, "Fire"), "Frost": (3, "Frost")},
    6: {"Holy": (1, "Healer"), "Protection": (2, "Tank"), "Retribution": (3, "DPS")},
    7: {"Holy": (2, "Healer"), "Shadow": (3, "DPS")},
    8: {"Assassination": (1, "DPS")},
    9: {
        "Elemental": (1, "Elemental"),
        "Enhancement": (2, "Enhancement"),
        "Restoration": (3, "Healer"),
    },
    10: {"Destruction": (3, "DPS")},
    11: {"Fury": (2, "DPS"), "Protection": (3, "Tank")},
}

# Blizzard's Classic primer: ruleset validity, never an observation of a player.
RACES = {
    "Dwarf": ("Alliance", frozenset((3, 6, 7, 8, 11))),
    "Gnome": ("Alliance", frozenset((4, 8, 10, 11))),
    "Human": ("Alliance", frozenset((4, 6, 7, 8, 10, 11))),
    "Night Elf": ("Alliance", frozenset((2, 3, 7, 8, 11))),
    "Orc": ("Horde", frozenset((3, 8, 9, 10, 11))),
    "Tauren": ("Horde", frozenset((2, 3, 9, 11))),
    "Troll": ("Horde", frozenset((3, 4, 7, 8, 9, 11))),
    "Undead": ("Horde", frozenset((4, 7, 8, 10, 11))),
}


def talent_tree(class_id: int, value: str | None) -> str | None:
    """Validate declared intent without selecting a WCL filter or encounter role."""
    if value is None or not value.strip():
        return None
    key = value.strip().casefold().replace(" ", "")
    aliases = {
        "bm": "beastmastery",
        "mm": "marksmanship",
        "marksman": "marksmanship",
        "feral": "feralcombat",
    }
    key = aliases.get(key, key)
    for name in TALENT_TREES.get(class_id, ()):
        if name.casefold().replace(" ", "") == key:
            return name
    raise ValueError(
        f"choose a {CLASS_NAMES.get(class_id, 'supported class')} talent tree: "
        + ", ".join(TALENT_TREES.get(class_id, ()))
    )


def category_label(class_id: int, slug: str | None) -> str:
    if slug is None:
        return "All Hunter categories" if class_id == 3 else "Unknown"
    record = WCL_CATEGORIES.get(class_id, {}).get(slug)
    return record[1] if record else slug


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
