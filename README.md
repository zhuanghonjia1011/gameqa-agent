# GameQA Agent

面向游戏测试的需求驱动 Agent 学习项目，基于 playtest-agent 二次开发。
开始时间：2026 年 11 月；状态：开发中，已完成离线执行与首轮基准。

## 已实现与待完成

已实现：Pydantic 用例结构校验、3 条示例用例、固定场景执行、状态与动作
JSONL 记录、单独注入缺陷的五种子评估，以及失败重放一致性检查。
新增代码为 AI 辅助编写的学习参考实现。

待完成：模型规划与工具选择、任务记忆、Agent 调用预算、模型视图脱敏、
新执行器的 MCP 接入和 HTML 报告。本仓库尚无 RAG 模块；没有实测的
Agent 提效比例。上游 Explorer、检测器和原有 MCP 服务均保留在 vendor 中。

## 本项目新增内容

| 位置 | 功能 |
| --- | --- |
| `src/gameqa/schemas.py` | 约束 fixture、动作、断言字段及数量 |
| `src/gameqa/runner.py` | 按用例执行、保存前后状态和失败证据 |
| `data/manual_cases.json` | 开门、药水、商店三类回归用例 |
| `benchmarks/baseline.py` | 五种子基准、按条件检出及重放验证 |
| `tests/test_starter.py` | 正常、注入缺陷与无效结构的测试 |

执行器将手工操作与结果记录整理成可重复运行的命令。实际节省的人工
时间尚未测量；不将执行器与 Explorer 的不同工作量耗时折算为提效比例。

## 快速运行

Python 3.12+。在仓库根目录运行（Windows PowerShell）：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e vendor/playtest-agent -e ".[dev]"
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m gameqa --out results/clean.jsonl
.venv/Scripts/python.exe benchmarks/baseline.py --out results/baseline
```

当前命令不需要 API Key，不调用模型。模型集成完成前不能验证 Agent 能力。

## 已保存的首轮实测

测试日期：2026-11-04。两种方法分别运行 1 个正常配置与 8 个单缺陷配置，
每个配置 seed 0 至 4，共 45 条件；探索器每条件最多 3 轮、每轮 250 步。

| 指标 | 新增三用例执行器 | 上游脚本探索器 |
| --- | --- | --- |
| 全部缺陷与种子组合检出 | 15/40（37.5%） | 39/40（97.5%） |
| 正常配置出现告警 | 0/5 | 0/5 |
| 模型调用 | 0 | 0 |

新增执行器覆盖的 3 类缺陷检出 15/15，正常用例 15/15 通过；另外 5 类
未覆盖。3 次抽样重放完全一致。新增测试套件 8 项通过。上游探索器漏检
角色异常无敌的 seed 1。五个种子的结果不代表生产环境指标。

[完整报告](docs/baseline-2026-11-04/基准报告.md) ·
[逐条件数据](docs/baseline-2026-11-04/trials.jsonl) ·
[原始记录](docs/baseline-2026-11-04/raw_results.jsonl)

原始记录含人为注入的缺陷标签，仅供评估；未来模型输入必须去除这些标签。
环境文件保存代码哈希，基准数据来自同一版本。运行耗时受机器与负载影响。

## 上游来源与许可

- 上游：[kevinnie2003/playtest-agent](https://github.com/kevinnie2003/playtest-agent)
- 固定提交：`578dab356ff55bccaad235d39cf7d8c4b2c4b79c`
- 上游源代码、作者声明与 MIT 许可证保留在 `vendor/playtest-agent`。
- 游戏、Explorer、原有检测器、评估器和 MCP 工具来自上游，不计为新增功能。
- 本仓库新增部分尚未指定开源许可证；公开可查看不等同于授予开源许可。
