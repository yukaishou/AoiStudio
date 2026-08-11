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
            self.plugins.append(PluginObject(plugin_main,information,self))
            print(f"插件{information['name']}加载成功")

    def start(self):
        # 专门不写try的，因为插件启动失败应该让引擎也跟着一起罢工，所以这个失败了直接走fatal报错
        for plugin in self.plugins:
            plugin.start()

    def update(self):
        # 这个得写try，谁也不想玩家玩着玩着崩了
        name = ""
        plugin = None
        try:
            for plugin in self.plugins:
                name = plugin.plugin_info['name']
                plugin.update()
        except Exception as e:
            print(f"ERROR: 插件{name}更新时出错: {e}")
            plugin.plugin.on_game_end()
            self.plugins.remove(plugin)
            print(f"插件{name}已卸载")


    def end(self):
        # 专门不写try的，因为插件end罢工应该让引擎也跟着一起罢工，所以这个失败了直接走fatal报错
        for plugin in self.plugins:
            plugin.plugin.end()


class PluginObject:
    def __init__(self,plugin_object,plugin_info,plugin_manager):
        self.plugin = plugin_object
        self.plugin_info = plugin_info
        self.plugin_manager = plugin_manager
        self.plugin.on_game_load()

    def start(self):
        for i in self.plugin_manager.plugins:
            self.rely_ons = self.plugin_info["rely_ons"]
            if i in self.plugin_manager.plugins:
                if i.plugin_info["name"] in self.rely_ons:
                    self.rely_ons.remove(i.plugin_info["name"])
        if len(self.rely_ons) == 0:
            self.plugin.on_game_start()
        else:
            self.plugin_manager.plugins.remove(self)
            print(f"插件{self.plugin_info['name']}的依赖插件：{self.rely_ons}未安装，因此无法启动并卸载")


    def update(self):
            self.plugin.on_game_update()

    def end(self):
        self.plugin.on_game_end()

    def on_unload(self):
        self.plugin.on_game_unload()