'''EventBus —— 事件发布订阅（§5.13，ADR-13）。

当前为单进程内存实现：list 存储 + 同步通知。
- topic 取 `event.event_type.value`；`'*'` 表示订阅全部。
- `drain()` 返回上次 drain 之后发布的事件，顺序与 publish 一致，并清空缓冲。
- `subscribe(topic)` 只返回迭代器（队列订阅），调用方必须消费；`on(topic, callback)` 提供同步回调，回调异常只记录日志、不影响发布方。

W4 起 Orchestrator 通过它发布事件；本期只提供实现与测试。
'''

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable, Iterator
from typing import Protocol, runtime_checkable

from contractnet.core.types import Event

logger = logging.getLogger(__name__)

WILDCARD_TOPIC = '*'


@runtime_checkable
class EventBus(Protocol):
    def publish(self, event: Event) -> None: ...
    def subscribe(self, topic: str) -> Iterator[Event]: ...
    def drain(self) -> list[Event]: ...


class InMemoryEventBus:
    '''list 存储 + 同步回调，W1–W8 的默认实现（ADR-13）。'''

    def __init__(self) -> None:
        self._events: list[Event] = []
        self._queues: dict[str, list[queue.Queue[Event]]] = {}
        self._callbacks: dict[str, list[Callable[[Event], None]]] = {}
        self._lock = threading.Lock()

    def publish(self, event: Event) -> None:
        topic = event.event_type.value
        with self._lock:
            self._events.append(event)
            queues = list(self._queues.get(topic, ())) + list(
                self._queues.get(WILDCARD_TOPIC, ())
            )
            callbacks = list(self._callbacks.get(topic, ())) + list(
                self._callbacks.get(WILDCARD_TOPIC, ())
            )

        for q in queues:
            q.put(event)
        for callback in callbacks:
            try:
                callback(event)
            except Exception:
                logger.exception(
                    'EventBus 订阅回调异常：topic=%s event=%s', topic, event.event_id
                )

    def subscribe(self, topic: str) -> Iterator[Event]:
        '''订阅 topic，返回阻塞式迭代器（用 next() 取事件）。

        迭代器必须被消费；不消费的队列会持续增长。同步回调请用 on()。
        '''
        q: queue.Queue[Event] = queue.Queue()
        with self._lock:
            self._queues.setdefault(topic, []).append(q)
        return self._iter_queue(q)

    def on(self, topic: str, callback: Callable[[Event], None]) -> None:
        '''注册同步回调；回调异常只记日志，不影响发布方。

        `on` 是内存实现的扩展方法，不要求 EventBus 协议包含它。
        '''
        with self._lock:
            self._callbacks.setdefault(topic, []).append(callback)

    def drain(self) -> list[Event]:
        with self._lock:
            events = self._events
            self._events = []
        return events

    @staticmethod
    def _iter_queue(q: queue.Queue[Event]) -> Iterator[Event]:
        while True:
            yield q.get()