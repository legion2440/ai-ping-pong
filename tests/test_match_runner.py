import math
import random
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pygame

from ga.genome import BotGenome
from game.match_runner import MatchConfig, run_match
from game.paddle import Paddle
from game.simulation import StepEvents
from game.utils import COLORS, COURT_H, COURT_W, COURT_X, COURT_Y, PADDLE_MARGIN

BASELINE_GENOME = BotGenome(260.0, 0.0, 8.0)


def scripted_simulation(events):
    instances = []

    class ScriptedSimulation:
        def __init__(self, rng=None):
            center_y = COURT_Y + COURT_H / 2
            self.p1 = Paddle(
                COURT_X + PADDLE_MARGIN,
                center_y,
                COLORS["cyan"],
            )
            self.p2 = Paddle(
                COURT_X + COURT_W - PADDLE_MARGIN,
                center_y,
                COLORS["lime"],
            )
            self.ball = SimpleNamespace(y=center_y)
            self.score1 = 0
            self.score2 = 0
            self.events = list(events)
            self.step_calls = 0
            self.rng = rng
            instances.append(self)

        def step(self, dt):
            event = self.events[self.step_calls]
            self.step_calls += 1
            if event.point_winner == "left":
                self.score1 += 1
            elif event.point_winner == "right":
                self.score2 += 1
            return event

    return ScriptedSimulation, instances


