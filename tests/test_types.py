'''数据结构的单元测试。这些是地基，必须稳。'''

from contractnet.core.types import Task, TaskDAG, TaskStatus


def test_ready_tasks_respects_dependencies():
    dag = TaskDAG(goal='g')
    a = Task(description='a')
    b = Task(description='b', depends_on=[a.task_id])
    dag.add(a)
    dag.add(b)

    assert dag.ready_tasks() == [a]          # b 依赖 a，现在只有 a 能跑

    dag.update_status(a.task_id, TaskStatus.DONE)
    assert dag.ready_tasks() == [b]          # a 完成后 b 才就绪


def test_all_terminal_includes_failed():
    '''all_terminal 必须把 FAILED / IMPOSSIBLE 也算终止。

    否则有任务失败时循环永远出不来 —— 这是参考实现踩过的坑。
    '''
    dag = TaskDAG(goal='g')
    t = Task(description='x')
    dag.add(t)
    assert dag.all_terminal() is False

    dag.update_status(t.task_id, TaskStatus.FAILED)
    assert dag.all_terminal() is True


def test_replanned_is_terminal():
    dag = TaskDAG(goal='g')
    t = Task(description='x')
    dag.add(t)
    dag.update_status(t.task_id, TaskStatus.REPLANNED)
    assert dag.all_terminal() is True


def test_unscored_artifact_has_none_quality():
    '''没有评分时 quality 必须是 None，不能拿阈值冒充分数。'''
    from contractnet.core.agent import BaseAgent
    from contractnet.core.quality_gate import QualityGate
    from contractnet.core.types import Contract

    agent = BaseAgent('a1', 'A', ['*'])
    contract = Contract(task_id='t1', description='x')
    artifact = agent.execute(contract)
    result = QualityGate().review(artifact, contract)

    assert result.score is None
