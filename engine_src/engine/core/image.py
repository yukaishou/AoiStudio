# engine_src/engine/scene/image.py
import pygame


class Image:
    def __init__(self, img=None, size=None, pos=None, scale=None, size_mode="auto",center=None,image_center=False):
        """
        初始化图像对象
        :param img: pygame.Surface 对象
        :param size: [width, height] 目标显示区域大小
        :param pos: [x, y] 位置
        :param scale: [scale_x, scale_y] 额外缩放比例
        :param size_mode: 尺寸模式 (auto, stretch, fill, contain, cover)
        """
        self.pos = pos or [0, 0]
        self.scale = scale if isinstance(scale, list) else [1, 1]
        self.size_mode = size_mode
        self.original_img = img  # 保存原始图像，避免多次缩放导致模糊

        # 确定目标区域大小
        if img:
            self._target_size = size or [img.get_width(), img.get_height()]
        else:
            self._target_size = size or [50, 50]

        self.image = None
        self.rect = None
        if img:
            self._update_scaled_image()
        self.game_center = center or [0, 0]
        self.image_center = image_center
        self.image.convert_alpha()


    def _update_scaled_image(self):
        """根据当前的 size_mode 和 scale 重新计算最终显示的图像"""
        if not self.original_img:
            return

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

    def draw(self, surface):
        if self.image is None:
            return

        # 处理偏移
        offset = self.game_center
        image_center_offset = [self.image.get_width() / 2, self.image.get_height() / 2] or [0, 0]

        if self.image_center:
            draw_pos = [int(self.pos[0] + offset[0] - image_center_offset[0]),
                        int(self.pos[1] + offset[1] - image_center_offset[1])]
        else:
            draw_pos = [int(self.pos[0] + offset[0]),
                    int(self.pos[1] + offset[1])]

        surface.blit(self.image, draw_pos)

    def set_pos(self, pos):
        self.pos = pos
        if self.image:
            self.rect.topleft = self.pos

    def get_pos(self):
        return self.pos

    def set_image(self, img=None, size=None, pos=None, scale=None, size_mode=None):
        """动态更换图像"""
        if pos: self.pos = pos
        if scale: self.scale = scale if isinstance(scale, list) else [1, 1]
        if size_mode: self.size_mode = size_mode
        if size: self._target_size = size

        if img:
            self.original_img = img
            if not size: self._target_size = [img.get_width(), img.get_height()]
            self._update_scaled_image()
        else:
            self.image = None
            self.rect = None

    def get_image(self):
        return self.image

    def set_size(self, size):
        self._target_size = size
        self._update_scaled_image()

    def get_size(self):
        return self._target_size

    def set_scale(self, scale):
        self.scale = scale
        self._update_scaled_image()

    def get_scale(self):
        return self.scale

    # --- 碰撞检测逻辑 ---
    def collide_point(self, pos):
        if self.image is None:
            return False
        offset = self.game_center


        # 计算实际绘制位置的相对坐标
        actual_x = pos[0] - (self.pos[0] + offset[0])
        actual_y = pos[1] - (self.pos[1] + offset[1])
        return self.image.get_rect().collidepoint(actual_x, actual_y)

    def collide_other(self, other):
        if self.image is None or other.image is None:
            return False
        offset = self.game_center


        my_rect = self.image.get_rect(topleft=(self.pos[0] + offset[0], self.pos[1] + offset[1]))
        other_rect = other.image.get_rect(topleft=(other.pos[0] + offset[0], other.pos[1] + offset[1]))
        return my_rect.colliderect(other_rect)

    def set_alpha(self, alpha):
        if self.image:
            self.image.set_alpha(alpha)

    def set_center(self, center):
        self.game_center = center

