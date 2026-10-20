"""Static strategy stays separate from measurements, assignments and game variants."""

import pytest

from necropsy.analysis.class_catalog import CLASS_NAMES
from necropsy.analysis.encounters.strategy import encounter_strategy
from necropsy.raids.scope import configurations
from necropsy.report.render.playbook_view import with_strategy
from necropsy.report.serialize import to_data


def test_sourced_strategy_is_available_to_all_legal_seed_configurations() -> None:
    for zone, encounter in (
        ("mc", 50663),
        ("mc", 50664),
        ("mc", 50665),
        ("mc", 50666),
        ("mc", 50667),
        ("mc", 50668),
        ("mc", 50669),
        ("mc", 50670),
        ("mc", 50671),
        ("mc", 50672),
        ("bwl", 50610),
        ("bwl", 50611),
        ("bwl", 50612),
        ("bwl", 50613),
        ("bwl", 50614),
        ("bwl", 50615),
        ("bwl", 50616),
        ("bwl", 50617),
        ("bwl", 50631),
        ("aq40", 50709),
        ("aq40", 50710),
        ("aq40", 50711),
        ("aq40", 50712),
        ("aq40", 50713),
        ("aq40", 50714),
        ("aq40", 50715),
        ("aq40", 50716),
        ("aq40", 50717),
    ):
        for config in configurations():
            strategy = encounter_strategy(zone, encounter, 1, config.class_id, config.metric)
            assert strategy is not None
            assert {i.section for i in strategy.items} == {"before", "during", "raid"}
            assert all(
                i.kind == "general-strategy" and i.source.startswith("https://")
                for i in strategy.items
            )
            assert "not an observed phase" in strategy.limitation


def test_curse_and_magic_removal_are_class_specific_without_assigning_duty() -> None:
    priest = encounter_strategy("mc", 50663, 1, 7, "hps")
    mage = encounter_strategy("mc", 50663, 1, 4, "dps")
    warrior = encounter_strategy("mc", 50663, 1, 11, "dps")
    assert priest and mage and warrior
    assert any(i.rule == "lucifron-magic-removal-v1" for i in priest.items)
    assert any(i.rule == "lucifron-decurse-v1" for i in mage.items)
    assert not any(
        i.rule in ("lucifron-decurse-v1", "lucifron-magic-removal-v1") for i in warrior.items
    )


def test_viscidus_healing_selection_keeps_healing_context() -> None:
    strategy = encounter_strategy("aq40", 50713, 2, 2, "hps")
    assert strategy
    assert any(i.rule == "viscidus-healing-context-v1" for i in strategy.items)
    assert not any(i.rule == "viscidus-mage-frost-v1" for i in strategy.items)


def test_aq40_capabilities_do_not_assign_every_class_the_same_control_or_removal() -> None:
    capabilities = {
        (50709, "skeram-mage-control-v1"): {"Mage"},
        (50710, "silithid-royalty-poison-removal-v1"): {"Druid", "Paladin", "Shaman"},
        (50711, "sartura-control-v1"): {"Paladin", "Rogue", "Warrior"},
        (50712, "fankriss-spawn-control-v1"): {"Paladin", "Rogue", "Warrior"},
        (50714, "huhuran-tranquilizing-shot-v1"): {"Hunter"},
        (50714, "huhuran-sting-removal-v1"): {"Druid", "Paladin", "Shaman"},
        (50715, "twin-emperors-warlock-tank-v1"): {"Warlock"},
    }
    for (encounter, rule), eligible in capabilities.items():
        for class_id, name in CLASS_NAMES.items():
            for partition in (1, 2):
                for metric in ("dps", "hps"):
                    strategy = encounter_strategy("aq40", encounter, partition, class_id, metric)
                    assert strategy
                    assert any(item.rule == rule for item in strategy.items) is (name in eligible)
            assert encounter_strategy("aq40", encounter, 3, class_id, "dps") is None


