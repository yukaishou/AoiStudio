import pygame
from .ui_element import UIElement

class UIButton(UIElement):
    def __init__(self, text, x, y, width, height, hit_sound_path=None, callback=None, font_path=None,anchor="center",engine = None):
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
            print(f"加载按钮字体失败: {e}")
            pygame.font.init()
            self.font = pygame.font.Font(None, 24)
        # 加载点击音效
        try:
            if hit_sound_path:
                self.click_sound = self.engine.resource_manager.load_sound(hit_sound_path)
                print("加载按钮点击音效成功")
            else:
                self.click_sound = None
                print("没有按钮点击音效")
        except Exception as e:
            print(f"加载按钮点击音效失败: {e}")
        self.hovered = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and self.hovered:
            if self.callback:
                if self.click_sound:
                    self.click_sound.play()
                self.callback()

    def draw(self, surface):
        color = (50, 50, 50) if self.hovered else (100, 100, 100)
        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        text_surf = self.font.render(self.text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

class UIImage(UIElement):
    def __init__(self, image_path, x, y, width, height,size_mode="cover",anchor="center",engine= None):
        super().__init__(x, y, width, height , anchor, engine)

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
            print(e)
            self.image = None

    def draw(self, surface):
        if self.image:
            surface.blit(self.image, self.rect.topleft)

class UIText(UIElement):
    def __init__(self, text, x, y, size=24, color=(255, 255, 255), font_path=None, anchor="center",engine= None):
        super().__init__(x, y, 0, 0)
        self.text = text
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
            print(f"加载字体失败: {e}")
            pygame.font.init()
            self.font = pygame.font.Font(None, size)
        self.update_rect()

    def update_rect(self):
        surf = self.font.render(self.text, True, self.color)
        self.rect.size = surf.get_size()

    def draw(self, surface):
        surf = self.font.render(self.text, True, self.color)
        surface.blit(surf, self.rect.topleft)

class UIRect(UIElement):
    def __init__(self, x, y, width, height, color=(255, 255, 255),border_radius=0, anchor="center",engine= None):
        super().__init__(x, y, width, height, anchor, engine)
        self.color = color
        self.rect = pygame.Rect(x, y, width, height)
        self.border_radius = border_radius
    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=self.border_radius)