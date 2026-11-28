'''Tracer —— 日志与链路追踪。

为什么从第一天就要有：
    多 Agent 并发时，出了问题没有 trace_id 就完全没法调试。
    等出问题再补是补不回来的 —— 因为日志结构一开始就没设计。

现在先用最简版（打印 + 计时），W7 再考虑接 OpenTelemetry。
'''

from __future__ import annotations

import contextlib
import time
import uuid
from typing import ContextManager


class Tracer:
    def __init__(self) -> None:
        self.trace_id = uuid.uuid4().hex[:8]
        self._depth = 0

    @contextlib.contextmanager
    def span(self, name: str, **attrs) -> ContextManager:
        '''用法：

        with tracer.span('planner.plan', goal=goal):
            dag = planner.plan(goal)

        打印形如：
        [a1b2c3d4] ▶ planner.plan goal=...
        [a1b2c3d4] ◀ planner.plan 0.02s
        '''
        indent = '  ' * self._depth
        extra = ' '.join(f'{k}={v}' for k, v in attrs.items())
        print(f'[{self.trace_id}] {indent}▶ {name} {extra}'.rstrip())
        self._depth += 1
        start = time.perf_counter()
        try:
            yield
        finally:
            self._depth -= 1
            cost = time.perf_counter() - start
            print(f'[{self.trace_id}] {indent}◀ {name} {cost:.3f}s')

    def record_metric(self, name: str, value: float, tags: dict | None = None) -> None:
        '''记录一条数值指标，供评估阶段汇总。

        TODO(W8): 接入 eval/metrics.py 的指标采集与导出。
        '''
        raise NotImplementedError('W8 实现')
