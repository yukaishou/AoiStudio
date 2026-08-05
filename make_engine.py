import datetime
import json
import os
import shutil
import zipfile
from engine_src.tools import assets_bundle_package_build
max_size = 100 * 1024 * 1024
def build(output_dir):
    #packager = assets_bundle_package_build.ZipPackageSplitter("engine_src/res",output_dir + "engine_output/paks")
    if os.path.exists(output_dir+"/engine_output"):
        shutil.rmtree(output_dir+"/engine_output")
        os.makedirs(output_dir+"/engine_output")


    else:
        os.makedirs(output_dir+"/engine_output")
    version = input("请输入播放器版本:")
    info_data = {
  "type": "player",
  "version": f"{version}",
  "build_time": f"{datetime.datetime.now().year}/{datetime.datetime.now().month}/{datetime.datetime.now().day}"
}
    with open(output_dir+"engine_output/info.json", "w" , encoding="utf-8") as f:
        json.dump(info_data, f, ensure_ascii=False, indent=4)
    os.system(f"pyinstaller --onefile --icon=AoiStudio.png  --distpath={output_dir+'engine_output'} --name=player engine_src/main.py")
    os.system(
        f"pyinstaller --onefile --noconsole --icon=AoiStudio.png  --distpath={output_dir + 'engine_output'} --name=debug_player engine_src/main.py")
    with zipfile.ZipFile(output_dir+"engine_output/player.aoi", "w") as zip:
        zip.write(output_dir+"engine_output/player.exe", "player.exe")
        zip.write(output_dir+"engine_output/debug_player.exe", "debug_player.exe")
        zip.write(output_dir+"engine_output/info.json", "info.json")
    os.remove(output_dir+"engine_output/player.exe")
    os.remove(output_dir+"engine_output/debug_player.exe")
    os.remove(output_dir+"engine_output/info.json")
    #shutil.copytree("engine_src/config", output_dir+"engine_output/config")
    #shutil.copytree("engine_src/icons", output_dir+"engine_output/icons")
    #shutil.copytree("engine_src/fonts", output_dir+"engine_output/fonts")
    #packager.package()


if __name__ == "__main__":
    build("makeout/")