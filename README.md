# ContractNet

> 契约驱动的多 Agent 协作调度框架
> 现成框架解决「编排便利性」，本项目解决「协作可靠性」

用户给出一句目标，系统自行决定：把任务拆成几块、每块派给谁、执行完如何验收、产出冲突如何处理 —— 不依赖人工预先定义的协作图。

> ⚠️ **项目状态**：进行中（W1/10）。当前为行走骨架，各模块为可运行的假实现，以 `TODO` 标注待实现位置。
> 本项目为工程实践项目，非生产级框架。

---

## 5 分钟跑起来

```powershell
git clone https://github.com/GuMing1234/ContractNet.git
cd ContractNet
pip install -e ".[dev]"

python -m pytest -q                    # 测试
python -X utf8 examples/quickstart.py  # 最小示例（不调模型，零成本）
```

> Windows 环境必须加 `-X utf8`，否则中文与符号字符会触发 `UnicodeEncodeError`。

预期输出：4 个成果物，其中「Implement the core functionality」由 **Coder Agent** 执行。

---

## 文档地图

| 我想知道 | 看哪 |
|---|---|
| 这个项目是什么 | 本页 |
| 文档总索引 | [docs/README.md](docs/README.md) |
| 怎么开始写代码 | [docs/01-setup.md](docs/01-setup.md) |
| 有什么规矩 | [docs/02-collaboration.md](docs/02-collaboration.md) |
| 我需要具备什么能力 | [docs/03-onboarding.md](docs/03-onboarding.md) |
| 系统怎么设计的 | [docs/04-design.md](docs/04-design.md) |
| 分工与排期 | [docs/05-project-plan.md](docs/05-project-plan.md) |
| 现在有什么活 | [TASKS.md](TASKS.md) |

---

## 目录结构

```
ContractNet/
├── src/contractnet/
│   ├── core/                 types / planner / auctioneer / agent /
│   │                         orchestrator / quality_gate / conflict
│   ├── llm/gateway.py        模型调用统一入口
│   ├── tools/sandbox.py      工具沙箱
│   ├── memory/store.py       状态与成果物存储
│   ├── observability/        日志与链路追踪
│   └── cli.py                命令行入口
├── tests/                    测试
├── examples/                 示例
├── eval/                     评估与基准
├── docs/                     文档（见索引）
└── TASKS.md                  任务板
```

---

## 许可

MIT，见 [LICENSE](LICENSE)。
