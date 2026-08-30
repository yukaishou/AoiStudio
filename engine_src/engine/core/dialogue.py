import pygame
import json
import operator
import re
import os
import sys
from engine_src.engine.core import log

# 添加 cfg_compiler 目录到路径，以便导入反编译器
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'cfg_compiler'))
try:
    from cfg_decompiler import decompile_cfgc_to_cfg
except ImportError:
    decompile_cfgc_to_cfg = None


def parse_and_eval(condition_str, context):
    """
    简单数值条件解析，支持 >= <= == != > <
    example: "千绘>=5"  context传入好感字典
    """
    parts = re.split(r'(>=|<=|==|!=|>|<)', condition_str)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) != 3:
        raise ValueError(f"条件表达式格式错误: {condition_str}")

    var, op_str, val_str = parts

    # 左侧一定是上下文中的变量
    if var not in context:
        raise ValueError(f"条件变量不存在：{var}")

    # 右侧支持数字 OR 另一个上下文变量
    if val_str in context:
        val = context[val_str]
    else:
        try:
            if "." in val_str:
                val = float(val_str)
            else:
                val = int(val_str)
        except ValueError:
            raise ValueError(f"条件右侧不是有效数字或变量: {val_str}")

    ops = {
        '>=': operator.ge, '<=': operator.le,
        '==': operator.eq, '!=': operator.ne,
        '>': operator.gt, '<': operator.lt
    }
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
        self.flags = set()
        self.characters_affection = {}
        self._active_options = []
        self._current_voice_sound = None  # 持有音频对象防止GC销毁
        # 记录已执行过script的节点索引，避免重复执行
        self.executed_script_indices = set()

        # 加载角色配置，增加异常捕获
        try:
            with open("config/characters.json", "r", encoding="utf-8") as f:
                characters_config = json.load(f)
            for i in characters_config["characters"]:
                self.characters_affection[i["name"]] = 0
        except Exception as e:
            log.log(2, f"加载角色配置失败 config/characters.json : {e}")

    def _norm_empty(self, val: str) -> str:
        """统一空值处理："" 和 "None" 归一为 "None"""
        if not isinstance(val, str):
            return "None"
        val = val.strip()
        return "None" if val in ("", "None") else val

    def _load_cfg_script(self, script_path: str) -> str:
        """加载 CFG 脚本，自动处理 .cfg_c 格式的转换"""
        # 首先尝试直接加载
        script_content = self.engine.resource_manager.load_text_file(script_path)
        
        # 如果加载失败，尝试添加 _c 后缀（兼容旧逻辑）
        if script_content is None and not script_path.endswith('_c'):
            script_path_with_c = script_path + "_c"
            script_content = self.engine.resource_manager.load_text_file(script_path_with_c)
            if script_content is not None:
                script_path = script_path_with_c
        
        # 如果仍然没有内容，返回空字符串
        if script_content is None:
            log.log(2, f"无法加载CFG脚本: {script_path}")
            return ""
        
        # 检查是否是 .cfg_c 格式（通过内容检测，而非文件扩展名）
        if script_path.endswith('.cfg_c') or (script_content.strip() and script_content.strip().startswith('[')):
            if decompile_cfgc_to_cfg is None:
                log.log(2, f"反编译器未加载，无法处理 .cfg_c 文件: {script_path}")
                return ""
            
            # 生成临时文件路径（使用绝对路径避免相对路径问题）
            import tempfile
            temp_dir = os.path.dirname(os.path.abspath(__file__))
            temp_cfg_c = os.path.join(temp_dir, 'temp_runtime.cfg_c')
            temp_cfg = os.path.join(temp_dir, 'temp_runtime.cfg')
            
            try:
                # 写入临时.cfg_c文件
                with open(temp_cfg_c, "w", encoding="utf-8") as f:
                    f.write(script_content)
                
                # 执行反编译
                decompile_cfgc_to_cfg(temp_cfg_c, temp_cfg)
                
                # 读取反编译后的内容
                with open(temp_cfg, "r", encoding="utf-8") as f:
                    cfg_text = f.read()
                
                # 清理临时文件
                if os.path.exists(temp_cfg_c):
                    os.remove(temp_cfg_c)
                if os.path.exists(temp_cfg):
                    os.remove(temp_cfg)
                
                return cfg_text
            except Exception as e:
                log.log(2, f"反编译 .cfg_c 文件失败 {script_path}: {e}")
                # 清理临时文件（即使出错也要清理）
                if os.path.exists(temp_cfg_c):
                    os.remove(temp_cfg_c)
                if os.path.exists(temp_cfg):
                    os.remove(temp_cfg)
                return ""
        else:
            # 普通 .cfg 文件，直接返回内容
            return script_content

    def load_dialogue(self, file_path):
        self.engine.event.emit("dialogue_load", {"dialogue_file_path": file_path})
        self.this_dialogue_is_finished = False
        self.current_dialogue_index = 0
        # 加载新对话时清空已执行script的记录
        self.executed_script_indices.clear()
        try:
            self.dialogue = self.engine.resource_manager.load_json_file(file_path)
        except Exception as e:
            log.log(2, f"对话文件加载失败 {file_path}: {e}")
            self.dialogue = {"dialogs": []}
        self.dialogue_file_path = file_path
        return self.dialogue

    def _on_option_selected(self, opt_index: int):
        """统一选项回调入口"""
        self.engine.event.emit("dialogue_option_selected", {"opt_index": opt_index})
        self.is_choice_active = False
        self.engine.dialog_choice.set_active(False)

        opt_data = self._active_options[opt_index]
        opt_script = self._norm_empty(opt_data["script"])

        if opt_script != "None":
            if opt_script.startswith("file:"):
                cfg_text = self._load_cfg_script(opt_script[5:])
                self.engine.cfg_decoder.execute(cfg_text)
            elif opt_script.startswith("cmd:"):
                self.engine.cfg_decoder.execute(opt_script[4:])

        path_raw = opt_data["next_dialog"]
        if path_raw.startswith("file:"):
            target_path = path_raw[5:]
            self.load_dialogue(target_path)
            self.start_dialogue()
        elif path_raw.startswith("id:"):
            target_id = path_raw[3:]
            if target_id not in self.engine.id_index_map:
                log.log(2, f"对话ID不存在: {target_id}")
                return
            target_path = self.engine.id_index_map[target_id]
            self.load_dialogue(target_path)
            self.start_dialogue()

    def start_dialogue(self, not_choice=False):
        self.engine.event.emit("dialogue_start", {"dialogue_index": self.current_dialogue_index, "not_choice": not_choice})
        self.auto_mode = not not_choice

        if len(self.dialogue.get("dialogs", [])) == 0:
            return
        # CFG等待时直接停止推进对话
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
            log.log(0, "Dialogue is finished")
            return

        log.log(0, f"Now Dialogue index : {self.current_dialogue_index}")
        current_node = dialog_list[self.current_dialogue_index]

        node_script = self._norm_empty(current_node.get("script", "None"))
        # 先执行script，如果进入等待则不显示文本，避免重复
        if node_script != "None" and self.current_dialogue_index not in self.executed_script_indices:
            if node_script.startswith("file:"):
                cfg_text = self._load_cfg_script(node_script[5:])
                self.engine.cfg_decoder.execute(cfg_text)
            elif node_script.startswith("cmd:"):
                self.engine.cfg_decoder.execute(node_script[4:])
            # 标记该节点的script已执行
            self.executed_script_indices.add(self.current_dialogue_index)
            # CFG执行后进入等待，直接返回，不显示文本
            if self.engine.cfg_decoder.is_waiting:
                return

        # 只有在没有等待状态时才显示文本和记录历史
        if len(self.engine.scene.bgm) > 0:
            now_bgm = f"file:{self.engine.scene.bgm[-1].path}"
        else:
            now_bgm = "None"

        # 历史记录最大保存50条
        if len(self.history_text) >= 50:
            self.history_text.pop(0)

        log_item = {
            "text": current_node.get("text", ""),
            "speaker": current_node.get("speaker", ""),
            "dialogue_file_path": self.dialogue_file_path,
            "bgm": now_bgm,
            "index": self.current_dialogue_index
        }
        self.history_text.append(log_item)
        self.engine.dialog_backlog.add_log(self.history_text[-1])

        self.engine.dialog_table.load_text(current_node.get("text", ""))
        self.engine.dialog_table.set_speaker(current_node.get("speaker", ""))

        voice_str = self._norm_empty(current_node.get("voice", "None"))
        self._current_voice_sound = None
        if voice_str != "None":
            if voice_str.startswith("file:"):
                voice_path = voice_str[5:]
                voice = self.engine.resource_manager.load_sound(voice_path)
                voice.set_volume(min(1.5, 1.0))  # pygame volume范围0‑1
                voice.play()
                self._current_voice_sound = voice

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
                            if not parse_and_eval(expr, self.characters_affection):
                                show_option = False
                        except Exception as e:
                            log.log(2, f"选项条件解析失败 {expr} : {e}")
                            show_option = False
                    else:
                        log.log(1, f"未知condition {cond_raw}")
                        show_option = False

                if not show_option:
                    continue

                callback = lambda i=idx: self._on_option_selected(i)
                self.engine.dialog_choice.add_option(opt["text"], callback)
        else:
            self.is_choice_active = False
            self.current_dialogue_index += 1

    def on_text_complete(self):
        """文本结束回调"""
        self.engine.event.emit("dialogue_text_complete", {"dialogue_index": self.current_dialogue_index})
        if self.is_choice_active:
            self.engine.dialog_choice.set_active(True)

    def on_next(self):
        self.engine.event.emit("dialogue_next", {"dialogue_index": self.current_dialogue_index})
        self.start_dialogue()

    def set_affection(self, name, value):
        """设置角色好感，覆盖原有值"""
        self.engine.event.emit("dialogue_set_affection", {"name": name, "value": value})
        self.characters_affection[name] = value

    def add_affection(self, name, value):
        """增加好感，不存在该角色则初始为0再加"""
        self.engine.event.emit("dialogue_add_affection", {"name": name, "value": value})
        self.characters_affection[name] = self.characters_affection.get(name, 0) + value

    def reduce_affection(self, name, value):
        """减少好感，不存在角色自动初始0再减"""
        self.engine.event.emit("dialogue_reduce_affection", {"name": name, "value": value})
        self.characters_affection[name] = self.characters_affection.get(name, 0) - value

    def add_flag(self, name):
        """添加flag标记"""
        self.engine.event.emit("dialogue_add_flag", {"name": name})
        self.flags.add(name)

    def remove_flag(self, name):
        """移除flag标记"""
        if name in self.flags:
            self.flags.remove(name)

    def has_flag(self, name) -> bool:
        """判断是否拥有flag"""
        return name in self.flags

    def get_affection(self, name, default=0):
        """获取角色好感"""
        return self.characters_affection.get(name, default)

    def get_save_data(self):
        """导出存档数据，供存档系统调用"""
        return {
            "flags": list(self.flags),
            "characters_affection": self.characters_affection.copy(),
            "dialogue_file_path": self.dialogue_file_path,
            "current_dialogue_index": self.current_dialogue_index,
            "this_dialogue_is_finished": self.this_dialogue_is_finished,
            "history_text": self.history_text.copy(),
            "executed_script_indices": list(self.executed_script_indices)
        }

    def load_save_data(self, save_data):
        """读档恢复对话状态"""
        self.flags = set(save_data.get("flags", []))
        self.characters_affection = save_data.get("characters_affection", {})
        self.dialogue_file_path = save_data.get("dialogue_file_path")
        self.current_dialogue_index = save_data.get("current_dialogue_index", 0)
        self.this_dialogue_is_finished = save_data.get("this_dialogue_is_finished", False)
        self.history_text = save_data.get("history_text", [])
        # 恢复已执行script的节点记录
        self.executed_script_indices = set(save_data.get("executed_script_indices", []))
        self.engine.dialog_backlog.history = self.history_text.copy()

        if self.dialogue_file_path:
            self.load_dialogue(self.dialogue_file_path)
            # 读档后刷新UI画面状态
            dialog_list = self.dialogue.get("dialogs", [])
            if 0 <= self.current_dialogue_index < len(dialog_list):
                node = dialog_list[self.current_dialogue_index]
                self.engine.dialog_table.load_text(node.get("text", ""))
                self.engine.dialog_table.set_speaker(node.get("speaker", ""))