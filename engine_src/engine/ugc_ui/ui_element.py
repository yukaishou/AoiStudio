import pygame
import time
from engine_src.engine.utils import smooth_tween


class UIAnimation:
    """UI动画类,支持位置、缩放、透明度动画"""
    
    def __init__(self):
        # 位置动画
        self.pos_animating = False
        self.pos_start = [0, 0]
        self.pos_target = [0, 0]
        self.pos_start_time = 0
        self.pos_duration = 0
        self.pos_ease_func = smooth_tween.linear
        
        # 缩放动画
        self.scale_animating = False
        self.scale_start = [1.0, 1.0]
        self.scale_target = [1.0, 1.0]
        self.scale_start_time = 0
        self.scale_duration = 0
        self.scale_ease_func = smooth_tween.linear
        
        # 透明度动画
        self.alpha_animating = False
        self.alpha_start = 255
        self.alpha_target = 255
        self.alpha_start_time = 0
        self.alpha_duration = 0
        self.alpha_ease_func = smooth_tween.linear
        self.current_alpha = 255
    
    def animate_position(self, target_x, target_y, duration=0.3, ease_func=None):
        """开始位置动画"""
        if not hasattr(self, 'element') or self.element is None:
            return
        self.pos_start = [self.element.raw_x, self.element.raw_y]
        self.pos_target = [target_x, target_y]
        self.pos_start_time = time.perf_counter()
        self.pos_duration = duration
        self.pos_ease_func = ease_func or smooth_tween.ease_out_cubic
        self.pos_animating = True
    
    def animate_scale(self, target_scale_x, target_scale_y, duration=0.3, ease_func=None, element=None):
        """开始缩放动画"""
        if element and hasattr(element, 'scale'):
            scale = element.scale
            self.scale_start = list(scale) if isinstance(scale, list) else [scale, scale]
        else:
            self.scale_start = [1.0, 1.0]
        self.scale_target = [target_scale_x, target_scale_y]
        self.scale_start_time = time.perf_counter()
        self.scale_duration = duration
        self.scale_ease_func = ease_func or smooth_tween.ease_out_cubic
        self.scale_animating = True
    
    def animate_alpha(self, target_alpha, duration=0.3, ease_func=None):
        """开始透明度动画"""
        self.alpha_start = self.current_alpha
        self.alpha_target = target_alpha
        self.alpha_start_time = time.perf_counter()
        self.alpha_duration = duration
        self.alpha_ease_func = ease_func or smooth_tween.ease_out_cubic
        self.alpha_animating = True
    
    def update_animation(self, dt, element):
        """更新所有动画"""
        now = time.perf_counter()
        
        # 更新位置动画
        if self.pos_animating:
            elapsed = now - self.pos_start_time
            t = min(elapsed / self.pos_duration, 1.0)
            smooth_t = self.pos_ease_func(t)
            new_x = smooth_tween.lerp(self.pos_start[0], self.pos_target[0], smooth_t)
            new_y = smooth_tween.lerp(self.pos_start[1], self.pos_target[1], smooth_t)
            element.set_position(new_x, new_y)
            if t >= 1.0:
                self.pos_animating = False
        
        # 更新缩放动画
        if self.scale_animating:
            elapsed = now - self.scale_start_time
            t = min(elapsed / self.scale_duration, 1.0)
            smooth_t = self.scale_ease_func(t)
            if hasattr(element, 'scale'):
                if isinstance(element.scale, list):
                    element.scale[0] = smooth_tween.lerp(self.scale_start[0], self.scale_target[0], smooth_t)
                    element.scale[1] = smooth_tween.lerp(self.scale_start[1], self.scale_target[1], smooth_t)
                else:
                    element.scale = smooth_tween.lerp(self.scale_start[0], self.scale_target[0], smooth_t)
            if t >= 1.0:
                self.scale_animating = False
        
        # 更新透明度动画
        if self.alpha_animating:
            elapsed = now - self.alpha_start_time
            t = min(elapsed / self.alpha_duration, 1.0)
            smooth_t = self.alpha_ease_func(t)
            self.current_alpha = int(smooth_tween.lerp(self.alpha_start, self.alpha_target, smooth_t))
            if t >= 1.0:
                self.alpha_animating = False


class UIElement:
    def __init__(self, x=0, y=0, width=100, height=100, anchor="topleft", engine=None):
        # 原始逻辑坐标(未经过锚点偏移)
        self.raw_x = x
        self.raw_y = y
        self.rect = pygame.Rect(x, y, width, height)
        self.anchor = anchor  # 锚点:topleft / center / bottomleft / topright / bottomright
        self.children = []
        self.parent = None
        self.is_visible = True
        self.color = (255, 255, 255)
        self.engine = engine
        self.animation = UIAnimation()

        if self.engine:
            self.update_anchor()

    def update(self, dt):
        """帧更新,递归子元素"""
        # 更新动画
        self.animation.update_animation(dt, self)
        
        for child in self.children:
            if child.is_visible:
                child.update(dt)

    def draw(self, surface):
        """绘制,递归子元素"""
        if not self.is_visible:
            return
        
        # 保存原始alpha并应用父级alpha
        original_alpha = self.animation.current_alpha
        
        for child in self.children:
            # 将父元素的alpha传递给子元素
            if hasattr(child, 'animation'):
                # 计算混合后的alpha（父子alpha相乘）
                combined_alpha = int(original_alpha * child.animation.current_alpha / 255)
                child.animation.current_alpha = combined_alpha
            
            child.draw(surface)
            
            # 恢复子元素原始alpha（避免影响后续帧）
            if hasattr(child, 'animation'):
                child.animation.current_alpha = int(combined_alpha * 255 / original_alpha) if original_alpha > 0 else 255

    def handle_event(self, event):
        """事件分发,递归子元素"""
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
        """设置原始偏移坐标,调用后刷新锚点位置"""
        self.raw_x = x
        self.raw_y = y
        self.update_anchor()

    def set_size(self, w, h):
        self.rect.width = w
        self.rect.height = h
        self.update_anchor()

    def get_global_rect(self):
        """获取相对于屏幕的全局rect(支持父级嵌套偏移,如果你后续做容器偏移)"""
        return self.rect.copy()