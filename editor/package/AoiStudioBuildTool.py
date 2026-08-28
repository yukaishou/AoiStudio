import json
import os
import py_compile
import shutil
import sys
import time
import gc
from tkinter import filedialog
from editor.package.os_tools import tool_image_to_ico, tool_chage_exe_icon
import assets_bundle_package_build
from common import pyc_compiler


class AoiBuildTool:
    def __init__(self, player_path, project_path, output_path, enable_pyc_obfuscate: bool = True):
        self.player_path = player_path
        self.project_path = project_path
        self.output_path = output_path
        self.enable_pyc_obfuscate = enable_pyc_obfuscate
        self.src_res = os.path.join(self.project_path, "res")
        self.backup_py_dir = os.path.join(self.output_path, "__build_py_backup")
        self.packager = None

    def _backup_project_py(self):
        """备份项目res全部py文件到备份目录，保留完整目录树"""
        if os.path.exists(self.backup_py_dir):
            shutil.rmtree(self.backup_py_dir)
        os.makedirs(self.backup_py_dir, exist_ok=True)
        for root, dirs, files in os.walk(self.src_res):
            if "__pycache__" in dirs:
                dirs.remove("__pycache__")
            rel = os.path.relpath(root, self.src_res)
            dst_sub = os.path.join(self.backup_py_dir, rel)
            os.makedirs(dst_sub, exist_ok=True)
            for f in files:
                if f.endswith(".py"):
                    shutil.copy2(os.path.join(root, f), os.path.join(dst_sub, f))

    def _restore_project_py(self):
        """从备份把py源码还原回项目res，恢复打包前状态"""
        if not os.path.exists(self.backup_py_dir):
            return
        # 删除项目当前所有py（此时是打包期间生成的pyc还在，py要写回来）
        for root, dirs, files in os.walk(self.src_res):
            if "__pycache__" in dirs:
                dirs.remove("__pycache__")
            for f in files:
                if f.endswith(".py"):
                    os.remove(os.path.join(root, f))
        # 把备份py复制回原res
        for root, dirs, files in os.walk(self.backup_py_dir):
            rel = os.path.relpath(root, self.backup_py_dir)
            dst_sub = os.path.join(self.src_res, rel)
            os.makedirs(dst_sub, exist_ok=True)
            for f in files:
                shutil.copy2(os.path.join(root, f), os.path.join(dst_sub, f))
        # 清理本次打包产生的pyc，不要残留在项目目录
        for root, dirs, files in os.walk(self.src_res):
            if "__pycache__" in dirs:
                dirs.remove("__pycache__")
            for f in files:
                if f.endswith(".pyc"):
                    os.remove(os.path.join(root, f))
        # 删除备份文件夹
        shutil.rmtree(self.backup_py_dir)

    def _project_to_only_pyc(self):
        """在源项目res：编译pyc，删除py，此时项目只有pyc"""
        pyc_compiler.compile_dir(self.src_res, self.src_res)
        for root, dirs, files in os.walk(self.src_res):
            if "__pycache__" in dirs:
                dirs.remove("__pycache__")
            for f in files:
                if f.endswith(".py"):
                    os.remove(os.path.join(root, f))

    def build(self):
        out_dir = os.path.join(self.output_path, "output")
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)
        os.makedirs(out_dir, exist_ok=True)
        os.makedirs(os.path.join(out_dir, "paks"), exist_ok=True)

        shutil.copytree(os.path.join(self.project_path, "config"), os.path.join(out_dir, "config"))
        shutil.copytree(os.path.join(self.project_path, "icons"), os.path.join(out_dir, "icons"))
        shutil.copytree(os.path.join(self.project_path, "fonts"), os.path.join(out_dir, "fonts"))

        config_fp = os.path.join(self.project_path, "config", "game.json")
        with open(config_fp, "r", encoding="utf‑8") as f:
            game_cfg = json.load(f)
        game_name = game_cfg["name"]

        exe_target = os.path.join(out_dir, f"{game_name}.exe")
        shutil.copyfile(self.player_path, exe_target)

        # ==========打包核心流程：备份‑try‑finally恢复==========
        self._backup_project_py()
        try:
            if self.enable_pyc_obfuscate:
                self._project_to_only_pyc()
            # packager读取【源项目res】，此时里面只有pyc
            self.packager = assets_bundle_package_build.ZipPackageSplitter(
                self.src_res,
                os.path.join(out_dir, "paks")
            )
            self.packager.package()

        finally:
            # 无论正常完成、异常报错，一定还原项目源码，清理项目内pyc
            self._restore_project_py()
        # =====================================================

        # 产物侧：输出目录不需要松散res文件夹（packager已经打进paks）
        out_res = os.path.join(out_dir, "res")
        if os.path.exists(out_res):
            shutil.rmtree(out_res)

        tmp_ico = "tmp_build_icon.ico"
        try:
            icon_src = os.path.join(self.project_path, "icons", "AppIcon.png")
            tool_image_to_ico.to_ico(icon_src, tmp_ico)
            tool_chage_exe_icon.patch_pyinstaller_icon_inplace(exe_target, tmp_ico)
        except Exception:
            print("图标替换失败")
            import traceback
            traceback.print_exc()
        finally:
            if os.path.exists(tmp_ico):
                os.remove(tmp_ico)
            backup_exe = os.path.splitext(exe_target)[0] + "_backup.exe"
            if os.path.exists(backup_exe):
                os.remove(backup_exe)

        gc.collect()
        time.sleep(0.25)

        final_folder = os.path.join(self.output_path, game_name)
        if os.path.exists(final_folder):
            shutil.rmtree(final_folder)
        shutil.move(out_dir, final_folder)

        if sys.platform == "win32":
            os.startfile(final_folder)
        print(f"打包完成输出：{final_folder}")


def main():

    enable_pyc = True
    if len(sys.argv) >= 5:
        proj = sys.argv[1]
        out = sys.argv[2]
        player_exe = sys.argv[3]
        enable_pyc = sys.argv[4].lower() == "true"
    elif len(sys.argv) >= 4:
        proj = sys.argv[1]
        out = sys.argv[2]
        player_exe = sys.argv[3]
    else:
        from tkinter import filedialog
        proj = filedialog.askdirectory(title="项目目录")
        if not proj:
            return
        player_exe = filedialog.askopenfilename(title="选择player.exe")
        if not player_exe:
            return
        out = filedialog.askdirectory(title="输出目录")
        if not out:
            return

    builder = AoiBuildTool(player_exe, proj, out, enable_pyc_obfuscate=enable_pyc)
    builder.build()



if __name__ == "__main__":
    main()