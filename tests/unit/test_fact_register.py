import copy
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from tests.golden.facts import REGISTER_PATH, FactRegister, FactStatus, load_register

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REGISTER_PATH.parent
NAXX_BOSS_SLUGS = {
    "patchwerk",
    "grobbulus",
    "gluth",
    "thaddius",
    "noth-the-plaguebringer",
    "heigan-the-unclean",
    "loatheb",
    "anub-rekhan",
    "grand-widow-faerlina",
    "maexxna",
    "instructor-razuvious",
    "gothik-the-harvester",
    "the-four-horsemen",
    "sapphiron",
    "kel-thuzad",
}


def _raw() -> dict[str, Any]:
    data = yaml.safe_load(REGISTER_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_register_loads() -> None:
    register = load_register()
    assert len(register.facts) > 0


def test_mandatory_set_is_non_empty_and_covers_every_boss() -> None:
    register = load_register()
    covered = {f.id.split(".", 1)[0] for f in register.mandatory}
    assert covered >= NAXX_BOSS_SLUGS


def test_every_fact_source_file_exists() -> None:
    for fact in load_register().facts:
        candidates = [FIXTURE / fact.source.file, REPO / fact.source.file]
        assert any(p.is_file() for p in candidates), f"{fact.id}: missing {fact.source.file}"


def test_unknown_status_is_rejected() -> None:
    data = copy.deepcopy(_raw())
    data["facts"][0]["status"] = "verified"
    with pytest.raises(ValidationError):
        FactRegister.model_validate(data)


def test_unknown_field_is_rejected() -> None:
    data = copy.deepcopy(_raw())
    data["facts"][0]["confidence"] = 1.0
    with pytest.raises(ValidationError):
        FactRegister.model_validate(data)


def test_disputed_fact_requires_resolution() -> None:
    data = copy.deepcopy(_raw())
    data["facts"][0]["status"] = "disputed"
    data["facts"][0].pop("resolution", None)
    with pytest.raises(ValidationError, match="resolution"):
        FactRegister.model_validate(data)


def test_verified_fact_requires_evidence() -> None:
    data = copy.deepcopy(_raw())
    data["facts"][0]["status"] = "verified-against-raw"
    data["facts"][0].pop("evidence", None)
    with pytest.raises(ValidationError, match="evidence"):
        FactRegister.model_validate(data)


def test_duplicate_ids_are_rejected() -> None:
    data = copy.deepcopy(_raw())
    data["facts"].append(copy.deepcopy(data["facts"][0]))
    with pytest.raises(ValidationError, match="duplicate"):
        FactRegister.model_validate(data)


def test_acceptance_flags_unverified_mandatory_facts() -> None:
    data = copy.deepcopy(_raw())
    first = data["facts"][0]
    first["mandatory"] = True
    first["status"] = FactStatus.ORACLE_ONLY.value
    problems = FactRegister.model_validate(data).acceptance_problems()
    assert any(p.startswith(first["id"]) for p in problems)


def test_acceptance_flags_unresolved_optional_oracle_facts() -> None:
    data = {
        "facts": [
            {
                "id": "x.optional",
                "statement": "An optional oracle-only fact.",
                "mode": "historical",
                "mandatory": False,
                "status": "oracle-only",
                "expected": 1,
                "source": {"file": "facts.yaml", "locator": "test"},
            }
        ]
    }
    problems = FactRegister.model_validate(data).acceptance_problems()
    assert "no mandatory facts" in problems
    assert any("without a recorded resolution" in p for p in problems)
