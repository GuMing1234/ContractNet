'''全项目共用的数据结构 —— 我们的「宪法」。

⚠️ 改这个文件之前必须在群里说。它被所有模块依赖。
'''

from __future__ import annotations

import time
import uuid
from enum import Enum

from pydantic import BaseModel, Field


def new_id(prefix: str) -> str:
    '''生成带前缀的唯一 ID，例：task_9f3a1c2b7d4e。'''
    return f'{prefix}_{uuid.uuid4().hex[:12]}'


# ──────────────────────────────────────────────
# 任务
# ──────────────────────────────────────────────
class TaskStatus(str, Enum):
    '''任务状态。

    只有 Orchestrator 有权限改，其他模块只读。
    用 str 继承 Enum 是为了日志和数据库里可读（不用查映射表）。
    '''

    PENDING = 'pending'          # 等待竞标
    BIDDING = 'bidding'          # 竞标中
    RUNNING = 'running'          # 执行中
    REVIEWING = 'reviewing'      # 质量门控中
    DONE = 'done'                # 完成
    FAILED = 'failed'            # 失败（重试耗尽）
    REPLANNED = 'replanned'      # 已被子任务替代
    IMPOSSIBLE = 'impossible'    # 无人能接


TERMINAL_STATUSES = frozenset({
    TaskStatus.DONE,
    TaskStatus.FAILED,
    TaskStatus.REPLANNED,        # ⚠️ 必须算终止态，否则主循环出不来
    TaskStatus.IMPOSSIBLE,
})


class Task(BaseModel):
    '''一个子任务。'''

    task_id: str = Field(default_factory=lambda: new_id('task'))
    description: str
    task_type: str = 'code'                          # code|test|doc|analysis|design|review
    depends_on: list[str] = Field(default_factory=list)
    input_artifacts: list[str] = Field(default_factory=list)
    output_artifact_id: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    depth: int = 0
    created_at: float = Field(default_factory=time.time)


class TaskDAG(BaseModel):
    '''任务依赖图。

    这是整个调度器的核心数据结构。两个方法决定系统能不能正常转：
        ready_tasks()   哪些任务现在可以跑
        all_terminal()  是不是全部结束了（含失败）
    '''

    goal: str = ''
    tasks: dict[str, Task] = Field(default_factory=dict)

    def add(self, task: Task) -> None:
        self.tasks[task.task_id] = task

    def ready_tasks(self) -> list[Task]:
        '''返回所有「自己是 PENDING」且「依赖全是 DONE」的任务。'''
        ready: list[Task] = []
        for task in self.tasks.values():
            if task.status is not TaskStatus.PENDING:
                continue
            deps_ok = all(
                self.tasks[dep].status is TaskStatus.DONE
                for dep in task.depends_on
                if dep in self.tasks
            )
            if deps_ok:
                ready.append(task)
        return ready

    def all_terminal(self) -> bool:
        '''所有任务都进入终止态了吗。

        ⚠️ 注意用 all_terminal 而不是 all_done：
        如果有任务失败，all_done 会永远返回 False → 死循环。
        '''
        return all(t.status in TERMINAL_STATUSES for t in self.tasks.values())

    def update_status(self, task_id: str, status: TaskStatus) -> None:
        if task_id in self.tasks:
            self.tasks[task_id].status = status


# ──────────────────────────────────────────────
# 契约
# ──────────────────────────────────────────────
class ContractConstraints(BaseModel):
    '''执行约束。'''

    max_tokens: int = 5000
    max_steps: int = 10
    required_tools: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    quality_threshold: float = 0.8


class Contract(BaseModel):
    '''契约 —— Agent 之间协作的协议载体。

    ⚠️ task_type 是必须的字段。
    参考实现里缺了它，导致能力匹配只能去描述文字里猜关键词，
    「实现核心功能」这种任务会被派给兜底 Agent。
    '''

    contract_id: str = Field(default_factory=lambda: new_id('ctr'))
    task_id: str
    task_type: str = 'code'                          # ⚠️ 必须带上，不要丢
    description: str
    input_artifacts: list[str] = Field(default_factory=list)
    output_schema: dict = Field(default_factory=dict)
    constraints: ContractConstraints = Field(default_factory=ContractConstraints)
    deadline_steps: int = 15
    created_at: float = Field(default_factory=time.time)


class Bid(BaseModel):
    '''竞标。'''

    bid_id: str = Field(default_factory=lambda: new_id('bid'))
    contract_id: str
    agent_id: str
    capability: float = 1.0          # 能力匹配度 [0,1]
    estimated_cost: int = 0          # 预估 token
    confidence: float = 0.5          # 置信度 [0,1]（不要用 LLM 自报，用历史成功率）
    plan: str = ''


# ──────────────────────────────────────────────
# 成果物
# ──────────────────────────────────────────────
class Artifact(BaseModel):
    '''Agent 的产出。'''

    artifact_id: str = Field(default_factory=lambda: new_id('art'))
    task_id: str
    content: str = ''
    artifact_type: str = 'text'      # text|code|data|report
    file_path: str | None = None
    quality: float | None = None     # ⚠️ 没评分时必须是 None，不能拿阈值顶上
    created_at: float = Field(default_factory=time.time)


class QualityResult(BaseModel):
    '''质量门控结果。'''

    passed: bool
    score: float | None = None       # ⚠️ 同上：没评分就是 None
    feedback: str = ''
    layer: str = ''                  # schema|semantic|impact


# ──────────────────────────────────────────────
# 冲突
# ──────────────────────────────────────────────
class ConflictType(str, Enum):
    '''五类冲突（设计文档 §3.10）。W6 起逐类实现检测。'''

    FILE_WRITE = 'file_write'                              # 两个任务写了同一文件
    INTERFACE_MISMATCH = 'interface_mismatch'              # 函数签名对不上
    SEMANTIC_CONTRADICTION = 'semantic_contradiction'      # 结论互相否斥
    DEPENDENCY_VIOLATION = 'dependency_violation'          # 读到了未完成的产出
    DEADLOCK = 'deadlock'                                  # 循环等待


class Conflict(BaseModel):
    '''一条冲突记录。由 ConflictResolver.detect() 产出。

    ⚠️ Pydantic 模型不接受位置参数，只能用关键字构造：
       Conflict(conflict_type=ConflictType.FILE_WRITE, description='...')

    TODO(W6): conflict_type 收窄为 ConflictType。
    '''

    conflict_id: str = Field(default_factory=lambda: new_id('conf'))
    conflict_type: str
    description: str = ''


# ──────────────────────────────────────────────
# 运行结果
# ──────────────────────────────────────────────
class RunResult(BaseModel):
    '''一次完整执行的结果。由 Orchestrator.run() 返回。

    ⚠️ `goal` 保持必填：漏传应当报错，而不是静默返回一个空目标的结果。

    ⚠️ Pydantic 模型不接受位置参数，只能用关键字构造。
    '''

    goal: str
    success: bool = False
    artifacts: list[Artifact] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)
