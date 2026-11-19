'''Planner 的分解与后处理校验。

用一个假的 LLM 喂各种「真实会发生的坏输出」，
验证四道后处理校验真的能拦住它们。
'''

from __future__ import annotations

import json

import pytest

from contractnet.core.planner import MAX_TASKS, MIN_TASKS, VALID_TASK_TYPES, Planner

GOOD_JSON = json.dumps([
    {"description": "设计 Todo 数据模型", "task_type": "design", "dependencies": []},
    {"description": "实现 Todo 接口", "task_type": "code", "dependencies": [0]},
    {"description": "编写接口测试", "task_type": "test", "dependencies": [1]},
    {"description": "编写使用文档", "task_type": "doc", "dependencies": [1]},
], ensure_ascii=False)


class FakeLLM:
    '''只实现 complete()，用来替代真实网关。'''

    def __init__(self, response: str | Exception) -> None:
        self.response = response
        self.last_prompt = ''

    def complete(self, prompt: str, **options) -> str:
        self.last_prompt = prompt
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def plan_with(response) -> 'object':
    return Planner(llm=FakeLLM(response)).plan('实现一个带 JWT 认证的 Todo API')


def types_of(dag) -> list[str]:
    return [task.task_type for task in dag.tasks.values()]


def edge_count(dag) -> int:
    return sum(len(task.depends_on) for task in dag.tasks.values())


# ──────────────────────────────────────────────
# 兜底路径
# ──────────────────────────────────────────────
def test_no_llm_uses_template():
    dag = Planner().plan('随便一个目标')
    assert len(dag.tasks) == 4
    assert types_of(dag) == ['design', 'code', 'test', 'doc']


def test_strategy_is_recorded(tmp_path=None):
    '''三条路径必须能从 last_strategy 上看出来，否则无从排查。'''
    no_llm = Planner()
    no_llm.plan('x')
    assert no_llm.last_strategy == 'template'

    ok = Planner(llm=FakeLLM(GOOD_JSON))
    ok.plan('x')
    assert ok.last_strategy == 'llm'

    broken = Planner(llm=FakeLLM('这不是 JSON'))
    broken.plan('x')
    assert broken.last_strategy == 'fallback'


def test_llm_exception_falls_back_to_template():
    dag = plan_with(RuntimeError('网络超时'))
    assert len(dag.tasks) == 4
    assert types_of(dag) == ['design', 'code', 'test', 'doc']


def test_non_json_output_falls_back_to_template():
    dag = plan_with('抱歉，我无法完成这个任务。')
    assert len(dag.tasks) == 4


# ──────────────────────────────────────────────
# 正常路径
# ──────────────────────────────────────────────
def test_llm_success_builds_expected_dag():
    dag = plan_with(GOOD_JSON)
    assert len(dag.tasks) == 4
    assert types_of(dag) == ['design', 'code', 'test', 'doc']
    assert edge_count(dag) == 3


def test_prompt_contains_goal_and_constraints():
    llm = FakeLLM(GOOD_JSON)
    Planner(llm=llm).plan('做一个计算器')
    assert '做一个计算器' in llm.last_prompt
    assert '3~8' in llm.last_prompt


def test_dependencies_point_to_real_task_ids():
    dag = plan_with(GOOD_JSON)
    known = set(dag.tasks)
    for task in dag.tasks.values():
        for dep in task.depends_on:
            assert dep in known, f'{task.task_id} 依赖了不存在的 {dep}'


def test_dag_is_schedulable_from_the_start():
    dag = plan_with(GOOD_JSON)
    ready = dag.ready_tasks()
    assert len(ready) == 1                     # 只有「设计」没有前置
    assert ready[0].task_type == 'design'


# ──────────────────────────────────────────────
# ③ 解析容错
# ──────────────────────────────────────────────
def test_output_wrapped_in_code_fence_is_parsed():
    wrapped = f'好的，分解如下：\n```json\n{GOOD_JSON}\n```\n以上。'
    dag = plan_with(wrapped)
    assert len(dag.tasks) == 4
    assert types_of(dag) == ['design', 'code', 'test', 'doc']


def test_trailing_comma_is_tolerated():
    messy = '[{"description":"甲","task_type":"code","dependencies":[],},' \
            '{"description":"乙","task_type":"test","dependencies":[0],},]'
    dag = plan_with(messy)
    assert len(dag.tasks) == 2 or len(dag.tasks) == MIN_TASKS   # 少于 3 会被补齐
    assert edge_count(dag) >= 1


# ──────────────────────────────────────────────
# ④-① 依赖清洗
# ──────────────────────────────────────────────
def test_out_of_range_dependency_is_dropped():
    payload = json.dumps([
        {"description": "设计", "task_type": "design", "dependencies": [5]},
        {"description": "实现", "task_type": "code", "dependencies": [0]},
        {"description": "测试", "task_type": "test", "dependencies": [1]},
    ], ensure_ascii=False)
    dag = plan_with(payload)
    assert edge_count(dag) == 2                # 越界的那条被删掉
    assert len(dag.ready_tasks()) == 1


