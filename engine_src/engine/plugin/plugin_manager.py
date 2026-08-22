import os
import zipfile
from importlib import util

from engine_src.engine.plugin.plugin_api import PluginAPI
import json
from engine_src.engine.core import log


class PluginManager:
    def __init__(self, engine):
        self.plugins = []
        self.engine = engine
        self.plugin_api = PluginAPI(self.engine)

    def load_plugin(self, path):
        self.engine.event.emit("plugin_load", {"plugin_path": path})
        if not os.path.exists("plugins_runtime"):
            os.mkdir("plugins_runtime")
        if path.endswith(".aoi"):
            try:
                with zipfile.ZipFile(path) as zf:
                    info_raw = zf.read("info.json")
                    info = json.loads(info_raw)
                    if info.get("type") != "plugin":
                        log.log(2, f"[PLUGIN] {path} 不是合法插件包")
                        return

                    plugin_info_raw = zf.read("plugin_info.json")
                    information = json.loads(plugin_info_raw)

                    zf.extractall(f"plugins_runtime/{information['name']}")
            except Exception as e:
                log.log(2, f"[PLUGIN] 插件加载失败 {path}: {e}")
                return

            plugin_main = self.engine.resource_manager.load_model(
                f"plugins_runtime/{information['name']}/plugin",
                f"plugin_{information['name']}"
            ).Plugin(self.plugin_api, self.engine, information["name"])

            self.plugins.append(PluginObject(plugin_main, information, self))
            log.log(0, f"[PLUGIN] 插件{information['name']}加载成功")

    def start(self):
        # 专门不写try的，因为插件启动失败应该让引擎也跟着一起罢工，所以这个失败了直接走fatal报错
        for plugin in self.plugins:
            plugin.start()

    def update(self):
        for plugin in self.plugins[:]:  # 切片拷贝，防止遍历过程列表修改出错
            name = plugin.plugin_info['name']
            try:
                plugin.update()
            except Exception as e:
                log.log(2, f"[PLUGIN] 插件{name}更新时出错: {e}")
                try:
                    plugin.plugin.on_game_end()
                except:
                    pass
                if plugin in self.plugins:
                    self.plugins.remove(plugin)
                log.log(0, f"[PLUGIN] 插件{name}已卸载")
    def end(self):
        # 专门不写try的，因为插件end罢工应该让引擎也跟着一起罢工，所以这个失败了直接走fatal报错
        for plugin in self.plugins:
            plugin.plugin.end()


class PluginObject:
    def __init__(self, plugin_object, plugin_info, plugin_manager):
        self.plugin = plugin_object
        self.plugin_info = plugin_info
        self.plugin_manager = plugin_manager
        self.plugin.on_game_load()

    def start(self):
        # 复制依赖列表，不修改原始plugin_info
        need_deps = self.plugin_info.get("rely_ons", []).copy()
        installed_names = [p.plugin_info["name"] for p in self.plugin_manager.plugins]

        missing = [dep for dep in need_deps if dep not in installed_names]
        if len(missing) == 0:
            self.plugin.on_game_start()
        else:
            # 标记为不可启动，不要在这里直接remove，交给上层处理
            log.log(2, f"[PLUGIN] 插件{self.plugin_info['name']}缺失依赖：{missing}，跳过启动")
            raise RuntimeError(f"Missing plugin dependency: {missing}")

    def update(self):
        self.plugin.on_game_update()

    def end(self):
        self.plugin.on_game_end()

    def on_unload(self):
        self.plugin.on_game_unload()