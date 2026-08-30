"""
CFG 命令执行器 - 重构的命令处理逻辑

改进点：
1. 更严格的参数验证
2. 详细的错误提示（包含行号）
3. 支持变量引用
4. 模块化设计，易于扩展
"""

import json
from typing import Optional, List, Any
from engine_src.engine.core import log
from .error_handler import CFGErrorHandler
from .variable_manager import VariableManager


class CommandExecutor:
    """
    CFG 命令执行器
    
    负责解析和执行所有 CFG 命令
    """
    
    # 中文命令映射表
    CHINESE_COMMAND_MAP = {
        "添加": "add",
        "增加": "add",
        "移动": "move",
        "切换": "switch",
        "退出": "quit",
        "动画": "animation",
        "好感": "affection",
        "好感度": "affection",
        "等待": "wait",
        "延迟": "wait",
        "移除": "remove",
        "删除": "remove",
        "跳转": "jump",
        "运行": "run",
        "执行": "run",
        "如果": "if",
        "条件": "if",
        "设置": "set",
        "赋值": "set",
        "转场": "transition",
        "画面切换": "transition",
        "显示CG": "show_cg",
        "隐藏CG": "hide_cg",
    }
    
    # 中文参数映射表
    CHINESE_PARAM_MAP = {
        # add 子类型
        "角色": "character",
        "立绘": "character",
        "人物": "character",
        "背景": "background",
        "场景": "background",
        "游戏对象": "game_object",
        "对象": "game_object",
        "组件": "component",
        "标志": "flag",
        "标记": "flag",
        # switch 目标类型
        "音乐": "bgm",
        "背景音乐": "bgm",
        # move 对象类型
        # animation 动画类型
        "淡入": "fade_to",
        "淡出": "fade_to",
        "缩放": "scale_to",
        "抖动": "shake",
        "震动": "shake",
        "跳跃": "jump",
        "闪烁开始": "start_blink",
        "闪烁停止": "stop_blink",
        # affection 操作
        "增加好感": "add",
        "减少好感": "reduce",
        "设置好感": "set",
        # transition 转场类型
        "淡入淡出": "fade",
        "黑场": "black_fade",
        # jump 跳转类型
        "剧本文件": "dialogue_file",
        "剧本索引": "dialogue_index",
        "对话文件": "dialogue_file",
        "对话索引": "dialogue_index",

    }
    
    def __init__(self, engine, error_handler: CFGErrorHandler, variable_manager: VariableManager):
        self.engine = engine
        self.error_handler = error_handler
        self.variable_manager = variable_manager
        
        # 注册命令
        self.commands = {
            "add": self.cmd_add,
            "move": self.cmd_move,
            "switch": self.cmd_switch,
            "quit": self.cmd_quit,
            "animation": self.cmd_animation,
            "affection": self.cmd_affection,
            "wait": self.cmd_wait,
            "remove": self.cmd_remove,
            "jump": self.cmd_jump,
            "run": self.cmd_run,
            "if": self.cmd_if,
            "set": self.cmd_set,  # 新增：设置变量
            "transition": self.cmd_transition,  # 屏幕转场
            "show_cg": self.cmd_show_cg,  # 显示CG图片
            "hide_cg": self.cmd_hide_cg,  # 隐藏CG图片
        }
    
    def map_chinese_command(self, cmd: str) -> str:
        """
        将中文命令映射为英文命令
        
        Args:
            cmd: 原始命令（可能是中文）
            
        Returns:
            映射后的英文命令
        """
        cmd_lower = cmd.lower()
        return self.CHINESE_COMMAND_MAP.get(cmd_lower, cmd_lower)
    
    def map_chinese_params(self, args: List[str]) -> List[str]:
        """
        将中文参数映射为英文参数
        
        Args:
            args: 原始参数列表
            
        Returns:
            映射后的参数列表
        """
        mapped_args = []
        for arg in args:
            arg_lower = arg.lower()
            mapped_args.append(self.CHINESE_PARAM_MAP.get(arg_lower, arg))
        return mapped_args
    
    def execute_command_with_chinese(self, cmd: str, args: List[str], line_number: int = 0):
        """
        支持中文命令的执行方法
        会先将中文命令和参数映射为英文
        
        Args:
            cmd: 命令名称（支持中文）
            args: 参数列表（支持中文）
            line_number: 行号
        """
        # 映射中文命令
        english_cmd = self.map_chinese_command(cmd)
        
        # 映射中文参数
        english_args = self.map_chinese_params(args)
        
        # 如果命令被映射了，记录日志
        if english_cmd != cmd.lower():
            log.log(0, f"[CFG] 中文命令映射: '{cmd}' -> '{english_cmd}'")
        
        # 执行映射后的命令
        self.execute_command(english_cmd, english_args, line_number)
    
    def execute_command(self, cmd: str, args: List[str], line_number: int = 0):
        """执行命令"""
        try:
            func = self.commands.get(cmd.lower())
            if func:
                func(args, line_number=line_number)
            else:
                self.error_handler.report_error(
                    f"未知指令: {cmd}",
                    line_number=line_number,
                    context=" ".join([cmd] + args[:5])
                )
        except Exception as e:
            self.error_handler.report_error(
                f"指令执行异常: {repr(e)}",
                line_number=line_number,
                context=f"{cmd} {' '.join(args[:5])}"
            )
            import traceback
            traceback.print_exc()
    
    def cmd_set(self, args: List[str], line_number: int = 0):
        """设置变量: set var_name value"""
        if len(args) < 2:
            self.error_handler.report_error(
                "set 用法: set var_name value",
                line_number=line_number
            )
            return
        
        var_name = args[0]
        var_value = " ".join(args[1:])
        
        try:
            self.variable_manager.set_variable(var_name, var_value)
        except Exception as e:
            self.error_handler.report_error(
                f"设置变量失败: {repr(e)}",
                line_number=line_number
            )
    
    def cmd_add(self, args: List[str], line_number: int = 0):
        """添加对象"""
        if not args:
            self.error_handler.report_error(
                "add 需要子类型 game_object / character / background / flag / component",
                line_number=line_number
            )
            return
        
        sub_type = args[0].lower()
        
        if sub_type == "character":
            if len(args) < 4:
                self.error_handler.report_error(
                    "add character file:x.png x y",
                    line_number=line_number
                )
                return
            
            path_token = args[1]
            try:
                x = float(args[2])
                y = float(args[3])
            except ValueError:
                self.error_handler.report_error(
                    "add character 坐标错误",
                    line_number=line_number
                )
                return
            
            real_path = path_token[5:] if path_token.startswith("file:") else path_token
            if self.engine and hasattr(self.engine, "scene"):
                self.engine.scene.add_character(real_path, [x, y])
            log.log(0, f"[CFG] add character {real_path} @({x},{y})")
        
        elif sub_type == "background":
            if len(args) < 2:
                self.error_handler.report_error(
                    "add background file:xxx.png",
                    line_number=line_number
                )
                return
            
            path_token = args[1]
            real_path = path_token[5:] if path_token.startswith("file:") else path_token
            if self.engine and hasattr(self.engine, "scene"):
                self.engine.scene.add_background(real_path)
            log.log(0, f"[CFG] add background {real_path}")
        
        elif sub_type == "game_object":
            if len(args) < 7:
                self.error_handler.report_error(
                    "add game_object name px py rot sx sy",
                    line_number=line_number
                )
                return
            
            go_name = args[1]
            try:
                px = float(args[2])
                py = float(args[3])
                rot = float(args[4])
                sx = float(args[5])
                sy = float(args[6])
            except ValueError:
                self.error_handler.report_error(
                    "add game_object 坐标参数错误",
                    line_number=line_number
                )
                return
            
            if not self.engine or not hasattr(self.engine, "g_o_manager"):
                self.error_handler.report_error(
                    "g_o_manager 未就绪",
                    line_number=line_number
                )
                return
            
            self.engine.g_o_manager.create_game_object(
                go_name,
                transform={"position": [px, py], "rotation": rot, "scale": [sx, sy]},
                parent=None
            )
            log.log(0, f"[CFG] create game_object {go_name}")
        
        elif sub_type == "component":
            if len(args) < 3:
                self.error_handler.report_error(
                    "add component go_name ComponentName { ... }",
                    line_number=line_number
                )
                return
            
            go_name = args[1]
            comp_type = args[2]
            
            # 从 CFGDecoder 获取当前解析的 JSON 块数据
            block_dict = {}
            if self.engine and hasattr(self.engine, 'cfg_decoder') and hasattr(self.engine.cfg_decoder, '_current_block_payload'):
                payload = self.engine.cfg_decoder._current_block_payload
                if payload:
                    try:
                        import json
                        block_dict = json.loads(payload)
                    except json.JSONDecodeError as e:
                        self.error_handler.report_error(
                            f"add component: JSON 解析失败: {e}",
                            line_number=line_number
                        )
                        return
            
            target_go = self.engine.g_o_manager.get_game_object(go_name) if self.engine and hasattr(self.engine, "g_o_manager") else None
            if target_go is None:
                self.error_handler.report_error(
                    f"add component：游戏对象 {go_name} 不存在",
                    line_number=line_number
                )
                return
            
            self.engine.g_o_manager.create_component(target_go, comp_type, block_dict)
        
        elif sub_type == "flag":
            if len(args) < 2:
                self.error_handler.report_error(
                    "add flag flag_name",
                    line_number=line_number
                )
                return
            
            flag_name = args[1]
            if self.engine and hasattr(self.engine, "dialog"):
                self.engine.dialog.add_flag(flag_name)
            log.log(0, f"[CFG] add flag {flag_name}")
    
    def cmd_move(self, args: List[str], line_number: int = 0):
        """移动对象"""
        if len(args) < 6:
            self.error_handler.report_error(
                "move 用法：move character 索引 x y 缓动 时长",
                line_number=line_number
            )
            return
        
        try:
            obj_type, idx_str, x_str, y_str, ease, dur_str = args[:6]
            if obj_type != "character":
                self.error_handler.report_error(
                    f"仅支持 move character，不支持 {obj_type}",
                    line_number=line_number
                )
                return
            
            idx = int(idx_str)
            x, y = float(x_str), float(y_str)
            dur = float(dur_str)
            
            log.log(0, f"[CFG] 角色 {idx} 移动到 ({x}, {y})，缓动={ease}，时长={dur}s")
            if self.engine and 0 <= idx < len(self.engine.scene.characters):
                self.engine.scene.characters[idx].move_to([x, y], ease, dur)
        except (ValueError, IndexError) as e:
            self.error_handler.report_error(
                f"move 参数错误：{e}",
                line_number=line_number
            )
    
    def cmd_switch(self, args: List[str], line_number: int = 0):
        """切换对象"""
        if not args:
            self.error_handler.report_error(
                "switch 指令缺少类型（background/bgm/character）",
                line_number=line_number
            )
            return
        
        target = args[0].lower()
        
        if target == "background" and len(args) >= 4:
            path, trans, dur_str = args[1], args[2], args[3]
            try:
                dur = float(dur_str)
                log.log(0, f"[CFG] 切换背景：{path}，过渡={trans}，时长={dur}s")
                if self.engine:
                    real_path = path[5:] if path.startswith("file:") else path
                    self.engine.scene.switch_background(real_path, trans, dur)
            except ValueError:
                self.error_handler.report_error(
                    f"过渡时长无效：{dur_str}",
                    line_number=line_number
                )
        
        elif target == "bgm" and len(args) >= 3:
            path, dur_str = args[1], args[2]
            try:
                dur = float(dur_str)
                log.log(0, f"[CFG] 切换 BGM：{path}，淡入时长={dur}s")
                if self.engine:
                    real_path = path[5:] if path.startswith("file:") else path
                    self.engine.scene.switch_bgm(real_path, dur)
            except ValueError:
                self.error_handler.report_error(
                    f"BGM 淡入时长无效：{dur_str}",
                    line_number=line_number
                )
        
        elif target == "character" and len(args) >= 6:
            idx_str, _, path, fade_dur_str, scale_dur_str = args[1:6]
            try:
                idx = int(idx_str)
                fade_dur = float(fade_dur_str)
                scale_dur = float(scale_dur_str)
                log.log(0, f"[CFG] 角色 {idx} 切换立绘：{path}")
                if self.engine and 0 <= idx < len(self.engine.scene.characters):
                    real_path = path[5:] if path.startswith("file:") else path
                    self.engine.scene.characters[idx].change_sprite(
                        real_path, fade_dur, scale_dur
                    )
            except (ValueError, IndexError) as e:
                self.error_handler.report_error(
                    f"switch character 参数错误：{e}",
                    line_number=line_number
                )
        else:
            self.error_handler.report_error(
                f"switch 用法错误或参数不足：{' '.join(args)}",
                line_number=line_number
            )
    def cmd_quit(self, args: List[str], line_number: int = 0):
        """退出"""
        self.error_handler.report_info("收到退出命令", line_number=line_number)
        if self.engine:
            self.engine.event.emit("cfg_quit_request", {})
        else:
            import sys
            sys.exit(0)
    
    def cmd_animation(self, args: List[str], line_number: int = 0):
        """动画"""
        if len(args) < 3:
            self.error_handler.report_error(
                "animation 用法：animation character 索引 动画名 ...",
                line_number=line_number
            )
            return
        
        try:
            obj_type, idx_str, anim = args[:3]
            if obj_type != "character":
                self.error_handler.report_error(
                    f"仅支持 animation character，不支持 {obj_type}",
                    line_number=line_number
                )
                return
            
            idx = int(idx_str)
            log.log(0, f"[CFG] 角色 {idx} 执行动画：{anim}")
            
            if not self.engine or not (0 <= idx < len(self.engine.scene.characters)):
                return
            
            char = self.engine.scene.characters[idx]
            
            if anim == "fade_to" and len(args) >= 5:
                alpha, dur = float(args[3]), float(args[4])
                char.fade_to(alpha, dur)
            elif anim == "scale_to" and len(args) >= 6:
                w, h, dur = int(args[3]), int(args[4]), float(args[5])
                char.scale_to(w, h, dur)
            elif anim == "shake" and len(args) >= 5:
                amp, dur = float(args[3]), float(args[4])
                char.shake(amp, dur)
            elif anim == "jump" and len(args) >= 5:
                height, dur = float(args[3]), float(args[4])
                char.jump(height, dur)
            elif anim == "start_blink" and len(args) >= 4:
                interval = float(args[3])
                char.start_blink(interval)
            elif anim == "stop_blink":
                char.stop_blink()
            else:
                self.error_handler.report_error(
                    f"未知动画或参数不足：{anim}",
                    line_number=line_number
                )
        except (ValueError, IndexError) as e:
            self.error_handler.report_error(
                f"animation 参数错误：{e}",
                line_number=line_number
            )
    
    def cmd_affection(self, args: List[str], line_number: int = 0):
        """好感度控制"""
        if len(args) < 3:
            self.error_handler.report_error(
                "affection 用法：affection 角色名 add/set/reduce 数值",
                line_number=line_number
            )
            return
        
        char_name, op, val_str = args[0], args[1].lower(), args[2]
        try:
            val = int(val_str)
            if not self.engine:
                return
            
            if op == "add":
                self.engine.dialog.add_affection(char_name, val)
            elif op == "reduce":
                self.engine.dialog.reduce_affection(char_name, val)
            elif op == "set":
                self.engine.dialog.set_affection(char_name, val)
            else:
                self.error_handler.report_error(
                    f"未知 affection 操作：{op}",
                    line_number=line_number
                )
                return
            
            log.log(0, f"[CFG] {char_name} 好感度 {op} {val}")
        except ValueError:
            self.error_handler.report_error(
                f"好感度数值无效：{val_str}",
                line_number=line_number
            )
    
    def cmd_wait(self, args: List[str], line_number: int = 0):
        """等待"""
        if not args:
            self.error_handler.report_error(
                "wait 需要时间参数，例 wait 2.0",
                line_number=line_number
            )
            return
        
        try:
            sec = float(args[0])
        except ValueError:
            self.error_handler.report_error(
                f"wait 参数不是数字 {args[0]}",
                line_number=line_number
            )
            return
        
        import pygame
        now = pygame.time.get_ticks()
        # 这里需要返回等待状态，由主解码器处理
        return sec
    
    def cmd_remove(self, args: List[str], line_number: int = 0):
        """移除对象"""
        if len(args) < 2:
            self.error_handler.report_error(
                "remove character|flag index/name",
                line_number=line_number
            )
            return
        
        sub_t = args[0].lower()
        if sub_t == "character":
            try:
                idx = int(args[1])
            except ValueError:
                self.error_handler.report_error(
                    "remove character 需要数字索引",
                    line_number=line_number
                )
                return
            
            if self.engine and hasattr(self.engine, "scene"):
                if 0 <= idx < len(self.engine.scene.characters):
                    self.engine.scene.characters.pop(idx)
                    log.log(0, f"[CFG] remove character {idx}")
        elif sub_t == "flag":
            flag_name = args[1]
            if self.engine and hasattr(self.engine, "dialog"):
                self.engine.dialog.remove_flag(flag_name)
            log.log(0, f"[CFG] remove flag {flag_name}")
    
    def cmd_jump(self, args: List[str], line_number: int = 0):
        """跳转"""
        if not args:
            self.error_handler.report_error(
                "jump 缺少参数",
                line_number=line_number
            )
            return
        
        if args[0] == "dialogue_file":
            log.log(0, f"[CFG] 跳转到剧本 {args[1]}")
            if args[1].startswith("id:"):
                target_index = str(args[1][3:])
                self.engine.event.emit("dialogue_jump",
                                       {"type": "jump_dialogue_file", "jump_type": "id", "dialogue_id": target_index})
                self.engine.dialog.load_dialogue(self.engine.id_index_map[target_index])
                self.engine.dialog.start_dialogue()
            if args[1].startswith("file:"):
                self.engine.event.emit("dialogue_jump", {"type": "jump_dialogue_file", "jump_type": "file",
                                                         "dialogue_path": args[1][5:]})
                self.engine.dialog.load_dialogue(args[1][5:])
                self.engine.dialog.start_dialogue()
        
        if args[0] == "dialogue_index":
            self.engine.event.emit("dialogue_jump", {"type": "jump_dialogue_index", "jump_type": "index",
                                                     "dialogue_index": int(args[1])})
            log.log(0, f"[CFG] 跳转到当前剧本对话 {args[1]}")
            self.engine.dialog.current_dialogue_index = int(args[1])
            self.engine.dialog.start_dialogue()
    
    def cmd_run(self, args: List[str], line_number: int = 0):
        """运行子脚本"""
        if not args:
            self.error_handler.report_error(
                "run 用法: run file:path/to/script.cfg",
                line_number=line_number
            )
            return
        
        path_token = args[0]
        if not path_token.startswith("file:"):
            self.error_handler.report_error(
                f"run 参数必须以 file: 开头，收到 {path_token}",
                line_number=line_number
            )
            return
        
        file_path = path_token[5:]
        try:
            script_text = self.engine.resource_manager.load_text_file(file_path)
            log.log(0, f"[CFG] run 加载子脚本 {file_path}")
            # 这里需要返回脚本内容，由主解码器处理
            return script_text
        except Exception as e:
            self.error_handler.report_error(
                f"run读取脚本失败 {file_path}, err={repr(e)}",
                line_number=line_number
            )
    
    def cmd_if(self, args: List[str], line_number: int = 0):
        """条件判断"""
        # 找到第一个 file:xxx 的下标
        file_pos = None
        for idx, tok in enumerate(args):
            if tok.startswith("file:"):
                file_pos = idx
                break
        
        if file_pos is None:
            self.error_handler.report_error(
                "[CFG if] 缺少 file: 脚本路径",
                line_number=line_number
            )
            return
        
        cond_args = args[:file_pos]
        remain_args = args[file_pos:]
        
        true_file = remain_args[0]
        false_file = None
        
        # 解析 else
        for idx, tok in enumerate(remain_args):
            if tok.lower() == "else":
                if idx + 1 < len(remain_args):
                    false_file = remain_args[idx+1]
                break
        
        cond_result, err = self._eval_condition(cond_args)
        if err is not None:
            self.error_handler.report_error(
                f"[CFG if] {err}",
                line_number=line_number
            )
            return
        
        if cond_result is True:
            log.log(0, f"[CFG if] 条件成立，执行 {true_file}")
            return self.cmd_run([true_file], line_number=line_number)
        else:
            if false_file is not None:
                log.log(0, f"[CFG if] 条件不成立，执行 {false_file}")
                return self.cmd_run([false_file], line_number=line_number)
            else:
                log.log(0, "[CFG if] 条件不成立，无else分支，跳过")
    
    def _eval_condition(self, cond_args):
        """评估条件"""
        if not cond_args:
            return None, "条件为空"
        
        first_arg = cond_args[0]
        
        # have_flags 检查
        if first_arg.startswith("have_flags:"):
            flag_part = first_arg[len("have_flags:"):]
            req_flags = [f.strip() for f in flag_part.split() if f.strip()]
            if not req_flags:
                return None, "have_flags:后面至少写一个flag名称"
            
            if not self.engine or not hasattr(self.engine, "dialog"):
                return None, "dialog系统未就绪"
            
            dialog = self.engine.dialog
            all_ok = all(dialog.has_flag(f) for f in req_flags)
            return all_ok, None
        
        # affection 检查
        if first_arg.startswith("affection:"):
            expr = first_arg[len("affection:"):]
            if not expr.strip():
                return None, "affection:后面需要条件表达式"
            
            if not self.engine or not hasattr(self.engine, "dialog"):
                return None, "dialog系统未就绪"
            
            dialog = self.engine.dialog
            try:
                from engine_src.engine.core.dialogue import parse_and_eval
                res = parse_and_eval(expr, dialog.characters_affection)
                return res, None
            except Exception as e:
                return None, f"好感条件解析失败: {repr(e)}"
        
        return None, f"未知条件前缀 {first_arg}，支持 have_flags: / affection:"
    
    def cmd_transition(self, args: List[str], line_number: int = 0):
        """屏幕转场命令"""
        if len(args) < 2:
            self.error_handler.report_error(
                "transition 参数不足，需要 type 和 duration",
                line_number=line_number
            )
            return
        
        transition_type = args[0]
        try:
            duration = float(args[1])
        except ValueError:
            self.error_handler.report_error(
                f"transition 无效的时长值: {args[1]}",
                line_number=line_number
            )
            return
        
        if transition_type not in ["fade", "black_fade"]:
            self.error_handler.report_error(
                f"transition 不支持的转场类型: {transition_type}",
                line_number=line_number
            )
            return
        
        # 启动转场动画
        if self.engine and hasattr(self.engine, 'screen_transition'):
            self.engine.screen_transition.start_transition(
                transition_type=transition_type,
                duration=duration
            )
        
        log.log(0, f"[CFG] 启动{transition_type}转场，时长={duration}s")
    
    def cmd_show_cg(self, args: List[str], line_number: int = 0):
        """显示CG图片"""
        if not args:
            self.error_handler.report_error(
                "show_cg 需要图片路径参数，例 show_cg file:path/to/cg.png",
                line_number=line_number
            )
            return
        
        path_token = args[0]
        if not path_token.startswith("file:"):
            self.error_handler.report_error(
                f"show_cg 参数必须以 file: 开头，收到 {path_token}",
                line_number=line_number
            )
            return
        
        image_path = path_token[5:]
        title = ""
        description = ""
        
        # 解析可选的标题和描述参数
        if len(args) >= 2:
            title = args[1]
        if len(args) >= 3:
            description = args[2]
        
        # 调用 UI 管理器显示 CG
        if self.engine and hasattr(self.engine, 'ugc_ui_manager'):
            try:
                self.engine.ugc_ui_manager.show_cg(image_path, title, description)
                log.log(0, f"[CFG] 显示CG: {image_path}, 标题: {title}, 描述: {description}")
            except Exception as e:
                self.error_handler.report_error(
                    f"show_cg 执行失败: {repr(e)}",
                    line_number=line_number
                )
        else:
            self.error_handler.report_error(
                "ugc_ui_manager 未就绪",
                line_number=line_number
            )
    
    def cmd_hide_cg(self, args: List[str], line_number: int = 0):
        """隐藏CG图片"""
        duration = 0.5  # 默认持续时间
        
        # 解析可选的持续时间参数
        if args:
            try:
                duration = float(args[0])
            except ValueError:
                self.error_handler.report_error(
                    f"hide_cg 无效的持续时间: {args[0]}",
                    line_number=line_number
                )
                return
        
        # 调用 UI 管理器隐藏所有 CG
        if self.engine and hasattr(self.engine, 'ugc_ui_manager'):
            try:
                self.engine.ugc_ui_manager.hide_all_cg(duration)
                log.log(0, f"[CFG] 隐藏CG，持续时间={duration}s")
            except Exception as e:
                self.error_handler.report_error(
                    f"hide_cg 执行失败: {repr(e)}",
                    line_number=line_number
                )
        else:
            self.error_handler.report_error(
                "ugc_ui_manager 未就绪",
                line_number=line_number
            )
