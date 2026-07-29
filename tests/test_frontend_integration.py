import hashlib
import io
import json
import random
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pygame

from ga.artifacts import GenerationRecord
from ga.genome import BotGenome
from game.controllers import BotController, HumanController
from game.main import BOTVBOT, HUMAN, MENU, Game, main
from game.utils import COLORS, COURT_H, COURT_Y, SCREEN_H, SCREEN_W

BASELINE_GENOME = BotGenome(260.0, 0.0, 8.0)
GENERATION_ONE_GENOME = BotGenome(300.0, 0.1, 12.0)
BEST_GENOME = BotGenome(320.0, 0.05, 8.0)
GENERATION_RECORDS = (
    GenerationRecord(
        generation=0,
        best_fitness=10.5,
        mean_fitness=2.25,
        worst_fitness=-5.0,
        genome=BASELINE_GENOME,
    ),
    GenerationRecord(
        generation=1,
        best_fitness=20.0,
        mean_fitness=12.75,
        worst_fitness=1.5,
        genome=BEST_GENOME,
    ),
)


def create_game(best_genome=BEST_GENOME, records=GENERATION_RECORDS):
    surface = pygame.Surface((SCREEN_W, SCREEN_H))
    with patch("game.main.pygame.init"), patch(
        "game.main.pygame.display.set_caption"
    ), patch(
        "game.main.pygame.display.set_mode",
        return_value=surface,
    ), patch(
        "game.main.pygame.time.Clock",
        return_value=MagicMock(),
    ):
        return Game(best_genome, records)


class GameValidationTests(unittest.TestCase):
    def _assert_rejected_before_pygame(
        self,
        exception_type,
        message,
        best_genome,
        records,
    ):
        with patch("game.main.pygame.init") as pygame_init, patch(
            "game.main.pygame.display.set_caption"
        ) as set_caption, patch(
            "game.main.pygame.display.set_mode"
        ) as set_mode, patch(
            "game.main.pygame.time.Clock"
        ) as clock:
            with self.assertRaisesRegex(exception_type, message):
                Game(best_genome, records)

        pygame_init.assert_not_called()
        set_caption.assert_not_called()
        set_mode.assert_not_called()
        clock.assert_not_called()

    def test_best_genome_must_be_bot_genome(self):
        self._assert_rejected_before_pygame(
            TypeError,
            "best_genome must be a BotGenome",
            BEST_GENOME.to_dict(),
            GENERATION_RECORDS,
        )

    def test_generation_records_must_be_iterable(self):
        self._assert_rejected_before_pygame(
            TypeError,
            "generation_records must be an iterable",
            BEST_GENOME,
            None,
        )

    def test_generation_records_must_not_be_empty(self):
        self._assert_rejected_before_pygame(
            ValueError,
            "generation_records must not be empty",
            BEST_GENOME,
            (),
        )

    def test_every_generation_record_must_have_the_expected_type(self):
        self._assert_rejected_before_pygame(
            TypeError,
            "generation_records must contain only GenerationRecord values",
            BEST_GENOME,
            (GENERATION_RECORDS[0], BEST_GENOME),
        )


class FrontendControllerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.random_state = random.getstate()
        random.seed(20260728)
        self.game = create_game()

    def tearDown(self):
        random.setstate(self.random_state)

    def test_human_mode_uses_exact_saved_best_genome(self):
        self.game.start(HUMAN)

        self.assertIsInstance(self.game.left_controller, HumanController)
        self.assertIsInstance(self.game.right_controller, BotController)
        self.assertIs(self.game.right_controller.genome, BEST_GENOME)
        self.assertNotEqual(self.game.right_controller.genome, BASELINE_GENOME)

    def test_bot_vs_bot_starts_with_two_independent_generation_zero_bots(self):
        self.game.start(BOTVBOT)

        self.assertEqual(
            (
                self.game.left_generation_index,
                self.game.right_generation_index,
            ),
            (0, 0),
        )
        self.assertIsInstance(self.game.left_controller, BotController)
        self.assertIsInstance(self.game.right_controller, BotController)
        self.assertIsNot(
            self.game.left_controller,
            self.game.right_controller,
        )
        self.assertIs(
            self.game.left_controller.genome,
            GENERATION_RECORDS[0].genome,
        )
        self.assertIs(
            self.game.right_controller.genome,
            GENERATION_RECORDS[0].genome,
        )
        self.assertIsNone(self.game.left_controller.target_y)
        self.assertIsNone(self.game.right_controller.target_y)

    def test_left_and_right_generations_change_independently(self):
        self.game.start(BOTVBOT)

        self.game.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d)
        )

        self.assertEqual(
            (
                self.game.left_generation_index,
                self.game.right_generation_index,
            ),
            (1, 0),
        )
        self.assertIs(
            self.game.left_controller.genome,
            GENERATION_RECORDS[1].genome,
        )
        self.assertIs(
            self.game.right_controller.genome,
            GENERATION_RECORDS[0].genome,
        )

        self.game.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
        )

        self.assertEqual(
            (
                self.game.left_generation_index,
                self.game.right_generation_index,
            ),
            (1, 1),
        )
        self.assertIs(
            self.game.left_controller.genome,
            GENERATION_RECORDS[1].genome,
        )
        self.assertIs(
            self.game.right_controller.genome,
            GENERATION_RECORDS[1].genome,
        )

        self.game.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a)
        )
        self.game.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT)
        )

        self.assertEqual(
            (
                self.game.left_generation_index,
                self.game.right_generation_index,
            ),
            (0, 0),
        )

    def test_generation_boundaries_do_not_wrap_or_reset(self):
        self.game.start(BOTVBOT)
        self.game.change_ball_speed(1)
        self.game.difficulty.elapsed = 7.5
        initial_controllers = (
            self.game.left_controller,
            self.game.right_controller,
        )
        initial_ball = self.game.ball
        self.game.simulation.score1 = 3
        initial_difficulty = (
            self.game.difficulty.ball_speed_multiplier,
            self.game.difficulty.paddle_height,
            self.game.difficulty.auto_enabled,
            self.game.difficulty.elapsed,
        )

        self.game.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a)
        )

        self.assertEqual(self.game.left_generation_index, 0)
        self.assertEqual(self.game.score1, 3)
        self.assertIs(self.game.ball, initial_ball)
        self.assertEqual(
            (self.game.left_controller, self.game.right_controller),
            initial_controllers,
        )
        self.assertEqual(
            (
                self.game.difficulty.ball_speed_multiplier,
                self.game.difficulty.paddle_height,
                self.game.difficulty.auto_enabled,
                self.game.difficulty.elapsed,
            ),
            initial_difficulty,
        )

        self.game.change_generation("left", 1)
        self.game.change_generation("right", 1)
        self.game.change_paddle_size(-1)
        self.game.difficulty.elapsed = 6.0
        last_controllers = (
            self.game.left_controller,
            self.game.right_controller,
        )
        last_ball = self.game.ball
        self.game.simulation.score2 = 4

        self.game.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d)
        )
        self.game.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
        )

        self.assertEqual(
            (
                self.game.left_generation_index,
                self.game.right_generation_index,
            ),
            (1, 1),
        )
        self.assertEqual(self.game.score2, 4)
        self.assertIs(self.game.ball, last_ball)
        self.assertEqual(
            (self.game.left_controller, self.game.right_controller),
            last_controllers,
        )
        self.assertEqual(self.game.difficulty.paddle_height, 85)
        self.assertEqual(self.game.difficulty.elapsed, 6.0)

    def test_actual_generation_change_resets_existing_simulation_and_controllers(self):
        self.game.start(BOTVBOT)
        simulation = self.game.simulation
        old_entities = (self.game.p1, self.game.p2, self.game.ball)
        old_controllers = (
            self.game.left_controller,
            self.game.right_controller,
        )
        simulation.score1 = 2
        simulation.score2 = 1

        self.game.change_ball_speed(2)
        self.game.change_paddle_size(-2)
        self.game.set_auto_difficulty(False)
        self.game.difficulty.elapsed = 9.0
        self.game.change_generation("right", 1)

        self.assertIs(self.game.simulation, simulation)
        self.assertEqual(
            (
                self.game.left_generation_index,
                self.game.right_generation_index,
            ),
            (0, 1),
        )
        self.assertEqual((self.game.score1, self.game.score2), (0, 0))
        self.assertTrue(
            all(
                new is not old
                for new, old in zip(
                    (self.game.p1, self.game.p2, self.game.ball),
                    old_entities,
                )
            )
        )
        self.assertIsNot(self.game.left_controller, old_controllers[0])
        self.assertIsNot(self.game.right_controller, old_controllers[1])
        self.assertIsNot(
            self.game.left_controller,
            self.game.right_controller,
        )
        self.assertIsNone(self.game.left_controller.target_y)
        self.assertIsNone(self.game.right_controller.target_y)
        self.assertEqual(
            (
                self.game.difficulty.ball_speed_multiplier,
                self.game.difficulty.paddle_height,
                self.game.difficulty.auto_enabled,
                self.game.difficulty.elapsed,
            ),
            (1.0, 90, True, 0.0),
        )
        self.assertIs(
            self.game.left_controller.genome,
            GENERATION_RECORDS[0].genome,
        )
        self.assertIs(
            self.game.right_controller.genome,
            GENERATION_RECORDS[1].genome,
        )

    def test_reentering_bot_vs_bot_starts_from_generation_zero(self):
        self.game.start(BOTVBOT)
        self.game.change_generation("left", 1)
        self.game.change_generation("right", 1)
        self.game.change_ball_speed(1)
        self.assertEqual(
            (
                self.game.left_generation_index,
                self.game.right_generation_index,
            ),
            (1, 1),
        )

        self.game.state = MENU
        self.game.start(BOTVBOT)

        self.assertEqual(
            (
                self.game.left_generation_index,
                self.game.right_generation_index,
            ),
            (0, 0),
        )
        self.assertEqual(
            (
                self.game.difficulty.ball_speed_multiplier,
                self.game.difficulty.paddle_height,
                self.game.difficulty.auto_enabled,
                self.game.difficulty.elapsed,
            ),
            (1.0, 90, True, 0.0),
        )
        self.assertIs(
            self.game.left_controller.genome,
            GENERATION_RECORDS[0].genome,
        )

    def test_generation_keys_are_ignored_outside_bot_vs_bot(self):
        menu_ball = self.game.ball
        self.game.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
        )
        self.assertEqual(self.game.state, MENU)
        self.assertIs(self.game.ball, menu_ball)

        self.game.start(HUMAN)
        human_ball = self.game.ball
        controllers = (
            self.game.left_controller,
            self.game.right_controller,
        )
        self.game.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
        )

        self.assertEqual(self.game.state, HUMAN)
        self.assertIs(self.game.ball, human_ball)
        self.assertEqual(
            (self.game.left_controller, self.game.right_controller),
            controllers,
        )

    def test_change_generation_rejects_invalid_side(self):
        self.game.start(BOTVBOT)

        with self.assertRaisesRegex(
            ValueError,
            "side must be 'left' or 'right'",
        ):
            self.game.change_generation("center", 1)

    def test_manual_speed_change_preserves_active_match(self):
        self.game.start(HUMAN)
        self.game.simulation.score1 = 3
        self.game.simulation.score2 = 2
        self.game.difficulty.elapsed = 7.5
        entities = (self.game.p1, self.game.p2, self.game.ball)
        controllers = (
            self.game.left_controller,
            self.game.right_controller,
        )
        positions = (
            self.game.p1.y,
            self.game.p2.y,
            self.game.ball.x,
            self.game.ball.y,
        )
        velocities = (self.game.ball.vx, self.game.ball.vy)

        self.assertTrue(self.game.change_ball_speed(1))

        self.assertEqual((self.game.score1, self.game.score2), (3, 2))
        self.assertEqual(
            (self.game.p1, self.game.p2, self.game.ball),
            entities,
        )
        self.assertEqual(
            (self.game.left_controller, self.game.right_controller),
            controllers,
        )
        self.assertEqual(
            (
                self.game.p1.y,
                self.game.p2.y,
                self.game.ball.x,
                self.game.ball.y,
            ),
            positions,
        )
        self.assertAlmostEqual(
            self.game.ball.vx,
            velocities[0] * 1.1,
        )
        self.assertAlmostEqual(
            self.game.ball.vy,
            velocities[1] * 1.1,
        )
        self.assertEqual(self.game.difficulty.elapsed, 7.5)

    def test_manual_paddle_change_preserves_match_and_clamps(self):
        self.game.start(BOTVBOT)
        self.game.simulation.score1 = 2
        self.game.p1.y = COURT_Y + 45
        ball = self.game.ball
        controllers = (
            self.game.left_controller,
            self.game.right_controller,
        )

        self.assertTrue(self.game.change_paddle_size(1))

        self.assertEqual(self.game.score1, 2)
        self.assertIs(self.game.ball, ball)
        self.assertEqual(
            (self.game.left_controller, self.game.right_controller),
            controllers,
        )
        self.assertEqual(self.game.p1.height, 95)
        self.assertEqual(self.game.p2.height, 95)
        self.assertEqual(self.game.p1.y, COURT_Y + 47.5)

    def test_auto_difficulty_applies_after_simulation_and_catches_up(self):
        self.game.start(BOTVBOT)
        events = []
        difficulty = self.game.difficulty

        def record_step(dt):
            events.append("simulation-step")
            return None

        class RecordingDifficulty:
            def __getattr__(self, name):
                return getattr(difficulty, name)

            def update(self, dt):
                events.append("difficulty-update")
                return difficulty.update(dt)

        self.game.difficulty = RecordingDifficulty()

        with patch.object(
            self.game.left_controller,
            "update",
        ), patch.object(
            self.game.right_controller,
            "update",
        ), patch.object(
            self.game.simulation,
            "step",
            side_effect=record_step,
        ):
            self.game.update(45.0)

        self.assertEqual(events, ["simulation-step", "difficulty-update"])
        self.assertEqual(
            self.game.difficulty.ball_speed_multiplier,
            1.2,
        )
        self.assertEqual(self.game.difficulty.paddle_height, 80)
        self.assertEqual(self.game.difficulty.elapsed, 5.0)
        self.assertEqual(self.game.ball.speed_multiplier, 1.2)
        self.assertEqual((self.game.p1.height, self.game.p2.height), (80, 80))

    def test_auto_off_pauses_game_progression(self):
        self.game.start(HUMAN)
        self.game.difficulty.elapsed = 12.0
        self.game.set_auto_difficulty(False)

        with patch.object(
            self.game.left_controller,
            "update",
        ), patch.object(
            self.game.right_controller,
            "update",
        ), patch.object(
            self.game.simulation,
            "step",
        ):
            self.game.update(100.0)

        self.assertEqual(self.game.difficulty.elapsed, 12.0)
        self.assertEqual(
            self.game.difficulty.ball_speed_multiplier,
            1.0,
        )
        self.assertEqual(self.game.difficulty.paddle_height, 90)

    def test_menu_does_not_advance_auto_timer(self):
        self.game.start(HUMAN)
        self.game.difficulty.elapsed = 6.0
        self.game.state = MENU

        self.game.update(100.0)

        self.assertEqual(self.game.difficulty.elapsed, 6.0)
        self.assertEqual(
            self.game.difficulty.ball_speed_multiplier,
            1.0,
        )
        self.assertEqual(self.game.difficulty.paddle_height, 90)

    def test_mouse_and_keyboard_use_the_same_control_methods(self):
        self.game.start(BOTVBOT)
        left_generation_rect = pygame.Rect(10, 10, 20, 20)
        right_generation_rect = pygame.Rect(40, 10, 20, 20)
        speed_rect = pygame.Rect(70, 10, 20, 20)
        paddle_rect = pygame.Rect(100, 10, 20, 20)
        auto_rect = pygame.Rect(130, 10, 20, 20)
        self.game.generation_buttons = [
            (left_generation_rect, "left", 1, True),
            (right_generation_rect, "right", 1, True),
        ]
        self.game.difficulty_buttons = [
            (speed_rect, "ball_speed", 1, True),
            (paddle_rect, "paddle_size", -1, True),
            (auto_rect, "auto", None, True),
        ]

        with patch.object(
            self.game,
            "change_generation",
        ) as change_generation, patch.object(
            self.game,
            "change_ball_speed",
        ) as change_ball_speed, patch.object(
            self.game,
            "change_paddle_size",
        ) as change_paddle_size, patch.object(
            self.game,
            "toggle_auto_difficulty",
        ) as toggle_auto:
            self.game.handle_event(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    pos=left_generation_rect.center,
                    button=1,
                )
            )
            self.game.handle_event(
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d)
            )
            self.game.handle_event(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    pos=right_generation_rect.center,
                    button=1,
                )
            )
            self.game.handle_event(
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
            )
            self.game.handle_event(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    pos=speed_rect.center,
                    button=1,
                )
            )
            self.game.handle_event(
                pygame.event.Event(
                    pygame.KEYDOWN,
                    key=pygame.K_EQUALS,
                )
            )
            self.game.handle_event(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    pos=paddle_rect.center,
                    button=1,
                )
            )
            self.game.handle_event(
                pygame.event.Event(
                    pygame.KEYDOWN,
                    key=pygame.K_LEFTBRACKET,
                )
            )
            self.game.handle_event(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    pos=auto_rect.center,
                    button=1,
                )
            )
            self.game.handle_event(
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_t)
            )

        self.assertEqual(
            change_generation.call_args_list,
            [
                call("left", 1),
                call("left", 1),
                call("right", 1),
                call("right", 1),
            ],
        )
        self.assertEqual(
            change_ball_speed.call_args_list,
            [call(1), call(1)],
        )
        self.assertEqual(
            change_paddle_size.call_args_list,
            [call(-1), call(-1)],
        )
        self.assertEqual(toggle_auto.call_count, 2)

    def test_disabled_generation_button_is_a_complete_no_op(self):
        self.game.start(BOTVBOT)
        disabled_rect = pygame.Rect(10, 10, 20, 20)
        self.game.generation_buttons = [
            (disabled_rect, "left", -1, False)
        ]
        self.game.simulation.score1 = 4
        self.game.change_ball_speed(1)
        self.game.difficulty.elapsed = 8.0
        entities = (self.game.p1, self.game.p2, self.game.ball)
        controllers = (
            self.game.left_controller,
            self.game.right_controller,
        )

        with patch.object(
            self.game,
            "change_generation",
        ) as change_generation:
            self.game.handle_event(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    pos=disabled_rect.center,
                    button=1,
                )
            )

        change_generation.assert_not_called()
        self.assertEqual(self.game.score1, 4)
        self.assertEqual(
            (self.game.p1, self.game.p2, self.game.ball),
            entities,
        )
        self.assertEqual(
            (self.game.left_controller, self.game.right_controller),
            controllers,
        )
        self.assertEqual(
            (
                self.game.difficulty.ball_speed_multiplier,
                self.game.difficulty.elapsed,
            ),
            (1.1, 8.0),
        )

    def test_ball_speed_shortcuts_cover_main_and_keypad_keys(self):
        self.game.start(HUMAN)

        with patch.object(
            self.game,
            "change_ball_speed",
        ) as change_ball_speed:
            for key in (
                pygame.K_MINUS,
                pygame.K_KP_MINUS,
                pygame.K_PLUS,
                pygame.K_EQUALS,
                pygame.K_KP_PLUS,
            ):
                self.game.handle_event(
                    pygame.event.Event(pygame.KEYDOWN, key=key)
                )

        self.assertEqual(
            change_ball_speed.call_args_list,
            [
                call(-1),
                call(-1),
                call(1),
                call(1),
                call(1),
            ],
        )

    def test_escape_still_returns_to_menu(self):
        self.game.start(BOTVBOT)

        self.game.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        )

        self.assertEqual(self.game.state, MENU)

    def test_update_order_remains_controller_clamp_controller_clamp_step(self):
        events = []

        class RecordingPaddle:
            def __init__(self, name):
                self.name = name

            def clamp(self, minimum, maximum):
                events.append(f"{self.name}-clamp")

        class RecordingController:
            def __init__(self, name):
                self.name = name

            def update(self, paddle, ball, dt):
                events.append(f"{self.name}-update")

        class RecordingSimulation:
            def __init__(self):
                self.p1 = RecordingPaddle("left")
                self.p2 = RecordingPaddle("right")
                self.ball = object()

            def step(self, dt):
                events.append("simulation-step")

        class RecordingDifficulty:
            def update(self, dt):
                events.append("difficulty-update")
                return 0

        self.game.state = HUMAN
        self.game.simulation = RecordingSimulation()
        self.game.difficulty = RecordingDifficulty()
        self.game.left_controller = RecordingController("left")
        self.game.right_controller = RecordingController("right")

        self.game.update(1 / 60)

        self.assertEqual(
            events,
            [
                "left-update",
                "left-clamp",
                "right-update",
                "right-clamp",
                "simulation-step",
                "difficulty-update",
            ],
        )


