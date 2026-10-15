"""Turn a validated analysis.json document into what the report and playbook show.

Everything a reader sees is decided here: wording, number formatting, which
comparison is primary, and how unknown values read. Templates only lay the
result out. The input is the analysis document alone; nothing here reads the
database or recomputes a metric.

Unknown values never become numbers: they render as "Unknown" with the reason
the analysis recorded.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Labels


RULE_HEADINGS: dict[str, str] = {
    "talent-build": "Consider the common talent build",
    "darkmoon-faire": "Match the common Darkmoon Faire buff",
    "trinket": "Review your trinket choice",
    "pet-absent": "Bring your pet into this fight",
    "pet-dps": "Raise your pet's damage",
    "pet-death": "Keep your pet alive",
    "pet-stopped-early": "Keep your pet attacking until the kill",
    "aimed-cadence": "Fit in more Aimed Shots",
    "rapid-fire-unused": "Use Rapid Fire",
    "explosives-unused": "Add explosives",
    "weave-adoption": "Consider Raptor Strike weaving",
    "raid-utility": "Crowd-control duty cost you shots",
    "foreign-target-padding": "Top parses pad on extra targets here",
    "raid-speed-v2": "A long kill limits this parse",
}

RULE_GROUPS: dict[str, str] = {
    "talent-build": "gear",
    "darkmoon-faire": "gear",
    "trinket": "gear",
    "pet-absent": "pet",
    "pet-dps": "pet",
    "pet-death": "pet",
    "pet-stopped-early": "pet",
    "aimed-cadence": "execution",
    "rapid-fire-unused": "execution",
    "explosives-unused": "execution",
    "weave-adoption": "execution",
    "raid-utility": "raid",
    "foreign-target-padding": "raid",
    "raid-speed-v2": "raid",
}

GROUP_TITLES: dict[str, str] = {
    "gear": "Gear & build",
    "pet": "Pet",
    "execution": "Execution & cooldowns",
    "raid": "Raid asks",
}

CONTROLLABILITY: dict[str, str] = {
    "player": "Your execution",
    "gear-build": "Gear & build",
    "pet": "Pet",
    "raid-assignment": "Raid assignment",
    "raid-speed-environment": "Raid speed & environment",
    "faction-racial-external": "Faction, race & externals",
    "rng-low-confidence": "Luck / low confidence",
}

LEVELS: dict[str, str] = {
    "observed": "Observed",
    "derived": "Calculated",
    "inferred": "Inferred",
    "unknown": "Unknown",
}

CATEGORY_LABELS: dict[str, str] = {
    "counted": "Counted",
    "excluded": "Excluded by encounter rule",
    "own": "Own (self or pet)",
    "unclassifiable": "Unidentified",
}

EVIDENCE_LABELS: dict[str, str] = {
    "subject.environment.talents": "Your talent build",
    "benchmarks.baseline.talents": "Comparison talent builds",
    "subject.environment.darkmoon_faire": "Your Darkmoon Faire buff",
    "benchmarks.baseline.darkmoon": "Comparison Darkmoon Faire buffs",
    "subject.hunter.gear.trinkets": "Your trinkets",
    "benchmarks.baseline.trinkets": "Comparison trinkets",
    "subject.hunter.pets": "Your pet-linked actors",
    "subject.hunter.hunter_pets": "Your pet's damage and activity",
    "benchmarks.baseline.medians.pet_dps": "Comparison pet DPS",
    "benchmarks.baseline.tauren_fill.medians.pet_dps": "Tauren-fill pet DPS",
    "subject.hunter.shots.aimed_shot": "Your Aimed Shots",
    "benchmarks.baseline.medians.aimed_per_min": "Comparison Aimed Shot rate",
    "benchmarks.baseline.tauren_fill.medians.aimed_per_min": "Tauren-fill Aimed Shot rate",
    "subject.hunter.rapid_fire": "Your Rapid Fire casts",
    "benchmarks.baseline.medians.first_rapid_fire_s": "Comparison first Rapid Fire",
    "subject.hunter.explosives": "Your explosives",
    "benchmarks.baseline.explosive_users": "Comparison explosive use",
    "subject.raptor_roles": "Your Raptor Strikes by target",
    "benchmarks.baseline.weave.boss": "Comparison weaving on the boss",
    "benchmarks.baseline.weave.non_boss": "Comparison weaving on other NPCs",
    "subject.hunter.friendly_crowd_control": "Your crowd control on raid members",
    "encounter.raid_utility": "Raid-utility window",
    "encounter.target_integrity": "Your damage by target type",
    "encounter.cohort_target_integrity": "Comparison damage by target type",
    "benchmarks.baseline.membership": "How the comparison group was chosen",
    "subject.kill_duration_s": "Your kill time",
    "benchmarks.raid_speed": "Kill-time comparisons",
}

MEDIAN_LABELS: dict[str, str] = {
    "auto_per_min": "Auto Shot rate",
    "aimed_per_min": "Aimed Shot rate",
    "multi_per_min": "Multi-Shot rate",
    "pet_dps": "pet DPS",
    "kill_s": "kill time",
    "first_rapid_fire_s": "first Rapid Fire time",
}

SHOTS = (("auto_shot", "Auto Shot"), ("aimed_shot", "Aimed Shot"), ("multi_shot", "Multi-Shot"))
SMALL_SAMPLE = 4
"""Comparisons on fewer known values than this carry a small-sample label."""
MAX_TIMELINE = 400
MAX_EVIDENCE_PARTS = 8


# ---------------------------------------------------------------------------
# View dataclasses


@dataclass(frozen=True)
class Value:
    """One displayed value: text plus how it is known."""

    text: str
    level: str
    """`observed`, `derived`, `inferred` or `unknown`."""
    note: str | None = None
    show_note: bool = False
    """Show the note even for a known value (supporting context, not a caveat)."""

    @property
    def known(self) -> bool:
        return self.level != "unknown"

    @property
    def level_label(self) -> str:
        return LEVELS.get(self.level, self.level)


@dataclass(frozen=True)
class EvidencePart:
    path: str
    value: str
    level: str
    claim: str
    rule: str | None
    note: str | None
    params: tuple[tuple[str, str], ...]
    refs: tuple[str, ...]
    ref_total: int
    coverage: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceView:
    label: str
    path: str
    parts: tuple[EvidencePart, ...]
    omitted: int
    """Nested evidence objects not listed (the path holds more than the cap)."""


@dataclass(frozen=True)
class Card:
    anchor: str
    rule: str
    group: str
    heading: str
    finding: str
    action: str
    severity: str
    confidence: str
    controllability: str
    benchmark: tuple[tuple[str, str], ...]
    small_sample: str | None
    limitations: tuple[str, ...]
    evidence: tuple[EvidenceView, ...]
    review_key: str


@dataclass(frozen=True)
class MetricRow:
    label: str
    yours: Value
    baseline: Value
    sample: str
    target: Value | None = None


@dataclass(frozen=True)
class KillComparisonView:
    reference: str
    reference_s: Value
    ratio: Value
    n_known: int
    membership: str


@dataclass(frozen=True)
class RaidSpeedView:
    subject_s: str
    median: KillComparisonView
    fastest: KillComparisonView | None
    basis: str
    flagged: bool


@dataclass(frozen=True)
class WeaveRoleView:
    label: str
    known: int
    with_raptor: int
    with_five: int
    verdict: Value
    yours: Value
    adoption: Value
    """The same-faction counts as one value, graded by how the entries were chosen."""


@dataclass(frozen=True)
class TargetShareRow:
    name: str
    kind: str
    aliases: str
    median: Value
    yours: Value
    sample: str


@dataclass(frozen=True)
class TargetRow:
    name: str
    kind: str
    category: str
    damage: str


@dataclass(frozen=True)
class IntegrityView:
    native: Value
    start_trash: Value
    foreign: Value
    foreign_share: Value
    foreign_targets: tuple[str, ...]
    unclassified: tuple[str, ...]
    cohort_median: Value


@dataclass(frozen=True)
class FillView:
    applied: bool
    """True only when at least one filled median is known and can be shown."""
    needed_for: tuple[str, ...]
    eligible: tuple[str, ...]
    excluded: tuple[str, ...]
    medians: tuple[MetricRow, ...]


@dataclass(frozen=True)
class CastRow:
    t_s: str
    kind: str


@dataclass(frozen=True)
class CohortRow:
    player: str
    position: str
    faction: str
    kill_s: str
    ranked_dps: str
    talents: str


@dataclass(frozen=True)
class Fact:
    label: str
    yours: Value
    typical: Value | None = None


@dataclass(frozen=True)
class PlaybookGroup:
    key: str
    title: str
    status: str
    """`action`, `no-change` or `insufficient`."""
    status_text: str
    facts: tuple[Fact, ...]
    cards: tuple[Card, ...]


@dataclass(frozen=True)
class BossView:
    encounter_id: int
    anchor: str
    name: str
    has_subject: bool
    kill_s: str
    ranked_dps: str
    cards: tuple[Card, ...]
    limits: tuple[str, ...]
    execution: tuple[MetricRow, ...]
    cooldowns: tuple[Fact, ...]
    pets: tuple[Fact, ...]
    gear: tuple[Fact, ...]
    timeline: tuple[CastRow, ...]
    timeline_total: int
    auto_gap: Value
    ceiling: tuple[tuple[str, str], ...]
    raid_speed: RaidSpeedView | None
    fill: FillView | None
    cross_faction: str | None
    weave: tuple[WeaveRoleView, ...]
    shares: tuple[TargetShareRow, ...]
    excluded_targets: tuple[str, ...]
    targets: tuple[TargetRow, ...]
    integrity: IntegrityView | None
    cohort: tuple[CohortRow, ...]
    excluded_counts: str
    rules_note: str
    playbook: tuple[PlaybookGroup, ...]
    counts_by_control: tuple[tuple[str, int], ...]
    top_severity: str
    reference: Mapping[str, Any] | None = None

    @property
    def ordered_cards(self) -> tuple[Card, ...]:
        """Stable severity ordering; original card anchors/review keys are retained."""
        order = {"high": 0, "medium": 1, "low": 2}
        return tuple(sorted(self.cards, key=lambda c: order.get(c.severity, 9)))

    @property
    def limit_summary(self) -> str:
        if not self.limits:
            return "Baseline available"
        more = len(self.limits) - 1
        return self.limits[0] + (f" (+{more} more)" if more else "")


@dataclass(frozen=True)
class DocumentView:
    title: str
    character: str
    realm: str
    zone: str
    mode: str
    scope: str
    archive_short: str
    archive_sha: str
    analysis_sha: str
    necropsy_version: str
    schema_version: int
    cross_faction: bool
    limitations: tuple[str, ...]
    coverage: tuple[tuple[str, str], ...]
    bosses: tuple[BossView, ...]
    total_cards: int
    controls: tuple[str, ...] = field(default_factory=tuple)
    reference: Mapping[str, Any] | None = None
    class_document: Mapping[str, Any] | None = None
    selected_spec: str | None = None
    selected_faction: str | None = None
    class_views: Mapping[int, Any] = field(default_factory=dict)
    class_name: str = "Hunter"
    analysis_key: str = "hunter"
    experience: Mapping[str, Any] = field(default_factory=dict)

    @property
    def navigation(self) -> tuple[Any, ...]:
        if self.class_document is None:
            return self.bosses
        return tuple(
            {
                "name": b["boss"],
                "anchor": f"boss-{b['encounter_id']}",
                "cards": b["recommendations"],
            }
            for b in self.class_document["bosses"]
        )


# ---------------------------------------------------------------------------
# Formatting


def _num(value: Any, digits: int = 2) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.{digits}f}"
    return str(value)


def _plain(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, list):
        if len(value) == 2 and all(isinstance(v, int) for v in value):
            return f"{value[0]}–{value[1]}"
        return f"{len(value)} item{'s' if len(value) != 1 else ''}"
    if isinstance(value, dict):
        return ", ".join(f"{k} {_num(v)}" for k, v in sorted(value.items()) if v is not None)
    return _num(value)


def is_evidence(node: Any) -> bool:
    return isinstance(node, dict) and "level" in node and "claim" in node


def value_of(ev: Any, fmt: Any = None, suffix: str = "") -> Value:
    """An evidence object as a displayed Value; unknown keeps its reason."""
    if not is_evidence(ev):
        return Value("Unknown", "unknown", "not recorded")
    level = str(ev["level"])
    note = ev.get("note")
    if level == "unknown" or ev.get("value") is None:
        return Value("Unknown", "unknown", note or "no value recorded")
    raw = ev["value"]
    text = fmt(raw) if fmt is not None else _plain(raw)
    return Value(f"{text}{suffix}", level, note)


def plain_value(raw: Any, fmt: Any = None, suffix: str = "") -> Value:
    if raw is None:
        return Value("Unknown", "unknown", "not recorded")
    return Value(f"{fmt(raw) if fmt else _plain(raw)}{suffix}", "derived")


def _sample(n_known: int, n_unknown: int = 0) -> str:
    text = f"{n_known} known measurements"
    if n_unknown:
        text += f" (+{n_unknown} unknown)"
    if n_known < SMALL_SAMPLE:
        text += " · limited sample"
    return text


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-") or "x"


# ---------------------------------------------------------------------------
# Evidence


def resolve(section: Mapping[str, Any], path: str) -> Any:
    """Follow a dotted evidence path inside one boss section; KeyError if absent."""
    node: Any = section
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(path)
        node = node[part]
    return node


def _ref_text(ref: Mapping[str, Any]) -> str:
    bits = [str(ref.get("source", "?")), str(ref.get("report", "?"))]
    if ref.get("fight") is not None:
        bits.append(f"fight {ref['fight']}")
    if ref.get("actor") is not None:
        bits.append(f"actor {ref['actor']}")
    text = " · ".join(bits)
    if ref.get("detail"):
        text += f" — {ref['detail']}"
    if ref.get("event_count"):
        listed = len(ref.get("events") or [])
        text += f" ({ref['event_count']} events"
        if listed:
            text += f", first {listed} listed"
        text += ")"
    return text


def _part(path: str, ev: Mapping[str, Any]) -> EvidencePart:
    refs = list(ev.get("refs") or [])
    coverage = tuple(
        f"{c['report']} · fight {c['fight']} · actor {c['actor']} · {c['direction']}"
        f" · {'trusted' if c['trusted'] else 'not trusted'}"
        for c in ev.get("coverage") or []
    )
    shown = value_of(ev)
    return EvidencePart(
        path=path,
        value=shown.text,
        level=str(ev["level"]),
        claim=str(ev["claim"]),
        rule=ev.get("rule"),
        note=ev.get("note"),
        params=tuple((str(k), _plain(v)) for k, v in sorted((ev.get("params") or {}).items())),
        refs=tuple(_ref_text(r) for r in refs[:10]),
        ref_total=len(refs),
        coverage=coverage,
    )


def _collect(node: Any, path: str, out: list[tuple[str, Mapping[str, Any]]]) -> None:
    if is_evidence(node):
        out.append((path, node))
        return
    if isinstance(node, dict):
        for k in sorted(node):
            _collect(node[k], f"{path}.{k}", out)
    elif isinstance(node, list):
        for i, child in enumerate(node):
            _collect(child, f"{path}[{i}]", out)


def evidence_view(section: Mapping[str, Any], path: str) -> EvidenceView:
    found: list[tuple[str, Mapping[str, Any]]] = []
    _collect(resolve(section, path), path, found)
    parts = tuple(_part(p, ev) for p, ev in found[:MAX_EVIDENCE_PARTS])
    label = EVIDENCE_LABELS.get(path, path.rsplit(".", 1)[-1].replace("_", " ").capitalize())
    return EvidenceView(label, path, parts, max(0, len(found) - MAX_EVIDENCE_PARTS))


# ---------------------------------------------------------------------------
# Cards


def review_key(analysis_sha: str, encounter_id: int, rec: Mapping[str, Any]) -> str:
    """Stable identity of one finding in one analysis document (for local review marks)."""
    role = str((rec.get("benchmark") or {}).get("role", ""))
    basis = "|".join([str(rec["rule"]), role, *sorted(rec["evidence"]), str(rec["finding"])])
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
    return f"necropsy:v1:{analysis_sha}:{encounter_id}:{rec['rule']}:{digest}"


_BENCH_LABELS = {
    "view": "Comparison",
    "n_known": "Known values",
    "median": "Median",
    "median_pet_dps": "Median pet DPS",
    "dominant": "Most common",
    "share": "Share",
    "target_range": "Target at your kill length",
    "basis": "Basis",
    "threshold": "Flag at",
    "reference": "Compared with",
    "reference_kill_s": "Reference kill (s)",
    "ratio": "Ratio",
    "role": "Target role",
    "with_raptor": "Used Raptor Strike",
    "with_five_raptors": "Five or more",
    "verdict": "Verdict",
    "median_foreign_pct": "Median foreign share (%)",
}
_VIEWS = {
    "same-faction-baseline": "Same-faction baseline",
    "same-faction-median": "Same-faction median kill",
    "same-faction-fastest": "Fastest same-faction kill",
    "same-faction-ceiling": "Best-ranked same-faction entry",
    "tauren-fill": "Tauren fill (fallback)",
}


def _bench_value(key: str, value: Any) -> str:
    if key == "view":
        return _VIEWS.get(str(value), str(value))
    if key == "share" and isinstance(value, float):
        return f"{value * 100:.0f}%"
    if key == "ratio" and isinstance(value, float):
        return f"{value:.2f}×"
    if key == "threshold" and isinstance(value, float):
        return f"{value:.1f}×"
    if key == "role":
        return "the boss" if value == "boss" else "adds and other NPCs"
    return _plain(value)


def _card(
    analysis_sha: str, encounter_id: int, index: int, rec: Mapping[str, Any], section: Any
) -> Card:
    bench = dict(rec.get("benchmark") or {})
    rows = tuple(
        (_BENCH_LABELS.get(k, k.replace("_", " ").capitalize()), _bench_value(k, v))
        for k, v in sorted(bench.items(), key=lambda kv: (kv[0] != "view", kv[0]))
        if v is not None and k != "verdict_rule"
    )
    n = bench.get("n_known")
    small = None
    if bench.get("view") == "tauren-fill":
        small = "Uses other-faction Tauren entries: fallback comparison"
    elif bench.get("view") == "same-faction-fastest":
        small = "Single fastest kill: no median available"
    elif isinstance(n, int) and n < SMALL_SAMPLE:
        small = f"Limited sample: {n} known value{'s' if n != 1 else ''}"
    limitations = tuple(rec.get("limitations") or ())
    rule = str(rec["rule"])
    return Card(
        anchor=f"boss-{encounter_id}-finding-{index + 1}",
        rule=rule,
        group=RULE_GROUPS.get(rule, "execution"),
        heading=RULE_HEADINGS.get(rule, rule.replace("-", " ").capitalize()),
        finding=str(rec["finding"]),
        action=str(rec["recommendation"]),
        severity=str(rec["severity"]),
        confidence=str(rec["confidence"]),
        controllability=CONTROLLABILITY.get(
            str(rec["controllability"]), str(rec["controllability"])
        ),
        benchmark=rows,
        small_sample=small,
        limitations=limitations,
        evidence=tuple(evidence_view(section, p) for p in rec["evidence"]),
        review_key=review_key(analysis_sha, encounter_id, rec),
    )


# ---------------------------------------------------------------------------
# Boss sections


def _median_row(
    label: str, mine: Value, median: Mapping[str, Any] | None, target: Any = None
) -> MetricRow:
    if median is None:
        return MetricRow(label, mine, Value("Unknown", "unknown", "no baseline"), "—")
    return MetricRow(
        label,
        mine,
        value_of(median["value"], lambda v: f"{v:.2f}"),
        _sample(int(median["n_known"]), int(median.get("n_unknown", 0))),
        None if target is None else value_of(target),
    )


def _first_rf(hunter: Mapping[str, Any]) -> Value:
    casts = hunter["rapid_fire"]["casts"]
    if not is_evidence(casts) or casts.get("value") is None:
        return value_of(casts)
    if not casts["value"]:
        return Value("Not cast", str(casts["level"]))
    return Value(f"{casts['value'][0]['t_s']:.1f} s", str(casts["level"]))


def cohort_value(text: str, baseline: Mapping[str, Any] | None) -> Value:
    """A value aggregated over the comparison entries, graded by how they were chosen."""
    if baseline is not None and baseline["membership"]["level"] == "inferred":
        return Value(text, "inferred", "comparison group rests on an inferred faction")
    return Value(text, "derived")


def _distribution_top(
    baseline: Mapping[str, Any] | None, key: str, names: Mapping[str, str]
) -> Value:
    """Most common value among the comparison entries, graded by how they were chosen."""
    dist = None if baseline is None else baseline.get(key)
    if not dist or not dist.get("counts") or not dist.get("n_known"):
        return Value("Unknown", "unknown", "no known values")
    counts = dist["counts"]
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0]
    label = names.get(top[0], top[0])
    return cohort_value(f"{label} ({top[1]}/{dist['n_known']})", baseline)


def _item_names(document: Mapping[str, Any]) -> dict[str, str]:
    names: dict[str, str] = {}
    for boss in document["bosses"]:
        for entry in [boss.get("subject"), *(boss.get("overall_cohort") or boss.get("cohort", []))]:
            if not entry:
                continue
            gear = entry["environment"].get("gear", {})
            for item in gear.get("value") or []:
                if isinstance(item, dict) and item.get("name"):
                    names[str(item["item_id"])] = str(item["name"])
    return names


def _trinkets(hunter: Mapping[str, Any], names: Mapping[str, str]) -> Value:
    def fmt(items: list[dict[str, Any]]) -> str:
        return (
            ", ".join(names.get(str(i["item_id"]), f"item {i['item_id']}") for i in items) or "none"
        )

    return value_of(hunter["gear"]["trinkets"], fmt)


def _names(items: list[Any]) -> str:
    return (
        ", ".join(str(i.get("name", i)) if isinstance(i, dict) else str(i) for i in items) or "none"
    )


def _kill_view(raw: Mapping[str, Any] | None) -> KillComparisonView | None:
    if raw is None:
        return None
    return KillComparisonView(
        reference=str(raw["reference"]),
        reference_s=value_of(raw["reference_s"], lambda v: f"{v:.0f} s"),
        ratio=value_of(raw["ratio"], lambda v: f"{v:.2f}×"),
        n_known=int(raw["n_known"]),
        membership=value_of(raw["membership"]).level_label,
    )


def _raid_speed(raw: Mapping[str, Any] | None) -> RaidSpeedView | None:
    if raw is None:
        return None
    median = _kill_view(raw["vs_median"])
    assert median is not None
    basis = raw.get("basis")
    threshold = raw.get("threshold")
    if basis == "median":
        text = f"Flag basis: same-faction median kill, flagged at {threshold:.1f}× or more."
    elif basis == "fastest":
        text = (
            "Flag basis: fastest same-faction kill (too few kill times for a median), "
            f"flagged at {threshold:.1f}× or more."
        )
    else:
        text = "No comparison available: no same-faction kill times."
    return RaidSpeedView(
        subject_s=f"{raw['subject_s']:.0f} s",
        median=median,
        fastest=_kill_view(raw.get("vs_fastest")),
        basis=text,
        flagged=bool(raw.get("flagged")),
    )


def _weave(baseline: Mapping[str, Any], subject: Mapping[str, Any]) -> tuple[WeaveRoleView, ...]:
    weave = baseline["weave"]
    roles: Any = subject.get("raptor_roles")
    out = []
    for key, label in (("boss", "On the boss"), ("non_boss", "On adds and other NPCs")):
        role = weave[key]
        mine = (
            Value(f"{roles['value'][key]} Raptor Strikes", str(roles["level"]))
            if is_evidence(roles) and roles.get("value") is not None
            else value_of(roles)
        )
        out.append(
            WeaveRoleView(
                label=label,
                known=int(role["known"]),
                with_raptor=int(role["with_raptor"]),
                with_five=int(role["with_five_raptors"]),
                verdict=value_of(role["verdict"]),
                yours=mine,
                adoption=cohort_value(
                    f"{role['with_raptor']} of {role['known']} used it, "
                    f"{role['with_five_raptors']} five or more",
                    baseline,
                ),
            )
        )
    return tuple(out)


def _shares(encounter: Mapping[str, Any]) -> tuple[tuple[TargetShareRow, ...], tuple[str, ...]]:
    raw = encounter.get("ranked_target_shares")
    if not raw:
        return (), ()
    rows = tuple(
        TargetShareRow(
            name=str(s.get("name") or "Unnamed target"),
            kind=str(s["kind"]),
            aliases=", ".join(s.get("aliases") or []),
            median=value_of(s["median_share_pct"], lambda v: f"{v:.1f}%"),
            yours=value_of(s["subject_share_pct"], lambda v: f"{v:.1f}%"),
            sample=_sample(int(s["n_known"]), int(s.get("n_unknown", 0))),
        )
        for s in raw["counted"]
    )
    return rows, tuple(raw.get("excluded") or ())


def _targets(subject: Mapping[str, Any]) -> tuple[TargetRow, ...]:
    by_target = subject["ranking"].get("by_target")
    if not is_evidence(by_target) or not by_target.get("value"):
        return ()
    return tuple(
        TargetRow(
            name=str(
                r.get("name")
                or (f"actor {r['actor_id']}" if r.get("actor_id") is not None else "no target")
            ),
            kind=str(r.get("kind") or "unlisted"),
            category=CATEGORY_LABELS.get(str(r["category"]), str(r["category"])),
            damage=_num(int(r["damage"])),
        )
        for r in by_target["value"]
    )


def _integrity(
    encounter: Mapping[str, Any], baseline: Mapping[str, Any] | None
) -> IntegrityView | None:
    ti = encounter.get("target_integrity")
    if not ti:
        return None
    median = encounter.get("cohort_median_foreign_share_pct")
    return IntegrityView(
        native=value_of(ti["native"]),
        start_trash=value_of(ti["start_trash"]),
        foreign=value_of(ti["foreign"]),
        foreign_share=value_of(ti["foreign_share_pct"], lambda v: f"{v:.1f}%"),
        foreign_targets=tuple(f"{n} ({_num(d)})" for n, d in ti.get("foreign_targets") or []),
        unclassified=tuple(f"{n} ({_num(d)})" for n, d in ti.get("unclassified_targets") or []),
        cohort_median=Value("Unknown", "unknown", "fewer than 3 entries with known shares")
        if median is None
        else cohort_value(f"{median:.1f}%", baseline),
    )


def _fill(baseline: Mapping[str, Any]) -> FillView | None:
    fill = baseline.get("tauren_fill")
    if not fill:
        return None
    rows = tuple(
        _median_row(MEDIAN_LABELS.get(k, k.replace("_", " ")), Value("—", "derived"), m)
        for k, m in sorted(fill["medians"].items())
    )
    return FillView(
        applied=any(m.baseline.known for m in rows),
        needed_for=tuple(MEDIAN_LABELS.get(k, k.replace("_", " ")) for k in fill["needed_for"]),
        eligible=tuple(fill["eligible"]),
        excluded=tuple(f"{p}: {r}" for p, r in fill["excluded"]),
        medians=rows,
    )


def _cohort(rows: Iterable[Mapping[str, Any]]) -> tuple[CohortRow, ...]:
    return tuple(
        CohortRow(
            player=str(e["player"]),
            position="—"
            if e.get("leaderboard_position") is None
            else f"#{e['leaderboard_position']}",
            faction=value_of(e["environment"]["faction"]).text,
            kill_s=f"{e['kill_duration_s']:.0f} s",
            ranked_dps=_plain(e["ranking"].get("ranked_dps")),
            talents=value_of(e["environment"]["talents"]).text,
        )
        for e in rows
    )


def _fact_known(fact: Fact) -> bool:
    return fact.yours.known and (fact.typical is None or fact.typical.known)


def _group_status(cards: list[Card], facts: tuple[Fact, ...]) -> tuple[str, str]:
    """`action`, `no-change` (all inputs known), `partial` (some known) or `insufficient`."""
    if cards:
        n = len(cards)
        return "action", f"{n} thing{'s' if n != 1 else ''} to review"
    known = [_fact_known(f) for f in facts]
    if known and all(known):
        return "no-change", "No change flagged"
    if any(known) or any(f.yours.known for f in facts):
        return "partial", "Partial evidence — no change flagged"
    return "insufficient", "Insufficient evidence"


def _no_hunter_pet(subject: Mapping[str, Any]) -> Value:
    """No Hunter pet in the list: proven only with the export's pet listing present."""
    hunter = subject["hunter"]
    listed = subject.get("pets_listed")
    if listed is None:
        return Value(
            "Unknown", "unknown", "pet-listing availability was not recorded in this analysis"
        )
    if listed is not True:
        return Value("Unknown", "unknown", "the export's pet listing is missing for this fight")
    if any(p["category"].get("value") is None for p in hunter["pets"]):
        return Value("Unknown", "unknown", "a pet-linked actor is unclassified")
    others = [f"{p['name']} ({p['category']['value']})" for p in hunter["pets"]]
    note = ("listed pet-linked actors: " + ", ".join(others)) if others else "no pets listed"
    return Value("None took part", "derived", note, show_note=True)


