import sys
import pygame
from engine_src.engine.core import log


class CFGDecoder:
    def __init__(self, engine=None):
        # 初始化 pygame（必须！否则 time 相关函数报错）
        if not pygame.get_init():
            pygame.init()

        self.engine = engine
        self.commands = {
            "add": self.add_object,
            "move": self.move_object,
            "switch": self.switch,
            "quit": sys.exit,
            "animation": self.animation,
            "affection": self.affection_control,
            "wait": self.wait,
            "remove": self.remove,
            "jump": self.jump
        }

        # ===== 等待与队列状态 =====
        self.is_waiting = False  # 是否正在等待
        self.wait_until = 0  # 等待结束时间（毫秒）
        self.pending_lines = []  # 待执行指令队列
        self.is_processing = False  # 是否正在处理序列

    def register(self, name, func):
        self.engine.event.emit("cfg_command_register", {"name": name, "func": func})
        """注册自定义指令"""
        self.commands[name.lower()] = func

    # -------------------------------------------------------------------------
    # 1. wait 指令（非阻塞）
    # -------------------------------------------------------------------------
    def wait(self, args):
        """等待指定秒数（非阻塞）"""
        if not args:
            log.log(2, "[CFG] wait 指令缺少时间参数，用法：wait 1.5")
            return
        try:
            duration = float(args[0])
            if duration < 0:
                log.log(2, f"[CFG] 等待时间不能为负数：{duration}")
                return
            self.wait_until = pygame.time.get_ticks() + duration * 1000
            self.is_waiting = True
            log.log(0, f"[CFG] 开始等待 {duration} 秒...")
        except ValueError:
            log.log(2, f"[CFG] 无效的等待时间：{args[0]}，请输入数字（如 1.0）")

    # -------------------------------------------------------------------------
    # 2. 每帧调用：检查等待是否结束，并续执行队列
    # -------------------------------------------------------------------------
    def update_wait(self):
        """在引擎主循环中每帧调用，驱动等待与队列执行"""
        if self.is_waiting:
            now = pygame.time.get_ticks()
            if now >= self.wait_until:
                self.is_waiting = False
                log.log(0, "[CFG] 等待结束，继续执行指令队列")
                self._resume()  # 等待结束，恢复执行
                return True
        return False

    def _resume(self):
        """等待结束后，执行队列直到下一个 wait 或队列为空"""
        while self.pending_lines and not self.is_waiting:
            next_line = self.pending_lines.pop(0)
            self.execute_line(next_line)
        # 队列为空则结束处理状态
        if not self.pending_lines:
            self.is_processing = False

    # -------------------------------------------------------------------------
    # 3. 执行入口：统一处理单行/多行，入队并启动执行
    # -------------------------------------------------------------------------
    def execute(self, line: str):
        self.engine.event.emit("cfg_command_execute",{"line": line})
        """外部调用：执行单行或多行指令（用 \n 分隔）"""
        # 拆分并清理空行
        lines = [l.strip() for l in line.split("\n") if l.strip()]
        if not lines:
            return

        # 加入队列尾部
        self.pending_lines.extend(lines)
        # 如果未在处理中，启动执行
        if not self.is_processing:
            self.is_processing = True
            self._resume()

    def execute_line(self, line: str):
        """执行单条指令（内部用），支持 // 注释"""
        # ========== 新增：//注释处理 ==========
        if "//" in line:
            line = line.split("//", 1)[0]
        line = line.strip()
        if not line:
            return
        # =====================================

        # 正在等待：不执行，队列会在 _resume 中处理
        if self.is_waiting:
            self.pending_lines.insert(0, line)
            return

        parts = line.strip().split(maxsplit=99999)
        if not parts:
            return

        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in self.commands:
            try:
                self.commands[cmd](args)
            except Exception as e:
                log.log(2, f"[CFG] 执行指令 {cmd} 出错：{e}")
        else:
            log.log(2, f"[CFG] 未知指令：{parts[0]}")

    # -------------------------------------------------------------------------
    # 4. 各指令实现（修复参数校验与越界）
    # -------------------------------------------------------------------------
    def add_object(self, args):
        if not args:
            log.log(2, "[CFG] add 指令缺少类型参数（character/background/flag）")
            return
        obj_type = args[0].lower()

        if obj_type == "character":
            if len(args) < 4:
                log.log(2, "[CFG] add character 用法：add character file:xxx.png x y")
                return
            try:
                path = args[1]
                x = float(args[2])
                y = float(args[3])
                log.log(0, f"[CFG] 添加角色：路径={path}, 位置=({x}, {y})")
                if path.startswith("file:") and self.engine:
                    self.engine.scene.add_character(path[5:], [x, y])
            except ValueError as e:
                log.log(2, f"[CFG] 坐标格式错误：{e}")

        elif obj_type == "background":
            if len(args) < 2:
                log.log(2, "[CFG] add background 用法：add background file:xxx.png")
                return
            path = args[1]
            log.log(0, f"[CFG] 添加背景：路径={path}")
            if path.startswith("file:") and self.engine:
                self.engine.scene.add_background(path[5:])

        elif obj_type == "flag":
            if len(args) < 2:
                log.log(2, "[CFG] add flag 用法：add flag flag_name")
                return
            flag_name = args[1]
            log.log(0, f"[CFG] 添加标志：{flag_name}")
            if self.engine:
                self.engine.dialog.add_flag(flag_name)

        else:
            log.log(2, f"[CFG] 未知 add 对象类型：{obj_type}")

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

    def remove(self, args):
        if not args:
            log.log(2, "[CFG] remove 缺少参数")
            return
        # remove character 索引
        # remove flag name
        if len(args) < 2:
            log.log(2, "[CFG] remove 缺少参数")
            return
        if args[0] == "character":
            self.engine.event.emit("dialogue_character_remove", {"character_name": args[1]})
            log.log(0, f"[CFG] 移除角色 {args[1]}")
            self.engine.scene.characters.remove(self.engine.scene.characters[int(args[1])])
        if args[0] == "flag":
            self.engine.event.emit("dialogue_flag_remove", {"flag_name": args[1]})
            log.log(0, f"[CFG] 移除标志 {args[1]}")
            self.engine.dialog.flags.remove(str(args[1]))

    def jump(self, args):
        if not args:
            log.log(2, "[CFG] jump 缺少参数")
            return
        if args[0] == "dialogue_file":
            log.log(0, f"[CFG] 跳转到剧本 {args[1]}")
            if args[1].startswith("id:"):
                target_index = str(args[1][3:])
                self.engine.event.emit("dialogue_jump", {"type":"jump_dialogue_file","jump_type":"id","dialogue_id": target_index})
                self.engine.dialog.load_dialogue(self.engine.id_index_map[target_index])
                self.engine.dialog.start_dialogue()
            if args[1].startswith("file:"):
                self.engine.event.emit("dialogue_jump", {"type":"jump_dialogue_file","jump_type":"file","dialogue_path": args[1][5:]})
                self.engine.dialog.load_dialogue(args[1][5:])
                self.engine.dialog.start_dialogue()
        if args[0] == "dialogue_index":
            self.engine.event.emit("dialogue_jump", {"type":"jump_dialogue_index","jump_type":"index","dialogue_index": int(args[1])})
            log.log(0, f"[CFG] 跳转到当前剧本对话 {args[1]}")
            self.engine.dialog.current_dialogue_index = int(args[1])
            self.engine.dialog.start_dialogue()