class FrontendRenderingTests(unittest.TestCase):
    def setUp(self):
        self.random_state = random.getstate()
        random.seed(20260728)
        self.game = create_game()

    def tearDown(self):
        random.setstate(self.random_state)

    def _drawn_texts(self, draw_text_mock):
        return [draw_call.args[1] for draw_call in draw_text_mock.call_args_list]

    def test_window_caption_omits_visual_frontend_suffix(self):
        surface = pygame.Surface((SCREEN_W, SCREEN_H))
        with patch("game.main.pygame.init"), patch(
            "game.main.pygame.display.set_caption"
        ) as set_caption, patch(
            "game.main.pygame.display.set_mode",
            return_value=surface,
        ), patch(
            "game.main.pygame.time.Clock",
            return_value=MagicMock(),
        ):
            Game(BEST_GENOME, GENERATION_RECORDS)

        set_caption.assert_called_once_with("PONG // EVOLVE")

    def test_menu_text_changes_without_button_geometry_changes(self):
        measurement_font = MagicMock()
        measurement_font.size.side_effect = lambda text: (len(text) * 7, 14)
        with patch("game.main.draw_text") as draw_text_mock, patch(
            "game.main.font",
            return_value=measurement_font,
        ):
            self.game.draw_menu()

        self.assertEqual(
            [rect for rect, _ in self.game.menu_buttons],
            [
                pygame.Rect(118, 250, 320, 130),
                pygame.Rect(462, 250, 320, 130),
            ],
        )
        texts = self._drawn_texts(draw_text_mock)
        self.assertIn("Pick a mode to watch the bot play.", texts)
        self.assertNotIn(
            "Visual frontend - pick a mode to watch the bot play.",
            texts,
        )
        self.assertIn("Play against the saved best bot.", texts)
        self.assertIn("Compare any two generation", texts)
        self.assertIn("champions.", texts)
        esc_call = next(
            draw_call
            for draw_call in draw_text_mock.call_args_list
            if draw_call.args[1] == "ESC"
        )
        footer_call = next(
            draw_call
            for draw_call in draw_text_mock.call_args_list
            if draw_call.args[1] == " returns to this menu during a match"
        )
        self.assertEqual(esc_call.args[4], COLORS["cyan"])
        self.assertTrue(esc_call.kwargs["bold"])
        self.assertEqual(footer_call.args[4], COLORS["muted"])
        self.assertFalse(footer_call.kwargs.get("bold", False))

    def test_human_hud_labels_saved_best_bot(self):
        self.game.start(HUMAN)

        with patch("game.main.draw_text") as draw_text_mock:
            self.game.draw_hud()

        texts = self._drawn_texts(draw_text_mock)
        self.assertIn("YOU", texts)
        self.assertIn("BEST BOT", texts)
        self.assertIn("HUMAN VS BOT", texts)

    def test_bot_hud_shows_independent_generations_and_fitness(self):
        self.game.start(BOTVBOT)
        self.game.change_generation("left", 1)

        with patch("game.main.draw_text") as draw_text_mock:
            self.game.draw_hud()

        texts = self._drawn_texts(draw_text_mock)
        self.assertIn("GEN 1", texts)
        self.assertIn("GEN 0", texts)
        self.assertIn("TRAIN FITNESS 20.0", texts)
        self.assertIn("TRAIN FITNESS 10.5", texts)
        self.assertIn("BOT VS BOT", texts)
        self.assertEqual(
            [
                (side, offset, enabled)
                for _, side, offset, enabled
                in self.game.generation_buttons
            ],
            [
                ("left", -1, True),
                ("left", 1, False),
                ("right", -1, False),
                ("right", 1, True),
            ],
        )

    def test_difficulty_panel_shows_values_and_mode_shortcuts(self):
        for state, expected in (
            (
                HUMAN,
                "−/+ BALL SPEED · [/] PADDLE SIZE · "
                "T AUTO · W/S OR MOUSE MOVE",
            ),
            (
                BOTVBOT,
                "A/D LEFT GEN · ←/→ RIGHT GEN · "
                "−/+ SPEED · [/] SIZE · T AUTO",
            ),
        ):
            with self.subTest(state=state):
                self.game.start(state)
                with patch("game.main.draw_text") as draw_text_mock:
                    self.game.draw_difficulty_panel()

                texts = self._drawn_texts(draw_text_mock)
                self.assertIn("BALL SPEED", texts)
                self.assertIn("x1.00", texts)
                self.assertIn("PADDLE SIZE", texts)
                self.assertIn("90 px", texts)
                self.assertIn("AUTO", texts)
                self.assertIn("ON", texts)
                self.assertIn(expected, texts)
                self.assertEqual(len(self.game.difficulty_buttons), 5)


