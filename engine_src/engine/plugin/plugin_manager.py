import os
import zipfile
import json
from engine_src.engine.plugin.plugin_api import PluginAPI
from engine_src.engine.core import log


class PluginManager:
    def __init__(self, engine):
        self.plugins = []
        self.engine = engine
        self.plugin_api = PluginAPI(self.engine)

    def _safe_extract_zip(self, zf: zipfile.ZipFile, target_dir: str):
        """防zip路径穿越解压"""
        for member in zf.infolist():
            member_path = os.path.normpath(os.path.join(target_dir, member.filename))
            if not member_path.startswith(os.path.normpath(target_dir)):
                raise RuntimeError(f"Zip路径非法逃逸: {member.filename}")
        zf.extractall(target_dir)

    def load_plugin(self, path):
        self.engine.event.emit("plugin_load", {"plugin_path": path})
        runtime_root = "plugins_runtime"
        if not os.path.exists(runtime_root):
            os.mkdir(runtime_root)

        if not path.endswith(".aoi"):
            return

        try:
            with zipfile.ZipFile(path) as zf:
                info_raw = zf.read("info.json")
                info = json.loads(info_raw)
                if info.get("type") != "plugin":
                    log.log(2, f"[PLUGIN] {path} 不是合法插件包")
                    return

                plugin_info_raw = zf.read("plugin_info.json")
                information = json.loads(plugin_info_raw)
                plugin_name = information["name"]

                # 预留：最低引擎版本校验
                require_version = information.get("require_engine_version", None)
                if require_version is not None:
                    # 可在这里做版本对比逻辑
                    pass

                target_extract = os.path.join(runtime_root, plugin_name)
                self._safe_extract_zip(zf, target_extract)

        except Exception as e:
            log.log(2, f"[PLUGIN] 插件包读取/解压失败 {path}: {e}")
            return

        try:
            mod = self.engine.resource_manager.load_model(
                f"plugins_runtime/{plugin_name}/plugin",
                f"plugin_{plugin_name}"
            )
            plugin_main_inst = mod.Plugin(self.plugin_api, self.engine, plugin_name)
        except Exception as e:
            log.log(2, f"[PLUGIN] 插件主类实例化失败 {plugin_name}: {e}")
            return

        plugin_obj = PluginObject(plugin_main_inst, information, self)
        self.plugins.append(plugin_obj)
        log.log(0, f"[PLUGIN] 插件{plugin_name}加载成功")

    def start(self):
        """逐个启动插件；单个插件失败仅禁用自身，不崩溃整个引擎"""
        for plugin in self.plugins:
            if not plugin.is_valid:
                continue
            try:
                plugin.start()
            except RuntimeError as e:
                log.log(2, f"[PLUGIN] 插件启动失败，已禁用：{e}")
                plugin.is_valid = False
            except Exception as e:
                log.log(2, f"[PLUGIN] 插件发生致命启动异常，禁用：{e}")
                plugin.is_valid = False

    def update(self):
        for plugin in self.plugins[:]:
            if not plugin.is_valid:
                continue
            name = plugin.plugin_info['name']
            try:
                plugin.update()
            except Exception as e:
                log.log(2, f"[PLUGIN] 插件{name}更新时出错: {e}")
                try:
                    plugin.plugin.on_game_end()
                except Exception:
                    pass
                if plugin in self.plugins:
                    self.plugins.remove(plugin)
                log.log(0, f"[PLUGIN] 插件{name}已因异常卸载")

    def end(self):
        """每个插件单独捕获异常，保证全部插件执行结束回调"""
        for plugin in self.plugins[:]:
            try:
                plugin.end()
            except Exception as e:
                log.log(2, f"[PLUGIN] 插件end回调异常 {plugin.plugin_info.get('name','?')}: {e}")
        self.plugins.clear()


class PluginObject:
    def __init__(self, plugin_object, plugin_info, plugin_manager):
        self.plugin = plugin_object
        self.plugin_info = plugin_info
        self.plugin_manager = plugin_manager
        self.is_valid = True

        try:
            self.plugin.on_game_load()
        except Exception as e:
            log.log(2, f"[PLUGIN] 插件on_game_load执行失败: {e}")
            self.is_valid = False

    def start(self):
        need_deps = self.plugin_info.get("rely_ons", []).copy()
        installed_names = [p.plugin_info["name"] for p in self.plugin_manager.plugins if p.is_valid]
        missing = [dep for dep in need_deps if dep not in installed_names]
        if missing:
            raise RuntimeError(f"缺失依赖插件: {missing}")
        self.plugin.on_game_start()

    def update(self):
        self.plugin.on_game_update()

    def end(self):
        self.plugin.on_game_end()

    def on_unload(self):
        self.plugin.on_game_unload()