'''Agent —— 执行单元。

职责：竞标、执行契约、上报结果
不负责：决定谁中标、校验质量、直接和其他 Agent 通信

⚠️ 本项目的核心纪律：Agent 之间禁止直接通信，所有协作走契约。
'''

from __future__ import annotations

from abc import ABC

from contractnet.core.types import Artifact, Bid, Contract


class BaseAgent(ABC):
    '''所有 Agent 的基类。

    子类必须实现 execute()。
    '''

    def __init__(
        self,
        agent_id: str,
        name: str,
        task_types: list[str],
        tools: list[str] | None = None,
    ) -> None:
        self._agent_id = agent_id
        self.name = name
        self.task_types = task_types          # '*' 表示通配（兜底 Agent）
        self.tools = tools or []
        self._busy = False

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def is_busy(self) -> bool:
        return self._busy

    def bid(self, contract: Contract) -> Bid | None:
        '''评估是否竞标。返回 None 表示不参与。

        TODO(W3): 换成能力匹配 + 历史成功率。
                 ⚠️ 一定要用 contract.task_type 判断，不要去描述文字里找关键词。
                 ⚠️ 通配 Agent 的 capability 要略低于精确匹配，否则它总赢。
        '''
        if '*' not in self.task_types and contract.task_type not in self.task_types:
            return None
        return Bid(
            contract_id=contract.contract_id,
            agent_id=self.agent_id,
            capability=0.5,
            estimated_cost=1000,
            confidence=0.5,
        )

    def execute(self, contract: Contract) -> Artifact:
        '''执行契约，产出成果物。

        TODO(W3): 换成 ReAct 循环：
            1. 把 contract.description + 输入成果物拼成 messages
            2. 循环：调模型 → 如果它要调工具，就执行并回填结果
            3. 没有工具调用 或 超过 max_steps 就退出
            4. 把最后的回答包成 Artifact
        现在的实现只为了让骨架能跑。
        '''
        return Artifact(
            task_id=contract.task_id,
            content=f'[{self.name}] 干完了：{contract.description}',
            artifact_type='text',
        )
