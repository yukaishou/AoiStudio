from engine_src.engine.core import log

class GameObjectBase:
    def __init__(self, name, transform, engine, parent=None):
        self.active = True
        self.parent = parent
        self.engine = engine
        self.name = name
        """
        Transform 示例
        {
           "position":[0,0],
           "rotation":0,
           "scale":[1,1]
        }
        """
        self.transform = transform

        # 组件包装数组：[{name, active, object:组件实例}]
        self.components = []
        self._started = False   # 控制 start 只执行一次

    def start(self):
        """物体生命周期：只执行一次，GO创建后第一帧调用"""
        if not self.active or self._started:
            return
        self._started = True
        self.engine.event.emit("game_object_start", {"name": self.name})

        for comp_data in self.components:
            try:
                if comp_data["active"]:
                    comp_data["object"].start()
            except Exception as e:
                log.log(2, f"Error in starting component[{comp_data['name']}]: {str(e)}")
                self.set_component_active(comp_data["name"], False)

    def update(self, dt: float):
        """每帧更新，接收dt帧间隔"""
        if not self.active:
            return

        # 第一次update时触发start生命周期
        if not self._started:
            self.start()

        self.engine.event.emit("game_object_update", {"name": self.name})

        # 按组件 update_order 排序
        comp_list = list(self.components)
        comp_list.sort(key=lambda d: d["object"].update_order)

        for comp_data in comp_list:
            try:
                if comp_data["active"]:
                    comp_data["object"].update(dt)
            except Exception as e:
                log.log(2, f"Error in updating component[{comp_data['name']}]: {str(e)}")
                self.set_component_active(comp_data["name"], False)

    def render(self, surface):
        """渲染，调用组件的 draw(surface)"""
        if not self.active:
            return
        self.engine.event.emit("game_object_render", {"name": self.name})

        for comp_data in self.components:
            try:
                if comp_data["active"]:
                    # 统一调用组件.draw(surface)，不是render
                    comp_data["object"].draw(surface)
            except Exception as e:
                log.log(2, f"Error in rendering component[{comp_data['name']}]: {str(e)}")
                self.set_component_active(comp_data["name"], False)

    def add_component(self, component,is_edit=False,is_script_component=False):
        """添加组件，包装成dict存入，组件实例必须拥有 .name 属性"""
        active = True
        if is_edit and is_script_component:
            active = False
        comp_data = {
            "name": component.name,
            "active": active,
            "object": component
        }
        self.components.append(comp_data)

    def remove_component(self, component):
        """移除组件，执行destroy生命周期"""
        for comp_data in list(self.components):
            if comp_data["object"] == component:
                log.log(2, "Component removed: " + comp_data["name"])
                comp_data["object"].destroy()
                self.components.remove(comp_data)
                break

    def set_component_active(self, component_name, active):
        """设置单个组件启用/禁用"""
        for comp_data in self.components:
            if comp_data["name"] == component_name:
                comp_data["active"] = active
                break

    def get_component(self, comp_name: str):
        """根据组件名字获取组件实例"""
        for comp_data in self.components:
            if comp_data["name"] == comp_name:
                return comp_data["object"]
        return None

    def destroy(self):
        """销毁GameObject，销毁全部组件"""
        for comp_data in list(self.components):
            try:
                comp_data["object"].destroy()
            except Exception as e:
                log.log(2, f"Component destroy error: {str(e)}")
        self.components.clear()
        self.active = False

    def set_position(self, position):
        """设置GameObject位置"""
        self.transform["position"] = position

    def set_rotation(self, rotation):
        """设置GameObject旋转"""
        self.transform["rotation"] = rotation

    def set_scale(self, scale):
        """设置GameObject缩放"""
        self.transform["scale"] = scale

    def get_position(self):
        """获取GameObject位置"""
        return self.transform["position"]

    def get_rotation(self):
        """获取GameObject旋转"""
        return self.transform["rotation"]

    def get_scale(self):
        """获取GameObject缩放"""
        return self.transform["scale"]