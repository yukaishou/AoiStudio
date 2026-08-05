import pygame

# -------------------------- 配置常量 --------------------------
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
BG_COLOR = (20, 22, 30)
PANEL_BG = (0,0,0)
TEXT_COLOR = (220, 220, 220)
TITLE_COLOR = (255,255,255)
SCROLL_BAR_COLOR = (80, 84, 94)
SCROLL_THUMB_COLOR = (120,130,150)
LINE_HEIGHT = 28
MARGIN = 20



# 字体
try:
    font_title = pygame.font.Font("fonts/default.ttf",24)
    font_text = pygame.font.Font("fonts/default.ttf",20)
except:
    font_title = pygame.font.SysFont("sans-serif",24)
    font_text = pygame.font.SysFont("sans-serif",20)


class BacklogViewer:
    def __init__(self):
        self.active = False
        # 每条为完整字典，包含text、speaker以及你其他业务字段(dialogue_file_path、bgm、index等)
        self.history = []
        self.scroll_y = 0
        self.max_scroll = 0
        self.panel_rect = pygame.Rect(MARGIN, MARGIN, SCREEN_WIDTH-MARGIN*2, SCREEN_HEIGHT-MARGIN*2)
        self.scroll_bar_width = 12
        # 设置不透明度
        self.panel_a = 128

    def add_log(self, log_dict:dict):
        """
        直接传入你的完整字典:
        {
            "text": "...",
            "speaker": "...",
            "dialogue_file_path": "...",
            "bgm": "...",
            "index": ...
        }
        回溯渲染仅读取 text / speaker，其余字段原样保存不作处理
        """
        self.history.append(log_dict)
        self._calc_scroll_limit()

    def _calc_scroll_limit(self):
        total_height = len(self.history)*LINE_HEIGHT
        view_height = self.panel_rect.height - MARGIN*2
        self.max_scroll = max(0, total_height - view_height-100)

    def scroll(self, delta):
        self.scroll_y += delta
        self.scroll_y = max(0, min(self.scroll_y, self.max_scroll))

    def draw(self, surf):
        if not self.active:
            return
        # 渲染不透明度
        panel_surface = pygame.Surface((self.panel_rect.width, self.panel_rect.height), pygame.SRCALPHA)
        color = (*BG_COLOR, self.panel_a)
        pygame.draw.rect(panel_surface, color, panel_surface.get_rect(), border_radius=MARGIN)
        surf.blit(panel_surface,self.panel_rect)
        title_surf = font_title.render("历史对话回溯 [ESC关闭]", True, TITLE_COLOR)
        surf.blit(title_surf, (self.panel_rect.x+MARGIN, self.panel_rect.y+8))

        view_area_y = self.panel_rect.y + 40
        view_h = self.panel_rect.height - 60

        clip_rect = pygame.Rect(self.panel_rect.x+MARGIN, view_area_y,
                                self.panel_rect.width-MARGIN*2-self.scroll_bar_width, view_h)
        old_clip = surf.get_clip()
        surf.set_clip(clip_rect)

        draw_y = view_area_y - self.scroll_y
        for item in self.history:
            speaker = item["speaker"]
            content = item["text"]
            spk_text = f"【{speaker}】" if speaker else ""
            line1 = font_text.render(spk_text, True, TITLE_COLOR)
            line2 = font_text.render(content, True, TEXT_COLOR)
            surf.blit(line1, (clip_rect.x, draw_y))
            surf.blit(line2, (clip_rect.x + line1.get_width()+6, draw_y))
            draw_y += LINE_HEIGHT

        surf.set_clip(old_clip)

        # 滚动条绘制
        bar_x = self.panel_rect.right - self.scroll_bar_width - 6
        bar_rect = pygame.Rect(bar_x, view_area_y, self.scroll_bar_width, view_h)
        pygame.draw.rect(surf, SCROLL_BAR_COLOR, bar_rect, border_radius=6)

        if self.max_scroll>0:
            thumb_h = max(30, view_h * (view_h/(self.max_scroll+view_h)))
            thumb_y = bar_rect.y + (view_h - thumb_h) * (self.scroll_y / self.max_scroll)
            thumb_rect = pygame.Rect(bar_x, thumb_y, self.scroll_bar_width, thumb_h)
            pygame.draw.rect(surf, SCROLL_THUMB_COLOR, thumb_rect, border_radius=6)

    def handle_event(self,event):
        if not self.active:
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.active = False
            elif event.key == pygame.K_UP:
                self.scroll(-LINE_HEIGHT)
            elif event.key == pygame.K_DOWN:
                self.scroll(LINE_HEIGHT)
            elif event.key == pygame.K_PAGEUP:
                self.scroll(-LINE_HEIGHT*8)
            elif event.key == pygame.K_PAGEDOWN:
                self.scroll(LINE_HEIGHT*8)
        if event.type == pygame.MOUSEWHEEL:
            self.scroll(-event.y*LINE_HEIGHT*2)

    def set_backlog_panel_center(self, center_x: int, center_y: int):
        self.panel_rect.centerx = center_x
        self.panel_rect.centery = center_y

