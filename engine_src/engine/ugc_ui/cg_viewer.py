import pygame
import time
from .ui_element import UIElement
from .ui_components import UIImage, UIText, UIButton
from engine_src.engine.utils import smooth_tween
from engine_src.engine.core import log


class CGTransition:
    """CG切换动画类型"""
    FADE = "fade"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"


class CGViewer(UIElement):
    """CG查看器组件，用于展示CG图片"""
    
    def __init__(self, x, y, width, height, anchor="center", engine=None):
        super().__init__(x, y, width, height, anchor, engine)
        
        # CG列表和索引
        self.cg_list = []
        self.current_index = 0
        self.is_visible = False
        
        # 切换动画设置
        self.transition_type = CGTransition.FADE
        self.is_transitioning = False
        self.transition_start_time = 0
        self.transition_duration = 0.5
        self.transition_progress = 0
        
        # 图像相关
        self.current_image = None
        self.next_image = None
        self.current_rect = pygame.Rect(0, 0, width, height)
        
        # 文本显示
        self.title = ""
        self.description = ""
        self.title_text = None
        self.description_text = None
        
        # 事件回调
        self.on_cg_changed = None
        self.on_cg_finished = None
        
        # 初始化UI元素
        self._supports_cg_viewer = True
        
        # 字体
        try:
            self.title_font = pygame.font.Font("fonts/default.ttf", 28)
            self.desc_font = pygame.font.Font("fonts/default.ttf", 20)
        except:
            self.title_font = pygame.font.SysFont(None, 28)
            self.desc_font = pygame.font.SysFont(None, 20)
    
    def set_cg_list(self, cg_list):
        """
        设置CG列表
        :param cg_list: 列表，每个元素为字典 {'image_path': str, 'title': str, 'description': str}
        """
        self.cg_list = cg_list
        self.current_index = 0
    
    def show_cg(self, image_path=None, title="", description="", cg_index=None):
        """
        显示CG
        :param image_path: CG图片路径
        :param title: CG标题
        :param description: CG描述
        :param cg_index: 如果使用cg_list，指定索引
        """
        if cg_index is not None and 0 <= cg_index < len(self.cg_list):
            self.current_index = cg_index
            cg_info = self.cg_list[cg_index]
            image_path = cg_info.get('image_path', '')
            title = cg_info.get('title', title)
            description = cg_info.get('description', description)
        
        if not image_path:
            return
        
        # 如果已经有CG在显示，执行切换动画
        if self.current_image is not None and self.is_visible:
            self.start_transition(image_path, title, description)
        else:
            # 直接加载显示
            self._load_and_display(image_path, title, description)
            self.is_visible = True
        
        # 触发回调
        if self.on_cg_changed:
            self.on_cg_changed(self.current_index)
    
    def hide_cg(self, duration=0.5):
        """隐藏CG"""
        if self.current_image is None:
            return
        
        # 淡出动画
        self.animation.animate_alpha(0, duration=duration)
        self._hide_duration = duration
        self._hide_start_time = time.perf_counter()
        self._hiding = True
    
    def set_transition(self, transition_type):
        """设置切换动画类型"""
        self.transition_type = transition_type
    
    def next_cg(self):
        """切换到下一张CG"""
        if not self.cg_list or self.is_transitioning:
            return
        self.current_index = (self.current_index + 1) % len(self.cg_list)
        cg_info = self.cg_list[self.current_index]
        self.show_cg(
            cg_info.get('image_path', ''), 
            cg_info.get('title', ''), 
            cg_info.get('description', ''),
            self.current_index
        )
    
    def prev_cg(self):
        """切换到上一张CG"""
        if not self.cg_list or self.is_transitioning:
            return
        self.current_index = (self.current_index - 1) % len(self.cg_list)
        cg_info = self.cg_list[self.current_index]
        self.show_cg(
            cg_info.get('image_path', ''), 
            cg_info.get('title', ''), 
            cg_info.get('description', ''),
            self.current_index
        )
    
    def is_cg_visible(self):
        """检查CG是否可见"""
        return self.is_visible and self.current_image is not None
    
    def start_transition(self, next_image_path, title, description):
        """开始切换动画"""
        self.is_transitioning = True
        self.transition_start_time = time.perf_counter()
        self.transition_progress = 0
        self.next_image_path = next_image_path
        self.next_title = title
        self.next_description = description
        
        try:
            self.next_image = self.engine.resource_manager.load_image(next_image_path)
            self.next_image = pygame.transform.smoothscale(
                self.next_image, (self.rect.width, self.rect.height)
            )
        except Exception as e:
            log.log(2, f"[CGViewer] 加载CG图片失败: {e}")
            self.is_transitioning = False
    
    def _load_and_display(self, image_path, title, description):
        """加载并显示CG"""
        try:
            img = self.engine.resource_manager.load_image(image_path)
            self.current_image = pygame.transform.smoothscale(
                img, (self.rect.width, self.rect.height)
            )
            self.current_rect = self.rect.copy()
            self.current_rect.x = 0
            self.current_rect.y = 0
            
            # 设置文本
            self.title = title
            self.description = description
            
            # 清除隐藏状态
            if hasattr(self, '_hiding'):
                self._hiding = False
            
            # 淡入动画
            self.animation.current_alpha = 0
            self.animation.animate_alpha(255, duration=self.transition_duration)
            
            # 调试输出：确认图片尺寸和绘制区域
            if self.current_image:
                log.log(0, f"[CGViewer] Image loaded: {self.current_image.get_size()}, Rect: {self.current_rect}")
        except Exception as e:
            log.log(2, f"[CGViewer] 加载CG图片失败: {e}")
    
    def update(self, dt):

        """更新CG查看器状态"""
        super().update(dt)
        
        # 调试：输出当前alpha值
        #if self.is_visible and self.current_image is not None:
            #log.log(0, f"[CGViewer] Update: alpha={self.animation.current_alpha}, animating={self.animation.alpha_animating}")
        
        # 处理隐藏动画
        if hasattr(self, '_hiding') and self._hiding:
            elapsed = time.perf_counter() - self._hide_start_time
            t = min(elapsed / self._hide_duration, 1.0)
            if t >= 1.0:
                self._hiding = False
                self.is_visible = False
                self.current_image = None
                self.title = ""
                self.description = ""
                if self.on_cg_finished:
                    self.on_cg_finished()
            return
        
        # 处理切换动画
        if self.is_transitioning:
            now = time.perf_counter()
            elapsed = now - self.transition_start_time
            self.transition_progress = min(elapsed / self.transition_duration, 1.0)
            
            smooth_t = smooth_tween.ease_in_out(self.transition_progress)
            
            if self.transition_type == CGTransition.FADE:
                # 淡入淡出效果
                if self.transition_progress < 0.5:
                    # 第一张图淡出
                    fade_out = 1.0 - (self.transition_progress * 2)
                    self.animation.current_alpha = int(255 * fade_out)
                else:
                    # 第二张图淡入
                    if self.transition_progress >= 0.5 and self.next_image is not None:
                        # 切换到新图
                        self.current_image = self.next_image
                        self.title = self.next_title
                        self.description = self.next_description
                        
                        fade_in = (self.transition_progress - 0.5) * 2
                        self.animation.current_alpha = int(255 * fade_in)
            elif self.transition_type == CGTransition.SLIDE_LEFT:
                # 左滑效果
                offset = int(self.rect.width * smooth_t)
                if self.transition_progress < 0.5:
                    self.current_rect.x = self.rect.x - offset
                else:
                    if self.next_image is not None:
                        self.current_image = self.next_image
                        self.current_rect.x = self.rect.x + self.rect.width - offset
                        self.title = self.next_title
                        self.description = self.next_description
            elif self.transition_type == CGTransition.SLIDE_RIGHT:
                # 右滑效果
                offset = int(self.rect.width * smooth_t)
                if self.transition_progress < 0.5:
                    self.current_rect.x = self.rect.x + offset
                else:
                    if self.next_image is not None:
                        self.current_image = self.next_image
                        self.current_rect.x = self.rect.x - self.rect.width + offset
                        self.title = self.next_title
                        self.description = self.next_description

            if self.transition_progress >= 1.0:
                self.is_transitioning = False
                self.current_rect = self.rect.copy()
                self.animation.current_alpha = 255
    
    def draw(self, surface):
        """绘制CG查看器"""
        if not self.is_visible or self.current_image is None:
            return
        
        # 调试：输出绘制时的alpha值
        #log.log(0, f"[CGViewer] Draw: alpha={self.animation.current_alpha}")
        
        # 绘制CG图片
        if self.animation.current_alpha < 255:
            temp_image = self.current_image.copy()
            temp_image.set_alpha(self.animation.current_alpha)
            surface.blit(temp_image, self.current_rect)
        else:
            surface.blit(self.current_image, self.current_rect)
        # 绘制半透明背景用于文本
        if self.title or self.description:
            overlay = pygame.Surface((self.rect.width, 100), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))
            surface.blit(overlay, (self.rect.x, self.rect.y))
            
            # 绘制标题
            if self.title:
                title_surf = self.title_font.render(self.title, True, (255, 255, 255))
                surface.blit(title_surf, (self.rect.x + 20, self.rect.y + 20))
            
            # 绘制描述
            if self.description:
                desc_surf = self.desc_font.render(self.description, True, (200, 200, 200))
                surface.blit(desc_surf, (self.rect.x + 20, self.rect.y + 55))
    
    def handle_event(self, event):
        """处理事件"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RIGHT:
                self.next_cg()
            elif event.key == pygame.K_LEFT:
                self.prev_cg()
            elif event.key == pygame.K_ESCAPE:
                self.hide_cg()
        
        super().handle_event(event)
