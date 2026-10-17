"""Report, playbook and package rendered from the subset's analysis.json."""

from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest

from necropsy.report import package as package_module
from necropsy.report.offline import run_offline
from necropsy.report.package import build_outputs, package_name, write_outputs
from necropsy.report.publish import BACKUP_PREFIX, STAGING_PREFIX
from necropsy.report.render import load_document, render_playbook, render_report
from necropsy.report.render.view import document_view
from tests.analysis_db import subset_db
from tests.fixture_paths import subset_path

HOSTILE = "</script><script>alert(1)</script>\"'><img src=x onerror=alert(2)>../..\\x Ünïcødé 名"


@pytest.fixture(scope="module")
def analysis(tmp_path_factory: pytest.TempPathFactory) -> bytes:
    out = tmp_path_factory.mktemp("subset")
    run_offline(subset_path(), out, db=subset_db(), package=False)
    return (out / "analysis.json").read_bytes()


class _Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.scripts = 0
        self.h1 = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        self.tags.append((tag, a))
        if a.get("id"):
            self.ids.append(str(a["id"]))
        if tag == "a" and a.get("href"):
            self.hrefs.append(str(a["href"]))
        if tag == "script":
            self.scripts += 1
        if tag == "h1":
            self.h1 += 1


def _parse(html: str) -> _Page:
    page = _Page()
    page.feed(html)
    return page


def _pages(analysis: bytes) -> dict[str, str]:
    document, sha = load_document(analysis)
    view = document_view(document, sha)
    return {"report.html": render_report(view), "playbook.html": render_playbook(view)}


def test_pages_are_self_contained_and_offline(analysis: bytes) -> None:
    for name, html in _pages(analysis).items():
        page = _parse(html)
        assert page.h1 == 1 and page.scripts == 1, name
        for tag, attrs in page.tags:
            assert "src" not in attrs, (name, tag)
            assert tag not in ("link", "iframe", "object", "embed", "img", "form"), (name, tag)
            for key, value in attrs.items():
                if key in ("href", "action", "src") and value:
                    if tag == "a" and key == "href" and value.startswith("https://"):
                        assert attrs.get("target") == "_blank"
                        assert attrs.get("rel") == "noopener noreferrer"
                        continue  # cited sources open only when the reader follows them
                    assert not re.match(r"^[a-z][a-z0-9+.-]*:", value), (name, value)
        assert "@import" not in html and "url(" not in html
        script = html.split("<script>")[1].split("</script>")[0]
        for forbidden in ("fetch(", "XMLHttpRequest", "import(", "WebSocket", "sendBeacon"):
            assert forbidden not in script, (name, forbidden)


def test_ids_are_unique_and_every_link_resolves(analysis: bytes) -> None:
    pages = _pages(analysis)
    ids = {name: set(_parse(html).ids) for name, html in pages.items()}
    for name, html in pages.items():
        page = _parse(html)
        assert len(page.ids) == len(set(page.ids)), name
        for href in page.hrefs:
            if href.startswith("https://"):
                continue
            target, _, anchor = href.partition("#")
            other = target or name
            assert other in pages, (name, href)
            if anchor:
                assert anchor in ids[other], (name, href)


def test_report_and_playbook_link_to_each_other(analysis: bytes) -> None:
    for name, html in _pages(analysis).items():
        hrefs = _parse(html).hrefs
        assert "report.html" in hrefs and "playbook.html" in hrefs, name


def test_rendering_is_deterministic(analysis: bytes) -> None:
    assert _pages(analysis) == _pages(analysis)
    first = build_outputs(analysis)
    second = build_outputs(analysis)
    assert first == second


def test_untrusted_citation_schemes_never_become_links(analysis: bytes) -> None:
    document = json.loads(analysis)
    document["overview"]["setup"]["subject_ammo"]["source"] = "javascript:alert(1)"
    document["overview"]["setup"]["pet_facts"]["sources"]["family_modifiers"] = [
        "javascript:alert(3)"
    ]
    for boss in document["bosses"]:
        if boss.get("playbook") and boss["playbook"].get("static"):
            static = boss["playbook"]["static"]
            static["encounter"]["source"] = "data:text/html,<script>alert(2)</script>"
            for bonus in static["type_bonuses"]:
                bonus["source"] = "file:///private/secret"
    for html in _pages(json.dumps(document).encode()).values():
        assert all(not h.startswith(("javascript:", "data:", "file:")) for h in _parse(html).hrefs)


