"""The ranking-damage rules reproduce every recorded WCL ranked amount (uv run pytest -m golden).

`external-damage-v1` and the Naxxramas ranking exclusions are empirical: WCL does
not document which adds it leaves out. This test is their standing validation.
Every recorded fight (overall top five per boss plus the subject's kills) must
match the ranked DPS recorded in the oracle within 15 damage over the fight.
"""

from __future__ import annotations

import csv

import pytest

from necropsy.analysis.context import participant_fights
from necropsy.analysis.encounters import encounter_rules
from necropsy.analysis.generic.targets import ranking_damage
from tests.analysis_db import connect, full_db
from tests.fixture_paths import golden_path, is_lfs_pointer, raw_export_path

pytestmark = pytest.mark.golden

ORACLE = "oracle/definitive"
TOLERANCE = 15


def _recorded_dps() -> dict[tuple[str, str], float]:
    recorded: dict[tuple[str, str], float] = {}
    top5 = golden_path(f"{ORACLE}/top5_definitive_with_faction_race_wf.csv")
    with top5.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            recorded[(row["Boss"], row["Hunter"])] = float(row["DPS"])
    playbook = golden_path(f"{ORACLE}/boss_playbook_definitive.csv")
    with playbook.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            recorded[(row["Boss"], "Haplina")] = float(row["Haplina_DPS"])
    return recorded


def test_every_recorded_fight_reproduces_its_ranked_amount() -> None:
    raw = raw_export_path()
    if not raw.is_file() or is_lfs_pointer(raw):
        pytest.fail(f"{raw.name} is missing or an LFS pointer. Run `git lfs pull` first.")
    recorded = _recorded_dps()
    checked = 0
    misses: list[str] = []
    with connect(full_db()) as con:
        for pf in participant_fights(con):
            dps = recorded.get((pf.boss, pf.player))
            if dps is None:
                continue
            rules = encounter_rules("classic_era", "naxxramas", pf.encounter_id)
            ranked = ranking_damage(con, pf, rules.excluded_from_ranking, rules.exclusion_rule)
            expected = dps * pf.duration_ms / 1000.0
            checked += 1
            if ranked.ranked.value is None or abs(ranked.ranked.value - expected) >= TOLERANCE:
                misses.append(f"{pf.boss} / {pf.player}: {ranked.ranked.value} vs {expected:.0f}")
    assert checked == 90
    assert misses == []
