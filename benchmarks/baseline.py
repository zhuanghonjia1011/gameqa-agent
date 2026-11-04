"""One offline baseline round; never constructs a model/API client.

Run from the project root: python benchmarks/baseline.py --out results/baseline
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor/playtest-agent/src")]

import pydantic
from gameqa.runner import run_case
from gameqa.schemas import CaseBatch
from playtest_agent.agent.client import LocalClient
from playtest_agent.agent.explorer import Explorer
from playtest_agent.agent.llm import NullPlanner
from playtest_agent.eval.harness import EXPECTED, make_flags
from playtest_agent.game.dungeon import BugFlags

SEEDS = [0, 1, 2, 3, 4]
NAMES = {
    "door_ignores_key": "无钥匙开门",
    "east_wall_missing": "边界穿墙",
    "potion_no_consume_check": "满血错误消耗药水",
    "shop_allows_negative_gold": "余额不足仍能购买",
    "player_invulnerable": "角色异常无敌",
    "softlock_after_turns": "操作失效软锁",
    "key_overflow_crash": "钥匙溢出崩溃",
    "goal_does_not_win": "到终点无法通关",
}
TARGET_CASE = {
    "door_ignores_key": "R1-door-without-key",
    "potion_no_consume_check": "R2-potion-at-full-hp",
    "shop_allows_negative_gold": "R4-shop-insufficient-gold",
}


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "results/baseline")
    args = parser.parse_args()
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=True)
    batch = CaseBatch.model_validate_json((ROOT / "data/manual_cases.json").read_text(encoding="utf-8"))
    environment = dict(
        report_date="2026-11-04", timezone="Asia/Shanghai",
        python=platform.python_version(), platform=platform.platform(),
        pydantic=pydantic.__version__, rounds=1, seeds=SEEDS,
        explorer_episodes=3, explorer_max_steps_per_episode=250,
        starter_cases=len(batch.cases), llm_enabled=False, api_calls=0,
        upstream_commit="578dab356ff55bccaad235d39cf7d8c4b2c4b79c",
        timing="perf_counter; model imports, warmup, output writing and replay checks excluded",
    )
    environment["sha256"] = {
        str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
        for directory in (ROOT / "src", ROOT / "vendor/playtest-agent/src", ROOT / "data", ROOT / "benchmarks")
        for p in sorted(directory.rglob("*"))
        if p.is_file() and p.suffix in (".py", ".json", ".md")
    }
    dump(output / "environment.json", environment)

    # Unscored warmup for each method. The measured round is executed serially.
    run_case(batch.cases[0])
    Explorer(LocalClient(seed=0), planner=NullPlanner(), seed=0).run(episodes=1, max_steps=20)
    rows, raw = [], []
    for bug in [None, *EXPECTED]:
        for seed in SEEDS:
            flags = make_flags(bug) if bug else BugFlags()
            start = time.perf_counter()
            cases = [run_case(case, seed, flags) for case in batch.cases]
            seconds = time.perf_counter() - start
            failed = [r["case_id"] for r in cases if r["status"] != "passed"]
            rows.append(dict(method="starter", bug=bug, seed=seed,
                             detected=bool(bug and TARGET_CASE.get(bug) in failed),
                             covered_by_suite=bug in TARGET_CASE if bug else None,
                             alerts=failed, case_count=len(cases), failed_cases=len(failed),
                             steps=sum(len(r["trace"]) for r in cases), seconds=seconds))
            raw.append(dict(method="starter", bug=bug, seed=seed, cases=cases))

            start = time.perf_counter()
            result = Explorer(LocalClient(seed=seed, bugs=flags), planner=NullPlanner(), seed=seed).run(
                episodes=3, max_steps=250)
            seconds = time.perf_counter() - start
            kinds = sorted({f.kind for f in result.findings})
            rows.append(dict(method="upstream_scripted", bug=bug, seed=seed,
                             detected=bool(bug and set(kinds) & set(EXPECTED[bug])),
                             alerts=kinds, steps=result.total_steps, seconds=seconds,
                             llm_calls=result.llm_calls, coverage=result.coverage))
            raw.append(dict(method="upstream_scripted", bug=bug, seed=seed,
                            result=result.to_dict()))
        print(f"Completed {bug or 'clean'}", flush=True)

    replay = []
    for bug, case_id in TARGET_CASE.items():
        case = next(c for c in batch.cases if c.id == case_id)
        reference = next(r for r in raw if r["method"] == "starter" and r["bug"] == bug and r["seed"] == 0)
        expected = next(c for c in reference["cases"] if c["case_id"] == case_id)
        actual = run_case(case, 0, make_flags(bug))
        replay.append(dict(bug=bug, seed=0, case_id=case_id,
                           exact_match=actual == expected))

    summaries = {}
    for method in ("starter", "upstream_scripted"):
        subset = [r for r in rows if r["method"] == method]
        defects = [r for r in subset if r["bug"]]
        clean = [r for r in subset if not r["bug"]]
        summaries[method] = dict(
            trials=len(subset), positive_conditions=len(defects),
            detected_conditions=sum(r["detected"] for r in defects),
            detection_rate=sum(r["detected"] for r in defects) / len(defects),
            clean_runs=len(clean), clean_runs_with_alerts=sum(bool(r["alerts"]) for r in clean),
            clean_alert_count=sum(len(r["alerts"]) for r in clean),
            total_steps=sum(r["steps"] for r in subset),
            total_compute_seconds=sum(r["seconds"] for r in subset),
            median_condition_ms=statistics.median(r["seconds"] for r in subset) * 1000,
        )
    summaries["starter"].update(
        total_case_executions=135, clean_case_executions=15,
        clean_passed_cases=15 - summaries["starter"]["clean_alert_count"],
        requirements_with_cases=["R1", "R2", "R4"], total_requirements=9,
        targeted_conditions=15,
        targeted_detected_conditions=sum(r["detected"] for r in rows if r["method"] == "starter" and r["covered_by_suite"]),
    )
    by_bug = {bug: {
        method: {str(seed): next(r["detected"] for r in rows if r["method"] == method and r["bug"] == bug and r["seed"] == seed) for seed in SEEDS}
        for method in ("starter", "upstream_scripted")}
        for bug in EXPECTED}
    assert len(rows) == 90
    assert all(r["llm_calls"] == 0 for r in rows if r["method"] == "upstream_scripted")
    assert all(r["exact_match"] for r in replay)
    dump(output / "summary.json", dict(methods=summaries, by_bug=by_bug, replay_checks=replay))
    for filename, records in (("trials.jsonl", rows), ("raw_results.jsonl", raw)):
        with (output / filename).open("w", encoding="utf-8") as stream:
            for row in records:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")

    s, u = summaries["starter"], summaries["upstream_scripted"]
    lines = ["# GameQA Agent 首轮离线基准", "", "测试日期：2026 年 11 月 4 日。单轮运行，无模型请求。", "",
             "## 本轮范围", "",
             "分别运行新增的三用例执行器，以及开源项目自带的脚本探索器。完整需求驱动 Agent 尚未实现，本报告不代表 Agent 效果或提效成绩。",
             "每种方法包含正常场景和八种单独注入的缺陷，每种配置运行 seed 0～4，共 45 个条件。探索器每条件最多 3 轮、每轮 250 步；用例执行器每条件运行现有 3 条单步用例。",
             "本轮不修改提示、检测规则或用例，也不使用跨 seed 合并检出的方法。", "",
             "## 主要结果", "", "| 指标 | 三用例执行器 | 上游脚本探索器 |", "| --- | --- | --- |",
             f"| 预置缺陷与 seed 组合检出 | {s['detected_conditions']}/40（{s['detection_rate']:.1%}） | {u['detected_conditions']}/40（{u['detection_rate']:.1%}） |",
             f"| 正常场景出现告警的运行 | {s['clean_runs_with_alerts']}/5 | {u['clean_runs_with_alerts']}/5 |",
             f"| 全部条件执行动作数 | {s['total_steps']} | {u['total_steps']} |",
             f"| 每条件计算耗时中位数 | {s['median_condition_ms']:.3f} ms | {u['median_condition_ms']:.3f} ms |",
             f"| 45 个条件的计算耗时合计 | {s['total_compute_seconds']:.4f} s | {u['total_compute_seconds']:.4f} s |", "",
             f"现有执行器的正常场景用例通过 {s['clean_passed_cases']}/15；对它已经覆盖的三种缺陷，检出 {s['targeted_detected_conditions']}/15。其余五类缺陷尚无对应测试用例，因此总体基准不能写成 100%。",
             "现有用例关联 R1、R2、R4，需求编号覆盖 3/9；这不等同于完整的语义覆盖或代码覆盖。三个已检出问题各抽 seed 0 重放一次，均与原始结果和轨迹完全一致。", "",
             "## 每类缺陷结果", "", "下列五位结果依次对应 seed 0、1、2、3、4，✓ 为检出，— 为未检出。", "",
             "| 缺陷 | 三用例执行器 | 上游脚本探索器 |", "| --- | --- | --- |"]
    for bug in EXPECTED:
        mark = lambda method: " ".join("✓" if by_bug[bug][method][str(seed)] else "—" for seed in SEEDS)
        lines.append(f"| {NAMES[bug]} | {mark('starter')} | {mark('upstream_scripted')} |")
    lines += ["", "## 解释与限制", "",
              "- 两种方法的测试范围和动作量不同，耗时不能直接换算为提效比例。计时含对象初始化及结果构造，排除导入、预热、文件写入与补充回放；单轮微秒级结果只用于留档。",
              "- 探索器及其检测能力来自上游开源项目；不能把它的检出成绩记为新增 Agent 的成绩。",
              "- 正常场景未触发告警只是这五次运行的观察，不代表生产环境误报率为零。这里不报告混合口径的 precision。",
              "- 尚未测量真实模型调用、任务规划、MCP、人工审核时间、端到端使用时间和提效比例。",
              "- 原始结果包含人为注入的缺陷标签，仅用于离线评估与复现；未来模型工具视图必须隐藏这些标签。", "",
              "## 接下来要验证", "",
              "补齐其余需求和缺陷用例后，完成规划、工具选择、记忆与预算控制。再在相同工具、初始信息和总动作预算下对比固定流程与 Agent，统计任务完成、检出、误报、调用量及人工耗时。", "",
              "## 复现与证据", "",
              "安装起步包依赖后，在项目根目录运行：", "", "```powershell",
              "python benchmarks/baseline.py --out results/baseline", "```", "",
              "environment.json 保存参数、环境和源码哈希；summary.json 保存汇总；trials.jsonl 保存逐条件指标；raw_results.jsonl 保存原始状态、动作、断言及上游报告。测试套件结果另存 tests.txt。"]
    (output / "基准报告.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summaries, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
