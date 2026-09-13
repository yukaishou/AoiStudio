"""
CFG_C 反编译器 - 将 .cfg_c 转换回 .cfg 格式
"""

import os
import sys
import re
import base64

# cfg_c标签到原始命令的映射
TAG_TO_COMMAND = {
    "[ADD] [CHAR]:": "add character",
    "[ADD] [BG]:": "add background",
    "[ADD] [GO]:": "add game_object",
    "[ADD] [COMP]:": "add component",
    "[ADD] [FLAG]:": "add flag",
    "[SWITCH] [BG]:": "switch background",
    "[SWITCH] [BGM]:": "switch bgm",
    "[MOVE] [CHAR]:": "move character",
    "[ANIM] [CHAR]:": "animation character",
    "[WAIT]:": "wait",
    "[QUIT]:": "quit",
    "[AFFECTION]:": "affection",
    "[REMOVE] [CHAR]:": "remove character",
    "[REMOVE] [BG]:": "remove background",
    "[JUMP] [FILE]:": "jump dialogue_file",
    "[JUMP] [INDEX]:": "jump dialogue_index",
    "[RUN] [FILE]:": "run file",
    "[IF]:": "if",
    "[SET]:": "set",
    "[TRANSITION]:": "transition",
    "[SHOW] [CG]:": "show_cg",
    "[HIDE] [CG]:": "hide_cg",
}

def decode_value(value):
    """如果值以b64:开头，则将其从base64解码并移除前缀"""
    if value.startswith("b64:"):
        encoded = value[4:]  # 移除 "b64:" 前缀
        try:
            decoded = base64.b64decode(encoded).decode('utf-8')
            return decoded  # 完全解码，不保留b64:前缀
        except Exception:
            print(f"[Decompiler WARNING] Failed to decode base64 value: {value}")
            return value
    return value

