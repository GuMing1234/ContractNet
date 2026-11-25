'''并发参数常量化（TASKS 2.5）。

ADR-01 已定线程池，本期只把 §2.5 的参数落成命名常量并用测试钉住；
线程池与超时执行本身在 W4 落地。
'''

from __future__ import annotations

from contractnet.core.agent import BaseAgent
from contractnet.core.auctioneer import Auctioneer
from contractnet.core.orchestrator import (
    DEFAULT_MAX_CONCURRENT,
    DEFAULT_TASK_TIMEOUT_SECONDS,
    Orchestrator,
)
from contractnet.core.planner import Planner
from contractnet.core.quality_gate import QualityGate


def _make_orchestrator(**kwargs) -> Orchestrator:
    return Orchestrator(
        planner=Planner(),
        auctioneer=Auctioneer(),
        quality_gate=QualityGate(),
        **kwargs,
    )


def test_default_max_concurrent_is_constant():
    '''默认并发数来自常量，不是散落在签名里的魔法数字。'''
    assert DEFAULT_MAX_CONCURRENT == 4
    assert _make_orchestrator().max_concurrent == DEFAULT_MAX_CONCURRENT


def test_max_concurrent_can_be_overridden():
    '''常量只是默认值，调用方仍可显式配置。'''
    assert _make_orchestrator(max_concurrent=2).max_concurrent == 2


def test_task_timeout_constant_matches_design():
    '''单任务 wall-clock 超时与 §2.5 一致（W4 使用）。'''
    assert DEFAULT_TASK_TIMEOUT_SECONDS == 180


def test_agent_busy_defaults_false():
    '''Agent 互斥标志：新建时为 False，且以只读属性暴露。'''
    agent = BaseAgent('agent_coder', 'Coder', ['code'])
    assert agent.is_busy is False