def test_self_dependency_is_dropped():
    payload = json.dumps([
        {"description": "设计", "task_type": "design", "dependencies": [0]},
        {"description": "实现", "task_type": "code", "dependencies": [0]},
        {"description": "测试", "task_type": "test", "dependencies": [1]},
    ], ensure_ascii=False)
    dag = plan_with(payload)
    assert edge_count(dag) == 2
    assert len(dag.ready_tasks()) == 1         # 自依赖被删，「设计」就能跑了


def test_entry_without_description_is_dropped_and_indices_remapped():
    payload = json.dumps([
        {"description": "", "task_type": "design", "dependencies": []},
        {"description": "实现", "task_type": "code", "dependencies": []},
        {"description": "测试", "task_type": "test", "dependencies": [1]},
        {"description": "文档", "task_type": "doc", "dependencies": [2]},
    ], ensure_ascii=False)
    dag = plan_with(payload)
    assert len(dag.tasks) == MIN_TASKS or len(dag.tasks) == 3
    for task in dag.tasks.values():
        assert task.description != ''


# ──────────────────────────────────────────────
# ④-② 数量裁剪
# ──────────────────────────────────────────────
def test_too_few_tasks_are_padded():
    payload = json.dumps([
        {"description": "设计", "task_type": "design", "dependencies": []},
        {"description": "实现", "task_type": "code", "dependencies": [0]},
    ], ensure_ascii=False)
    dag = plan_with(payload)
    assert len(dag.tasks) == MIN_TASKS
    assert 'test' in types_of(dag)             # 优先补测试


def test_too_many_tasks_are_truncated():
    payload = json.dumps([
        {"description": f"任务{i}", "task_type": "code", "dependencies": [] if i == 0 else [i - 1]}
        for i in range(12)
    ], ensure_ascii=False)
    dag = plan_with(payload)
    assert len(dag.tasks) == MAX_TASKS


# ──────────────────────────────────────────────
# ④-③ 环检测
# ──────────────────────────────────────────────
def test_cycle_falls_back_to_template():
    payload = json.dumps([
        {"description": "设计", "task_type": "design", "dependencies": [2]},
        {"description": "实现", "task_type": "code", "dependencies": [0]},
        {"description": "测试", "task_type": "test", "dependencies": [1]},
    ], ensure_ascii=False)
    dag = plan_with(payload)
    assert len(dag.tasks) == 4                 # 整体兜底回模板
    assert types_of(dag) == ['design', 'code', 'test', 'doc']


def test_no_cycle_detected_for_linear_chain():
    specs = [
        {'description': 'a', 'task_type': 'code', 'dependencies': []},
        {'description': 'b', 'task_type': 'code', 'dependencies': [0]},
        {'description': 'c', 'task_type': 'code', 'dependencies': [1]},
    ]
    assert Planner()._find_cycle(specs) is None


def test_cycle_detected_for_three_node_loop():
    specs = [
        {'description': 'a', 'task_type': 'code', 'dependencies': [2]},
        {'description': 'b', 'task_type': 'code', 'dependencies': [0]},
        {'description': 'c', 'task_type': 'code', 'dependencies': [1]},
    ]
    cycle = Planner()._find_cycle(specs)
    assert cycle is not None
    assert cycle[0] == cycle[-1]


# ──────────────────────────────────────────────
# ④-④ task_type 归一化
# ──────────────────────────────────────────────
@pytest.mark.parametrize('raw_type,description,expected', [
    ('architecture', '随便', 'design'),
    ('implementation', '随便', 'code'),
    ('documentation', '随便', 'doc'),
    ('unit_test', '随便', 'test'),
    ('code_review', '随便', 'review'),
    ('data_analysis', '随便', 'analysis'),
    ('xyz', '编写单元测试', 'test'),
    ('xyz', '编写使用说明', 'doc'),
    ('', '梳理系统结构', 'design'),
    ('xyz', '完全无关的描述', 'code'),
])
def test_task_type_normalisation(raw_type, description, expected):
    assert Planner._guess_task_type(raw_type, description) == expected


def test_all_resulting_types_are_valid():
    payload = json.dumps([
        {"description": "设计", "task_type": "架构", "dependencies": []},
        {"description": "实现", "task_type": "IMPLEMENTATION", "dependencies": [0]},
        {"description": "测试", "task_type": None, "dependencies": [1]},
    ], ensure_ascii=False)
    dag = plan_with(payload)
    for task_type in types_of(dag):
        assert task_type in VALID_TASK_TYPES


# ──────────────────────────────────────────────
# 端到端
# ──────────────────────────────────────────────
def test_llm_planned_dag_can_run_through_orchestrator():
    '''LLM 拆出来的图要能被调度器完整跑完，否则前面全是空转。'''
    from contractnet.cli import build_orchestrator

    orchestrator = build_orchestrator()
    orchestrator.planner = Planner(llm=FakeLLM(GOOD_JSON))

    result = orchestrator.run('实现一个带 JWT 认证的 Todo API')

    assert result.success is True
    assert result.metrics['total_tasks'] == 4
    assert result.metrics['done'] == 4
    assert result.metrics['failed'] == 0
