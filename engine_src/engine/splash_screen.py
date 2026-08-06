import pygame
import sys

# ===================== 配置参数（仿Unity开屏）=====================
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 540
FPS = 60

# 第一段LOGO动画时长
FADE_IN_DURATION = 1.0    # Logo淡入时长
STAY_DURATION = 1.5       # Logo静止显示时长
FADE_OUT_DURATION = 0.8   # Logo淡出时长

# 第二段LOGO动画时长
FADE_IN_DURATION_2 = 1.0
STAY_DURATION_2 = 1.5
FADE_OUT_DURATION_2 = 0.8

LOGO_PATH = "icons/Engine.png"    # 第一张Logo
LOGO2_PATH = "icons/GameComponyLogo.png"    # 第二张Logo（新增）
BACKGROUND_COLOR = (100,100,100)        # 灰色背景
TEXT_CONTENT = "Made With AoiStudio"
TEXT_COLOR = (255, 255, 255)
TEXT_FONT_SIZE = 64

# 动画阶段枚举（新增第二段状态）
STATE_FADE_IN = 0
STATE_STAY = 1
STATE_FADE_OUT = 2
STATE_FADE_IN_2 = 3    # 新增：第二张图淡入
STATE_STAY_2 = 4       # 新增：第二张图停留
STATE_FADE_OUT_2 = 5   # 新增：第二张图淡出
STATE_FINISHED = 6

def main(size,game_name,show_logo2,show_logo1):
    global BACKGROUND_COLOR, current_logo
    pygame.init()
    SCREEN_HEIGHT = size[1]
    SCREEN_WIDTH = size[0]
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(game_name)
    pygame.display.set_icon(pygame.image.load("icons/AppIcon.png"))
    clock = pygame.time.Clock()


    # 加载第一张Logo（强制200x200）
    try:
        logo_img = pygame.image.load(LOGO_PATH).convert_alpha()
    except FileNotFoundError:
        print("未找到Logo1图片，将使用纯色方块代替")
        logo_img = pygame.Surface((200, 200), pygame.SRCALPHA)
        pygame.draw.rect(logo_img, (255, 255, 255), (0, 0, 200, 200))
    # 强制缩放为200x200
    logo_img = pygame.transform.scale(logo_img, (200, 200))

    # 加载第二张Logo
    try:
        logo2_img = pygame.image.load(LOGO2_PATH).convert_alpha()
    except FileNotFoundError:
        print("未找到Logo2图片，将使用纯色方块代替")
        logo2_img = pygame.Surface((200, 200), pygame.SRCALPHA)
        pygame.draw.rect(logo2_img, (200, 200, 200), (0, 0, 200, 200))


    # 文字字体
    try:
        font = pygame.font.SysFont("sans-serif", TEXT_FONT_SIZE)
    except:
        font = pygame.font.Font(None, TEXT_FONT_SIZE)

    text_surface = font.render(TEXT_CONTENT, True, TEXT_COLOR)

    # 布局位置（两张图共用同一位置）
    logo_rect = logo_img.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 40))
    text_rect = text_surface.get_rect(center=(SCREEN_WIDTH//2, logo_rect.bottom + 35))

    # 动画状态变量
    if show_logo1:
        anim_state = STATE_FADE_IN
    elif show_logo2:
        anim_state = STATE_FADE_IN_2
    else:
        anim_state = STATE_FINISHED
    timer = 0.0
    alpha = 0
    if show_logo1:
        current_logo = logo_img  # 当前显示的Logo
    elif show_logo2:
        current_logo = logo2_img


    running = True

    while running:
        dt = clock.tick(FPS) / 1000.0
        timer += dt

        # 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            # 空格跳过动画
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    anim_state = STATE_FINISHED

        # ---------------------- 动画状态机（新增第二段逻辑）----------------------
        if anim_state == STATE_FADE_IN:
            progress = timer / FADE_IN_DURATION
            alpha = min(255, int(255 * progress))
            if progress >= 1.0:
                anim_state = STATE_STAY
                timer = 0.0

        elif anim_state == STATE_STAY:
            alpha = 255
            if timer >= STAY_DURATION:
                anim_state = STATE_FADE_OUT
                timer = 0.0

        elif anim_state == STATE_FADE_OUT:
            progress = timer / FADE_OUT_DURATION
            alpha = max(0, int(255 * (1 - progress)))
            if progress >= 1.0:
                if show_logo2:
                    anim_state = STATE_FADE_IN_2  # 切换到第二张图淡入
                    current_logo = logo2_img  # 切换显示第二张图
                else:
                    anim_state = STATE_FINISHED
                timer = 0.0

        # 新增：第二张图淡入
        elif anim_state == STATE_FADE_IN_2:
            BACKGROUND_COLOR = (0,0,0)
            logo_rect = logo2_img.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            progress = timer / FADE_IN_DURATION_2
            alpha = min(255, int(255 * progress))
            if progress >= 1.0:
                anim_state = STATE_STAY_2
                timer = 0.0

        # 新增：第二张图停留
        elif anim_state == STATE_STAY_2:
            alpha = 255
            if timer >= STAY_DURATION_2:
                anim_state = STATE_FADE_OUT_2
                timer = 0.0

        # 新增：第二张图淡出
        elif anim_state == STATE_FADE_OUT_2:
            progress = timer / FADE_OUT_DURATION_2
            alpha = max(0, int(255 * (1 - progress)))
            if progress >= 1.0:
                anim_state = STATE_FINISHED

        elif anim_state == STATE_FINISHED:
            running = False

        # 绘制
        screen.fill(BACKGROUND_COLOR)

        # 设置透明度，Logo和文字共用透明度同步渐变
        current_logo.set_alpha(alpha)
        screen.blit(current_logo, logo_rect)

        # 文字透明图层实现淡入淡出
        if not anim_state == STATE_FADE_IN_2 and not anim_state == STATE_STAY_2 and not anim_state == STATE_FADE_OUT_2:
            text_canvas = pygame.Surface(text_surface.get_size(), pygame.SRCALPHA)
            text_canvas.blit(text_surface, (0, 0))
            text_canvas.set_alpha(alpha)
            screen.blit(text_canvas, text_rect)

        pygame.display.flip()

    # 开屏结束，进入主游戏
    print("开屏动画完成，加载游戏主场景...")

if __name__ == "__main__":
    main((960, 540), "AoiStudio Game")