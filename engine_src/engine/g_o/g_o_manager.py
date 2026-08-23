from engine_src.engine.core import log
from engine_src.engine.g_o.game_object_base import GameObjectBase
from engine_src.engine.g_o.components import sprite_renderer

COMPONENTS_MAP = {
    "SpriteRenderer": sprite_renderer.SpriteRenderer,
}

class GOManager:
    def __init__(self,engine):
        self.engine = engine
        self.game_objects = []

    def create_game_object(self, name,transform,parent=None):
        self.engine.event.emit("game_object_created",{"name":name,"transform":transform,"parent":parent})
        log.log(0,"Game Object Created: "+name)
        new_game_object = GameObjectBase(name,transform,self.engine,parent=parent)
        self.game_objects.append(new_game_object)
        return new_game_object

    def create_component(self, go, comp_name: str, props: dict):
        cls = self.get_component_by_name(comp_name)
        if cls is None:
            log.warning(f"组件不存在:{comp_name}")
            return None
        inst = cls(go, props, self.engine)
        go.add_component(inst)
        return inst

    def get_game_object(self, name):
        for game_object in self.game_objects:
            if game_object.name == name:
                return game_object
        return None

    def remove_game_object(self, name):
        self.engine.event.emit("gamme_object_removed",{"name":name})
        for game_object in self.game_objects:
            if game_object.name == name:
                self.game_objects.remove(game_object)
                return True
            return False
        return False

    def update(self, dt: float):
        go_list = list(self.game_objects)
        for go in go_list:
            go.update(dt)

    def render(self,surface):
        for game_object in self.game_objects:
            game_object.render(surface)

    def set_active(self, name, active):
        self.engine.event.emit("gamme_object_active_changed",{"name":name,"active":active})
        game_object = self.get_game_object(name)
        if game_object:
            game_object.active = active
            return True
        return False

    def get_component_by_name(self,component_name):
        return COMPONENTS_MAP.get(component_name,None)