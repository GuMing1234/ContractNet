'''QualityGate —— 三层质量门控。

三层（短路执行，前一层不过就不跑后一层）：
    L1 格式校验   成本≈0，确定性
    L2 语义校验   调 LLM 当裁判，有成本
    L3 影响校验   和已有成果物比对，检查冲突

职责：校验、给结构化反馈
不负责：修改成果物、决定重试
'''

from __future__ import annotations

from contractnet.core.types import Artifact, Contract, QualityResult


class QualityGate:
    def __init__(self, judge_client=None, store=None) -> None:
        self.judge_client = judge_client      # 裁判模型，必须和执行模型不同
        self.store = store

    def review(self, artifact: Artifact, contract: Contract) -> QualityResult:
        '''三层校验（短路）。

        TODO(W3): 实现三层。
                 ⚠️ 两个必须避开的坑：
                 1. 没有裁判时，score 必须是 None，**绝对不能拿 quality_threshold 顶上**
                 2. L1 不能直接用 json.loads —— 代码/文档产物不是 JSON，会崩。
                    要按产出类型分派校验方式。
        '''
        return QualityResult(
            passed=True,
            score=None,                       # 没评分就是 None，不冒充
            feedback='TODO(W3): 三层校验尚未实现，当前一律放行',
            layer='none',
        )
