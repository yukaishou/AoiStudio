import os
import shutil
import subprocess
from engine_src.tools import assets_bundle_package_build
import json
import sys
import platform

max_size = 100 * 1024 * 1024

def kill_exes(process_names):
    """Force kill running processes by name to free locked files"""
    for name in process_names:
        subprocess.run(["taskkill", "/F", "/IM", name],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def build(output_dir, editor_ui_ver, player_ver, abt_ver):
    exe_dir = os.path.join(output_dir, "editor_output", "bin")
    main_exe = os.path.join(output_dir, "editor_output", "AoiStudioEditor.exe")
    hook_path = os.path.abspath("my_hooks")  # 动态钩子路径

    # Kill running instances before cleanup
    kill_exes(["AoiStudioEditor.exe", "AoiStudio_Player.exe", "AoiStudio_Player_debug.exe",
               "AoiStudioBuildTool.exe", "AoiStudio_Debugger.exe"])

    editor_out = os.path.join(output_dir, "editor_output")
    if os.path.exists(editor_out):
        shutil.rmtree(editor_out)
    os.makedirs(editor_out)
    os.makedirs(exe_dir)

    # 播放器、debug播放器、BuildTool
    if player_ver != "":
        ret = subprocess.run([
            "pyinstaller",
            "--onefile", "--noconsole", "--icon=AoiStudio.png",
            "--distpath", exe_dir,
            "--name", "AoiStudio_Player",
            "engine_src/main.py"
        ])
        if ret.returncode != 0:
            print("!!! AoiStudio_Player 打包失败")

        ret = subprocess.run([
            "pyinstaller",
            "--onefile", "--icon=AoiStudio.png",
            "--distpath", exe_dir,
            "--name", "AoiStudio_Player_debug",
            "engine_src/main.py"
        ])
        if ret.returncode != 0:
            print("!!! AoiStudio_Player_debug 打包失败")

        ret = subprocess.run([
            "pyinstaller",
            "--onefile", "--icon=AoiStudio.png",
            "--distpath", exe_dir,
            "--name", "AoiStudioBuildTool",
            "editor/package/AoiStudioBuildTool.py"
        ])
        if ret.returncode != 0:
            print("!!! AoiStudioBuildTool 打包失败")

    # ========== 编辑器本体：使用正确参数 --additional‑hooks‑dir ==========
    ret = subprocess.run([
    "pyinstaller",
    "--onefile", "--noconsole", "--icon=AoiStudio.png",
    "--exclude-module", "pyqtgraph",
    "--exclude-module", "PyQt5",
    "--distpath", editor_out,
    "--name", "AoiStudioEditor",
    "editor/editor_main.py"
])
    if ret.returncode != 0:
        print("!!! AoiStudioEditor 打包失败！")
        sys.exit(1)

    # Debugger
    ret = subprocess.run([
        "pyinstaller",
        "--noconsole", "--onefile", "--icon=AoiStudio.png",
        "--distpath", exe_dir,
        "--add-data", "debugger/AoiStudio.png;icons",
        "--name", "AoiStudio_Debugger",
        "debugger/debugger_main.py"
    ])
    if ret.returncode != 0:
        print("!!! AoiStudio_Debugger 打包失败")

    # 复制资源目录
    shutil.copytree("editor/config", os.path.join(editor_out, "config"))
    shutil.copytree("editor/res", os.path.join(editor_out, "res"))

    config_json_path = os.path.join(editor_out, "config", "editor.json")
    with open(config_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "version": {
                "editor_ui": f"{editor_ui_ver}",
                "player": f"{player_ver}",
                "abt": f"{abt_ver}"
            },
            "platform": {
                "name": f"{platform.system()}"
            }
        }, indent=4, fp=f)

if __name__ == "__main__":
    build_player = input("是否编译播放器和ABT：")
    if build_player != "y":
        editor_ui_ver = input("请输入编辑器UI版本：")
        build("makeout/", editor_ui_ver, "", "")
        sys.exit()
    editor_ui_ver = input("请输入编辑器UI版本：")
    player_ver = input("请输入播放器版本：")
    abt_ver = input("请输入ABT版本：")
    build("makeout/", editor_ui_ver, player_ver, abt_ver)