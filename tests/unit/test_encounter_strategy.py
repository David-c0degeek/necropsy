"""Static strategy stays separate from measurements, assignments and game variants."""

from necropsy.analysis.encounters.strategy import encounter_strategy
from necropsy.raids.scope import configurations
from necropsy.report.render.playbook_view import with_strategy
from necropsy.report.serialize import to_data


def test_sourced_strategy_is_available_to_all_legal_seed_configurations() -> None:
    for zone, encounter in (("mc", 50663), ("bwl", 50631), ("aq40", 50713)):
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


def test_unverified_bosses_and_partitions_do_not_inherit_strategy() -> None:
    assert encounter_strategy("mc", 50664, 1, 3, "dps") is None
    assert encounter_strategy("mc", 50631, 1, 3, "dps") is None
    for partition in (3, 7, 11, True):
        assert encounter_strategy("mc", 50663, partition, 3, "dps") is None
    assert encounter_strategy("naxxramas", 51118, 1, 3, "dps") is None


def test_old_saved_documents_do_not_acquire_current_strategy_during_render() -> None:
    view = {"pull_before": (), "pull_during": (), "pull_asks": (), "pull_limits": ()}
    assert with_strategy(view, {}) is view
    strategy = encounter_strategy("mc", 50663, 1, 7, "hps")
    updated = with_strategy(view, {"encounter_strategy": to_data(strategy)})
    assert updated["pull_before"] and updated["pull_during"] and updated["pull_asks"]
    assert "not an observed phase" in updated["pull_limits"][0]
    assert updated["pull_before"][0]["sources"][0]["url"].endswith("/Lucifron")
    assert not view["pull_before"]
