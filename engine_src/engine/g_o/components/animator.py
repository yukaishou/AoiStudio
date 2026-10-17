from engine_src.engine.core import log
from engine_src.engine.g_o import component_base


class Animator(component_base.ComponentBase):
    # 默认帧间隔：每帧 0.1 秒（10 FPS）
    DEFAULT_FRAME_INTERVAL = 0.1

    def __init__(self, game_object, properties: dict, engine):
        super().__init__(game_object, properties, engine)

        # 动画资源信息
        self.current_animation_type = "split_animation"  # "split_animation" | "tile_animation"
        self.current_animation_path = ""
        self.frames_surfaces = []
        self.keys = []

        # 播放参数
        self.animation_speed = float(self.properties.get("animation_speed", 1.0))
        self.animation_loop = bool(self.properties.get("animation_loop", False))
        # 每帧持续秒数（帧间隔），直接填 0.2 / 0.5 这种时间
        self.frame_interval = float(
            self.properties.get("frame_duration", self.DEFAULT_FRAME_INTERVAL)
        )

        # 播放状态
        self.playing = False
        self.finished = False
        self.current_frame_index = 0
        self.current_playing_time = 0.0  # 当前帧已播放秒数

        self.sprite_renderer = self.game_object.get_component("SpriteRenderer")
        if self.properties.get("animation_path"):
            self.load_animation_from_file(self.properties.get("animation_path"))

    # ------------------------------------------------------------------
    # 加载
    # ------------------------------------------------------------------

    def load_animation_from_file(self, file_path):
        """从 JSON 加载动画。自动判断瓦片动画 / 分片动画。"""
        content = self.engine.resource_manager.load_json_file(file_path)
        if not content:
            log.log(2, "load_animation_from_file: content is None")
            return

        if content.get("raw") is not None:
            frames = self._load_tile_animation(content)
            self.current_animation_type = "tile_animation"
        else:
            frames = self._load_split_animation(content)
            self.current_animation_type = "split_animation"

        self.frames_surfaces = frames
        self.keys = content.get("keys", [])
        self.frame_interval = self._resolve_frame_interval(content, len(frames))
        self.animation_speed = float(content.get("speed", 1.0))
        self.animation_loop = bool(content.get("loop", False))
        self.playing = bool(content.get("auto_play", False))
        self.current_animation_path = file_path

        # 重新加载后重置播放状态
        self.finished = False
        self.current_frame_index = 0
        self.current_playing_time = 0.0

    def _resolve_frame_interval(self, content, frame_count):
        """确定每帧时长（秒）。
        """
        if content.get("frame_duration") is not None:
            return float(content["frame_duration"])
        return self.DEFAULT_FRAME_INTERVAL

    def _load_tile_animation(self, content):
        """瓦片动画：一张大图里按行列切帧。"""
        image = self.engine.resource_manager.load_image(content["path"])
        return self.engine.image_tool.split_image(
            image,
            content["raw"],
            content["rate"],
            content["height"],
            content["width"],
            content["frames"],
        )

    def _load_split_animation(self, content):
        """分片动画：每帧一张独立图片。"""
        base_path = content["path"]
        frames = []
        num = 0
        for i in range(content["frames"]):
            frames.append(
                self.engine.resource_manager.load_image(base_path + "/" + str(num) + ".png")
            )
            num += 1
        return frames

    # ------------------------------------------------------------------
    # 播放控制
    # ------------------------------------------------------------------

    def set_animation(self, file_path, auto_play=True):
        """切换动画：重新加载并可选自动播放。"""
        self.load_animation_from_file(file_path)
        self.playing = auto_play
        if not auto_play:
            self.finished = False

    def play(self):
        """开始播放。非循环动画已播完时，从头再来。"""
        if not self.frames_surfaces:
            return
        if self.finished:
            self.current_frame_index = 0
            self.current_playing_time = 0.0
            self.finished = False
        self.playing = True

    def stop(self):
        """停止并回到第一帧。"""
        self.playing = False
        self.finished = False
        self.current_playing_time = 0.0
        self.current_frame_index = 0

    def pause(self):
        """暂停：保留当前帧和时间。"""
        self.playing = False

    def resume(self):
        """从暂停恢复。"""
        if self.frames_surfaces:
            self.playing = True

    # ------------------------------------------------------------------
    # 每帧更新
    # ------------------------------------------------------------------

    def update(self, dt: float):
        if not self.playing or not self.frames_surfaces:
            return

        frame_count = len(self.frames_surfaces)

        # 帧间隔无效：定格最后一帧并停止，避免除零 / 死循环
        if self.frame_interval <= 0:
            self.current_frame_index = frame_count - 1
            self.playing = False
            return

        # 累加“当前帧已播放时间”；speed 是倍率，实际每帧时长 = frame_interval / speed
        self.current_playing_time += dt * self.animation_speed

        # 用 while 而不是 if：防止单帧 dt 过大时跨过多帧丢失进度
        while self.current_playing_time >= self.frame_interval:
            self.current_playing_time -= self.frame_interval
            self.current_frame_index += 1

            if self.current_frame_index >= frame_count:
                if self.animation_loop:
                    self.current_frame_index = 0
                else:
                    # 非循环：停在最后一帧
                    self.current_frame_index = frame_count - 1
                    self.current_playing_time = 0.0
                    self.playing = False
                    self.finished = True
                    break

        if self.sprite_renderer:
            self.sprite_renderer.set_image(self.frames_surfaces[self.current_frame_index])

    # ------------------------------------------------------------------
    # 便捷查询
    # ------------------------------------------------------------------

    def is_playing(self):
        return self.playing

    def is_finished(self):
        """非循环动画是否已播完。"""
        return self.finished

    @property
    def total_duration(self):
        """整轮动画总时长（秒），仅用于查询。"""
        return self.frame_interval * len(self.frames_surfaces)

    def get_current_key(self):
        """返回当前帧对应的 key（如果 JSON 里提供了 keys 字段）。"""
        if 0 <= self.current_frame_index < len(self.keys):
            return self.keys[self.current_frame_index]
        return None