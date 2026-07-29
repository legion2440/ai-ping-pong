import pygame

SCREEN_W, SCREEN_H = 900, 690
FPS = 60

COURT_W, COURT_H = 860, 460
COURT_X = (SCREEN_W - COURT_W) // 2
COURT_Y = 140

PADDLE_W, PADDLE_H = 14, 90
PADDLE_MARGIN = 26
BALL_SIZE = 16

HUMAN_SPEED = 420
BOT_BASE_SPEED = 260

COLORS = {
    "bg": (14, 15, 20),
    "panel": (24, 26, 34),
    "border": (46, 49, 63),
    "grid": (30, 32, 42),
    "text": (222, 224, 232),
    "muted": (120, 124, 138),
    "cyan": (86, 199, 214),
    "lime": (163, 214, 122),
    "magenta": (196, 138, 214),
    "ball": (238, 232, 205),
}

_font_cache = {}


def clear_font_cache():
    _font_cache.clear()


def font(size, bold=False):
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont("consolas,couriernew,monospace", size, bold=bold)
    return _font_cache[key]


def draw_text(surface, text, pos, size=16, color=None, bold=False, center=False):
    color = color or COLORS["text"]
    surf = font(size, bold).render(text, True, color)
    rect = surf.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    surface.blit(surf, rect)
    return rect
