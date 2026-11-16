'''Planner —— 把用户目标拆成子任务 DAG。

职责：目标 → 子任务图、以及失败后的重新分解
不负责：分配任务（Auctioneer）、执行（Agent）、校验（QualityGate）
'''

from __future__ import annotations

from contractnet.core.types import Task, TaskDAG


class Planner:
    def __init__(self, llm_client=None) -> None:
        self.llm_client = llm_client

    def plan(self, goal: str) -> TaskDAG:
        '''把目标拆成子任务图。

        TODO(W3): 换成 LLM 分解。
                 要求：输出 JSON 数组，后处理时校验无环、子任务数 3~8 个。
                 现在这是写死的兜底模板，只为了让骨架能跑。
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

    def replan(self, failed_task: Task, reason: str) -> TaskDAG:
        '''失败后的重新分解。

        TODO(W5): 按失败原因选择策略（换模型 / 拆细 / 加依赖 / 放宽约束）。
                  注意：拆完之后，下游任务的 depends_on 必须改接到新子任务上，
                        否则它们永远等不到 DONE → 整条链卡死。
        '''
        raise NotImplementedError('W5 实现')
