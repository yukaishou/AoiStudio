import pygame
from .ui_element import UIElement
from engine_src.engine.core import log
from engine_src.engine.utils import smooth_tween

class UIButton(UIElement):
    def __init__(self, text, x, y, width, height, hit_sound_path=None, callback=None, font_path=None, anchor="center", engine=None):
        super().__init__(x, y, width, height, anchor, engine)
        self.text = text
        self.callback = callback
        # 加载指定的字体
        try:
            if font_path:
                font_path = f"{font_path}"
                self.font = pygame.font.Font(font_path, 24)
            else:
                self.font = pygame.font.SysFont(None, 24)
        except Exception as e:
            log.log(2, f"[UI] 加载按钮字体失败: {e}")
            pygame.font.init()
            self.font = pygame.font.Font(None, 24)
        # 加载点击音效
        try:
            if hit_sound_path:
                self.click_sound = self.engine.resource_manager.load_sound(hit_sound_path)
                log.log(4, f"[UI] 加载按钮点击音效成功")
            else:
                self.click_sound = None
                log.log(4, f"[UI] 没有按钮点击音效")
        except Exception as e:
            log.log(2, f"[UI] 加载按钮点击音效失败: {e}")
        self.hovered = False
        self.scale = [1.0, 1.0]
        self.base_color = [100, 100, 100]
        self.hover_color = [50, 50, 50]
        self.current_color = list(self.base_color)
        self.color_animating = False
        self.color_start = list(self.base_color)
        self.color_target = list(self.base_color)
        self.color_start_time = 0
        self.color_duration = 0.2
        self.is_clicking = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            was_hovered = self.hovered
            self.hovered = self.rect.collidepoint(event.pos)
            
            # 悬停动画
            if self.hovered and not was_hovered:
                # 开始放大动画
                self.animation.animate_scale(1.05, 1.05, duration=0.2, element=self)
                # 开始颜色过渡动画
                self._animate_color(self.hover_color)
            elif not self.hovered and was_hovered:
                # 恢复原始大小
                self.animation.animate_scale(1.0, 1.0, duration=0.2, element=self)
                # 恢复原始颜色
                self._animate_color(self.base_color)
                
        if event.type == pygame.MOUSEBUTTONDOWN and self.hovered:
            if self.callback:
                # 点击反馈动画
                self.is_clicking = True
                self.animation.animate_scale(0.95, 0.95, duration=0.1, element=self)
                if self.click_sound:
                    self.click_sound.play()
                self.callback()
                
        if event.type == pygame.MOUSEBUTTONUP and self.is_clicking:
            # 释放后恢复到悬停状态
            self.is_clicking = False
            if self.hovered:
                self.animation.animate_scale(1.05, 1.05, duration=0.1, element=self)
    
    def _animate_color(self, target_color):
        """开始颜色过渡动画"""
        import time
        self.color_start = list(self.current_color)
        self.color_target = list(target_color)
        self.color_start_time = time.perf_counter()
        self.color_duration = 0.2
        self.color_animating = True
    
    def update(self, dt):
        """更新按钮状态和动画"""
        super().update(dt)
        
        # 更新颜色动画
        if self.color_animating:
            import time
            now = time.perf_counter()
            elapsed = now - self.color_start_time
            t = min(elapsed / self.color_duration, 1.0)
            smooth_t = smooth_tween.ease_out_cubic(t)
            
            for i in range(3):
                self.current_color[i] = int(smooth_tween.lerp(self.color_start[i], self.color_target[i], smooth_t))
            
            if t >= 1.0:
                self.color_animating = False

    def draw(self, surface):
        # 使用动画后的颜色
        color = tuple(self.current_color)
        
        # 应用透明度
        if self.animation.current_alpha < 255:
            # 创建临时surface用于透明度混合
            temp_surface = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            color_with_alpha = (*color, self.animation.current_alpha)
            pygame.draw.rect(temp_surface, color_with_alpha, temp_surface.get_rect(), border_radius=10)
            surface.blit(temp_surface, self.rect.topleft)
            
            # 渲染带透明度的文本
            text_surf = self.font.render(self.text, True, (255, 255, 255))
            text_surf.set_alpha(self.animation.current_alpha)
            text_rect = text_surf.get_rect(center=self.rect.center)
            surface.blit(text_surf, text_rect)
        else:
            # 完全不透明时直接绘制
            pygame.draw.rect(surface, color, self.rect, border_radius=10)
            
            # 渲染文本
            text_surf = self.font.render(self.text, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=self.rect.center)
            surface.blit(text_surf, text_rect)


