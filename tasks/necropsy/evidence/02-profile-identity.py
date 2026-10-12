"""Do the same events carry identical JSON in different streams? Compare full-JSON vs core-key identity."""

import collections
import json
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
z = zipfile.ZipFile(sys.argv[1])
names = [n for n in z.namelist() if not n.endswith("/")]
CORE = (
    "timestamp",
    "type",
    "sourceID",
    "sourceInstance",
    "targetID",
    "targetInstance",
    "abilityGameID",
    "fight",
    "amount",
    "hitType",
    "stack",
    "extraAbilityGameID",
    "overheal",
    "absorbed",
    "resourceChange",
)
streams = collections.defaultdict(list)
for n in names:
    if n.startswith("events/") and n.rsplit("/", 1)[-1][:6] in ("source", "target"):
        streams[n.rsplit("_", 1)[0]].append(n)
by_fight = collections.defaultdict(list)
for key in streams:
    p = key.split("/")
    by_fight[(p[1], p[2])].append(key)

mismatch_examples = []
stats = collections.Counter()
for _fk, keys in list(by_fight.items()):
    full_counts = []
    core_counts = []
    core_to_full = collections.defaultdict(set)
    for key in keys:
        evs = []
        for page in sorted(streams[key]):
            evs.extend((json.loads(z.read(page)) or {}).get("data") or [])
        fc = collections.Counter(json.dumps(e, sort_keys=True) for e in evs)
        cc = collections.Counter(tuple(e.get(k) for k in CORE) for e in evs)
        for e in evs:
            core_to_full[tuple(e.get(k) for k in CORE)].add(json.dumps(e, sort_keys=True))
        full_counts.append(fc)
        core_counts.append(cc)

    def merged(counts):
        m = collections.Counter()
        for c in counts:
            for k, v in c.items():
                m[k] = max(m[k], v)
        return m

    def inconsistent(counts):
        seen = collections.defaultdict(set)
        for c in counts:
            for k, v in c.items():
                seen[k].add(v)
        return sum(1 for s in seen.values() if len(s) > 1)

    stats["full_unique_after_merge"] += sum(merged(full_counts).values())
    stats["core_unique_after_merge"] += sum(merged(core_counts).values())
    stats["full_multiplicity_inconsistent_ids"] += inconsistent(full_counts)
    stats["core_multiplicity_inconsistent_ids"] += inconsistent(core_counts)
    multi = [v for v in core_to_full.values() if len(v) > 1]
    stats["core_keys_with_differing_json"] += len(multi)
    if multi and len(mismatch_examples) < 2:
        a, b = sorted(multi[0])[:2]
        da, db = json.loads(a), json.loads(b)
        mismatch_examples.append(
            {k: (da.get(k), db.get(k)) for k in set(da) | set(db) if da.get(k) != db.get(k)}
        )
print(dict(stats))
for ex in mismatch_examples:
    print("diff fields:", ex)
