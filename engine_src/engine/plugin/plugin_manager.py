import os
import zipfile
from importlib import util

from engine_src.engine.plugin.plugin_api import PluginAPI
import json

class PluginManager:
    def __init__(self,engine):
        self.plugins = []
        self.engine = engine
        self.plugin_api = PluginAPI(self.engine)

    def load_plugin(self,path):
        if not os.path.exists("plugins_runtime"):
            os.mkdir("plugins_runtime")
        if path.endswith(".aoi"):

            with zipfile.ZipFile(path) as zf:
                try:
                    if not json.load(zf.open("info.json", "r"))["type"] == "plugin":
                        return
                    information = json.load(zf.open("plugin_info.json", "r"))

                    zf.extractall(f"plugins_runtime/{information["name"]}")

                except Exception as e:
                    print(f"ERROR: 插件加载失败{path}: {e}")
                    return
            # 这里调用引擎资源管理器封装好的加载模块方法
            plugin_main = self.engine.resource_manager.load_model(
                f"plugins_runtime/{information['name']}/plugin",
                f"plugin_{information['name']}"
            ).Plugin(
                self.plugin_api,self.engine,information["name"]
            )
            self.plugins.append(PluginObject(plugin_main,information))
            print(f"插件{information['name']}加载成功")

    def start(self):
        for plugin in self.plugins:
            plugin.start()

    def update(self):
        for plugin in self.plugins:
            plugin.update()

    def end(self):
        for plugin in self.plugins:
            plugin.plugin.end()


class PluginObject:
    def __init__(self,plugin_object,plugin_info):
        self.plugin = plugin_object
        self.plugin_info = plugin_info
        self.plugin.on_game_load()

    def start(self):
        self.plugin.on_game_start()

    def update(self):
        self.plugin.on_game_update()

    def end(self):
        self.plugin.on_game_end()