def test_conditional_guidance_keeps_both_choices_and_uncertainty(analysis: bytes) -> None:
    document = json.loads(analysis)
    item = document["bosses"][0]["playbook"]["static"]["guidance"]["items"][0]
    item["status"] = "conditional"
    item["text"] = "GUIDANCE_PRIMARY"
    item["otherwise"] = "GUIDANCE_ALTERNATIVE"
    item["condition"] = {
        "name": "kill_within_rapid_fire_cooldown",
        "status": "unknown",
        "detail": "GUIDANCE_REASON_UNKNOWN",
        "level": "unknown",
    }
    for html in _pages(json.dumps(document).encode()).values():
        assert "Conditional advice: GUIDANCE_PRIMARY" in html
        assert "Alternative: GUIDANCE_ALTERNATIVE" in html
        assert "unknown: GUIDANCE_REASON_UNKNOWN" in html


def _hostile(analysis: bytes) -> bytes:
    document = json.loads(analysis)
    document["subject"]["name"] = HOSTILE
    boss = document["bosses"][0]
    boss["boss"] = HOSTILE
    boss["cohort"][0]["player"] = HOSTILE
    for rec in boss["recommendations"]:
        rec["finding"] = HOSTILE
    shares = boss["encounter"]["ranked_target_shares"]["counted"]
    shares[0]["name"] = HOSTILE
    return json.dumps(document, sort_keys=True).encode("utf-8")


def test_hostile_strings_are_escaped_everywhere(analysis: bytes) -> None:
    hostile = _hostile(analysis)
    for name, html in _pages(hostile).items():
        page = _parse(html)
        assert page.scripts == 1, name
        assert not [t for t, _ in page.tags if t == "img"], name
        assert "<script>alert(1)" not in html and "onerror=alert(2)>" not in html
        assert "&lt;/script&gt;" in html and "Ünïcødé 名" in html
    outputs = build_outputs(hostile)
    names = [n for n in outputs if n.endswith(".zip")]
    assert names == [package_name(json.loads(hostile))]
    assert re.fullmatch(r"necropsy-\d+-\d+\.zip", names[0])
    data = outputs[names[0]]
    assert data is not None
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for member in zf.namelist():
            assert ".." not in member and "\\" not in member and not member.startswith("/")
        rows = zf.read("tables/recommendations.csv").decode("utf-8")
        assert HOSTILE.split("\n")[0][:10] in rows


def test_csv_cells_cannot_start_a_formula(analysis: bytes) -> None:
    document = json.loads(analysis)
    document["bosses"][0]["recommendations"][0]["finding"] = "=HYPERLINK(1)"
    tables = package_module.tables(document)
    assert "'=HYPERLINK(1)" in tables["tables/recommendations.csv"].decode("utf-8")


def test_package_contents_and_manifest(analysis: bytes) -> None:
    outputs = build_outputs(analysis)
    [zip_name] = [n for n in outputs if n.endswith(".zip")]
    data = outputs[zip_name]
    assert data is not None
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        assert names == sorted(names)
        assert {"analysis.json", "report.html", "playbook.html", "manifest.json"} <= set(names)
        assert {n for n in names if n.startswith("tables/")} == {
            "tables/recommendations.csv",
            "tables/cohort.csv",
            "tables/target_shares.csv",
            "tables/execution.csv",
            "tables/ability-use.csv",
        }
        assert zf.read("analysis.json") == analysis
        assert zf.read("report.html") == outputs["report.html"]
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["analysis_sha256"] == hashlib.sha256(analysis).hexdigest()
        listed = {f["path"]: f for f in manifest["files"]}
        assert set(listed) == set(names) - {"manifest.json"}
        for path, entry in listed.items():
            body = zf.read(path)
            assert entry["sha256"] == hashlib.sha256(body).hexdigest()
            assert entry["bytes"] == len(body)
        assert "Not anonymised" in manifest["notice"]
        for info in zf.infolist():
            assert info.date_time == (1980, 1, 1, 0, 0, 0)
        evidence = [n for n in names if n.startswith("evidence/")]
        document = json.loads(analysis)
        assert len(evidence) == len(document["bosses"])
        for n in evidence:
            assert re.fullmatch(r"evidence/\d+\.json", n)


