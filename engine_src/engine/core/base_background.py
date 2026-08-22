import pygame
from engine_src.engine.core import image
from engine_src.engine.utils import smooth_tween
from engine_src.engine.core import log

class BaseBackground():
    def __init__(self, image_path,engine):
        super().__init__()
        self.image_path = image_path
        self.engine = engine
        self.alpha = 255
        self.target_alpha = 255
        self.speed = 0.005
        self.is_fade_out = False
        self.image = engine.resource_manager.load_image(image_path)
        self.image_obj = image.Image(self.image,None,[0,0],[1,1],"fill",self.engine.get_center(),True)
        if self.engine.is_full_screen:
            self.image_obj.set_scale(self.engine.dpi.to_real_size([1,1]))
        else:
            self.image_obj.set_scale([1,1])
    def update(self):
        self.alpha = smooth_tween.lerp(self.alpha, self.target_alpha, self.speed)
        self.image_obj.set_alpha(self.alpha)
        if self.alpha <= 0.7:
            if self.is_fade_out:
                self.engine.scene.backgrounds.remove(self)


    def draw(self, screen):
        self.image_obj.draw(screen)

    def fade_out(self,speed=0.005):
        self.engine.event.emit("background_fade_out",{"background":self,"speed":speed})
        log.log(0,"fade out")
        self.is_fade_out = True
        self.speed = speed
        self.target_alpha = 0

    def set_background(self, image_path):
        self.engine.event.emit("background_change",{"background":self,"image_path":image_path})
        self.image_path = image_path
        self.image = self.engine.resource_manager.load_image(image_path)
        self.image_obj.set_image(self.image,None,[0,0],[1,1],"fill")

    def change_center(self,center):
        self.image_obj.set_center(center)
        if self.engine.is_full_screen:
            self.image_obj.set_scale(self.engine.dpi.to_real_size([1,1]))
        else:
            self.image_obj.set_scale([1,1])