def test_aq40_healing_and_dangerous_removal_context_stays_explicit() -> None:
    for encounter, slug in (
        (50709, "skeram"),
        (50710, "silithid-royalty"),
        (50711, "sartura"),
        (50712, "fankriss"),
        (50714, "huhuran"),
        (50715, "twin-emperors"),
        (50716, "ouro"),
        (50717, "cthun"),
    ):
        for metric in ("dps", "hps"):
            strategy = encounter_strategy("aq40", encounter, 1, 7, metric)
            assert strategy
            assert any(i.rule == f"{slug}-healing-v1" for i in strategy.items) is (metric == "hps")
    hunter = encounter_strategy("aq40", 50714, 1, 3, "dps")
    druid = encounter_strategy("aq40", 50714, 1, 2, "hps")
    assert hunter and druid
    assert "separate Berserk" in next(
        i.text for i in hunter.items if i.rule == "huhuran-tranquilizing-shot-v1"
    )
    assert "removal can deal damage" in next(
        i.text for i in druid.items if i.rule == "huhuran-sting-removal-v1"
    )


def test_gehennas_distinguishes_curse_removal_from_patient_healing_context() -> None:
    for class_id, metric, decurse, healing in (
        (2, "hps", True, True),
        (4, "dps", True, False),
        (7, "hps", False, True),
        (11, "dps", False, False),
    ):
        strategy = encounter_strategy("mc", 50665, 1, class_id, metric)
        assert strategy
        rules = {item.rule for item in strategy.items}
        assert ("gehennas-assigned-decurse-v1" in rules) is decurse
        assert ("gehennas-healing-recipient-context-v1" in rules) is healing


def test_geddon_applies_class_and_healing_strategy_without_inventing_duty() -> None:
    for class_id, metric, removal, pets, healing in (
        (7, "hps", True, False, True),
        (6, "dps", True, False, False),
        (3, "dps", False, True, False),
        (11, "dps", False, False, False),
    ):
        strategy = encounter_strategy("mc", 50668, 1, class_id, metric)
        assert strategy
        rules = {item.rule for item in strategy.items}
        assert ("geddon-magic-removal-v1" in rules) is removal
        assert ("geddon-hunter-pet-recovery-v1" in rules) is pets
        assert ("geddon-healer-bomb-coverage-v1" in rules) is healing


def test_geddon_holy_paladin_items_cite_the_verified_source() -> None:
    wiki = "https://warcraft.wiki.gg/wiki/Baron_Geddon"
    strategy = encounter_strategy("mc", 50668, 1, 6, "hps")
    assert strategy
    by_rule = {item.rule: item for item in strategy.items}
    assert set(by_rule) == {
        "geddon-bomb-route-and-coverage-v1",
        "geddon-paladin-cleanse-preparation-v1",
        "geddon-paladin-healer-loadout-applicability-v1",
        "geddon-bomb-and-inferno-recovery-v1",
        "geddon-magic-removal-v1",
        "geddon-healer-bomb-coverage-v1",
        "geddon-bomb-and-dispel-backup-v1",
    }
    assert all(item.source == wiki and item.retrieved == "2026-10-19" for item in by_rule.values())
    for class_id, metric in ((6, "dps"), (7, "hps"), (2, "hps")):
        other = encounter_strategy("mc", 50668, 1, class_id, metric)
        assert other
        assert "geddon-paladin-healer-loadout-applicability-v1" not in {
            item.rule for item in other.items
        }


def test_lucifron_paladin_items_cite_the_verified_source_and_split_by_class() -> None:
    wiki = "https://warcraft.wiki.gg/wiki/Lucifron"
    paladin_only = {
        "lucifron-paladin-cleanse-preparation-v1",
        "lucifron-paladin-healer-loadout-applicability-v1",
        "lucifron-paladin-curse-range-v1",
        "lucifron-paladin-doom-priority-v1",
    }
    strategy = encounter_strategy("mc", 50663, 1, 6, "hps")
    assert strategy
    by_rule = {item.rule: item for item in strategy.items}
    assert paladin_only <= set(by_rule)
    assert "lucifron-magic-removal-v1" not in by_rule
    assert all(
        by_rule[rule].source == wiki and by_rule[rule].retrieved == "2026-10-20"
        for rule in paladin_only
    )
    assert "do not record positions" in by_rule["lucifron-paladin-curse-range-v1"].text
    for class_id, metric in ((6, "dps"), (7, "hps"), (2, "hps"), (4, "dps")):
        other = encounter_strategy("mc", 50663, 1, class_id, metric)
        assert other
        rules = {item.rule for item in other.items}
        assert not paladin_only & rules
        assert ("lucifron-magic-removal-v1" in rules) is (class_id == 7)


