"""
CFG 解码器主类 - 整合所有模块

保持与原 cfg_decoder.CFGDecoder 完全兼容
"""

import json
import os
import sys
import pygame
from engine_src.engine.core import log
from .error_handler import CFGErrorHandler
from .variable_manager import VariableManager
from .parser import CFGParser
from .commands import CommandExecutor


class CFGDecoder:
    """
    CFG 解码器 - 重构版本
    
    完全兼容原 cfg_decoder.CFGDecoder 接口，同时提供新功能：
    - 增强的错误处理
    - 变量系统
    - 改进的解析器
    - 模块化命令执行
    """
    
    def __init__(self, engine=None):
        if not pygame.get_init():
            pygame.init()
        
        self.engine = engine
        
        # 初始化新模块
        self.error_handler = CFGErrorHandler()
        self.variable_manager = VariableManager()
        self.parser = CFGParser(self.error_handler, self.variable_manager)
        self.command_executor = CommandExecutor(engine, self.error_handler, self.variable_manager)
        
        # 保持与原代码兼容的命令字典
        self.commands = self.command_executor.commands
        
        # 状态变量（与原代码保持一致）
        self.is_waiting = False
        self.wait_until = 0
        self.pending_lines = []
        self.is_processing = False
        self._current_block_payload = None
    
    def register(self, name, func):
        """注册自定义命令"""
        if self.engine is not None:
            self.engine.event.emit("cfg_command_register", {"name": name, "func": func})
        self.commands[name.lower()] = func
    
    def execute(self, line: str):
        """执行脚本"""
        if self.engine is not None:
            self.engine.event.emit("cfg_command_execute", {"line": line})
        
        # 使用新解析器
        stmts = self.parser.parse(line)
        
        # 调试输出
        log.log(0, f"[CFG-DBG] split stmts count={len(stmts)}")
        for idx, s in enumerate(stmts):
            log.log(0, f"[CFG-DBG] stmt[{idx}] = |{s}|")
        
        if not stmts:
            return
        
        self.pending_lines.extend(stmts)
        if not self.is_processing:
            self.is_processing = True
            self._resume()
    
    def _resume(self):
        """恢复执行"""
        while self.pending_lines and not self.is_waiting:
            stmt = self.pending_lines.pop(0)
            self.execute_line(stmt)
        self.is_processing = False
    
    def execute_line(self, line: str):
        """执行单行"""
        # 处理内联 if/else/endif 块
        if line.startswith("__IF_BLOCK__:"):
            content = line[len("__IF_BLOCK__:"):]
            parts = content.split("||", 2)
            if len(parts) < 3:
                self.error_handler.report_error(f"if 块格式错误: {content[:80]}")
                return
            
            cond_str = parts[0]
            true_block = parts[1]
            false_block = parts[2]
            
            # 评估条件
            if cond_str:
                cond_args = cond_str.split()
                cond_result, err = self.command_executor._eval_condition(cond_args)
                if err is not None:
                    self.error_handler.report_error(f"[CFG if] {err}")
                    return
            else:
                cond_result = True
            
            if cond_result:
                log.log(0, "[CFG if] 条件成立，执行 if 块")
                if true_block.strip():
                    self.execute(true_block)
            else:
                log.log(0, "[CFG if] 条件不成立，执行 else 块")
                if false_block.strip():
                    self.execute(false_block)
            return
        
        # 移除注释
        if "//" in line:
            line = line.split("//", 1)[0].strip()
        if "#" in line:
            line = line.split("#", 1)[0].strip()
        
        if not line:
            return
        
        # 解析 tokens
        tokens = []
        idx = 0
        n = len(line)
        while idx < n:
            while idx < n and line[idx].isspace():
                idx += 1
            if idx >= n:
                break
            if line[idx] == '{':
                block_content, new_idx = CFGParser.extract_brace_block(line, idx)
                block_content = CFGParser.strip_inner_comment(block_content)
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
            
            # 使用新的命令执行器
            if cmd == "wait":
                wait_time = self.command_executor.cmd_wait(args)
                if wait_time is not None:
                    now = pygame.time.get_ticks()
                    self.wait_until = now + int(wait_time * 1000)
                    self.is_waiting = True
            elif cmd == "run":
                script_text = self.command_executor.cmd_run(args)
                if script_text:
                    self.execute(script_text)
            else:
                self.command_executor.execute_command(cmd, args)
            
            self._current_block_payload = None
        except Exception as e:
            self.error_handler.report_error(f"指令执行异常 cmd={cmd}, err={repr(e)}")
            import traceback
            traceback.print_exc()
            self._current_block_payload = None
    
    def update_wait(self, now_ms):
        """更新等待状态"""
        if self.is_waiting:
            if now_ms >= self.wait_until:
                self.is_waiting = False
                self._resume()
                # 等待结束后，如果处于对话模式且当前节点有script已执行，自动推进对话
                if self.engine and hasattr(self.engine, 'dialog') and self.engine.in_dialog_game:
                    # 触发对话继续推进
                    self.engine.dialog.start_dialogue(not_choice=False)
    
    def reset(self):
        """重置解码器"""
        self.pending_lines.clear()
        self.is_waiting = False
        self.wait_until = 0
        self.is_processing = False
        self._current_block_payload = None
        self.error_handler.clear()
