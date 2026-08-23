from engine_src.engine.g_o.component_base import ComponentBase
from engine_src.engine.core.image import Image


class SpriteRenderer(ComponentBase):
    def __init__(self, game_object, properties, engine):
        super().__init__(game_object, properties, engine)
        self.image_path = properties.get("image_path", "")
        self.alpha = float(properties.get("alpha", 255))
        self.size_mode = properties.get("size_mode", "auto")
        self.image_center = bool(properties.get("image_center", True))

        self.original_img = None
        self.image_wrapper: Image | None = None

    def start(self):
        """GameObject 创建后执行一次"""
        if not self.image_path:
            return
        # 加载原始surface
        self.original_img = self.engine.resource_manager.load_image(self.image_path)
        if self.original_img is None:
            return
        go = self.game_object
        self.image_wrapper = Image(
            img=self.original_img,
            pos=[go.transform["position"][0], go.transform["position"][1]],
            scale=[go.transform["scale"][0], go.transform["scale"][1]],
            size_mode=self.size_mode,
            image_center=True,
            center=self.engine.get_center(),
        )
        self.image_wrapper.set_alpha(self.alpha)

    def update(self,dt):
        """每帧同步 GameObject 坐标、缩放、透明度到 Image"""
        if self.image_wrapper is None:
            return
        go = self.game_object
        # 同步位置
        self.image_wrapper.set_pos([go.transform["position"][0], go.transform["position"][1]])
        # 同步缩放
        self.image_wrapper.set_scale([go.transform["scale"][0], go.transform["scale"][1]])
        # 同步透明度
        self.image_wrapper.set_alpha(self.alpha)

    def draw(self, surface):
        """渲染调用，传入pygame.Surface"""
        if self.image_wrapper is None or not self.game_object.active:
            return
        self.image_wrapper.draw(surface)

    def set_image_path(self, path: str):
        """更换贴图路径"""
        self.image_path = path
        new_surf = self.engine.resource_manager.load_image(path)
        if new_surf and self.image_wrapper:
            self.original_img = new_surf
            self.image_wrapper.set_image(img=new_surf)

    def set_alpha(self, value: float):
        self.alpha = max(0.0, min(255.0, value))
        if self.image_wrapper:
            self.image_wrapper.set_alpha(self.alpha)

    def get_image_wrapper(self) -> Image | None:
        return self.image_wrapper

    def destroy(self):
        """组件销毁，仅解绑，资源交给resource_manager管理"""
        self.image_wrapper = None
        self.original_img = None