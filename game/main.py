"""Visual frontend for the AI ping-pong project (Pygame).

Pure rendering / game-loop layer: menu, human-vs-bot, bot-vs-bot. Bot behavior
is routed through parameterized controllers, with no evolutionary training
attached yet.
"""
import os
import sys
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    project_root = Path(__file__).resolve().parent.parent
    os.chdir(project_root)
    os.execv(
        sys.executable,
        [sys.executable, "-m", "game.main", *sys.argv[1:]],
    )

import pygame

from .controllers import BaselineController, HumanController
from .simulation import MatchSimulation
from .utils import (
    COLORS,
    COURT_H,
    COURT_W,
    COURT_X,
    COURT_Y,
    FPS,
    SCREEN_H,
    SCREEN_W,
    draw_text,
)

MENU, HUMAN, BOTVBOT = "menu", "human", "botvbot"


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("PONG // EVOLVE - visual frontend")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()

        self.state = MENU
        self.menu_buttons = []
        self.left_controller = None
        self.right_controller = None
        self._reset_court()

    def _reset_court(self):
        if hasattr(self, "simulation"):
            self.simulation.reset()
        else:
            self.simulation = MatchSimulation()

    @property
    def p1(self):
        return self.simulation.p1

    @property
    def p2(self):
        return self.simulation.p2

    @property
    def ball(self):
        return self.simulation.ball

    @property
    def score1(self):
        return self.simulation.score1

    @property
    def score2(self):
        return self.simulation.score2

    def start(self, state):
        self.state = state
        self._reset_court()
        if state == HUMAN:
            self.left_controller = HumanController()
        else:
            self.left_controller = BaselineController()
        self.right_controller = BaselineController()
        self.left_controller.reset()
        self.right_controller.reset()

    # ---- input -----------------------------------------------------------
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.state = MENU
        if event.type == pygame.MOUSEBUTTONDOWN and self.state == MENU:
            for rect, target in self.menu_buttons:
                if rect.collidepoint(event.pos):
                    self.start(target)

    # ---- update ------------------------------------------------------------
    def update(self, dt):
        if self.state not in (HUMAN, BOTVBOT):
            return

        self.left_controller.update(self.p1, self.ball, dt)
        self.p1.clamp(COURT_Y, COURT_Y + COURT_H)

        self.right_controller.update(self.p2, self.ball, dt)
        self.p2.clamp(COURT_Y, COURT_Y + COURT_H)

        self.simulation.step(dt)

    # ---- draw --------------------------------------------------------------
    def draw_grid(self, surface):
        step = 42
        for x in range(0, SCREEN_W, step):
            pygame.draw.line(surface, COLORS["grid"], (x, 0), (x, SCREEN_H), 1)
        for y in range(0, SCREEN_H, step):
            pygame.draw.line(surface, COLORS["grid"], (0, y), (SCREEN_W, y), 1)

    def draw_menu(self):
        s = self.screen
        s.fill(COLORS["bg"])
        self.draw_grid(s)
        draw_text(s, "GENETIC ALGORITHM · PING-PONG SIMULATION", (SCREEN_W // 2, 90), 14, COLORS["cyan"], center=True)
        draw_text(s, "PONG // EVOLVE", (SCREEN_W // 2, 140), 46, COLORS["text"], bold=True, center=True)
        draw_text(s, "Visual frontend - pick a mode to watch the bot play.", (SCREEN_W // 2, 185), 16, COLORS["muted"], center=True)

        self.menu_buttons = []
        labels = [
            ("HUMAN VS BOT", "Play against the current best bot.", HUMAN, COLORS["cyan"]),
            ("BOT VS BOT", "Watch two bots battle.", BOTVBOT, COLORS["lime"]),
        ]
        btn_w, btn_h, gap = 320, 130, 24
        start_x = (SCREEN_W - (btn_w * 2 + gap)) // 2
        y = 250
        for i, (title, desc, target, color) in enumerate(labels):
            rect = pygame.Rect(start_x + i * (btn_w + gap), y, btn_w, btn_h)
            pygame.draw.rect(s, COLORS["panel"], rect, border_radius=4)
            pygame.draw.rect(s, color, rect, width=1, border_radius=4)
            draw_text(s, title, (rect.x + 20, rect.y + 20), 18, COLORS["text"], bold=True)
            draw_text(s, desc, (rect.x + 20, rect.y + 52), 13, COLORS["muted"])
            self.menu_buttons.append((rect, target))

        draw_text(s, "ESC returns to this menu during a match", (SCREEN_W // 2, y + btn_h + 40), 12, COLORS["muted"], center=True)

    def draw_hud(self):
        s = self.screen
        p1_label = "YOU" if self.state == HUMAN else "BOT A"
        p2_label = "BOT" if self.state == HUMAN else "BOT B"

        draw_text(s, p1_label, (COURT_X + 40, 45), 12, COLORS["muted"])
        draw_text(s, str(self.score1), (COURT_X + 40, 62), 30, COLORS["cyan"], bold=True)

        cx = SCREEN_W // 2
        mode_label = "HUMAN VS BOT" if self.state == HUMAN else "BOT VS BOT"
        draw_text(s, mode_label, (cx, 40), 15, COLORS["muted"], center=True)

        draw_text(s, p2_label, (COURT_X + COURT_W - 90, 45), 12, COLORS["muted"])
        draw_text(s, str(self.score2), (COURT_X + COURT_W - 60, 62), 30, COLORS["lime"], bold=True)

    def draw_court(self):
        s = self.screen
        court_rect = pygame.Rect(COURT_X, COURT_Y, COURT_W, COURT_H)
        pygame.draw.rect(s, (18, 19, 26), court_rect, border_radius=4)
        pygame.draw.rect(s, COLORS["border"], court_rect, width=1, border_radius=4)

        dash_h, gap = 10, 8
        y = COURT_Y
        while y < COURT_Y + COURT_H:
            pygame.draw.line(s, COLORS["border"], (SCREEN_W // 2, y), (SCREEN_W // 2, min(y + dash_h, COURT_Y + COURT_H)), 2)
            y += dash_h + gap

        self.p1.draw(s)
        self.p2.draw(s)
        self.ball.draw(s)

    def draw_game(self):
        self.screen.fill(COLORS["bg"])
        self.draw_grid(self.screen)
        self.draw_hud()
        self.draw_court()
        if self.state == HUMAN:
            draw_text(self.screen, "UP/W  ·  DOWN/S  ·  MOUSE - MOVE PADDLE", (SCREEN_W // 2, COURT_Y + COURT_H + 26), 13, COLORS["muted"], center=True)

    def draw(self):
        if self.state == MENU:
            self.draw_menu()
        else:
            self.draw_game()
        pygame.display.flip()

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.draw()


if __name__ == "__main__":
    Game().run()
