"""Choose the same-faction comparison cohort for one boss from WCL ranking pages.

The analyze CLI uses this selector through acquisition orchestration.

The cohort key keeps every comparison dimension with how it is applied:
`enforced` (rows that do not match are excluded), `recorded` (kept per row, not
filtered) or `unknown`. Ranking rows carry no character faction, only the guild's
faction number, so a row's faction is INFERRED from the guild rule at best; a
`verify` callback can supply an observed faction, which overrides the guild rule.
A row whose faction stays unknown is never counted as same-faction, and a short
cohort is reported as partial with its reason, never filled from other rows.

The query shape was ported from the recorded exporter and exercised by
authenticated live runs. End-to-end acceptance is recorded separately.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from functools import cache
from typing import Any

from necropsy.analysis.context import realm_key
from necropsy.analysis.encounters import zone_encounters
from necropsy.analysis.evidence import Faction
from necropsy.analysis.roles import CLASS_NAMES, ranking_policy
from necropsy.rules import load_rules
from necropsy.wcl.client import (
    RATE_FIELDS,
    BudgetExceeded,
    Endpoint,
    InvalidResponse,
    PageBudgetExhausted,
    PermissionDenied,
    RateLimit,
    RateLimited,
    WclClient,
    pages,
)
from necropsy.wcl.context import SUPPORTED_ZONE_ID, CharacterContext
from necropsy.wcl.sites import SITES, Site, UnsupportedSite, require_supported

HUNTER = "Hunter"
GAME = "classic_era"
ZONE = "naxxramas"

LEADERBOARD_QUERY = f"""
query NecropsyLeaderboard($encounter: Int!, $partition: Int!, $page: Int!) {{
  worldData {{
    encounter(id: $encounter) {{
      id
      characterRankings(
        page: $page
        partition: $partition
        metric: dps
        includeCombatantInfo: true
        className: "{HUNTER}"
      )
    }}
  }}
  {RATE_FIELDS}
}}
"""
"""Shape ported from the recorded exporter and exercised by authenticated live runs."""


def leaderboard_query(key: CohortKey) -> str:
    if key.class_name.value == "Hunter":
        return (
            LEADERBOARD_QUERY.replace(
                'className: "Hunter"', 'className: "Hunter"\n        specName: "Marksmanship"'
            )
            if key.spec.status == "enforced" and key.spec.value == "Marksmanship"
            else LEADERBOARD_QUERY
        )
    class_id = next(cid for cid, name in CLASS_NAMES.items() if name == key.class_name.value)
    policy = ranking_policy(class_id, key.spec.value, key.metric.value)
    return LEADERBOARD_QUERY.replace("metric: dps", f"metric: {policy.metric}").replace(
        'className: "Hunter"',
        f'className: "{policy.class_name}"\n        specName: "{policy.category}"',
    )


_FACTIONS = {"Alliance": Faction.ALLIANCE, "Horde": Faction.HORDE}


class CohortRefused(Exception):
    """The context cannot support a same-faction cohort; nothing was queried."""


@cache
def _cfg() -> dict[str, Any]:
    return dict(load_rules(GAME, "benchmarks")["live_cohort"])


@dataclass(frozen=True, slots=True)
class Dimension:
    value: Any
    status: str
    """`enforced`, `recorded` or `unknown`."""
    note: str | None = None


@dataclass(frozen=True)
class CohortKey:
    site: Dimension
    game: Dimension
    zone: Dimension
    partition: Dimension
    encounter: Dimension
    difficulty: Dimension
    size: Dimension
    class_name: Dimension
    spec: Dimension
    role: Dimension
    faction: Dimension

    @property
    def metric(self) -> Dimension:
        metric = "hps" if self.role.value in ("restoration", "healer") else "dps"
        return Dimension(metric, "enforced", "ranking query metric")


def _ready(context: CharacterContext) -> None:
    if context.zone_id != SUPPORTED_ZONE_ID:
        raise CohortRefused(f"zone {context.zone_id} is not supported")
    if context.partition is None:
        raise CohortRefused(context.ambiguity or "no partition chosen")
    if context.faction.level != "observed" or not isinstance(context.faction.value, Faction):
        raise CohortRefused("the character's faction is unknown; same-faction selection needs it")
    if context.class_id.level != "observed":
        raise CohortRefused("the character class is not observed")
    try:
        ranking_policy(context.class_id.value, context.ranking_category, context.ranking_metric)
    except ValueError as error:
        raise CohortRefused(str(error)) from None


def _supported_encounter(encounter_id: Any) -> int:
    if (
        not isinstance(encounter_id, int)
        or isinstance(encounter_id, bool)
        or encounter_id not in zone_encounters(GAME, ZONE)
    ):
        raise CohortRefused(f"encounter {encounter_id!r} is not a supported boss of this zone")
    return encounter_id


def cohort_key(site: Site, context: CharacterContext, encounter_id: int) -> CohortKey:
    """The key for one boss; refuses a context that cannot give a same-faction cohort."""
    require_supported(site)
    _ready(context)
    _supported_encounter(encounter_id)
    assert context.partition is not None
    faction: Faction = context.faction.value
    policy = ranking_policy(
        context.class_id.value, context.ranking_category, context.ranking_metric
    )
    return CohortKey(
        site=Dimension(site.host, "enforced"),
        game=Dimension(GAME, "enforced", "site family vanilla; ranking rows carry no game build"),
        zone=Dimension(context.zone_id, "enforced"),
        partition=Dimension(context.partition.id, "enforced"),
        encounter=Dimension(encounter_id, "enforced"),
        difficulty=Dimension(0, "enforced", "hardModeLevel must be 0"),
        size=Dimension(
            None,
            "recorded",
            "row size is attendance, not the raid format; kept per row, never filtered",
        ),
        class_name=Dimension(policy.class_name, "enforced", "query className and each row's class"),
        spec=Dimension(
            policy.category or "all Hunter specs",
            "enforced" if policy.category else "recorded",
            "query specName and each row's spec"
            if policy.category
            else "no spec filter is applied; each row's spec is kept",
        ),
        role=Dimension(policy.role, "enforced", f"metric {policy.metric}"),
        faction=Dimension(faction.value, "enforced", "subject's observed faction"),
    )


@dataclass(frozen=True, slots=True)
class RowFaction:
    value: str | None
    level: str
    """`observed`, `inferred` or `unknown`."""
    source: str
    rule: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class Candidate:
    position: int
    """1-based rank among every raw row read, skipped rows included."""
    page: int
    name: str
    server: str | None
    region: str | None
    report_code: str | None
    fight_id: int | None
    amount: float | None
    spec: str | None
    size: int | None
    faction: RowFaction
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class Verdict:
    """The outcome of an attempted faction check of one ranking row."""

    status: str
    """`observed`, `unknown` (attempted, no usable faction) or `inaccessible`."""
    faction: Faction | None = None
    reason: str | None = None


Verify = Callable[[Candidate], "Verdict | Faction | None"]
"""Check a row: a Verdict, a bare observed Faction (legacy form), or None when no
check was attempted (the row keeps its guild inference)."""


def _verdict(result: Verdict | Faction | None) -> Verdict | None:
    if result is None or isinstance(result, Verdict):
        return result
    return Verdict("observed", result)


@dataclass(frozen=True, slots=True)
class PageRead:
    page: int
    rows: int


@dataclass
class Selection:
    key: CohortKey
    deep: list[Candidate] = field(default_factory=list)
    """Same-faction rows selected for deep acquisition (accessibility unproven)."""
    metadata: list[Candidate] = field(default_factory=list)
    """Every selected same-faction row, the deep ones included."""
    overall_first: Candidate | None = None
    """Raw position 1 as context; selected through the normal path only if it qualifies."""
    other_faction: int = 0
    unresolved: list[Candidate] = field(default_factory=list)
    inaccessible: list[Candidate] = field(default_factory=list)
    """Rows with no report reference to acquire."""
    key_mismatch: list[Candidate] = field(default_factory=list)
    duplicates: int = 0
    displaced: list[Candidate] = field(default_factory=list)
    """Metadata rows given up so an observed row could take a deep slot."""
    verdicts: dict[int, Verdict] = field(default_factory=dict)
    """Attempted checks by raw position (observed, unknown or inaccessible)."""
    raw_pages: list[dict[str, Any]] = field(default_factory=list)
    """Every ranking page document as returned, for the snapshot."""
    contradicted: list[Candidate] = field(default_factory=list)
    """Rows whose observed faction contradicted the guild rule (reclassified)."""
    subject_rows: int = 0
    pages: list[PageRead] = field(default_factory=list)
    complete: bool = False
    stop: str = ""
    """Why paging stopped: `targets met`, `no more pages`, `page budget` or a typed error."""
    rate: RateLimit | None = None
    rule_set: str = ""
    endpoint: Endpoint | None = None

    @property
    def partial_reasons(self) -> tuple[str, ...]:
        cfg = _cfg()
        out = []
        if len(self.deep) < int(cfg["deep"]):
            out.append(f"{len(self.deep)} of {cfg['deep']} same-faction deep entries")
        if len(self.deep) < int(cfg["min_same_faction"]):
            out.append(f"below the minimum of {cfg['min_same_faction']} same-faction entries")
        if len(self.metadata) < int(cfg["metadata"]):
            out.append(f"{len(self.metadata)} of {cfg['metadata']} same-faction metadata rows")
        if self.stop not in ("targets met", "no more pages"):
            out.append(f"stopped early: {self.stop}")
        return tuple(out)


def guild_faction(row: dict[str, Any]) -> RowFaction:
    rule = _cfg()["guild_faction"]
    guild = row.get("guild")
    raw = guild.get("faction") if isinstance(guild, dict) else None
    if not isinstance(raw, int) or isinstance(raw, bool):
        why = "no guild" if not isinstance(guild, dict) else f"guild faction {raw!r} unusable"
        return RowFaction(None, "unknown", "wcl-ranking-guild-faction", None, why)
    name = rule["map"].get(raw)
    if name is None:
        return RowFaction(
            None, "unknown", "wcl-ranking-guild-faction", str(rule["rule"]), f"code {raw} unmapped"
        )
    return RowFaction(
        str(name),
        "inferred",
        "wcl-ranking-guild-faction",
        str(rule["rule"]),
        "the guild's faction, not the character's own record",
    )


def _norm(text: Any) -> str:
    return str(text or "").strip().casefold()


def _decode(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            raise InvalidResponse("characterRankings is not valid JSON") from None
    return value


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def fetch_page(
    client: WclClient,
    key: CohortKey,
    *,
    endpoint: Endpoint = "client",
    raw_pages: list[dict[str, Any]] | None = None,
) -> Callable[[int], tuple[list[Any], Any, Any]]:
    """A page fetcher for `client.pages`, checking each page belongs to the key.

    Every page goes to the one `endpoint` given; raw page documents are appended to
    `raw_pages` when a list is passed.
    """

    def fetch(page: int) -> tuple[list[Any], Any, Any]:
        client.ensure_budget(None)
        result = client.query(
            leaderboard_query(key),
            {"encounter": key.encounter.value, "partition": key.partition.value, "page": page},
            endpoint=endpoint,
        )
        encounter = (result.data.get("worldData") or {}).get("encounter")
        if not isinstance(encounter, dict) or encounter.get("id") != key.encounter.value:
            raise InvalidResponse(f"page {page} is not for encounter {key.encounter.value}")
        if raw_pages is not None:
            raw_pages.append(
                {
                    "page": page,
                    "characterRankings": encounter.get("characterRankings"),
                    "captured_at": result.captured_at,
                }
            )
        return page_items(encounter.get("characterRankings"), page)

    return fetch


def page_items(raw: Any, page: int) -> tuple[list[Any], Any, Any]:
    """(rows, hasMorePages, identity) of one characterRankings value."""
    data = _decode(raw)
    if not isinstance(data, dict) or not isinstance(data.get("rankings"), list):
        raise InvalidResponse(f"page {page} has no rankings list")
    rows = data["rankings"]
    canonical = json.dumps(rows, sort_keys=True, default=str).encode("utf-8")
    identity = hashlib.sha256(canonical).hexdigest()
    return [(page, len(rows), r) for r in rows], data.get("hasMorePages"), identity


def _candidate(position: int, page: int, row: Any) -> Candidate:
    if not isinstance(row, dict):
        raise InvalidResponse(f"ranking row {position} is not an object")
    raw_report, raw_server = row.get("report"), row.get("server")
    report: dict[str, Any] = raw_report if isinstance(raw_report, dict) else {}
    server: dict[str, Any] = raw_server if isinstance(raw_server, dict) else {}
    amount = row.get("amount")
    return Candidate(
        position,
        page,
        str(row.get("name") or ""),
        server.get("name"),
        server.get("region"),
        code if isinstance(code := report.get("code"), str) and code.strip() else None,
        fight if (fight := _int(report.get("fightID"))) is not None and fight > 0 else None,
        float(amount)
        if isinstance(amount, (int, float)) and not isinstance(amount, bool)
        else None,
        row.get("spec"),
        _int(row.get("size")),
        guild_faction(row),
        row,
    )


def _is_subject(c: Candidate, context: CharacterContext) -> bool:
    """Ranking rows carry no character id: match on name, realm key and region.

    Realms are compared by `realm_key` ("Pyrewood Village" = "PyrewoodVillage"),
    the same normalisation the offline analysis uses for WCL's two spellings.
    """
    if _norm(c.name) != _norm(context.name.value):
        return False
    if context.server.value is not None and realm_key(c.server) != realm_key(
        str(context.server.value)
    ):
        return False
    return context.region.value is None or _norm(c.region) == _norm(context.region.value)


def _matches_key(c: Candidate, key: CohortKey) -> str | None:
    if c.raw.get("class") != key.class_name.value:
        return f"class {c.raw.get('class')!r}"
    if key.spec.status == "enforced" and c.spec != key.spec.value:
        return f"spec {c.spec!r}"
    level = c.raw.get("hardModeLevel")
    if not isinstance(level, int) or isinstance(level, bool) or level != 0:
        return f"hardModeLevel {level!r} (must be the integer 0)"
    return None


def _check_key(key: CohortKey, context: CharacterContext) -> None:
    """Refuse a key that is not the canonical key for this context, before reading any row.

    The key is rebuilt from the context and compared dimension by dimension: value,
    value type (so True never passes for 1) and status and note. A key that claims
    another site, role, spec policy or size status than selection applies is refused.
    """
    site = SITES.get(key.site.value) if isinstance(key.site.value, str) else None
    if site is None:
        raise CohortRefused(f"site {key.site.value!r} is not a Warcraft Logs site")
    try:
        require_supported(site)
    except UnsupportedSite as error:
        raise CohortRefused(str(error)) from None
    expected = cohort_key(site, context, key.encounter.value)
    for name in CohortKey.__dataclass_fields__:
        got, want = getattr(key, name), getattr(expected, name)
        if got != want or type(got.value) is not type(want.value):
            raise CohortRefused(f"the key's {name} {got!r} is not the supported {want!r}")


def select(
    rows: Iterator[Any],
    key: CohortKey,
    context: CharacterContext,
    verify: Verify | None = None,
    *,
    deep_needs_observed: bool = False,
) -> Selection:
    """Walk ranking rows in leaderboard order and pick same-faction candidates.

    Without `deep_needs_observed`, `verify` (when given) checks every row, as before.
    With it, same-faction rows that could take a deep slot and guildless rows are checked;
    known other-faction guild rows are excluded before report acquisition.
    and a deep slot accepts only an observed same-faction verdict; other rows keep
    their guild inference and may fill metadata only. An attempted check that finds
    no usable faction discards the guild inference.
    """
    _check_key(key, context)
    cfg = _cfg()
    deep_n, meta_n = int(cfg["deep"]), int(cfg["metadata"])
    want = _FACTIONS[str(key.faction.value)]
    out = Selection(key, rule_set=str(cfg["rule_set"]))
    seen: set[tuple[Any, ...]] = set()
    position = 0
    last_page = None
    try:
        for page, size, row in rows:
            if page != last_page:
                out.pages.append(PageRead(page, size))
                last_page = page
            position += 1
            c = _candidate(position, page, row)
            if position == 1:
                out.overall_first = c
            if _is_subject(c, context):
                out.subject_rows += 1
                continue
            identity = (c.report_code, c.fight_id, _norm(c.name), realm_key(c.server))
            if identity in seen:
                out.duplicates += 1
                continue
            seen.add(identity)
            if _matches_key(c, key) is not None:
                out.key_mismatch.append(c)
                continue
            if c.report_code is None or c.fight_id is None:
                out.inaccessible.append(c)
                continue
            wanted_check = verify is not None and (
                not deep_needs_observed
                or c.faction.level == "unknown"
                or (c.faction.value == key.faction.value and len(out.deep) < deep_n)
            )
            verdict = _verdict(verify(c)) if wanted_check and verify is not None else None
            if verdict is not None:
                out.verdicts[position] = verdict
                if verdict.status == "inaccessible":
                    out.inaccessible.append(c)
                    continue
                if verdict.status == "observed" and verdict.faction is not None:
                    if c.faction.level == "inferred" and c.faction.value != verdict.faction.value:
                        out.contradicted.append(c)
                    c = _with_faction(c, RowFaction(verdict.faction.value, "observed", "verify"))
                else:
                    c = _with_faction(
                        c,
                        RowFaction(
                            None, "unknown", "verify", None, verdict.reason or "check failed"
                        ),
                    )
                if position == 1:
                    out.overall_first = c
            faction = _FACTIONS.get(c.faction.value or "")
            if faction is None:
                out.unresolved.append(c)
                continue
            if faction is not want:
                out.other_faction += 1
                continue
            deep_ok = len(out.deep) < deep_n and (
                c.faction.level == "observed" or not deep_needs_observed
            )
            if deep_ok and len(out.metadata) >= meta_n:
                # Keep deep within metadata and metadata within its target: make room
                # by dropping the lowest-ranked metadata row that is not deep.
                spare = [m for m in out.metadata if m not in out.deep]
                if spare:
                    out.metadata.remove(spare[-1])
                    out.displaced.append(spare[-1])
            if len(out.metadata) < meta_n:
                out.metadata.append(c)
                if deep_ok:
                    out.deep.append(c)
            if len(out.deep) >= deep_n and len(out.metadata) >= meta_n:
                out.stop = "targets met"
                break
        else:
            out.stop = "no more pages"
    except PageBudgetExhausted:
        out.stop = "page budget"
    except (BudgetExceeded, PermissionDenied, RateLimited) as error:
        out.stop = f"{type(error).__name__}: {error}"
        out.rate = error.rate
    out.complete = not out.partial_reasons
    return out


def _with_faction(c: Candidate, faction: RowFaction) -> Candidate:
    return Candidate(
        c.position,
        c.page,
        c.name,
        c.server,
        c.region,
        c.report_code,
        c.fight_id,
        c.amount,
        c.spec,
        c.size,
        faction,
        c.raw,
    )


def select_boss(
    client: WclClient,
    site: Site,
    context: CharacterContext,
    encounter_id: int,
    verify: Verify | None = None,
    *,
    endpoint: Endpoint = "client",
    deep_needs_observed: bool = False,
    prefetched: Selection | None = None,
) -> Selection:
    """Page one boss's declared class/category until same-faction targets are met."""
    key = cohort_key(site, context, encounter_id)
    raw: list[dict[str, Any]] = []
    network_fetch = fetch_page(client, key, endpoint=endpoint, raw_pages=raw)

    def fetch(page: int) -> tuple[list[Any], Any, Any]:
        if prefetched is not None:
            if prefetched.key != key or prefetched.endpoint != endpoint:
                raise CohortRefused("prefetched leaderboard query identity differs")
            saved = [p for p in prefetched.raw_pages if p.get("page") == page]
            if len(saved) == 1:
                raw.append(saved[0])
                return page_items(saved[0]["characterRankings"], page)
        return network_fetch(page)

    rows = pages(fetch, max_pages=int(_cfg()["max_pages"]))
    selection = select(rows, key, context, verify, deep_needs_observed=deep_needs_observed)
    selection.raw_pages = raw
    selection.endpoint = endpoint
    if selection.rate is None:
        selection.rate = client.last_rate
    return selection


def prefetch_boss(
    client: WclClient,
    site: Site,
    context: CharacterContext,
    encounter_id: int,
    *,
    endpoint: Endpoint = "client",
) -> Selection:
    """Capture ranking context before deep samples consume the raid's allowance."""
    key = cohort_key(site, context, encounter_id)
    raw: list[dict[str, Any]] = []
    rows, _, _ = fetch_page(client, key, endpoint=endpoint, raw_pages=raw)(1)
    selection = select(iter(rows), key, context, deep_needs_observed=True)
    selection.raw_pages = raw
    selection.endpoint = endpoint
    selection.stop = "ranking metadata prefetched; deep samples not yet acquired"
    selection.rate = client.last_rate
    return selection


__all__ = [
    "LEADERBOARD_QUERY",
    "Candidate",
    "CohortKey",
    "CohortRefused",
    "Dimension",
    "RowFaction",
    "Selection",
    "Verdict",
    "Verify",
    "cohort_key",
    "guild_faction",
    "page_items",
    "select",
    "select_boss",
]