def decompile_cfgc_to_cfg(input_path, output_path):
    """将 .cfg_c 文件还原为 .cfg 格式"""
    print(f"[Decompiler] Processing: {input_path}")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 调试：打印前几行内容
    print(f"[Decompiler DEBUG] First 5 lines of input:")
    for idx, line in enumerate(lines[:5]):
        print(f"  Line {idx}: {repr(line.strip())}")
    
    cfg_lines = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # 检查是否为命令标签
        if line in TAG_TO_COMMAND:
            command = TAG_TO_COMMAND[line]
            params = {}
            
            # 调试：打印当前命令
            print(f"[Decompiler DEBUG] Found command: {line} -> {command}")
            
            # 读取后续参数行
            j = i + 1
            while j < len(lines):
                param_line = lines[j].strip()
                # 跳过空行
                if not param_line:
                    j += 1
                    continue
                # 参数行应该以[开头，包含]，但不以:结尾（命令标签以:结尾）
                if param_line.startswith('[') and ']' in param_line and not param_line.endswith(':'):
                    match = re.match(r'\[(\w+)\]\s*(.*)', param_line)
                    if match:
                        param_name = match.group(1)
                        param_value = match.group(2).strip()
                        params[param_name] = param_value
                        print(f"[Decompiler DEBUG]   Param: {param_name} = '{param_value}'")
                    else:
                        print(f"[Decompiler WARNING] Failed to parse param line: {param_line}")
                    j += 1
                else:
                    break
            
            # 调试：打印解析到的参数
            print(f"[Decompiler DEBUG]   All params: {params}")
            
            # 根据命令类型组装参数字符串
            args = []
            
            if command == 'add character':
                path = decode_value(params.get('PATH', ''))
                if not path: print(f"[Decompiler WARNING] Missing PATH for add character")
                args = [path, decode_value(params.get('X', '0')), decode_value(params.get('Y', '0'))]
            elif command == 'add background':
                path = decode_value(params.get('PATH', ''))
                if not path: print(f"[Decompiler WARNING] Missing PATH for add background")
                args = [path, decode_value(params.get('X', '0')), decode_value(params.get('Y', '0'))]
            elif command == 'add game_object':
                args = [decode_value(params.get('NAME', ''))]
            elif command == 'add component':
                args = [decode_value(params.get('GO_NAME', '')), decode_value(params.get('COMP_TYPE', ''))]
            elif command == 'add flag':
                args = [decode_value(params.get('FLAG_NAME', ''))]
            elif command == 'switch background':
                path = decode_value(params.get('PATH', ''))
                if not path:
                    print(f"[Decompiler WARNING] Missing PATH for switch background, skipping")
                    i = j
                    continue
                args = [path, decode_value(params.get('TRANSITION', 'fade')), decode_value(params.get('DURATION', '0.5'))]
            elif command == 'switch bgm':
                path = decode_value(params.get('PATH', ''))
                if not path:
                    print(f"[Decompiler WARNING] Missing PATH for switch bgm, skipping")
                    i = j
                    continue
                args = [path, decode_value(params.get('FADE_DURATION', '1.0'))]
            elif command == 'move character':
                args = [decode_value(params.get('INDEX', '0')), decode_value(params.get('X', '0')), decode_value(params.get('Y', '0')), 
                       decode_value(params.get('EASING', 'linear')), decode_value(params.get('DURATION', '0.5'))]
            elif command == 'animation character':
                args = [decode_value(params.get('INDEX', '0')), decode_value(params.get('TYPE', 'shake')), 
                       decode_value(params.get('PARAM1', '8.0')), decode_value(params.get('PARAM2', '1.0')), decode_value(params.get('DURATION', '0.5'))]
            elif command == 'wait':
                args = [decode_value(params.get('TIME', '1.0'))]
            elif command == 'quit':
                args = []
            elif command == 'affection':
                args = [decode_value(params.get('CHAR_NAME', '')), decode_value(params.get('OP', 'add')), decode_value(params.get('VALUE', '0'))]
            elif command == 'remove character':
                args = [decode_value(params.get('INDEX', '0'))]
            elif command == 'remove background':
                args = [decode_value(params.get('INDEX', '0'))]
            elif command == 'jump dialogue_file':
                args = [decode_value(params.get('PATH', ''))]
            elif command == 'jump dialogue_index':
                args = [decode_value(params.get('INDEX', '0'))]
            elif command == 'run file':
                path = decode_value(params.get('PATH', ''))
                if not path:
                    print(f"[Decompiler WARNING] Missing PATH for run file, skipping")
                    i = j
                    continue
                # 如果路径以:开头但不是file:，自动添加file前缀
                if path.startswith(':') and not path.startswith('file:'):
                    path = 'file' + path
                    print(f"[Decompiler INFO] Auto-fixed PATH: {path}")
                # run命令的特殊格式：run file:path（不是run file path）
                cfg_lines.append(f"run {path}")
                i = j
                continue
            elif command == 'if':
                args = [decode_value(params.get('CONDITION', '')), decode_value(params.get('TRUE_FILE', '')), decode_value(params.get('FALSE_FILE', ''))]
            elif command == 'set':
                args = [decode_value(params.get('VAR_NAME', '')), decode_value(params.get('VALUE', ''))]
            elif command == 'transition':
                args = [decode_value(params.get('TYPE', 'fade')), decode_value(params.get('DURATION', '0.5'))]
            elif command == 'show_cg':
                args = [decode_value(params.get('PATH', '')), decode_value(params.get('TITLE', '')), decode_value(params.get('DESCRIPTION', ''))]
            elif command == 'hide_cg':
                args = [decode_value(params.get('DURATION', '0.5'))]
            
            # 组装命令字符串
            if args:
                cfg_lines.append(f"{command} {' '.join(args)}")
            else:
                cfg_lines.append(command)
            
            i = j  # 跳过已处理的参数行
        elif line.startswith("[CMD]:"):
            # 通用命令，原样输出
            cmd = line.split(":", 1)[1].strip()
            cfg_lines.append(cmd)
            i += 1
        else:
            i += 1
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(cfg_lines))
    
    print(f"[Decompiler] Success: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: exe_file <input.cfg_c>")
    else:
        input_file = sys.argv[1]
        output_file = os.path.splitext(input_file)[0] + ".cfg"
        decompile_cfgc_to_cfg(input_file, output_file)
