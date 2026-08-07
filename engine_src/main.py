import os
import shutil
from datetime import datetime

import pygame
from engine_src.engine.core import engine
from engine_src.engine import splash_screen
from common import AoiStudioCrasher
import json
import traceback
import platform

if __name__ == "__main__":
    game = None
    if os.name == 'nt':  # Windows DPI感知
        from ctypes import windll
        windll.user32.SetProcessDPIAware()
        try:
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    pygame.init()
    try:
        game_config = json.load(open("config/game.json", "r", encoding="utf-8"))
        game_window_size = (game_config["game_size"][0], game_config["game_size"][1])
        if game_config["splash_screen"]:
            splash_screen.main(game_window_size, game_config["name"],
                               game_config["show_studio_logo"],
                               game_config["show_made_with_engine"])
        game = engine.Engine(game_config["name"], game_window_size)
        game.run()
        shutil.rmtree("plugins_runtime")
    except Exception as e:
        if os.path.exists("plugins_runtime"):
            shutil.rmtree("plugins_runtime")

        # 安全退出引擎，game可能未实例化
        if game is not None:
            try:
                game.quit()
            except Exception:
                pass
        # 确保pygame关闭
        try:
            pygame.quit()
        except Exception:
            pass

        crash_text = f"""AoiStudio Fatal Crash Report
========================================
Crash Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
OS: {platform.system()} {platform.release()}
Python Version: {platform.python_version()}
Pygame Version: {pygame.__version__}
Engine Version: {json.load(open("config/game.json", "r", encoding="utf-8"))["engine_version"]}
========================================

Exception Traceback:
{traceback.format_exc()}
"""
        # 注释掉messagebox，避免双重弹窗干扰；也可以保留，按需选择
        # messagebox.showerror("AoiStudio Error", str(e) + "\n Click OK to exit")
        AoiStudioCrasher.main(crash_text)

    finally:
        # 兜底释放pygame资源
        try:
            pygame.quit()
        except Exception:
            pass