class FrontendCliTests(unittest.TestCase):
    def _run_main(
        self,
        arguments,
        *,
        project_root,
        invocation_cwd,
        best_genome=BEST_GENOME,
        records=GENERATION_RECORDS,
    ):
        with patch(
            "game.main.PROJECT_ROOT",
            project_root,
        ), patch(
            "game.main.INVOCATION_CWD",
            invocation_cwd,
        ), patch(
            "game.main.load_best_genome",
            return_value=best_genome,
        ) as model_loader, patch(
            "game.main.load_generation_history",
            return_value=records,
        ) as history_loader, patch(
            "game.main.Game",
        ) as game_class:
            main(arguments)

        return model_loader, history_loader, game_class

    def test_defaults_use_canonical_project_paths_and_exact_loaded_objects(self):
        with tempfile.TemporaryDirectory() as project_directory:
            with tempfile.TemporaryDirectory() as invocation_directory:
                project_root = Path(project_directory)
                invocation_cwd = Path(invocation_directory)

                model_loader, history_loader, game_class = self._run_main(
                    [],
                    project_root=project_root,
                    invocation_cwd=invocation_cwd,
                )

        model_loader.assert_called_once_with(
            project_root / "models" / "best_bot.json"
        )
        history_loader.assert_called_once_with(
            project_root / "logs" / "generations.csv"
        )
        game_class.assert_called_once_with(BEST_GENOME, GENERATION_RECORDS)
        game_class.return_value.run.assert_called_once_with()

    def test_explicit_relative_paths_use_invocation_cwd(self):
        with tempfile.TemporaryDirectory() as project_directory:
            with tempfile.TemporaryDirectory() as invocation_directory:
                project_root = Path(project_directory)
                invocation_cwd = Path(invocation_directory)

                model_loader, history_loader, _ = self._run_main(
                    [
                        "--model-path",
                        "models/best_bot.json",
                        "--generations-path",
                        "logs/generations.csv",
                    ],
                    project_root=project_root,
                    invocation_cwd=invocation_cwd,
                )

        model_loader.assert_called_once_with(
            invocation_cwd / "models" / "best_bot.json"
        )
        history_loader.assert_called_once_with(
            invocation_cwd / "logs" / "generations.csv"
        )

    def test_absolute_paths_are_not_rebased(self):
        with tempfile.TemporaryDirectory() as project_directory:
            with tempfile.TemporaryDirectory() as invocation_directory:
                with tempfile.TemporaryDirectory() as output_directory:
                    project_root = Path(project_directory)
                    invocation_cwd = Path(invocation_directory)
                    model_path = Path(output_directory) / "model.json"
                    history_path = Path(output_directory) / "history.csv"

                    model_loader, history_loader, _ = self._run_main(
                        [
                            "--model-path",
                            str(model_path),
                            "--generations-path",
                            str(history_path),
                        ],
                        project_root=project_root,
                        invocation_cwd=invocation_cwd,
                    )

        model_loader.assert_called_once_with(model_path)
        history_loader.assert_called_once_with(history_path)

    def test_loading_error_becomes_argparse_error_without_game_or_traceback(self):
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch(
                "game.main.PROJECT_ROOT",
                root,
            ), patch(
                "game.main.INVOCATION_CWD",
                root,
            ), patch(
                "game.main.load_best_genome",
                side_effect=ValueError("invalid model"),
            ), patch(
                "game.main.Game",
            ) as game_class, redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as raised:
                    main([])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("error: invalid model", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())
        game_class.assert_not_called()

    def test_mismatched_model_and_history_are_rejected_before_game(self):
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch(
                "game.main.PROJECT_ROOT",
                root,
            ), patch(
                "game.main.INVOCATION_CWD",
                root,
            ), patch(
                "game.main.load_best_genome",
                return_value=GENERATION_ONE_GENOME,
            ), patch(
                "game.main.load_generation_history",
                return_value=GENERATION_RECORDS,
            ), patch(
                "game.main.Game",
            ) as game_class, redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as raised:
                    main([])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn(
            "best model genome does not match the final generation champion",
            stderr.getvalue(),
        )
        self.assertNotIn("Traceback", stderr.getvalue())
        game_class.assert_not_called()


