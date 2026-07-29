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
from .difficulty import (
    BALL_SPEED_MAX,
    BALL_SPEED_MIN,
    DifficultyState,
    PADDLE_HEIGHT_MAX,
    PADDLE_HEIGHT_MIN,
)
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
    clear_font_cache,
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
        self.left_generation_index = 0
        self.right_generation_index = 0
        self.difficulty = DifficultyState()

        pygame.init()
        clear_font_cache()
        pygame.display.set_caption("PONG // EVOLVE")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()

        self.state = MENU
        self.menu_buttons = []
        self.generation_buttons = []
        self.difficulty_buttons = []
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
            self.left_generation_index = 0
            self.right_generation_index = 0
        self.difficulty.reset()
        self._reset_court()

        if state == HUMAN:
            self.left_controller = HumanController()
            self.right_controller = BotController(self.best_genome)
        else:
            self._create_generation_controllers()

        self.left_controller.reset()
        self.right_controller.reset()

    def _create_generation_controllers(self):
        left = self.generation_records[self.left_generation_index]
        right = self.generation_records[self.right_generation_index]
        self.left_controller = BotController(left.genome)
        self.right_controller = BotController(right.genome)

    def change_generation(self, side, offset):
        if side not in ("left", "right"):
            raise ValueError("side must be 'left' or 'right'")
        if isinstance(offset, bool) or not isinstance(offset, int):
            raise TypeError("offset must be an int")
        if self.state != BOTVBOT:
            return False

        attribute = f"{side}_generation_index"
        current_index = getattr(self, attribute)
        new_index = min(
            len(self.generation_records) - 1,
            max(0, current_index + offset),
        )
        if new_index == current_index:
            return False

        setattr(self, attribute, new_index)
        self.difficulty.reset()
        self._reset_court()
        self._create_generation_controllers()
        return True

    def set_auto_difficulty(self, enabled):
        return self.difficulty.set_auto(enabled)

    def toggle_auto_difficulty(self):
        return self.set_auto_difficulty(
            not self.difficulty.auto_enabled
        )

    def change_ball_speed(self, offset):
        if self.state not in (HUMAN, BOTVBOT):
            return False
        if not self.difficulty.adjust_ball_speed(offset):
            return False
        self.ball.set_speed_multiplier(
            self.difficulty.ball_speed_multiplier
        )
        return True

    def change_paddle_size(self, offset):
        if self.state not in (HUMAN, BOTVBOT):
            return False
        if not self.difficulty.adjust_paddle_height(offset):
            return False
        self._apply_paddle_height()
        return True

    def _apply_paddle_height(self):
        for paddle in (self.p1, self.p2):
            paddle.set_height(self.difficulty.paddle_height)
            paddle.clamp(COURT_Y, COURT_Y + COURT_H)

    def _apply_difficulty(self):
        self.ball.set_speed_multiplier(
            self.difficulty.ball_speed_multiplier
        )
        self._apply_paddle_height()

    def _run_difficulty_action(self, action, offset=None):
        if action == "ball_speed":
            return self.change_ball_speed(offset)
        if action == "paddle_size":
            return self.change_paddle_size(offset)
        if action == "auto":
            return self.toggle_auto_difficulty()
        raise ValueError(f"unknown difficulty action: {action}")

    # ---- input -----------------------------------------------------------
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = MENU
                return
            if self.state not in (HUMAN, BOTVBOT):
                return
            if self.state == BOTVBOT:
                if event.key == pygame.K_a:
                    self.change_generation("left", -1)
                elif event.key == pygame.K_d:
                    self.change_generation("left", 1)
                elif event.key == pygame.K_LEFT:
                    self.change_generation("right", -1)
                elif event.key == pygame.K_RIGHT:
                    self.change_generation("right", 1)
            if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.change_ball_speed(-1)
            elif event.key in (
                pygame.K_PLUS,
                pygame.K_EQUALS,
                pygame.K_KP_PLUS,
            ):
                self.change_ball_speed(1)
            elif event.key == pygame.K_LEFTBRACKET:
                self.change_paddle_size(-1)
            elif event.key == pygame.K_RIGHTBRACKET:
                self.change_paddle_size(1)
            elif event.key == pygame.K_t:
                self.toggle_auto_difficulty()

        if (
            event.type == pygame.MOUSEBUTTONDOWN
            and getattr(event, "button", 1) == 1
        ):
            if self.state == MENU:
                for rect, target in self.menu_buttons:
                    if rect.collidepoint(event.pos):
                        self.start(target)
                        return
            elif self.state in (HUMAN, BOTVBOT):
                if self.state == BOTVBOT:
                    for (
                        rect,
                        side,
                        offset,
                        enabled,
                    ) in self.generation_buttons:
                        if enabled and rect.collidepoint(event.pos):
                            self.change_generation(side, offset)
                            return
                for (
                    rect,
                    action,
                    offset,
                    enabled,
                ) in self.difficulty_buttons:
                    if enabled and rect.collidepoint(event.pos):
                        self._run_difficulty_action(action, offset)
                        return

    # ---- update ------------------------------------------------------------
    def update(self, dt):
        if self.state not in (HUMAN, BOTVBOT):
            return

        self.left_controller.update(self.p1, self.ball, dt)
        self.p1.clamp(COURT_Y, COURT_Y + COURT_H)

        self.right_controller.update(self.p2, self.ball, dt)
        self.p2.clamp(COURT_Y, COURT_Y + COURT_H)

        self.simulation.step(dt)
        if self.difficulty.update(dt):
            self._apply_difficulty()

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
                ("Compare any two generation", "champions."),
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

    def _draw_control_button(
        self,
        rect,
        label,
        color,
        enabled=True,
    ):
        border_color = color if enabled else COLORS["border"]
        text_color = color if enabled else COLORS["muted"]
        pygame.draw.rect(
            self.screen,
            COLORS["panel"],
            rect,
            border_radius=3,
        )
        pygame.draw.rect(
            self.screen,
            border_color,
            rect,
            width=1,
            border_radius=3,
        )
        draw_text(
            self.screen,
            label,
            rect.center,
            13,
            text_color,
            bold=enabled,
            center=True,
        )

    def _draw_generation_selector(
        self,
        side,
        center_x,
        record,
        color,
        index,
    ):
        y = 22
        previous_rect = pygame.Rect(center_x - 92, y, 28, 24)
        next_rect = pygame.Rect(center_x + 64, y, 28, 24)
        previous_enabled = index > 0
        next_enabled = index < len(self.generation_records) - 1

        self._draw_control_button(
            previous_rect,
            "◀",
            color,
            previous_enabled,
        )
        self._draw_control_button(
            next_rect,
            "▶",
            color,
            next_enabled,
        )
        draw_text(
            self.screen,
            f"GEN {record.generation}",
            (center_x, y + 12),
            13,
            COLORS["text"],
            bold=True,
            center=True,
        )
        draw_text(
            self.screen,
            f"TRAIN FITNESS {record.best_fitness}",
            (center_x, 61),
            11,
            COLORS["muted"],
            center=True,
        )
        self.generation_buttons.extend(
            (
                (
                    previous_rect,
                    side,
                    -1,
                    previous_enabled,
                ),
                (
                    next_rect,
                    side,
                    1,
                    next_enabled,
                ),
            )
        )

    def draw_hud(self):
        s = self.screen
        self.generation_buttons = []
        if self.state == HUMAN:
            p1_label = "YOU"
            p2_label = "BEST BOT"
            mode_label = "HUMAN VS BOT"
            draw_text(
                s,
                p1_label,
                (COURT_X + 40, 45),
                12,
                COLORS["muted"],
            )
            draw_text(
                s,
                p2_label,
                (COURT_X + COURT_W - 90, 45),
                12,
                COLORS["muted"],
            )
        else:
            left = self.generation_records[
                self.left_generation_index
            ]
            right = self.generation_records[
                self.right_generation_index
            ]
            mode_label = "BOT VS BOT"
            self._draw_generation_selector(
                "left",
                145,
                left,
                COLORS["cyan"],
                self.left_generation_index,
            )
            self._draw_generation_selector(
                "right",
                SCREEN_W - 145,
                right,
                COLORS["lime"],
                self.right_generation_index,
            )

        draw_text(
            s,
            str(self.score1),
            (COURT_X + 40, 78),
            30,
            COLORS["cyan"],
            bold=True,
        )
        draw_text(
            s,
            mode_label,
            (SCREEN_W // 2, 40),
            15,
            COLORS["muted"],
            center=True,
        )
        draw_text(
            s,
            str(self.score2),
            (COURT_X + COURT_W - 60, 78),
            30,
            COLORS["lime"],
            bold=True,
        )

    def draw_difficulty_panel(self):
        panel = pygame.Rect(
            COURT_X,
            COURT_Y + COURT_H + 10,
            COURT_W,
            52,
        )
        pygame.draw.rect(
            self.screen,
            COLORS["panel"],
            panel,
            border_radius=4,
        )
        pygame.draw.rect(
            self.screen,
            COLORS["border"],
            panel,
            width=1,
            border_radius=4,
        )

        button_y = panel.y + 12
        button_size = (28, 24)
        self.difficulty_buttons = []

        draw_text(
            self.screen,
            "BALL SPEED",
            (40, panel.y + 17),
            12,
            COLORS["muted"],
        )
        speed_down = pygame.Rect(130, button_y, *button_size)
        speed_up = pygame.Rect(242, button_y, *button_size)
        speed_down_enabled = (
            self.difficulty.ball_speed_multiplier > BALL_SPEED_MIN
        )
        speed_up_enabled = (
            self.difficulty.ball_speed_multiplier < BALL_SPEED_MAX
        )
        self._draw_control_button(
            speed_down,
            "−",
            COLORS["cyan"],
            speed_down_enabled,
        )
        self._draw_control_button(
            speed_up,
            "+",
            COLORS["cyan"],
            speed_up_enabled,
        )
        draw_text(
            self.screen,
            f"x{self.difficulty.ball_speed_multiplier:.2f}",
            (200, button_y + 12),
            13,
            COLORS["text"],
            bold=True,
            center=True,
        )
        self.difficulty_buttons.extend(
            (
                (
                    speed_down,
                    "ball_speed",
                    -1,
                    speed_down_enabled,
                ),
                (
                    speed_up,
                    "ball_speed",
                    1,
                    speed_up_enabled,
                ),
            )
        )

        draw_text(
            self.screen,
            "PADDLE SIZE",
            (310, panel.y + 17),
            12,
            COLORS["muted"],
        )
        paddle_down = pygame.Rect(416, button_y, *button_size)
        paddle_up = pygame.Rect(530, button_y, *button_size)
        paddle_down_enabled = (
            self.difficulty.paddle_height > PADDLE_HEIGHT_MIN
        )
        paddle_up_enabled = (
            self.difficulty.paddle_height < PADDLE_HEIGHT_MAX
        )
        self._draw_control_button(
            paddle_down,
            "−",
            COLORS["lime"],
            paddle_down_enabled,
        )
        self._draw_control_button(
            paddle_up,
            "+",
            COLORS["lime"],
            paddle_up_enabled,
        )
        draw_text(
            self.screen,
            f"{self.difficulty.paddle_height} px",
            (488, button_y + 12),
            13,
            COLORS["text"],
            bold=True,
            center=True,
        )
        self.difficulty_buttons.extend(
            (
                (
                    paddle_down,
                    "paddle_size",
                    -1,
                    paddle_down_enabled,
                ),
                (
                    paddle_up,
                    "paddle_size",
                    1,
                    paddle_up_enabled,
                ),
            )
        )

        draw_text(
            self.screen,
            "AUTO",
            (615, panel.y + 17),
            12,
            COLORS["muted"],
        )
        auto_rect = pygame.Rect(665, button_y, 76, 24)
        self._draw_control_button(
            auto_rect,
            "ON" if self.difficulty.auto_enabled else "OFF",
            COLORS["magenta"],
        )
        self.difficulty_buttons.append(
            (auto_rect, "auto", None, True)
        )

        if self.state == HUMAN:
            legend = (
                "−/+ BALL SPEED · [/] PADDLE SIZE · "
                "T AUTO · W/S OR MOUSE MOVE"
            )
        else:
            legend = (
                "A/D LEFT GEN · ←/→ RIGHT GEN · "
                "−/+ SPEED · [/] SIZE · T AUTO"
            )
        draw_text(
            self.screen,
            legend,
            (SCREEN_W // 2, SCREEN_H - 10),
            10,
            COLORS["muted"],
            center=True,
        )

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
        self.draw_difficulty_panel()

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
