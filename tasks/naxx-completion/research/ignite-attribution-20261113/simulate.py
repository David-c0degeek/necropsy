"""Ignite credit: per tick, equal floor split among contributors of the current instance."""

import collections
import json
import sys
import zipfile
from fractions import Fraction
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
IGN = 12654
HERE = Path(__file__).resolve().parent
rows = json.loads((HERE / "rows.json").read_text(encoding="utf-8"))
want = {(r["report"], r["fight"], r["player"]): r for r in rows if r["cat"] == "Fire" or r["ign"]}
arch = {}
for p in sorted(Path("tests/golden/raids/raw").glob("naxx-*/*.zip")):
    with zipfile.ZipFile(p) as z:
        m = json.loads(z.read("necropsy-snapshot.json"))
        if m["subject"]["class_id"] != 4:
            continue
        for f in m["fights"]:
            arch.setdefault((f["reportID"], f["fightID"]), p)
variants = sys.argv[1:] or ["instance-fire", "instance-any", "instance-fire-noreset"]
res = collections.Counter()
miss = collections.defaultdict(list)
for (code, fid, player), r in want.items():
    p = arch.get((code, fid))
    if not p:
        continue
    z = zipfile.ZipFile(p)
    rep = json.loads(z.read(f"reports/{code}/bundle.json"))["reportData"]["report"]
    fight = next(f for f in rep["fights"] if f["id"] == fid)
    acts = {a["id"]: a for a in rep["masterData"]["actors"]}
    school = {a["gameID"]: a.get("type") for a in rep["masterData"]["abilities"]}
    me = next(
        a["id"] for a in acts.values() if a.get("type") == "Player" and a.get("name") == player
    )
    names = sorted(
        n for n in z.namelist() if n.startswith(f"events/{code}/fight_{fid}/encounter/all_")
    )
    evs = sorted(
        (e for n in names for e in json.loads(z.read(n))["data"]), key=lambda e: e["timestamp"]
    )
    pd = rep.get("playerDetails", {}).get("data", {}).get("playerDetails", {})
    fire = {
        p2["id"]
        for role in pd.values()
        for p2 in role
        if p2.get("type") == "Mage" and any(s.get("spec") == "Fire" for s in p2.get("specs", []))
    }
    mages = {a["id"] for a in acts.values() if a.get("subType") == "Mage"}
    pub = r["pub"]
    dec = len(pub.split(".")[1]) if "." in pub else 0
    infight = set(fight["friendlyPlayers"])
    critters = {
        e["sourceID"]
        for e in evs
        if e.get("type") == "damage"
        and e.get("hitType") == 2
        and school.get(e.get("abilityGameID")) == "4"
        and e.get("abilityGameID") != IGN
    }
    firecasters = {
        e["sourceID"]
        for e in evs
        if e.get("type") == "damage"
        and school.get(e.get("abilityGameID")) == "4"
        and e.get("abilityGameID") != IGN
    }
    fixed = {
        "fw-fire": fire & infight,
        "fw-fire-crit": fire & infight & critters,
        "fw-mage-crit": mages & infight & critters,
        "fw-fire-cast": fire & infight & firecasters,
    }
    for v in variants:
        if v in fixed:
            cf = 0
            for e in evs:
                if e.get("type") == "damage" and e.get("abilityGameID") == IGN:
                    pl = fixed[v] | {e["sourceID"]}
                    k = len(pl)
                    amt = e["amount"]
                    if me in pl:
                        sh = amt // k
                        cf += sh + (amt - sh * k if me == e["sourceID"] else 0)
            good = abs((Fraction(r["nonign"]) + cf) * 1000 / r["d"] - Fraction(pub)) < Fraction(
                1, 10**dec
            )
            res[(v, good)] += 1
            if not good:
                miss[v].append(
                    (
                        r["enc"],
                        player,
                        round(r["need"], 1),
                        cf,
                        round(r["need"] - cf, 1),
                        len(fixed[v]),
                    )
                )
            continue
        if v.startswith("pi"):
            per = collections.defaultdict(set)
            key = (
                (lambda e: (e.get("targetID"), e.get("targetInstance")))
                if "inst" in v
                else (lambda e: e.get("targetID"))
            )
            for e in evs:
                if (
                    e.get("type") == "damage"
                    and e.get("sourceID") in fire & infight
                    and e.get("hitType") == 2
                    and school.get(e.get("abilityGameID")) == "4"
                    and e.get("abilityGameID") != IGN
                ):
                    per[key(e)].add(e["sourceID"])
            cf = Fraction(0) if "frac" in v else 0
            for e in evs:
                if e.get("type") == "damage" and e.get("abilityGameID") == IGN:
                    pl = per[key(e)] or {e["sourceID"]}
                    if "owner" in v:
                        pl = pl | {e["sourceID"]}
                    k = len(pl)
                    amt = e["amount"]
                    if me in pl:
                        if "frac" in v:
                            cf += Fraction(amt, k)
                        else:
                            sh = amt // k
                            rem = amt - sh * k
                            holder = e["sourceID"] if e["sourceID"] in pl else min(pl)
                            cf += sh + (rem if me == holder else 0)
            good = abs((Fraction(r["nonign"]) + cf) * 1000 / r["d"] - Fraction(pub)) < Fraction(
                1, 10**dec
            )
            res[(v, good)] += 1
            if not good:
                miss[v].append(
                    (
                        r["enc"],
                        player,
                        round(r["need"], 1),
                        round(float(cf)),
                        round(r["need"] - float(cf), 1),
                    )
                )
            continue
        if v.startswith("pt"):
            per = collections.defaultdict(set)
            for e in evs:
                if (
                    e.get("type") == "damage"
                    and e.get("sourceID") in fire & infight
                    and (e.get("hitType") == 2 or "cast" in v)
                    and school.get(e.get("abilityGameID")) == "4"
                    and e.get("abilityGameID") != IGN
                ):
                    per[e.get("targetID")].add(e["sourceID"])
            cf = 0
            for e in evs:
                if e.get("type") == "damage" and e.get("abilityGameID") == IGN:
                    pl = per[e.get("targetID")] | {e["sourceID"]}
                    k = len(pl)
                    amt = e["amount"]
                    if me in pl:
                        sh = amt // k
                        cf += sh + (amt - sh * k if me == e["sourceID"] else 0)
            good = abs((Fraction(r["nonign"]) + cf) * 1000 / r["d"] - Fraction(pub)) < Fraction(
                1, 10**dec
            )
            res[(v, good)] += 1
            if not good:
                miss[v].append(
                    (r["enc"], player, round(r["need"], 1), cf, round(r["need"] - cf, 1))
                )
            continue
        if v.startswith("alive"):
            base = fixed["fw-fire-crit"]
            dead = set()
            cf = 0
            deaths = collections.Counter()
            for e in evs:
                if e.get("type") == "death" and e.get("targetID") in base:
                    dead.add(e["targetID"])
                if (
                    v == "alive-res"
                    and e.get("type") in ("resurrect",)
                    and e.get("targetID") in dead
                ):
                    dead.discard(e["targetID"])
                if e.get("type") == "damage" and e.get("abilityGameID") == IGN:
                    pl = (base - dead) | {e["sourceID"]}
                    k = len(pl)
                    amt = e["amount"]
                    if me in pl:
                        sh = amt // k
                        cf += sh + (amt - sh * k if me == e["sourceID"] else 0)
            good = abs((Fraction(r["nonign"]) + cf) * 1000 / r["d"] - Fraction(pub)) < Fraction(
                1, 10**dec
            )
            res[(v, good)] += 1
            if not good:
                miss[v].append(
                    (
                        r["enc"],
                        player,
                        round(r["need"], 1),
                        cf,
                        round(r["need"] - cf, 1),
                        len(base),
                        len(dead),
                    )
                )
            continue
        if v.startswith("cum"):
            elig2 = fire & infight if "fire" in v else mages & infight
            seen = set()
            cf = 0
            for e in evs:
                if (
                    e.get("type") == "damage"
                    and e.get("sourceID") in elig2
                    and (e.get("hitType") == 2 or "cast" in v)
                    and school.get(e.get("abilityGameID")) == "4"
                    and e.get("abilityGameID") != IGN
                ):
                    seen.add(e["sourceID"])
                if e.get("type") == "damage" and e.get("abilityGameID") == IGN:
                    pl = seen | {e["sourceID"]}
                    k = len(pl)
                    amt = e["amount"]
                    if me in pl:
                        sh = amt // k
                        cf += sh + (amt - sh * k if me == e["sourceID"] else 0)
            good = abs((Fraction(r["nonign"]) + cf) * 1000 / r["d"] - Fraction(pub)) < Fraction(
                1, 10**dec
            )
            res[(v, good)] += 1
            if not good:
                miss[v].append(
                    (r["enc"], player, round(r["need"], 1), cf, round(r["need"] - cf, 1), len(seen))
                )
            continue
        elig = fire if "fire" in v else mages
        pool = collections.defaultdict(set)
        cf = 0
        for e in evs:
            t = e.get("targetID")
            if (
                e.get("abilityGameID") == IGN
                and e.get("type") == "removedebuff"
                and "noreset" not in v
            ):
                pool[t] = set()
            if (
                e.get("type") == "damage"
                and e.get("sourceID") in elig
                and e.get("hitType") == 2
                and school.get(e.get("abilityGameID")) == "4"
                and e.get("abilityGameID") != IGN
            ):
                pool[t].add(e["sourceID"])
            if e.get("type") == "damage" and e.get("abilityGameID") == IGN:
                pl = pool[t] | {e["sourceID"]}
                k = len(pl)
                amt = e["amount"]
                if me in pl:
                    sh = amt // k
                    cf += sh + (amt - sh * k if me == e["sourceID"] else 0)
        good = abs((Fraction(r["nonign"]) + cf) * 1000 / r["d"] - Fraction(pub)) < Fraction(
            1, 10**dec
        )
        res[(v, good)] += 1
        if not good:
            miss[v].append((r["enc"], player, round(r["need"], 1), cf, round(r["need"] - cf, 1)))
for k, n in sorted(res.items()):
    print(n, k)
for v in variants:
    print("--", v)
    for x in miss[v][:15]:
        print(x)
