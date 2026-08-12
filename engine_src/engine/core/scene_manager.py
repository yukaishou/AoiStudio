import pygame
from engine_src.engine.core import base_background, base_character
from engine_src.engine.core import base_sound
from engine_src.engine.core import log


class Scene:
    def __init__(self, engine):
        self.engine = engine
        self.backgrounds = []
        self.characters = []
        self.bgm = []

    def update(self):
        for background in self.backgrounds:
            background.update()
        for character in self.characters:
            character.update()
        for bgm in self.bgm:
            bgm.update()

    def draw(self, screen):
        for background in self.backgrounds:
            background.draw(screen)
        for character in self.characters:
            character.draw(screen)

    def add_background(self, image_path):
        background = base_background.BaseBackground(image_path, self.engine)

        self.backgrounds.append(background)
        return background

    def add_character(self, image_path, position):
        log.log(0, f"[SCENE] Adding character: {image_path}, {position}")
        character = base_character.BaseCharacter(image_path, position, self.engine)
        self.characters.append(character)
        return character

    def switch_background(self, background_path, way, speed):
        #先创建一个当前也就是0号背景,然后让那个复制的淡出，然后把0号背景换成新的背景就照了
        if len(self.backgrounds) == 0:
            self.add_background(background_path)
            return
        new_background = self.add_background(self.backgrounds[0].image_path)
        old_background = self.backgrounds[0].set_background(background_path)
        new_background.fade_out(speed)

    def switch_bgm(self, bgm_path, fade_speed):
        if len(self.bgm) > 0:
            self.bgm[0].fade_out(fade_speed)
            bgm = base_sound.BaseSound(bgm_path, self.engine)
            bgm.fade_in(fade_speed)
            self.bgm.append(bgm)
        else:
            bgm = base_sound.BaseSound(bgm_path, self.engine)
            bgm.play(-1)
            self.bgm.append(bgm)

    def change_scene_center(self, center):
        for character in self.characters:
            character.change_center(center)
        for background in self.backgrounds:
            background.change_center(center)