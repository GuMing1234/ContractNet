'''冒烟测试：保证所有模块都能 import、骨架能跑通。

如果一个 PR 让这里挂了，说明整个包都导不进去了 —— 必须立刻修。
'''

import pytest


def test_import_all_modules():
    from contractnet import __version__                      # noqa: F401
    from contractnet.cli import build_orchestrator           # noqa: F401
    from contractnet.core import agent, auctioneer, conflict  # noqa: F401
    from contractnet.core import orchestrator, planner       # noqa: F401
    from contractnet.core import quality_gate, types         # noqa: F401
    from contractnet.llm import gateway                      # noqa: F401
    from contractnet.memory import store                     # noqa: F401
    from contractnet.observability import tracer             # noqa: F401
    from contractnet.tools import sandbox                    # noqa: F401


def test_skeleton_runs_end_to_end():
    '''骨架能跑完整链路：分解 → 竞标 → 执行 → 门控。'''
    from contractnet.cli import build_orchestrator

    orch = build_orchestrator()
    result = orch.run('写一个 hello world')

    assert result.success is True
    assert len(result.artifacts) == 4
    assert result.metrics['done'] == 4


@pytest.mark.parametrize('task_type,expected_agent', [
    ('code', 'agent_coder'),
    ('test', 'agent_tester'),
    ('doc', 'agent_doc'),
])
def test_task_routed_to_right_agent(task_type, expected_agent):
    '''任务要派给正确的人。

    这是参考实现里的真实 bug：Contract 丢了 task_type，
    导致能力匹配只能去描述文字里找关键词，「实现核心功能」被派给了兜底 Agent。
    我们这里用 task_type 字段判断，所以不会错。
    '''
    from contractnet.core.agent import BaseAgent
    from contractnet.core.auctioneer import Auctioneer
    from contractnet.core.types import Contract

    agents = [
        BaseAgent('agent_coder', 'Coder', ['code', 'design']),
        BaseAgent('agent_tester', 'Tester', ['test']),
        BaseAgent('agent_doc', 'Doc', ['doc']),
        BaseAgent('agent_general', 'General', ['*']),
    ]
    contract = Contract(task_id='t1', task_type=task_type, description='随便一句描述，不含关键词')
    winner = Auctioneer().auction(contract, agents)
    assert winner is not None
    assert winner.agent_id == expected_agent
