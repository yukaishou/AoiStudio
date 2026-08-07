import json
import os
from datetime import date

class SaveGame:
    def __init__(self,engine):
        self.engine = engine

    def save_game(self,path):
        dialogue_file_path = self.engine.dialog.dialogue_file_path
        if self.engine.dialog.current_dialogue_index == 0:
            dialogue_index = self.engine.dialog.current_dialogue_index
        else:
            dialogue_index = self.engine.dialog.current_dialogue_index -1
        flags = list(self.engine.dialog.flags)
        characters_affection = self.engine.dialog.characters_affection
        background_path = self.engine.scene.backgrounds[0].image_path
        history_texts = self.engine.dialog.history_text
        characters = []
        for i in self.engine.scene.characters:
            tmp_chr = {
                "image_path": i.image_path,
                "position":i.logic_target_position
            }
            characters.append(tmp_chr)
        save_game_data = {
    "format_version":1,
    "time":f"{date.today().year}/{date.today().month}/{date.today().day}",
    "dialogue":{
        "file_path":f"file:{dialogue_file_path}",
        "index":dialogue_index
    },
    "variables":{
        "characters_affection":characters_affection
    },
    "flags":flags,
    "scene":{
        "now_background":f"file:{background_path}",
        "characters":characters,
        "bgm":f"file:{self.engine.scene.bgm[len(self.engine.scene.bgm)-1].path}"
    },
    "history_text": history_texts

}
        with open(path,"w",encoding="utf-8") as f:
            json.dump(save_game_data,f,ensure_ascii=False,indent=4)

    def load_game(self,path):
        if not os.path.exists(path):
            print("存档不存在")
            return
        save_game_data = json.load(open(path,"r",encoding="utf-8"))
        for i in self.engine.scene.bgm:
            i.sound.stop()
        self.engine.scene.bgm = []
        self.engine.scene.backgrounds = []
        self.engine.scene.characters = []
        self.engine.dialog.load_dialogue(save_game_data["dialogue"]["file_path"][5:])
        self.engine.dialog.current_dialogue_index = save_game_data["dialogue"]["index"]
        self.engine.scene.add_background(save_game_data["scene"]["now_background"][5:])
        for i in save_game_data["scene"]["characters"]:
            self.engine.scene.add_character(i["image_path"],i["position"])
        self.engine.dialog.flags = save_game_data["flags"]
        self.engine.dialog.characters_affection = save_game_data["variables"]["characters_affection"]
        self.engine.dialog.history_text = save_game_data["history_text"]
        self.engine.scene.switch_bgm(save_game_data["scene"]["bgm"][5:],0.5)
        self.engine.dialog.start_dialogue(True)

    def init_solt(self):
        if not os.path.exists("saves"):
            os.mkdir("saves")

    def load_solt(self,solt_index):
        self.load_game(f"saves/save_solt{solt_index}.json")

    def save_solt(self,solt_index):
        self.init_solt()
        self.save_game(f"saves/save_solt{solt_index}.json")

    def get_solt_path(self,solt_index):
        return f"saves/save_solt{solt_index}.json"
