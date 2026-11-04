"""Day-1 reference: run reviewed cases and retain every action transition.

Future work includes requirement-ID validation, rich assertion operators,
bounded AI orchestration, normalization, eval metrics and custom MCP tools.
"""
from playtest_agent.agent.client import LocalClient
from playtest_agent.game.dungeon import BugFlags

from .schemas import TestCase


def run_case(case: TestCase, seed: int = 0, bugs: BugFlags | None = None) -> dict:
    client = LocalClient(seed=seed, bugs=bugs)
    client.reset()
    game = client.game
    if case.fixture in ("door_no_key", "door_with_key"):
        game.player = (8, 3)
        game.keys = 1 if case.fixture == "door_with_key" else 0
    elif case.fixture in ("shop_no_gold", "shop_with_gold"):
        game.player = (16, 9)
        game.gold = 5 if case.fixture == "shop_with_gold" else 0
    trace = []
    crashed = False
    for action in case.actions:
        before = game.state().to_dict()
        after = client.step(action)
        trace.append(dict(before=before, action=action, after=after.state,
                          error=after.error, crashed=after.crashed))
        if after.crashed:
            crashed = True
            break
    final = game.state().to_dict()
    checks = [dict(field=rule.field, expected=rule.value, actual=final[rule.field],
                   passed=final[rule.field] == rule.value) for rule in case.expected]
    return dict(case_id=case.id, requirement_ids=case.requirement_ids,
                seed=seed, fixture=case.fixture, actions=case.actions,
                injected_bugs=vars(bugs or BugFlags()),
                status="crashed" if crashed else ("passed" if all(r["passed"] for r in checks) else "failed"),
                checks=checks, trace=trace)
