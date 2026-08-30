import os
import threading
import pygame
import json

from engine_src.engine.resource import resource
from engine_src.engine.core import scene_manager
from engine_src.engine.core import image
from engine_src.engine.ui import dialog_table
from engine_src.engine.ui import dialog_choice
from engine_src.engine.core import dialogue
from engine_src.engine.core import cfg_decoder
import engine_src.engine.core.cfg_decoder
CFGDecoderClass = engine_src.engine.core.cfg_decoder.CFGDecoder
from engine_src.engine.utils import dpi_tool
from engine_src.engine.core import save_game
from engine_src.engine.ui import dialog_backtext
from engine_src.engine.ugc_ui import ui_manager
from engine_src.engine.ugc_ui import ui_loader
from engine_src.engine.plugin import plugin_manager
from engine_src.engine.core import log
from engine_src.engine.debug import debugger_tcp_serevr
from engine_src.engine.core.event import event_bus
from engine_src.engine.g_o import g_o_manager
from engine_src.engine.core import input
from engine_src.engine.core.screen_transition import ScreenTransition



class Engine:
    def __init__(self, game_title, game_size):
        """
        初始化游戏窗口
        :param game_title: 窗口标题
        :param game_size: 逻辑窗口大小 (width, height)
        """
        pygame.display.set_caption(game_title)
        pygame.display.set_icon(pygame.image.load("icons/AppIcon.png"))

        # 使用with上下文防止文件句柄泄露
        with open("config/dialog_index.json", "r", encoding="utf-8") as f:
            self.id_index_map = json.load(f)
        with open("config/main_menu.json", "r", encoding="utf-8") as f:
            self.main_menu_config = json.load(f)

        self.center = [game_size[0] // 2, game_size[1] // 2]
        self.screen_size = pygame.display.list_modes()[0]
        self.fullscreen_center = [self.screen_size[0] // 2, self.screen_size[1] // 2]
        self.game_name = game_title
        self.game_size = game_size
        self.screen = pygame.display.set_mode(game_size, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.SCALED)

        # 游戏状态
        self.running = True
        self.in_dialog_game = False
        self.fps = 60
        self.clock = pygame.time.Clock()
        self.clock.tick(self.fps)
        self.is_full_screen = False
        self.is_looking_backtext = False
        self.save_game_ui_selected_solt = 0
        
        # 黑屏转场相关
        self.transition_active = False
        self.transition_start_time = 0
        self.transition_duration = 0.5
        self.transition_alpha = 0
        self.transition_target_callback = None

        # 初始化模块
        self.dpi = dpi_tool.DPITool(self.game_size, pygame.display.list_modes()[0])
        self.save_game_system = save_game.SaveGame(self)
        self.resource_manager = resource.AssetManager(self)
        self.scene = scene_manager.Scene(self)
        self.dialog = dialogue.Dialogue(self)
        self.cfg_decoder = CFGDecoderClass(self)
        self.debug_server = debugger_tcp_serevr.DebugServerMain(self)
        self.event = event_bus.EventBus()
        self.g_o_manager = g_o_manager.GOManager(self)
        self.input = input.InputManager(self.event)
        
        # 屏幕转场管理器
        self.screen_transition = ScreenTransition(self)

        # 初始化 UI
        self._create_global_ui_root_game_object()
        self.ugc_ui_manager = ui_manager.UIManager(self.game_size, self)
        self.dialog_table = dialog_table.GalDialogBox(
            self.screen, 40, game_size[1] - 180, game_size[0] - 80, 160, self.dialog
        )
        self.dialog_choice = dialog_choice.GalChoiceUI(self.screen)
        self.dialog_choice.set_panel_pos(game_size[0] * 0.5 - 200, game_size[1] * 0.5 - 100)
        self.dialog_backlog = dialog_backtext.BacklogViewer()
        self.dialog_backlog.set_backlog_panel_center(self.center[0], self.center[1])

        # 修复重复传参 self,self
        ui_loader_ = ui_loader.UILoader(self.global_ui_root.get_component("GlobalUIRoot"),self)
        self.main_menu_ui = ui_loader_.load_from_file(self.main_menu_config["main_menu_ui_path"][5:])
        self.save_game_ui = ui_loader_.load_from_file(self.main_menu_config["save_game_ui_path"][5:])
        self.settings = ui_loader_.load_from_file(self.main_menu_config["settings_ui_path"][5:])

        try:
            self.main_menu_bgm = self.resource_manager.load_sound(self.main_menu_config["bgm"][5:])
        except Exception as e:
            log.log(2, f"[ENGINE] 加载背景音乐失败: {e}")

        try:
            self.main_menu_background = image.Image(
                self.resource_manager.load_image(self.main_menu_config["background"][5:]),
                None, [0, 0], [1, 1], "fill", self.center, True
            )
        except Exception as e:
            log.log(2, f"[ENGINE] 加载背景图片失败: {e}")

        self.ugc_ui_manager.set_root(self.main_menu_ui)
        # 原代码这里if self.in_dialog_game永远False，删除，外部调用start_dialog_game

        # 插件系统初始化
        self.plugin_manager = plugin_manager.PluginManager(self)
        
        # 自动初始化 CGViewer
        self._init_cg_viewer()

    def _init_cg_viewer(self):
        """初始化全屏 CG 查看器"""
        from engine_src.engine.ugc_ui.cg_viewer import CGViewer
        
        cg_viewer = CGViewer(
            x=self.game_size[0] // 2,
            y=self.game_size[1] // 2,
            width=self.game_size[0],
            height=self.game_size[1],
            anchor="center",
            engine=self
        )
        self.ugc_ui_manager.add_cg_viewer(cg_viewer)

    def run(self):
        self.fps_font = pygame.font.Font("fonts/default.ttf", 24)
        if not self.in_dialog_game:
            try:
                self.main_menu_bgm.play(loops=-1)
            except Exception as e:
                log.log(3, f"[ENGINE] BGM播放失败 {e}")

        # 加载插件
        if os.path.exists("plugins"):
            for root, _, files in os.walk("plugins"):
                for file in files:
                    if file.endswith(".aoi"):
                        self.plugin_manager.load_plugin(os.path.join(root, file))
        self.plugin_manager.start()

        # 设置daemon=True，主程序退出线程自动销毁
        threading.Thread(target=self.debug_server.start, daemon=True).start()

        # 游戏主循环
        while self.running:
            self.input.frame_begin()  # 输入处理
            for event in pygame.event.get():
                self.input.process_pygame_event(event)  # 处理事件ad
                if event.type == pygame.QUIT:
                    self.running = False

                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.event.emit("mouse_click", {
                        "pos": pygame.mouse.get_pos(),
                        "pos_for_scene": self.get_mouse_pos_for_scene(),
                        "button": event.button
                    })
                    # 打开回溯日志时不再处理对话框点击
                    if self.in_dialog_game and not self.is_looking_backtext:
                        self.dialog_choice.handle_click()
                        pos = pygame.mouse.get_pos()
                        if self.dialog_table.rect.collidepoint(pos):
                            has_next = self.dialog_table.handle_click()
                            if has_next:
                                self.dialog.on_text_complete()
                                self.dialog.on_next()
                            else:
                                self.dialog.on_text_complete()

                if event.type == pygame.KEYDOWN:
                    # F11全屏切换
                    if event.key == pygame.K_F11:
                        self.fullscreen()
                    # S存档 L读档 B打开回溯
                    if event.key == pygame.K_s:
                        self.save_game_system.save_game(self.save_game_system.get_solt_path(1))
                    if event.key == pygame.K_l:
                        self.save_game_system.load_game(self.save_game_system.get_solt_path(1))
                    if event.key == pygame.K_b:
                        if self.in_dialog_game:
                            self.is_looking_backtext = not self.is_looking_backtext
                            self.dialog_backlog.active = self.is_looking_backtext

                # 事件分发：回溯打开优先接收事件
                if self.is_looking_backtext:
                    self.dialog_backlog.handle_event(event)
                else:
                    self.ugc_ui_manager.handle_event(event)

            pygame.display.update()
            delta_time = self.clock.tick(self.fps) / 1000.0
            self.screen.fill((0, 0, 0))

            self.scene.update()
            self.g_o_manager.update(delta_time)

            if not self.in_dialog_game:
                try:
                    self.main_menu_background.draw(self.screen)
                except Exception as e:
                    log.log(3, f"[ENGINE] 主菜单背景绘制异常 {e}")

            self.scene.draw(self.screen)
            self.g_o_manager.render(self.screen)
            self.cfg_decoder.update_wait(pygame.time.get_ticks())
            
            # 绘制屏幕转场效果
            self.screen_transition.draw(self.screen)

            if not self.is_looking_backtext:
                self.dialog_table.update(delta_time)
                self.dialog_choice.update()
            self.ugc_ui_manager.draw(self.screen)
            # 调整绘制顺序：先画对话框，最后画 UGC UI (包含 CG)
            if self.in_dialog_game:
                self.dialog_table.render()
                self.dialog_choice.render()
                self.dialog_backlog.draw(self.screen)
            


            self.plugin_manager.update()
            
            # 更新屏幕转场
            self.screen_transition.update(delta_time)
            
            self.event.update()

            # FPS文字黄色
            self.screen.blit(
                self.fps_font.render(f"FPS: {int(self.clock.get_fps())}", True, (200, 200, 0)),
                (10, 10)
            )
        # 循环退出后做资源释放
        self._cleanup()

    def _create_global_ui_root_game_object(self):
        self.global_ui_root = self.g_o_manager.create_game_object("GlobalUIRoot",{"position":[0,0],"rotate":0,"scale":[1,1]})
        self.g_o_manager.create_component(self.global_ui_root,"GlobalUIRoot",{})
    def _cleanup(self):
        """退出时资源清理"""
        log.log(1, "[ENGINE] 执行引擎退出清理")
        self.plugin_manager.end()
        self.debug_server.stop()
        pygame.mixer.music.stop()
        pygame.quit()

    def start_dialog_game(self, is_go_from_save_game=False, save_path=""):
        """开始对话游戏，先播放黑屏转场"""
        
        # 定义转场完成后的回调
        def on_transition_half_complete():
            """转场完成后真正进入游戏"""
            self.event.emit("dialog_start_game", {"is_go_from_save_game": is_go_from_save_game, "save_path": save_path})
            if not is_go_from_save_game:
                try:
                    self.main_menu_bgm.stop()
                except Exception as e:
                    log.log(2, f"[ENGINE]停止主菜单BGM失败 {e}")
                self.in_dialog_game = True
                self.ugc_ui_manager.clear_ui()
                with open("config/dialog.json", "r", encoding="utf-8") as f:
                    first_start_dialog_config = json.load(f)

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
        
        # 启动黑屏转场，设置回调
        self.screen_transition.start_transition("black_fade", 1, half_callback=on_transition_half_complete)

    def fullscreen(self):
        # 修复：切换后同步状态变量
        pygame.display.toggle_fullscreen()
        self.is_full_screen = not self.is_full_screen
        self.event.emit("fullscreen", {"is_full_screen": self.is_full_screen})

    def quit(self):
        self.running = False

    def get_center(self):
        if self.is_full_screen:
            return self.fullscreen_center
        else:
            return self.center

    def get_screen_size(self):
        if self.is_full_screen:
            return self.screen_size
        else:
            return self.game_size

    def get_mouse_pos(self):
        return [pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1]]

    def get_mouse_pos_for_scene(self):
        game_center = self.get_center()
        mouse_pos = self.get_mouse_pos()
        mouse_pos = [mouse_pos[0] - game_center[0], mouse_pos[1] - game_center[1]]
        return mouse_pos

    def set_mouse_visible(self, visible):
        pygame.mouse.set_visible(visible)

    def test_g_o(self):

        if self.g_o_manager is None:
            return
        obj = self.g_o_manager.create_game_object(
            "test_go",
            {"position": [-300, -100], "scale": [1, 1], "rotation": 0},
            None
        )
        self.g_o_manager.create_component(
            obj,
            "SpriteRenderer",
            {"image_path": "characters/chr_2.png", "alpha": 255}
        )
        self.event.subscribe("dialog_start_game", self.delete_test_go)

    def delete_test_go(self, data=None):
        self.g_o_manager.remove_game_object("test_go")
    
    def test_cg_viewer(self):
        """测试CG查看器功能"""
        from engine_src.engine.ugc_ui.cg_viewer import CGViewer, CGTransition
        
        # 创建CG查看器
        cg_viewer = CGViewer(
            x=self.game_size[0] // 2,
            y=self.game_size[1] // 2,
            width=self.game_size[0] - 100,
            height=self.game_size[1] - 200,
            anchor="center",
            engine=self
        )
        
        # 设置CG列表
        cg_viewer.set_cg_list([
            {
                'image_path': 'backgrounds/bg1.png',
                'title': '场景一',
                'description': '这是第一个CG场景的描述'
            },
            {
                'image_path': 'backgrounds/bg2.png',
                'title': '场景二',
                'description': '这是第二个CG场景的描述'
            }
        ])
        
        # 显示第一张CG
        cg_viewer.show_cg(cg_index=0)
        
        # 添加到UI管理器
        self.ugc_ui_manager.add_cg_viewer(cg_viewer)
        
        # 创建简单的UI根节点来包含CG查看器
        from engine_src.engine.ugc_ui.ui_element import UIElement
        root = UIElement(0, 0, self.game_size[0], self.game_size[1], engine=self)
        root.add_child(cg_viewer)
        self.ugc_ui_manager.set_root(root)
        
        log.log(0, "[ENGINE] CG查看器测试已启动")