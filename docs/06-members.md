# 团队成员与分工

> **你的第一个 PR 就是改这个文件：在表格最后一行之后追加你自己那一行（暂时先不填写负责模块，开完组会再写）。**
> 只追加，不要修改或删除其他人的行。

| 名字   | GitHub          | 负责模块 | 备份模块 | 加入日期   |
| ------ | --------------- | -------- | -------- | ---------- |
| 宋旭涛 | GuMing1234      | R1       |          | 2026-11-17 |
| 贺持   | Secret-Keep     | R7       |          | 2026-11-17 |
| 夏传祥 | 123xcx321       | R4       |          | 2026-11-17 |
| 孙晶   | HAD-bot         | R2       |          | 2026-11-18 |
| 郭精蕾 | gjlqmy-code     | R3       |          | 2026-11-18 |
| 朱亚全 | littleflyingpig | R8       |          | 2026-11-19 |
| 张哲闻 | searchadventure | R5       |          | 2026-11-20 |
| 贺之瀚 |                 | R6       |          |            |

> **副审（Reviewer）：夏传祥（R4）**，持仓库 Write 权限。负责人的 PR 需其 approve 后才能合并。
> 规则见 [`02-collaboration.md`](02-collaboration.md) §六 6.1。

---

## 模块清单（供认领参考）

| 模块              | 文件                      | 职责                                 |
| ----------------- | ------------------------- | ------------------------------------ |
| **types**         | `core/types.py`           | 数据结构（全员依赖，改动需群里通知） |
| **planner**       | `core/planner.py`         | 把用户目标拆成子任务 DAG             |
| **auctioneer**    | `core/auctioneer.py`      | 竞标收集与仲裁                       |
| **agent**         | `core/agent.py`           | Agent 基类 + ReAct 执行循环          |
| **orchestrator**  | `core/orchestrator.py`    | 主循环、状态机、并发控制             |
| **quality_gate**  | `core/quality_gate.py`    | 三层校验                             |
| **conflict**      | `core/conflict.py`        | 冲突检测与消解                       |
| **llm**           | `llm/gateway.py`          | LLM 网关（重试/缓存/预算）           |
| **tools**         | `tools/sandbox.py`        | 工具执行与沙箱                       |
| **memory**        | `memory/store.py`         | 状态与成果物存储                     |
| **observability** | `observability/tracer.py` | 日志、trace、指标                    |
| **eval**          | `eval/`                   | 基准任务与评估报告                   |
