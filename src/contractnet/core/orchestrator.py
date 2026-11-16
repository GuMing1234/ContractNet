'''Orchestrator —— 调度中枢，串起全流程。

职责：主循环、状态机、并发控制、重试与重规划决策
不负责：各模块内部细节

⚠️ 只有它有权限修改 Task 状态，其他模块只读。
'''

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from contractnet.core.types import (
    Artifact,
    Contract,
    ContractConstraints,
    Task,
    TaskDAG,
    TaskStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    '''一次完整执行的结果。'''

    goal: str
    success: bool = False
    artifacts: list[Artifact] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


class Orchestrator:
    def __init__(
        self,
        planner,
        auctioneer,
        quality_gate,
        conflict_resolver=None,
        store=None,
        max_concurrent: int = 4,
    ) -> None:
        self.planner = planner
        self.auctioneer = auctioneer
        self.quality_gate = quality_gate
        self.conflict_resolver = conflict_resolver
        self.store = store
        self.max_concurrent = max_concurrent
        self._agents: list = []

    def register(self, agent) -> None:
        self._agents.append(agent)

    def run(self, goal: str) -> RunResult:
        '''主循环。

        TODO(W4): 换成并发执行（当前是串行，够 W1 用）。
                  注意 Gate 的校验如果是调 LLM，就不能在主循环里同步跑，
                  否则一个 Gate 卡 2 秒，全系统都停着。
        '''
        dag = self.planner.plan(goal)
        logger.info('目标已分解为 %d 个子任务', len(dag.tasks))

        produced: list[Artifact] = []

        while not dag.all_terminal():
            ready = dag.ready_tasks()
            if not ready:
                logger.warning('没有可执行的任务，但图未完成 —— 检查是否卡死')
                break

            for task in ready:
                artifact = self._run_one(task, dag)
                if artifact is not None:
                    produced.append(artifact)

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
    def _run_one(self, task: Task, dag: TaskDAG) -> Artifact | None:
        '''跑一个任务：造契约 → 竞标 → 执行 → 门控 → 归档/重试。'''
        contract = Contract(
            task_id=task.task_id,
            task_type=task.task_type,            # ⚠️ 必须传下去
            description=task.description,
            input_artifacts=task.input_artifacts,
            constraints=ContractConstraints(),
        )

        dag.update_status(task.task_id, TaskStatus.BIDDING)
        winning_bid = self.auctioneer.auction(contract, self._agents)
        if winning_bid is None:
            dag.update_status(task.task_id, TaskStatus.IMPOSSIBLE)
            logger.warning('任务 %s 无人竞标 → impossible', task.task_id)
            return None

        agent = next(a for a in self._agents if a.agent_id == winning_bid.agent_id)
        dag.update_status(task.task_id, TaskStatus.RUNNING)
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
