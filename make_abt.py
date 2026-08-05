import datetime
import json
import os
import shutil
import zipfile
from engine_src.tools import assets_bundle_package_build
max_size = 100 * 1024 * 1024
def build(output_dir):
    #packager = assets_bundle_package_build.ZipPackageSplitter("engine_src/res",output_dir + "engine_output/paks")
    if os.path.exists(output_dir+"/abt_output"):
        shutil.rmtree(output_dir+"/abt_output")
        os.makedirs(output_dir+"/abt_output")


    else:
        os.makedirs(output_dir+"/abt_output")
    version = input("请输入abt版本:")
    info_data = {
  "type": "abt",
  "version": f"{version}",
  "build_time": f"{datetime.datetime.now().year}/{datetime.datetime.now().month}/{datetime.datetime.now().day}"
}
    with open(output_dir+"abt_output/info.json", "w" , encoding="utf-8") as f:
        json.dump(info_data, f, ensure_ascii=False, indent=4)
    os.system(f"pyinstaller --onefile --icon=AoiStudio.png  --distpath={output_dir+'abt_output'} --name=abt editor/package/AoiStudioBuildTool.py")

    with zipfile.ZipFile(output_dir+"abt_output/abt.aoi", "w") as zip:
        zip.write(output_dir+"abt_output/abt.exe", "abt.exe")
        zip.write(output_dir+"abt_output/info.json", "info.json")
    os.remove(output_dir+"abt_output/abt.exe")
    os.remove(output_dir+"abt_output/info.json")
    #shutil.copytree("engine_src/config", output_dir+"engine_output/config")
    #shutil.copytree("engine_src/icons", output_dir+"engine_output/icons")
    #shutil.copytree("engine_src/fonts", output_dir+"engine_output/fonts")
    #packager.package()


if __name__ == "__main__":
    build("makeout/")