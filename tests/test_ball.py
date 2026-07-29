import random
import unittest
from unittest.mock import patch

from game.ball import Ball


class BallRandomnessTests(unittest.TestCase):
    def test_same_seed_produces_same_serve_sequence(self):
        first = Ball(0, 0, rng=random.Random(20260728))
        second = Ball(0, 0, rng=random.Random(20260728))

        first_serves = []
        second_serves = []
        for _ in range(4):
            first.reset(10, 20)
            second.reset(10, 20)
            first_serves.append((first.vx, first.vy))
            second_serves.append((second.vx, second.vy))

        self.assertEqual(first_serves, second_serves)

    def test_injected_rng_does_not_change_global_random_state(self):
        global_state = random.getstate()
        ball = Ball(0, 0, rng=random.Random(1234))

        ball.reset(10, 20)
        ball.reset(10, 20)

        self.assertEqual(random.getstate(), global_state)

    def test_rng_none_uses_existing_global_random_module(self):
        ball = Ball(0, 0)

        with patch.object(random, "choice", return_value=-1) as choice, patch.object(
            random,
            "uniform",
            return_value=42.5,
        ) as uniform:
            ball.reset(10, 20)

        choice.assert_called_once_with([-1, 1])
        uniform.assert_called_once_with(-100, 100)
        self.assertEqual((ball.vx, ball.vy), (-260, 42.5))

    def test_sequential_resets_advance_the_same_rng(self):
        seed = 9876
        rng = random.Random(seed)
        reference = random.Random(seed)
        ball = Ball(0, 0, rng=rng)

        for _ in range(3):
            expected_vx = 260 * reference.choice([-1, 1])
            expected_vy = reference.uniform(-100, 100)
            ball.reset(10, 20)
            self.assertEqual((ball.vx, ball.vy), (expected_vx, expected_vy))


class BallRuntimeSpeedTests(unittest.TestCase):
    def test_default_reset_preserves_legacy_types_and_rng_order(self):
        ball_rng = random.Random(20260728)
        expected_rng = random.Random(20260728)
        expected_vx = 260 * expected_rng.choice([-1, 1])
        expected_vy = expected_rng.uniform(-100, 100)
        ball = Ball(0, 0, rng=ball_rng)

        ball.reset(10, 20)

        self.assertEqual(ball.vx, expected_vx)
        self.assertIs(type(ball.vx), int)
        self.assertEqual(ball.vy, expected_vy)
        self.assertEqual(ball.speed_multiplier, 1.0)

    def test_runtime_multiplier_scales_velocity_without_moving_ball(self):
        ball = Ball(10, 20, vx=-260, vy=75)

        self.assertTrue(ball.set_speed_multiplier(1.5))

        self.assertEqual((ball.x, ball.y), (10, 20))
        self.assertEqual((ball.vx, ball.vy), (-390.0, 112.5))
        self.assertEqual(ball.speed_multiplier, 1.5)
        self.assertFalse(ball.set_speed_multiplier(1.5))

    def test_reset_uses_current_runtime_multiplier(self):
        ball_rng = random.Random(20260728)
        expected_rng = random.Random(20260728)
        direction = expected_rng.choice([-1, 1])
        vertical_speed = expected_rng.uniform(-100, 100)
        ball = Ball(0, 0, rng=ball_rng, speed_multiplier=1.5)

        ball.reset(10, 20)

        self.assertEqual(ball.vx, 260 * direction * 1.5)
        self.assertEqual(ball.vy, vertical_speed * 1.5)

    def test_scaled_bounce_uses_scaled_caps_and_vertical_impulse(self):
        ball = Ball(
            10,
            120,
            vx=2000,
            vy=1000,
            speed_multiplier=2.0,
        )

        ball.bounce_off_paddle(100, -1)

        self.assertEqual(ball.vx, -1360.0)
        self.assertEqual(ball.vy, 840.0)

    def test_invalid_runtime_multiplier_is_rejected(self):
        for value, exception_type in (
            (True, TypeError),
            ("1.0", TypeError),
            (0, ValueError),
            (-1, ValueError),
            (float("nan"), ValueError),
            (float("inf"), ValueError),
        ):
            with self.subTest(value=value):
                with self.assertRaises(exception_type):
                    Ball(0, 0, speed_multiplier=value)


if __name__ == "__main__":
    unittest.main()
