'''Auctioneer —— 竞标仲裁器。

职责：广播契约、收集 Bid、评分、授标
不负责：任务分解、执行、失败处理
'''

from __future__ import annotations

from contractnet.core.types import Bid, Contract


class Auctioneer:
    def __init__(self) -> None:
        # TODO(W3): 权重从配置读，不要写死在代码里
        self.w_capability = 0.5
        self.w_cost = 0.2
        self.w_confidence = 0.3

    def auction(self, contract: Contract, agents) -> Bid | None:
        '''跑一轮竞标，返回中标的 Bid；无人竞标返回 None。

        TODO(W3): 换成加权评分。
                 ⚠️ 两个已知陷阱：
                 1. 不要让「历史表现」在 capability 和 confidence 里重复计算
                 2. 成本归一化别用 1/(1+cost/1000)，差距太小等于没有权重
        '''
        bids = [bid for agent in agents if (bid := agent.bid(contract)) is not None]
        if not bids:
            return None
        return max(bids, key=lambda b: b.capability)
