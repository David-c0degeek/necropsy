import pytest

from necropsy.analysis.evidence import (
    MAX_EVENT_REFS,
    Claim,
    CoverageRef,
    Evidenced,
    EvidenceError,
    EvidenceLevel,
    EvidenceRef,
    WindfuryStatus,
    complete_or_unknown,
    derived,
    inferred,
    observed,
    unknown,
)

REF = EvidenceRef("R", 1, 2, "events", (("uid", 0),), 1)
TRUSTED = CoverageRef("R", 1, 2, "source", trusted=True)
UNTRUSTED = CoverageRef("R", 1, 2, "source", trusted=False)


def test_factories_set_levels() -> None:
    assert observed(1, REF).level is EvidenceLevel.OBSERVED
    assert derived(1, REF).level is EvidenceLevel.DERIVED
    assert inferred(1, REF, rule_id="r").level is EvidenceLevel.INFERRED
    assert unknown("why").level is EvidenceLevel.UNKNOWN


def test_unknown_carries_no_value() -> None:
    with pytest.raises(EvidenceError):
        Evidenced(1, EvidenceLevel.UNKNOWN)
    assert unknown("why").value is None
    assert not unknown("why").known


@pytest.mark.parametrize("level", [EvidenceLevel.OBSERVED, EvidenceLevel.DERIVED])
def test_known_values_need_references_and_a_value(level: EvidenceLevel) -> None:
    with pytest.raises(EvidenceError, match="reference"):
        Evidenced(1, level)
    with pytest.raises(EvidenceError, match="needs a value"):
        Evidenced(None, level, (REF,))


def test_inference_must_name_its_rule() -> None:
    with pytest.raises(EvidenceError, match="rule"):
        Evidenced(1, EvidenceLevel.INFERRED, (REF,))


def test_complete_claim_needs_trusted_coverage() -> None:
    with pytest.raises(EvidenceError, match="trusted coverage"):
        Evidenced(0, EvidenceLevel.DERIVED, (REF,), claim=Claim.COMPLETE)
    with pytest.raises(EvidenceError, match="trusted coverage"):
        Evidenced(0, EvidenceLevel.DERIVED, (REF,), claim=Claim.COMPLETE, coverage=(UNTRUSTED,))
    with pytest.raises(EvidenceError, match="trusted coverage"):
        Evidenced(
            0, EvidenceLevel.DERIVED, (REF,), claim=Claim.COMPLETE, coverage=(TRUSTED, UNTRUSTED)
        )


@pytest.mark.parametrize("build", [observed, derived])
def test_non_occurrence_cannot_bypass_the_complete_contract(build: object) -> None:
    with pytest.raises(EvidenceError, match="non-occurrence"):
        build(WindfuryStatus.NOT_OBSERVED, REF)  # type: ignore[operator]
    with pytest.raises(EvidenceError, match="non-occurrence"):
        Evidenced(WindfuryStatus.NOT_OBSERVED, EvidenceLevel.DERIVED, (REF,))


def test_complete_or_unknown_keeps_the_coverage_decision() -> None:
    gone = complete_or_unknown(WindfuryStatus.NOT_OBSERVED, [UNTRUSTED], REF)
    assert gone.level is EvidenceLevel.UNKNOWN
    assert gone.coverage == (UNTRUSTED,)
    assert complete_or_unknown(0, [], REF).level is EvidenceLevel.UNKNOWN
    known = complete_or_unknown(0, [TRUSTED], REF, rule_id="r", params={"w": 1})
    assert known.value == 0
    assert known.claim is Claim.COMPLETE
    assert known.coverage == (TRUSTED,)
    assert known.params == (("w", 1),)
    not_seen = complete_or_unknown(WindfuryStatus.NOT_OBSERVED, [TRUSTED], REF)
    assert not_seen.value is WindfuryStatus.NOT_OBSERVED


def test_observed_zero_field_is_a_value_claim() -> None:
    assert observed(0, REF).claim is Claim.VALUE


def test_event_refs_are_capped_but_counted() -> None:
    ref = EvidenceRef.events("R", 1, 2, [(f"u{i}", 0) for i in range(120)])
    assert len(ref.event_ids) == MAX_EVENT_REFS
    assert ref.event_count == 120