def test_shazzrah_keeps_friendly_curse_and_hostile_magic_removal_distinct() -> None:
    for class_id, name in CLASS_NAMES.items():
        strategy = encounter_strategy("mc", 50667, 1, class_id, "dps")
        assert strategy
        rules = {item.rule for item in strategy.items}
        assert ("shazzrah-assigned-curse-removal-v1" in rules) is (name in {"Druid", "Mage"})
        assert ("shazzrah-assigned-boss-purge-v1" in rules) is (name in {"Priest", "Shaman"})


def test_sulfuron_support_capabilities_use_named_classes_without_assigning_duty() -> None:
    for class_id, name in CLASS_NAMES.items():
        for metric in ("dps", "hps"):
            strategy = encounter_strategy("mc", 50669, 1, class_id, metric)
            assert strategy
            rules = {item.rule for item in strategy.items}
            assert ("sulfuron-assigned-interrupts-v1" in rules) is (
                name in {"Druid", "Mage", "Rogue", "Shaman", "Warrior"}
            )
            assert ("sulfuron-friendly-magic-removal-v1" in rules) is (
                name in {"Paladin", "Priest"}
            )
            assert ("sulfuron-divided-healing-coverage-v1" in rules) is (metric == "hps")


def test_unverified_bosses_and_partitions_do_not_inherit_strategy() -> None:
    assert encounter_strategy("mc", 50709, 1, 3, "dps") is None
    assert encounter_strategy("mc", 50631, 1, 3, "dps") is None
    for partition in (3, 7, 11, True):
        assert encounter_strategy("mc", 50663, partition, 3, "dps") is None
    assert encounter_strategy("naxxramas", 51118, 1, 3, "dps") is None


def test_chromaggus_removal_capabilities_do_not_cross_affliction_types() -> None:
    capabilities = {
        "chromaggus-curse-removal-v1": {"Druid", "Mage"},
        "chromaggus-magic-removal-v1": {"Paladin", "Priest"},
        "chromaggus-felhunter-magic-removal-v1": {"Warlock"},
        "chromaggus-disease-removal-v1": {"Paladin", "Priest", "Shaman"},
        "chromaggus-poison-removal-v1": {"Druid", "Paladin", "Shaman"},
        "chromaggus-hunter-frenzy-v1": {"Hunter"},
    }
    for class_id, name in CLASS_NAMES.items():
        for metric in ("dps", "hps"):
            strategy = encounter_strategy("bwl", 50616, 1, class_id, metric)
            assert strategy
            rules = {item.rule for item in strategy.items}
            for rule, classes in capabilities.items():
                assert (rule in rules) is (name in classes), (name, rule)
            assert "chromaggus-hourglass-preparation-v1" in rules


def test_nefarian_call_response_is_for_the_named_class_and_curse_capability() -> None:
    calls = {f"nefarian-{name.lower()}-call-v1" for name in CLASS_NAMES.values()}
    for class_id, name in CLASS_NAMES.items():
        for partition in (1, 2):
            strategy = encounter_strategy("bwl", 50617, partition, class_id, "hps")
            assert strategy
            rules = {item.rule for item in strategy.items}
            assert rules & calls == {f"nefarian-{name.lower()}-call-v1"}
            assert ("nefarian-veil-curse-v1" in rules) is (name in {"Druid", "Mage"})
        assert encounter_strategy("bwl", 50617, 3, class_id, "hps") is None


