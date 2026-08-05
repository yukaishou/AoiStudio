import os

import pygame

if os.name == 'nt':  # 检查操作系统是否为Windows
    from ctypes import windll

    windll.user32.SetProcessDPIAware()  # 设置进程为DPI感知

    try:
        # 设置更高版本的DPI感知
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

pygame.init()
class GalChoiceUI:
    """
    【独立 GAL 选项界面模块】
    纯选项选择弹窗，无任何对话框耦合，接口丰富，即插即用
    支持：鼠标悬浮、点击选择、动态更新选项、样式全自定义
    """
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        if __name__ == "__main__":
            self.font = pygame.font.Font("default.ttf", 24)
        else:
            self.font = pygame.font.Font("fonts/default.ttf", 24)

        # 总开关
        self.active = False

        # 面板全局样式
        self.panel_bg = (0, 0, 0)
        self.panel_alpha = 220
        self.panel_x = 0
        self.panel_y = 0
        self.panel_width = 400
        self.panel_height = 260
        self.panel_radius = 8

        # 选项样式
        self.option_normal_color = (60, 60, 60)
        self.option_hover_color = (90, 90, 90)
        self.option_text_color = (255, 255, 255)
        self.option_height = 40
        self.option_gap = 12
        self.option_radius = 4

        # 文本偏移
        self.text_offset_x = 15

        # 选项数据列表 [文本, 回调函数]
        self.options = []
        self.hover_index = -1

    # ====================== 大量对外接口 ======================
    def set_panel_pos(self, x: int, y: int):
        """设置选项面板位置"""
        self.panel_x = x
        self.panel_y = y

    def set_panel_size(self, w: int, h: int):
        """设置选项面板尺寸"""
        self.panel_width = w
        self.panel_height = h

    def set_panel_style(self, bg_color, alpha: int, radius: int):
        """设置面板背景样式"""
        self.panel_bg = bg_color
        self.panel_alpha = max(0, min(255, alpha))
        self.panel_radius = radius

    def set_option_style(self, normal_color, hover_color, text_color):
        """设置选项按钮颜色"""
        self.option_normal_color = normal_color
        self.option_hover_color = hover_color
        self.option_text_color = text_color

    def set_option_layout(self, opt_height: int, opt_gap: int):
        """设置选项高度和间距"""
        self.option_height = opt_height
        self.option_gap = opt_gap

    def set_font(self, font: pygame.font.Font):
        """更换字体"""
        self.font = font

    def clear_options(self):
        """清空所有选项"""
        self.options.clear()
        self.hover_index = -1

    def add_option(self, text: str, callback):
        """
        添加一个选项
        :param text: 选项文字
        :param callback: 点击触发的回调函数
        """
        self.options.append([text, callback])

    def remove_option(self, index: int):
        """移除指定索引的选项"""
        if 0 <= index < len(self.options):
            del self.options[index]
            if self.hover_index >= index:
                self.hover_index -= 1


    def set_active(self, state: bool):
        """显示/隐藏选项面板"""
        self.active = state
        # 对选项的数量适配面板大小
        self.update_panel_scale()

    def is_active(self) -> bool:
        """判断选项面板是否开启"""
        return self.active

    def update_panel_scale(self):
        self.panel_height = self.option_height * len(self.options) + self.option_gap * (len(self.options) - 1) + 40

    # ====================== 逻辑更新 ======================
    def update(self):
        """每一帧更新悬浮状态"""
        if not self.active or len(self.options) == 0:
            self.hover_index = -1
            return

        mx, my = pygame.mouse.get_pos()
        self.hover_index = -1

        # 遍历判断悬浮
        start_y = self.panel_y + 20
        for idx in range(len(self.options)):
            opt_y = start_y + idx * (self.option_height + self.option_gap)
            opt_rect = pygame.Rect(
                self.panel_x + 20, opt_y,
                self.panel_width - 40, self.option_height
            )
            if opt_rect.collidepoint(mx, my):
                self.hover_index = idx
                break
        self.update_panel_scale()

    def handle_click(self):
        """鼠标点击判定，触发选项回调"""
        if not self.active or self.hover_index == -1:
            return False

        # 执行对应回调
        func = self.options[self.hover_index][1]
        if callable(func):
            func()
        return True

    # ====================== 渲染 ======================
    def render(self):
        """绘制选项面板"""
        if not self.active:
            return

        # 绘制透明背景面板
        panel_surf = pygame.Surface((self.panel_width, self.panel_height), pygame.SRCALPHA)
        bg_color = (*self.panel_bg, self.panel_alpha)
        pygame.draw.rect(panel_surf, bg_color, panel_surf.get_rect(), border_radius=self.panel_radius)

        # 绘制所有选项
        start_y = 20
        for idx, (text, _) in enumerate(self.options):
            opt_y = start_y + idx * (self.option_height + self.option_gap)
            opt_rect = pygame.Rect(20, opt_y, self.panel_width - 40, self.option_height)

            # 悬浮变色
            if idx == self.hover_index:
                color = self.option_hover_color
            else:
                color = self.option_normal_color

            pygame.draw.rect(panel_surf, color, opt_rect, border_radius=self.option_radius)

            # 绘制文字
            text_surf = self.font.render(text, True, self.option_text_color)
            panel_surf.blit(text_surf, (opt_rect.x + self.text_offset_x, opt_rect.y + 8))

        self.screen.blit(panel_surf, (self.panel_x, self.panel_y))

    def get_panel_pos(self):
        return self.panel_x, self.panel_y

    def get_panel_size(self):
        return self.panel_width, self.panel_height


# ====================== 使用示例 ======================
if __name__ == "__main__":
    screen = pygame.display.set_mode((900, 600))
    clock = pygame.time.Clock()

    # 初始化选项UI
    choice_ui = GalChoiceUI(screen)
    choice_ui.set_panel_pos(250, 180)
    choice_ui.set_panel_size(400, 220)

    # 测试回调
    def choose_a():
        print("选择了选项A：温柔安抚")
        choice_ui.set_active(False)

    def choose_b():
        print("选择了选项B：沉默回避")
        choice_ui.set_active(False)

    def choose_c():
        print("选择了选项C：开口质问")
        choice_ui.set_active(False)

    # 添加选项
    choice_ui.add_option("温柔安抚对方", choose_a)
    choice_ui.add_option("沉默避开对视", choose_b)
    choice_ui.add_option("焦急开口质问", choose_c)

    # 开启选项面板
    choice_ui.set_active(True)

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        screen.fill((20, 20, 20))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                choice_ui.handle_click()

        choice_ui.update()
        choice_ui.render()

        pygame.display.flip()

    pygame.quit()
