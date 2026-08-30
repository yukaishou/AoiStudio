import threading
import time

import pygame

from engine_src.engine.core import log
from engine_src.engine.utils import smooth_tween


class BaseSound:
    def __init__(self, path, engine):
        self.path = path
        self.sound = None
        self.engine = engine

        self._lock = threading.Lock()

        self.volume = 0.0
        self.target_volume = 0.5
        self.speed = 0.1
        self.is_fade_out = False
        self.load_finished = False
        self.load_failed = False
        self.is_playing = False

        threading.Thread(target=self._load_sound_thread, daemon=True).start()

    def _load_sound_thread(self):
        success = True
        exc_info = None
        try:
            self.sound = self.engine.resource_manager.load_sound(self.path)
        except Exception as e:
            success = False
            exc_info = str(e)

        with self._lock:
            if not success:
                self.load_failed = True
            self.load_finished = True

        if not success and exc_info is not None:
            # emit放到锁外面
            self.engine.event.emit("sound_load_error", {"path": self.path, "error": exc_info})

    def play(self, loops: int):
        with self._lock:
            if self.is_playing:
                return
        threading.Thread(target=self._play_thread, args=(loops,), daemon=True).start()

    def _play_thread(self, loops):
        # 修复：同时判断加载完成 OR 加载失败，防止死循环
        while True:
            with self._lock:
                if self.load_finished or self.load_failed:
                    break
            time.sleep(0.1)

        # 锁内拷贝状态，锁外做事件与播放
        sound_obj = None
        vol = 0.0
        with self._lock:
            if self.load_failed or self.sound is None:
                return
            sound_obj = self.sound
            vol = self.volume
            self.is_playing = True

        # ⚠️ emit、pygame操作全部移出锁块！防止事件回调死锁
        self.engine.event.emit("sound_play", {"sound_path": self.path, "loops": loops})
        sound_obj.set_volume(vol)
        sound_obj.play(loops=loops)

    def update(self):
        need_remove = False
        with self._lock:
            if not self.load_finished or self.load_failed or self.sound is None:
                return
            if not self.sound.get_num_channels():
                self.is_playing = False
                return

            self.volume = smooth_tween.lerp(self.volume, self.target_volume, self.speed)
            self.sound.set_volume(self.volume)

            if self.is_fade_out:
                if abs(self.volume) <= 0.01:
                    self.sound.stop()
                    self.is_playing = False
                    self.is_fade_out = False
                    need_remove = True

        # 移出锁块操作外部列表，避免交叉锁
        if need_remove:
            try:
                self.engine.scene.bgm.remove(self)
            except (ValueError, AttributeError):
                pass

    def fade(self, target: float, speed: float):
        # 先拷贝参数，锁只改成员，emit放到外面
        with self._lock:
            self.target_volume = target
            self.speed = speed
        self.engine.event.emit("sound_fade", {"sound_path": self.path, "target_volume": target, "speed": speed})

    def fade_out(self, speed: float):
        with self._lock:
            self.is_fade_out = True
            self.target_volume = 0.0
            self.speed = speed
        self.engine.event.emit("sound_fade_out", {"sound_path": self.path, "speed": speed})

    def fade_in(self, speed: float, target_volume: float = 0.5):
        should_play = False
        with self._lock:
            if not self.is_playing:
                should_play = True
            self.target_volume = target_volume
            self.speed = speed
        self.engine.event.emit("sound_fade_in", {"sound_path": self.path, "speed": speed})
        if should_play:
            self.play(-1)

    def stop(self):
        snd = None
        with self._lock:
            if self.sound and self.load_finished and not self.load_failed:
                snd = self.sound
            self.is_playing = False
            self.is_fade_out = False
        if snd is not None:
            snd.stop()

    def pause(self):
        pass


class BaseMusic:
    """
    BGM 音乐类 - 使用 pygame.mixer.music
    
    与 BaseSound 的区别：
    - BaseSound: 短音效，使用 pygame.mixer.Sound，加载到内存
    - BaseMusic: 长音乐(BGM)，使用 pygame.mixer.music，流式播放
    已弃用，建议使用BaseSound来播放BGM
    """
    
    def __init__(self, path, engine):
        self.path = path
        self.engine = engine
        
        self._lock = threading.Lock()
        
        self.volume = 0.5
        self.target_volume = 0.5
        self.speed = 0.1
        self.is_fade_out = False
        self.load_finished = False
        self.load_failed = False
        self.is_playing = False
        
        # 异步加载音乐
        threading.Thread(target=self._load_music_thread, daemon=True).start()
    
    def _load_music_thread(self):
        """加载音乐文件"""
        try:
            # 使用 resource_manager 的 load_music 方法
            success = self.engine.resource_manager.load_music(self.path)
            with self._lock:
                if success:
                    self.load_finished = True
                    log.log(0, f"[MUSIC] 加载成功: {self.path}")
                else:
                    self.load_failed = True
                    log.log(2, f"[MUSIC] 加载失败: {self.path}")
        except Exception as e:
            with self._lock:
                self.load_failed = True
            self.engine.event.emit("music_load_error", {"path": self.path, "error": str(e)})
            log.log(2, f"[MUSIC] 加载异常: {repr(e)}")
    
    def play(self, loops: int = -1):
        """播放音乐，loops=-1无限循环"""
        if self.is_playing:
            return

        if self.load_failed:
                return
        if not self.load_finished:
            return
        # 停止之前的音乐（pygame.mixer.music 是全局单例）
        pygame.mixer.music.stop()

        self.engine.event.emit("music_play", {"music_path": self.path, "loops": loops})
        pygame.mixer.music.set_volume(self.volume)
        pygame.mixer.music.play(loops=loops)
        self.is_playing = True

    def update(self):
        """每帧调用，音量插值更新"""
        if not self.load_finished or self.load_failed:
            return

        # 检查是否还在播放
        if not pygame.mixer.music.get_busy():
            self.is_playing = False
            return

        # 音量淡入淡出
        self.volume = smooth_tween.lerp(self.volume, self.target_volume, self.speed)
        pygame.mixer.music.set_volume(self.volume)

        if self.is_fade_out:
            if abs(self.volume) <= 0.01:
                pygame.mixer.music.stop()
                self.is_playing = False
                try:
                    self.engine.scene.bgm.remove(self)
                except (ValueError, AttributeError):
                    pass

    def fade(self, target: float, speed: float):
        """设置淡入淡出目标"""
        self.engine.event.emit("music_fade", {"music_path": self.path, "target_volume": target, "speed": speed})
        self.target_volume = target
        self.speed = speed

    def fade_out(self, speed: float):
        """淡出"""
        self.engine.event.emit("music_fade_out", {"music_path": self.path, "speed": speed})
        self.is_fade_out = True
        self.fade(0.0, speed)

    
    def fade_in(self, speed: float, target_volume: float = 0.5):
        """淡入"""
        self.engine.event.emit("music_fade_in", {"music_path": self.path, "speed": speed})
        if not self.is_playing:
            self.play(-1)
        self.fade(target_volume, speed)

    
    def stop(self):
        """立即停止"""
        if self.load_finished and not self.load_failed:
            pygame.mixer.music.stop()
        self.is_playing = False
        self.is_fade_out = False

    
    def pause(self):
        """暂停"""
        pygame.mixer.music.pause()
    
    def unpause(self):
        """恢复播放"""
        pygame.mixer.music.unpause()
