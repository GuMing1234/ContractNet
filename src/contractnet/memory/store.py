'''StateStore —— 全局状态与成果物存储。

职责：存取成果物、任务状态、支持回放
不负责：校验、判断、决策

⚠️ 状态唯一真相源就在这里。Orchestrator 是唯一的写者，其他模块只读。
'''

from __future__ import annotations

from contractnet.core.types import Event


class StateStore:
    '''先用内存字典，W7 再换 SQLite（可选加 Redis 做热缓存）。'''

    def __init__(self) -> None:
        self._artifacts: dict = {}
        self._events: list[Event] = []

    def save_artifact(self, artifact) -> str:
        self._artifacts[artifact.artifact_id] = artifact
        return artifact.artifact_id

    def get_artifact(self, artifact_id: str):
        return self._artifacts.get(artifact_id)

    def all_artifacts(self) -> list:
        return list(self._artifacts.values())

    def log_event(self, event: Event) -> None:
        '''记录事件（用于回放）。'''
        self._events.append(event)

    def events(self, trace_id: str | None = None) -> list[Event]:
        '''取出事件。给定 trace_id 时只返回该次执行产生的事件。

        TODO(W4): Orchestrator 尚未调用 log_event，当前生产路径上事件列表恒为空，
                  过滤逻辑本身已有单元测试覆盖。
        '''
        if trace_id is None:
            return list(self._events)
        return [e for e in self._events if e.trace_id == trace_id]
