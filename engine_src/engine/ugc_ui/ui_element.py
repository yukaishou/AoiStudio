import pygame

class UIElement:
    def __init__(self, x=0, y=0, width=100, height=100, anchor="center",engine = None):
        self.rect = pygame.Rect(x, y, width, height)
        self.anchor = anchor  # 锚点: center, topleft, bottomright 等
        self.children = []
        self.parent = None
        self.is_visible = True
        self.color = (255, 255, 255)
        self.engine = engine

    def update(self, dt):
        for child in self.children:
            child.update(dt)

    def draw(self, surface):
        if not self.is_visible:
            return
        # 简单的占位绘制，子类会覆盖它
        # pygame.draw.rect(surface, self.color, self.rect, 2) # 调试用边框
        for child in self.children:
            child.draw(surface)

    def handle_event(self, event):
        for child in self.children:
            child.handle_event(event)

    def add_child(self, element):
        element.parent = self
        self.children.append(element)