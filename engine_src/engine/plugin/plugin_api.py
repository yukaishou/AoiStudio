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

    def import_model(self,plugin_name,path,name):
        """
        导入模型
        :param path: 模型路径
        :return: 模型
        """
        path = f"plugins_runtime/{plugin_name}/{path}".replace(".py","")
        return self.resource_manager.load_model(path,name)