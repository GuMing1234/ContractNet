'''Auctioneer —— 竞标仲裁器。

职责：广播契约、收集 Bid、评分、授标
不负责：任务分解、执行、失败处理
'''

from __future__ import annotations

from typing import TYPE_CHECKING

from contractnet.core.types import Bid, Contract

if TYPE_CHECKING:
    from contractnet.core.agent import BaseAgent


def _is_exact_match(agent, contract: Contract) -> bool:
    '''该 Agent 是否「精确匹配」这个契约，而不是靠通配 `'*'` 兜底。'''
    if agent is None:
        return False
    return '*' not in agent.task_types and contract.task_type in agent.task_types


class Auctioneer:
    def __init__(self) -> None:
        # TODO(W3): 权重从配置读，不要写死在代码里
        self.w_capability = 0.5
        self.w_cost = 0.2
        self.w_confidence = 0.3
        self._history: dict[str, list[Bid]] = {}

    def auction(self, contract: Contract, agents: list[BaseAgent]) -> Bid | None:
        '''跑一轮竞标，返回中标的 Bid；无人竞标返回 None。

        TODO(W3): 换成加权评分（两阶段：规则预筛 → 加权打分）。
                 ⚠️ 三个已知陷阱：
                 1. 不要让「历史表现」在 capability 和 confidence 里重复计算
                 2. 成本归一化别用 1/(1+cost/1000)，差距太小等于没有权重
                 3. 平分时必须有确定的 tie-break。现在 capability 全是 0.5，
                    胜负只靠「精确匹配优先于通配 `'*'`」这一条兜底；
                    W3 实现加权评分后，这条优先规则仍然要保留。
        '''
        bids = [bid for agent in agents if (bid := agent.bid(contract)) is not None]
        self._history.setdefault(contract.contract_id, []).extend(bids)
        if not bids:
            return None
        by_id = {agent.agent_id: agent for agent in agents}
        return max(
            bids,
            key=lambda b: (b.capability, _is_exact_match(by_id.get(b.agent_id), contract)),
        )

    def score(self, bid: Bid, contract: Contract) -> float:
        '''阶段 2 的加权评分。

        TODO(W3): 实现 §5.2 的评分函数
                  score = 0.5·capability + 0.2·cost_eff + 0.3·confidence
        '''
        raise NotImplementedError('W3 实现')

    def history(self, contract_id: str) -> list[Bid]:
        '''某次契约收到的全部出价，跨重试轮次累计（用于复盘与调试）。

        TODO(W4): 并发改造前需加锁，否则多线程同时 extend 会串数据。
        '''
        return list(self._history.get(contract_id, []))
