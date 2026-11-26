'''EventBus 内存实现（§5.13 / TASKS W2）。

覆盖设计文档的三个测试点：drain 顺序、回调异常隔离、协议可替换。
'''

from __future__ import annotations

from contractnet.core.event_bus import EventBus, InMemoryEventBus
from contractnet.core.types import Event, EventType


def _event(
    event_type: EventType = EventType.TASK_CREATED,
    trace_id: str = 't1',
) -> Event:
    return Event(trace_id=trace_id, event_type=event_type)


def test_drain_returns_events_in_order_and_clears():
    '''drain() 按 publish 顺序返回，取完清空。'''
    bus = InMemoryEventBus()
    events = [_event(trace_id='t1'), _event(EventType.GATE_PASSED, 't2')]

    for event in events:
        bus.publish(event)

    assert bus.drain() == events
    assert bus.drain() == []


def test_subscribe_receives_only_matching_topic():
    '''只收到自己 topic 的事件；不匹配的事件留在别的频道。'''
    bus = InMemoryEventBus()
    subscription = bus.subscribe(EventType.TASK_CREATED.value)
    matched = _event(EventType.TASK_CREATED)

    bus.publish(_event(EventType.GATE_PASSED))
    bus.publish(matched)

    assert next(subscription) is matched


def test_wildcard_subscriber_receives_all_events():
    '''通配 '*' 订阅全部事件，且顺序不变。'''
    bus = InMemoryEventBus()
    subscription = bus.subscribe('*')
    first = _event(EventType.TASK_CREATED)
    second = _event(EventType.GATE_PASSED)

    bus.publish(first)
    bus.publish(second)

    assert next(subscription) is first
    assert next(subscription) is second


def test_callback_exception_does_not_break_publish():
    '''一个订阅回调抛异常，发布方与其他订阅方都不受影响。'''
    bus = InMemoryEventBus()
    seen: list[Event] = []

    def boom(event: Event) -> None:
        raise RuntimeError('订阅方故意报错')

    bus.on(EventType.TASK_CREATED.value, boom)
    bus.on(EventType.TASK_CREATED.value, seen.append)
    event = _event()

    bus.publish(event)  # 不应抛出

    assert seen == [event]


def test_on_callback_does_not_create_queue():
    '''callback-only 用法不创建队列，避免无人消费导致内存增长。'''
    bus = InMemoryEventBus()
    bus.on(EventType.TASK_CREATED.value, lambda event: None)
    assert bus._queues == {}


def test_in_memory_bus_satisfies_protocol():
    '''调用方只依赖 EventBus 协议，可以无缝替换实现。'''
    assert isinstance(InMemoryEventBus(), EventBus)