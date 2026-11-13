"""Ignite: what Ignite credit does published DPS imply, vs the mage's own fire crits?"""

import collections
import json
import sys
import zipfile
from fractions import Fraction
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from scripts import comparison_followup as fu  # noqa: E402
from scripts import freeze_dps_ranking as dps  # noqa: E402

HERE = Path(__file__).resolve().parent
REGISTER = Path("tasks/naxx-completion/followup-comparisons.json")

real = dps.consistent
orig = dps.compute
out = []
IGNITE = 12654


def rec(spec, base, metric="dps"):
    dps.consistent = lambda *a: True
    try:
        res = orig(spec, base, metric=metric)
    finally:
        dps.consistent = real
    if metric != "dps" or spec["class"] != "Mage":
        return res
    d, pub, R = res["duration_ms"], res["published"], res["totals"]["ranked"]
    ign = sum(
        e["raw"]["amount"] * e["multiplicity"]
        for e in res["events"]
        if e["disposition"] == "ranked" and e["raw"].get("abilityGameID") == IGNITE
    )
    crit = collections.Counter()
    hits = collections.Counter()
    for e in res["events"]:
        raw = e["raw"]
        if e["disposition"] != "ranked" or raw.get("abilityGameID") == IGNITE:
            continue
        a = raw.get("abilityGameID")
        amt = raw["amount"] + (raw.get("absorbed") or 0)
        if raw.get("hitType") == 2:
            crit[a] += amt * e["multiplicity"]
        hits[a] += amt * e["multiplicity"]
    need = Fraction(pub) * d / 1000 - (R - ign)
    out.append(
        {
            "cat": spec["category"],
            "enc": spec["encounter"],
            "player": spec["player"],
            "report": spec["report"],
            "fight": spec["fight"],
            "ok": real(R, d, pub),
            "ign": ign,
            "need": float(need),
            "crit": dict(crit),
            "nonign": R - ign,
            "pub": pub,
            "d": d,
        }
    )
    return res


dps.compute = rec
register = json.loads(REGISTER.read_bytes())
for a in sorted({c["archive"]["path"] for c in register["cells"]}):
    with zipfile.ZipFile(a) as z:
        s = json.loads(z.read("necropsy-snapshot.json"))["subject"]
    if s["class_id"] == 4 and s.get("ranking_metric", "dps") == "dps":
        fu.cells(Path(a))
text = json.dumps(out, ensure_ascii=False, default=str) + "\n"
(HERE / "rows.json").write_text(text, encoding="utf-8")
print(len(out))
