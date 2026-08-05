import pygame
import time
import random
from engine_src.engine.core import image
from engine_src.engine.utils import smooth_tween


class BaseCharacter:
    def __init__(self, character_image_path, position, engine):
        self.image_path = character_image_path
        self.move_type = "linear"
        self.speed = 1.0
        self.engine = engine
        # 存储逻辑坐标
        self.logic_position = position.copy()
        self.logic_target_position = position.copy()
        self._pos_finished = True

        # ========= 时间驱动动画：透明度 0.0~1.0 =========
        self.alpha = 1.0
        self.target_alpha = 1.0
        self._alpha_start_time = 0.0
        self._alpha_start_val = 1.0
        self._alpha_duration = 0.0
        self._alpha_ease_func = smooth_tween.linear
        self._alpha_finished = True

        # ========= 时间驱动动画：缩放（逻辑缩放比例） =========
        self.logic_scale = [1.0, 1.0]
        self.logic_target_scale = [1.0, 1.0]
        self._scale_start_time = 0.0
        self._scale_start_val = [1.0, 1.0]
        self._scale_duration = 0.0
        self._scale_ease_func = smooth_tween.linear
        self._scale_finished = True

        # 抖动（逻辑幅度）
        self.shake_active = False
        self.logic_shake_magnitude = 0.0
        self.shake_duration = 0.0
        self.shake_max_duration = 0.0
        self._shake_offset = [0.0, 0.0]

        # 闪烁
        self.blink_active = False
        self.blink_interval = 0.2
        self.blink_timer = 0.0

        # ========= GAL演出跳跃：逻辑高度 =========
        self._jump_active = False
        self._jump_start_time = 0.0
        self._jump_duration = 0.0
        self.logic_jump_height = 0.0
        self._jump_offset_y = 0.0

        # ========= 立绘淡入淡出切换状态 =========
        self._sprite_switching = False
        self._sprite_switch_phase = 0  # 0:空闲 1:淡出中 2:换图瞬间 3:淡入中
        self._sprite_switch_fade_out = 0.25
        self._sprite_switch_fade_in = 0.25
        self._sprite_pending_path = None

        # 初始化Image，使用逻辑坐标与缩放
        self.character_image = image.Image(
            img=self.engine.resource_manager.load_image(character_image_path),
            pos=self.logic_position,
            scale=self.logic_scale,
            size_mode="fill",
            center=engine.get_center(),
            image_center=True
        )
        # 应用DPI缩放
        self._apply_dpi_scale()

    def update(self):
        now = time.perf_counter()
        dt = self.engine.delta_time if hasattr(self.engine, "delta_time") else 0.016

        # ====================== 立绘切换状态机（淡出‑换图‑淡入） ======================
        if self._sprite_switching:
            if self._sprite_switch_phase == 1:
                # 淡出阶段，等待淡出完成
                if self._alpha_finished:
                    self._sprite_switch_phase = 2
            elif self._sprite_switch_phase == 2:
                # 瞬间切换图片资源，使用Image.set_image
                new_surface = self.engine.resource_manager.load_image(self._sprite_pending_path)
                self.character_image.set_image(img=new_surface)
                self._sprite_switch_phase = 3
                # 开始淡入
                self.fade_to(1.0, duration=self._sprite_switch_fade_in)
            elif self._sprite_switch_phase == 3:
                if self._alpha_finished:
                    self._sprite_switching = False
                    self._sprite_switch_phase = 0
                    self._sprite_pending_path = None

        # ====================== 位置：原始残差lerp（线性插值，逻辑坐标） ======================
        if self.move_type == "linear":
            self.logic_position = [
                smooth_tween.lerp(self.logic_position[0], self.logic_target_position[0], self.speed),
                smooth_tween.lerp(self.logic_position[1], self.logic_target_position[1], self.speed)
            ]
            eps = 0.5
            arrived_x = abs(self.logic_position[0] - self.logic_target_position[0]) < eps
            arrived_y = abs(self.logic_position[1] - self.logic_target_position[1]) < eps
            self._pos_finished = arrived_x and arrived_y

        # ====================== GAL抛物线跳跃演出（逻辑高度） ======================
        if self._jump_active:
            elapsed = now - self._jump_start_time
            t = min(elapsed / self._jump_duration, 1.0)
            self._jump_offset_y = -4 * self.logic_jump_height * t * (1 - t)
            if t >= 1.0:
                self._jump_active = False
                self._jump_offset_y = 0.0

        # -------------------------- 透明度tween --------------------------
        if not self._alpha_finished:
            a_val, finished_a = smooth_tween.get_tween_value(
                self._alpha_start_val, self.target_alpha,
                self._alpha_start_time, self._alpha_duration,
                self._alpha_ease_func, now
            )
            self.alpha = a_val
            self._alpha_finished = finished_a
            # 转0‑1浮点数 → 0‑255整数，调用Image.set_alpha
            self.character_image.set_alpha(int(max(0.0, min(1.0, self.alpha)) * 255))

        # -------------------------- 缩放tween（逻辑缩放） --------------------------
        if not self._scale_finished:
            sx, finished_sx = smooth_tween.get_tween_value(
                self._scale_start_val[0], self.logic_target_scale[0],
                self._scale_start_time, self._scale_duration,
                self._scale_ease_func, now
            )
            sy, finished_sy = smooth_tween.get_tween_value(
                self._scale_start_val[1], self.logic_target_scale[1],
                self._scale_start_time, self._scale_duration,
                self._scale_ease_func, now
            )
            self.logic_scale[0] = sx
            self.logic_scale[1] = sy
            self._scale_finished = finished_sx and finished_sy
            # 应用DPI缩放后的实际缩放
            real_scale = self.engine.dpi.to_real_size(self.logic_scale)
            self.character_image.scale = real_scale.copy()
            self.character_image._update_scaled_image()

        # -------------------------- 抖动动画（逻辑幅度） --------------------------
        if self.shake_active:
            self.shake_duration -= dt
            if self.shake_duration <= 0:
                self.shake_active = False
                self._shake_offset = [0.0, 0.0]
            else:
                decay = self.shake_duration / self.shake_max_duration
                mag = self.logic_shake_magnitude * decay
                self._shake_offset[0] = random.uniform(-mag, mag)
                self._shake_offset[1] = random.uniform(-mag, mag)
        else:
            self._shake_offset = [0.0, 0.0]

        # -------------------------- 闪烁动画 --------------------------
        if self.blink_active:
            self.blink_timer += dt
            if self.blink_timer >= self.blink_interval:
                self.blink_timer = 0.0
                if abs(self.alpha) > 0.1:
                    self.fade_to(0.0, duration=self.blink_interval*0.4)
                else:
                    self.fade_to(1.0, duration=self.blink_interval*0.4)

        # ====================== 统一DPI坐标转换：逻辑 → 物理 ======================
        # 逻辑位置 + 抖动偏移 + 跳跃偏移 → 物理渲染位置
        logic_render_x = self.logic_position[0] + self._shake_offset[0]
        logic_render_y = self.logic_position[1] + self._shake_offset[1] + self._jump_offset_y
        if self.engine.is_full_screen:
            real_render_pos = self.engine.dpi.to_real(logic_render_x, logic_render_y)
        else:
            real_render_pos = (logic_render_x, logic_render_y)
        self.character_image.set_pos(real_render_pos)

    def draw(self, screen):
        self.character_image.draw(screen)

    def move_to(self, position, move_type="linear", speed=1.0):
        # 传入逻辑坐标
        self.logic_target_position = position.copy()
        self.move_type = move_type
        self.speed = speed
        self._pos_finished = False

    # ============ 对外动画API ============
    def fade_to(self, alpha, duration=0.3, ease_func=None):
        # 执行手动淡入淡出时自动停止闪烁，避免动画冲突
        self.stop_blink()
        self.target_alpha = alpha
        self._alpha_start_time = time.perf_counter()
        self._alpha_start_val = self.alpha
        self._alpha_duration = duration
        self._alpha_ease_func = ease_func if ease_func else smooth_tween.linear
        self._alpha_finished = False

    def scale_to(self, scale_x, scale_y, duration=0.3, ease_func=None):
        # 传入逻辑缩放比例
        self.logic_target_scale[0] = scale_x
        self.logic_target_scale[1] = scale_y
        self._scale_start_time = time.perf_counter()
        self._scale_start_val = self.logic_scale.copy()
        self._scale_duration = duration
        self._scale_ease_func = ease_func if ease_func else smooth_tween.linear
        self._scale_finished = False

    def shake(self, magnitude=8.0, duration=0.5):
        # 传入逻辑幅度
        self.shake_active = True
        self.logic_shake_magnitude = magnitude
        self.shake_duration = duration
        self.shake_max_duration = duration

    def start_blink(self, interval=0.18):
        self.blink_active = True
        self.blink_interval = interval
        self.blink_timer = 0.0

    def stop_blink(self):
        self.blink_active = False

    def is_move_finished(self):
        return self._pos_finished

    # ========= GAL演出跳跃函数 =========
    def jump(self, jump_height=60, duration=0.4):
        """
        GalGame角色演出跳一跳，只视觉上浮下落，逻辑坐标不变
        :param jump_height: 跳跃最大高度(逻辑像素)
        :param duration: 整段跳跃时间(秒)，包含上升+下落
        """
        self._jump_active = True
        self._jump_start_time = time.perf_counter()
        self.logic_jump_height = jump_height
        self._jump_duration = duration

    def is_jump_finished(self):
        return not self._jump_active

    # ========= 新增：淡入淡出切换立绘图像 =========
    def change_sprite(self, image_path, fade_out=0.25, fade_in=0.25):
        """
        平滑切换角色立绘：淡出 → 替换资源 → 淡入
        :param image_path: 新立绘资源路径
        :param fade_out: 淡出耗时(秒)
        :param fade_in: 淡入耗时(秒)
        """
        if self._sprite_switching:
            return
        self._sprite_switching = True
        self._sprite_switch_phase = 1
        self._sprite_switch_fade_out = fade_out
        self._sprite_switch_fade_in = fade_in
        self._sprite_pending_path = image_path
        self.fade_to(0.0, duration=fade_out)

    def is_sprite_switch_finished(self):
        """剧情等待：立绘切换动画是否全部完成"""
        return not self._sprite_switching

    def reset_animation(self):
        """一键重置全部动画状态，切场景/清除角色状态时调用"""
        self.stop_blink()
        self.shake_active = False
        self._shake_offset = [0.0,0.0]
        self._jump_active = False
        self._jump_offset_y = 0.0
        self._sprite_switching = False
        self._sprite_switch_phase = 0
        self._sprite_pending_path = None

        self.alpha = 1.0
        self.target_alpha = 1.0
        self._alpha_finished = True
        self.character_image.set_alpha(255)

        # 重置逻辑缩放
        self.logic_scale = [1.0,1.0]
        self.logic_target_scale = [1.0,1.0]
        self._scale_finished = True
        # 应用DPI缩放
        self._apply_dpi_scale()

    def change_center(self, center):
        # center为逻辑坐标，转换为物理坐标后设置
        if not self.engine.is_full_screen:
            real_center = center
        else:
            real_center = center
        self.character_image.set_center(real_center)
        # 应用DPI缩放
        self._apply_dpi_scale()

    def _apply_dpi_scale(self):
        """内部方法：统一应用DPI缩放到Image"""
        if not self.engine.is_full_screen:
            self.character_image.set_scale(self.logic_scale)
            return
        real_scale = self.engine.dpi.to_real_size(self.logic_scale)
        self.character_image.set_scale(real_scale)
        self.character_image._update_scaled_image()


