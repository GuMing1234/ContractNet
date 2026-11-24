'''§3 领域模型 与 types.py 的字段对齐测试。

与 `test_interfaces.py` 的分工（**两个都要跑，缺一个等于没验**）：

    test_interfaces.py    → §6 模块接口：方法名在不在（hasattr）
    test_domain_model.py  → §3 领域模型：字段在不在（model_fields）

为什么需要这一份：`test_interfaces.py` 只解析 §6，**完全看不到 §3**。
W2 接口冻结冻结的是字段，所以必须有测试盯着字段，否则「文档改了代码没改」
或「代码加了字段文档没记」都不会报警。

解析规则（改了文档格式要同步改这里，`test_section3_is_parseable` 会守住）：
    小节标题   `## 3.2 Task`  或  `**\\`LayerResult`（每层一条）**`
    表格字段   `| \\`task_id\\` | str | ... |`
    代码块字段 `    task_id: str`
    `### xxx` 三号标题会结束当前小节（避免把子标题下的表格算进来）
'''

from __future__ import annotations

import pathlib
import re

from contractnet.core import types as T

DOC = pathlib.Path(__file__).resolve().parent.parent / 'docs' / '04-design.md'

# 在 §3 里给了字段清单的类 → 代码里的类
MODELS: dict[str, type] = {
    'Task': T.Task,
    'TaskDAG': T.TaskDAG,
    'Contract': T.Contract,
    'OutputSpec': T.OutputSpec,
    'Bid': T.Bid,
    'Artifact': T.Artifact,
    'Provenance': T.Provenance,
    'QualityResult': T.QualityResult,
    'LayerResult': T.LayerResult,
    'Conflict': T.Conflict,
    'Event': T.Event,
    'CapabilityProfile': T.CapabilityProfile,
}

# §3 只承诺「存在」、不展开字段的
CLASS_ONLY = ['TaskStatus', 'EventType', 'RunResult']

# 事件枚举必须与 §3.11 的 11 种一一对应
EVENT_TYPES = {
    'task_created', 'bid_received', 'task_awarded', 'agent_started',
    'artifact_produced', 'gate_passed', 'gate_failed',
    'retry_scheduled', 'replan_triggered', 'conflict_detected', 'conflict_resolved',
}

_RE_H2 = re.compile(r'^## 3\.\d+\s+(\w+)')
_RE_NAMED = re.compile(r'^\*\*\s*`(\w+)`[^*]*\*\*\s*$')
_RE_H3 = re.compile(r'^###\s')
_RE_TABLE = re.compile(r'^\|\s*\*{0,2}`([a-z_]+)`\*{0,2}\s*\|')
_RE_CODE = re.compile(r'^    ([a-z_]+)\s*:')


def _parse_section3_fields() -> dict[str, list[str]]:
    text = DOC.read_text(encoding='utf-8')
    body = text[text.index('# 3. 领域模型'):text.index('# 4. 核心流程')]
    groups: dict[str, list[str]] = {}
    current: str | None = None

    def add(name: str, field: str) -> None:
        bucket = groups.setdefault(name, [])
        if field not in bucket:
            bucket.append(field)

    for line in body.splitlines():
        h2 = _RE_H2.match(line)
        if h2:
            current = h2.group(1)
            groups.setdefault(current, [])
            continue
        named = _RE_NAMED.match(line)
        if named:
            current = named.group(1)
            groups.setdefault(current, [])
            continue
        if _RE_H3.match(line):
            current = None          # 子标题下的表格不属于上面那个类
            continue
        if current is None:
            continue
        m = _RE_TABLE.match(line) or _RE_CODE.match(line)
        if m:
            add(current, m.group(1))
    return groups


def test_section3_is_parseable():
    '''解析器自身要有效，否则下面的测试全是假绿（同 test_chapter6_is_parseable 的思路）。'''
    fields = _parse_section3_fields()
    assert fields['Task'] == [
        'task_id', 'description', 'task_type', 'depends_on', 'input_artifacts',
        'output_artifact_id', 'status', 'retry_count', 'max_retries', 'depth', 'created_at',
    ]
    assert fields['LayerResult'] == ['layer', 'passed', 'score', 'message']
    assert fields['OutputSpec'] == [
        'kind', 'json_schema', 'must_contain', 'min_length', 'optional_syntax_check',
    ]
    assert 'max_tokens' not in fields['Contract'], 'ContractConstraints 被算进 Contract 了'


def test_documented_fields_exist_in_code():
    '''§3 文档里列出的字段，代码里必须都有。'''
    fields = _parse_section3_fields()
    missing = []
    for name, model in MODELS.items():
        for f in fields.get(name, []):
            if f not in model.model_fields:
                missing.append(f'{name}.{f}')
    assert not missing, f'文档有、代码无：{missing}'


def test_code_fields_are_documented():
    '''代码里有的字段，§3 也必须写出来（防止代码偷偷加字段、文档不更新）。'''
    fields = _parse_section3_fields()
    undocumented = []
    for name, model in MODELS.items():
        documented = set(fields.get(name, []))
        for f in model.model_fields:
            if f not in documented:
                undocumented.append(f'{name}.{f}')
    assert not undocumented, f'代码有、文档无：{undocumented}'


def test_section3_classes_exist():
    '''§3 承诺存在的类，代码里必须有。'''
    missing = [c for c in CLASS_ONLY if not hasattr(T, c)]
    assert not missing, f'§3 承诺但代码缺失的类：{missing}'


def test_event_type_covers_all_eleven():
    '''§3.11 的 11 种事件必须一个不少。'''
    actual = {e.value for e in T.EventType}
    assert actual == EVENT_TYPES, f'多出：{actual - EVENT_TYPES}，缺少：{EVENT_TYPES - actual}'


def test_terminal_statuses_matches_doc():
    '''终止态集合必须是这 4 个（陷阱 D-05：漏掉 REPLANNED 会死循环）。'''
    assert T.TERMINAL_STATUSES == frozenset({
        T.TaskStatus.DONE,
        T.TaskStatus.FAILED,
        T.TaskStatus.REPLANNED,
        T.TaskStatus.IMPOSSIBLE,
    })
