import unittest

from game.difficulty import (
    AUTO_INTERVAL,
    BALL_SPEED_DEFAULT,
    BALL_SPEED_MAX,
    BALL_SPEED_MIN,
    DifficultyState,
    PADDLE_HEIGHT_DEFAULT,
    PADDLE_HEIGHT_MAX,
    PADDLE_HEIGHT_MIN,
)


class DifficultyStateTests(unittest.TestCase):
    def test_defaults_and_reset_restore_the_locked_protocol(self):
        state = DifficultyState()

        self.assertEqual(
            (
                state.ball_speed_multiplier,
                state.paddle_height,
                state.auto_enabled,
                state.elapsed,
            ),
            (
                BALL_SPEED_DEFAULT,
                PADDLE_HEIGHT_DEFAULT,
                False,
                0.0,
            ),
        )

        state.adjust_ball_speed(3)
        state.adjust_paddle_height(-4)
        state.set_auto(True)
        state.elapsed = 7.5
        state.reset()

        self.assertEqual(
            (
                state.ball_speed_multiplier,
                state.paddle_height,
                state.auto_enabled,
                state.elapsed,
            ),
            (
                BALL_SPEED_DEFAULT,
                PADDLE_HEIGHT_DEFAULT,
                False,
                0.0,
            ),
        )

    def test_manual_adjustments_are_clamped_without_float_drift(self):
        state = DifficultyState()

        for _ in range(20):
            state.adjust_ball_speed(1)
            state.adjust_paddle_height(-1)

        self.assertEqual(state.ball_speed_multiplier, BALL_SPEED_MAX)
        self.assertEqual(state.paddle_height, PADDLE_HEIGHT_MIN)
        self.assertFalse(state.adjust_ball_speed(1))
        self.assertFalse(state.adjust_paddle_height(-1))

        for _ in range(20):
            state.adjust_ball_speed(-1)
            state.adjust_paddle_height(1)

        self.assertEqual(state.ball_speed_multiplier, BALL_SPEED_MIN)
        self.assertEqual(state.paddle_height, PADDLE_HEIGHT_MAX)

    def test_auto_level_is_applied_after_exact_interval(self):
        state = DifficultyState()
        state.set_auto(True)

        self.assertEqual(state.update(AUTO_INTERVAL - 0.25), 0)
        self.assertEqual(state.ball_speed_multiplier, 1.0)
        self.assertEqual(state.paddle_height, 90)

        self.assertEqual(state.update(0.25), 1)
        self.assertEqual(state.ball_speed_multiplier, 1.1)
        self.assertEqual(state.paddle_height, 85)
        self.assertEqual(state.elapsed, 0.0)

    def test_large_dt_applies_multiple_levels_and_keeps_remainder(self):
        state = DifficultyState()
        state.set_auto(True)

        self.assertEqual(state.update(AUTO_INTERVAL * 3 + 5.0), 3)

        self.assertEqual(state.ball_speed_multiplier, 1.3)
        self.assertEqual(state.paddle_height, 75)
        self.assertEqual(state.elapsed, 5.0)

    def test_auto_off_pauses_and_resume_uses_saved_elapsed(self):
        state = DifficultyState()
        self.assertTrue(state.set_auto(True))
        state.update(12.0)

        self.assertTrue(state.set_auto(False))
        self.assertEqual(state.update(100.0), 0)
        self.assertEqual(state.elapsed, 12.0)
        self.assertFalse(state.set_auto(False))

        self.assertTrue(state.set_auto(True))
        self.assertEqual(state.update(8.0), 1)
        self.assertEqual(state.elapsed, 0.0)

    def test_manual_changes_do_not_reset_elapsed(self):
        state = DifficultyState()
        state.set_auto(True)
        state.update(7.25)

        state.adjust_ball_speed(1)
        state.adjust_paddle_height(-1)

        self.assertEqual(state.elapsed, 7.25)

    def test_invalid_values_are_rejected(self):
        for value in (True, "1.0"):
            with self.subTest(ball_speed_multiplier=value):
                with self.assertRaises(TypeError):
                    DifficultyState(ball_speed_multiplier=value)
        for value in (float("nan"), float("inf"), 0.49, 2.01):
            with self.subTest(ball_speed_multiplier=value):
                with self.assertRaises(ValueError):
                    DifficultyState(ball_speed_multiplier=value)

        with self.assertRaises(TypeError):
            DifficultyState(paddle_height=True)
        with self.assertRaises(ValueError):
            DifficultyState(paddle_height=49)
        with self.assertRaises(TypeError):
            DifficultyState(auto_enabled=1)
        with self.assertRaises(ValueError):
            DifficultyState(elapsed=-1)

        state = DifficultyState()
        with self.assertRaises(TypeError):
            state.adjust_ball_speed(True)
        with self.assertRaises(TypeError):
            state.set_auto(1)
        with self.assertRaises(ValueError):
            state.update(-0.01)
        with self.assertRaises(ValueError):
            state.update(float("inf"))


if __name__ == "__main__":
    unittest.main()