def _boss(
    document: Mapping[str, Any],
    boss: Mapping[str, Any],
    analysis_sha: str,
    names: Mapping[str, str],
) -> BossView:
    from necropsy.report.render.playbook_view import boss_view

    reference = boss_view(boss, names, analysis_sha, document)
    eid = int(boss["encounter_id"])
    anchor = f"boss-{eid}"
    subject = boss.get("subject")
    benchmarks = boss["benchmarks"]
    baseline = benchmarks.get("baseline")
    encounter = boss["encounter"]
    cards = tuple(
        _card(analysis_sha, eid, i, r, boss) for i, r in enumerate(boss["recommendations"])
    )
    limits: list[str] = []
    rules = boss["rules"]
    rule = rules["ranking_exclusion_rule"]
    rules_note = (
        f"Ranking exclusions: {rule['rule']} ({rule['basis']}"
        + (f"; {rule['validation']}" if rule.get("validation") else "")
        + ")."
    )
    if subject is None:
        return BossView(
            eid,
            anchor,
            str(boss["boss"]),
            False,
            "—",
            "—",
            cards,
            ("No kill for this character in the snapshot.",),
            (),
            (),
            (),
            (),
            (),
            0,
            Value("Unknown", "unknown", "no kill"),
            (),
            None,
            None,
            None,
            (),
            (),
            (),
            (),
            None,
            (),
            "",
            rules_note,
            (),
            (),
            "none",
            reference=reference,
        )
    hunter = subject["hunter"]
    medians = baseline["medians"] if baseline else {}
    targets = baseline["shot_targets"] if baseline else {}
    execution = tuple(
        _median_row(
            f"{label} per minute",
            value_of(hunter["shots"][key]["per_minute"], lambda v: f"{v:.2f}"),
            medians.get(f"{key.split('_')[0]}_per_min"),
            targets.get(key.split("_")[0]),
        )
        for key, label in SHOTS
    )
    pets = []
    for pet in hunter["hunter_pets"]:
        pets.append(
            Fact(
                f"{pet['name']} DPS",
                value_of(pet["dps"], lambda v: f"{v:.1f}"),
                value_of(medians["pet_dps"]["value"], lambda v: f"{v:.1f}")
                if "pet_dps" in medians
                else None,
            )
        )
        pets.append(Fact(f"{pet['name']} family", value_of(pet["family"])))
        deaths = pet["deaths"]["deaths"]
        pets.append(
            Fact(f"{pet['name']} deaths", value_of(deaths, lambda v: str(len(v)) if v else "none"))
        )
    if not hunter["hunter_pets"]:
        pets.append(Fact("Hunter pet in this fight", _no_hunter_pet(subject)))
    cooldowns = (
        Fact(
            "First Rapid Fire",
            _first_rf(hunter),
            value_of(medians["first_rapid_fire_s"]["value"], lambda v: f"{v:.1f} s")
            if "first_rapid_fire_s" in medians
            else None,
        ),
        Fact("Rapid Fire uptime", value_of(hunter["rapid_fire_uptime_s"], lambda v: f"{v:.1f} s")),
        Fact(
            "Quick Shots uptime", value_of(hunter["quick_shots_uptime_s"], lambda v: f"{v:.1f} s")
        ),
        Fact(
            "Explosives used",
            Value(
                str(sum(len(e["casts"]["value"] or []) for e in hunter["explosives"].values())),
                "derived",
            )
            if all(e["casts"].get("value") is not None for e in hunter["explosives"].values())
            else Value("Unknown", "unknown", "explosive casts incomplete"),
            cohort_value(
                f"{baseline['explosive_users']}/{baseline['explosive_known']} entries", baseline
            )
            if baseline
            else None,
        ),
    )
    env = subject["environment"]
    gear = (
        Fact(
            "Talents",
            value_of(env["talents"]),
            _distribution_top(baseline, "talents", {}),
        ),
        Fact(
            "Darkmoon Faire",
            value_of(env["darkmoon_faire"]),
            _distribution_top(baseline, "darkmoon", {}),
        ),
        Fact(
            "Trinkets",
            _trinkets(hunter, names),
            _distribution_top(baseline, "trinkets", names),
        ),
        Fact("World buffs", value_of(env["world_buffs"], _names)),
        Fact(
            "Windfury",
            Value(
                str(env["windfury"]["status"]).replace("-", " "),
                "unknown" if env["windfury"]["status"] == "unknown" else "derived",
            ),
        ),
    )
    casts: list[dict[str, Any]] = []
    for group in (hunter["shots"], {"rapid_fire": hunter["rapid_fire"]}, hunter["explosives"]):
        for stats in group.values():
            if is_evidence(stats["casts"]) and stats["casts"].get("value"):
                casts.extend(stats["casts"]["value"])
    casts.sort(key=lambda c: (c["t_s"], c["kind"], c["event_uid"]))
    timeline = tuple(
        CastRow(f"{c['t_s']:.2f}", str(c["kind"]).replace("_", " ")) for c in casts[:MAX_TIMELINE]
    )
    gap = hunter["auto_gap"]
    flagged = gap["flagged"]
    auto_gap = value_of(flagged, lambda v: f"{len(v)} long gaps (advisory)")
    if baseline is None:
        limits.append("No same-faction comparison: the character's faction is unknown.")
    else:
        for key, m in sorted(medians.items()):
            if m["value"].get("value") is None:
                label = MEDIAN_LABELS.get(key, key.replace("_", " "))
                limits.append(f"Same-faction {label} unknown: {m['value'].get('note')}")
        fill = baseline.get("tauren_fill")
        if fill:
            if any(m["value"].get("value") is not None for m in fill["medians"].values()):
                limits.append("A Tauren fill fallback supplies some comparisons.")
            elif fill["eligible"]:
                limits.append(
                    "A Tauren fill was considered; qualifying entries were still too few "
                    "for a median."
                )
            else:
                limits.append("A Tauren fill was considered, but no other-faction entry qualified.")
        membership = baseline["membership"]
        if membership["level"] == "inferred":
            limits.append("Same-faction membership rests on an inferred faction.")
    ceiling_raw = benchmarks.get("ceiling")
    ceiling = (
        ()
        if ceiling_raw is None
        else (
            ("Player", str(ceiling_raw["player"])),
            (
                "Leaderboard position",
                "—"
                if ceiling_raw["leaderboard_position"] is None
                else f"#{ceiling_raw['leaderboard_position']}",
            ),
            ("Ranked DPS", _plain(ceiling_raw["ranked_dps"])),
            ("Kill time", f"{ceiling_raw['kill_duration_s']:.0f} s"),
            ("Membership", value_of(ceiling_raw["membership"]).level_label),
        )
    )
    cross = benchmarks.get("cross_faction")
    shares, excluded_targets = _shares(encounter)
    excluded = benchmarks.get("excluded")
    speed = _raid_speed(benchmarks.get("raid_speed"))
    playbook_facts: dict[str, tuple[Fact, ...]] = {
        "gear": gear,
        "pet": tuple(pets),
        "execution": tuple(Fact(r.label, r.yours, r.baseline) for r in execution) + cooldowns,
        "raid": (
            Fact(
                "Kill time",
                Value(f"{subject['kill_duration_s']:.0f} s", "derived"),
                speed.median.reference_s if speed is not None else None,
            ),
        ),
    }
    playbook = []
    for key in ("gear", "pet", "execution", "raid"):
        group_cards = [c for c in cards if c.group == key]
        status, text = _group_status(group_cards, playbook_facts[key])
        playbook.append(
            PlaybookGroup(
                key, GROUP_TITLES[key], status, text, playbook_facts[key], tuple(group_cards)
            )
        )
    controls: dict[str, int] = {}
    for c in cards:
        controls[c.controllability] = controls.get(c.controllability, 0) + 1
    order = {"high": 0, "medium": 1, "low": 2}
    top = min((c.severity for c in cards), key=lambda s: order.get(s, 9), default="none")
    return BossView(
        encounter_id=eid,
        anchor=anchor,
        name=str(boss["boss"]),
        has_subject=True,
        kill_s=f"{subject['kill_duration_s']:.0f} s",
        ranked_dps=_plain(subject["ranking"].get("ranked_dps")),
        cards=cards,
        limits=tuple(limits),
        execution=execution,
        cooldowns=cooldowns,
        pets=tuple(pets),
        gear=gear,
        timeline=timeline,
        timeline_total=len(casts),
        auto_gap=auto_gap,
        ceiling=ceiling,
        raid_speed=speed,
        fill=_fill(baseline) if baseline else None,
        cross_faction=None
        if cross is None
        else f"{cross['label']} Rank one: {cross.get('rank_one') or '—'}.",
        weave=_weave(baseline, subject) if baseline else (),
        shares=shares,
        excluded_targets=excluded_targets,
        targets=_targets(subject),
        integrity=_integrity(encounter, baseline),
        cohort=_cohort(boss["cohort"]),
        excluded_counts=""
        if not excluded
        else f"Left out of the comparison: {excluded['other_faction']} other-faction, "
        f"{excluded['unknown_faction']} unknown-faction entries.",
        rules_note=rules_note,
        playbook=tuple(playbook),
        counts_by_control=tuple(sorted(controls.items())),
        top_severity=top,
        reference=reference,
    )


