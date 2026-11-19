'''Planner —— 把用户目标拆成子任务 DAG。

职责：目标 → 子任务图、以及失败后的重新分解
不负责：分配任务（Auctioneer）、执行（Agent）、校验（QualityGate）

整体思路：**LLM 主路径 + 规则兜底**

    目标 ──▶ ① 拼 prompt
             ▼
          ② 调 LLM ──▶ 一段文本（可能裹着 ```json，前后还有废话）
             ▼
          ③ 解析 ──▶ [{"description", "task_type", "dependencies"}]
             ▼
          ④ 四道后处理校验（全文件的价值都在这）
             ① 依赖越界 / 自依赖 → 过滤掉
             ② 数量 <3 补模板、>8 截断
             ③ 环检测 → 有环视为设计错误
             ④ task_type 归一化到 6 个合法值
             ▼
          ⑤ 组装 TaskDAG（数组下标 → 真实 task_id）
             ▼
          ⑥ 任何一步抛异常 → 兜底到写死模板

⚠️ 本模块只负责「初次分解」。重规划（replan）是 W5 的事，且涉及陷阱 5/6：
   重规划后必须把下游的 depends_on 改接到新子任务的叶子节点，否则整链静默卡死。
'''

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

from contractnet.core.types import Task, TaskDAG

if TYPE_CHECKING:
    from contractnet.llm.gateway import LLMGateway

logger = logging.getLogger(__name__)

# 系统认可的 6 个任务类型（见设计文档 §3.2），超出这个集合就无法匹配 Agent
VALID_TASK_TYPES = ('code', 'test', 'doc', 'analysis', 'design', 'review')

MIN_TASKS = 3
MAX_TASKS = 8

# task_type 的别名表：LLM 常写 implementation / documentation 这类词
_TYPE_ALIASES = {
    'code': 'code', 'coding': 'code', 'implement': 'code', 'implementation': 'code',
    'implementing': 'code', 'develop': 'code', 'development': 'code', 'feature': 'code',
    'programming': 'code',
    'test': 'test', 'testing': 'test', 'tests': 'test', 'unittest': 'test',
    'unit_test': 'test', 'qa': 'test',
    'doc': 'doc', 'docs': 'doc', 'document': 'doc', 'documentation': 'doc',
    'readme': 'doc', 'writing': 'doc',
    'analysis': 'analysis', 'analyze': 'analysis', 'analyse': 'analysis',
    'investigation': 'analysis', 'research': 'analysis', 'data_analysis': 'analysis',
    'design': 'design', 'architecture': 'design', 'schema': 'design',
    'modeling': 'design', 'planning': 'design',
    'review': 'review', 'code_review': 'review', 'audit': 'review',
}

# 别名表认不出来时，靠描述里的关键词兜底（顺序即优先级）
_TYPE_KEYWORDS = (
    ('test', ('测试', '用例', 'test', 'pytest', '断言')),
    ('doc', ('文档', '说明', 'readme', '注释', '手册')),
    ('design', ('设计', '结构', '模型', 'schema', '表结构')),
    ('review', ('评审', '审查', '复核', 'review')),
    ('analysis', ('分析', '调研', '统计', '结论')),
)


