import pygame
from .ui_components import UIButton, UIImage, UIText
from .ui_loader import UILoader
from .cg_viewer import CGViewer, CGTransition


class UIManager:
    def __init__(self, screen_size,engine=None):
        self.root = None
        self.screen_size = screen_size
        self.ui_loader = UILoader
        self.engine = engine
        self.cg_viewers = []  # 管理所有CG查看器
    
    def add_cg_viewer(self, cg_viewer):
        """添加CG查看器到管理器"""
        if cg_viewer and not isinstance(cg_viewer, CGViewer):
            return
        self.cg_viewers.append(cg_viewer)
    
    def remove_cg_viewer(self, cg_viewer):
        """从管理器移除CG查看器"""
        if cg_viewer in self.cg_viewers:
            self.cg_viewers.remove(cg_viewer)
    
    def get_cg_viewer(self, index=0):
        """获取指定索引的CG查看器"""
        if 0 <= index < len(self.cg_viewers):
            return self.cg_viewers[index]
        return None
    
    def show_cg(self, image_path, title="", description="", transition=CGTransition.FADE):
        """
        通过管理器显示CG
        :param image_path: CG图片路径
        :param title: CG标题
        :param description: CG描述
        :param transition: 切换动画类型
        """
        for viewer in self.cg_viewers:
            viewer.set_transition(transition)
            viewer.show_cg(image_path, title, description)
    
    def hide_all_cg(self, duration=0.5):
        """隐藏所有CG"""
        for viewer in self.cg_viewers:
            viewer.hide_cg(duration)
    
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
        # 先绘制 UI 根节点
        if self.root:
            self.root.draw(surface)
        
        # 再绘制所有 CG 查看器（确保 CG 在最上层）
        for viewer in self.cg_viewers:
            if viewer and viewer.is_visible:
                viewer.draw(surface)

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