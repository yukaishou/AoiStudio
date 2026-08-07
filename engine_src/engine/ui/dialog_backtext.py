import pygame

# -------------------------- 配置常量 --------------------------
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
BG_COLOR = (25,25,25)
TEXT_COLOR = (220, 220, 220)
TITLE_COLOR = (255, 255, 255)
SCROLL_BAR_COLOR = (80, 84, 94)
SCROLL_THUMB_COLOR = (120, 130, 150)
LINE_HEIGHT = 28
MARGIN = 10
MAX_BACKLOG_ENTRIES = 600
PAGE_STEP = LINE_HEIGHT * 8
SCROLL_SPEED_MULT = 2
MIN_THUMB_HEIGHT = 30

# 强制初始化字体模块
pygame.font.init()

# 字体（优先系统中文字体，避免方块）
try:
    font_title = pygame.font.Font("fonts/default.ttf", 24)
    font_text = pygame.font.Font("fonts/default.ttf", 20)
except Exception:
    # Windows/macOS 中文字体 fallback
    font_title = pygame.font.SysFont(["simhei", "Microsoft YaHei", "sans-serif"], 24)
    font_text = pygame.font.SysFont(["simhei", "Microsoft YaHei", "sans-serif"], 20)


class BacklogViewer:
    def __init__(self):
        self.active = False
        self.history = []
        self._render_cache = []  # (speaker_surf, text_surf)
        self.scroll_y = 0
        self.max_scroll = 0

        self.panel_rect = pygame.Rect(MARGIN, MARGIN, SCREEN_WIDTH - MARGIN*2, SCREEN_HEIGHT - MARGIN*2)
        self.scroll_bar_width = 12
        self.panel_a = 200  # 提高不透明度，避免被背景覆盖

        # 缓存Surface与脏标记
        self._panel_surface = None
        self._title_surface = None
        self._panel_dirty = True
        self._title_dirty = True

        self._bar_rect = pygame.Rect(0, 0, 0, 0)
        self._thumb_h = MIN_THUMB_HEIGHT

    def add_log(self, log_dict: dict):
        """添加历史并预渲染，确保缓存同步"""
        if len(self.history) >= MAX_BACKLOG_ENTRIES:
            self.history.pop(0)
            self._render_cache.pop(0)

        self.history.append(log_dict)
        speaker = log_dict.get("speaker", "")
        content = log_dict.get("text", "")
        spk_text = f"【{speaker}】" if speaker else ""

        # 预渲染文本（关键：必须成功生成Surface）
        spk_surf = font_text.render(spk_text, True, TITLE_COLOR)
        txt_surf = font_text.render(content, True, TEXT_COLOR)
        self._render_cache.append((spk_surf, txt_surf))

        self._calc_scroll_meta()
        # 调试：确认缓存生成
        #print(f"[Backlog] 缓存生成：{spk_text[:10]}... | 总数：{len(self._render_cache)}")

    def set_logs(self, log_list: list):
        """批量添加历史"""
        self.history = log_list
        self._render_cache = []
        for log_dict in log_list:
            self.add_log(log_dict)

    def _calc_scroll_meta(self):
        """计算滚动范围，确保max_scroll正确"""
        total_height = len(self.history) * LINE_HEIGHT
        view_height = self.panel_rect.height - MARGIN * 2
        self.max_scroll = max(0, total_height - view_height)

        view_h = self.panel_rect.height - 60
        if self.max_scroll > 0:
            self._thumb_h = max(MIN_THUMB_HEIGHT, view_h * (view_h / (self.max_scroll + view_h)))
        else:
            self._thumb_h = view_h

    # 兼容旧引擎调用
    def _calc_scroll_limit(self):
        self._calc_scroll_meta()

    def scroll(self, delta: int):
        self.scroll_y = max(0, min(self.scroll_y + delta, self.max_scroll))

    def _rebuild_panel(self):
        """重建半透明面板，确保不覆盖文本"""
        w, h = self.panel_rect.size
        self._panel_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        fill_color = (*BG_COLOR, self.panel_a)
        pygame.draw.rect(self._panel_surface, fill_color, (0, 0, w, h), border_radius=MARGIN)
        self._panel_dirty = False

    def _rebuild_title(self):
        self._title_surface = font_title.render("历史对话回溯 [ESC关闭]", True, TITLE_COLOR)
        self._title_dirty = False

    def draw(self, surf: pygame.Surface):
        if not self.active:
            return

        # 重建脏资源
        if self._panel_dirty or self._panel_surface is None:
            self._rebuild_panel()
        if self._title_dirty or self._title_surface is None:
            self._rebuild_title()

        # 1. 绘制面板（先画背景，再画文本，避免被覆盖）
        surf.blit(self._panel_surface, self.panel_rect)
        surf.blit(self._title_surface, (self.panel_rect.x + MARGIN, self.panel_rect.y + 8))

        # 2. 视口区域定义（修复坐标与裁剪）
        view_area_y = self.panel_rect.y + 40
        view_h = self.panel_rect.height - 60
        clip_x = self.panel_rect.x + MARGIN
        # 修复：裁剪宽度 = 面板宽 - 边距*2 - 滚动条宽
        clip_w = self.panel_rect.width - MARGIN*2 - self.scroll_bar_width - 6
        clip_rect = pygame.Rect(clip_x, view_area_y, clip_w, view_h)

        # 3. 裁剪区域（只在视口内绘制）
        old_clip = surf.get_clip()
        surf.set_clip(clip_rect)

        # 4. 修复：计算可见行（核心：draw_y 必须在视口内）
        draw_start_y = view_area_y - self.scroll_y
        first_idx = max(0, int((view_area_y - draw_start_y) / LINE_HEIGHT))
        last_idx = min(len(self._render_cache), int((view_area_y + view_h - draw_start_y) / LINE_HEIGHT) + 2)

        # 5. 局部变量加速，减少属性查找
        render_cache = self._render_cache
        cx = clip_rect.x
        line_h = LINE_HEIGHT

        for idx in range(first_idx, last_idx):
            spk_surf, txt_surf = render_cache[idx]
            cy = draw_start_y + idx * line_h
            # 绘制说话人+文本（确保坐标在clip内）
            surf.blit(spk_surf, (cx, cy))
            surf.blit(txt_surf, (cx + spk_surf.get_width() + 6, cy))

        # 恢复裁剪
        surf.set_clip(old_clip)

        # 7. 绘制滚动条
        bar_x = self.panel_rect.right - self.scroll_bar_width - 6
        self._bar_rect.update(bar_x, view_area_y, self.scroll_bar_width, view_h)
        pygame.draw.rect(surf, SCROLL_BAR_COLOR, self._bar_rect, border_radius=6)

        if self.max_scroll > 0:
            thumb_y = self._bar_rect.y + (view_h - self._thumb_h) * (self.scroll_y / self.max_scroll)
            thumb_rect = pygame.Rect(bar_x, thumb_y, self.scroll_bar_width, self._thumb_h)
            pygame.draw.rect(surf, SCROLL_THUMB_COLOR, thumb_rect, border_radius=6)

    def handle_event(self, event: pygame.event.Event):
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
                self.scroll(-PAGE_STEP)
            elif event.key == pygame.K_PAGEDOWN:
                self.scroll(PAGE_STEP)
        elif event.type == pygame.MOUSEWHEEL:
            delta = event.y * LINE_HEIGHT * SCROLL_SPEED_MULT
            delta = max(-PAGE_STEP, min(PAGE_STEP, delta))
            self.scroll(-delta)

    def set_backlog_panel_center(self, center_x: int, center_y: int):
        self.panel_rect.center = (center_x, center_y)
        self._panel_dirty = True
        self._calc_scroll_meta()

    def set_panel_alpha(self, alpha: int):
        self.panel_a = max(0, min(255, alpha))
        self._panel_dirty = True

    def clear(self):
        self.history.clear()
        self._render_cache.clear()
        self.scroll_y = 0
        self.max_scroll = 0
        self._calc_scroll_meta()

    def set_active(self, value: bool):
        self.active = value
        # 打开时自动滚动到底部（可选，方便看最新）
        if value:
            self.scroll_y = self.max_scroll