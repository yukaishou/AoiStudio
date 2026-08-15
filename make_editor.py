import os
import shutil
from engine_src.tools import assets_bundle_package_build
import json
import sys
import platform
max_size = 100 * 1024 * 1024
def build(output_dir,editor_ui_ver,player_ver,abt_ver):
    if os.path.exists(output_dir+"/editor_output"):
        shutil.rmtree(output_dir+"/editor_output")
        os.makedirs(output_dir+"/editor_output")
        os.makedirs(output_dir+"/editor_output/bin")

    else:
        os.makedirs(output_dir+"/editor_output")
        os.makedirs(output_dir+"/editor_output/bin")
    if not player_ver == "":
        os.system(
            f"pyinstaller --onefile --noconsole --icon=AoiStudio.png  --distpath={output_dir + 'editor_output/bin'} --name=AoiStudio_Player engine_src/main.py")
        os.system(
            f"pyinstaller --onefile  --icon=AoiStudio.png  --distpath={output_dir + 'editor_output/bin'} --name=AoiStudio_Player_debug engine_src/main.py")
        os.system(
            f"pyinstaller --onefile --icon=AoiStudio.png  --distpath={output_dir + 'editor_output/bin'} --name=AoiStudioBuildTool editor/package/AoiStudioBuildTool.py")
    os.system(
        f"pyinstaller --onefile --noconsole --icon=AoiStudio.png  --distpath={output_dir + 'editor_output'} --name=AoiStudioEditor editor/editor_main.py")
    os.system(
        f"pyinstaller --noconsole  --onefile --icon=AoiStudio.png  --distpath={output_dir + 'editor_output/bin'} --add-data debugger/AoiStudio.png;icons --name=AoiStudio_Debugger debugger/debugger_main.py")

    shutil.copytree("editor/config", output_dir+"editor_output/config")
    shutil.copytree("editor/res", output_dir+"editor_output/res")
    with open(f"{output_dir}editor_output/config/editor.json", "w") as f:
        json.dump({

                "version": {
                    "editor_ui": f"{editor_ui_ver}",
                    "player": f"{player_ver}",
                    "abt":f"{abt_ver}"
                },
                "platform": {
                    "name": f"{platform.system()}"
                }

        },indent=4,fp=f)




if __name__ == "__main__":
    build_player = input("是否编译播放器和ABT：")
    if not build_player == "y":
        editor_ui_ver = input("请输入编辑器UI版本：")
        build("makeout/",editor_ui_ver,"","")
        sys.exit()
    editor_ui_ver = input("请输入编辑器UI版本：")
    player_ver = input("请输入播放器版本：")
    abt_ver = input("请输入ABT版本：")
    build("makeout/",editor_ui_ver,player_ver,abt_ver)