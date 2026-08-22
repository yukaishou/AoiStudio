import os
import sys
import shutil

def main():
    if os.path.exists('makeout/plugin_sdk_output'):
        shutil.rmtree('makeout/plugin_sdk_output')
    os.makedirs('makeout/plugin_sdk_output')
    shutil.copyfile("plugin_sdk/icon.png", "makeout/plugin_sdk_output/icon.png")
    os.system("pyinstaller --onefile --icon AoiStudio.png --name AoiStudioPluginSDK --distpath makeout/plugin_sdk_output plugin_sdk/AoiStudioPluginBuildTool.py")

if __name__ == "__main__":
    main()
