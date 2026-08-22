import ctypes
import os
import shutil
import sys
from datetime import datetime

import pygame
from engine_src.engine.core import engine
from engine_src.engine import splash_screen
from common import AoiStudioCrasher
from common import check_game_file_full
from tkinter import messagebox
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
    # 仅Windows执行
    if sys.platform == "win32":
        # 设置独立AppUserModelID，让Windows把这个进程当成独立应用，不再归到pygame通用组
        buf = ctypes.create_unicode_buffer("aoistudio.runtime.game")
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(buf)

    pygame.init()
    if not check_game_file_full.check_game_file_full(os.getcwd()) == check_game_file_full.NOT_MISS:
        messagebox.showwarning("关键文件缺失")
    try:
        game_config = json.load(open("config/game.json", "r", encoding="utf-8"))
        game_window_size = (game_config["game_size"][0], game_config["game_size"][1])
        if game_config["splash_screen"]:
            splash_screen.main(game_window_size, game_config["name"],
                               game_config["show_studio_logo"],
                               game_config["show_made_with_engine"])
        game = engine.Engine(game_config["name"], game_window_size)
        game.run()
        if os.path.exists("plugins_runtime"):
            shutil.rmtree("plugins_runtime")
        game.debug_server.stop()
    except Exception as e:
        # 安全退出引擎，game可能未实例化
        if game is not None:
            try:
                game.debug_server.stop()
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
    if os.path.exists("plugins_runtime"):
        shutil.rmtree("plugins_runtime")

