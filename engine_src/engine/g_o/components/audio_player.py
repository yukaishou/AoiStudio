from engine_src.engine.g_o.component_base import ComponentBase
from engine_src.engine.core.base_sound import BaseSound


class AudioPlayer(ComponentBase):
    def __init__(self, game_object, properties, engine):
        super().__init__(game_object, properties, engine)
        self.sound_path = properties.get("sound_path", "")
        self.volume = float(properties.get("volume", 0.5))
        self.loops = int(properties.get("loops", 0))
        self.auto_play = bool(properties.get("auto_play", False))

        self.base_sound: BaseSound | None = None

    def start(self):
        """GameObject 创建后执行一次"""
        if not self.sound_path:
            return
        self.base_sound = BaseSound(self.sound_path, self.engine)
        self.base_sound.volume = self.volume
        self.base_sound.target_volume = self.volume
        if self.auto_play:
            self.play()

    def update(self, dt):
        """每帧更新淡入淡出逻辑"""
        if self.base_sound:
            self.base_sound.update()

    def play(self, loops=None):
        """播放音频"""
        if self.base_sound:
            loops = loops if loops is not None else self.loops
            self.base_sound.play(loops)

    def stop(self):
        """停止播放"""
        if self.base_sound:
            self.base_sound.sound.stop()

    def set_volume(self, value: float):
        """设置音量 (0.0 ~ 1.0)"""
        self.volume = max(0.0, min(1.0, value))
        if self.base_sound:
            self.base_sound.target_volume = self.volume

    def fade(self, target: float, speed: float):
        """淡入淡出到目标音量"""
        if self.base_sound:
            self.base_sound.fade(target, speed)

    def fade_out(self, speed: float = 0.1):
        """淡出"""
        if self.base_sound:
            self.base_sound.fade_out(speed)

    def fade_in(self, speed: float = 0.1):
        """淡入"""
        if self.base_sound:
            self.base_sound.fade_in(speed)

    def set_sound_path(self, path: str):
        """更换音频路径"""
        self.sound_path = path
        if self.base_sound:
            new_sound = self.engine.resource_manager.load_sound(path)
            if new_sound:
                self.base_sound.sound = new_sound
                self.base_sound.path = path
                self.base_sound.volume = self.volume
                self.base_sound.target_volume = self.volume

    def get_base_sound(self) -> BaseSound | None:
        return self.base_sound

    def destroy(self):
        """组件销毁"""
        if self.base_sound:
            self.base_sound.sound.stop()
        self.base_sound = None
