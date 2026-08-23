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

class ScriptBase(ComponentBase):
    def __init__(self, game_object, properties: dict, engine):
        super().__init__(game_object, properties, engine)
        self.is_script = True
        self.update_order = 100

    def start(self):
        pass

    def update(self, dt: float):
        pass

