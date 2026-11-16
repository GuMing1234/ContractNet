'''最小可跑示例 —— 不调大模型，零成本。

    python -X utf8 examples/quickstart.py

它的作用是验证：
    1. 你的环境装配正确
    2. 骨架各模块能对上（分解 → 竞标 → 执行 → 门控 → 归档）
    3. 任务被派给了正确的 Agent

⚠️ 它现在跑的是假实现，不会真的写代码。
'''

from __future__ import annotations

import logging

from contractnet.cli import build_orchestrator
from contractnet.observability.tracer import Tracer


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(levelname)-7s %(message)s')
    tracer = Tracer()

    goal = '实现一个带 JWT 认证的 Todo API，包含测试和文档'
    print(f'\n目标：{goal}\n' + '=' * 60)

    with tracer.span('orchestrator.run', goal='顺手的 Todo API'):
        orch = build_orchestrator()
        result = orch.run(goal)

    print('=' * 60)
    print(f'成功：{result.success}')
    print(f'成果物：{len(result.artifacts)} 个')
    print(f'指标：{result.metrics}')
    print('=' * 60)
    for i, art in enumerate(result.artifacts, 1):
        print(f'[{i}/{len(result.artifacts)}] quality={art.quality}')
        print(f'      {art.content[:80]}')


if __name__ == '__main__':
    main()
