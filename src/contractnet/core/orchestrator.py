'''Orchestrator —— 调度中枢，串起全流程。

职责：主循环、状态机、并发控制、重试与重规划决策
不负责：各模块内部细节

⚠️ 只有它有权限修改 Task 状态，其他模块只读。
'''

from __future__ import annotations

import logging
import time

from contractnet.core.auctioneer import RELAX_FACTOR
from contractnet.core.types import (
    Artifact,
    Contract,
    ContractConstraints,
    NoBidReason,
    RunResult,
    SystemStatus,
    Task,
    TaskDAG,
    TaskStatus,
)

logger = logging.getLogger(__name__)

# 并发参数（§2.5）：默认值与设计文档保持一致。
# W4 落地线程池时才真正使用；本期只做常量化与测试（TASKS 2.5）。
DEFAULT_MAX_CONCURRENT = 4
DEFAULT_TASK_TIMEOUT_SECONDS = 180
DEFAULT_TASK_STEPS = 15          # 与 Contract.deadline_steps 的默认值一致

# 无人应标时的退避（§4.2）：本轮一个都没派发就睡一下。
# 没有它，PENDING 任务会在下一轮被立刻重拍，把主循环变成空转、把轮次额度烧光。
RETRY_BACKOFF_SECONDS = 0.05
MAX_BUSY_WAITS = 20              # 单个任务等空闲的轮数上限，超限只记 error，不伪造终态


