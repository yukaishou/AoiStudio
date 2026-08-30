"""
CFG 解析器 - 改进的脚本解析功能

改进点：
1. 强制缩进检查（可选）
2. 增强的注释支持（// 和 #）
3. 更好的错误定位
4. 变量引用解析
"""

import re
from typing import List, Optional, Tuple
from engine_src.engine.core import log
from .error_handler import CFGErrorHandler
from .variable_manager import VariableManager


class CFGParser:
    """
    CFG 脚本解析器
    
    特性：
    - 支持 // 和 # 单行注释
    - 可选的强制缩进检查
    - 嵌套 if/else/endif 块解析
    - 变量引用自动解析
    - 详细的错误定位
    """
    
    def __init__(self, error_handler: CFGErrorHandler, variable_manager: VariableManager,
                 enforce_indent: bool = False):
        self.error_handler = error_handler
        self.variable_manager = variable_manager
        self.enforce_indent = enforce_indent  # 是否强制缩进检查
        self.IF_BLOCK_SEP = "||"  # 块内分隔符
    
    def parse(self, text: str, file_path: str = "") -> List[str]:
        """
        解析 CFG 脚本为语句列表
        
        Args:
            text: 脚本内容（支持.cfg和.cfg_c格式）
            file_path: 文件路径（用于错误定位）
        
        Returns:
            语句列表
        """
        self.error_handler.current_file = file_path
        
        # 检测是否为.cfg_c格式
        if self._is_cfgc_format(text):
            return self._parse_cfgc(text, file_path)
        
        # 原始.cfg格式解析
        lines = text.splitlines()
        stmts = []
        
        for i, line in enumerate(lines):
            self.error_handler.set_current_location(i + 1, file_path)
            
            # 移除注释（支持 // 和 #）
            cleaned_line = self._remove_comments(line)
            if not cleaned_line.strip():
                continue
            
            # 检查缩进（如果启用）
            if self.enforce_indent:
                indent_level = len(line) - len(line.lstrip())
                if indent_level % 4 != 0:
                    self.error_handler.report_warning(
                        f"缩进不是4的倍数: {indent_level}",
                        line_number=i + 1,
                        context=line[:50]
                    )
            
            stmts.append(cleaned_line.strip())
        
        # 处理 if/else/endif 块
        return self._process_blocks(stmts, file_path)
    
    def _is_cfgc_format(self, text: str) -> bool:
        """检测是否为.cfg_c格式"""
        # .cfg_c格式通常以[开头的标签开始
        lines = text.strip().split('\n')
        for line in lines[:10]:  # 检查前10行
            stripped = line.strip()
            if stripped and stripped.startswith('['):
                return True
        return False
    
    def _parse_cfgc(self, text: str, file_path: str) -> List[str]:
        """解析.cfg_c格式为可执行的语句"""
        lines = text.splitlines()
        stmts = []
        current_command = None
        current_params = {}
        
        for i, line in enumerate(lines):
            self.error_handler.set_current_location(i + 1, file_path)
            stripped = line.strip()
            
            if not stripped:
                continue
            
            # 检测命令标签（如 [ADD] [CHAR]:）
            if stripped.startswith('[') and ':' in stripped:
                # 保存上一个命令
                if current_command:
                    cmd_str = self._cfgc_to_command(current_command, current_params)
                    if cmd_str:
                        stmts.append(cmd_str)
                
                # 解析新命令
                current_command = stripped
                current_params = {}
            
            # 检测参数（如 [PATH] file:xx/xx）
            elif stripped.startswith('[') and ']' in stripped:
                match = re.match(r'\[(\w+)\]\s*(.*)', stripped)
                if match and current_command:
                    param_name = match.group(1)
                    param_value = match.group(2).strip()
                    current_params[param_name] = param_value
        
        # 保存最后一个命令
        if current_command:
            cmd_str = self._cfgc_to_command(current_command, current_params)
            if cmd_str:
                stmts.append(cmd_str)
        
        return stmts
    
    def _cfgc_to_command(self, tag: str, params: dict) -> str:
        """将.cfg_c标签和参数转换为可执行命令"""
        # 定义标签到命令的映射
        tag_map = {
            '[ADD] [CHAR]:': 'add character',
            '[ADD] [BG]:': 'add background',
            '[ADD] [GO]:': 'add game_object',
            '[ADD] [COMP]:': 'add component',
            '[ADD] [FLAG]:': 'add flag',
            '[SWITCH] [BG]:': 'switch background',
            '[SWITCH] [BGM]:': 'switch bgm',
            '[MOVE] [CHAR]:': 'move character',
            '[ANIM] [CHAR]:': 'animation character',
            '[WAIT]:': 'wait',
            '[QUIT]:': 'quit',
            '[AFFECTION]:': 'affection',
            '[REMOVE] [CHAR]:': 'remove character',
            '[REMOVE] [BG]:': 'remove background',
            '[JUMP] [FILE]:': 'jump dialogue_file',
            '[JUMP] [INDEX]:': 'jump dialogue_index',
            '[RUN] [FILE]:': 'run file',
            '[IF]:': 'if',
            '[SET]:': 'set',
            '[TRANSITION]:': 'transition',
            '[SHOW] [CG]:': 'show_cg',
            '[HIDE] [CG]:': 'hide_cg',
        }
        
        command = tag_map.get(tag)
        if not command:
            return None
        
        # 根据命令类型组装参数字符串
        args = []
        
        if command == 'add character':
            path = params.get('PATH', '')
            x = params.get('X', '0')
            y = params.get('Y', '0')
            args = [path, x, y]
        
        elif command == 'add background':
            path = params.get('PATH', '')
            x = params.get('X', '0')
            y = params.get('Y', '0')
            args = [path, x, y]
        
        elif command == 'add game_object':
            name = params.get('NAME', '')
            args = [name]
        
        elif command == 'add component':
            go_name = params.get('GO_NAME', '')
            comp_type = params.get('COMP_TYPE', '')
            args = [go_name, comp_type]
        
        elif command == 'add flag':
            flag_name = params.get('FLAG_NAME', '')
            args = [flag_name]
        
        elif command == 'switch background':
            path = params.get('PATH', '')
            transition = params.get('TRANSITION', 'fade')
            duration = params.get('DURATION', '0.5')
            args = [path, transition, duration]
        
        elif command == 'switch bgm':
            path = params.get('PATH', '')
            fade_duration = params.get('FADE_DURATION', '1.0')
            args = [path, fade_duration]
        
        elif command == 'move character':
            index = params.get('INDEX', '0')
            x = params.get('X', '0')
            y = params.get('Y', '0')
            easing = params.get('EASING', 'linear')
            duration = params.get('DURATION', '0.5')
            args = [index, x, y, easing, duration]
        
        elif command == 'animation character':
            index = params.get('INDEX', '0')
            anim_type = params.get('TYPE', 'shake')
            param1 = params.get('PARAM1', '8.0')
            param2 = params.get('PARAM2', '1.0')
            duration = params.get('DURATION', '0.5')
            args = [index, anim_type, param1, param2, duration]
        
        elif command == 'wait':
            time = params.get('TIME', '1.0')
            args = [time]
        
        elif command == 'affection':
            char_name = params.get('CHAR_NAME', '')
            op = params.get('OP', 'add')
            value = params.get('VALUE', '0')
            args = [char_name, op, value]
        
        elif command == 'remove character':
            index = params.get('INDEX', '0')
            args = [index]
        
        elif command == 'remove background':
            index = params.get('INDEX', '0')
            args = [index]
        
        elif command == 'jump dialogue_file':
            path = params.get('PATH', '')
            args = [path]
        
        elif command == 'jump dialogue_index':
            index = params.get('INDEX', '0')
            args = [index]
        
        elif command == 'run file':
            path = params.get('PATH', '')
            args = [path]
        
        elif command == 'if':
            condition = params.get('CONDITION', '')
            true_file = params.get('TRUE_FILE', '')
            false_file = params.get('FALSE_FILE', '')
            args = [condition, true_file, false_file]
        
        elif command == 'set':
            var_name = params.get('VAR_NAME', '')
            value = params.get('VALUE', '')
            args = [var_name, value]
        
        elif command == 'transition':
            trans_type = params.get('TYPE', 'fade')
            duration = params.get('DURATION', '0.5')
            args = [trans_type, duration]
        
        elif command == 'show_cg':
            path = params.get('PATH', '')
            title = params.get('TITLE', '')
            description = params.get('DESCRIPTION', '')
            args = [path, title, description]
        
        elif command == 'hide_cg':
            duration = params.get('DURATION', '0.5')
            args = [duration]
        
        elif command == 'quit':
            args = []
        
        # 组装命令字符串
        if args:
            return f"{command} {' '.join(args)}"
        else:
            return command
    
    def _remove_comments(self, line: str) -> str:
        """移除行中的注释（支持 // 和 #）"""
        # 先处理 // 注释
        if "//" in line:
            line = line.split("//", 1)[0]
        # 再处理 # 注释（但要避免在字符串中）
        if "#" in line:
            line = line.split("#", 1)[0]
        return line
    
    def _process_blocks(self, stmts: List[str], file_path: str) -> List[str]:
        """处理 if/else/endif 块"""
        result = []
        i = 0
        
        while i < len(stmts):
            line = stmts[i]
            lower = line.lower().lstrip()
            
            # 检测 if 关键字
            if lower.startswith("if ") or lower == "if":
                # 检查是否为单行 if 语法（包含 file: 路径）
                if "file:" in line:
                    result.append(line)
                    i += 1
                    continue
                
                # 多行 if 块处理
                cond_part = line[3:].strip() if len(line) > 3 else ""
                
                true_lines = []
                false_lines = []
                in_else = False
                depth = 0
                i += 1
                
                while i < len(stmts):
                    inner = stmts[i].strip()
                    inner_lower = inner.lower().lstrip()
                    
                    handled = False
                    if inner_lower.startswith("if ") or inner_lower == "if":
                        depth += 1
                        (true_lines if not in_else else false_lines).append(inner)
                        handled = True
                    elif inner_lower == "endif":
                        depth -= 1
                        if depth < 0:
                            i += 1
                            break
                        (true_lines if not in_else else false_lines).append(inner)
                        handled = True
                    elif inner_lower == "else" and depth == 0:
                        in_else = True
                        handled = True
                    
                    if not handled:
                        (true_lines if not in_else else false_lines).append(inner)
                    i += 1
                
                true_block = "\n".join(true_lines)
                false_block = "\n".join(false_lines)
                token = f"__IF_BLOCK__:{cond_part}{self.IF_BLOCK_SEP}{true_block}{self.IF_BLOCK_SEP}{false_block}"
                result.append(token)
                continue
            
            result.append(line)
            i += 1
        
        return result
    
    @staticmethod
    def extract_brace_block(text: str, start_idx: int) -> Tuple[Optional[str], int]:
        """
        提取花括号块内容
        
        Returns:
            (块内容, 结束位置)
        """
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
    def strip_inner_comment(text: str) -> str:
        """移除块内部的注释"""
        lines = []
        for line in text.splitlines():
            if "//" in line:
                line = line.split("//", 1)[0]
            if "#" in line:
                line = line.split("#", 1)[0]
            lines.append(line)
        return "\n".join(lines).strip()
