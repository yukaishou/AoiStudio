import json
from .ui_components import UIButton, UIText, UIImage
from .ui_element import UIElement

class UILoader:
    def __init__(self, script_instance,engine):
        """
        初始化UI加载器
        :param script_instance: 调用此加载器的脚本实例，用于绑定事件回调
        """
        self.script = script_instance
        self.engine = engine
        self.script_instance = script_instance
        self.created_elements = {}  # 存储已创建的元素，方便后续引用

    def load_from_file(self, file_path):
        file_path = file_path
        """从JSON文件加载UI"""
        config = self.engine.resource_manager.load_json_file(file_path)
        return self._build_ui(config)

    def _build_ui(self, config):
        """根据配置构建UI"""
        root = UIElement(0, 0, self.engine.game_size[0], self.engine.game_size[1])
        if not config:
            return root
        for element_config in config.get("elements", []):
            element = self._create_element(element_config)
            #element.engine = self.engine
            if element:
                root.add_child(element)
                # 保存元素引用
                element_id = element_config.get("id")
                if element_id:
                    self.created_elements[element_id] = element
                    
                # 绑定事件
                self._bind_events(element, element_config.get("events", {}))
        return root

    def _create_element(self, config):
        """根据配置创建单个UI元素"""
        element_type = config["type"]
        props = config["properties"]
        
        try:
            if element_type == "UIButton":
                return UIButton(
                    text=props["text"],
                    x=props["x"],
                    y=props["y"],
                    width=props["width"],
                    height=props["height"],
                    callback=lambda: self._handle_callback(config.get("events", {}).get("on_click")),
                    font_path=props.get("font_path"),
                    engine = self.engine
                )
                
            elif element_type == "UIText":
                color = props.get("color", [255, 255, 255])
                return UIText(
                    text=props["text"],
                    x=props["x"],
                    y=props["y"],
                    size=props.get("size", 24),
                    color=(color[0], color[1], color[2]),
                    font_path=props.get("font_path"),
                    engine = self.engine
                )
                
            elif element_type == "UIImage":
                return UIImage(
                    image_path=props["image_path"],
                    x=props["x"],
                    y=props["y"],
                    width=props["width"],
                    height=props["height"],
                    size_mode=props["size_mode"],
                    engine = self.engine
                )
                
            else:
                print(f"未知的UI元素类型: {element_type}")
                return None
                
        except Exception as e:
            print(f"创建UI元素失败: {e}")
            return None

    def _bind_events(self, element, events):
        """绑定事件（目前只处理点击事件）"""
        # 事件绑定已在_create_element中通过lambda完成
        pass

    def _handle_callback(self, callback_name):
        """处理回调函数"""
        if callback_name and hasattr(self.script, callback_name):
            getattr(self.script, callback_name)()
        else:
            print(f"未找到回调函数: {callback_name}")