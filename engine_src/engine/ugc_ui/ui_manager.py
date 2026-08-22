import pygame
from .ui_components import UIButton, UIImage, UIText
from .ui_loader import UILoader

class UIManager:
    def __init__(self, screen_size,engine=None):
        self.root = None
        self.screen_size = screen_size
        self.ui_loader = UILoader
        self.engine = engine



    def set_root(self, root_element):
        self.engine.event.emit("ui_root_set", {"root": root_element})
        self.root = root_element
        # 自动居中根节点（如果锚点是 center）
        if self.root and self.root.anchor == "center":
            self.root.rect.center = (self.screen_size[0] // 2, self.screen_size[1] // 2)

    def update(self, dt):
        if self.root:
            self.root.update(dt)

    def draw(self, surface):
        if self.root:
            self.root.draw(surface)

    def handle_event(self, event):
        if self.root:
            self.root.handle_event(event)

    def clear_ui(self):
        self.root = None

    def open(self, file_path):
        """
        另一个名字的load_from_file方法，用于兼容旧脚本和方便其他不知道新api的开发者。
        """
        print("Opening UI file:", file_path,"Notice, new ui system open ui file is changed")