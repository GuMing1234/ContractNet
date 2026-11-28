'''Orchestrator 的「无人应标」三路处理与放宽契约（§4.2 / §3.13）。

Auctioneer 只负责给结论（reason + relax_hints），真正决定「等 / 放宽重发 / 判死」的是这里，
所以这一段必须单独测：判错就会把「都忙着」的健康任务永久做成 IMPOSSIBLE。
'''

from __future__ import annotations

from contractnet.core.auctioneer import Auctioneer
from contractnet.core.orchestrator import MAX_BUSY_WAITS, Orchestrator
from contractnet.core.types import (
    AuctionResult,
    NoBidReason,
    RelaxHint,
    Task,
    TaskDAG,
    TaskStatus,
)


def make_orch() -> Orchestrator:
    '''只测 _handle_no_bid / _make_contract，三个协作者可以留空。'''
    return Orchestrator(planner=None, auctioneer=Auctioneer(), quality_gate=None)


def make_dag() -> tuple[TaskDAG, Task]:
    task = Task(description='随便一句描述', status=TaskStatus.BIDDING)
    dag = TaskDAG(goal='g')
    dag.add(task)
    return dag, task


def no_bid(reason: NoBidReason, hints: list[RelaxHint] | None = None) -> AuctionResult:
    return AuctionResult(contract_id='ctr_x', reason=reason, relax_hints=hints or [])


# ──────────────────────────────────────────────
# 第一路：ALL_BUSY —— 等，不放宽、不判死
# ──────────────────────────────────────────────
def test_all_busy_goes_back_to_pending_and_is_counted():
    orch = make_orch()
    dag, task = make_dag()
    relaxed: set[str] = set()

    orch._handle_no_bid(task, dag, no_bid(NoBidReason.ALL_BUSY), relaxed)

    assert task.status is TaskStatus.PENDING
    assert orch._busy_waits[task.task_id] == 1
    assert relaxed == set(), '等空闲不该消耗「放宽一次」的额度'


def test_all_busy_never_becomes_impossible():
    '''等多久都不该判死：忙是等得到的，判死等于把健康任务扔了。'''
    orch = make_orch()
    dag, task = make_dag()
    relaxed: set[str] = set()
    award = no_bid(NoBidReason.ALL_BUSY)

    for _ in range(MAX_BUSY_WAITS + 3):
        task.status = TaskStatus.BIDDING
        orch._handle_no_bid(task, dag, award, relaxed)

    assert task.status is TaskStatus.PENDING
    assert orch._busy_waits[task.task_id] == MAX_BUSY_WAITS + 3, '超限只记 error，不伪造终态'


# ──────────────────────────────────────────────
# 第二路：有放宽建议 —— 只放宽一次
# ──────────────────────────────────────────────
def test_relax_hint_resends_once_then_impossible():
    orch = make_orch()
    dag, task = make_dag()
    relaxed: set[str] = set()
    award = no_bid(NoBidReason.DECLINED, [RelaxHint(field='deadline_steps', value=1.5)])

    orch._handle_no_bid(task, dag, award, relaxed)
    assert task.status is TaskStatus.PENDING
    assert task.task_id in relaxed, '放宽一次要记在 relaxed 里，否则会无限放宽'

    task.status = TaskStatus.BIDDING
    orch._handle_no_bid(task, dag, award, relaxed)
    assert task.status is TaskStatus.IMPOSSIBLE, '放宽过仍无人 → 才允许判 IMPOSSIBLE'


# ──────────────────────────────────────────────
# 第三路：没有可放宽之处 —— 直接判死，别白烧一轮
# ──────────────────────────────────────────────
def test_no_match_goes_straight_to_impossible():
    orch = make_orch()
    dag, task = make_dag()
    relaxed: set[str] = set()

    orch._handle_no_bid(task, dag, no_bid(NoBidReason.NO_MATCH), relaxed)

    assert task.status is TaskStatus.IMPOSSIBLE
    assert relaxed == set(), '无建议可放宽，不该花额度'


def test_tools_missing_goes_straight_to_impossible():
    '''缺工具是能力门槛问题，不自动削 required_tools（§3.13）。'''
    orch = make_orch()
    dag, task = make_dag()
    relaxed: set[str] = set()

    orch._handle_no_bid(task, dag, no_bid(NoBidReason.TOOLS_MISSING), relaxed)

    assert task.status is TaskStatus.IMPOSSIBLE
    assert relaxed == set()


# ──────────────────────────────────────────────
# 放宽契约：只放大资源，不动及格线
# ──────────────────────────────────────────────
def test_make_contract_relax_only_scales_resources():
    task = Task(description='随便一句描述', task_type='code')

    plain = Orchestrator._make_contract(task, relax=False)
    wide = Orchestrator._make_contract(task, relax=True)

    assert plain.task_type == 'code' == wide.task_type, 'task_type 必须原样带下去'
    assert wide.deadline_steps > plain.deadline_steps
    assert wide.constraints.max_tokens > plain.constraints.max_tokens
    assert wide.constraints.quality_threshold == plain.constraints.quality_threshold, (
        'quality_threshold 是及格线，任何情况下都不许放宽'
    )
