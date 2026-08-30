"""
CFG 脚本编译器 - 将 .cfg 转换为结构化的 .cfg_c 格式
"""

import os
import sys
import re

# 指令映射表：原始指令关键字 -> cfg_c 标签及参数定义
COMMAND_MAP = {
    "add character": {"tag": "[ADD] [CHAR]:", "params": ["PATH", "X", "Y"]},
    "switch background": {"tag": "[SWITCH] [BG]:", "params": ["PATH", "FADE"]},
    "wait": {"tag": "[WAIT]:", "params": ["TIME"]},
    "show text": {"tag": "[SHOW] [TEXT]:", "params": ["CONTENT"]},
    "play bgm": {"tag": "[PLAY] [BGM]:", "params": ["PATH"]},
    "stop bgm": {"tag": "[STOP] [BGM]:", "params": []},
    "transition": {"tag": "[TRANSITION]:", "params": ["TYPE", "TIME"]},
}

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
                        value = param_values[i]
                        # 处理 file: 前缀或特殊格式
                        compiled_lines.append(f"    [{param_name}] {value}")
                
                matched = True
                break
        
        if not matched:
            # 如果没匹配到，原样保留或作为通用指令处理
            compiled_lines.append(f"[CMD]: {cleaned}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(compiled_lines))
    
    print(f"[Compiler] Success: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python compiler_main.py <input.cfg>")
    else:
        input_file = sys.argv[1]
        output_file = os.path.splitext(input_file)[0] + ".cfg_c"
        compile_cfg_to_cfgc(input_file, output_file)
