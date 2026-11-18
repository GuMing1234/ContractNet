'''ConflictResolver —— 冲突检测与消解。

五种冲突类型（W6 逐步实现）：
    1. 文件写冲突      两个任务写了同一个文件
    2. 接口不一致      函数签名对不上
    3. 语义矛盾        两个结论互相否斥
    4. 依赖违规        读到了还没完成的产出
    5. 死锁            循环等待

职责：检测冲突、给出消解策略
不负责：判断单个成果物质量
'''

from __future__ import annotations

from contractnet.core.types import Conflict, TaskDAG


class ConflictResolver:
    def detect(self, dag: TaskDAG, store=None) -> list[Conflict]:
        '''检测冲突。返回 Conflict 列表。

        TODO(W6): 先做「文件写冲突」（最简也最实用），
                  再做「依赖违规」，最后才考虑 AST 接口对比。
        '''
        return []

    def resolve(self, conflict: Conflict, dag: TaskDAG):
        '''消解冲突。返回消解策略说明。

        TODO(W6): 串行化 / 重新执行下游 / 并行对比取优 / 强制终止。
                  TODO(W2): 返回类型 Resolution 在接口冻结时定稿。
        '''
        raise NotImplementedError('W6 实现')
