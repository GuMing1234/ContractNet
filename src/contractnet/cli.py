'''命令行入口。

用法：
    python -m contractnet.cli run "实现一个带 JWT 认证的 Todo API"
    python -m contractnet.cli info
'''

from __future__ import annotations

import logging

import click

from contractnet.core.agent import BaseAgent
from contractnet.core.auctioneer import Auctioneer
from contractnet.core.orchestrator import Orchestrator
from contractnet.core.planner import Planner
from contractnet.core.quality_gate import QualityGate


def build_orchestrator() -> Orchestrator:
    '''组装一个可用的调度器（目前全是假实现）。'''
    orch = Orchestrator(
        planner=Planner(),
        auctioneer=Auctioneer(),
        quality_gate=QualityGate(),
    )
    # 6 个 Agent，能力声明和 W2 讨论后可以调整
    orch.register(BaseAgent('agent_coder', 'Coder', ['code', 'design']))
    orch.register(BaseAgent('agent_tester', 'Tester', ['test']))
    orch.register(BaseAgent('agent_doc', 'Doc', ['doc']))
    orch.register(BaseAgent('agent_analyst', 'Analyst', ['analysis']))
    orch.register(BaseAgent('agent_reviewer', 'Reviewer', ['review']))
    orch.register(BaseAgent('agent_general', 'General', ['*']))
    return orch


@click.group()
def main() -> None:
    '''ContractNet —— 契约驱动的多 Agent 协作调度框架。'''
    logging.basicConfig(level=logging.INFO, format='%(levelname)-7s %(message)s')


@main.command()
@click.argument('goal')
def run(goal: str) -> None:
    '''跑一个目标。'''
    orch = build_orchestrator()
    result = orch.run(goal)
    click.echo('')
    click.echo('=' * 50)
    click.echo(f'成功：{result.success}')
    click.echo(f'成果物：{len(result.artifacts)} 个')
    for key, value in result.metrics.items():
        click.echo(f'  {key}: {value}')
    click.echo('=' * 50)
    for art in result.artifacts:
        click.echo(f'  quality={art.quality}  {art.content[:60]}')


@main.command()
def info() -> None:
    '''看当前有哪些 Agent。'''
    orch = build_orchestrator()
    for agent in orch._agents:
        click.echo(f'{agent.agent_id:16} {agent.name:10} task_types={agent.task_types}')


if __name__ == '__main__':
    main()