def test_bwl_control_and_frenzy_capabilities_keep_distinct_encounter_scope() -> None:
    capabilities = {
        (50610, "razorgore-dragonkin-sleep-v1"): "Druid",
        (50610, "razorgore-controller-shield-v1"): "Priest",
        (50612, "broodlord-suppression-duty-v1"): "Rogue",
        (50615, "flamegor-hunter-tranquilizing-shot-v1"): "Hunter",
    }
    for (encounter, rule), required in capabilities.items():
        for class_id, name in CLASS_NAMES.items():
            strategy = encounter_strategy("bwl", encounter, 1, class_id, "dps")
            assert strategy
            assert any(item.rule == rule for item in strategy.items) is (name == required)
    individual = encounter_strategy("bwl", 50614, 1, 4, "dps")
    combined = encounter_strategy("bwl", 50631, 1, 4, "dps")
    assert individual and combined
    assert not {i.rule for i in individual.items} & {i.rule for i in combined.items}
    assert "no dispel type" in next(
        i.text for i in individual.items if i.rule == "ebonroc-shadow-handoff-v1"
    )


def test_old_saved_documents_do_not_acquire_current_strategy_during_render() -> None:
    view = {"pull_before": (), "pull_during": (), "pull_asks": (), "pull_limits": ()}
    assert with_strategy(view, {}) is view
    strategy = encounter_strategy("mc", 50663, 1, 7, "hps")
    updated = with_strategy(view, {"encounter_strategy": to_data(strategy)})
    assert updated["pull_before"] and updated["pull_during"] and updated["pull_asks"]
    assert "not an observed phase" in updated["pull_limits"][0]
    assert updated["pull_before"][0]["sources"][0]["url"].endswith("/Lucifron")
    assert not view["pull_before"]


def test_majordomo_control_capability_is_mage_specific_and_healing_is_metric_specific() -> None:
    for class_id, name in CLASS_NAMES.items():
        for metric in ("dps", "hps"):
            strategy = encounter_strategy("mc", 50671, 1, class_id, metric)
            assert strategy
            rules = {item.rule for item in strategy.items}
            assert ("majordomo-assigned-polymorph-v1" in rules) is (name == "Mage")
            assert ("majordomo-healing-coverage-v1" in rules) is (metric == "hps")


def test_ragnaros_party_support_and_sons_capabilities_use_named_classes() -> None:
    for class_id, name in CLASS_NAMES.items():
        strategy = encounter_strategy("mc", 50672, 1, class_id, "hps")
        assert strategy
        rules = {item.rule for item in strategy.items}
        for rule, owner in (
            ("ragnaros-hunter-sons-control-v1", "Hunter"),
            ("ragnaros-mage-sons-control-v1", "Mage"),
            ("ragnaros-paladin-party-support-v1", "Paladin"),
            ("ragnaros-shaman-party-support-v1", "Shaman"),
        ):
            assert (rule in rules) is (name == owner)
        assert "ragnaros-healing-context-v1" in rules


MC_PALADIN_WIKI = {
    50664: "https://warcraft.wiki.gg/wiki/Magmadar",
    50665: "https://warcraft.wiki.gg/wiki/Gehennas",
    50666: "https://warcraft.wiki.gg/wiki/Garr",
    50667: "https://warcraft.wiki.gg/wiki/Shazzrah",
    50669: "https://warcraft.wiki.gg/wiki/Sulfuron_Harbinger",
    50670: "https://warcraft.wiki.gg/wiki/Golemagg_the_Incinerator",
    50671: "https://warcraft.wiki.gg/wiki/Majordomo_Executus",
    50672: "https://warcraft.wiki.gg/wiki/Ragnaros_(tactics)",
}


@pytest.mark.parametrize("encounter", sorted(MC_PALADIN_WIKI))
def test_mc_paladin_healer_items_cite_the_boss_wiki_and_reach_only_paladin_healers(
    encounter: int,
) -> None:
    strategy = encounter_strategy("mc", encounter, 1, 6, "hps")
    assert strategy
    prefix = f"{MC_PALADIN_WIKI[encounter].rsplit('/', 1)[1].split('_')[0].lower()}-paladin-"
    # The earlier Ragnaros aura item keeps its own Wowhead spell source.
    paladin = [
        i
        for i in strategy.items
        if i.rule.startswith(prefix) and i.rule != "ragnaros-paladin-party-support-v1"
    ]
    assert paladin and {i.section for i in paladin} <= {"before", "during", "raid"}
    assert all(
        i.source == MC_PALADIN_WIKI[encounter] and i.retrieved == "2026-10-20" for i in paladin
    )
    # Every boss states its loadout source limitation instead of inventing a gear rule.
    assert f"{prefix}healer-loadout-applicability-v1" in {i.rule for i in paladin}
    for class_id, metric in ((6, "dps"), (7, "hps"), (2, "hps"), (4, "dps")):
        other = encounter_strategy("mc", encounter, 1, class_id, metric)
        assert other
        assert not {i.rule for i in paladin} & {i.rule for i in other.items}


