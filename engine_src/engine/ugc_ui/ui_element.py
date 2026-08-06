import pygame


class UIElement:
    def __init__(self, x=0, y=0, width=100, height=100, anchor="topleft", engine=None):
        # 原始逻辑坐标（未经过锚点偏移）
        self.raw_x = x
        self.raw_y = y
        self.rect = pygame.Rect(x, y, width, height)
        self.anchor = anchor  # 锚点：topleft / center / bottomleft / topright / bottomright
        self.children = []
        self.parent = None
        self.is_visible = True
        self.color = (255, 255, 255)
        self.engine = engine

        if self.engine:
            self.update_anchor()

    def update(self, dt):
        """帧更新，递归子元素"""
        for child in self.children:
            if child.is_visible:
                child.update(dt)

    def draw(self, surface):
        """绘制，递归子元素"""
        if not self.is_visible:
            return
        # pygame.draw.rect(surface, self.color, self.rect, 2)  # 调试边框
        for child in self.children:
            child.draw(surface)

    def handle_event(self, event):
        """事件分发，递归子元素"""
        if not self.is_visible:
            return
        for child in self.children:
            child.handle_event(event)

    def add_child(self, element):
        element.parent = self
        self.children.append(element)

    def remove_child(self, element):
        if element in self.children:
            element.parent = None
            self.children.remove(element)

    def update_anchor(self):
        """
        根据锚点计算真实rect坐标
        engine.get_center() 返回 (screen_w//2, screen_h//2)
        raw_x / raw_y 是相对于锚点的偏移量
        """
        if not self.engine:
            return
        cx, cy = self.engine.get_center()
        w = self.rect.width
        h = self.rect.height

        if self.anchor == "center":
            # raw_x,raw_y 相对于屏幕中心偏移
            self.rect.centerx = cx + self.raw_x
            self.rect.centery = cy + self.raw_y
        elif self.anchor == "topleft":
            # raw_x,raw_y 就是屏幕左上角偏移
            self.rect.topleft = (self.raw_x, self.raw_y)
        elif self.anchor == "topright":
            self.rect.topright = (cx * 2 + self.raw_x, self.raw_y)
        elif self.anchor == "bottomleft":
            self.rect.bottomleft = (self.raw_x, cy * 2 + self.raw_y)
        elif self.anchor == "bottomright":
            self.rect.bottomright = (cx * 2 + self.raw_x, cy * 2 + self.raw_y)
        else:
            # fallback 默认 topleft
            self.rect.topleft = (self.raw_x, self.raw_y)

    def set_position(self, x, y):
        """设置原始偏移坐标，调用后刷新锚点位置"""
        self.raw_x = x
        self.raw_y = y
        self.update_anchor()

    def set_size(self, w, h):
        self.rect.width = w
        self.rect.height = h
        self.update_anchor()

    def get_global_rect(self):
        """获取相对于屏幕的全局rect（支持父级嵌套偏移，如果你后续做容器偏移）"""
        return self.rect.copy()