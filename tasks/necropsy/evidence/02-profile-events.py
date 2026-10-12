"""Read-only profile of the full export for ingest design."""

import collections
import json
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
z = zipfile.ZipFile(sys.argv[1])
names = [n for n in z.namelist() if not n.endswith("/")]

types = collections.Counter()
fields = collections.defaultdict(collections.Counter)
dup_within_stream = 0
page_boundary_overlap = 0
cross_stream_dup = 0
total = 0
streams = collections.defaultdict(list)
for n in names:
    if n.startswith("events/") and n.rsplit("/", 1)[-1][:6] in ("source", "target"):
        streams[n.rsplit("_", 1)[0]].append(n)

per_fight = collections.defaultdict(list)  # (code,fight) -> list of (stream, events)
for key, pages in streams.items():
    evs = []
    prev_last = None
    for page in sorted(pages):
        d = json.loads(z.read(page)) or {}
        data = d.get("data") or []
        if prev_last is not None and data and json.dumps(data[0], sort_keys=True) == prev_last:
            page_boundary_overlap += 1
        if data:
            prev_last = json.dumps(data[-1], sort_keys=True)
        evs.extend(data)
    c = collections.Counter(json.dumps(e, sort_keys=True) for e in evs)
    dup_within_stream += sum(v - 1 for v in c.values() if v > 1)
    total += len(evs)
    for e in evs:
        types[e["type"]] += 1
        for k in e:
            fields[e["type"]][k] += 1
    parts = key.split("/")
    per_fight[(parts[1], parts[2])].append((key, c))

for _fk, lst in per_fight.items():
    allc = collections.Counter()
    for _, c in lst:
        for k, v in c.items():
            allc[k] += v
    merged_max = collections.Counter()
    for _, c in lst:
        for k, v in c.items():
            merged_max[k] = max(merged_max[k], v)
    cross_stream_dup += sum(allc.values()) - sum(merged_max.values())

print("streams", len(streams), "events", total)
print("exact dup within a stream (same JSON):", dup_within_stream)
print("page-boundary first==prev last:", page_boundary_overlap)
print("cross-stream copies removable by max-multiplicity:", cross_stream_dup)
print("types:", types.most_common())
allkeys = collections.Counter()
for _t, c in fields.items():
    allkeys.update(c.keys())
print("fields:", sorted(allkeys))
