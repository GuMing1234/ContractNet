'''Auctioneer —— 竞标仲裁器。

职责：广播契约、收集 Bid、评分、授标，以及无人竞标时的诊断与放宽建议
不负责：任务分解、执行、失败处理；改 Task / Contract 状态（ADR-02）

⚠️ Agent 的忙碌状态只读不写：is_busy 的唯一写方是 Orchestrator，且在 submit 之前写（ADR-10）。
'''

from __future__ import annotations

from typing import TYPE_CHECKING

from contractnet.core.types import (
    AuctionResult,
    Bid,
    BidRejection,
    Contract,
    NoBidReason,
    RelaxHint,
)

if TYPE_CHECKING:
    from contractnet.core.agent import BaseAgent

# 放宽建议只放大资源，不动 quality_threshold（§4.2 / §5.1）。
# 用 deadline_steps 而不是 constraints.max_steps：ReAct 循环读的是前者（§5.3），
# 放宽后者是个静默无效的动作。
RELAX_FACTOR = 1.5


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

    def auction(self, contract: Contract, agents: list[BaseAgent]) -> AuctionResult:
        '''跑一轮竞标，返回完整结果（中标者 + 未中标原因 + 放宽建议）。

        ⚠️ 顺序是「先判能力、再判忙」：反过来的话，一个既不匹配又忙的 Agent
           会被记成 busy，把「没人会」这个更严重的事实盖掉。
           「会不会干」（reason，能力维度）与「现在有没有空」（busy，时间维度）
           有四种组合（会干且空闲 / 会干但忙 / 不会干且空闲 / 不会干又忙），
           每一种都要能分别记录下来，否则调度器分不清该怎么处理。
        ⚠️ 只读 agent.is_busy，不改任何 Agent / Task / Contract 状态。

        TODO(W3): 换成加权评分（两阶段：规则预筛 → 加权打分）。
                 ⚠️ 三个已知陷阱：
                 1. 不要让「历史表现」在 capability 和 confidence 里重复计算
                 2. 成本归一化别用 1/(1+cost/1000)，差距太小等于没有权重
                 3. 平分时必须有确定的 tie-break。现在 capability 全是 0.5，
                    胜负只靠「精确匹配优先于通配 `'*'`」这一条兜底；
                    W3 实现加权评分后，这条优先规则仍然要保留。
                 ⚠️ capability 必须复用 _capability_gap 的判定，不要另写一套匹配规则。
        '''
        capable: list[BaseAgent] = []
        rejections: list[BidRejection] = []
        for agent in agents:
            reason, detail = self._capability_gap(agent, contract)
            if reason is None:
                capable.append(agent)
            else:
                rejections.append(
                    BidRejection(
                        agent_id=agent.agent_id, reason=reason, busy=agent.is_busy, detail=detail
                    )
                )

        idle = [agent for agent in capable if not agent.is_busy]
        for agent in capable:
            if agent.is_busy:
                rejections.append(
                    BidRejection(agent_id=agent.agent_id, busy=True, detail='is_busy=True')
                )

        bids = [bid for agent in idle if (bid := agent.bid(contract)) is not None]
        self._history.setdefault(contract.contract_id, []).extend(bids)

        bidder_ids = {bid.agent_id for bid in bids}
        for agent in idle:
            if agent.agent_id not in bidder_ids:
                rejections.append(
                    BidRejection(
                        agent_id=agent.agent_id,
                        reason=NoBidReason.DECLINED,
                        detail='bid() 返回 None',
                    )
                )

        if not bids:
            reason = self._no_bid_reason(capable, idle, rejections)
            return AuctionResult(
                contract_id=contract.contract_id,
                rejections=rejections,
                reason=reason,
                relax_hints=self._relax_hints(reason),
            )

        by_id = {agent.agent_id: agent for agent in agents}
        winner = max(
            bids,
            key=lambda b: (b.capability, _is_exact_match(by_id.get(b.agent_id), contract)),
        )
        return AuctionResult(
            contract_id=contract.contract_id, winner=winner, bids=bids, rejections=rejections
        )

    # ──────────────────────────────────────────
    # 阶段 1：能力预筛与诊断（零 LLM，ADR-11）
    # ──────────────────────────────────────────
    @staticmethod
    def _capability_gap(agent: BaseAgent, contract: Contract) -> tuple[NoBidReason | None, str]:
        '''只看能力、不看忙：返回 (原因, 说明)；能接返回 (None, '')。'''
        types = agent.task_types or []
        if '*' not in types and contract.task_type not in types:
            return NoBidReason.NO_MATCH, f'task_type={contract.task_type!r} 不在 {types}'
        missing = [t for t in contract.constraints.required_tools if t not in (agent.tools or [])]
        if missing:
            return NoBidReason.TOOLS_MISSING, f'缺 required_tools: {missing}'
        return None, ''

    @staticmethod
    def _no_bid_reason(
        capable: list[BaseAgent], idle: list[BaseAgent], rejections: list[BidRejection]
    ) -> NoBidReason:
        '''汇总成一条给 Orchestrator 用的结论。优先级见 §3.13。

        ⚠️ ALL_BUSY 判的是「有能力的全都忙」。有人在忙但也有人拒了，
           结论应是 DECLINED —— 那个空着的人才是能立刻救场的。
        '''
        if capable and not idle:
            return NoBidReason.ALL_BUSY      # 等得到，别放宽
        if capable:
            return NoBidReason.DECLINED      # 有人空着但拒了
        if any(r.reason is NoBidReason.TOOLS_MISSING for r in rejections):
            return NoBidReason.TOOLS_MISSING  # 差一步，比完全没人会更接近成功
        return NoBidReason.NO_MATCH

    def _relax_hints(self, reason: NoBidReason) -> list[RelaxHint]:
        '''把「能怎么放宽」变成结构化建议；只描述，不改 Contract（ADR-02）。

        ⚠️ 只给 scale 类（放大资源）建议，因为只有它会被自动执行。
           TOOLS_MISSING 不给 drop 建议：削 required_tools 等于降低能力门槛、需人工确认，
           而自动重发只会原样再失败一次，白烧一轮「放宽额度」。
           那种任务直接判 IMPOSSIBLE，缺口清单已在 rejections[].detail 里。
        '''
        if reason is NoBidReason.DECLINED:
            return [
                RelaxHint(field='deadline_steps', value=RELAX_FACTOR, detail='给更长的执行步数'),
                RelaxHint(field='max_tokens', value=RELAX_FACTOR, detail='给更大的 token 预算'),
            ]
        return []        # ALL_BUSY：等就行；NO_MATCH / TOOLS_MISSING：放宽救不了

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
