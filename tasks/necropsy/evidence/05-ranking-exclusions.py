"""Which target names must be excluded per boss so external damage matches oracle rankings?"""
import csv
import itertools
import sys
from collections import defaultdict

import duckdb

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:/repos/necropsy/src")
from necropsy.analysis.context import owned_pets, participant_fights  # noqa: E402

con = duckdb.connect(sys.argv[1], read_only=True)
O = r"C:/repos/necropsy/tests/golden/haplina_naxx/oracle/definitive/"
orc = {(r["Boss"], r["Hunter"]): float(r["DPS"])
       for r in csv.DictReader(open(O + "top5_definitive_with_faction_race_wf.csv", encoding="utf-8"))}
for r in csv.DictReader(open(O + "boss_playbook_definitive.csv", encoding="utf-8")):
    orc[(r["Boss"], "Haplina")] = float(r["Haplina_DPS"])

by_boss = defaultdict(list)
for pf in participant_fights(con):
    own = [pf.actor_id, *[p.actor_id for p in owned_pets(con, pf)]]
    rows = con.execute(
        """SELECT a.name, a.game_id, sum(e.amount) FROM events e
           LEFT JOIN actors a ON a.report_code=e.report_code AND a.actor_id=e.target_id
           WHERE e.report_code=? AND e.fight_id=? AND e.type='damage'
             AND e.source_id IN (SELECT unnest(?::BIGINT[]))
             AND e.target_id NOT IN (SELECT unnest(?::BIGINT[]))
           GROUP BY 1,2""", [pf.report_code, pf.fight_id, own, own]).fetchall()
    target = orc.get((pf.boss, pf.player))
    if target is None:
        continue
    by_boss[pf.boss].append((pf.player, {(n, g): int(a) for n, g, a in rows}, target * pf.duration_ms / 1000))

for boss, rows in sorted(by_boss.items()):
    names = sorted({k for _, d, _ in rows for k in d})
    exact = sum(1 for _, d, t in rows if abs(sum(d.values()) - t) < 15)
    if exact == len(rows):
        continue
    best = None
    for k in range(1, min(4, len(names)) + 1):
        for combo in itertools.combinations(names, k):
            ok = sum(1 for _, d, t in rows
                     if abs(sum(v for n, v in d.items() if n not in combo) - t) < 15)
            if best is None or ok > best[0]:
                best = (ok, combo)
        if best and best[0] == len(rows):
            break
    print(boss, f"exact without exclusions {exact}/{len(rows)}", "best", best[0], best[1])
    for player, d, t in rows:
        print("   ", player, round(t), {f"{n}:{g}": v for (n, g), v in d.items()})
