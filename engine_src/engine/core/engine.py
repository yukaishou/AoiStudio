import os
import shutil

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
from engine_src.engine.plugin import plugin_manager

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
        # 游戏状态
        self.running = True
        self.in_dialog_game = False
        self.fps = 60
        self.clock = pygame.time.Clock()
        self.clock.tick(self.fps)
        self.is_full_screen = False
        self.is_looking_backtext = False
        self.save_game_ui_selected_solt = 0

        # 初始化模块
        self.dpi = dpi_tool.DPITool(self.game_size, pygame.display.list_modes()[0])
        self.save_game_system = save_game.SaveGame(self)
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
        try:
            self.main_menu_background = image.Image(self.resource_manager.load_image(self.main_menu_config["background"][5:]),None,[0,0],[1,1],"fill",self.center,True)
        except:
            print("加载背景图片失败")
        self.ugc_ui_manager.set_root(self.main_menu_ui)
        if self.in_dialog_game:
            self.start_dialog_game()

        # 插件系统初始化
        self.plugin_manager = plugin_manager.PluginManager(self)
        
    def run(self):
        #self.fullscreen()
        self.fps_font = pygame.font.Font("fonts/default.ttf", 24)
        if not self.in_dialog_game:
            try:
                self.main_menu_bgm.play(loops=-1)
            except:
                pass
        # 插件加载
        if os.path.exists("plugins"):
            for root,dirs,files in os.walk("plugins"):
                for file in files:
                    if file.endswith(".aoi"):
                        self.plugin_manager.load_plugin(os.path.join(root,file))
        self.plugin_manager.start()
        # 游戏主循环
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    # 处理鼠标点击事件
                    if self.in_dialog_game and not self.is_looking_backtext:
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
                            else:
                                self.dialog.on_text_complete()

                if event.type == pygame.KEYDOWN:
                    # 全屏
                    if event.key == pygame.K_F11:
                        self.fullscreen()

                    # 测试用，保存游戏,读取游戏
                    if event.key == pygame.K_s:
                        self.save_game_system.save_game("test_save_game.save")
                    if event.key == pygame.K_l:
                        if not self.in_dialog_game:
                            self.in_dialog_game  = True
                            self.ugc_ui_manager.clear_ui()
                        self.save_game_system.load_game("test_save_game.save")
                    if event.key == pygame.K_b:
                        if self.in_dialog_game:
                            self.is_looking_backtext = not self.is_looking_backtext
                            self.dialog_backlog.active = not self.dialog_backlog.active

                self.dialog_backlog.handle_event(event)
                self.ugc_ui_manager.handle_event(event)

            pygame.display.update()
            delta_time = self.clock.tick(self.fps) / 1000.0
            self.screen.fill((0,0,0))
            self.scene.update()
            if not self.in_dialog_game:
                try:
                    self.main_menu_background.draw(self.screen)
                except:
                    pass
            self.scene.draw(self.screen)
            self.cfg_decoder.update_wait()
            if not self.is_looking_backtext:
                self.dialog_table.update(delta_time)
                self.dialog_choice.update()
            self.ugc_ui_manager.draw(self.screen)
            if self.in_dialog_game:
                self.dialog_table.render()
                self.dialog_choice.render()
                self.dialog_backlog.draw(self.screen)
            self.plugin_manager.update()
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
            elif first_start_dialog_config["startFrom"].startswith("id:"):
                start_from_path = self.id_index_map[first_start_dialog_config["startFrom"][3:]]
                self.dialog.load_dialogue(start_from_path)
            if first_start_dialog_config["startBG"].startswith("file:"):
                start_bg = first_start_dialog_config["startBG"][5:]
                self.scene.add_background(start_bg)
            self.dialog.start_dialogue()
        else:
            self.save_game_system.load_game(save_path)

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

    # 以下为UI事件回调

    def on_quit_game(self):
        self.quit()

    def on_start_new_game(self):
        self.start_dialog_game()

    def on_open_settings(self):
        self.ugc_ui_manager.set_root(self.settings)

    def on_back_main_menu(self):
        self.ugc_ui_manager.set_root(self.main_menu_ui)

    def on_load_game(self):
        self.ugc_ui_manager.set_root(self.save_game_ui)

    def on_close_save_load(self):
        self.ugc_ui_manager.set_root(self.main_menu_ui)

    def on_load_selected_save(self):
        self.start_dialog_game(True, self.save_game_system.get_solt_path(self.save_game_ui_selected_solt))

    def on_slot_click_0(self):
        self.save_game_ui_selected_solt = 0

    def on_slot_click_1(self):
        self.save_game_ui_selected_solt = 1

    def on_slot_click_2(self):
        self.save_game_ui_selected_solt = 2

    def on_slot_click_3(self):
        self.save_game_ui_selected_solt = 3

    def on_slot_click_4(self):
        self.save_game_ui_selected_solt = 4

    def on_slot_click_5(self):
        self.save_game_ui_selected_solt = 5