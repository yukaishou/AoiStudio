"""
InputManager：输入管理器
职责：封装pygame原始输入，提供：持续按住、刚刚按下、刚刚松开；
对外不暴露pygame原始key数组；
配合event_bus可以分发 key_down / key_up 事件。
"""
import pygame
from engine_src.engine.core.event import event_bus


class InputManager:
    def __init__(self, event_bus_instance: event_bus.EventBus):
        self._event_bus = event_bus_instance

        # pygame原始按键状态数组，不对外暴露
        self._raw_keys = None

        # 当前帧瞬时集合：本帧刚按下 / 本帧刚松开，每帧清空
        self.key_just_pressed: set[int] = set()
        self.key_just_released: set[int] = set()

        # 鼠标
        self.mouse_pos: tuple[int, int] = (0, 0)
        self.mouse_buttons: tuple[bool, bool, bool] = (False, False, False)
        self.mouse_just_pressed: set[int] = set()   # 1左键,2中键,3右键

    def frame_begin(self):
        """
        【每帧开头调用】
        刷新按键状态，清空瞬时标记。
        在engine主循环最开头执行。
        """
        self._raw_keys = pygame.key.get_pressed()
        self.mouse_buttons = pygame.mouse.get_pressed()
        self.mouse_pos = pygame.mouse.get_pos()

        # 瞬时状态每帧重置
        self.key_just_pressed.clear()
        self.key_just_released.clear()
        self.mouse_just_pressed.clear()

    def process_pygame_event(self, event):
        """
        传入pygame event事件，解析键盘/鼠标事件，填充瞬时集合，同时向事件总线发送事件
        在for event in pygame.event.get()循环内调用
        """
        if event.type == pygame.KEYDOWN:
            self.key_just_pressed.add(event.key)
            self._event_bus.emit("key_down", {"key": event.key})

        elif event.type == pygame.KEYUP:
            self.key_just_released.add(event.key)
            self._event_bus.emit("key_up", {"key": event.key})

        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.mouse_just_pressed.add(event.button)

    # -------- 键盘查询接口 --------
    def is_pressed(self, key: int) -> bool:
        """该键当前帧处于按住状态（持续按住）"""
        if self._raw_keys is None:
            return False
        return bool(self._raw_keys[key])

    def is_just_pressed(self, key: int) -> bool:
        """本帧刚刚按下，只触发一次"""
        return key in self.key_just_pressed

    def is_just_released(self, key: int) -> bool:
        """本帧刚刚松开，只触发一次"""
        return key in self.key_just_released

    # -------- 鼠标查询接口 --------
    def get_mouse_pos(self) -> tuple[int, int]:
        return self.mouse_pos

    def is_mouse_button_pressed(self, btn: int) -> bool:
        """btn:1左键 2中键 3右键，持续按住"""
        return bool(self.mouse_buttons[btn - 1])

    def is_mouse_button_just_pressed(self, btn: int) -> bool:
        """本帧鼠标按键刚刚按下"""
        return btn in self.mouse_just_pressed