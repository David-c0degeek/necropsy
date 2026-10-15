"""Acquire one character's Naxxramas data: subject fights, cohorts, deep event streams.

The analyze CLI passes the acquired data to the snapshot writer and offline pipeline.

Per supported boss: the subject's own fight is chosen from its rankings
(rule `subject-fight-v1`), the same-faction cohort is chosen by the benchmark
selector with every deep candidate's faction checked against its own report,
and each deep entry (subject, cohort, and the optional cross-faction #1) is
fetched as a whole generation: report bundle, player actor, faction, pets, then
player and pet event streams into the immutable cache. Nothing here analyses
the data.

Every request goes to the one endpoint the caller chose; there is no fallback.
Running out of points or hitting the rate limit stops the run at once with a
partial result that keeps everything acquired so far and names where it
stopped; a rerun reuses completed cache streams.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from functools import cache
from typing import Any

from necropsy.analysis.context import realm_key
from necropsy.analysis.evidence import Faction
from necropsy.analysis.roles import CLASS_NAMES, ranking_policy
from necropsy.rules import load_rules
from necropsy.wcl.cache import Cache, FightKey, StreamPages, valid_report_code
from necropsy.wcl.client import (
    RATE_FIELDS,
    BudgetExceeded,
    Endpoint,
    InvalidResponse,
    NotFound,
    PermissionDenied,
    RateLimited,
    WclClient,
)
from necropsy.wcl.cohort import (
    Candidate,
    CohortKey,
    Selection,
    Verdict,
    cohort_key,
    prefetch_boss,
    select_boss,
)
from necropsy.wcl.context import CharacterContext
from necropsy.wcl.fetch import (
    Bundle,
    ReportInaccessible,
    RevisionChanged,
    fetch_bundle,
    fetch_stream,
    report_query,
    report_query_for_metric,
)
from necropsy.wcl.sites import Site

GAME = "classic_era"
ZONE = "naxxramas"

SUBJECT_QUERY = f"""
query NecropsySubject($id: Int!, $encounter: Int!, $partition: Int!) {{
  characterData {{
    character(id: $id) {{
      encounterRankings(encounterID: $encounter, partition: $partition, metric: dps,
                        includeCombatantInfo: true)
    }}
  }}
  {RATE_FIELDS}
}}
"""
"""Shape ported from the recorded exporter and exercised by authenticated live runs."""

_FACTIONS = {"Alliance": Faction.ALLIANCE, "Horde": Faction.HORDE}
_UNREACHABLE = (ReportInaccessible, PermissionDenied, NotFound)
_STOPS = (BudgetExceeded, RateLimited)


class RunStopped(Exception):
    """Points or rate limits ended the run; carries where it stopped."""


@cache
def _faction_codes() -> dict[int, Faction]:
    return {int(k): _FACTIONS[str(v)] for k, v in load_rules(GAME, "externals")["factions"].items()}


@cache
def _live() -> dict[str, Any]:
    return dict(load_rules(GAME, "benchmarks")["live_cohort"])


@cache
def boss_order() -> tuple[int, ...]:
    """Supported encounters in the zone rule data's order."""
    return tuple(int(e["id"]) for e in load_rules(GAME, f"zones/{ZONE}")["encounters"])


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def _decode(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            raise InvalidResponse("rankings are not valid JSON") from None
    return value


# -- subject fight ---------------------------------------------------------------


@dataclass(frozen=True)
class SubjectPick:
    row: dict[str, Any] | None
    report_code: str | None
    fight_id: int | None
    rule: str
    notes: tuple[str, ...]
    """Why rows were excluded, why rankings were unavailable, and ties on missing fields."""


def _subject_row(
    row: Any, class_id: int = 3, category: str | None = None
) -> tuple[str, int, float] | str:
    if not isinstance(row, dict):
        return "row is not an object"
    class_name = CLASS_NAMES[class_id]
    value = row.get("class")
    if not ((type(value) is int and value == class_id) or value == class_name):
        return f"class {value!r} is not {class_name}"
    if category is not None and row.get("spec") != category:
        return f"spec {row.get('spec')!r} is not {category}"
    report = row.get("report")
    code = report.get("code") if isinstance(report, dict) else None
    fight = _int(report.get("fightID")) if isinstance(report, dict) else None
    if not valid_report_code(code) or fight is None or fight <= 0:
        return "no valid report reference"
    amount = _finite(row.get("amount"))
    if amount is None or amount < 0:
        return "no finite non-negative amount"
    assert isinstance(code, str)
    return code, fight, amount


def pick_subject(
    rows: list[Any], notes: tuple[str, ...] = (), *, class_id: int = 3, category: str | None = None
) -> SubjectPick:
    """Highest amount; then higher rankPercent, earlier startTime (missing after present).

    On the recorded Naxxramas fixture this reproduces the export's chosen subject
    fight on 15 of 15 bosses (ordering by rankPercent first would not). A present
    but unusable tie field counts as missing and is noted.
    """
    rule = str(load_rules(GAME, "benchmarks")["subject_fight"]["rule"])
    out: list[str] = list(notes)
    valid: dict[tuple[str, int], dict[str, Any]] = {}
    conflicting: set[tuple[str, int]] = set()
    for row in rows:
        checked = _subject_row(row, class_id, category)
        if isinstance(checked, str):
            out.append(f"excluded: {checked}")
            continue
        code, fight, _ = checked
        ident = (code, fight)
        if ident in valid and valid[ident] != row:
            conflicting.add(ident)
        valid.setdefault(ident, row)
    for ident in sorted(conflicting):
        out.append(f"excluded: {ident[0]} fight {ident[1]} has conflicting ranking rows")
        del valid[ident]
    if not valid:
        return SubjectPick(None, None, None, rule, (*out, "no valid subject fight"))

    def tie(row: dict[str, Any], name: str) -> float | None:
        value = _finite(row.get(name))
        if value is None or value < 0 or (name == "rankPercent" and value > 100):
            return None
        return value

    def order(item: tuple[tuple[str, int], dict[str, Any]]) -> tuple[Any, ...]:
        (code, fight), row = item
        percent, start = tie(row, "rankPercent"), tie(row, "startTime")
        return (
            -(_finite(row.get("amount")) or 0.0),
            percent is None,
            -(percent or 0.0),
            start is None,
            start or 0.0,
            code,
            fight,
        )

    ranked = sorted(valid.items(), key=order)
    (code, fight), row = ranked[0]
    if len(ranked) > 1 and order(ranked[0])[0] == order(ranked[1])[0]:
        for name in ("rankPercent", "startTime"):
            if tie(row, name) is None:
                out.append(f"tie on amount decided with {name} missing or unusable")
    return SubjectPick(row, code, fight, rule, tuple(out))


def subject_rankings(
    client: WclClient, context: CharacterContext, key: CohortKey, endpoint: Endpoint
) -> tuple[Any, list[Any], tuple[str, ...]]:
    """(raw encounterRankings document, ranking rows, notes on why rows are unavailable)."""
    client.ensure_budget(None)
    result = client.query(
        SUBJECT_QUERY.replace("metric: dps", "metric: hps")
        if key.metric.value == "hps"
        else SUBJECT_QUERY,
        {
            "id": context.character_id.value,
            "encounter": key.encounter.value,
            "partition": key.partition.value,
        },
        endpoint=endpoint,
    )
    character = (result.data.get("characterData") or {}).get("character")
    if not isinstance(character, dict):
        raise InvalidResponse("the subject character is missing from the answer")
    raw = character.get("encounterRankings")
    if raw is None:
        return raw, [], ("WCL returned no rankings for this boss",)
    data = _decode(raw)
    rows = data.get("ranks") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return raw, [], ("the rankings document has no ranks list (invalid)",)
    return raw, rows, ()


# -- identity checks from a report bundle -------------------------------------------


def player_actor(
    report: dict[str, Any], name: str, server: str | None, class_name: str = "Hunter"
) -> tuple[int | None, str]:
    """The one player actor of the expected class with this name and realm, or None with why not."""
    actors = (report.get("masterData") or {}).get("actors")
    if not isinstance(actors, list):
        return None, "report has no actor list"
    found = [
        a
        for a in actors
        if isinstance(a, dict)
        and a.get("type") == "Player"
        and str(a.get("name") or "") == name
        and (server is None or realm_key(a.get("server")) == realm_key(server))
    ]
    if len(found) != 1:
        return None, f"{len(found)} player actors named {name!r} on that realm"
    actor = found[0]
    actor_id = _int(actor.get("id"))
    if actor_id is None or actor_id <= 0:
        return None, "the player actor has no valid id"
    if actor.get("subType") != class_name:
        return None, f"the player actor is a {actor.get('subType')!r}, not a {class_name}"
    return actor_id, "matched by name and realm"


def _details(report: dict[str, Any], actor_id: int) -> list[dict[str, Any]]:
    raw = report.get("playerDetails")
    data = raw.get("data") if isinstance(raw, dict) else None
    details = data.get("playerDetails") if isinstance(data, dict) else None
    if not isinstance(details, dict):
        return []
    return [
        e
        for role in details.values()
        if isinstance(role, list)
        for e in role
        if isinstance(e, dict) and _int(e.get("id")) == actor_id
    ]


def faction_verdict(report: dict[str, Any], actor_id: int, class_name: str = "Hunter") -> Verdict:
    """Observed faction from playerDetails combatantInfo.factionID; else unknown with why."""
    entries = _details(report, actor_id)
    if not entries:
        return Verdict("unknown", None, "the actor has no player details")
    if any(e.get("type") != class_name for e in entries):
        return Verdict("unknown", None, f"player details do not describe a {class_name}")
    codes = []
    for e in entries:
        info = e.get("combatantInfo")
        if isinstance(info, dict) and "factionID" in info:
            code = _int(info.get("factionID"))
            if code is None:
                return Verdict("unknown", None, f"factionID {info.get('factionID')!r} unusable")
            codes.append(code)
    if not codes:
        return Verdict("unknown", None, "no factionID in the player details")
    names = _faction_codes()
    unmapped = sorted({c for c in codes if c not in names})
    if unmapped:
        return Verdict("unknown", None, f"unmapped faction codes {unmapped}")
    values = {names[c] for c in codes}
    if len(values) > 1:
        return Verdict("unknown", None, "faction fields disagree")
    return Verdict("observed", values.pop(), "playerDetails combatantInfo.factionID")


def fight_pets(
    report: dict[str, Any], fight: dict[str, Any], actor_id: int
) -> tuple[list[int] | None, str]:
    """Pets the player owned in this fight, proven by the fight list and masterData.

    Returns (ids, why). None means unknown: the fight lists no pets, an owner is
    missing or malformed, the same pet has two owners, or masterData does not
    agree (absent pet actor, not a pet, another owner). An empty list is a proven
    absence: a well-formed fight list in which no pet belongs to the player.
    """
    listed = fight.get("friendlyPets")
    if not isinstance(listed, list):
        return None, "the fight lists no friendly pets"
    owners: dict[int, int] = {}
    for p in listed:
        if not isinstance(p, dict):
            return None, "a friendly pet entry is not an object"
        pid, owner = _int(p.get("id")), _int(p.get("petOwner"))
        if pid is None or pid <= 0:
            return None, "a friendly pet has no valid id"
        if owner is None or owner <= 0:
            return None, f"pet {pid} has no valid owner"
        if owners.get(pid, owner) != owner:
            return None, f"pet {pid} is listed with two owners"
        owners[pid] = owner
    actors = (report.get("masterData") or {}).get("actors")
    if not isinstance(actors, list):
        return None, "report has no actor list"
    by_id: dict[int, dict[str, Any]] = {}
    for a in actors:
        aid = _int(a.get("id")) if isinstance(a, dict) else None
        if aid is None:
            continue
        if aid in by_id and by_id[aid] != a:
            return None, f"masterData lists actor {aid} twice with different records"
        by_id[aid] = a
    fight_only = []
    for pid, owner in owners.items():
        actor = by_id.get(pid)
        if actor is None or actor.get("type") != "Pet":
            return None, f"pet {pid} is not a pet actor in masterData"
        if "petOwner" not in actor or actor.get("petOwner") is None:
            fight_only.append(pid)
            continue
        master_owner = _int(actor.get("petOwner"))
        if master_owner is None or master_owner <= 0:
            return None, f"masterData gives pet {pid} an unusable owner"
        if master_owner != owner:
            return None, f"pet {pid}: fight says owner {owner}, masterData says {master_owner}"
    mine = sorted(pid for pid, owner in owners.items() if owner == actor_id)
    if fight_only:
        return mine, f"masterData gives no owner for pets {sorted(fight_only)}; fight list only"
    return mine, "fight pet list and masterData agree"


# -- entries ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StreamRecord:
    role: str
    actor_id: int
    direction: str
    identity: dict[str, Any]
    pages: int
    events: int
    reused: bool
    meta: dict[str, Any]


@dataclass
class Entry:
    kind: str
    """`subject`, `cohort` or `cross_faction`."""
    name: str
    server: str | None
    report_code: str
    fight_id: int
    candidate: Candidate | None = None
    status: str = "pending"
    """`complete`, `rejected` (faction not the one required), `unknown` (identity or
    faction could not be established), `inaccessible`, `failed`, or `stopped` (the run
    hit its points or rate limit during this entry)."""
    reason: str | None = None
    verdict: Verdict | None = None
    bundle_key: FightKey | None = None
    bundle_sha256: str | None = None
    """Full digest of the report generation used to verify this entry."""
    actor_id: int | None = None
    pets: list[int] | None = None
    """None means pet ownership could not be proven (unknown), never "no pets"."""
    pets_reason: str | None = None
    streams: list[StreamRecord] = field(default_factory=list)
    generations: int = 0


def _record(role: str, actor_id: int, direction: str, stream: StreamPages) -> StreamRecord:
    return StreamRecord(
        role,
        actor_id,
        direction,
        stream.identity,
        len(stream.pages),
        sum(len(p["data"]) for p in stream.pages),
        stream.reused,
        stream.meta,
    )


class Run:
    """One acquisition run: shared client, cache, endpoint, bundle memo and stage."""

    def __init__(
        self,
        client: WclClient,
        store: Cache,
        site: Site,
        endpoint: Endpoint = "client",
        *,
        class_id: int = 3,
        category: str | None = None,
        metric: str | None = None,
    ) -> None:
        self.client, self.store, self.site, self.endpoint = client, store, site, endpoint
        self.policy = ranking_policy(class_id, category, metric)
        self.report_points_bound = 6.0
        """Conservative floor; observed account-wide report costs may only increase it."""
        self._bundles: dict[tuple[str, int], Bundle] = {}
        self.stage = "starting"

    def bundle(self, code: str, fight: int, encounter: int, *, fresh: bool = False) -> Bundle:
        if fresh or (code, fight) not in self._bundles:
            before = self.client.last_rate
            self._bundles[(code, fight)] = fetch_bundle(
                self.client,
                self.store,
                self.site,
                code,
                fight,
                encounter,
                endpoint=self.endpoint,
                metric=self.policy.metric,
            )
            after = self.client.last_rate
            if (
                before is not None
                and after is not None
                and after.points_spent >= before.points_spent
            ):
                self.report_points_bound = max(
                    self.report_points_bound, after.points_spent - before.points_spent
                )
        found = self._bundles[(code, fight)]
        if _int(found.fight.get("encounterID")) != encounter:
            raise InvalidResponse(
                f"{code} fight {fight} is encounter {found.fight.get('encounterID')!r}, "
                f"not {encounter}"
            )
        return found

    def verify(self, encounter: int) -> Callable[[Candidate], Verdict]:
        """Selector callback: the row's faction from its own report bundle."""

        def check(c: Candidate) -> Verdict:
            if c.report_code is None or c.fight_id is None:
                return Verdict("inaccessible", None, "no report reference")
            self.stage = f"faction check of {c.name} ({c.report_code} fight {c.fight_id})"
            try:
                bundle = self.bundle(c.report_code, c.fight_id, encounter)
            except _UNREACHABLE as error:
                return Verdict("inaccessible", None, f"{type(error).__name__}: {error}")
            except InvalidResponse as error:
                return Verdict("unknown", None, f"invalid report data: {error}")
            actor, why = player_actor(bundle.report, c.name, c.server, self.policy.class_name)
            if actor is None:
                return Verdict("unknown", None, why)
            return faction_verdict(bundle.report, actor, self.policy.class_name)

        return check

    def entry(self, entry: Entry, encounter: int, want: Faction) -> Entry:
        """Fetch one whole generation; a revision change restarts it once.

        Points or rate limits mark the entry `stopped` (keeping what it has) and
        raise RunStopped so the caller stops making requests.
        """
        for generation in (1, 2):
            entry.generations = generation
            entry.streams, entry.pets, entry.pets_reason = [], None, None
            entry.actor_id, entry.bundle_key = None, None
            entry.bundle_sha256 = None
            try:
                self._generation(entry, encounter, want, fresh=generation > 1)
                return entry
            except RevisionChanged as error:
                if generation == 2:
                    entry.status, entry.reason = "failed", f"revision changed twice: {error}"
                    entry.streams = []
                    return entry
            except _UNREACHABLE as error:
                entry.status, entry.reason = "inaccessible", f"{type(error).__name__}: {error}"
                entry.streams = []
                return entry
            except InvalidResponse as error:
                entry.status, entry.reason = "failed", f"invalid response: {error}"
                entry.streams = []
                return entry
            except _STOPS as error:
                entry.status = "stopped"
                entry.reason = f"{type(error).__name__} during {self.stage}: {error}"
                raise RunStopped(entry.reason) from error
        return entry  # pragma: no cover

    def _generation(self, entry: Entry, encounter: int, want: Faction, fresh: bool) -> None:
        where = f"{entry.kind} {entry.name} ({entry.report_code} fight {entry.fight_id})"
        self.stage = f"report bundle for {where}"
        bundle = self.bundle(entry.report_code, entry.fight_id, encounter, fresh=fresh)
        entry.bundle_key = bundle.key
        entry.bundle_sha256 = bundle.sha256
        actor, why = player_actor(bundle.report, entry.name, entry.server, self.policy.class_name)
        if actor is None:
            entry.status, entry.reason = "unknown", why
            return
        entry.actor_id = actor
        entry.verdict = faction_verdict(bundle.report, actor, self.policy.class_name)
        if entry.verdict.status != "observed" or entry.verdict.faction is None:
            entry.status, entry.reason = "unknown", entry.verdict.reason
            return
        if entry.verdict.faction is not want:
            entry.status = "rejected"
            entry.reason = f"observed {entry.verdict.faction.value}, needed {want.value}"
            return
        entry.pets, entry.pets_reason = fight_pets(bundle.report, bundle.fight, actor)
        targets = [("player", actor)] + [("pet", pid) for pid in entry.pets or ()]
        for role, actor_id in targets:
            for direction in ("source", "target"):
                self.stage = f"{role} {actor_id} {direction} events for {where}"
                stream = fetch_stream(self.client, self.store, bundle, role, actor_id, direction)
                entry.streams.append(_record(role, actor_id, direction, stream))
        entry.status = "complete"
        entry.reason = None if entry.pets is not None else f"pets unknown: {entry.pets_reason}"


# -- per boss -----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Dropped:
    candidate: Candidate
    reason: str


@dataclass
class BossAcquisition:
    encounter_id: int
    key: CohortKey | None = None
    subject_raw: Any = None
    subject_pick: SubjectPick | None = None
    subject: Entry | None = None
    selection: Selection | None = None
    """The selector's provisional result; final outcomes are in `cohort`, `dropped`
    and `metadata`."""
    cohort: list[Entry] = field(default_factory=list)
    """Deep entries attempted, in order; usable ones have status `complete`."""
    dropped: list[Dropped] = field(default_factory=list)
    """Metadata rows removed from the final cohort, with why (failed check or entry)."""
    metadata: list[Candidate] = field(default_factory=list)
    """Final same-faction metadata rows (known contradictions and unreachable removed)."""
    cross_faction_requested: bool = False
    cross_faction_applicable: bool | None = None
    """False when the overall #1 is own-faction or already a complete entry (nothing to
    fetch); None while its faction is unresolved; True for an observed other faction."""
    cross_faction: Entry | None = None
    cross_faction_reason: str | None = None
    coverage: dict[str, Any] = field(default_factory=dict)


def _coverage(boss: BossAcquisition, stopped: str | None) -> dict[str, Any]:
    cfg = _live()
    target, minimum, meta_target = (
        int(cfg["deep"]),
        int(cfg["min_same_faction"]),
        int(cfg["metadata"]),
    )
    usable = [e for e in boss.cohort if e.status == "complete"]
    levels = [c.faction.level for c in boss.metadata]
    reasons = []
    if boss.subject is None or boss.subject.status != "complete":
        why = "no subject fight" if boss.subject is None else boss.subject.reason
        if boss.subject is None and boss.subject_pick is not None:
            why = "; ".join(boss.subject_pick.notes) or why
        reasons.append(f"subject fight not acquired: {why}")
    if len(usable) < target:
        reasons.append(f"{len(usable)} of {target} same-faction deep entries")
    if len(usable) < minimum:
        reasons.append(f"below the minimum of {minimum} same-faction entries")
    if len(boss.metadata) < meta_target:
        reasons.append(f"{len(boss.metadata)} of {meta_target} same-faction metadata rows")
    for e in [boss.subject, *usable]:
        if e is not None and e.status == "complete" and e.pets is None:
            reasons.append(f"pets unknown for {e.name}: {e.pets_reason}")
    if (
        boss.cross_faction_requested
        and boss.cross_faction_applicable is not False
        and (boss.cross_faction is None or boss.cross_faction.status != "complete")
    ):
        why = boss.cross_faction_reason
        if boss.cross_faction is not None:
            why = f"{boss.cross_faction.status}: {boss.cross_faction.reason}"
        reasons.append(f"cross-faction ceiling not acquired: {why}")
    if boss.selection is not None and boss.selection.stop not in ("targets met", "no more pages"):
        reasons.append(f"selection stopped: {boss.selection.stop}")
    if stopped:
        reasons.append(f"run stopped: {stopped}")
    return {
        "complete": not reasons,
        "usable_deep": len(usable),
        "target": target,
        "below_minimum": len(usable) < minimum,
        "metadata": len(boss.metadata),
        "metadata_target": meta_target,
        "metadata_observed": levels.count("observed"),
        "metadata_inferred": levels.count("inferred"),
        "reasons": reasons,
    }


@dataclass(frozen=True)
class ReportSet:
    """One combined report answer covering every complete entry's fight in a report."""

    key: FightKey
    """Locates the revision (its fight is the first of `fight_ids`)."""
    fight_ids: tuple[int, ...]
    endpoint: Endpoint
    report: dict[str, Any]
    sha256: str
    """Full digest of this exact cached combined-report record."""


class MixedRevision(Exception):
    """Entries of one report come from different revisions; nothing can be published."""


@dataclass
class Acquisition:
    endpoint: Endpoint
    cross_faction: bool
    context: CharacterContext | None = None
    """The resolved character the run was for (identity comes from here, not names)."""
    requested: tuple[int, ...] = ()
    """Every encounter the run was asked for, in order; all stay in the coverage."""
    bosses: list[BossAcquisition] = field(default_factory=list)
    stopped: str | None = None
    """Collection stopped; Druid personal data may already cover later comparison gaps."""
    reports: dict[str, ReportSet] = field(default_factory=dict)
    """Filled by `finalize_reports`: the combined report per code, for the snapshot."""
    comparison_order: tuple[int, ...] = ()
    """Planned comparison fetch order; report and snapshot remain in requested order."""
    metadata_order: tuple[int, ...] = ()
    """Completed first-page ranking prefetches, in requested encounter order."""

    def complete_entries(self) -> list[tuple[BossAcquisition, Entry]]:
        out = []
        for boss in self.bosses:
            for e in [boss.subject, *boss.cohort, boss.cross_faction]:
                if e is not None and e.status == "complete":
                    out.append((boss, e))
        return out


def _quota_stop(selection: Selection) -> bool:
    return selection.stop.startswith(tuple(f"{e.__name__}:" for e in _STOPS))


def _acquire_subject(
    run: Run, context: CharacterContext, boss: BossAcquisition, cross_faction: bool
) -> None:
    """Fill `boss` step by step, so a RunStopped leaves everything acquired in place."""
    encounter = boss.encounter_id
    key = cohort_key(run.site, context, encounter)
    boss.key = key
    boss.cross_faction_requested = cross_faction
    want: Faction = context.faction.value
    run.stage = "subject rankings"
    try:
        raw, rows, notes = subject_rankings(run.client, context, key, run.endpoint)
    except _STOPS as error:
        raise RunStopped(f"{type(error).__name__} during {run.stage}: {error}") from error
    boss.subject_raw = raw
    boss.subject_pick = pick_subject(
        rows, notes, class_id=context.class_id.value, category=context.ranking_category
    )
    pick = boss.subject_pick
    if pick.report_code is not None and pick.fight_id is not None:
        server = context.server.value
        boss.subject = Entry(
            "subject",
            str(context.name.value),
            None if server is None else str(server),
            pick.report_code,
            pick.fight_id,
        )
        run.entry(boss.subject, encounter, want)


def _acquire_comparisons(
    run: Run,
    context: CharacterContext,
    boss: BossAcquisition,
    cross_faction: bool,
) -> None:
    encounter = boss.encounter_id
    want: Faction = context.faction.value
    run.stage = "leaderboard selection"
    boss.selection = select_boss(
        run.client,
        run.site,
        context,
        encounter,
        run.verify(encounter),
        endpoint=run.endpoint,
        deep_needs_observed=True,
        **({"prefetched": boss.selection} if boss.selection is not None else {}),
    )
    selection = boss.selection
    boss.metadata = list(selection.metadata)
    if _quota_stop(selection):
        raise RunStopped(f"{selection.stop} during {run.stage}")
    target = int(_live()["deep"])
    verify = run.verify(encounter)
    for c in selection.metadata:
        if sum(1 for e in boss.cohort if e.status == "complete") >= target:
            break
        if c.faction.level != "observed":
            try:
                verdict = verify(c)
            except _STOPS as error:
                raise RunStopped(f"{type(error).__name__} during {run.stage}: {error}") from error
            if verdict.status != "observed" or verdict.faction is not want:
                why = verdict.reason or verdict.status
                if verdict.status == "observed" and verdict.faction is not None:
                    why = f"observed {verdict.faction.value}"
                boss.dropped.append(Dropped(c, f"replacement check: {why}"))
                boss.metadata.remove(c)
                continue
        assert c.report_code is not None and c.fight_id is not None
        entry = Entry("cohort", c.name, c.server, c.report_code, c.fight_id, candidate=c)
        boss.cohort.append(entry)
        run.entry(entry, encounter, want)
        if entry.status != "complete":
            boss.dropped.append(Dropped(c, f"entry {entry.status}: {entry.reason}"))
            boss.metadata.remove(c)
    if not cross_faction:
        return
    first = selection.overall_first
    if first is None or first.report_code is None or first.fight_id is None:
        boss.cross_faction_reason = "the overall #1 has no usable report reference"
        return
    ref = (first.report_code, first.fight_id)
    attempts = [e for e in [boss.subject, *boss.cohort] if e and (e.report_code, e.fight_id) == ref]
    if any(e.status == "complete" for e in attempts):
        boss.cross_faction_applicable = False
        boss.cross_faction_reason = "the overall #1 is already acquired as a same-faction entry"
        return
    current = next((e.verdict for e in reversed(attempts) if e.verdict is not None), None)
    try:
        verdict = current or selection.verdicts.get(1) or verify(first)
    except _STOPS as error:
        raise RunStopped(f"{type(error).__name__} during {run.stage}: {error}") from error
    if verdict.status != "observed" or verdict.faction is None:
        boss.cross_faction_reason = f"faction not observed: {verdict.reason or verdict.status}"
    elif verdict.faction is want:
        boss.cross_faction_applicable = False
        boss.cross_faction_reason = "the overall #1 is the subject's own faction"
    else:
        boss.cross_faction_applicable = True
        boss.cross_faction = Entry(
            "cross_faction", first.name, first.server, first.report_code, first.fight_id, first
        )
        run.entry(boss.cross_faction, encounter, verdict.faction)


def acquire_boss(
    run: Run,
    context: CharacterContext,
    boss: BossAcquisition,
    cross_faction: bool,
) -> None:
    """Preserve the original per-boss flow for Hunter and single-boss acquisitions."""
    _acquire_subject(run, context, boss, cross_faction)
    _acquire_comparisons(run, context, boss, cross_faction)


def _acquire_spec_view(run: Run, context: CharacterContext, out: Acquisition) -> Acquisition:
    """Personal spec coverage precedes examples; absent personal fights get examples first."""
    for encounter in out.requested:
        boss = BossAcquisition(encounter)
        out.bosses.append(boss)
        try:
            _acquire_subject(run, context, boss, out.cross_faction)
        except RunStopped as stop:
            out.stopped = f"personal data, encounter {encounter}: {stop}"
            break
    if out.stopped is None:
        order = {encounter: i for i, encounter in enumerate(boss_order())}
        comparisons = sorted(
            out.bosses,
            key=lambda b: (
                b.subject is not None and b.subject.status == "complete",
                order[b.encounter_id],
            ),
        )
        out.comparison_order = tuple(b.encounter_id for b in comparisons)
        original_policy = run.client.policy
        try:

            def reserve_policy(extra_fights: int) -> None:
                rate = run.client.last_rate
                if rate is None:
                    raise RunStopped("no budget reading available for comparisons")
                fights = {(e.report_code, e.fight_id) for _, e in out.complete_entries()}
                prospective = len(fights) + extra_fights
                reserve = 2 * run.report_points_bound * prospective
                # Lowering the comparison budget cannot spend the finalization reserve.
                # Event pagination still pays against this guard on every request.
                run.client.policy = replace(
                    original_policy,
                    wait_for_reset=False,
                    budget_share=max(
                        0.01, original_policy.budget_share - reserve / rate.limit_per_hour
                    ),
                )

            for boss in out.bosses:
                try:
                    reserve_policy(0)
                    _acquire_rankings(run, context, boss)
                    out.metadata_order += (boss.encounter_id,)
                except (*_STOPS, RunStopped) as stop:
                    out.stopped = (
                        f"ranking metadata, encounter {boss.encounter_id}: {stop}; "
                        "budget reserve kept for fresh report finalization"
                    )
                    break
            for boss in comparisons if out.stopped is None else ():
                try:
                    reserve_policy(int(_live()["deep"]) + int(out.cross_faction))
                    _acquire_comparisons(run, context, boss, out.cross_faction)
                except RunStopped as stop:
                    out.stopped = (
                        f"comparisons, encounter {boss.encounter_id}: {stop}; "
                        "budget reserve kept for fresh report finalization"
                    )
                    break
        finally:
            run.client.policy = original_policy
    for boss in out.bosses:
        boss.coverage = _coverage(boss, out.stopped)
    return out


def _acquire_rankings(run: Run, context: CharacterContext, boss: BossAcquisition) -> None:
    """Keep ranking references across the raid before spending on deep event samples."""
    run.stage = f"ranking metadata, encounter {boss.encounter_id}"
    boss.selection = prefetch_boss(
        run.client, run.site, context, boss.encounter_id, endpoint=run.endpoint
    )
    boss.metadata = list(boss.selection.metadata)


def acquire(
    client: WclClient,
    store: Cache,
    site: Site,
    context: CharacterContext,
    *,
    endpoint: Endpoint = "client",
    cross_faction: bool = False,
    encounters: tuple[int, ...] | None = None,
) -> Acquisition:
    """Acquire every supported boss (or `encounters`), stopping cleanly on point limits."""
    run = Run(
        client,
        store,
        site,
        endpoint,
        class_id=context.class_id.value,
        category=context.ranking_category,
        metric=context.ranking_metric,
    )
    requested = tuple(encounters or boss_order())
    out = Acquisition(endpoint, cross_faction, context, requested)
    if (context.class_id.value == 2 or context.ranking_category is not None) and len(requested) > 1:
        return _acquire_spec_view(run, context, out)
    for encounter in requested:
        boss = BossAcquisition(encounter)
        out.bosses.append(boss)
        try:
            acquire_boss(run, context, boss, cross_faction)
        except RunStopped as stop:
            out.stopped = f"encounter {encounter}: {stop}"
        boss.coverage = _coverage(boss, out.stopped)
        if out.stopped:
            break
    return out


def finalize_reports(run: Run, acquisition: Acquisition) -> dict[str, ReportSet]:
    """Fetch one combined report per code over the exact fight set of its complete entries.

    Network acquisition finalization (never part of the offline writer). Every
    entry of a code must share one revision and the combined answer must have it
    too, contain every selected fight with its encounter, and list each entry's
    player and pet actors with the same identity; otherwise `MixedRevision` or
    `InvalidResponse`, and nothing is recorded. Points or rate limits raise
    `RunStopped`.
    """
    by_code: dict[str, list[tuple[BossAcquisition, Entry]]] = {}
    for boss, entry in acquisition.complete_entries():
        by_code.setdefault(entry.report_code, []).append((boss, entry))
    sets: dict[str, ReportSet] = {}
    for code in sorted(by_code):
        items = by_code[code]
        keys = {e.bundle_key for _, e in items if e.bundle_key is not None}
        revisions = {k.revision for k in keys}
        if len(revisions) != 1 or len(keys) != len({e.fight_id for _, e in items}):
            raise MixedRevision(f"report {code} entries span revisions {sorted(revisions)}")
        revision = revisions.pop()
        encounters: dict[int, int] = {}
        for boss, e in items:
            if encounters.setdefault(e.fight_id, boss.encounter_id) != boss.encounter_id:
                raise InvalidResponse(f"{code} fight {e.fight_id} is claimed by two bosses")
        fight_ids = tuple(sorted(encounters))
        locate = FightKey(run.site, code, revision, fight_ids[0])
        # Rankings/archive access metadata can change without a report revision.
        # Finalize afresh, then bind this run to the exact content-addressed answer.
        run.stage = f"combined report {code} fights {list(fight_ids)}"
        try:
            run.client.ensure_budget(None)
            result = report_query(
                run.client,
                report_query_for_metric(run.policy.metric),
                {"code": code, "fightIDs": list(fight_ids)},
                run.endpoint,
            )
        except _STOPS as error:
            raise RunStopped(f"{type(error).__name__} during {run.stage}: {error}") from error
        report = (result.data.get("reportData") or {}).get("report")
        if not isinstance(report, dict) or report.get("code") != code:
            raise ReportInaccessible(f"WCL returned no usable combined report {code}")
        if _int(report.get("revision")) != revision:
            raise MixedRevision(
                f"combined report {code} is revision {report.get('revision')!r}, "
                f"entries are {revision}"
            )
        _check_report_set(report, code, encounters, [e for _, e in items], run.policy.class_name)
        digest = run.store.put_report_set(locate, fight_ids, run.endpoint, report)
        sets[code] = ReportSet(locate, fight_ids, run.endpoint, report, digest)
    acquisition.reports = sets
    return sets


def _check_report_set(
    report: dict[str, Any],
    code: str,
    encounters: dict[int, int],
    entries: list[Entry],
    class_name: str = "Hunter",
) -> None:
    fights = report.get("fights")
    found: dict[int, dict[str, Any]] = {}
    for f in fights or ():
        fid = _int(f.get("id")) if isinstance(f, dict) else None
        if fid is not None:
            found[fid] = f
    if set(found) != set(encounters):
        raise InvalidResponse(
            f"combined report {code} fights {sorted(found)} != {sorted(encounters)}"
        )
    for fid, encounter in encounters.items():
        if _int(found[fid].get("encounterID")) != encounter:
            raise InvalidResponse(f"combined report {code} fight {fid} is another encounter")
    for e in entries:
        actor, why = player_actor(report, e.name, e.server, class_name)
        if actor != e.actor_id:
            raise InvalidResponse(
                f"combined report {code}: {e.name} is not actor {e.actor_id} ({why})"
            )
        if e.pets is not None and e.actor_id is not None:
            pets, _ = fight_pets(report, found[e.fight_id], e.actor_id)
            if pets != e.pets:
                raise InvalidResponse(f"combined report {code}: pets of {e.name} differ")


__all__ = [
    "SUBJECT_QUERY",
    "Acquisition",
    "BossAcquisition",
    "Dropped",
    "Entry",
    "MixedRevision",
    "ReportSet",
    "Run",
    "RunStopped",
    "StreamRecord",
    "SubjectPick",
    "acquire",
    "acquire_boss",
    "boss_order",
    "faction_verdict",
    "fight_pets",
    "finalize_reports",
    "pick_subject",
    "player_actor",
    "subject_rankings",
]
