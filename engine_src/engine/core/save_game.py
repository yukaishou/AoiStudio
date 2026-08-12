import json
import os
from datetime import date
from engine_src.engine.core import log


class SaveGame:
    def __init__(self, engine):
        self.engine = engine

    def save_game(self, path):
        dialogue_file_path = self.engine.dialog.dialogue_file_path
        if self.engine.dialog.current_dialogue_index == 0:
            dialogue_index = self.engine.dialog.current_dialogue_index
        else:
            dialogue_index = self.engine.dialog.current_dialogue_index
        flags = list(self.engine.dialog.flags)
        characters_affection = self.engine.dialog.characters_affection
        if len(self.engine.scene.backgrounds) == 0:
            background_path = "None"
        else:
            background_path = f"file:{self.engine.scene.backgrounds[0].image_path}"
        history_texts = self.engine.dialog.history_text
        characters = []
        if len(self.engine.scene.bgm) == 0:
            bgm = "None"
        else:
            bgm = f"file:{self.engine.scene.bgm[len(self.engine.scene.bgm) - 1].path}"
        for i in self.engine.scene.characters:
            tmp_chr = {
                "image_path": i.image_path,
                "position": i.logic_target_position
            }
            characters.append(tmp_chr)
        save_game_data = {
            "format_version": 1,
            "time": f"{date.today().year}/{date.today().month}/{date.today().day}",
            "dialogue": {
                "file_path": f"file:{dialogue_file_path}",
                "index": dialogue_index
            },
            "variables": {
                "characters_affection": characters_affection
            },
            "flags": flags,
            "scene": {
                "now_background": f"{background_path}",
                "characters": characters,
                "bgm": f"{bgm}"
            },
            "history_text": history_texts

        }
        if not os.path.exists("saves"):
            os.mkdir("saves")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(save_game_data, f, ensure_ascii=False, indent=4)
        log.log(0, f"[SAVE] 完成存档写入：{path}")

    def load_game(self, path):
        if not os.path.exists(path):
            log.log(2, f"[SAVE] 存档不存在：{path}")
            return
        save_game_data = json.load(open(path, "r", encoding="utf-8"))
        for i in self.engine.scene.bgm:
            i.sound.stop()
        self.engine.scene.bgm = []
        self.engine.scene.backgrounds = []
        self.engine.scene.characters = []
        self.engine.dialog.history_text = []
        self.engine.dialog.load_dialogue(save_game_data["dialogue"]["file_path"][5:])
        self.engine.dialog.current_dialogue_index = save_game_data["dialogue"]["index"]
        if not save_game_data["scene"]["now_background"] == "None":
            self.engine.scene.add_background(save_game_data["scene"]["now_background"][5:])
        for i in save_game_data["scene"]["characters"]:
            self.engine.scene.add_character(i["image_path"], i["position"])
            # 限制角色数量,为了防止角色被加载的cfg脚本而加载其他角色
            self.engine.scene.characters = self.engine.scene.characters[:len(save_game_data["scene"]["characters"])]

        self.engine.dialog.flags = save_game_data["flags"]
        self.engine.dialog.characters_affection = save_game_data["variables"]["characters_affection"]
        self.engine.dialog.history_text = save_game_data["history_text"]
        if not save_game_data["scene"]["bgm"] == "None":
            self.engine.scene.switch_bgm(save_game_data["scene"]["bgm"][5:], 0.5)
        self.engine.dialog.start_dialogue(True)
        log.log(0, f"[SAVE] 成功读取存档：{path}")

    def init_solt(self):
        if not os.path.exists("saves"):
            os.mkdir("saves")
            log.log(0, "[SAVE] 创建存档目录 saves")

    def load_solt(self, solt_index):
        self.load_game(f"saves/save_solt{solt_index}.save")

    def save_solt(self, solt_index):
        self.init_solt()
        self.save_game(f"saves/save_solt{solt_index}.save")

    def get_solt_path(self, solt_index):
        return f"saves/save_solt{solt_index}.save"