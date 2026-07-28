import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pygame

from ga.genome import BotGenome
from game.controllers import BaselineController, BotController, HumanController
from game.paddle import Paddle
from game.utils import COURT_X, COURT_Y


class Keys:
    def __init__(self, pressed=()):
        self.pressed = set(pressed)

    def __getitem__(self, key):
        return key in self.pressed


def make_paddle(y=100):
    return Paddle(0, y, (0, 0, 0))


class BotControllerTests(unittest.TestCase):
    def test_baseline_matches_direct_paddle_tracking(self):
        ball = SimpleNamespace(y=180)
        controlled_paddle = make_paddle()
        direct_paddle = make_paddle()
        dt = 1 / 60

        BaselineController().update(controlled_paddle, ball, dt)
        direct_paddle.track(ball.y, 260.0, dt, 8.0)

        self.assertEqual(controlled_paddle.y, direct_paddle.y)

    def test_paddle_speed_changes_movement(self):
        ball = SimpleNamespace(y=300)
        slow_paddle = make_paddle()
        fast_paddle = make_paddle()
        slow = BotController(BotGenome(120.0, 0.0, 0.0))
        fast = BotController(BotGenome(420.0, 0.0, 0.0))

        slow.update(slow_paddle, ball, 0.1)
        fast.update(fast_paddle, ball, 0.1)

        self.assertEqual(slow_paddle.y, 112)
        self.assertEqual(fast_paddle.y, 142)

    def test_movement_threshold_changes_stopping_distance(self):
        ball = SimpleNamespace(y=200)
        exact_paddle = make_paddle()
        distant_paddle = make_paddle()
        exact = BotController(BotGenome(420.0, 0.0, 0.0))
        distant = BotController(BotGenome(420.0, 0.0, 40.0))

        exact.update(exact_paddle, ball, 1)
        distant.update(distant_paddle, ball, 1)

        self.assertEqual(exact_paddle.y, 200)
        self.assertEqual(distant_paddle.y, 160)

    def test_reaction_time_delays_target_updates(self):
        paddle = make_paddle()
        ball = SimpleNamespace(y=150)
        controller = BotController(BotGenome(120.0, 0.20, 0.0))

        controller.update(paddle, ball, 0.05)
        self.assertEqual(paddle.y, 106)
        self.assertEqual(controller.target_y, 150)

        ball.y = 50
        controller.update(paddle, ball, 0.10)
        self.assertEqual(paddle.y, 118)
        self.assertEqual(controller.target_y, 150)

        controller.update(paddle, ball, 0.10)
        self.assertEqual(paddle.y, 106)
        self.assertEqual(controller.target_y, 50)
        self.assertEqual(controller.elapsed_time, 0.0)

    def test_zero_reaction_time_updates_target_every_frame(self):
        paddle = make_paddle()
        ball = SimpleNamespace(y=150)
        controller = BotController(BotGenome(120.0, 0.0, 0.0))

        controller.update(paddle, ball, 0.05)
        self.assertEqual(paddle.y, 106)

        ball.y = 50
        controller.update(paddle, ball, 0.05)
        self.assertEqual(paddle.y, 100)
        self.assertEqual(controller.target_y, 50)

    def test_reset_discards_previous_target_and_timer(self):
        paddle = make_paddle()
        ball = SimpleNamespace(y=150)
        controller = BotController(BotGenome(120.0, 0.30, 0.0))

        controller.update(paddle, ball, 0.05)
        ball.y = 50
        controller.update(paddle, ball, 0.10)
        self.assertEqual(controller.target_y, 150)
        self.assertEqual(controller.elapsed_time, 0.10)

        controller.reset()
        self.assertIsNone(controller.target_y)
        self.assertEqual(controller.elapsed_time, 0.0)

        before_update = paddle.y
        controller.update(paddle, ball, 0.05)
        self.assertLess(paddle.y, before_update)
        self.assertEqual(controller.target_y, 50)

    def test_baseline_controllers_do_not_share_state(self):
        left = BaselineController()
        right = BaselineController()
        left_paddle = make_paddle()
        right_paddle = make_paddle()

        left.update(left_paddle, SimpleNamespace(y=180), 0.1)

        self.assertIsNot(left, right)
        self.assertIsNot(left.genome, right.genome)
        self.assertEqual(left.target_y, 180)
        self.assertIsNone(right.target_y)
        self.assertEqual(right_paddle.y, 100)


class HumanControllerTests(unittest.TestCase):
    def setUp(self):
        self.controller = HumanController()
        self.paddle = make_paddle(COURT_Y + 100)

    def update_with_input(self, keys=(), mouse=(0, 0), dt=0.1):
        with patch.object(
            pygame.key,
            "get_pressed",
            return_value=Keys(keys),
        ), patch.object(pygame.mouse, "get_pos", return_value=mouse):
            self.controller.update(self.paddle, None, dt)

    def test_keyboard_moves_up_and_down(self):
        start_y = self.paddle.y

        for key in (pygame.K_w, pygame.K_UP):
            with self.subTest(direction="up", key=key):
                self.paddle.y = start_y
                self.update_with_input(keys=(key,))
                self.assertLess(self.paddle.y, start_y)

        for key in (pygame.K_s, pygame.K_DOWN):
            with self.subTest(direction="down", key=key):
                self.paddle.y = start_y
                self.update_with_input(keys=(key,))
                self.assertGreater(self.paddle.y, start_y)

    def test_mouse_position_overrides_keyboard_movement(self):
        mouse_y = COURT_Y + 150

        self.update_with_input(
            keys=(pygame.K_w,),
            mouse=(COURT_X + 100, mouse_y),
        )

        self.assertEqual(self.paddle.y, mouse_y)

    def test_mouse_outside_court_does_not_override_position(self):
        start_y = self.paddle.y

        self.update_with_input(mouse=(0, 0))

        self.assertEqual(self.paddle.y, start_y)


if __name__ == "__main__":
    unittest.main()