def test_ragnaros_and_majordomo_paladin_items_keep_only_supported_guide_claims() -> None:
    rag_strategy = encounter_strategy("mc", 50672, 1, 6, "hps")
    assert rag_strategy
    ragnaros = {i.rule: i.text for i in rag_strategy.items}
    ring = ragnaros["ragnaros-paladin-healer-ring-v1"]
    # The guide's Wrath targeting and radius conflict with spell data; neither is certified.
    assert "random player" not in ring and "20 yards" not in ring and "secondary ring" in ring
    engage = ragnaros["ragnaros-paladin-return-engage-v1"]
    assert engage.startswith("After Ragnaros submerges") and "whichever comes first" in engage
    domo_strategy = encounter_strategy("mc", 50671, 1, 6, "hps")
    assert domo_strategy
    majordomo = {i.rule: i.text for i in domo_strategy.items}
    assert "portal" not in majordomo["majordomo-paladin-mage-pairs-v1"]


MC_WIKI = {
    **MC_PALADIN_WIKI,
    50663: "https://warcraft.wiki.gg/wiki/Lucifron",
    50668: "https://warcraft.wiki.gg/wiki/Baron_Geddon",
}


@pytest.mark.parametrize("encounter", sorted(MC_WIKI))
@pytest.mark.parametrize(("class_id", "tag"), [(7, "priest"), (9, "shaman")])
def test_mc_priest_and_shaman_healer_items_cite_the_boss_wiki_and_reach_only_that_class(
    encounter: int, class_id: int, tag: str
) -> None:
    strategy = encounter_strategy("mc", encounter, 1, class_id, "hps")
    assert strategy
    boss = MC_WIKI[encounter].rsplit("/", 1)[1].split("_")[0].lower()
    boss = "geddon" if boss == "baron" else boss
    prefix = f"{boss}-{tag}-"
    # Only the named earlier item keeps its own spell source; any other wrong
    # citation under this prefix fails instead of being filtered away.
    earlier = {"ragnaros-shaman-party-support-v1"}
    own = [i for i in strategy.items if i.rule.startswith(prefix) and i.rule not in earlier]
    assert own
    assert all(i.source == MC_WIKI[encounter] for i in own)
    assert all(i.retrieved in ("2026-10-19", "2026-10-20") for i in own)
    assert any(i.rule == f"{prefix}healer-loadout-applicability-v1" for i in own)
    assert {i.section for i in own} <= {"before", "during", "raid"}
    opposite = 9 if class_id == 7 else 7
    others = ((class_id, "dps"), (opposite, "hps"), (6, "hps"), (2, "hps"), (4, "dps"))
    for other_class, metric in others:
        other = encounter_strategy("mc", encounter, 1, other_class, metric)
        assert other
        assert not {i.rule for i in own} & {i.rule for i in other.items}


def test_fear_and_faction_capability_claims_name_their_limits() -> None:
    def text(encounter: int, class_id: int, rule: str) -> str:
        strategy = encounter_strategy("mc", encounter, 1, class_id, "hps")
        assert strategy
        return next(i.text for i in strategy.items if i.rule == rule)

    assert "Dwarf" in text(50664, 7, "magmadar-priest-fear-ward-v1")
    shaman = text(50664, 9, "magmadar-shaman-fear-counter-source-v1")
    assert "Dwarf" in shaman and "Tremor Totem" in shaman and "not assessed" in shaman
    assert "Horde raid has no Paladins" in text(50671, 9, "majordomo-shaman-pull-roles-source-v1")
    ring = text(50672, 9, "ragnaros-shaman-healer-ring-v1")
    assert "knockback" not in ring and "secondary ring" in ring
    assert text(50663, 7, "lucifron-priest-curse-range-v1").startswith(
        "Lucifron's Curse reaches 40"
    )
