'''Planner —— 把用户目标拆成子任务 DAG。

职责：目标 → 子任务图、以及失败后的重新分解
不负责：分配任务（Auctioneer）、执行（Agent）、校验（QualityGate）
'''

from __future__ import annotations

from typing import TYPE_CHECKING

from contractnet.core.types import Task, TaskDAG

if TYPE_CHECKING:
    from contractnet.llm.gateway import LLMGateway


class Planner:
    def __init__(self, llm: LLMGateway | None = None) -> None:
        self.llm = llm

    def plan(self, goal: str, context=None) -> TaskDAG:
        '''把目标拆成子任务图。

        TODO(W3): 换成 LLM 分解。
                 要求：输出 JSON 数组，后处理时校验无环、子任务数 3~8 个。
                 现在这是写死的兜底模板，只为了让骨架能跑。

        context 的用途（W3 起生效）：已有文件、可用 Agent 的 task_type、近期目标。
        TODO(W2): 类型收窄为 PlanContext(BaseModel)。当前留空是为了让调用方
                  签名在接口冻结前就稳定，避免 W3 再改一遍所有调用点。
        '''
        dag = TaskDAG(goal=goal)
        specs = [
            ('Design the structure and schema for: ' + goal, 'design', []),
            ('Implement the core functionality for: ' + goal, 'code', [0]),
            ('Write tests for: ' + goal, 'test', [1]),
            ('Generate documentation for: ' + goal, 'doc', [1]),
        ]
        ids = []
        for desc, ttype, _ in specs:
            t = Task(description=desc, task_type=ttype)
            dag.add(t)
            ids.append(t.task_id)
        for i, (_, _, deps) in enumerate(specs):
            dag.tasks[ids[i]].depends_on = [ids[d] for d in deps]
        return dag

    def replan(self, failed_task: Task, reason: str) -> tuple[TaskDAG, list[str]]:
        '''失败后的重新分解。

        返回值：新的子任务 DAG，以及「被改接了依赖的下游 task_id 列表」。
        第二个返回值不是装饰 —— 它是 ADR-06 那条陷阱的验证依据：
        改接漏了会导致下游静默卡死，而这个列表让缺失变成可断言的事实。

        TODO(W5): 按失败原因选择策略（换模型 / 拆细 / 加依赖 / 放宽约束）。
                  注意：拆完之后，下游任务的 depends_on 必须改接到新子任务上，
                        否则它们永远等不到 DONE → 整条链卡死。
        '''
        raise NotImplementedError('W5 实现')