def document_view(document: Mapping[str, Any], analysis_sha: str) -> DocumentView:
    from necropsy.analysis.class_catalog import CLASS_NAMES
    from necropsy.report.render.class_view import bosses as class_bosses
    from necropsy.report.render.experience import experience
    from necropsy.report.render.playbook_view import overview_view

    names = _item_names(document)
    is_class = document["subject"]["class_id"] != 3
    class_id = document["subject"]["class_id"]
    analysis_key = "druid" if class_id == 2 else "combat"
    bosses = (
        ()
        if is_class
        else tuple(_boss(document, b, analysis_sha, names) for b in document["bosses"])
    )
    subject = document["subject"]
    snapshot = document["snapshot"]
    coverage = document["coverage"]
    return DocumentView(
        title=f"{subject['name']} · {document['zone']['name']}",
        character=str(subject["name"]),
        realm=f"{subject['server']} ({subject['region']})",
        zone=str(document["zone"]["name"]),
        mode=str(document["mode"]),
        scope=str(snapshot["scope"]),
        archive_short=str(snapshot["archive_sha256"])[:12],
        archive_sha=str(snapshot["archive_sha256"]),
        analysis_sha=analysis_sha,
        necropsy_version=str(document["necropsy_version"]),
        schema_version=int(document["schema_version"]),
        cross_faction=bool(document["options"]["cross_faction"]),
        limitations=tuple(document["cohort"]["limitations"]),
        coverage=(
            ("Event streams", _num(coverage["streams"])),
            ("Streams not complete", _num(coverage["streams_not_complete"])),
            ("Event anomalies", _num(coverage["event_anomalies"])),
            ("Snapshot issues", _num(coverage["snapshot_issues"])),
        ),
        bosses=bosses,
        total_cards=sum(len(b.cards) for b in bosses),
        reference={"faction_label": CLASS_NAMES[class_id] + " encounter roles"}
        if is_class
        else overview_view(document),
        class_document=document if is_class else None,
        class_views=class_bosses(document, analysis_sha, analysis_key) if is_class else {},
        class_name=CLASS_NAMES[class_id],
        analysis_key=analysis_key if is_class else "hunter",
        experience=experience(document, CLASS_NAMES[class_id]),
        selected_spec=(document.get("acquisition") or {}).get("selected_category")
        or (
            (document["bosses"][0].get("playbook") or {}).get("selected_category")
            if is_class and document["bosses"]
            else None
        ),
        selected_faction=(document.get("acquisition") or {}).get("subject_faction")
        or (
            (document["bosses"][0].get("playbook") or {}).get("selected_faction")
            if is_class and document["bosses"]
            else None
        ),
    )


__all__ = ["DocumentView", "document_view", "evidence_view", "resolve", "review_key"]
