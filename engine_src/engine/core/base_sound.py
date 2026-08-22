import pygame
from engine_src.engine.utils import smooth_tween

class BaseSound:
    def __init__(self,path,engine):
        self.path = path
        self.sound = engine.resource_manager.load_sound(path)
        self.volume = 0.5
        self.target_volume = 0.5
        self.speed = 0.1
        self.is_fade_out = False
        self.engine = engine

    def play(self,loops):
        self.engine.event.emit("sound_play",{"sound_path":self.path,"loops":loops})
        self.sound.play(loops= loops)

    def update(self):
        self.volume = smooth_tween.lerp(self.volume,self.target_volume,self.speed)
        self.sound.set_volume(self.volume)
        if self.is_fade_out:
            if self.volume <= 0.1:
                self.sound.stop()
                self.engine.scene.bgm.remove(self)


    def fade(self,target,speed):
        self.engine.event.emit("sound_fade",{"sound_path":self.path,"target_volume":target,"speed":speed})
        self.target_volume = target
        self.speed = speed

    def fade_out(self,speed):
        self.engine.event.emit("sound_fade_out",{"sound_path":self.path,"speed":speed})
        self.is_fade_out = True
        self.fade(0,speed)

    def fade_in(self,speed):
        self.engine.event.emit("sound_fade_in",{"sound_path":self.path,"speed":speed})
        self.play(-1)
        self.fade(0.5,speed)
