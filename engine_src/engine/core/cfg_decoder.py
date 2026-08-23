import json
import os
import sys
import pygame
from engine_src.engine.core import log


class CFGDecoder:
    def __init__(self, engine=None):
        if not pygame.get_init():
            pygame.init()

        self.engine = engine
        self.commands = {
            "add": self.add_object,
            "move": self.move_object,
            "switch": self.switch,
            "quit": self.cmd_quit,
            "animation": self.animation,
            "affection": self.affection_control,
            "wait": self.wait,
            "remove": self.remove,
            "jump": self.jump,
            "run": self.cmd_run,
        }

        self.is_waiting = False
        self.wait_until = 0
        self.pending_lines = []
        self.is_processing = False
        self._current_block_payload = None

    def register(self, name, func):
        if self.engine is not None:
            self.engine.event.emit("cfg_command_register", {"name": name, "func": func})
        self.commands[name.lower()] = func

    @staticmethod
    def _extract_brace_block(text: str, start_idx: int):
        brace_depth = 0
        end_pos = -1
        for i in range(start_idx, len(text)):
            if text[i] == '{':
                brace_depth += 1
            elif text[i] == '}':
                brace_depth -= 1
                if brace_depth == 0:
                    end_pos = i
                    break
        if end_pos == -1:
            return None, len(text)
        block_inner = text[start_idx+1:end_pos]
        return block_inner.strip(), end_pos + 1

    @staticmethod
    def _strip_inner_comment(text: str) -> str:
        """FIX: 移除块内部 // 注释"""
        lines = []
        for line in text.splitlines():
            if "//" in line:
                line = line.split("//", 1)[0]
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _split_statements(text: str):
        stmts = []
        pos = 0
        n = len(text)
        brace = 0
        start = 0
        while pos < n:
            c = text[pos]
            if c == '{':
                brace += 1
            elif c == '}':
                brace -= 1
            # 只有不在大括号内部，换行才作为语句分隔符
            if brace == 0 and c in ('\n', '\r'):
                seg = text[start:pos].strip()
                if seg:
                    stmts.append(seg)
                # 跳过换行
                while pos < n and text[pos] in ('\n', '\r'):
                    pos += 1
                start = pos
                continue
            pos += 1
        # 处理最后一条语句
        seg = text[start:pos].strip()
        if seg:
            stmts.append(seg)
        return stmts

    def execute(self, line: str):
        if self.engine is not None:
            self.engine.event.emit("cfg_command_execute", {"line": line})
        stmts = self._split_statements(line)
        # =========调试输出，看分割出来的语句列表=========
        log.log(0, f"[CFG-DBG] split stmts count={len(stmts)}")
        for idx, s in enumerate(stmts):
            log.log(0, f"[CFG-DBG] stmt[{idx}] = |{s}|")
        # ==============================================
        if not stmts:
            return
        self.pending_lines.extend(stmts)
        if not self.is_processing:
            self.is_processing = True
            self._resume()

    def _resume(self):
        while self.pending_lines and not self.is_waiting:
            stmt = self.pending_lines.pop(0)
            self.execute_line(stmt)
        self.is_processing = False

    def execute_line(self, line: str):
        if "//" in line:
            line = line.split("//", 1)[0].strip()
        if not line:
            return

        tokens = []
        idx = 0
        n = len(line)
        while idx < n:
            while idx < n and line[idx].isspace():
                idx += 1
            if idx >= n:
                break
            if line[idx] == '{':
                block_content, new_idx = self._extract_brace_block(line, idx)
                block_content = self._strip_inner_comment(block_content)
                tokens.append(("__BLOCK__", block_content))
                idx = new_idx
            else:
                j = idx
                while j < n and not line[j].isspace() and line[j] != '{':
                    j += 1
                word = line[idx:j]
                tokens.append(("TOKEN", word))
                idx = j

        if not tokens:
            return
        cmd = tokens[0][1].lower()
        args = []
        block_payload = None
        for typ, val in tokens[1:]:
            if typ == "__BLOCK__":
                block_payload = val
            else:
                args.append(val)

        try:
            self._current_block_payload = block_payload
            func = self.commands.get(cmd)
            if func is not None:
                func(args)
            else:
                log.log(2, f"[CFG] 未知指令: {cmd}")
            self._current_block_payload = None
        except Exception as e:
            log.log(2, f"[CFG] 指令执行异常 cmd={cmd}, err={repr(e)}")
            import traceback
            traceback.print_exc()
            self._current_block_payload = None

    def wait(self, args):
        if not args:
            log.log(2, "[CFG] wait 需要时间参数，例 wait 2.0")
            return
        try:
            sec = float(args[0])
        except ValueError:
            log.log(2, f"[CFG] wait 参数不是数字 {args[0]}")
            return
        now = pygame.time.get_ticks()
        self.wait_until = now + int(sec * 1000)
        self.is_waiting = True

    def update_wait(self, now_ms):
        if self.is_waiting:
            if now_ms >= self.wait_until:
                self.is_waiting = False
                self._resume()

    def cmd_quit(self, args):
        log.log(0, "[CFG] receive quit command")
        if self.engine:
            self.engine.event.emit("cfg_quit_request", {})
        else:
            sys.exit(0)

    def add_object(self, args):
        if not args:
            log.log(2, "[CFG] add 需要子类型 game_object / character / background / flag / component")
            return
        sub_type = args[0].lower()

        if sub_type == "game_object":
            if len(args) < 7:
                log.log(2, "[CFG] add game_object name px py rot sx sy")
                return
            go_name = args[1]
            try:
                px = float(args[2])
                py = float(args[3])
                rot = float(args[4])
                sx = float(args[5])
                sy = float(args[6])
            except ValueError:
                log.log(2, "[CFG] add game_object 坐标参数错误")
                return
            if not self.engine or not hasattr(self.engine, "g_o_manager"):
                log.log(2, "[CFG] g_o_manager 未就绪")
                return
            self.engine.g_o_manager.create_game_object(
                go_name,
                transform={"position": [px, py], "rotation": rot, "scale": [sx, sy]},
                parent=None
            )
            log.log(0, f"[CFG] create game_object {go_name}")

        elif sub_type == "component":
            if len(args) < 3:
                log.log(2, "[CFG] add component go_name ComponentName { ... }")
                return
            go_name = args[1]
            comp_type = args[2]
            block_txt = self._current_block_payload
            block_dict = {}
            if block_txt is not None:
                block_txt = block_txt.strip()
                try:
                    block_dict = json.loads(block_txt)
                    log.log(0, "[CFG] component block: JSON解析模式成功")
                except json.JSONDecodeError:
                    log.log(1, "[CFG] component块非JSON，回退key:value模式")
                    for raw_line in block_txt.splitlines():
                        line = raw_line.strip()
                        if not line:
                            continue
                        if ":" not in line:
                            log.log(2, f"[CFG] component行忽略(无冒号): {line}")
                            continue
                        try:
                            k, v = line.split(":", 1)
                            block_dict[k.strip()] = v.strip()
                        except Exception as e:
                            log.log(2, f"[CFG] component行解析失败 {line}, err={e}")

            target_go = self.engine.g_o_manager.get_game_object(go_name)
            if target_go is None:
                log.log(2, f"[CFG] add component：游戏对象 {go_name} 不存在")
                return
            self.engine.g_o_manager.create_component(target_go, comp_type, block_dict)

        elif sub_type == "character":
            if len(args) <4:
                log.log(2, "[CFG] add character file:x.png x y")
                return
            path_token = args[1]
            try:
                x = float(args[2])
                y = float(args[3])
            except ValueError:
                log.log(2, "[CFG] add character坐标错误")
                return
            real_path = path_token[5:] if path_token.startswith("file:") else path_token
            if self.engine and hasattr(self.engine, "scene"):
                self.engine.scene.add_character(real_path, [x,y])
            log.log(0, f"[CFG] add character {real_path} @({x},{y})")

        elif sub_type == "background":
            if len(args) < 2:
                log.log(2, "[CFG] add background file:xxx.png")
                return
            path_token = args[1]
            real_path = path_token[5:] if path_token.startswith("file:") else path_token
            if self.engine and hasattr(self.engine, "scene"):
                self.engine.scene.add_background(real_path)
            log.log(0, f"[CFG] add background {real_path}")

        elif sub_type == "flag":
            if len(args) < 2:
                log.log(2, "[CFG] add flag flag_name")
                return
            flag_name = args[1]
            if self.engine and hasattr(self.engine, "dialog"):
                self.engine.dialog.add_flag(flag_name)
            log.log(0, f"[CFG] add flag {flag_name}")

    def move_object(self, args):
        if len(args) < 6:
            log.log(2, "[CFG] move 用法：move character 索引 x y 缓动 时长")
            return
        try:
            obj_type, idx_str, x_str, y_str, ease, dur_str = args[:6]
            if obj_type != "character":
                log.log(2, f"[CFG] 仅支持 move character，不支持 {obj_type}")
                return
            idx = int(idx_str)
            x, y = float(x_str), float(y_str)
            dur = float(dur_str)
            log.log(0, f"[CFG] 角色 {idx} 移动到 ({x}, {y})，缓动={ease}，时长={dur}s")
            if self.engine and 0 <= idx < len(self.engine.scene.characters):
                self.engine.scene.characters[idx].move_to([x, y], ease, dur)
        except (ValueError, IndexError) as e:
            log.log(2, f"[CFG] move 参数错误：{e}")

    def switch(self, args):
        if not args:
            log.log(2, "[CFG] switch 指令缺少类型（background/bgm/character）")
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
                log.log(2, f"[CFG] 过渡时长无效：{dur_str}")

        elif target == "bgm" and len(args) >= 3:
            path, dur_str = args[1], args[2]
            try:
                dur = float(dur_str)
                log.log(0, f"[CFG] 切换 BGM：{path}，淡入时长={dur}s")
                if self.engine:
                    real_path = path[5:] if path.startswith("file:") else path
                    self.engine.scene.switch_bgm(real_path, dur)
            except ValueError:
                log.log(2, f"[CFG] BGM 淡入时长无效：{dur_str}")

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
                log.log(2, f"[CFG] switch character 参数错误：{e}")
        else:
            log.log(2, f"[CFG] switch 用法错误或参数不足：{' '.join(args)}")

    def animation(self, args):
        if len(args) < 3:
            log.log(2, "[CFG] animation 用法：animation character 索引 动画名 ...")
            return
        try:
            obj_type, idx_str, anim = args[:3]
            if obj_type != "character":
                log.log(2, f"[CFG] 仅支持 animation character，不支持 {obj_type}")
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
                log.log(2, f"[CFG] 未知动画或参数不足：{anim}")
        except (ValueError, IndexError) as e:
            log.log(2, f"[CFG] animation 参数错误：{e}")

    def affection_control(self, args):
        if len(args) < 3:
            log.log(2, "[CFG] affection 用法：affection 角色名 add/set/reduce 数值")
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
                log.log(2, f"[CFG] 未知 affection 操作：{op}")
            log.log(0, f"[CFG] {char_name} 好感度 {op} {val}")
        except ValueError:
            log.log(2, f"[CFG] 好感度数值无效：{val_str}")

    def remove(self, args):
        if len(args) <2:
            log.log(2, "[CFG] remove character|flag index/name")
            return
        sub_t = args[0].lower()
        if sub_t == "character":
            try:
                idx = int(args[1])
            except ValueError:
                log.log(2, "[CFG] remove character 需要数字索引")
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

    def jump(self, args):
        if not args:
            log.log(2, "[CFG] jump 缺少参数")
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

    def cmd_run(self, args):
        """
        CFG指令: run file:xxx.cfg
        嵌入执行另一个cfg脚本，执行完毕回到当前脚本继续执行
        """
        if not args:
            log.log(2, "[CFG] run 用法: run file:path/to/script.cfg")
            return
        path_token = args[0]
        if not path_token.startswith("file:"):
            log.log(2, f"[CFG] run 参数必须以 file: 开头，收到 {path_token}")
            return
        file_path = path_token[5:]
        try:
            script_text = self.engine.resource_manager.load_text_file(file_path)  # 读取子脚本内容
            log.log(0, f"[CFG] run 加载子脚本 {file_path}")
            # 直接调用execute，会把子脚本所有语句解析后追加进pending_lines队列
            # 自动复用现有的 _split_statements、wait暂停逻辑
            self.execute(script_text)
        except Exception as e:
            log.log(2, f"[CFG] run读取脚本失败 {file_path}, err={repr(e)}")
            import traceback
            traceback.print_exc()

    def reset(self):
        """对外重置接口，切换脚本/场景调用"""
        self.pending_lines.clear()
        self.is_waiting = False
        self.wait_until = 0
        self.is_processing = False
        self._current_block_payload = None