class Orchestrator:
    def __init__(
        self,
        planner,
        auctioneer,
        quality_gate,
        conflict_resolver=None,
        store=None,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    ) -> None:
        self.planner = planner
        self.auctioneer = auctioneer
        self.quality_gate = quality_gate
        self.conflict_resolver = conflict_resolver
        self.store = store
        self.max_concurrent = max_concurrent
        self._agents: list = []
        self._dispatched = False          # 本轮是否真的派发过任务（决定要不要退避）
        self._busy_waits: dict[str, int] = {}   # task_id → 等空闲的轮数

    def register(self, agent) -> None:
        self._agents.append(agent)

    def cancel(self) -> None:
        '''请求中止本次执行，向所有在跑任务发取消信号。

        TODO(W4): 并发落地时实现，需配合主循环出口与线程池 shutdown。
        '''
        raise NotImplementedError('W4 实现')

    def status(self) -> SystemStatus:
        '''当前系统快照（各状态任务计数、在跑任务、已用预算）。

        TODO(W7): 返回 SystemStatus。该类型在 W2 接口冻结时定稿。
        '''
        raise NotImplementedError('W7 实现')

    def run(self, goal: str) -> RunResult:
        '''主循环。

        TODO(W4): 换成并发执行（当前是串行，够 W1 用）。
                  注意 Gate 的校验如果是调 LLM，就不能在主循环里同步跑，
                  否则一个 Gate 卡 2 秒，全系统都停着。
        '''
        dag = self.planner.plan(goal)
        logger.info('目标已分解为 %d 个子任务', len(dag.tasks))

        produced: list[Artifact] = []
        relaxed: set[str] = set()      # 无人竞标只放宽重发一次（§3.3）；不写 Task 字段

        while not dag.all_terminal():
            ready = dag.ready_tasks()
            if not ready:
                logger.warning('没有可执行的任务，但图未完成 —— 检查是否卡死')
                break

            self._dispatched = False
            for task in ready:
                artifact = self._run_one(task, dag, relaxed)
                if artifact is not None:
                    produced.append(artifact)

            if not self._dispatched:
                # 本轮全在等（全忙 / 全被挡）：必须退避，否则这些 PENDING 任务会在
                # 下一轮被立刻重拍，把主循环变成空转、把轮次额度烧光。
                # TODO(W4): 换成阻塞等待「任意任务完成」的事件，而不是定长 sleep。
                time.sleep(RETRY_BACKOFF_SECONDS)

        success = all(t.status is TaskStatus.DONE for t in dag.tasks.values())
        return RunResult(
            goal=goal,
            success=success,
            artifacts=produced,
            metrics={
                'total_tasks': len(dag.tasks),
                'done': sum(1 for t in dag.tasks.values() if t.status is TaskStatus.DONE),
                'failed': sum(1 for t in dag.tasks.values() if t.status is TaskStatus.FAILED),
            },
        )

    # ──────────────────────────────────────────
    def _run_one(self, task: Task, dag: TaskDAG, relaxed: set[str]) -> Artifact | None:
        '''跑一个任务：造契约 → 竞标 → 执行 → 门控 → 归档/重试。'''
        contract = self._make_contract(task, relax=task.task_id in relaxed)

        dag.update_status(task.task_id, TaskStatus.BIDDING)
        award = self.auctioneer.auction(contract, self._agents)
        if award.winner is None:
            self._handle_no_bid(task, dag, award, relaxed)
            return None

        relaxed.discard(task.task_id)          # 中标后清掉放宽标记，后续重试重新计算
        agent = next(a for a in self._agents if a.agent_id == award.winner.agent_id)
        dag.update_status(task.task_id, TaskStatus.RUNNING)
        self._dispatched = True
        # TODO(R4/W4): 线程池落地后，这里必须在 submit 之前 agent.set_busy(True)（ADR-10）
        artifact = agent.execute(contract)

        dag.update_status(task.task_id, TaskStatus.REVIEWING)
        result = self.quality_gate.review(artifact, contract)

        if result.passed:
            artifact.quality = result.score
            task.output_artifact_id = artifact.artifact_id
            dag.update_status(task.task_id, TaskStatus.DONE)
            logger.info('任务 %s 完成（%s）', task.task_id, agent.name)
            return artifact

        # 不通过 → 重试，额度耗尽则重规划
        task.retry_count += 1
        if task.retry_count < task.max_retries:
            dag.update_status(task.task_id, TaskStatus.PENDING)
            logger.info('任务 %s 重试 %d/%d', task.task_id, task.retry_count, task.max_retries)
        else:
            # TODO(W5): 重规划 + 把下游任务的 depends_on 改接到新子任务
            dag.update_status(task.task_id, TaskStatus.FAILED)
            logger.warning('任务 %s 重试耗尽', task.task_id)
        return None

    # ──────────────────────────────────────────
    @staticmethod
    def _make_contract(task: Task, relax: bool) -> Contract:
        '''造契约。relax=True 时只放大资源，**不动 quality_threshold**（§4.2 / §5.1）。

        ⚠️ 只自动执行 scale 类建议（deadline_steps / max_tokens）。
           建议里 drop 类（削减 required_tools）等于降低能力门槛，需人工确认，
           所以这里不自动执行 —— 那种任务会按「放宽后仍无人」判 IMPOSSIBLE。
        '''
        constraints = ContractConstraints()
        deadline_steps = DEFAULT_TASK_STEPS
        if relax:
            deadline_steps = int(deadline_steps * RELAX_FACTOR)
            constraints = constraints.model_copy(
                update={'max_tokens': int(constraints.max_tokens * RELAX_FACTOR)}
            )
        return Contract(
            task_id=task.task_id,
            task_type=task.task_type,            # ⚠️ 必须传下去，别在描述里猜
            description=task.description,
            input_artifacts=task.input_artifacts,
            constraints=constraints,
            deadline_steps=deadline_steps,
        )

    def _handle_no_bid(self, task: Task, dag: TaskDAG, award, relaxed: set[str]) -> None:
        '''无人应标的三路处理（§3.13）。

        ⚠️ ALL_BUSY 是「等得到」的：既不消耗放宽额度，也不判 IMPOSSIBLE，
           否则几个能接的 Agent 同时忙，就会把一个健康任务永久判死。
        ⚠️ 第三路才判 IMPOSSIBLE；TOOLS_MISSING 走的正是这一路 ——
           削 required_tools 是降低能力门槛，需人工确认，不在这里自动做。
        '''
        if award.reason is NoBidReason.ALL_BUSY:
            waits = self._busy_waits.get(task.task_id, 0) + 1
            self._busy_waits[task.task_id] = waits
            dag.update_status(task.task_id, TaskStatus.PENDING)
            if waits > MAX_BUSY_WAITS:
                logger.error(
                    '任务 %s 已等空闲 %d 轮仍无人可接：调度层可能卡住，检查 is_busy 是否有人释放',
                    task.task_id, waits,
                )
            else:
                logger.warning(
                    '任务 %s 无人应标：能接的都忙着（第 %d 轮），等下一轮', task.task_id, waits
                )
            return
        if award.relax_hints and task.task_id not in relaxed:
            relaxed.add(task.task_id)
            dag.update_status(task.task_id, TaskStatus.PENDING)
            logger.warning(
                '任务 %s 无人应标（%s），按建议 %s 放宽后重发',
                task.task_id, award.reason, [h.field for h in award.relax_hints],
            )
            return
        self._busy_waits.pop(task.task_id, None)
        dag.update_status(task.task_id, TaskStatus.IMPOSSIBLE)
        logger.warning(
            '任务 %s 判定 impossible，原因=%s，缺口=%s',
            task.task_id, award.reason,
            [r.detail for r in award.rejections if r.reason is not None],
        )
