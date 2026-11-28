'''Auctioneer 的授标与「无人竞标」诊断。

重点覆盖 §3.13 的四种 NoBidReason：它们是 Orchestrator 分支的唯一依据，
搞混一个，调度器就会把「都忙着」当成「没人会」直接判 IMPOSSIBLE。

诊断逻辑的判定顺序也是被测的一部分：先能力、后忙——
否则一个既不匹配又忙的 Agent 会把「没人会」这个更严重的事实盖掉。
'''

from __future__ import annotations

from contractnet.core.agent import BaseAgent
from contractnet.core.auctioneer import Auctioneer
from contractnet.core.types import Contract, ContractConstraints, NoBidReason


def make_contract(task_type: str = 'code', required_tools: list[str] | None = None) -> Contract:
    return Contract(
        task_id='task_x',
        task_type=task_type,
        description='随便一句描述，不含任何关键词',
        constraints=ContractConstraints(required_tools=required_tools or []),
    )


def mark_busy(agent: BaseAgent) -> BaseAgent:
    '''标记 Agent 忙碌。

    TODO(R4): BaseAgent 提供 set_busy() 之后改成 agent.set_busy(True)；
              现在直写私有字段只是为了本模块能先测。
    '''
    agent._busy = True
    return agent


class SilentAgent(BaseAgent):
    '''有能力接、也空闲，但主动拒标。'''

    def bid(self, contract: Contract):
        return None


# ──────────────────────────────────────────────
# 正常授标
# ──────────────────────────────────────────────
def test_winner_carries_bids_and_no_reason():
    agents = [BaseAgent('a1', 'Coder', ['code']), BaseAgent('a2', 'Coder', ['code'])]
    res = Auctioneer().auction(make_contract(), agents)

    assert res.winner is not None
    assert res.reason is None, '有中标者时不应该再给原因'
    assert len(res.bids) == 2, 'bids 要保留全部出价（含落选），供复盘'
    assert res.rejections == []


def test_busy_agent_does_not_bid():
    '''ADR-10：忙的 Agent 在竞标阶段就被过滤，不是提交后才排队。'''
    idle = BaseAgent('a_idle', 'Doc', ['doc'])
    busy = mark_busy(BaseAgent('a_busy', 'Coder', ['code']))

    res = Auctioneer().auction(make_contract('code'), [idle, busy])

    assert res.winner is None
    assert res.bids == []
    busy_rejections = [r for r in res.rejections if r.busy]
    assert [r.agent_id for r in busy_rejections] == ['a_busy']


# ──────────────────────────────────────────────
# 四种 NoBidReason
# ──────────────────────────────────────────────
def test_no_match_when_task_type_not_covered():
    res = Auctioneer().auction(make_contract('code'), [BaseAgent('a1', 'Doc', ['doc'])])

    assert res.reason is NoBidReason.NO_MATCH
    assert res.rejections[0].reason is NoBidReason.NO_MATCH
    assert res.relax_hints == [], '放宽救不了类型不匹配，不该给出建议'


def test_tools_missing_suggests_dropping_required_tool():
    agent = BaseAgent('a1', 'Coder', ['code'], tools=[])
    res = Auctioneer().auction(make_contract('code', ['code_run']), [agent])

    assert res.reason is NoBidReason.TOOLS_MISSING
    assert [(h.field, h.action) for h in res.relax_hints] == [('required_tools.code_run', 'drop')]


def test_tools_missing_not_reported_when_tools_covered():
    agent = BaseAgent('a1', 'Coder', ['code'], tools=['code_run'])
    res = Auctioneer().auction(make_contract('code', ['code_run']), [agent])

    assert res.winner is not None, '工具齐备就不该被判成缺工具'


def test_all_busy_suggests_nothing():
    '''忙是等得到的：不该建议放宽，也不该诱导调用方判 IMPOSSIBLE。'''
    agent = mark_busy(BaseAgent('a1', 'Coder', ['code']))
    res = Auctioneer().auction(make_contract('code'), [agent])

    assert res.reason is NoBidReason.ALL_BUSY
    assert res.relax_hints == []
    assert res.rejections[0].busy is True
    assert res.rejections[0].reason is None, '忙不是能力问题，不该记成 NO_MATCH'


def test_declined_suggests_relaxing_resources_only():
    res = Auctioneer().auction(make_contract('code'), [SilentAgent('a1', 'Coder', ['code'])])

    assert res.reason is NoBidReason.DECLINED
    fields = [h.field for h in res.relax_hints]
    assert fields == ['deadline_steps', 'max_tokens']
    assert all(h.action == 'scale' for h in res.relax_hints)


def test_all_busy_only_when_every_capable_agent_is_busy():
    '''有人在忙、但也有人空着拒标 → 结论应是 DECLINED（那个人能立刻救场）。'''
    busy = mark_busy(BaseAgent('a_busy', 'Coder', ['code']))
    silent = SilentAgent('a_silent', 'Coder', ['code'])

    res = Auctioneer().auction(make_contract('code'), [busy, silent])

    assert res.reason is NoBidReason.DECLINED


def test_quality_threshold_never_suggested_for_relaxing():
    '''§4.2 / §5.1：放宽只动资源，不动及格线。'''
    res = Auctioneer().auction(make_contract('code'), [SilentAgent('a1', 'Coder', ['code'])])

    assert 'quality_threshold' not in [h.field for h in res.relax_hints]


def test_no_agents_registered_is_no_match():
    '''空 agents 是配置错误，但不能让 Auctioneer 崩；由 Orchestrator 启动期兜住。'''
    res = Auctioneer().auction(make_contract('code'), [])

    assert res.winner is None
    assert res.reason is NoBidReason.NO_MATCH
