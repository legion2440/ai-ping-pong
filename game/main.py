"""Visual frontend for trained AI ping-pong bots."""
import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import sys
from pathlib import Path

_INVOCATION_CWD_ENV = "_AI_PING_PONG_GAME_INVOCATION_CWD"
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__" and __package__ is None:
    os.environ[_INVOCATION_CWD_ENV] = os.getcwd()
    os.chdir(PROJECT_ROOT)
    os.execv(
        sys.executable,
        [sys.executable, "-m", "game.main", *sys.argv[1:]],
    )

INVOCATION_CWD = Path(
    os.environ.pop(_INVOCATION_CWD_ENV, os.getcwd())
).resolve()

import argparse

import pygame

from ga.artifacts import (
    GenerationRecord,
    load_best_genome,
    load_generation_history,
)
from ga.genome import BotGenome

from .controllers import BotController, HumanController
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
    font,
)

MENU, HUMAN, BOTVBOT = "menu", "human", "botvbot"


class Game:
    def __init__(self, best_genome, generation_records):
        if not isinstance(best_genome, BotGenome):
            raise TypeError("best_genome must be a BotGenome")

        try:
            generation_records = tuple(generation_records)
        except TypeError as error:
            raise TypeError(
                "generation_records must be an iterable"
            ) from error
        if not generation_records:
            raise ValueError("generation_records must not be empty")
        if any(
            not isinstance(record, GenerationRecord)
            for record in generation_records
        ):
            raise TypeError(
                "generation_records must contain only GenerationRecord values"
            )

        self.best_genome = best_genome
        self.generation_records = generation_records
        self.generation_index = 0

        pygame.init()
        pygame.display.set_caption("PONG // EVOLVE")
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
        if state == BOTVBOT:
            self.generation_index = 0
        self._reset_court()

        if state == HUMAN:
            self.left_controller = HumanController()
            self.right_controller = BotController(self.best_genome)
        else:
            self._create_generation_controllers()

        self.left_controller.reset()
        self.right_controller.reset()

    def _create_generation_controllers(self):
        current = self.generation_records[self.generation_index]
        initial = self.generation_records[0]
        self.left_controller = BotController(current.genome)
        self.right_controller = BotController(initial.genome)

    def change_generation(self, offset):
        if self.state != BOTVBOT:
            return

        new_index = min(
            len(self.generation_records) - 1,
            max(0, self.generation_index + offset),
        )
        if new_index == self.generation_index:
            return

        self.generation_index = new_index
        self._reset_court()
        self._create_generation_controllers()

    # ---- input -----------------------------------------------------------
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.state = MENU
        if event.type == pygame.KEYDOWN and self.state == BOTVBOT:
            if event.key == pygame.K_LEFT:
                self.change_generation(-1)
            elif event.key == pygame.K_RIGHT:
                self.change_generation(1)
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
        draw_text(s, "Pick a mode to watch the bot play.", (SCREEN_W // 2, 185), 16, COLORS["muted"], center=True)

        self.menu_buttons = []
        labels = [
            (
                "HUMAN VS BOT",
                ("Play against the saved best bot.",),
                HUMAN,
                COLORS["cyan"],
            ),
            (
                "BOT VS BOT",
                ("Compare generation champions with", "generation 0."),
                BOTVBOT,
                COLORS["lime"],
            ),
        ]
        btn_w, btn_h, gap = 320, 130, 24
        start_x = (SCREEN_W - (btn_w * 2 + gap)) // 2
        y = 250
        for i, (title, description_lines, target, color) in enumerate(labels):
            rect = pygame.Rect(start_x + i * (btn_w + gap), y, btn_w, btn_h)
            pygame.draw.rect(s, COLORS["panel"], rect, border_radius=4)
            pygame.draw.rect(s, color, rect, width=1, border_radius=4)
            draw_text(s, title, (rect.x + 20, rect.y + 20), 18, COLORS["text"], bold=True)
            for line_index, line in enumerate(description_lines):
                draw_text(
                    s,
                    line,
                    (rect.x + 20, rect.y + 52 + line_index * 20),
                    13,
                    COLORS["muted"],
                )
            self.menu_buttons.append((rect, target))

        esc_label = "ESC"
        footer_label = " returns to this menu during a match"
        esc_width, esc_height = font(12, bold=True).size(esc_label)
        footer_width, footer_height = font(12).size(footer_label)
        footer_x = (SCREEN_W - esc_width - footer_width) // 2
        footer_center_y = y + btn_h + 40
        draw_text(
            s,
            esc_label,
            (footer_x, footer_center_y - esc_height // 2),
            12,
            COLORS["cyan"],
            bold=True,
        )
        draw_text(
            s,
            footer_label,
            (footer_x + esc_width, footer_center_y - footer_height // 2),
            12,
            COLORS["muted"],
        )

    def draw_hud(self):
        s = self.screen
        if self.state == HUMAN:
            p1_label = "YOU"
            p2_label = "BEST BOT"
            mode_label = "HUMAN VS BOT"
        else:
            current = self.generation_records[self.generation_index]
            initial = self.generation_records[0]
            last = self.generation_records[-1]
            p1_label = f"GEN {current.generation}"
            p2_label = f"GEN {initial.generation}"
            mode_label = (
                f"BOT VS BOT (GEN {current.generation} / "
                f"GEN {last.generation}) · "
                f"TRAIN FITNESS {current.best_fitness}"
            )

        draw_text(s, p1_label, (COURT_X + 40, 45), 12, COLORS["muted"])
        draw_text(s, str(self.score1), (COURT_X + 40, 62), 30, COLORS["cyan"], bold=True)

        cx = SCREEN_W // 2
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
            draw_text(self.screen, "UP/W  ·  DOWN/S  ·  MOUSE - MOVE PADDLE", (SCREEN_W // 2, SCREEN_H - 10), 13, COLORS["muted"], center=True)
        else:
            draw_text(self.screen, "LEFT/RIGHT  ·  CHANGE GENERATION", (SCREEN_W // 2, SCREEN_H - 10), 13, COLORS["muted"], center=True)

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


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Run the visual AI ping-pong frontend"
    )
    parser.add_argument("--model-path", type=Path, default=None)
    parser.add_argument("--generations-path", type=Path, default=None)
    return parser


def _resolve_artifact_path(path, canonical_path):
    if path is None:
        return PROJECT_ROOT / canonical_path
    if path.is_absolute():
        return path
    return INVOCATION_CWD / path


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    model_path = _resolve_artifact_path(
        args.model_path,
        Path("models/best_bot.json"),
    )
    generations_path = _resolve_artifact_path(
        args.generations_path,
        Path("logs/generations.csv"),
    )

    try:
        best_genome = load_best_genome(model_path)
        generation_records = load_generation_history(generations_path)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    if best_genome != generation_records[-1].genome:
        parser.error(
            "best model genome does not match the final generation champion"
        )

    Game(best_genome, generation_records).run()


if __name__ == "__main__":
    main()
