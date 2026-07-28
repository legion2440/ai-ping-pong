import unittest

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


if __name__ == "__main__":
    unittest.main()
