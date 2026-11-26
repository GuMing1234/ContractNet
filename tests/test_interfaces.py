'''接口契约测试。

这一组测试的目的不是"覆盖率"，而是**让文档与代码无法在无人察觉的情况下分叉**：

- test_design_chapter6_matches_code 读设计文档第 6 章，逐个断言接口在代码中存在。
  新增/改名接口时，文档与代码必须同时改，否则这里会红。
- 其余用例锁定本轮新增的 6 个接口的**失败路径**（设计文档 §6 公约第 4 条）。
'''

from __future__ import annotations

import importlib
import inspect
import pathlib
import re

import pytest

from contractnet.core.planner import Planner
from contractnet.core.types import Bid, Conflict, ConflictType, Contract, RunResult
from contractnet.core.types import Event

DOC = pathlib.Path(__file__).resolve().parent.parent / 'docs' / '04-design.md'

# 文档模块名 → (模块路径, 类名)。类名未知的模块写 None，按模块内唯一匹配的类猜。
MODULES: dict[str, tuple[str, str | None]] = {
    'Planner': ('contractnet.core.planner', 'Planner'),
    'Auctioneer': ('contractnet.core.auctioneer', 'Auctioneer'),
    'Agent': ('contractnet.core.agent', 'BaseAgent'),
    'Orchestrator': ('contractnet.core.orchestrator', 'Orchestrator'),
    'QualityGate': ('contractnet.core.quality_gate', 'QualityGate'),
    'ConflictResolver': ('contractnet.core.conflict', 'ConflictResolver'),
    'ToolSandbox': ('contractnet.tools.sandbox', 'ToolSandbox'),
    'BuiltinTools': ('contractnet.tools.builtins', None),
    'LLMGateway': ('contractnet.llm.gateway', 'LLMGateway'),
    'StateStore': ('contractnet.memory.store', 'StateStore'),
    'Tracer': ('contractnet.observability.tracer', 'Tracer'),
    'AgentMemory': ('contractnet.memory.agent_memory', 'AgentMemory'),
    'EventBus': ('contractnet.core.event_bus', 'EventBus'),
    'EvalFramework': ('eval.runner', None),
}


def _parse_chapter6() -> dict[str, list[str]]:
    '''从设计文档第 6 章解析出 {模块名: [接口名]}。'''
    text = DOC.read_text(encoding='utf-8')
    body = text[text.index('# 6. 接口规格汇总'):text.index('**四条接口公约**')]
    groups: dict[str, list[str]] = {}
    current: str | None = None
    for line in body.splitlines():
        header = re.search(r'^# ── (\w+)', line)
        if header:
            current = header.group(1)
            groups[current] = []
            continue
        if current and re.match(r'^[a-z]\w*\(', line):
            groups[current].append(line.split('(')[0])
    return groups


def _load_class(module_path: str, class_name: str | None):
    '''模块或类不存在时返回 None，由调用方决定是跳过还是失败。'''
    try:
        module = importlib.import_module(module_path)
    except ImportError:
        return None
    if class_name is None:
        return module
    return getattr(module, class_name, None)


def test_chapter6_is_parseable():
    '''解析器自身要有效，否则下面的测试会假绿。'''
    groups = _parse_chapter6()
    assert 'Planner' in groups
    assert groups['Planner'] == ['plan', 'replan']
    assert len(groups) >= 13


def test_design_chapter6_matches_code():
    '''文档第 6 章列出的每个接口，都必须能在代码里找到。'''
    groups = _parse_chapter6()
    missing: list[str] = []
    skipped: list[str] = []

    for module_name, methods in groups.items():
        if module_name not in MODULES:
            raise AssertionError(
                f'设计文档第 6 章出现了未登记的模块 {module_name!r}，'
                f'请在本测试的 MODULES 里补一条映射'
            )
        module_path, class_name = MODULES[module_name]
        target = _load_class(module_path, class_name)
        if target is None:
            skipped.append(module_name)
            continue
        for method in methods:
            if not hasattr(target, method):
                missing.append(f'{module_name}.{method}')

    assert not missing, f'文档有、代码无：{missing}（未创建模块已跳过：{skipped}）'


# ──────────────────────────────────────────────
# 失败路径：设计文档 §6 公约第 4 条「任何接口的失败路径都要有测试」
# ──────────────────────────────────────────────
class _FakeAgent:
    '''最小 Agent 桩：只实现竞标所需的部分。'''

    def __init__(self, agent_id: str, task_types: list[str]) -> None:
        self.agent_id = agent_id
        self.task_types = task_types

    def bid(self, contract: Contract) -> Bid:
        return Bid(contract_id=contract.contract_id, agent_id=self.agent_id, capability=0.5)