class MatchConfigTests(unittest.TestCase):
    def test_dt_is_normalized_to_float(self):
        config = MatchConfig(dt=1, max_steps=10, score_limit=2)

        self.assertEqual(config.dt, 1.0)
        self.assertIsInstance(config.dt, float)

    def test_invalid_dt_is_rejected(self):
        for value in (True, "0.1"):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    MatchConfig(dt=value)
        for value in (0, -0.1, math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    MatchConfig(dt=value)

    def test_step_and_score_limits_require_positive_real_ints(self):
        for field_name in ("max_steps", "score_limit"):
            for value in (True, 1.5, "1"):
                with self.subTest(field_name=field_name, value=value):
                    parameters = {field_name: value}
                    with self.assertRaises(TypeError):
                        MatchConfig(**parameters)
            for value in (0, -1):
                with self.subTest(field_name=field_name, value=value):
                    parameters = {field_name: value}
                    with self.assertRaises(ValueError):
                        MatchConfig(**parameters)


class MatchRunnerTests(unittest.TestCase):
    def test_same_seed_and_inputs_produce_identical_results(self):
        config = MatchConfig(max_steps=600, score_limit=3)

        first = run_match(
            BASELINE_GENOME,
            BASELINE_GENOME,
            seed=20260728,
            config=config,
        )
        second = run_match(
            BASELINE_GENOME,
            BASELINE_GENOME,
            seed=20260728,
            config=config,
        )

        self.assertEqual(first, second)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_run_match_does_not_change_global_random_state(self):
        global_state = random.getstate()

        run_match(
            BASELINE_GENOME,
            BASELINE_GENOME,
            seed=20260728,
            config=MatchConfig(max_steps=100),
        )

        self.assertEqual(random.getstate(), global_state)

    def test_max_steps_terminates_at_exact_limit(self):
        result = run_match(
            BASELINE_GENOME,
            BASELINE_GENOME,
            seed=20260728,
            config=MatchConfig(dt=0.25, max_steps=7, score_limit=5),
        )

        self.assertEqual(result.steps, 7)
        self.assertEqual(result.simulated_seconds, 1.75)
        self.assertEqual(result.termination_reason, "max_steps")

    def test_score_limit_wins_when_reached_on_last_allowed_step(self):
        fake_class, instances = scripted_simulation(
            [
                StepEvents(point_winner="left"),
                StepEvents(point_winner="left"),
                StepEvents(point_winner="right"),
            ]
        )

        with patch("game.match_runner.MatchSimulation", fake_class):
            result = run_match(
                BASELINE_GENOME,
                BASELINE_GENOME,
                seed=1,
                config=MatchConfig(max_steps=2, score_limit=2),
            )

        self.assertEqual(instances[0].step_calls, 2)
        self.assertEqual(result.steps, 2)
        self.assertEqual((result.left_score, result.right_score), (2, 0))
        self.assertEqual(result.winner, "left")
        self.assertEqual(result.termination_reason, "score_limit")

    def test_metrics_track_returns_completed_and_unfinished_rallies(self):
        fake_class, _ = scripted_simulation(
            [
                StepEvents(left_return=True),
                StepEvents(right_return=True, point_winner="left"),
                StepEvents(left_return=True),
                StepEvents(right_return=True),
                StepEvents(right_return=True),
            ]
        )

        with patch("game.match_runner.MatchSimulation", fake_class):
            result = run_match(
                BASELINE_GENOME,
                BASELINE_GENOME,
                seed=1,
                config=MatchConfig(max_steps=5, score_limit=5),
            )

        self.assertEqual(result.left_returns, 2)
        self.assertEqual(result.right_returns, 3)
        self.assertEqual(result.longest_rally, 3)
        self.assertEqual((result.left_score, result.right_score), (1, 0))
        self.assertEqual(result.termination_reason, "max_steps")

    def test_result_to_dict_contains_nested_config_and_genomes(self):
        left_genome = BotGenome(200.0, 0.1, 5.0)
        right_genome = BotGenome(300.0, 0.2, 10.0)
        config = MatchConfig(max_steps=1)

        result = run_match(
            left_genome,
            right_genome,
            seed=-5,
            config=config,
        )
        payload = result.to_dict()

        self.assertEqual(payload["seed"], -5)
        self.assertEqual(payload["config"], config.to_dict())
        self.assertEqual(payload["left_genome"], left_genome.to_dict())
        self.assertEqual(payload["right_genome"], right_genome.to_dict())
        self.assertNotIn("fitness", payload)

    def test_run_match_does_not_use_display_rendering_or_clock(self):
        forbidden = AssertionError("headless match used a graphical API")
        with patch.object(
            pygame.display,
            "set_mode",
            side_effect=forbidden,
        ), patch.object(
            pygame.display,
            "flip",
            side_effect=forbidden,
        ), patch.object(
            pygame.time,
            "Clock",
            side_effect=forbidden,
        ):
            run_match(
                BASELINE_GENOME,
                BASELINE_GENOME,
                seed=1,
                config=MatchConfig(max_steps=10),
            )

    def test_runner_creates_isolated_controllers(self):
        controllers = []

        class TrackingController:
            def __init__(self, genome):
                self.genome = genome
                self.target_y = None
                self.elapsed_time = 0.0
                controllers.append(self)

            def update(self, paddle, ball, dt):
                self.target_y = ball.y
                self.elapsed_time += dt

        with patch("game.match_runner.BotController", TrackingController):
            run_match(
                BotGenome(200.0, 0.1, 5.0),
                BotGenome(300.0, 0.2, 10.0),
                seed=-1,
                config=MatchConfig(max_steps=1),
            )

        self.assertEqual(len(controllers), 2)
        self.assertIsNot(controllers[0], controllers[1])
        self.assertNotEqual(controllers[0].genome, controllers[1].genome)
        self.assertIsNotNone(controllers[0].target_y)
        self.assertIsNotNone(controllers[1].target_y)

    def test_seed_requires_a_real_int_and_allows_negative_values(self):
        for value in (True, 1.5, "1"):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    run_match(
                        BASELINE_GENOME,
                        BASELINE_GENOME,
                        seed=value,
                        config=MatchConfig(max_steps=1),
                    )

        result = run_match(
            BASELINE_GENOME,
            BASELINE_GENOME,
            seed=-1,
            config=MatchConfig(max_steps=1),
        )
        self.assertEqual(result.seed, -1)


if __name__ == "__main__":
    unittest.main()
