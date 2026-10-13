"""Gothik weave by side/phase, and which targets count toward ranked damage per boss.

Usage: uv run python tasks/necropsy/evidence/05-gothik-and-parse-targets.py <full.duckdb>
"""

import statistics
import sys
from collections import defaultdict

import duckdb

from necropsy.analysis.context import owned_pets, participant_fights
from necropsy.analysis.encounters import encounter_rules
from necropsy.analysis.generic.environment import environment_profile

sys.stdout.reconfigure(encoding="utf-8")
con = duckdb.connect(sys.argv[1], read_only=True)
RAPTOR = [14263, 14265, 14266]
LIVING = {16124, 16125, 16126}
SPECTRAL = {16127, 16148, 16149, 16150}
GOTHIK = 16060

pfs = participant_fights(con)

print("=== Gothik: per Hunter, side by damage and Raptor Strike targets ===")
for pf in pfs:
    if pf.encounter_id != 51109:
        continue
    faction = environment_profile(con, pf).faction.value
    own = [pf.actor_id, *[p.actor_id for p in owned_pets(con, pf)]]
    rows = con.execute(
        """SELECT a.game_id, a.name, sum(coalesce(e.amount,0))
           FROM events e LEFT JOIN actors a ON a.report_code=e.report_code AND a.actor_id=e.target_id
           WHERE e.report_code=? AND e.fight_id=? AND e.type='damage' AND e.source_id=?
           GROUP BY 1,2""",
        [pf.report_code, pf.fight_id, pf.actor_id],
    ).fetchall()
    living = sum(r[2] for r in rows if r[0] in LIVING)
    spectral = sum(r[2] for r in rows if r[0] in SPECTRAL)
    boss = sum(r[2] for r in rows if r[0] == GOTHIK)
    other = sum(r[2] for r in rows if r[0] not in LIVING | SPECTRAL | {GOTHIK})
    first_boss = con.execute(
        """SELECT min(e.timestamp) FROM events e JOIN actors a
             ON a.report_code=e.report_code AND a.actor_id=e.target_id
           WHERE e.report_code=? AND e.fight_id=? AND e.type='damage' AND a.game_id=?""",
        [pf.report_code, pf.fight_id, GOTHIK],
    ).fetchone()[0]
    start = con.execute(
        "SELECT start_time FROM fights WHERE report_code=? AND fight_id=?",
        [pf.report_code, pf.fight_id],
    ).fetchone()[0]
    raptors = con.execute(
        """SELECT e.timestamp, a.game_id, a.name FROM events e
           LEFT JOIN actors a ON a.report_code=e.report_code AND a.actor_id=e.target_id
           WHERE e.report_code=? AND e.fight_id=? AND e.type='cast' AND e.source_id=?
             AND e.ability_game_id IN (SELECT unnest(?::BIGINT[])) ORDER BY 1""",
        [pf.report_code, pf.fight_id, pf.actor_id, RAPTOR],
    ).fetchall()
    side = "living" if living > spectral else "spectral"
    boss_phase = None if first_boss is None else round((first_boss - start) / 1000)
    rap = defaultdict(lambda: [0, 0])  # name -> [before boss phase, boss phase]
    for ts, gid, name in raptors:
        rap[name][int(first_boss is not None and ts >= first_boss)] += 1
    print(
        f"{pf.player:14} {pf.kind:5} {str(faction):8} pos={pf.leaderboard_position} "
        f"kill={pf.duration_ms/1000:.0f}s side={side} living={living} spectral={spectral} "
        f"gothik={boss} other={other} gothik_from={boss_phase}s raptors={len(raptors)} "
        f"{dict(rap)}"
    )

print("\n=== Ranked damage by target, per boss (median share over the recorded top five) ===")
by_boss: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
excluded_names: dict[str, set[str]] = defaultdict(set)
for pf in pfs:
    if pf.kind == "you":
        continue
    rules = encounter_rules("classic_era", "naxxramas", pf.encounter_id)
    own = [pf.actor_id, *[p.actor_id for p in owned_pets(con, pf)]]
    rows = con.execute(
        """SELECT a.game_id, a.name, sum(coalesce(e.amount,0))
           FROM events e LEFT JOIN actors a ON a.report_code=e.report_code AND a.actor_id=e.target_id
           WHERE e.report_code=? AND e.fight_id=? AND e.type='damage'
             AND e.source_id IN (SELECT unnest(?::BIGINT[]))
             AND e.target_id NOT IN (SELECT unnest(?::BIGINT[]))
           GROUP BY 1,2""",
        [pf.report_code, pf.fight_id, own, own],
    ).fetchall()
    counted = {(g, n): a for g, n, a in rows if not rules.excluded_from_ranking(g, n)}
    total = sum(counted.values()) or 1
    for (g, n), a in counted.items():
        by_boss[pf.boss][f"{n} ({g})"].append(100.0 * a / total)
    for g, n, a in rows:
        if rules.excluded_from_ranking(g, n):
            excluded_names[pf.boss].add(f"{n} ({g})")

for boss, targets in by_boss.items():
    print(f"\n{boss}  excluded: {sorted(excluded_names[boss]) or '-'}")
    for name, shares in sorted(targets.items(), key=lambda kv: -statistics.median(kv[1] + [0] * (5 - len(kv[1])))):
        padded = shares + [0.0] * (5 - len(shares))
        med = statistics.median(padded)
        if max(shares) >= 1.0:
            print(f"   {name:45} median {med:5.1f}%  max {max(shares):5.1f}%  in {len(shares)}/5")
