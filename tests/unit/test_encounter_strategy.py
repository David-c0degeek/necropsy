"""Static strategy stays separate from measurements, assignments and game variants."""

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
        ("aq40", 50713),
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
