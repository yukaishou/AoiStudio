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

# UI事件回调
    def on_quit_game(self):
        self.engine.quit()

    def on_start_new_game(self):
        self.engine.start_dialog_game()

    def on_open_settings(self):
        self.engine.ugc_ui_manager.set_root(self.engine.settings)

    def on_back_main_menu(self):
        self.engine.ugc_ui_manager.set_root(self.engine.main_menu_ui)

    def on_load_game(self):
        self.engine.ugc_ui_manager.set_root(self.engine.save_game_ui)

    def on_close_save_load(self):
        self.engine.ugc_ui_manager.set_root(self.engine.main_menu_ui)

    def on_load_selected_save(self):
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