class UIImage(UIElement):
    def __init__(self, image_path, x, y, width, height, size_mode="cover", anchor="center", engine=None):
        super().__init__(x, y, width, height, anchor, engine)

        try:
            img = self.engine.resource_manager.load_image(image_path)
            self.pos = [x, y]
            self.scale = [width, height] if isinstance([width, height], list) else [1, 1]
            self.size_mode = size_mode
            self.original_img = img  # 保存原始图像，避免多次缩放导致模糊
            self._target_size = [img.get_width(), img.get_height()]

            self.image = img
            self.rect = None

            self.game_center = self.engine.center
            self.image_center = True
            self.image.convert_alpha()
            original_w, original_h = self.original_img.get_width(), self.original_img.get_height()
            target_w = self._target_size[0] * self.scale[0]
            target_h = self._target_size[1] * self.scale[1]

            final_w, final_h = original_w, original_h

            if self.size_mode == "auto":
                # 保持原始像素大小，仅应用 scale
                final_w = int(original_w * self.scale[0])
                final_h = int(original_h * self.scale[1])

            elif self.size_mode == "stretch":
                # 强制拉伸到目标区域
                final_w, final_h = int(target_w), int(target_h)

            elif self.size_mode == "contain":
                # 保持宽高比，完整显示在区域内
                if original_w == 0 or original_h == 0: return
                ratio = min(target_w / original_w, target_h / original_h)
                final_w, final_h = int(original_w * ratio), int(original_h * ratio)

            elif self.size_mode in ["fill", "cover"]:
                # 保持宽高比，填满区域（可能会超出或裁剪）
                if original_w == 0 or original_h == 0: return
                ratio = max(target_w / original_w, target_h / original_h)
                final_w, final_h = int(original_w * ratio), int(original_h * ratio)

            # 使用 smoothscale 获得更好的缩放质量
            self.image = pygame.transform.smoothscale(self.original_img, (max(1, final_w), max(1, final_h)))
            self.rect = self.image.get_rect(topleft=self.pos)
        except Exception as e:
            log.log(2, f"[UI] UIImage 加载异常: {e}")
            self.image = None

    def update(self, dt):
        """更新图片动画"""
        super().update(dt)
        
        # 如果正在缩放动画,重新计算图像大小
        if self.animation.scale_animating:
            self._update_image_size()

    def _update_image_size(self):
        """根据当前缩放值更新图像大小"""
        if not self.original_img:
            return
            
        original_w, original_h = self.original_img.get_width(), self.original_img.get_height()
        target_w = self._target_size[0] * self.scale[0]
        target_h = self._target_size[1] * self.scale[1]

        final_w, final_h = original_w, original_h

        if self.size_mode == "auto":
            final_w = int(original_w * self.scale[0])
            final_h = int(original_h * self.scale[1])
        elif self.size_mode == "stretch":
            final_w, final_h = int(target_w), int(target_h)
        elif self.size_mode == "contain":
            if original_w == 0 or original_h == 0: return
            ratio = min(target_w / original_w, target_h / original_h)
            final_w, final_h = int(original_w * ratio), int(original_h * ratio)
        elif self.size_mode in ["fill", "cover"]:
            if original_w == 0 or original_h == 0: return
            ratio = max(target_w / original_w, target_h / original_h)
            final_w, final_h = int(original_w * ratio), int(original_h * ratio)

        self.image = pygame.transform.smoothscale(self.original_img, (max(1, final_w), max(1, final_h)))
        self.rect = self.image.get_rect(topleft=self.pos)

    def draw(self, surface):
        if self.image:
            # 应用透明度
            if self.animation.current_alpha < 255:
                temp_image = self.image.copy()
                temp_image.set_alpha(self.animation.current_alpha)
                surface.blit(temp_image, self.rect.topleft)
            else:
                surface.blit(self.image, self.rect.topleft)