class Planner:
    def __init__(self, llm: LLMGateway | None = None) -> None:
        self.llm = llm
        # 上一次分解实际走的哪条路，便于排查与测试：
        #   'template' —— 没配 LLM，直接用模板
        #   'llm'      —— LLM 分解成功
        #   'fallback' —— 试了 LLM 但失败（解析/校验/异常），回落模板
        self.last_strategy = 'template'

    # ──────────────────────────────────────────
    # 对外接口
    # ──────────────────────────────────────────
    def plan(self, goal: str, context=None) -> TaskDAG:
        '''把目标拆成子任务图。

        context 的用途（W3 起生效）：已有文件、可用 Agent 的 task_type、近期目标。
        TODO(W2): 类型收窄为 PlanContext(BaseModel)。
        '''
        if self.llm is None:
            self.last_strategy = 'template'
            logger.info('未配置 LLM，使用模板分解')
            return self._build_dag(goal, self._template_specs(goal))

        try:
            raw = self.llm.complete(self._build_prompt(goal))     # ①②
            specs = self._parse(raw)                              # ③
            specs = self._clean_specs(specs)                      # ④-①
            specs = self._adjust_count(specs, goal)               # ④-②
            cycle = self._find_cycle(specs)                       # ④-③
            if cycle is not None:
                raise ValueError(f'LLM 分解出现环：{" → ".join(map(str, cycle))}')
            specs = self._normalise_types(specs)                  # ④-④
            dag = self._build_dag(goal, specs)                    # ⑤
            self.last_strategy = 'llm'
            logger.info('LLM 分解成功，共 %d 个子任务', len(specs))
            return dag
        except Exception as exc:                                  # ⑥
            self.last_strategy = 'fallback'
            logger.warning('LLM 分解失败，回落到模板：%s', exc)
            return self._build_dag(goal, self._template_specs(goal))

    def replan(self, failed_task: Task, reason: str) -> tuple[TaskDAG, list[str]]:
        '''失败后的重新分解。

        返回值：新的子任务 DAG，以及「被改接了依赖的下游 task_id 列表」。
        第二个返回值不是装饰 —— 它是 ADR-06 那条陷阱的验证依据：
        改接漏了会导致下游静默卡死，而这个列表让缺失变成可断言的事实。

        TODO(W5): 按失败原因选择策略（换模型 / 拆细 / 加依赖 / 放宽约束）。
                  注意：拆完之后，下游任务的 depends_on 必须改接到新子任务上，
                        否则它们永远等不到 DONE → 整条链卡死。
        '''
        raise NotImplementedError('W5 实现')

    # ──────────────────────────────────────────
    # ① 拼 prompt
    # ──────────────────────────────────────────
    def _build_prompt(self, goal: str) -> str:
        return f'''你是一个任务分解器。把下面的目标拆成 3~8 个子任务。

目标：{goal}

只输出 JSON 数组，不要任何解释文字，不要 Markdown 代码块之外的内容。
数组元素格式：
{{"description": "子任务描述", "task_type": "code|test|doc|analysis|design|review", "dependencies": [前置任务的数组下标]}}

硬性约束：
1. 子任务数量必须在 3~8 之间
2. dependencies 只能引用比当前下标更小的索引（即只能依赖前面已列出的任务）
3. task_type 只能取上面 6 个值之一
4. 每个子任务应当 5~15 步可以完成

输出示例：
[{{"description": "设计数据模型", "task_type": "design", "dependencies": []}},
 {{"description": "实现核心逻辑", "task_type": "code", "dependencies": [0]}},
 {{"description": "编写测试", "task_type": "test", "dependencies": [1]}}]
'''

    # ──────────────────────────────────────────
    # ③ 解析：从一段可能很脏的文本里抠出 JSON 数组
    # ──────────────────────────────────────────
    def _parse(self, raw: str) -> list:
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError('LLM 返回为空')

        text = raw.strip()

        # 去掉 ```json ... ``` 包裹
        if '```' in text:
            chunks = text.split('```')
            if len(chunks) >= 3:
                inner = chunks[1].strip()
                if inner.lower().startswith('json'):
                    inner = inner[4:]
                text = inner.strip()

        start, end = text.find('['), text.rfind(']')
        if start == -1 or end == -1 or end < start:
            raise ValueError('输出里找不到 JSON 数组')

        body = text[start:end + 1]
        body = re.sub(r',\s*([}\]])', r'\1', body)      # 容忍尾逗号

        data = json.loads(body)
        if not isinstance(data, list):
            raise ValueError('顶层不是数组')
        return data

    # ──────────────────────────────────────────
    # ④-① 清洗：丢掉无效项，过滤越界/自依赖，重排下标
    # ──────────────────────────────────────────
    def _clean_specs(self, raw: list) -> list[dict]:
        kept: list[tuple[int, dict]] = []
        for index, item in enumerate(raw):
            if not isinstance(item, dict):
                logger.warning('第 %d 项不是对象，丢弃', index)
                continue
            description = str(item.get('description') or '').strip()
            if not description:
                logger.warning('第 %d 项缺少 description，丢弃', index)
                continue
            kept.append((
                index,
                {
                    'description': description,
                    'task_type': item.get('task_type'),
                    'dependencies': item.get('dependencies') or [],
                },
            ))

        if not kept:
            raise ValueError('没有任何可用的子任务')

        # 原始下标 → 新下标。被丢弃的项不会出现在 remap 里，
        # 因此指向它们的依赖会被当作「越界」一并清理掉。
        remap = {old: new for new, (old, _) in enumerate(kept)}

        specs: list[dict] = []
        for old, spec in kept:
            deps: list[int] = []
            for dep in spec['dependencies']:
                if not isinstance(dep, int) or isinstance(dep, bool):
                    logger.warning('依赖 %r 不是整数，已忽略', dep)
                    continue
                if dep not in remap:
                    logger.warning('依赖索引 %s 越界，已从「%s」移除', dep, spec['description'][:20])
                    continue
                new_dep = remap[dep]
                if new_dep == remap[old]:
                    logger.warning('「%s」依赖自己，已移除', spec['description'][:20])
                    continue
                if new_dep not in deps:
                    deps.append(new_dep)
            spec['dependencies'] = sorted(deps)
            specs.append(spec)

        return specs

    # ──────────────────────────────────────────
    # ④-② 数量：<3 补模板，>8 截断
    # ──────────────────────────────────────────
    def _adjust_count(self, specs: list[dict], goal: str) -> list[dict]:
        if len(specs) > MAX_TASKS:
            logger.warning('拆出 %d 个子任务，超过上限 %d，截断', len(specs), MAX_TASKS)
            specs = specs[:MAX_TASKS]
            for spec in specs:
                spec['dependencies'] = [d for d in spec['dependencies'] if d < len(specs)]

        while len(specs) < MIN_TASKS:
            logger.warning('只有 %d 个子任务，少于下限 %d，补模板', len(specs), MIN_TASKS)
            last = len(specs) - 1
            deps = [last] if last >= 0 else []
            existing = {s['task_type'] for s in specs}
            if 'test' not in existing:
                specs.append({'description': f'为以下目标补充测试：{goal}',
                              'task_type': 'test', 'dependencies': deps})
            elif 'doc' not in existing:
                specs.append({'description': f'为以下目标补充文档：{goal}',
                              'task_type': 'doc', 'dependencies': deps})
            else:
                specs.append({'description': f'复核以下目标的完成情况：{goal}',
                              'task_type': 'review', 'dependencies': deps})

        return specs

    # ──────────────────────────────────────────
    # ④-③ 环检测（DFS 三色标记）
    # ──────────────────────────────────────────
    def _find_cycle(self, specs: list[dict]) -> list[int] | None:
        '''返回环上的下标序列（首尾相同），无环返回 None。'''
        total = len(specs)
        state = [0] * total          # 0=未访问 1=在栈上 2=已完成
        stack: list[int] = []
        found: list[int] | None = None

        def visit(node: int) -> bool:
            nonlocal found
            if state[node] == 1:                     # 回到栈上的节点 → 成环
                found = [*stack[stack.index(node):], node]
                return True
            if state[node] == 2:
                return False
            state[node] = 1
            stack.append(node)
            for dep in specs[node]['dependencies']:
                if 0 <= dep < total and visit(dep):
                    return True
            stack.pop()
            state[node] = 2
            return False

        for i in range(total):
            if state[i] == 0 and visit(i):
                return found
        return None

    # ──────────────────────────────────────────
    # ④-④ task_type 归一化
    # ──────────────────────────────────────────
    def _normalise_types(self, specs: list[dict]) -> list[dict]:
        for spec in specs:
            spec['task_type'] = self._guess_task_type(spec.get('task_type'), spec['description'])
        return specs

    @staticmethod
    def _guess_task_type(raw_type, description: str) -> str:
        name = str(raw_type or '').strip().lower().replace('-', '_').replace(' ', '_')
        if name in VALID_TASK_TYPES:
            return name
        if name in _TYPE_ALIASES:
            return _TYPE_ALIASES[name]

        text = f'{name} {description}'.lower()
        hits = []
        for task_type, keywords in _TYPE_KEYWORDS:
            position = min((text.find(kw) for kw in keywords if kw in text), default=-1)
            if position >= 0:
                hits.append((position, task_type))
        if hits:
            return min(hits)[1]

        logger.warning('无法判定 task_type（原值 %r），回落为 code', raw_type)
        return 'code'

    # ──────────────────────────────────────────
    # ⑤ 组装 TaskDAG：数组下标 → 真实 task_id
    # ──────────────────────────────────────────
    def _build_dag(self, goal: str, specs: list[dict]) -> TaskDAG:
        dag = TaskDAG(goal=goal)
        tasks = [
            Task(description=spec['description'], task_type=spec['task_type'])
            for spec in specs
        ]
        for task in tasks:
            dag.add(task)

        ids = [task.task_id for task in tasks]
        for index, spec in enumerate(specs):
            tasks[index].depends_on = [
                ids[dep] for dep in spec['dependencies'] if 0 <= dep < len(ids)
            ]
        return dag

    # ──────────────────────────────────────────
    # ⑥ 兜底模板（LLM 不可用 / 输出不可信时使用）
    # ──────────────────────────────────────────
    @staticmethod
    def _template_specs(goal: str) -> list[dict]:
        return [
            {'description': 'Design the structure and schema for: ' + goal,
             'task_type': 'design', 'dependencies': []},
            {'description': 'Implement the core functionality for: ' + goal,
             'task_type': 'code', 'dependencies': [0]},
            {'description': 'Write tests for: ' + goal,
             'task_type': 'test', 'dependencies': [1]},
            {'description': 'Generate documentation for: ' + goal,
             'task_type': 'doc', 'dependencies': [1]},
        ]
