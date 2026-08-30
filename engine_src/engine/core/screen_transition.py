import pygame
import time
from engine_src.engine.utils import smooth_tween


class ScreenTransition:
    """屏幕转场效果管理器 - 支持淡入淡出效果"""
    
    def __init__(self, engine):
        self.on_half_complete_callback = None
        self.is_half_complete = False
        self.engine = engine
        self.active = False
        self.transition_type = "fade"  # fade, black_fade
        self.start_time = 0
        self.duration = 0.5  # 总时长（淡入+淡出）
        self.alpha = 0
        self.on_complete_callback = None
    
    def start_transition(self, transition_type="black_fade", duration=0.5, callback=None,half_callback=None):
        """开始转场动画 - 淡入淡出效果"""
        self.active = True
        self.transition_type = transition_type
        self.duration = duration
        self.start_time = time.perf_counter()
        self.alpha = 0
        self.on_complete_callback = callback
        self.on_half_complete_callback = half_callback
        self.is_half_complete = False
    
    def update(self, dt):
        """更新转场动画 - 淡入淡出"""
        if not self.active:
            return
        
        now = time.perf_counter()
        elapsed = now - self.start_time
        t = min(elapsed / self.duration, 1.0)
        
        # 淡入淡出：0→0.5 淡入，0.5→1.0 淡出
        if t <= 0.5:
            # 淡入阶段：从 0 到 1
            phase_t = t / 0.5  # 0→1
            smooth_t = smooth_tween.ease_in_out(phase_t)
        else:
            if self.on_half_complete_callback and not self.is_half_complete:
                self.on_half_complete_callback()
                self.is_half_complete = True
            # 淡出阶段：从 1 到 0
            phase_t = (t - 0.5) / 0.5  # 0→1
            smooth_t = 1.0 - smooth_tween.ease_in_out(phase_t)
        
        self.alpha = int(255 * smooth_t)
        
        if t >= 1.0:
            self.active = False
            self.alpha = 0
            if self.on_complete_callback:
                self.on_complete_callback()
    
    def draw(self, surface):
        """绘制转场遮罩"""
        if not self.active or self.alpha <= 0:
            return
        
        if self.transition_type == "black_fade":
            # 黑色半透明遮罩
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, self.alpha))
            surface.blit(overlay, (0, 0))
        elif self.transition_type == "fade":
            # 白色遮罩
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, self.alpha))
            surface.blit(overlay, (0, 0))
    
    def is_active(self):
        """检查转场是否正在进行"""
        return self.active
