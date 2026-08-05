import pygame


class GalDialogBox:
    """
    GalGame 对话框组件
    黑色纯色背景对话框，打字机文本效果，丰富外部调用接口
    """
    def __init__(
        self,
        surf: pygame.Surface,
        x: int,
        y: int,
        width: int,
        height: int,
            dialogue_system=None,
        font: pygame.font.Font = None
    ):
        # 目标渲染画布
        self.screen = surf
        # 对话框基础矩形
        self.rect = pygame.Rect(x, y, width, height)
        self.dialogue_system = dialogue_system

        # ===================== 外观配置 =====================
        self.bg_color = (0, 0, 0)          # 背景黑色
        self.border_color = (120, 120, 120)# 边框颜色
        self.border_width = 2               # 边框粗细
        self.alpha = 230                    # 整体透明度 0~255
        self.padding = (20, 16)             # 文本内边距 (左右,上下)

        # ===================== 文字配置 =====================
        if font is None:
            font = pygame.font.Font("fonts/default.ttf", 24)
        self.font = font
        self.text_color = (255, 255, 255)
        self.text_speed = 0.06              # 每个字符间隔秒数
        self.line_height = 32               # 行间距
        self.max_line_count = 5             # 对话框最大显示行数

        # ===================== 文本数据 =====================
        self.full_text = ""                # 完整原始文本
        self.display_text = ""             # 当前显示文字（打字机）
        self.text_timer = 0.0
        self.char_index = 0                # 当前打到第几个字
        self.text_finished = False         # 是否全部显示完成
        self.fst = False

        # 分页相关
        self.page_lines = []               # 分页后的文本行列表
        self.current_page = 0

        # 角色名（可选顶部名称栏）
        self.speaker_name = ""
        self.name_color = (220, 200, 100)
        self.name_height = 36

        # ===================== 状态控制 =====================
        self.visible = True
        self.skip_speed = 0.001            # 按住加速的文字速度

    # ==============================================
    # 【对外接口】大量可调用方法
    # ==============================================
    def set_position(self, x: int, y: int):
        """设置对话框坐标"""
        self.rect.topleft = (x, y)

    def set_size(self, w: int, h: int):
        """设置对话框宽高"""
        self.rect.width = w
        self.rect.height = h

    def set_bg_color(self, color):
        """设置背景颜色"""
        self.bg_color = color

    def set_border(self, color, width: int):
        """设置边框颜色与粗细"""
        self.border_color = color
        self.border_width = width

    def set_alpha(self, value: int):
        """设置透明度 0~255"""
        self.alpha = max(0, min(255, value))

    def set_padding(self, horizontal: int, vertical: int):
        """设置文本内边距"""
        self.padding = (horizontal, vertical)

    def set_font(self, font: pygame.font.Font):
        """更换字体"""
        self.font = font

    def set_text_color(self, color):
        """正文文字颜色"""
        self.text_color = color

    def set_name_color(self, color):
        """角色名字颜色"""
        self.name_color = color

    def set_text_speed(self, sec: float):
        """常规打字速度（每个字符间隔秒）"""
        self.text_speed = sec

    def set_line_height(self, height: int):
        """文本行间距"""
        self.line_height = height

    def set_max_line(self, line_num: int):
        """一页最多显示多少行文本"""
        self.max_line_count = line_num

    def set_speaker(self, name: str):
        """设置说话角色名称，空字符串隐藏名称栏"""
        self.speaker_name = name

    def set_visible(self, state: bool):
        """显示/隐藏对话框"""
        self.visible = state

    def load_text(self, text: str):
        """
        加载新对话文本，自动重新开始打字动画、自动分页
        :param text: 完整对话文本
        """
        self.full_text = text
        self.display_text = ""
        self.char_index = 0
        self.text_timer = 0.0
        self.text_finished = False
        self.current_page = 0
        self._split_text_to_pages()

    def skip_all_text(self):
        """立刻显示当前页全部文字"""
        self.text_finished = True
        self.display_text = self._get_page_full_text(self.current_page)

    def next_page(self) -> bool:
        """
        切换下一页
        :return: 是否还有下一页，False代表文本全部结束
        """
        if self.current_page + 1 < len(self.page_lines):
            self.current_page += 1
            self.char_index = 0
            self.display_text = ""
            self.text_finished = False
            self.text_timer = 0.0
            return True
        return False

    def is_text_complete(self) -> bool:
        """当前页面文字是否已经全部显示完毕"""
        return self.text_finished

    def handle_click(self) -> bool:
        """
        点击对话框时调用的逻辑
        返回 True = 可以切换下一页
        使用方式：if event.type == pygame.MOUSEBUTTONDOWN and box.rect.collidepoint(pos): box.handle_click()
        """
        if not self.text_finished:
            self.skip_all_text()
            return False
        else:
            return True

    def update(self, dt: float, fast: bool = False):
        """
        每一帧更新打字动画
        :param dt: delta_time 帧间隔秒
        :param fast: 是否加速（按住按键快速打字）
        """
        if not self.visible or self.text_finished:
            return

        speed = self.skip_speed if fast else self.text_speed
        self.text_timer += dt

        if self.text_timer >= speed:
            self.text_timer = 0.0
            page_content = self._get_page_full_text(self.current_page)
            if self.char_index < len(page_content):
                self.fst = True
                self.display_text += page_content[self.char_index]
                self.char_index += 1
            else:
                self.text_finished = True
                if self.fst:
                    self.fst = False
                    self.dialogue_system.on_text_complete()

    def render(self):
        """渲染对话框到画布，每一帧调用"""
        if not self.visible:
            return

        # 创建透明图层绘制框体
        dialog_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        # 背景填充
        bg_rgba = (*self.bg_color, self.alpha)
        pygame.draw.rect(dialog_surface, bg_rgba, dialog_surface.get_rect(), border_radius=6)
        # 边框
        if self.border_width > 0:
            pygame.draw.rect(
                dialog_surface, self.border_color,
                dialog_surface.get_rect(), width=self.border_width, border_radius=6
            )

        # 绘制角色名称
        offset_y = self.padding[1]
        if self.speaker_name:
            name_surf = self.font.render(self.speaker_name, True, self.name_color)
            dialog_surface.blit(name_surf, (self.padding[0], offset_y))
            offset_y += self.name_height

        # 绘制当前文本（自动换行）
        lines = self._wrap_text(self.display_text, self.rect.width - self.padding[0] * 2)
        for line in lines[:self.max_line_count]:
            text_surf = self.font.render(line, True, self.text_color)
            dialog_surface.blit(text_surf, (self.padding[0], offset_y))
            offset_y += self.line_height

        # 贴到主画布
        self.screen.blit(dialog_surface, self.rect.topleft)

    # ==============================================
    # 【内部工具函数】
    # ==============================================
    def _wrap_text(self, text: str, max_width: int) -> list[str]:
        """文本自动换行"""
        words = list(text)
        lines = []
        current_line = ""
        for char in words:
            test_line = current_line + char
            if self.font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = char
        if current_line:
            lines.append(current_line)
        return lines

    def _split_text_to_pages(self):
        """把完整文本分割成多页"""
        all_lines = self._wrap_text(self.full_text, self.rect.width - self.padding[0] * 2)
        self.page_lines = []
        for i in range(0, len(all_lines), self.max_line_count):
            page_chunk = all_lines[i:i + self.max_line_count]
            self.page_lines.append("".join(page_chunk))

    def _get_page_full_text(self, page_idx: int) -> str:
        if 0 <= page_idx < len(self.page_lines):
            return self.page_lines[page_idx]
        return ""

    def get_position(self):
        return self.rect.topleft

    def get_size(self):
        return self.rect.size


# ======================== 使用示例 ========================
if __name__ == "__main__":
    SCREEN_W, SCREEN_H = 1000, 600
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()

    # 创建对话框实例：底部放置
    dialog = GalDialogBox(
        surf=screen,
        x=40,
        y=SCREEN_H - 180,
        width=SCREEN_W - 80,
        height=140
    )
    # 配置参数演示
    dialog.set_speaker("少女")
    dialog.load_text("欢迎来到这个世界！这里是一段很长很长的测试对话，文字会自动换行。点击对话框可以快速显示全部文字，再次点击翻页。\n第二页测试内容！")

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        screen.fill((30, 30, 30))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                if dialog.rect.collidepoint(pos):
                    has_next = dialog.handle_click()
                    if has_next:
                        print("进入下一页")

        # 更新打字动画
        dialog.update(dt)
        dialog.render()

        pygame.display.flip()
    pygame.quit()