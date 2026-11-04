import argparse
import json
from pathlib import Path

from playtest_agent.eval.harness import make_flags
from playtest_agent.game.dungeon import BugFlags

from .runner import run_case
from .schemas import CaseBatch


def main():
    parser = argparse.ArgumentParser(description="GameQA Day-1 starter: offline case runner")
    parser.add_argument("--cases", type=Path, default=Path("data/manual_cases.json"))
    parser.add_argument("--out", type=Path, default=Path("results/run.jsonl"))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--bug", action="append", choices=BugFlags.all_names(), default=[])
    args = parser.parse_args()
    batch = CaseBatch.model_validate_json(args.cases.read_text(encoding="utf-8"))
    bugs = BugFlags()
    for name in args.bug:
        one = make_flags(name)
        setattr(bugs, name, getattr(one, name))
    results = [run_case(case, args.seed, bugs) for case in batch.cases]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in results), encoding="utf-8")
    print(json.dumps(dict(cases=len(results), passed=sum(r["status"] == "passed" for r in results),
                          failed=sum(r["status"] != "passed" for r in results), report=str(args.out))))


if __name__ == "__main__":
    main()