class UIText(UIElement):
    def __init__(self, text, x, y, size=24, color=(255, 255, 255), font_path=None, anchor="center", engine=None):
        super().__init__(x, y, 0, 0)
        self.full_text = text
        self.displayed_text = ""
        self.text = ""  # 用于兼容
        self.size = size
        self.color = color
        # 加载指定的字体，如果未指定则使用默认字体
        try:
            if font_path:
                font_path = f"{font_path}"
                self.font = pygame.font.Font(font_path, size)
            else:
                self.font = pygame.font.SysFont(None, size)
        except Exception as e:
            log.log(2, f"[UI] 加载字体失败: {e}")
            pygame.font.init()
            self.font = pygame.font.Font(None, size)
        
        # 打字机效果相关
        self.typewriter_enabled = False
        self.typewriter_speed = 0.05  # 每个字符的间隔时间(秒)
        self.typewriter_start_time = 0
        self.typewriter_index = 0
        self.typewriter_finished = False
        
        self.update_rect()

    def enable_typewriter(self, speed=0.05):
        """启用打字机效果"""
        self.typewriter_enabled = True
        self.typewriter_speed = speed
        self.typewriter_start_time = 0
        self.typewriter_index = 0
        self.typewriter_finished = False
        self.displayed_text = ""

    def disable_typewriter(self):
        """禁用打字机效果,显示完整文本"""
        self.typewriter_enabled = False
        self.displayed_text = self.full_text
        self.typewriter_finished = True
        self.update_rect()

    def update(self, dt):
        """更新文本动画"""
        super().update(dt)
        
        # 更新打字机效果
        if self.typewriter_enabled and not self.typewriter_finished:
            import time
            now = time.perf_counter()
            
            if self.typewriter_start_time == 0:
                self.typewriter_start_time = now
            
            elapsed = now - self.typewriter_start_time
            chars_to_show = int(elapsed / self.typewriter_speed)
            
            if chars_to_show >= len(self.full_text):
                self.displayed_text = self.full_text
                self.typewriter_finished = True
            else:
                self.displayed_text = self.full_text[:chars_to_show]
            
            self.text = self.displayed_text
            self.update_rect()

    def update_rect(self):
        surf = self.font.render(self.displayed_text if self.typewriter_enabled else self.full_text, True, self.color)
        self.rect.size = surf.get_size()

    def draw(self, surface):
        text_to_render = self.displayed_text if self.typewriter_enabled else self.full_text
        surf = self.font.render(text_to_render, True, self.color)
        
        # 应用透明度
        if self.animation.current_alpha < 255:
            surf.set_alpha(self.animation.current_alpha)
        
        surface.blit(surf, self.rect.topleft)


class UIRect(UIElement):
    def __init__(self, x, y, width, height, color=(255, 255, 255), border_radius=0, anchor="center", engine=None):
        super().__init__(x, y, width, height, anchor, engine)
        self.color = color
        self.rect = pygame.Rect(x, y, width, height)
        self.border_radius = border_radius

    def draw(self, surface):
        # 应用透明度
        if self.animation.current_alpha < 255:
            temp_surface = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            color_with_alpha = (*self.color, self.animation.current_alpha)
            pygame.draw.rect(temp_surface, color_with_alpha, temp_surface.get_rect(), border_radius=self.border_radius)
            surface.blit(temp_surface, self.rect.topleft)
        else:
            pygame.draw.rect(surface, self.color, self.rect, border_radius=self.border_radius)