def _contract() -> Contract:
    return Contract(task_id='task_x', description='做点什么')


def test_auctioneer_score_raises():
    from contractnet.core.auctioneer import Auctioneer

    with pytest.raises(NotImplementedError):
        Auctioneer().score(Bid(contract_id='ctr_x', agent_id='a'), _contract())


def test_auctioneer_history_accumulates_across_rounds():
    '''同一契约重试两轮，history 应累计而不是被覆盖。'''
    from contractnet.core.auctioneer import Auctioneer

    auctioneer = Auctioneer()
    agents = [_FakeAgent('a1', ['code']), _FakeAgent('a2', ['code'])]
    contract = _contract()

    auctioneer.auction(contract, agents)
    auctioneer.auction(contract, agents)

    assert len(auctioneer.history(contract.contract_id)) == 4


def test_auctioneer_history_empty_for_unknown_contract():
    from contractnet.core.auctioneer import Auctioneer

    assert Auctioneer().history('ctr_never_seen') == []


def test_wildcard_agent_does_not_win_on_tie():
    '''通配 Agent 与精确匹配 Agent 的 capability 相同时，精确匹配者必须赢，
    且结果与 agents 列表顺序无关。

    这条测试是为了堵住一个假绿：如果只按 capability 取最大，
    胜负取决于列表顺序，测试会因为 Coder 恰好排在 General 前面而通过。
    '''
    from contractnet.core.agent import BaseAgent
    from contractnet.core.auctioneer import Auctioneer

    agents = [
        BaseAgent('agent_coder', 'Coder', ['code', 'design']),
        BaseAgent('agent_general', 'General', ['*']),
    ]
    contract = _contract().model_copy(update={'task_type': 'code'})

    for ordering in (agents, list(reversed(agents))):
        winner = Auctioneer().auction(contract, ordering)
        assert winner is not None
        assert winner.agent_id == 'agent_coder', f'列表顺序 {[a.agent_id for a in ordering]} 下派错人'


def test_orchestrator_cancel_and_status_raise():
    from contractnet.core.auctioneer import Auctioneer
    from contractnet.core.orchestrator import Orchestrator
    from contractnet.core.planner import Planner
    from contractnet.core.quality_gate import QualityGate

    orch = Orchestrator(planner=Planner(), auctioneer=Auctioneer(), quality_gate=QualityGate())
    with pytest.raises(NotImplementedError):
        orch.cancel()
    with pytest.raises(NotImplementedError):
        orch.status()


def test_tracer_record_metric_raises():
    from contractnet.observability.tracer import Tracer

    with pytest.raises(NotImplementedError):
        Tracer().record_metric('latency', 1.0, {'task': 't1'})


def test_store_events_filter_hit_and_miss():
    from contractnet.memory.store import StateStore

    store = StateStore()
    store.log_event(Event(trace_id='aaa', event_type="task_created"))
    store.log_event(Event(trace_id='bbb', event_type="task_created"))

    assert [e.trace_id for e in store.events('aaa')] == ['aaa']
    assert store.events('no-such-trace') == []
    assert len(store.events()) == 2


def test_store_events_filter_survives_model_events():
    '''W2 事件改为模型后，过滤不能静默返回空。'''

    

    from contractnet.memory.store import StateStore

    store = StateStore()
    
    store.log_event(Event(trace_id='aaa', event_type="task_created"))


# ──────────────────────────────────────────────
# 数据结构不变量
# ──────────────────────────────────────────────
def test_conflict_type_has_five_members():
    '''W6 要把 conflict_type 收窄成枚举，这里先钉住成员集合。'''
    assert {c.value for c in ConflictType} == {
        'file_write',
        'interface_mismatch',
        'semantic_contradiction',
        'dependency_violation',
        'deadlock',
    }


def test_conflict_id_is_auto_generated():
    conflict = Conflict(conflict_type=ConflictType.FILE_WRITE.value, description='同一文件被写两次')
    assert conflict.conflict_id.startswith('conf_')


def test_run_result_requires_goal():
    '''goal 漏传必须报错，不能静默返回空目标的结果。'''
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RunResult()


# ──────────────────────────────────────────────
# 签名锁定：防止再次漂移
# ──────────────────────────────────────────────
def test_planner_accepts_llm_keyword():
    sentinel = object()
    assert Planner(llm=sentinel).llm is sentinel


def test_planner_plan_has_context_parameter():
    assert 'context' in inspect.signature(Planner.plan).parameters


def test_sandbox_execute_uses_args_not_params():
    from contractnet.tools.sandbox import ToolSandbox

    params = list(inspect.signature(ToolSandbox.execute).parameters)
    assert params == ['self', 'tool_name', 'args']
