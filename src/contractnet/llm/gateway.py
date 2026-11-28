'''LLM 网关 —— 所有对大模型的调用都从这里走。

为什么必须有这一层（而不是各处直接调 SDK）：
    1. 重试/超时/降级策略统一，不用每个调用点写一遍
    2. 测试时可以整体替换成假客户端（不花钱）
    3. 能统一统计 token 消耗、按模块归因

⚠️ 本模块即设计文档 §5.8 的 LLMGateway，接口规格见 §6。
'''

from __future__ import annotations

import logging
import os

from contractnet.core.types import LLMResponse

logger = logging.getLogger(__name__)


class LLMError(Exception):
    '''LLM 调用失败。'''


class LLMGateway:
    def __init__(self, api_key: str | None = None, base_url: str | None = None,
                 model: str | None = None) -> None:
        self.api_key = api_key or os.environ.get('CONTRACTNET_API_KEY', '')
        self.base_url = base_url or os.environ.get('CONTRACTNET_BASE_URL', '')
        self.model = model or os.environ.get('CONTRACTNET_MODEL', '')
        self._client = None

    def complete(self, prompt: str, **opts) -> str:
        '''单轮补全，返回纯文本。

        TODO(W3): 实现。要求：
            - 用 openai SDK（兼容 DeepSeek / 智谱 / OpenAI）
            - 失败重试（指数退避），但 401/403/404 这类错误要快速失败，不重试
            - 记录 token 消耗
            - 提供「回放模式」：把上次的请求/响应存下来，下次直接读（省钱的测试手段）
        '''
        raise NotImplementedError('W3 实现')

    def chat(self, messages: list[dict], tools: list[dict] | None = None, **opts) -> LLMResponse:
        '''多轮对话 + 工具定义，供 ReAct 循环使用。

        TODO(W3): 实现。返回内容要能拿到 content 与 tool_calls。
        '''
        raise NotImplementedError('W3 实现')
