import time
import os
from engine_src.engine.utils import smooth_tween
from engine_src.engine.core import log


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
        
        self.transition_active = False
        self.transition_start_time = 0
        self.transition_duration = 0.3
        self.transition_type = "fade"
        self.transition_alpha = 255
        self.target_ui = None
        self.save_load_mode = "load"

    def _start_transition(self, target_ui, anim_type="fade", duration=0.3):
        self.transition_active = True
        self.transition_start_time = time.perf_counter()
        self.transition_duration = duration
        self.transition_type = anim_type
        self.transition_alpha = 255
        self.target_ui = target_ui
    
    def _apply_transition_effect(self, ui_element):
        if not self.transition_active or not ui_element:
            return
        now = time.perf_counter()
        elapsed = now - self.transition_start_time
        t = min(elapsed / self.transition_duration, 1.0)
        smooth_t = smooth_tween.ease_out_cubic(t)
        if self.transition_type == "fade":
            current_alpha = int(255 * (1 - smooth_t))
            if hasattr(ui_element, 'animation'):
                ui_element.animation.current_alpha = current_alpha
        elif self.transition_type == "slide_up":
            offset_y = self.engine.game_size[1] * smooth_t
            if hasattr(ui_element, 'raw_y'):
                ui_element.set_position(ui_element.raw_x, ui_element.raw_y - offset_y)
    
    def _complete_transition(self):
        if self.target_ui:
            self.engine.ugc_ui_manager.set_root(self.target_ui)
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

    def on_open_save_in_game(self):
        """游戏中按S打开存档界面(保存模式)"""
        self.save_load_mode = "save"
        self._refresh_save_slot_info()
        self._show_save_load_ui()
        self._start_transition(self.engine.save_game_ui, "fade", 0.3)
        self.engine.save_game_ui_active = True

    def on_open_load_in_game(self):
        """游戏中按L打开读档界面"""
        self.save_load_mode = "load"
        self._refresh_save_slot_info()
        self._show_save_load_ui()
        self._start_transition(self.engine.save_game_ui, "fade", 0.3)
        self.engine.save_game_ui_active = True

    def _show_save_load_ui(self):
        """根据模式显示不同的按钮"""
        save_loader = getattr(self.engine, '_save_game_ui_loader', None)
        if not save_loader:
            return
        created = save_loader.created_elements
        
        if self.save_load_mode == "save":
            save_btn = created.get("btn_save")
            load_btn = created.get("btn_load")
            title = created.get("title_text")
            if save_btn: save_btn.is_visible = True
            if load_btn: load_btn.is_visible = False
            if title:
                title.full_text = "保存存档"
                title.displayed_text = title.full_text
        else:
            save_btn = created.get("btn_save")
            load_btn = created.get("btn_load")
            title = created.get("title_text")
            if save_btn: save_btn.is_visible = False
            if load_btn: load_btn.is_visible = True
            if title:
                title.full_text = "读取存档"
                title.displayed_text = title.full_text

    def on_back_main_menu(self):
        self._start_transition(self.engine.main_menu_ui, "fade", 0.3)

    def on_load_game(self):
        self.save_load_mode = "load"
        self._refresh_save_slot_info()
        self._show_save_load_ui()
        self._start_transition(self.engine.save_game_ui, "fade", 0.3)
        self.engine.save_game_ui_active = True

    def on_close_save_load(self):
        self.engine.save_game_ui_active = False
        if self.engine.in_dialog_game:
            self.engine.save_game_ui_selected_slot = -1
            self.engine.ugc_ui_manager.clear_ui()
        else:
            self._start_transition(self.engine.main_menu_ui, "fade", 0.3)

    def on_load_selected_save(self):
        """根据模式执行读档或存档"""
        slot = self.engine.save_game_ui_selected_slot
        if slot < 0:
            log.log(1, "[SAVE] 请先选择一个存档槽位")
            return
        if self.save_load_mode == "load":
            self.engine.save_game_ui_active = False
            self._start_transition(None, "fade", 0.3)
            self.engine.start_dialog_game(True, self.engine.save_game_system.get_slot_path(slot))
        else:
            self.engine.save_game_system.save_slot(slot)
            log.log(0, f"[SAVE] 已存档到槽位 {slot}")
            self.engine.save_game_ui_selected_slot = -1
            self.engine.save_game_ui_active = False
            self.engine.ugc_ui_manager.clear_ui()

    def on_save_and_return(self):
        slot = self.engine.save_game_ui_selected_slot
        if slot < 0:
            log.log(1, "[SAVE] 请先选择一个存档槽位")
            return
        self.engine.save_game_system.save_slot(slot)
        log.log(0, f"[SAVE] 已存档到槽位 {slot}")
        self.engine.save_game_ui_selected_slot = -1
        self.engine.save_game_ui_active = False
        self.engine.ugc_ui_manager.clear_ui()

    def on_slot_click_0(self):
        self.engine.save_game_ui_selected_slot = 0
        self._highlight_slot(0)

    def on_slot_click_1(self):
        self.engine.save_game_ui_selected_slot = 1
        self._highlight_slot(1)

    def on_slot_click_2(self):
        self.engine.save_game_ui_selected_slot = 2
        self._highlight_slot(2)

    def on_slot_click_3(self):
        self.engine.save_game_ui_selected_slot = 3
        self._highlight_slot(3)

    def on_slot_click_4(self):
        self.engine.save_game_ui_selected_slot = 4
        self._highlight_slot(4)

    def on_slot_click_5(self):
        self.engine.save_game_ui_selected_slot = 5
        self._highlight_slot(5)

    def _highlight_slot(self, clicked_index):
        save_loader = getattr(self.engine, '_save_game_ui_loader', None)
        if not save_loader:
            return
        created = save_loader.created_elements
        for i in range(6):
            bg_el = created.get(f"slot_bg_{i}")
            title_el = created.get(f"slot{i}_title")
            if bg_el:
                if i == clicked_index:
                    bg_el.color = (60, 70, 100)
                    bg_el.current_color = [60, 70, 100]
                else:
                    bg_el.color = (45, 48, 60)
                    bg_el.current_color = [45, 48, 60]
            if title_el:
                if i == clicked_index:
                    title_el.color = (255, 220, 100)
                else:
                    title_el.color = (240, 240, 240)
                title_el.update_rect()

    def _find_element_by_id(self, element, target_id):
        if hasattr(element, 'id') and element.id == target_id:
            return element
        if hasattr(element, 'children'):
            for child in element.children:
                result = self._find_element_by_id(child, target_id)
                if result:
                    return result
        return None

    def _refresh_save_slot_info(self):
        save_loader = getattr(self.engine, '_save_game_ui_loader', None)
        if not save_loader:
            return
        created = save_loader.created_elements
        save_sys = self.engine.save_game_system
        for i in range(6):
            info = save_sys.get_slot_info(i)
            title_el = created.get(f"slot{i}_title")
            char_el = created.get(f"slot{i}_char")
            time_el = created.get(f"slot{i}_time")
            if title_el:
                title_el.full_text = f"存档 {i+1:02d}"
                title_el.displayed_text = title_el.full_text
                title_el.update_rect()
            if char_el:
                if info["has_save"]:
                    char_text = info["character"] if info["character"] else "--无角色--"
                    char_el.full_text = char_text
                    char_el.color = (160, 160, 200)
                else:
                    char_el.full_text = "--空存档--"
                    char_el.color = (100, 100, 100)
                char_el.displayed_text = char_el.full_text
                char_el.update_rect()
            if time_el:
                if info["has_save"]:
                    time_el.full_text = info["time"]
                    time_el.color = (130, 130, 160)
                else:
                    time_el.full_text = ""
                    time_el.color = (100, 100, 100)
                time_el.displayed_text = time_el.full_text
                time_el.update_rect()

    def update(self, dt: float):
        if self.transition_active:
            now = time.perf_counter()
            elapsed = now - self.transition_start_time
            if elapsed >= self.transition_duration:
                self._complete_transition()
            else:
                current_ui = self.engine.ugc_ui_manager.root
                if current_ui:
                    self._apply_transition_effect(current_ui)
