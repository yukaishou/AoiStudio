"""
CFG 脚本编译器 - 将 .cfg 转换为结构化的 .cfg_c 格式
"""

import os
import sys
import re
import base64

# 全局变量：是否启用base64编码（默认启用）
ENABLE_BASE64 = True

# 指令映射表：原始指令关键字 -> cfg_c 标签及参数定义
COMMAND_MAP = {
    "add character": {"tag": "[ADD] [CHAR]:", "params": ["PATH", "X", "Y"]},
    "add background": {"tag": "[ADD] [BG]:", "params": ["PATH", "X", "Y"]},
    "add game_object": {"tag": "[ADD] [GO]:", "params": ["NAME"]},
    "add component": {"tag": "[ADD] [COMP]:", "params": ["GO_NAME", "COMP_TYPE"]},
    "add flag": {"tag": "[ADD] [FLAG]:", "params": ["FLAG_NAME"]},
    "switch background": {"tag": "[SWITCH] [BG]:", "params": ["PATH", "TRANSITION", "DURATION"]},
    "switch bgm": {"tag": "[SWITCH] [BGM]:", "params": ["PATH", "FADE_DURATION"]},
    "move character": {"tag": "[MOVE] [CHAR]:", "params": ["INDEX", "X", "Y", "EASING", "DURATION"]},
    "animation character": {"tag": "[ANIM] [CHAR]:", "params": ["INDEX", "TYPE", "PARAM1", "PARAM2", "DURATION"]},
    "wait": {"tag": "[WAIT]:", "params": ["TIME"]},
    "quit": {"tag": "[QUIT]:", "params": []},
    "affection": {"tag": "[AFFECTION]:", "params": ["CHAR_NAME", "OP", "VALUE"]},
    "remove character": {"tag": "[REMOVE] [CHAR]:", "params": ["INDEX"]},
    "remove background": {"tag": "[REMOVE] [BG]:", "params": ["INDEX"]},
    "jump dialogue_file": {"tag": "[JUMP] [FILE]:", "params": ["PATH"]},
    "jump dialogue_index": {"tag": "[JUMP] [INDEX]:", "params": ["INDEX"]},
    "run file": {"tag": "[RUN] [FILE]:", "params": ["PATH"]},
    "if": {"tag": "[IF]:", "params": ["CONDITION", "TRUE_FILE", "FALSE_FILE"]},
    "set": {"tag": "[SET]:", "params": ["VAR_NAME", "VALUE"]},
    "transition": {"tag": "[TRANSITION]:", "params": ["TYPE", "DURATION"]},
    "show_cg": {"tag": "[SHOW] [CG]:", "params": ["PATH", "TITLE", "DESCRIPTION"]},
    "hide_cg": {"tag": "[HIDE] [CG]:", "params": ["DURATION"]},
}

def encode_value(value):
    """对参数值进行base64编码（受ENABLE_BASE64控制）"""
    if ENABLE_BASE64:
        encoded = base64.b64encode(value.encode('utf-8')).decode('utf-8')
        return f"b64:{encoded}"
    return value

def remove_comments(line):
    """移除行中的注释（支持 // 和 #）"""
    if "//" in line:
        line = line.split("//", 1)[0]
    if "#" in line:
        line = line.split("#", 1)[0]
    return line.strip()

def compile_cfg_to_cfgc(input_path, output_path):
    """将 .cfg 文件编译为 .cfg_c 格式"""
    print(f"[Compiler] Processing: {input_path}")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    compiled_lines = []
    
    for line in lines:
        cleaned = remove_comments(line)
        if not cleaned:
            continue
        
        # 尝试匹配已知指令
        matched = False
        lower_line = cleaned.lower()
        
        for keyword, info in COMMAND_MAP.items():
            if lower_line.startswith(keyword):
                # 提取参数部分
                params_str = cleaned[len(keyword):].strip()
                
                # 写入指令头
                compiled_lines.append(info["tag"])
                
                # 写入参数
                param_values = params_str.split()
                for i, param_name in enumerate(info["params"]):
                    if i < len(param_values):
                        value = encode_value(param_values[i])
                        compiled_lines.append(f"    [{param_name}] {value}")
                
                matched = True
                break
        
        if not matched:
            # 如果没匹配到，原样保留或作为通用指令处理
            compiled_lines.append(f"[CMD]: {cleaned}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(compiled_lines))
    
    print(f"[Compiler] Success: {output_path}")

def compile_dir(input_dir, output_dir):
    """将目录下的所有 .cfg 文件编译为 .cfg_c 格式，保留子目录结构"""
    print(f"[Compiler] Processing directory: {input_dir}")

    if not os.path.exists(input_dir):
        print(f"[Compiler] Error: Input directory does not exist.")
        return

    os.makedirs(output_dir, exist_ok=True)

    for root, dirs, files in os.walk(input_dir):
        # 计算相对路径，用于在输出目录重建文件夹层级
        rel_root = os.path.relpath(root, input_dir)
        out_sub_dir = os.path.join(output_dir, rel_root)
        os.makedirs(out_sub_dir, exist_ok=True)

        for file in files:
            if file.endswith(".cfg"):
                input_path = os.path.join(root, file)
                base_name = os.path.splitext(file)[0]
                output_path = os.path.join(out_sub_dir, base_name + ".cfg_c")
                print(f"[Compiler] Compile: {input_path} -> {output_path}")
                compile_cfg_to_cfgc(input_path, output_path)

if __name__ == "__main__":
    # 解析命令行参数：--nobase64 参数禁用base64编码
    if "--nobase64" in sys.argv:
        ENABLE_BASE64 = False
        sys.argv.remove("--nobase64")
    
    if len(sys.argv) < 2:
        print("Usage: exe_file [--nobase64] <input.cfg> [output_dir]")
    else:
        if len(sys.argv) >= 3:
            compile_dir(sys.argv[1], sys.argv[2])
        input_file = sys.argv[1]
        output_file = os.path.splitext(input_file)[0] + ".cfg_c"
        compile_cfg_to_cfgc(input_file, output_file)