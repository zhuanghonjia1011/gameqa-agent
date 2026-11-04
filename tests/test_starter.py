import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from gameqa.runner import run_case
from gameqa.schemas import CaseBatch, TestCase as Case
from playtest_agent.game.dungeon import BugFlags

DATA = json.loads((Path(__file__).parents[1] / "data/manual_cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", DATA["cases"])
def test_reviewed_examples_pass_on_clean_game(case):
    result = run_case(Case.model_validate(case))
    assert result["status"] == "passed"
    assert len(result["trace"]) == len(case["actions"])


@pytest.mark.parametrize("index,bugs", [(0, BugFlags(door_ignores_key=True)),
                                        (1, BugFlags(potion_no_consume_check=True)),
                                        (2, BugFlags(shop_allows_negative_gold=True))])
def test_injected_defect_causes_expected_assertion_failure(index, bugs):
    result = run_case(Case.model_validate(DATA["cases"][index]), bugs=bugs)
    assert result["status"] == "failed"
    assert any(not check["passed"] for check in result["checks"])


def test_actions_outside_the_tool_contract_are_rejected():
    case = {**DATA["cases"][0], "actions": ["arbitrary_code"]}
    with pytest.raises(ValidationError):
        Case.model_validate(case)


def test_batch_rejects_unexpected_fields():
    with pytest.raises(ValidationError):
        CaseBatch.model_validate({**DATA, "unreviewed": True})
