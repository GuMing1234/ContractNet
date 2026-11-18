# 团队成员与分工

> **你的第一个 PR 就是改这个文件：加上你自己那一行(暂时先不填写负责模块，开完组会再写)。**

| 名字   | GitHub      | 负责模块          | 备份模块  | 加入日期       |
| ---- | ----------- | ------------- | ----- | ---------- |
| 例：张三 | @zhangsan   | planner（任务分解） | types | 2026-11-20 |
| 贺持   | Secret-Keep |               |       | 2026-11-17 |
| 夏传祥   | 123xcx321   |               |       | 2026-11-17 |
|      |             |               |       |            |
|      |             |               |       |            |
|      |             |               |       |            |
|      |             |               |       |            |
|      |             |               |       |            |
|      |             |               |       |            |
|      |             |               |       |            |

---

## 模块清单（供认领参考）

| 模块                | 文件                        | 职责                    |
| ----------------- | ------------------------- | --------------------- |
| **types**         | `core/types.py`           | 数据结构（全员依赖，改动需群里通知）    |
| **planner**       | `core/planner.py`         | 把用户目标拆成子任务 DAG        |
| **auctioneer**    | `core/auctioneer.py`      | 竞标收集与仲裁               |
| **agent**         | `core/agent.py`           | Agent 基类 + ReAct 执行循环 |
| **orchestrator**  | `core/orchestrator.py`    | 主循环、状态机、并发控制          |
| **quality_gate**  | `core/quality_gate.py`    | 三层校验                  |
| **conflict**      | `core/conflict.py`        | 冲突检测与消解               |
| **llm**           | `llm/client.py`           | LLM 客户端（重试/缓存/预算）     |
| **tools**         | `tools/sandbox.py`        | 工具执行与沙箱               |
| **memory**        | `memory/store.py`         | 状态与成果物存储              |
| **observability** | `observability/tracer.py` | 日志、trace、指标           |
| **eval**          | `eval/`                   | 基准任务与评估报告             |
