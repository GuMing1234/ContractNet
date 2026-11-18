'''工具沙箱 —— Agent 的操作要受权限和资源限制。

设计要求：
    - 文件读写限制在 workspace 目录内（防路径穿越）
    - 命令执行有超时
    - 输出长度截断（防止一次吐 10MB 把上下文撑爆）
    - 每次调用写审计日志

⚠️ 它是「误操作防护」，不是「安全边界」。别对外宣称能防住恶意代码。
'''

from __future__ import annotations


class ToolSandbox:
    def __init__(self, workspace: str = 'workspace') -> None:
        self.workspace = workspace

    def execute(self, tool_name: str, args: dict) -> str:
        '''执行一个工具调用，返回结果字符串（或错误信息）。

        TODO(W6): 实现 file_read / file_write / code_run 三个工具。
                  code_run 用 subprocess.run(timeout=...)，先做土版本，
                  不要一上来想 Docker。
                  TODO(W2): 返回类型收窄为 ToolResult；SandboxLimits 一并定稿。
        '''
        raise NotImplementedError('W6 实现')
