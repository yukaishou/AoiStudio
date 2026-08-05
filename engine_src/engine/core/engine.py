import pygame
import json
import sys
from engine_src.engine.resource import resource
from engine_src.engine.core import scene_manager
from engine_src.engine.core import image
from engine_src.engine.ui import dialog_table
from engine_src.engine.ui import dialog_choice
from engine_src.engine.core import dialogue
from engine_src.engine.core import cfg_decoder
from engine_src.engine.utils import dpi_tool
from engine_src.engine.core import save_game
from engine_src.engine.ui import dialog_backtext
from engine_src.engine.ugc_ui import ui_manager
from engine_src.engine.ugc_ui import ui_loader

class Engine:
    def __init__(self,game_title,game_size):
        """
        ????
        初始化游戏窗口??????
        :param game_title:
        :param game_size:
        """
        self.id_index_map = json.load(open("config/dialog_index.json"))
        self.main_menu_config = json.load(open("config/main_menu.json"))
        self.center = [game_size[0] // 2, game_size[1] // 2]
        self.screen_size = pygame.display.list_modes()[0]
        self.fullscreen_center = [self.screen_size[0] // 2, self.screen_size[1] // 2]
        self.game_name = game_title
        self.game_size = game_size
        self.screen = pygame.display.set_mode(game_size,pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.SCALED)
        pygame.display.set_caption(game_title)
        pygame.display.set_icon(pygame.image.load("icons/AppIcon.png"))
        self.running = True
        self.in_dialog_game = False
        self.fps = 60
        self.clock = pygame.time.Clock()
        self.clock.tick(self.fps)
        self.is_full_screen = False

        # 初始化模块
        self.dpi = dpi_tool.DPITool(self.game_size, pygame.display.list_modes()[0])
        self.save_game = save_game.SaveGame(self)
        self.resource_manager = resource.AssetManager(self)
        self.scene = scene_manager.Scene(self)
        self.dialog = dialogue.Dialogue(self)
        self.cfg_decoder = cfg_decoder.CFGDecoder(self)
        # 初始化 UI
        self.ugc_ui_manager = ui_manager.UIManager(self.game_size)
        self.dialog_table = dialog_table.GalDialogBox(self.screen,40,game_size[1]-180,game_size[0]-80,160,self.dialog)
        self.dialog_choice = dialog_choice.GalChoiceUI(self.screen)
        self.dialog_choice.set_panel_pos(game_size[0]*0.5-200,game_size[1]*0.5-100)
        self.dialog_backlog = dialog_backtext.BacklogViewer()
        self.dialog_backlog.set_backlog_panel_center(self.center[0],self.center[1])
        ui_loader_ = ui_loader.UILoader(self, self)
        self.main_menu_ui = ui_loader_.load_from_file(self.main_menu_config["main_menu_ui_path"][5:])
        self.save_game_ui = ui_loader_.load_from_file(self.main_menu_config["save_game_ui_path"][5:])
        self.settings = ui_loader_.load_from_file(self.main_menu_config["settings_ui_path"][5:])
        self.main_menu_bgm = self.resource_manager.load_sound(self.main_menu_config["bgm"][5:])
        self.main_menu_background = image.Image(self.resource_manager.load_image(self.main_menu_config["background"][5:]),None,[0,0],[1,1],"fill",self.center,True)
        self.ugc_ui_manager.set_root(self.main_menu_ui)
        if self.in_dialog_game:
            self.start_dialog_game()
        
    def run(self):
        #self.fullscreen()
        self.fps_font = pygame.font.Font("fonts/default.ttf", 24)
        if not self.in_dialog_game:
            self.main_menu_bgm.play(loops=-1)
        # 游戏主循环
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit(0)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    # 处理鼠标点击事件
                    if self.in_dialog_game:
                        self.dialog_choice.handle_click()
                        pos = pygame.mouse.get_pos()
                        # logical_x = pos[0] * (self.game_size[0] / self.screen.get_width())
                        # logical_y = pos[1] * (self.game_size[1] / self.screen.get_height())
                        # pos = (logical_x, logical_y)
                        if self.dialog_table.rect.collidepoint(pos):
                            has_next = self.dialog_table.handle_click()
                            if has_next:
                                self.dialog.on_text_complete()
                                self.dialog.on_next()

                if event.type == pygame.KEYDOWN:
                    # 全屏
                    if event.key == pygame.K_F11:
                        self.fullscreen()

                    # 测试用，保存游戏,读取游戏
                    if event.key == pygame.K_s:
                        self.save_game.save_game_ui("test_save_game.save")
                    if event.key == pygame.K_l:
                        if not self.in_dialog_game:
                            self.in_dialog_game  = True
                            self.ugc_ui_manager.clear_ui()
                        self.save_game.load_game("test_save_game.save")
                    if event.key == pygame.K_b:
                        if self.in_dialog_game:
                            self.dialog_backlog.active = not self.dialog_backlog.active
                self.dialog_backlog.handle_event(event)
                self.ugc_ui_manager.handle_event(event)

            pygame.display.update()
            delta_time = self.clock.tick(self.fps) / 1000.0
            self.screen.fill((0,0,0))
            self.scene.update()
            if not self.in_dialog_game:
                self.main_menu_background.draw(self.screen)
            self.scene.draw(self.screen)
            self.cfg_decoder.update_wait()
            self.dialog_table.update(delta_time)
            self.dialog_choice.update()
            self.ugc_ui_manager.draw(self.screen)
            if self.in_dialog_game:
                self.dialog_table.render()
                self.dialog_choice.render()
                self.dialog_backlog.draw(self.screen)
            #文字为黄色
            self.screen.blit(self.fps_font.render("FPS: " + str(int(self.clock.get_fps())), True, (200, 200, 0)), (10, 10))


    def start_dialog_game(self,is_go_from_save_game=False,save_path=""):
        self.main_menu_bgm.stop()
        if not is_go_from_save_game:
            self.in_dialog_game = True
            self.ugc_ui_manager.clear_ui()
            first_start_dialog_config = json.load(open("config/dialog.json","r",encoding="utf-8"))
            if first_start_dialog_config["startFrom"].startswith("file:"):
                start_from_path = first_start_dialog_config["startFrom"][5:]
                self.dialog.load_dialogue(start_from_path)
            if first_start_dialog_config["startBG"].startswith("file:"):
                start_bg = first_start_dialog_config["startBG"][5:]
                self.scene.add_background(start_bg)
            self.dialog.start_dialogue()
        else:
            self.save_game_ui.load_game(save_path)

    def fullscreen(self):
        if pygame.display.is_fullscreen():
            self.unfullscreen()
            return
        #self.screen = pygame.display.set_mode(pygame.display.list_modes()[0],pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.SCALED)
        pygame.display.toggle_fullscreen()
        # 由于用了pygame-ce，这些东西就他哥的不用了
        # 以下代码是用神秘原版pygame实现，现在不需要了

        #self.screen = pygame.display.set_mode(pygame.display.list_modes()[0],pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.SCALED)
        #self.scene.change_scene_center(self.fullscreen_center)
        #self.dialog_table.set_position(self.dpi.to_real(self.dialog_table.get_position()[0],0)[0],self.dpi.to_real(0,self.dialog_table.get_position()[1])[1])
        #self.dialog_table.set_size(self.dpi.to_real(self.dialog_table.get_size()[0],0)[0],self.dpi.to_real(0,self.dialog_table.get_size()[1])[1])
        #self.dialog_choice.set_panel_pos(self.dpi.to_real(self.dialog_choice.get_panel_pos()[0],0)[0],self.dpi.to_real(0,self.dialog_choice.get_panel_pos()[1])[1])
        #self.dialog_choice.set_panel_size(self.dpi.to_real(self.dialog_choice.get_panel_size()[0],self.dialog_choice.get_panel_pos()[1])[0],self.dialog_choice.get_panel_size()[1])
    def unfullscreen(self):
        #self.screen = pygame.display.set_mode(self.game_size,pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.SCALED)
        pygame.display.toggle_fullscreen()

    def quit(self):
        self.running = False

    def get_center(self):
        if self.is_full_screen:
            return self.fullscreen_center
        else:
            return self.center

    def get_screen_size(self):
        if self.is_full_screen:
            return pygame.display.list_modes()[0]
        else:
            return self.game_size

    def on_quit_game(self):
        self.quit()

    def on_start_new_game(self):
        self.start_dialog_game()

    def on_open_settings(self):
        self.ugc_ui_manager.set_root(self.settings)

    def on_back_main_menu(self):
        self.ugc_ui_manager.set_root(self.main_menu_ui)


