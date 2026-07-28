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


if __name__ == "__main__":
    unittest.main()
