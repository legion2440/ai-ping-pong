import math
import random
import unittest
from unittest.mock import patch

from ga.artifacts import GenerationRecord
from ga.evaluation import EvaluationConfig, evaluate_generation_history
from ga.genome import BotGenome
from game.controllers import BotController
from game.match_runner import MatchConfig, run_match
from game.simulation import MatchSimulation
from game.utils import (
    BALL_SIZE,
    COURT_H,
    COURT_W,
    COURT_X,
    COURT_Y,
    PADDLE_H,
)

MINIMUM_GENOME = BotGenome(120.0, 0.0, 0.0)
MAXIMUM_GENOME = BotGenome(420.0, 0.30, 40.0)


class EvaluationEdgeCaseTests(unittest.TestCase):
    def test_extreme_valid_genomes_produce_finite_headless_metrics(self):
        records = (
            GenerationRecord(0, -1.0, -2.0, -3.0, MINIMUM_GENOME),
            GenerationRecord(1, 3.0, 2.0, 1.0, MAXIMUM_GENOME),
        )
        config = EvaluationConfig(
            seeds=(-1000, 1000),
            match_config=MatchConfig(
                dt=1 / 60,
                max_steps=120,
                score_limit=1,
            ),
        )
        random_state = random.getstate()

        with patch("pygame.display.set_mode") as set_mode, patch(
            "pygame.display.flip"
        ) as flip, patch(
            "pygame.time.Clock"
        ) as clock:
            report = evaluate_generation_history(records, config)

        set_mode.assert_not_called()
        flip.assert_not_called()
        clock.assert_not_called()
        self.assertEqual(random.getstate(), random_state)
        values = [
            report.training_mean_delta,
            report.held_out_fitness_delta,
            report.final_vs_initial.fitness,
            *(
                generation.held_out.fitness
                for generation in report.generations
            ),
        ]
        self.assertTrue(all(math.isfinite(value) for value in values))

    def test_long_headless_match_does_not_create_a_window(self):
        with patch("pygame.display.set_mode") as set_mode, patch(
            "pygame.display.flip"
        ) as flip, patch(
            "pygame.time.Clock"
        ) as clock:
            result = run_match(
                MINIMUM_GENOME,
                MAXIMUM_GENOME,
                seed=1000,
                config=MatchConfig(max_steps=3600, score_limit=5),
            )

        set_mode.assert_not_called()
        flip.assert_not_called()
        clock.assert_not_called()
        self.assertLessEqual(result.steps, 3600)
        self.assertTrue(math.isfinite(result.simulated_seconds))

    def test_extreme_controllers_remain_inside_vertical_court_bounds(self):
        simulation = MatchSimulation(rng=random.Random(1000))
        controllers = (
            BotController(MINIMUM_GENOME),
            BotController(MAXIMUM_GENOME),
        )

        for _ in range(600):
            controllers[0].update(
                simulation.p1,
                simulation.ball,
                1 / 60,
            )
            simulation.p1.clamp(COURT_Y, COURT_Y + COURT_H)
            controllers[1].update(
                simulation.p2,
                simulation.ball,
                1 / 60,
            )
            simulation.p2.clamp(COURT_Y, COURT_Y + COURT_H)
            simulation.step(1 / 60)

            for paddle in (simulation.p1, simulation.p2):
                self.assertGreaterEqual(
                    paddle.y,
                    COURT_Y + PADDLE_H / 2,
                )
                self.assertLessEqual(
                    paddle.y,
                    COURT_Y + COURT_H - PADDLE_H / 2,
                )

    def test_ball_at_maximum_vertical_speed_stays_inside_walls(self):
        simulation = MatchSimulation(rng=random.Random(1000))
        half = BALL_SIZE / 2

        simulation.ball.y = COURT_Y + half
        simulation.ball.vy = -420.0
        simulation.ball.update(1 / 60, COURT_Y, COURT_Y + COURT_H)
        self.assertGreaterEqual(simulation.ball.y - half, COURT_Y)
        self.assertGreaterEqual(simulation.ball.vy, 0)

        simulation.ball.y = COURT_Y + COURT_H - half
        simulation.ball.vy = 420.0
        simulation.ball.update(1 / 60, COURT_Y, COURT_Y + COURT_H)
        self.assertLessEqual(
            simulation.ball.y + half,
            COURT_Y + COURT_H,
        )
        self.assertLessEqual(simulation.ball.vy, 0)

    def test_scoring_resets_the_ball_to_court_center(self):
        simulation = MatchSimulation(rng=random.Random(1000))
        simulation.ball.x = COURT_X + COURT_W + 31

        events = simulation.step(0.0)

        self.assertEqual(events.point_winner, "left")
        self.assertEqual((simulation.score1, simulation.score2), (1, 0))
        self.assertEqual(
            (simulation.ball.x, simulation.ball.y),
            (
                COURT_X + COURT_W / 2,
                COURT_Y + COURT_H / 2,
            ),
        )
        self.assertEqual(abs(simulation.ball.vx), 260)


if __name__ == "__main__":
    unittest.main()