def test_package_holds_no_secrets_or_local_paths(analysis: bytes) -> None:
    outputs = build_outputs(analysis)
    [zip_name] = [n for n in outputs if n.endswith(".zip")]
    data = outputs[zip_name]
    assert data is not None
    patterns = [
        re.compile(rb"(?i)bearer\s+[a-z0-9._-]{20,}"),
        re.compile(rb"(?i)client_secret"),
        re.compile(rb"(?i)access_token"),
        re.compile(rb"(?i)[a-z]:\\\\users\\\\"),
        re.compile(rb"/home/[a-z]"),
        re.compile(rb"\.wcl_user_token"),
    ]
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in zf.namelist():
            body = zf.read(name)
            for pattern in patterns:
                assert not pattern.search(body), (name, pattern.pattern)


def test_no_package_removes_a_previous_one(analysis: bytes, tmp_path: Path) -> None:
    write_outputs(analysis, tmp_path)
    zip_name = package_name(json.loads(analysis))
    assert (tmp_path / zip_name).exists()
    write_outputs(analysis, tmp_path, include_package=False)
    assert not (tmp_path / zip_name).exists()
    assert (tmp_path / "report.html").exists()


@pytest.mark.parametrize("stage", ["render", "zip"])
def test_build_failure_keeps_the_previous_set(
    analysis: bytes, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    write_outputs(analysis, tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}

    def boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError(f"{stage} failed")

    monkeypatch.setattr(package_module, "render_playbook" if stage == "render" else "_zip", boom)
    changed = analysis.replace(b'"cross_faction": false', b'"cross_faction": false ')
    with pytest.raises(RuntimeError):
        write_outputs(changed, tmp_path)
    after = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    assert after == before
    assert not [n for n in after if n.startswith((STAGING_PREFIX, BACKUP_PREFIX))]


def test_playbook_states_follow_the_evidence(analysis: bytes) -> None:
    document, sha = load_document(analysis)
    view = document_view(document, sha)
    statuses = {g.status for b in view.bosses for g in b.playbook}
    assert "action" in statuses
    for boss in view.bosses:
        for group in boss.playbook:
            if group.status == "action":
                assert group.cards
            elif group.status == "no-change":
                assert not group.cards and all(f.yours.known for f in group.facts)
                assert all(f.typical is None or f.typical.known for f in group.facts)
            elif group.status == "partial":
                assert not group.cards and any(f.yours.known for f in group.facts)
                assert not all(
                    f.yours.known and (f.typical is None or f.typical.known) for f in group.facts
                )
            else:
                assert not group.cards and not any(f.yours.known for f in group.facts)


def test_unknown_values_never_render_as_numbers(analysis: bytes) -> None:
    document, sha = load_document(analysis)
    kt = document_view(document, sha).bosses[-1]
    # One same-faction entry on Kel'Thuzad in the subset: every median is unknown.
    for row in kt.execution:
        assert row.baseline.text == "Unknown" and row.baseline.note
    assert kt.raid_speed is not None and kt.raid_speed.median.ratio.text == "Unknown"
    assert kt.raid_speed.fastest is not None and kt.raid_speed.fastest.ratio.known


def test_playbook_is_an_action_sheet_and_report_retains_the_detail(analysis: bytes) -> None:
    view = document_view(*load_document(analysis))
    report = render_report(view)
    playbook = render_playbook(view)
    for heading in (
        "Recommended opener",
        "Your full logged gear for this selected best parse",
        "Execution plan",
        "Loadout plan",
    ):
        assert heading in report
    assert "Recorded opening:" in report and "Same-faction comparator:" in report
    assert "Observed cast timing" in report
    assert not any(tag == "table" for tag, _ in _parse(playbook).tags)
    assert 'class="comparison-snapshot"' not in playbook
    assert 'class="action-evidence"' not in playbook
    assert "Severity:" not in playbook and "High confidence" not in playbook
    for boss in view.bosses:
        assert f'href="report.html#{boss.anchor}"' in playbook
        for group in boss.playbook:
            assert f'id="{boss.anchor}-{group.key}"' in report
        for phase in ("before", "during", "raid"):
            assert f'id="{boss.anchor}-{phase}"' in playbook
    assert "Before the pull" in playbook and "During the fight" in playbook
    assert "Coordinate with the raid" in playbook
    assert "Recorded opening example, not a required rotation" in playbook


def test_playbook_keeps_action_affecting_uncertainty(analysis: bytes) -> None:
    document = json.loads(analysis)
    rec = document["bosses"][0]["recommendations"][0]
    rec["confidence"] = "low"
    rec["limitations"] = ["Confirm the assigned duty before changing this action."]
    html = _pages(json.dumps(document).encode())["playbook.html"]
    assert "Tentative advice: limited evidence" in html
    assert "Confirm the assigned duty before changing this action." in html
    assert "Conditional advice:" in html


def test_quick_plan_keeps_missing_and_inferred_evidence_visible(analysis: bytes) -> None:
    from necropsy.report.render.playbook_view import _quick_plan

    document = json.loads(analysis)
    plan = document["bosses"][0]["playbook"]
    plan["opener"]["comparator_sequence"] = None
    plan["rapid_fire"]["same_faction_first_s"].update(
        value=None, n_values=1, n_without=2, n_unknown=1, level="inferred"
    )
    rows = _quick_plan(plan, {}, {}, {})
    text = " ".join(part["text"] + " " + part["note"] for row in rows for part in row["lines"])
    assert "no comparator ranged opening" in text and "timing unknown" in text
    assert "No comparable ranged opening is available" in text
    assert "Practice pattern from the same-faction comparator" not in text
    assert "2 had no RF cast recorded" in text and "1 unknown" in text
    assert "membership is inferred" in text


def test_reference_ability_section_requires_recorded_reference(analysis: bytes) -> None:
    document = json.loads(analysis)
    boss = document["bosses"][0]
    document["bosses"] = [boss]
    faction = boss["subject"]["environment"]["faction"]["value"]
    reference = next(
        e for e in boss["overall_cohort"] if e["environment"]["faction"]["value"] == faction
    )
    boss["benchmarks"]["ceiling"]["player"] = reference["player"]
    reference["ability_use"] = {
        "value": {"Auto Shot": 2},
        "level": "observed",
        "claim": "complete",
        "refs": [],
    }
    before = _pages(json.dumps(document).encode())
    boss["overall_cohort"] = []
    boss["playbook"]["opener"]["comparator_sequence"] = None
    after = _pages(json.dumps(document).encode())
    assert "Compare ability use with the reference player" in before["report.html"]
    assert "Compare ability use with the reference player" not in after["report.html"]
    assert "No comparable ranged opening is available" in after["report.html"]
    for name in ("report.html", "playbook.html"):
        assert "Unknown: no comparator ranged opening recorded" in after[name]


def test_overall_unknown_reason_preserves_failed_requested_context(analysis: bytes) -> None:
    from necropsy.report.render.playbook_view import _overall_reason

    document = json.loads(analysis)
    boss = document["bosses"][0]
    boss["benchmarks"]["overall_top"] = None
    assert "--cross-faction" in _overall_reason(boss, {}, True)
    document["acquisition"] = {
        "cross_faction": True,
        "bosses": [
            {
                "encounter_id": boss["encounter_id"],
                "cross_faction_reason": "archived report inaccessible",
            }
        ],
    }
    assert "archived report inaccessible" in _overall_reason(boss, document, True)
    boss["benchmarks"]["overall_top"] = {"player": "Recorded", "ranked_dps": None}
    assert "ranked DPS is unavailable" in _overall_reason(boss, document, True)


def test_inferred_membership_shows_in_the_playbook(analysis: bytes) -> None:
    document = json.loads(analysis)
    document["bosses"][0]["benchmarks"]["baseline"]["membership"]["level"] = "inferred"
    document["bosses"][0]["benchmarks"]["baseline"]["membership"]["rule"] = "r"
    changed = json.dumps(document, sort_keys=True).encode("utf-8")
    view = document_view(*load_document(changed))
    gear = next(g for g in view.bosses[0].playbook if g.key == "gear")
    talents = next(f for f in gear.facts if f.label == "Talents")
    assert talents.typical is not None and talents.typical.level == "inferred"
    html = render_playbook(view)
    assert "Comparator membership is inferred" in html


def test_data_notes_never_claim_a_full_comparison(analysis: bytes) -> None:
    document, sha = load_document(analysis)
    view = document_view(document, sha)
    notes = {b.limit_summary for b in view.bosses}
    assert "Full comparison" not in notes
    assert any(n == "Baseline available" for n in notes)


def _patched(analysis: bytes, change: Any) -> tuple[dict[str, Any], str]:
    document = json.loads(analysis)
    change(document)
    return load_document(json.dumps(document, sort_keys=True).encode("utf-8"))


def _no_pets(listed: bool | None) -> Any:
    def change(document: dict[str, Any]) -> None:
        subject = document["bosses"][0]["subject"]
        subject["hunter"]["hunter_pets"] = []
        subject["hunter"]["pets"] = []
        subject["hunter"].pop("pet_roster_complete", None)
        subject["hunter"].pop("total_pet_dps", None)
        if listed is None:
            subject.pop("pets_listed", None)
        else:
            subject["pets_listed"] = listed

    return change


@pytest.mark.parametrize(
    ("listed", "text"), [(False, "Unknown"), (None, "Unknown"), (True, "None took part")]
)
def test_no_pet_is_proven_only_with_a_pet_listing(
    analysis: bytes, listed: bool | None, text: str
) -> None:
    view = document_view(*_patched(analysis, _no_pets(listed)))
    pet = next(g for g in view.bosses[0].playbook if g.key == "pet")
    fact = next(f for f in pet.facts if f.label == "Hunter pet in this fight")
    assert fact.yours.text == text
    html = render_report(view)
    if listed is None:
        assert fact.yours.note == "pet-listing availability was not recorded in this analysis"
    elif listed is False:
        assert fact.yours.note == "the export's pet listing is missing for this fight"
        assert "pet listing is missing" in html
    else:
        assert fact.yours.note == "no pets listed"
        assert "no pets listed" in html


def _inferred(document: dict[str, Any]) -> None:
    for boss in document["bosses"]:
        baseline = boss["benchmarks"].get("baseline")
        if baseline:
            baseline["membership"]["level"] = "inferred"
            baseline["membership"]["rule"] = "r"


def test_every_cohort_aggregate_keeps_the_inferred_grade(analysis: bytes) -> None:
    view = document_view(*_patched(analysis, _inferred))
    for boss in view.bosses:
        if not boss.has_subject or not boss.weave:
            continue
        explosives = next(f for f in boss.cooldowns if f.label == "Explosives used")
        assert explosives.typical is not None and explosives.typical.level == "inferred"
        assert all(w.adoption.level == "inferred" for w in boss.weave)
        if boss.integrity is not None and boss.integrity.cohort_median.known:
            assert boss.integrity.cohort_median.level == "inferred"


def _fill(known: bool, eligible: bool | None = None) -> Any:
    def change(document: dict[str, Any]) -> None:
        baseline = document["bosses"][0]["benchmarks"]["baseline"]
        value: dict[str, Any] = (
            {
                "value": 7.5,
                "level": "inferred",
                "claim": "value",
                "rule": "r",
                "refs": [{"source": "cohort", "report": "R"}],
            }
            if known
            else {"value": None, "level": "unknown", "claim": "value", "note": "only 2"}
        )
        baseline["tauren_fill"] = {
            "needed_for": ["aimed_per_min"],
            "eligible": ["Moo"] if (known if eligible is None else eligible) else [],
            "excluded": [["Grunt", "race Orc"]],
            "medians": {
                "aimed_per_min": {"value": value, "n_known": 3 if known else 2, "n_unknown": 0}
            },
            "membership": {
                "value": "x",
                "level": "inferred",
                "claim": "value",
                "rule": "r",
                "refs": [{"source": "cohort", "report": "R"}],
            },
        }

    return change


@pytest.mark.parametrize("known", [True, False])
def test_fill_is_reported_as_used_only_when_it_supplies_a_value(
    analysis: bytes, known: bool
) -> None:
    view = document_view(*_patched(analysis, _fill(known)))
    boss = view.bosses[0]
    assert boss.fill is not None and boss.fill.applied is known
    html = render_report(view)
    if known:
        assert "supplies some comparisons" in " ".join(boss.limits)
        assert "Tauren fill (fallback comparison)" in html
    else:
        assert "no other-faction entry qualified" in " ".join(boss.limits)
        assert "Tauren fill considered — not used" in html
        assert "Grunt: race Orc" in html


def test_fill_with_too_few_qualifying_entries_says_so(analysis: bytes) -> None:
    view = document_view(*_patched(analysis, _fill(False, eligible=True)))
    boss = view.bosses[0]
    assert boss.fill is not None and not boss.fill.applied and boss.fill.eligible == ("Moo",)
    assert any("still too few" in limit for limit in boss.limits)
    assert "Qualifying entries were still too few for a median" in render_report(view)
