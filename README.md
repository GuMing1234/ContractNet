# ContractNet

> 契约驱动的多 Agent 协作调度框架
> **现成框架解决「编排便利性」，我们解决「协作可靠性」。**

一个用户目标进来，系统自动完成：**任务分解 → Agent 竞标 → 执行 → 质量门控 → 冲突消解**，不需要人工预先画好协作图。

> ⚠️ **项目状态**：进行中（W1/10）。当前是**行走骨架** —— 所有模块是可运行的假实现，
> 用 `TODO` 标出了待实现的位置。这不是生产级框架，是一个学生团队的工程实践项目。
> 提交规范与隐私须知见 `docs/repo-policy.md`（公开仓库守则）。

---

## 5 分钟跑起来

```powershell
# 1. 装依赖（-e 表示可编辑安装，改了代码立刻生效）
pip install -e ".[dev]"

# 2. 跑测试
python -m pytest -q

# 3. 跑最小示例（不调大模型，零成本）
python -X utf8 examples/quickstart.py
```

> **Windows 必看**：项目含中文和 `✓`，**不加 `-X utf8` 会 `UnicodeEncodeError`**。

看到类似下面的输出就说明环境通了：

```
[1/4] Design the structure ...   → Coder   ✅
[2/4] Implement the core ...     → Coder   ✅
...
```

---

## 目录结构

```
ContractNet/
├── src/contractnet/          源码（src 布局，import 才不混乱）
│   ├── core/                 核心模块
│   │   ├── types.py          ★ 全项目共用数据结构（改之前必须群里说）
│   │   ├── planner.py        任务分解
│   │   ├── auctioneer.py     竞标仲裁
│   │   ├── agent.py          Agent 基类与执行
│   │   ├── orchestrator.py   主循环（调度中枢）
│   │   ├── quality_gate.py   三层质量门控
│   │   └── conflict.py       冲突检测与消解
│   ├── llm/client.py         LLM 客户端封装
│   ├── tools/sandbox.py      工具沙箱
│   ├── memory/store.py       状态存储
│   ├── observability/tracer.py  日志与链路追踪
│   └── cli.py                命令行入口
├── tests/                    测试
├── examples/                 示例
├── eval/                     评估与基准任务
├── docs/                     文档
│   ├── members.md            ★ 团队分工表（第一个 PR 改这个）
│   ├── architecture.md       架构说明
│   ├── github-setup.md       GitHub 操作手册
│   ├── decisions/            决策记录（每人一份）
│   └── plan/                 设计文档
├── TASKS.md                  ★ 任务板：谁在做什么、做到哪了
├── CONTRIBUTING.md           ★ 六条铁律 + 协作流程（必读）
└── .github/pull_request_template.md
```

---

## 团队必读（按顺序）

1. [CONTRIBUTING.md](CONTRIBUTING.md) —— 六条铁律，违反会被打回
2. [docs/github-setup.md](docs/github-setup.md) —— 第一次怎么提交代码
3. [TASKS.md](TASKS.md) —— 现在有什么活可以领
4. [docs/members.md](docs/members.md) —— 谁负责什么

---

## 当前状态

**W1 阶段：行走骨架（walking skeleton）**

每个模块目前都是**能跑通的假实现**，用 `TODO` 标出了要替换的地方：

```bash
# 找出所有待实现的地方
grep -rn "TODO" src/
```

骨架能跑通的意义：**在还没有真实功能的时候，就已经验证了「模块之间能不能对上」。**
