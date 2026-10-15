"""Druid personal coverage precedes comparison spending; Hunter retains its order."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from necropsy.wcl import acquire as module
from necropsy.wcl.acquire import Entry, RunStopped, acquire
from necropsy.wcl.cache import Cache
from necropsy.wcl.cohort import cohort_key
from necropsy.wcl.context import Field
from necropsy.wcl.sites import VANILLA
from tests.integration.test_live_snapshot import _client
from tests.unit.test_wcl_acquire import PATCHWERK, FakeWcl, Player, _context

SAPPHIRON = 51119


@pytest.mark.parametrize("class_id", [2, 3])
def test_personal_first_is_druid_only_and_fetch_order_is_recorded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    class_id: int,
) -> None:
    calls = []
    original_policies = []

    def subject(run: Any, context: Any, boss: Any, cross: bool) -> None:
        calls.append(("personal", boss.encounter_id))
        boss.key = cohort_key(VANILLA, context, boss.encounter_id)
        if boss.encounter_id == PATCHWERK:
            boss.subject = Entry("subject", "Haplina", "Whitemane", "Report", 3, status="complete")

    def comparisons(run: Any, context: Any, boss: Any, cross: bool) -> None:
        calls.append(("comparison", boss.encounter_id))
        original_policies.append(run.client.policy)

    monkeypatch.setattr(module, "_acquire_subject", subject)
    monkeypatch.setattr(module, "_acquire_comparisons", comparisons)
    context = replace(
        _context(),
        class_id=Field(class_id, "observed", "test"),
        ranking_category="Balance" if class_id == 2 else None,
    )
    client = _client(FakeWcl([], Player("Haplina")))
    original = client.policy
    out = acquire(client, Cache(tmp_path), VANILLA, context, encounters=(PATCHWERK, SAPPHIRON))
    if class_id == 2:
        assert calls == [
            ("personal", PATCHWERK),
            ("personal", SAPPHIRON),
            ("comparison", SAPPHIRON),
            ("comparison", PATCHWERK),
        ]
        assert out.comparison_order == (SAPPHIRON, PATCHWERK)
        assert all(p.budget_share < original.budget_share for p in original_policies)
        assert all(p.wait_for_reset is False for p in original_policies)
    else:
        assert calls == [
            ("personal", PATCHWERK),
            ("comparison", PATCHWERK),
            ("personal", SAPPHIRON),
            ("comparison", SAPPHIRON),
        ]
        assert out.comparison_order == ()
        assert all(p is original for p in original_policies)
    assert [b.encounter_id for b in out.bosses] == [PATCHWERK, SAPPHIRON]
    assert client.policy is original


@pytest.mark.parametrize("unexpected", [False, True])
def test_comparison_stop_or_exception_restores_budget_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    unexpected: bool,
) -> None:
    def subject(run: Any, context: Any, boss: Any, cross: bool) -> None:
        boss.key = cohort_key(VANILLA, context, boss.encounter_id)

    def comparisons(*args: Any) -> None:
        if unexpected:
            raise RuntimeError("unexpected comparison error")
        raise RunStopped("BudgetExceeded: comparison allowance exhausted")

    monkeypatch.setattr(module, "_acquire_subject", subject)
    monkeypatch.setattr(module, "_acquire_comparisons", comparisons)
    context = replace(_context(), class_id=Field(2, "observed", "test"), ranking_category="Balance")
    client = _client(FakeWcl([], Player("Haplina")))
    client.policy = replace(client.policy, wait_for_reset=True)
    original = client.policy
    if unexpected:
        with pytest.raises(RuntimeError, match="unexpected"):
            acquire(client, Cache(tmp_path), VANILLA, context, encounters=(PATCHWERK, SAPPHIRON))
    else:
        result = acquire(
            client, Cache(tmp_path), VANILLA, context, encounters=(PATCHWERK, SAPPHIRON)
        )
        assert len(result.bosses) == 2
        assert "reserve kept" in str(result.stopped)
        assert all(not b.coverage["complete"] for b in result.bosses)
    assert client.policy is original
