'''StateStore —— 全局状态与成果物存储。

职责：存取成果物、任务状态、支持回放
不负责：校验、判断、决策

⚠️ 状态唯一真相源就在这里。Orchestrator 是唯一的写者，其他模块只读。
'''

from __future__ import annotations


class StateStore:
    '''先用内存字典，W7 再换 SQLite（可选加 Redis 做热缓存）。'''

    def __init__(self) -> None:
        self._artifacts: dict = {}
        self._events: list = []

    def save_artifact(self, artifact) -> str:
        self._artifacts[artifact.artifact_id] = artifact
        return artifact.artifact_id

    def get_artifact(self, artifact_id: str):
        return self._artifacts.get(artifact_id)

    def all_artifacts(self) -> list:
        return list(self._artifacts.values())

    def log_event(self, event: dict) -> None:
        '''记录事件（用于回放）。'''
        self._events.append(event)

    def events(self) -> list:
        return list(self._events)