class FrontendTraceRegressionTests(unittest.TestCase):
    def test_baseline_fixture_preserves_original_bot_vs_bot_trace(self):
        random_state = random.getstate()
        try:
            random.seed(20260728)
            baseline_record = GenerationRecord(
                generation=0,
                best_fitness=0.0,
                mean_fitness=0.0,
                worst_fitness=0.0,
                genome=BASELINE_GENOME,
            )
            game = create_game(BASELINE_GENOME, (baseline_record,))
            game.start(BOTVBOT)
            game.set_auto_difficulty(False)

            def snapshot(step):
                return {
                    "ball": {
                        "vx": game.ball.vx,
                        "vy": game.ball.vy,
                        "x": game.ball.x,
                        "y": game.ball.y,
                    },
                    "game_state": game.state,
                    "p1_y": game.p1.y,
                    "p2_y": game.p2.y,
                    "score1": game.score1,
                    "score2": game.score2,
                    "step": step,
                }

            states = [snapshot(0)]
            for step in range(1, 3601):
                game.update(1 / 60)
                if step % 60 == 0:
                    states.append(snapshot(step))

            payload = {
                "config": {
                    "commit": "71916ef",
                    "dt": 1 / 60,
                    "sample_every": 60,
                    "seed": 20260728,
                    "steps": 3600,
                },
                "states": states,
            }
            trace = (
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
        finally:
            random.setstate(random_state)

        self.assertEqual(
            hashlib.sha256(trace.encode("utf-8")).hexdigest().upper(),
            "876864848BD0F29AB2F2ADE077F3C740AAA980E4F682018CC3DDE84297DB54FA",
        )


if __name__ == "__main__":
    unittest.main()
