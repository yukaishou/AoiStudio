import pygame

from engine_src.engine.g_o.component_base import ComponentBase

class CollisionBox(ComponentBase):
    def __init__(self, game_object, properties: dict, engine):
        super().__init__(game_object, properties, engine)
        # 场景局部坐标系 Rect（不含窗口中心偏移）
        self._collision_rect = pygame.Rect(0, 0, 100, 100)
        self._sync_rect()

    def _sync_rect(self):
        """同步碰撞盒，从go位置、缩放、properties更新_rect，抽成公共函数，init/update复用"""
        go_pos = self.game_object.get_position()
        go_scale = self.game_object.get_scale()
        w = self.properties.get("width", 100)
        h = self.properties.get("height", 100)

        self._collision_rect.x = go_pos[0] - w * 0.5
        self._collision_rect.y = go_pos[1] - h * 0.5
        self._collision_rect.width = go_scale[0] * w
        self._collision_rect.height = go_scale[1] * h

    def update(self, dt: float):
        self._sync_rect()

    def draw(self, surface):
        """调试绘制碰撞盒，转换到屏幕坐标"""
        if not self.properties.get("draw", False):
            return
        # _collision_rect：场景局部坐标；加上窗口中心得到屏幕坐标
        screen_rect = self._collision_rect.copy()
        cx, cy = self.engine.get_center()
        screen_rect.x += cx
        screen_rect.y += cy
        pygame.draw.rect(surface, (255, 0, 0), screen_rect, 5)

    def check_collision_for_rect(self, rect: pygame.Rect):
        """检测与另一个矩形（场景局部坐标）是否相交"""
        return self._collision_rect.colliderect(rect)

    def check_point(self, sx: float, sy: float):
        """检测点(场景局部坐标)是否落在碰撞盒内，给鼠标点击直接调用"""
        return self._collision_rect.collidepoint(sx, sy)

    def check_collision_for_scene(self):
        """检测与场景内其他CollisionBox碰撞，返回碰撞信息"""
        go_list = list(self.engine.g_o_manager.game_objects)
        for other_go in go_list:
            # 跳过自己
            if other_go is self.game_object:
                continue
            other_cb = other_go.get_component("CollisionBox")
            if other_cb is None:
                continue
            other_rect = other_cb._collision_rect
            if self._collision_rect.colliderect(other_rect):
                return {
                    "is_collision": True,
                    "other_object": other_go,
                    "other_rect": other_rect
                }
        return {"is_collision": False, "other_object": None, "other_rect": None}