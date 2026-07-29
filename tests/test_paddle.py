import unittest

import pygame

from game.paddle import Paddle


class PaddleTrackingTests(unittest.TestCase):
    def test_track_does_not_cross_threshold_boundary(self):
        for target_y, expected_y in ((120, 112), (80, 88)):
            with self.subTest(target_y=target_y):
                paddle = Paddle(0, 100, (0, 0, 0))

                paddle.track(target_y, speed_cap=1000, dt=1, threshold=8)

                self.assertEqual(paddle.y, expected_y)
                self.assertEqual(abs(target_y - paddle.y), 8)

                paddle.track(target_y, speed_cap=1000, dt=1, threshold=8)
                self.assertEqual(paddle.y, expected_y)

    def test_track_reduces_last_step_to_remaining_distance(self):
        paddle = Paddle(0, 100, (0, 0, 0))

        paddle.track(120, speed_cap=10, dt=1, threshold=8)
        self.assertEqual(paddle.y, 110)

        before_last_step = paddle.y
        paddle.track(120, speed_cap=10, dt=1, threshold=8)

        self.assertEqual(paddle.y - before_last_step, 2)
        self.assertEqual(paddle.y, 112)
        self.assertEqual(abs(120 - paddle.y), 8)


class PaddleHeightTests(unittest.TestCase):
    def test_default_height_preserves_existing_geometry(self):
        paddle = Paddle(50, 100, (0, 0, 0))

        self.assertEqual(paddle.height, 90)
        self.assertEqual(paddle.rect(), pygame.Rect(43, 55, 14, 90))

    def test_custom_height_is_used_by_rect_and_clamp(self):
        paddle = Paddle(50, 100, (0, 0, 0), height=50)

        self.assertEqual(paddle.rect(), pygame.Rect(43, 75, 14, 50))
        paddle.y = 10
        paddle.clamp(20, 200)
        self.assertEqual(paddle.y, 45)
        paddle.y = 190
        paddle.clamp(20, 200)
        self.assertEqual(paddle.y, 175)

    def test_set_height_preserves_center_until_explicit_clamp(self):
        paddle = Paddle(50, 65, (0, 0, 0))

        self.assertTrue(paddle.set_height(120))
        self.assertEqual(paddle.y, 65)
        paddle.clamp(20, 200)
        self.assertEqual(paddle.y, 80)
        self.assertFalse(paddle.set_height(120))

    def test_invalid_height_is_rejected(self):
        for value, exception_type in (
            (True, TypeError),
            (50.0, TypeError),
            (0, ValueError),
            (-1, ValueError),
        ):
            with self.subTest(value=value):
                with self.assertRaises(exception_type):
                    Paddle(0, 0, (0, 0, 0), height=value)


if __name__ == "__main__":
    unittest.main()
