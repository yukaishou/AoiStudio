import pygame
import json
import operator
import re
from engine_src.engine.core import log

def parse_and_eval(condition_str, context):
    # 1. 拆解 (支持 >=, <=, ==, !=, >, <)
    parts = re.split(r'(>=|<=|==|!=|>|<)', condition_str)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) != 3:
        raise ValueError(f"条件表达式格式错误: {condition_str}")

    var, op_str, val_str = parts
    # 支持整数、小数
    if "." in val_str:
        val = float(val_str)
    else:
        val = int(val_str)

    # 运算符映射
    ops = {
        '>=': operator.ge, '<=': operator.le,
        '==': operator.eq, '!=': operator.ne,
        '>': operator.gt, '<': operator.lt
    }
    # 从上下文中获取实际数值，变量不存在默认0
    real_val = context.get(var, 0)
    return ops[op_str](real_val, val)


class Dialogue:
    def __init__(self, engine):
        self.engine = engine
        self.dialogue = {}
        self.current_dialogue_index = 0
        self.is_choice_active = False
        self.auto_mode = False
        self.this_dialogue_is_finished = False
        self.dialogue_file_path = None
        self.history_text = []
        # flags改为集合，自动去重，判断存在更快
        self.flags = set()
        # 好感：key=角色名，value=数值，替换原来的list列表
        self.characters_affection = {}
        # 缓存当前激活的选项数据
        self._active_options = []
        characters_config = json.load(open("config/characters.json","r",encoding="utf-8"))
        for i in characters_config["characters"]:
            self.characters_affection[i["name"]] = 0
    def _norm_empty(self, val: str) -> str:
        """统一空值处理："" 和 "None" 归一为 "None"""
        if not isinstance(val, str):
            return "None"
        val = val.strip()
        return "None" if val in ("", "None") else val

    def load_dialogue(self, file_path):
        self.this_dialogue_is_finished = False
        self.current_dialogue_index = 0
        self.dialogue = self.engine.resource_manager.load_json_file(file_path)
        self.dialogue_file_path = file_path
        return self.dialogue

    def _on_option_selected(self, opt_index: int):
        """统一选项回调入口"""
        self.is_choice_active = False
        self.engine.dialog_choice.set_active(False)

        opt_data = self._active_options[opt_index]
        opt_script = self._norm_empty(opt_data["script"])

        # 执行选项附带脚本（好感增减写在这里）
        if opt_script != "None":
            if opt_script.startswith("file:"):
                cfg_text = self.engine.resource_manager.load_text_file(opt_script[5:])
                self.engine.cfg_decoder.execute(cfg_text)
            elif opt_script.startswith("cmd:"):
                self.engine.cfg_decoder.execute(opt_script[4:])

        path_raw = opt_data["next_dialog"]
        if path_raw.startswith("file:"):
            target_path = path_raw[5:]
            self.load_dialogue(target_path)
            self.start_dialogue()
        elif path_raw.startswith("id:"):
            target_index = str(path_raw[3:])
            self.load_dialogue(self.engine.id_index_map[target_index])
            self.start_dialogue()

    def start_dialogue(self, not_choice=False):
        if self.dialogue is None or len(self.dialogue) == 0:
            return
        if self.engine.cfg_decoder.is_waiting:
            return

        if self.is_choice_active:
            if not_choice:
                self.engine.dialog_choice.set_active(False)
                self.engine.dialog_backlog.history = self.history_text
            else:
                return

        dialog_list = self.dialogue.get("dialogs", [])
        if self.current_dialogue_index >= len(dialog_list):
            self.this_dialogue_is_finished = True
            log.log(0,"Dialogue is finished")
            return

        log.log(0,f"Now Dialogue index : {self.current_dialogue_index}")
        current_node = dialog_list[self.current_dialogue_index]

        if len(self.engine.scene.bgm) > 0:
            now_bgm = f"file:{self.engine.scene.bgm[-1].path}"
        else:
            now_bgm = "None"

        # 历史记录最大保存50条
        if len(self.history_text) >= 50:
            self.history_text.pop(0)

        self.history_text.append({
            "text": current_node.get("text", ""),
            "speaker": current_node.get("speaker", ""),
            "dialogue_file_path": self.dialogue_file_path,
            "bgm": now_bgm,
            "index": self.current_dialogue_index
        })
        #self.engine.dialog_backlog.set_log = self.history_text
        #self.engine.dialog_backlog._calc_scroll_limit()
        self.engine.dialog_backlog.add_log(self.history_text[-1])

        # 加载文本与说话人
        self.engine.dialog_table.load_text(current_node.get("text", ""))
        self.engine.dialog_table.set_speaker(current_node.get("speaker", ""))

        voice_str = self._norm_empty(current_node.get("voice", "None"))
        if voice_str != "None":
            if voice_str.startswith("file:"):
                voice_path = voice_str[5:]
                voice = self.engine.resource_manager.load_sound(voice_path)
                voice.set_volume(1.5)
                voice.play()

        # 执行本条对话前置script
        node_script = self._norm_empty(current_node.get("script", "None"))
        if node_script != "None":
            if node_script.startswith("file:"):
                cfg_text = self.engine.resource_manager.load_text_file(node_script[5:])
                self.engine.cfg_decoder.execute(cfg_text)
            elif node_script.startswith("cmd:"):
                self.engine.cfg_decoder.execute(node_script[4:])

        option_list = current_node.get("options", [])
        if len(option_list) > 0:
            self.is_choice_active = True
            self.engine.dialog_choice.clear_options()
            self._active_options = option_list

            for idx, opt in enumerate(option_list):
                show_option = True
                cond_raw = self._norm_empty(opt.get("condition", "None"))
                if cond_raw != "None":
                    if cond_raw.startswith("have_flags:"):
                        flag_str = cond_raw[11:]
                        flags_req = [x.strip() for x in flag_str.split() if x.strip()]
                        if not all(f in self.flags for f in flags_req):
                            show_option = False
                    elif cond_raw.startswith("affection:"):
                        expr = cond_raw[11:]
                        try:
                            # 直接把完整好感字典丢给解析器
                            if not parse_and_eval(expr, self.characters_affection):
                                show_option = False
                        except Exception as e:
                            log.log(2,f"选项条件解析失败 {expr} : {e}")
                            show_option = False
                    else:
                        # 未知condition直接隐藏选项
                        log.log(1,f"未知condition {cond_raw}")
                        show_option = False

                if not show_option:
                    continue

                callback = lambda i=idx: self._on_option_selected(i)
                self.engine.dialog_choice.add_option(opt["text"], callback)
        else:
            self.is_choice_active = False
            self.current_dialogue_index += 1

    def on_text_complete(self):
        if self.is_choice_active:
            self.engine.dialog_choice.set_active(True)
        else:
            if self.auto_mode:
                self.start_dialogue()

    def on_next(self):
        self.start_dialogue()


    def set_affection(self, name, value):
        """设置角色好感，覆盖原有值"""
        self.characters_affection[name] = value

    def add_affection(self, name, value):
        """增加好感，不存在该角色则初始为0再加"""
        self.characters_affection[name] = self.characters_affection.get(name, 0) + value

    def reduce_affection(self, name, value):
        """减少好感，不存在角色跳过"""
        self.characters_affection[name] = self.characters_affection.get(name, 0) - value

    def add_flag(self,name):
        self.flags.add(name)