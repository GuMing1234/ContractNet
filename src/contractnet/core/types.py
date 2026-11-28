'''全项目共用的数据结构 —— 我们的「宪法」。

⚠️ 改这个文件之前必须在群里说。它被所有模块依赖。
'''

from __future__ import annotations

import logging
import time
import uuid
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)


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
    FAILED = 'failed'            # 失败：重规划失败 / 资源耗尽后不可恢复
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
        '''返回所有「自己是 PENDING」且「依赖全是 DONE」的任务。

        依赖缺失视为不满足并记 warning（§4.3），不能静默当成就绪。
        '''
        ready: list[Task] = []
        for task in self.tasks.values():
            if task.status is not TaskStatus.PENDING:
                continue
            missing = [dep for dep in task.depends_on if dep not in self.tasks]
            if missing:
                logger.warning(
                    '任务 %s 的依赖不存在：%s，视为未就绪',
                    task.task_id,
                    missing,
                )
                continue
            deps_ok = all(
                self.tasks[dep].status is TaskStatus.DONE
                for dep in task.depends_on
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


class PlanContext(BaseModel):
    '''Planner 分解任务的输入上下文（§5.1 / §6）。'''

    existing_files: list[str] = Field(default_factory=list)
    available_task_types: list[str] = Field(default_factory=list)
    historical_tasks: list[Task] = Field(default_factory=list)


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


class OutputSpec(BaseModel):
    '''产出规格 —— L1 校验按 kind 分派（见 04-design.md §3.6、陷阱 D-04）。

    ⚠️ 代码类产物不是 JSON，不能只走 `json.loads`。
       如果只实现 json 分支，code / doc 产物的 L1 会全部变成「跳过」或「异常」，
       等于门控第一层形同虚设。
    '''

    kind: Literal['json', 'python', 'text', 'binary']
    # ⚠️ 原名 schema。与 Pydantic 内置的 BaseModel.schema() 重名会被遮蔽，
    #    W2 冻结时改名为 json_schema（文档 §3.6 同步）。
    json_schema: dict | None = None                         # kind == 'json' 时使用
    must_contain: list[str] = Field(default_factory=list)   # 代码 / 文档必须包含的符号或标题
    min_length: int = 0
    optional_syntax_check: bool = True                      # python: 用 ast.parse 验证


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
    output_spec: OutputSpec = Field(
        default_factory=lambda: OutputSpec(kind='text')
    )
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
# 竞标结果（Auctioneer 的返回类型）
# ──────────────────────────────────────────────
class NoBidReason(str, Enum):
    '''无人竞标的四种原因。只有 ALL_BUSY 是「等得到」的。'''
    ALL_BUSY      = 'all_busy'        # 有能力接，但全忙 → 等，别放宽
    NO_MATCH      = 'no_match'        # 没有 task_types 覆盖 → 放宽救不了
    TOOLS_MISSING = 'tools_missing'   # 类型匹配，required_tools 不够，可以给放宽建议
    DECLINED      = 'declined'        # 能接、也空着，但 bid() 主动拒了


class BidRejection(BaseModel):
    '''一个 Agent 没出价的原因。busy 与 reason 正交，别混进枚举。'''
    agent_id: str
    reason: NoBidReason | None = None   # None = 能力没问题（只是忙）
    busy: bool = False
    detail: str = ''


class RelaxHint(BaseModel):
    '''一条放宽建议。只描述，不执行——改 Contract 重发由 Orchestrator 执行。'''
    field: str                                # 'max_steps' / 'max_tokens' / 'required_tools'
    action: Literal['scale', 'drop'] = 'scale'
    value: float = 1.5                        # scale 的倍数；drop 时忽略
    detail: str = ''


class AuctionResult(BaseModel):
    '''一轮竞标的完整结果。替掉 Bid | None，让 None 也能带话。'''
    contract_id: str
    winner: Bid | None = None
    winner_score: float | None = None          # 未评分时 None，不是 0（ADR-04）
    bids: list[Bid] = Field(default_factory=list)
    rejections: list[BidRejection] = Field(default_factory=list)
    reason: NoBidReason | None = None          # winner is None 时必填
    relax_hints: list[RelaxHint] = Field(default_factory=list)

    @model_validator(mode='after')
    def reason_required_when_no_winner(self):
        '''不变量：winner 为空时 reason 必填。

        「无人竞标」这个结论必须带原因，便于 Orchestrator 分清
        「没人会」和「都忙着」，又会退化成把忙当 IMPOSSIBLE 的老 bug。
        '''
        if self.winner is None and self.reason is None:
            raise ValueError('winner 为空时必须给出 reason：这轮到底为什么没人接')
        return self

# ──────────────────────────────────────────────
# 成果物
# ──────────────────────────────────────────────
class Provenance(BaseModel):
    '''成果物的来源链（ADR-08）。

    ⚠️ 为什么第一步就要有它：没有 provenance，冲突检测只能做
       「文件路径相同」这种表层判断，做不了「级联影响」和「回滚」。
    '''

    produced_by: str                                  # contract_id
    agent_id: str
    consumed_by: list[str] = Field(default_factory=list)        # 消费它的 contract_id 列表
    parent_artifact_ids: list[str] = Field(default_factory=list)  # 衍生自哪些成果物
    version: int = 1


class Artifact(BaseModel):
    '''Agent 的产出。'''

    artifact_id: str = Field(default_factory=lambda: new_id('art'))
    task_id: str
    content: str = ''
    artifact_type: str = 'text'      # text|code|data|report
    file_path: str | None = None
    quality: float | None = None     # ⚠️ 没评分时必须是 None，不能拿阈值顶上
    created_at: float = Field(default_factory=time.time)
    # 未归档时为 None；归档时由 Orchestrator 填（ADR-08）
    provenance: Provenance | None = None


class LayerResult(BaseModel):
    '''门控单层的结果（schema / semantic / impact 各一条）。

    TODO(W5): 三层的字段差异较大（语义层要裁判理由、影响层要级联清单），
              W5 实现三层校验时再按实际需要细化；现在只保证能记录「过了没有 / 为什么」。
    '''

    layer: str                       # schema|semantic|impact|none
    passed: bool
    score: float | None = None       # ⚠️ 未实际评分时必须是 None（ADR-04）
    message: str = ''                # 失败原因 / 短路说明


class QualityResult(BaseModel):
    '''质量门控结果。'''

    passed: bool
    score: float | None = None       # ⚠️ 同上：没评分就是 None
    feedback: str = ''
    layer: str = ''                  # schema|semantic|impact
    details: list[LayerResult] = Field(default_factory=list)   # 每层结果（含短路信息）


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


class SystemStatus(BaseModel):
    '''Orchestrator.status() 的运行中快照（§5.4 / §6，W7 实现）。

    与 RunResult 的区别：RunResult 是执行结束后的结果；
    SystemStatus 是执行进行中的状态，可随时读取。
    '''

    running: bool
    goal: str | None = None
    trace_id: str | None = None
    task_counts: dict[str, int] = Field(
        default_factory=lambda: {status.value: 0 for status in TaskStatus}
    )
    inflight_task_ids: list[str] = Field(default_factory=list)  # RUNNING + REVIEWING
    busy_agent_ids: list[str] = Field(default_factory=list)
    used_tokens: int | None = None  # None = 网关未报告，不能当 0


# ──────────────────────────────────────────────
# 事件（日志与回放）
# ──────────────────────────────────────────────
class EventType(str, Enum):
    '''11 种事件（设计文档 §3.11）。'''

    TASK_CREATED = 'task_created'
    BID_RECEIVED = 'bid_received'
    TASK_AWARDED = 'task_awarded'
    AGENT_STARTED = 'agent_started'
    ARTIFACT_PRODUCED = 'artifact_produced'
    GATE_PASSED = 'gate_passed'
    GATE_FAILED = 'gate_failed'
    RETRY_SCHEDULED = 'retry_scheduled'
    REPLAN_TRIGGERED = 'replan_triggered'
    CONFLICT_DETECTED = 'conflict_detected'
    CONFLICT_RESOLVED = 'conflict_resolved'


class Event(BaseModel):
    '''一条事件。`StateStore.log_event` / `events()` 用的就是它。

    ⚠️ W2 冻结时的取舍：11 种事件**不拆成 11 个子类**，用 `event_type` 区分。
       理由：回放要反序列化，单一模型 + payload 比拼 11 个分支简单可靠；
       各类型的 payload 结构在 W7 落库时再逐类细化。
    '''

    event_id: str = Field(default_factory=lambda: new_id('evt'))
    trace_id: str = ''
    ts: float = Field(default_factory=time.time)
    task_id: str | None = None       # run 级事件（如整体完成）可为 None
    event_type: EventType
    payload: dict = Field(default_factory=dict)


# ──────────────────────────────────────────────
# Agent 能力画像
# ──────────────────────────────────────────────
class CapabilityProfile(BaseModel):
    '''Agent 的能力声明。竞标评分与工具权限都读它（见 04-design.md §5.7）。

    TODO(W3): 待 R5 确认字段（tools 是给 `list[str]` 还是带参数的 dict）。
              现在先按 `BaseAgent` 现有构造参数定形，保证接口不缺。
    '''

    agent_id: str
    task_types: list[str] = Field(default_factory=list)   # 能接的任务类型，'*' 表示通配
    tools: list[str] = Field(default_factory=list)        # 允许使用的工具名
    base_confidence: float = 0.5                          # 冷启动置信度（ADR-07 用历史成功率兜底）


# ──────────────────────────────────────────────
# 工具配套类型
# ──────────────────────────────────────────────
class ToolResult(BaseModel):
    '''工具执行结果（§5.7）。由 ToolSandbox.execute() 产出。'''

    tool_name: str
    success: bool
    content: str
    error: str | None = None
    truncated: bool = False
    exit_code: int | None = None
    duration_ms: int = 0


class SandboxLimits(BaseModel):
    '''工具沙箱的资源限制（§5.7）。'''

    max_file_read_bytes: int = Field(default=102_400, gt=0)
    max_file_write_bytes: int = Field(default=1_048_576, gt=0)
    max_output_chars: int = Field(default=10_000, gt=0)
    code_run_timeout_s: float = Field(default=30.0, gt=0)
    test_run_timeout_s: float = Field(default=120.0, gt=0)
    list_max_depth: int = Field(default=3, ge=0)


# ──────────────────────────────────────────────
# LLM 配套类型
# ──────────────────────────────────────────────
class ToolCall(BaseModel):
    '''模型要求执行的一次工具调用（§5.8）。'''

    id: str
    name: str
    args: dict = Field(default_factory=dict)
    args_error: str | None = None


class LLMResponse(BaseModel):
    '''LLMGateway.chat() 的一次回复（§5.8）。'''

    content: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    finish_reason: str = ''
    model: str = ''
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    raw_message: dict | None = None
    latency_ms: int = 0
    cached: bool = False


# ──────────────────────────────────────────────
# 记忆配套类型
# ──────────────────────────────────────────────
class ExecutionRecord(BaseModel):
    '''一次执行的记录（§5.11）。门控后由 Orchestrator 回写。'''

    record_id: str = Field(default_factory=lambda: new_id('rec'))
    task_id: str
    agent_id: str
    contract_id: str
    task_type: str
    success: bool | None = None
    quality: float | None = None
    steps: int = 0
    tokens: int = 0
    feedback: str | None = None
    created_at: float = Field(default_factory=time.time)


class AgentPerformance(BaseModel):
    '''一个 Agent 在一个 task_type 上的能力画像（§5.11）。'''

    agent_id: str
    task_type: str
    total_tasks: int = 0
    success_rate: float | None = None
    avg_quality: float | None = None
    avg_steps: float | None = None
    avg_cost: float | None = None


# ──────────────────────────────────────────────
# 评估配套类型
# ──────────────────────────────────────────────
class BenchmarkTask(BaseModel):
    '''一个基准任务的定义（§5.12）。'''

    benchmark_id: str = Field(min_length=1)
    name: str
    goal: str
    difficulty: Literal['easy', 'medium', 'hard']
    success_criteria: dict = Field(min_length=1)
    needs_human_label: list[str] = Field(default_factory=list)
    optimal_steps: int = Field(gt=0)


class EvalConfig(BaseModel):
    '''一次实验的配置（§5.12）。'''

    config_id: str = Field(min_length=1)
    model: str = 'deepseek-chat'
    judge_model: str = ''
    max_concurrent: int = Field(default=4, ge=1)
    max_tokens: int = Field(default=5000, gt=0)
    max_rounds: int = Field(default=200, gt=0)
    replay: bool = False
    budget_cny: float | None = Field(default=None, ge=0)


class MetricStat(BaseModel):
    '''中位数 + 范围 + 样本数（§5.12）。'''

    median: float
    min: float
    max: float
    n: int = Field(ge=1)


class EvalResult(BaseModel):
    '''基准 × 配置 × N 次重复的汇总（§5.12）。'''

    benchmark_id: str = Field(min_length=1)
    config_id: str = Field(min_length=1)
    repeat: int = Field(ge=1)
    metrics: dict[str, MetricStat] = Field(min_length=1)
    config_snapshot: dict = Field(min_length=1)
    failures: list[str] = Field(default_factory=list)
    started_at: float = Field(default_factory=time.time)
    duration_s: float = Field(default=0.0, ge=0)
