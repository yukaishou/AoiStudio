import json
import os
import shutil
import sys
import time
import gc
from tkinter import filedialog
from editor.os_tools import tool_image_to_ico, tool_chage_exe_icon
import assets_bundle_package_build

class AoiBuildTool:
    def __init__(self,player_path,project_path,output_path):
        self.player_path = player_path
        self.project_path = project_path
        self.output_path = output_path
        self.packager = assets_bundle_package_build.ZipPackageSplitter(project_path+"/res",output_path+"/output/paks")

    def build(self):
        out_dir = os.path.join(self.output_path, "output")
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)
        os.mkdir(out_dir)
        os.mkdir(os.path.join(out_dir, "paks"))
        shutil.copytree(os.path.join(self.project_path,"config"), os.path.join(out_dir,"config"))
        shutil.copytree(os.path.join(self.project_path,"icons"), os.path.join(out_dir,"icons"))
        shutil.copytree(os.path.join(self.project_path,"fonts"), os.path.join(out_dir,"fonts"))

        game_cfg = json.load(open(os.path.join(self.project_path,"config","game.json"), "r", encoding="utf-8"))
        game_name = game_cfg["name"]

        exe_target = os.path.join(out_dir, f"{game_name}.exe")
        shutil.copyfile(self.player_path, exe_target)

        self.packager.package()

        tmp_ico = "tmp.ico"
        try:
            tool_image_to_ico.to_ico(os.path.join(self.project_path,"icons","AppIcon.png"), tmp_ico)
            tool_chage_exe_icon.patch_pyinstaller_icon_inplace(exe_target, tmp_ico)
        except Exception as e:
            print("图标转换失败")
            import traceback
            traceback.print_exc()
        finally:
            # 清理临时ico
            if os.path.exists(tmp_ico):
                os.remove(tmp_ico)
            # 删除生成的backup备份文件，不要打进发布包
            backup_exe = os.path.splitext(exe_target)[0] + "_backup.exe"
            if os.path.exists(backup_exe):
                os.remove(backup_exe)

        # 强制回收所有对象，释放pefile、ctypes残留文件锁！解决WinError32占用
        gc.collect()
        time.sleep(0.25)

        final_folder = os.path.join(self.output_path, game_name)
        shutil.move(out_dir, final_folder)

        os.startfile(final_folder)
        # 这个是阻塞的，是用来看日志的，用来测试的时候就把注释去掉
        #input("按Enter键退出...")


if __name__ == "__main__":
    if len(sys.argv) >=4:
        project_path = sys.argv[1]
        output_path = sys.argv[2]
        player_path = sys.argv[3]
    else:
        project_path = filedialog.askdirectory()
        if not project_path:
            exit()
        player_path = filedialog.askopenfilename()
        if not player_path:
            exit()
        output_path = filedialog.askdirectory()
        if not output_path:
            exit()
    tool = AoiBuildTool(player_path,project_path,output_path)
    tool.build()