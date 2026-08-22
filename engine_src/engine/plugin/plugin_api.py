import os


class PluginAPI:
    """
    插件API
    """
    def __init__(self,engine):
        self.engine = engine
        self.resource_manager = engine.resource_manager
        self.dialogue_manager = engine.dialog
        self.ugc_ui_manager = engine.ugc_ui_manager
        self.dialog_choice_table = engine.dialog_choice
        self.dialog_table = engine.dialog_table
        self.dialog_backlog = engine.dialog_backlog

    def import_model(self,plugin_name,path,name):
        """
        导入模型
        :param path: 模型路径
        :return: 模型
        """
        path = f"plugins_runtime/{plugin_name}/{path}".replace(".py","")
        return self.resource_manager.load_model(path,name)

    def call(self, plugin_name, function_name, *args, **kwargs):
        """
        调用其他插件的函数
        """
        print(f"[PluginAPI] Call {plugin_name} function {function_name}")
        try:
            for wrapper in self.engine.plugin_manager.plugins:
                if wrapper.plugin_info["name"] == plugin_name:
                    plugin = wrapper.plugin
                    if not hasattr(plugin, function_name):
                        print(f"[PluginAPI] 插件 '{plugin_name}' 没有函数 '{function_name}'")
                        return None
                    func = getattr(plugin, function_name)
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        print(f"[PluginAPI] 被调用插件内部异常 {plugin_name}.{function_name}: {e}")
                        return None
            print(f"[PluginAPI] 未找到插件 '{plugin_name}'")
            return None
        except Exception as e:
            print(f"[PluginAPI] 调用错误: {plugin_name}.{function_name} - {e}")
            return None

    def register_cfg_command(self, command_name, command_func):
        """
        注册cfg命令
        """
        self.engine.cfg_decoder.register_command( command_name, command_func)