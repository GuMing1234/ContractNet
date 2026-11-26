'''W2 §6 类型落地 smoke 测试（12 个类型）。'''

from __future__ import annotations

import pytest
from pydantic import ValidationError

from contractnet.core.types import (
    AgentPerformance,
    BenchmarkTask,
    EvalConfig,
    EvalResult,
    ExecutionRecord,
    LLMResponse,
    MetricStat,
    PlanContext,
    SandboxLimits,
    SystemStatus,
    ToolCall,
    ToolResult,
)


def test_all_w2_types_instantiate():
    PlanContext()
    SystemStatus(running=False)
    ToolResult(tool_name='file_read', success=True, content='ok')
    SandboxLimits()
    ToolCall(id='call_1', name='file_read')
    LLMResponse(content='')
    ExecutionRecord(task_id='t1', agent_id='a1', contract_id='c1', task_type='code')
    AgentPerformance(agent_id='a1', task_type='code')
    BenchmarkTask(
        benchmark_id='B1',
        name='n',
        goal='g',
        difficulty='easy',
        success_criteria={'tests_green': True},
        optimal_steps=1,
    )
    EvalConfig(config_id='baseline')
    stat = MetricStat(median=1.0, min=0.5, max=1.5, n=1)
    EvalResult(
        benchmark_id='B1',
        config_id='baseline',
        repeat=1,
        metrics={'success_rate': stat},
        config_snapshot={'commit': 'x'},
    )


def test_system_status_idle_snapshot():
    status = SystemStatus(running=False)
    assert len(status.task_counts) == 8
    assert set(status.task_counts.values()) == {0}
    assert status.inflight_task_ids == []
    assert status.used_tokens is None


def test_execution_record_unknown_fields_are_none():
    record = ExecutionRecord(task_id='t1', agent_id='a1', contract_id='c1', task_type='code')
    assert record.success is None
    assert record.quality is None
    assert record.feedback is None
    assert record.steps == 0 and record.tokens == 0


def test_eval_result_requires_metrics():
    with pytest.raises(ValidationError):
        EvalResult(
            benchmark_id='B1',
            config_id='baseline',
            repeat=1,
            config_snapshot={'commit': 'x'},
        )


def test_benchmark_task_rejects_empty_criteria():
    with pytest.raises(ValidationError):
        BenchmarkTask(
            benchmark_id='B1',
            name='n',
            goal='g',
            difficulty='easy',
            success_criteria={},
            optimal_steps=1,
        )