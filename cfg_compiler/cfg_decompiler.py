"""
CFG_C 反编译器 - 将 .cfg_c 转换回 .cfg 格式
"""

import os
import sys

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
                    match = __import__('re').match(r'\[(\w+)\]\s*(.*)', param_line)
                    if match:
                        param_name = match.group(1)
                        param_value = match.group(2).strip()
                        params[param_name] = param_value
                        print(f"[Decompiler DEBUG]   Param: {param_name} = {param_value}")
                    j += 1
                else:
                    break
            
            # 调试：打印解析到的参数
            print(f"[Decompiler DEBUG]   All params: {params}")
            
            # 根据命令类型组装参数字符串
            args = []
            
            if command == 'add character':
                args = [params.get('PATH', ''), params.get('X', '0'), params.get('Y', '0')]
            elif command == 'add background':
                args = [params.get('PATH', ''), params.get('X', '0'), params.get('Y', '0')]
            elif command == 'add game_object':
                args = [params.get('NAME', '')]
            elif command == 'add component':
                args = [params.get('GO_NAME', ''), params.get('COMP_TYPE', '')]
            elif command == 'add flag':
                args = [params.get('FLAG_NAME', '')]
            elif command == 'switch background':
                args = [params.get('PATH', ''), params.get('TRANSITION', 'fade'), params.get('DURATION', '0.5')]
            elif command == 'switch bgm':
                args = [params.get('PATH', ''), params.get('FADE_DURATION', '1.0')]
            elif command == 'move character':
                args = [params.get('INDEX', '0'), params.get('X', '0'), params.get('Y', '0'), 
                       params.get('EASING', 'linear'), params.get('DURATION', '0.5')]
            elif command == 'animation character':
                args = [params.get('INDEX', '0'), params.get('TYPE', 'shake'), 
                       params.get('PARAM1', '8.0'), params.get('PARAM2', '1.0'), params.get('DURATION', '0.5')]
            elif command == 'wait':
                args = [params.get('TIME', '1.0')]
            elif command == 'quit':
                args = []
            elif command == 'affection':
                args = [params.get('CHAR_NAME', ''), params.get('OP', 'add'), params.get('VALUE', '0')]
            elif command == 'remove character':
                args = [params.get('INDEX', '0')]
            elif command == 'remove background':
                args = [params.get('INDEX', '0')]
            elif command == 'jump dialogue_file':
                args = [params.get('PATH', '')]
            elif command == 'jump dialogue_index':
                args = [params.get('INDEX', '0')]
            elif command == 'run file':
                args = [params.get('PATH', '')]
            elif command == 'if':
                args = [params.get('CONDITION', ''), params.get('TRUE_FILE', ''), params.get('FALSE_FILE', '')]
            elif command == 'set':
                args = [params.get('VAR_NAME', ''), params.get('VALUE', '')]
            elif command == 'transition':
                args = [params.get('TYPE', 'fade'), params.get('DURATION', '0.5')]
            elif command == 'show_cg':
                args = [params.get('PATH', ''), params.get('TITLE', ''), params.get('DESCRIPTION', '')]
            elif command == 'hide_cg':
                args = [params.get('DURATION', '0.5')]
            
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
        print("Usage: python cfg_decompiler.py <input.cfg_c>")
    else:
        input_file = sys.argv[1]
        output_file = os.path.splitext(input_file)[0] + ".cfg"
        decompile_cfgc_to_cfg(input_file, output_file)
