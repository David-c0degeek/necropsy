"""Class/category policies reach the real cohort query with matching metrics."""

import pytest

from necropsy.analysis.class_catalog import CLASS_NAMES
from necropsy.analysis.roles import ranking_policy, selected_spec
from necropsy.wcl.cohort import cohort_key, leaderboard_query
from necropsy.wcl.context import Field
from necropsy.wcl.sites import VANILLA
from tests.class_fixture import CASES
from tests.unit.test_wcl_cohort import _context


@pytest.mark.parametrize(("class_id", "category", "ability", "role"), CASES)
def test_category_reaches_class_spec_and_metric_filters(
    class_id: int,
    category: str,
    ability: str,
    role: str,
) -> None:
    policy = ranking_policy(class_id, selected_spec(category))
    context = _context(class_id=Field(class_id, "observed", "test"), ranking_category=category)
    key = cohort_key(VANILLA, context, 51118)
    query = leaderboard_query(key)
    assert f'className: "{CLASS_NAMES[class_id]}"' in query
    assert f'specName: "{category}"' in query
    assert f"metric: {policy.metric}" in query
    assert key.role.value == role
    assert key.metric.value == ("hps" if role == "healer" else "dps")
    with pytest.raises(ValueError, match="ranking metric"):
        ranking_policy(class_id, category, "dps" if role == "healer" else "hps")


def test_tank_and_healer_aliases_resolve_after_class_selection() -> None:
    assert ranking_policy(11, selected_spec("Tank")).category == "Protection"
    assert ranking_policy(6, selected_spec("Healer")).category == "Holy"
    assert ranking_policy(9, selected_spec("Healer")).category == "Restoration"
    assert ranking_policy(8, selected_spec("DPS")).category == "Assassination"


@pytest.mark.parametrize(
    ("class_id", "unsupported"), [(8, "Combat"), (10, "Affliction"), (3, "Survival")]
)
def test_unverified_ranking_filters_are_not_silently_replaced(
    class_id: int, unsupported: str
) -> None:
    with pytest.raises(ValueError):
        ranking_policy(class_id, unsupported)
