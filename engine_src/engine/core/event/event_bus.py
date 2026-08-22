# event_bus.py - 极简纯净版，核心只有一个字典
from collections import deque

class EventBus:
    def __init__(self):
        # 核心结构：字典 → 事件名称(str) → 回调函数列表(List)
        self._handlers = {}
        # 简易异步队列（存放待处理的 (事件名, 数据) 元组）
        self._queue = deque()

    # ---------- 订阅 ----------
    def subscribe(self, event_type, callback):
        """订阅事件，直接把函数塞进列表"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(callback)

    # ---------- 取消订阅 ----------
    def unsubscribe(self, event_type, callback):
        """取消订阅：从列表中移除指定函数"""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(callback)
            except ValueError:
                pass  # 如果函数不在里面，忽略即可

    # ---------- 同步触发（立即执行） ----------
    def emit(self, event_type, data=None):
        """立即触发事件"""
        # 关键：用 .copy() 复制一份列表，防止回调里修改列表导致崩溃
        for callback in self._handlers.get(event_type, []).copy():
            callback(data)

    # ---------- 异步投递（下一帧执行） ----------
    def post(self, event_type, data=None):
        """将事件放入队列，等待下一帧处理"""
        self._queue.append((event_type, data))

    # ---------- 主循环更新（每帧调用） ----------
    def update(self):
        """处理异步队列中的所有事件（先投递的先处理）"""
        while self._queue:
            event_type, data = self._queue.popleft()  # 先进先出
            self.emit(event_type, data)  # 内部已带 .copy() 保护