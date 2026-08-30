# engine_src/engine/g_o/component_base.py
class ComponentBase:
    def __init__(self, game_object, properties: dict, engine):
        self.game_object = game_object
        self.properties = properties
        self.engine = engine
        self.is_script = False
        self.update_order = 50
        self.name = self.__class__.__name__

    def start(self):
        pass

    def update(self, dt: float):
        pass

    def destroy(self):
        pass

    def draw(self, surface):
        pass

    def get_save_data(self):
        """获取组件的存档数据"""
        return self.properties.copy()

    def load_save_data(self, data: dict):
        """从存档数据加载组件状态"""
        self.properties.update(data)