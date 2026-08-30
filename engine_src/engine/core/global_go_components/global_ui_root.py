import time
from engine_src.engine.utils import smooth_tween

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

class GlobalUIRoot(ComponentBase):
    def __init__(self, game_object, properties: dict, engine):
        super().__init__(game_object, properties, engine)
        self.is_script = True
        self.update_order = 100
        
        # UI切换动画相关
        self.transition_active = False
        self.transition_start_time = 0
        self.transition_duration = 0.3
        self.transition_type = "fade"
        self.transition_alpha = 255
        self.target_ui = None  # 要切换到的目标UI

# UI事件回调
    def _start_transition(self, target_ui, anim_type="fade", duration=0.3):
        """开始UI切换过渡"""
        self.transition_active = True
        self.transition_start_time = time.perf_counter()
        self.transition_duration = duration
        self.transition_type = anim_type
        self.transition_alpha = 255
        self.target_ui = target_ui
    
    def _apply_transition_effect(self, ui_element):
        """将过渡效果应用到UI元素"""
        if not self.transition_active or not ui_element:
            return
        
        now = time.perf_counter()
        elapsed = now - self.transition_start_time
        t = min(elapsed / self.transition_duration, 1.0)
        smooth_t = smooth_tween.ease_out_cubic(t)
        
        if self.transition_type == "fade":
            # 淡出效果: alpha从255降到0
            current_alpha = int(255 * (1 - smooth_t))
            if hasattr(ui_element, 'animation'):
                ui_element.animation.current_alpha = current_alpha
        elif self.transition_type == "slide_up":
            # 向上滑出
            offset_y = self.engine.game_size[1] * smooth_t
            if hasattr(ui_element, 'raw_y'):
                ui_element.set_position(ui_element.raw_x, ui_element.raw_y - offset_y)
    
    def _complete_transition(self):
        """完成过渡并切换到目标UI"""
        if self.target_ui:
            self.engine.ugc_ui_manager.set_root(self.target_ui)
            # 重置目标UI的动画状态
            if hasattr(self.target_ui, 'animation'):
                self.target_ui.animation.current_alpha = 255
        
        self.transition_active = False
        self.transition_alpha = 255
        self.target_ui = None

    def on_quit_game(self):
        self.engine.quit()

    def on_start_new_game(self):
        self._start_transition(None, "fade", 0.3)
        self.engine.start_dialog_game()

    def on_open_settings(self):
        self._start_transition(self.engine.settings, "fade", 0.3)

    def on_back_main_menu(self):
        self._start_transition(self.engine.main_menu_ui, "fade", 0.3)

    def on_load_game(self):
        self._start_transition(self.engine.save_game_ui, "fade", 0.3)

    def on_close_save_load(self):
        self._start_transition(self.engine.main_menu_ui, "fade", 0.3)

    def on_load_selected_save(self):
        self._start_transition(None, "fade", 0.3)
        self.engine.start_dialog_game(True, self.engine.save_game_system.get_solt_path(self.engine.save_game_ui_selected_solt))

    def on_slot_click_0(self):
        self.engine.save_game_ui_selected_solt = 0

    def on_slot_click_1(self):
        self.engine.save_game_ui_selected_solt = 1

    def on_slot_click_2(self):
        self.engine.save_game_ui_selected_solt = 2

    def on_slot_click_3(self):
        self.engine.save_game_ui_selected_solt = 3

    def on_slot_click_4(self):
        self.engine.save_game_ui_selected_solt = 4

    def on_slot_click_5(self):
        self.engine.save_game_ui_selected_solt = 5

    def update(self, dt: float):
        """更新过渡动画"""
        if self.transition_active:
            now = time.perf_counter()
            elapsed = now - self.transition_start_time
            
            if elapsed >= self.transition_duration:
                # 过渡完成,切换UI
                self._complete_transition()
            else:
                # 应用过渡效果到当前UI
                current_ui = self.engine.ugc_ui_manager.root
                if current_ui:
                    self._apply_transition_effect(current_ui)
