import random
import unittest
from unittest.mock import patch

import pygame

from game.simulation import MatchSimulation, StepEvents
from game.utils import (
    BALL_SIZE,
    COLORS,
    COURT_H,
    COURT_W,
    COURT_X,
    COURT_Y,
    HUMAN_SPEED,
    PADDLE_MARGIN,
)


class MatchSimulationTests(unittest.TestCase):
    def setUp(self):
        self.random_state = random.getstate()
        random.seed(20260728)
        self.simulation = MatchSimulation()

    def tearDown(self):
        random.setstate(self.random_state)

    def test_initial_state_matches_existing_court(self):
        simulation = self.simulation
        center_y = COURT_Y + COURT_H / 2

        self.assertEqual((simulation.score1, simulation.score2), (0, 0))
        self.assertEqual(
            (simulation.p1.x, simulation.p1.y),
            (COURT_X + PADDLE_MARGIN, center_y),
        )
        self.assertEqual(
            (simulation.p2.x, simulation.p2.y),
            (COURT_X + COURT_W - PADDLE_MARGIN, center_y),
        )
        self.assertEqual(
            (simulation.ball.x, simulation.ball.y),
            (COURT_X + COURT_W / 2, center_y),
        )
        self.assertEqual(simulation.p1.color, COLORS["cyan"])
        self.assertEqual(simulation.p2.color, COLORS["lime"])
        self.assertEqual(simulation.p1.speed, HUMAN_SPEED)
        self.assertEqual(simulation.p2.speed, HUMAN_SPEED)
        self.assertEqual(abs(simulation.ball.vx), 260)

    def test_ball_bounces_off_top_wall_and_stays_inside(self):
        ball = self.simulation.ball
        ball.y = COURT_Y + BALL_SIZE / 2
        ball.vy = -100

        self.simulation.step(0.1)

        self.assertEqual(ball.y, COURT_Y + BALL_SIZE / 2)
        self.assertGreater(ball.vy, 0)

    def test_ball_bounces_off_bottom_wall_and_stays_inside(self):
        ball = self.simulation.ball
        ball.y = COURT_Y + COURT_H - BALL_SIZE / 2
        ball.vy = 100

        self.simulation.step(0.1)

        self.assertEqual(ball.y, COURT_Y + COURT_H - BALL_SIZE / 2)
        self.assertLess(ball.vy, 0)

    def test_left_paddle_collision_moves_ball_outside_paddle(self):
        simulation = self.simulation
        paddle_rect = simulation.p1.rect()
        simulation.ball.x = paddle_rect.right + 1
        simulation.ball.y = simulation.p1.y
        simulation.ball.vx = -260
        simulation.ball.vy = 0

        events = simulation.step(0)

        self.assertEqual(events, StepEvents(left_return=True))
        self.assertGreater(simulation.ball.vx, 0)
        self.assertEqual(simulation.ball.x, paddle_rect.right + BALL_SIZE / 2)
        velocity_after_collision = simulation.ball.vx
        next_events = simulation.step(0)
        self.assertEqual(next_events, StepEvents())
        self.assertEqual(simulation.ball.vx, velocity_after_collision)

    def test_right_paddle_collision_moves_ball_outside_paddle(self):
        simulation = self.simulation
        paddle_rect = simulation.p2.rect()
        simulation.ball.x = paddle_rect.left - 1
        simulation.ball.y = simulation.p2.y
        simulation.ball.vx = 260
        simulation.ball.vy = 0

        events = simulation.step(0)

        self.assertEqual(events, StepEvents(right_return=True))
        self.assertLess(simulation.ball.vx, 0)
        self.assertEqual(simulation.ball.x, paddle_rect.left - BALL_SIZE / 2)
        velocity_after_collision = simulation.ball.vx
        next_events = simulation.step(0)
        self.assertEqual(next_events, StepEvents())
        self.assertEqual(simulation.ball.vx, velocity_after_collision)

    def test_left_goal_increases_right_score_and_resets_ball(self):
        simulation = self.simulation
        simulation.ball.x = COURT_X - 31

        events = simulation.step(0)

        self.assertEqual(events, StepEvents(point_winner="right"))
        self.assertEqual((simulation.score1, simulation.score2), (0, 1))
        self.assertEqual(
            (simulation.ball.x, simulation.ball.y),
            (COURT_X + COURT_W / 2, COURT_Y + COURT_H / 2),
        )

    def test_right_goal_increases_left_score_and_resets_ball(self):
        simulation = self.simulation
        simulation.ball.x = COURT_X + COURT_W + 31

        events = simulation.step(0)

        self.assertEqual(events, StepEvents(point_winner="left"))
        self.assertEqual((simulation.score1, simulation.score2), (1, 0))
        self.assertEqual(
            (simulation.ball.x, simulation.ball.y),
            (COURT_X + COURT_W / 2, COURT_Y + COURT_H / 2),
        )

    def test_reset_recreates_initial_match_state(self):
        simulation = self.simulation
        original_objects = (simulation.p1, simulation.p2, simulation.ball)
        simulation.score1 = 3
        simulation.score2 = 2
        simulation.p1.y = COURT_Y
        simulation.ball.x = 0

        simulation.reset()

        self.assertEqual((simulation.score1, simulation.score2), (0, 0))
        self.assertIsNot(simulation.p1, original_objects[0])
        self.assertIsNot(simulation.p2, original_objects[1])
        self.assertIsNot(simulation.ball, original_objects[2])
        self.assertEqual(simulation.p1.y, COURT_Y + COURT_H / 2)
        self.assertEqual(simulation.p2.y, COURT_Y + COURT_H / 2)
        self.assertEqual(
            (simulation.ball.x, simulation.ball.y),
            (COURT_X + COURT_W / 2, COURT_Y + COURT_H / 2),
        )

    def test_ordinary_step_returns_empty_events(self):
        before = (
            self.simulation.score1,
            self.simulation.score2,
            self.simulation.ball.vx,
            self.simulation.ball.vy,
        )

        events = self.simulation.step(0)

        self.assertEqual(events, StepEvents())
        self.assertEqual(
            (
                self.simulation.score1,
                self.simulation.score2,
                self.simulation.ball.vx,
                self.simulation.ball.vy,
            ),
            before,
        )

    def test_reset_reuses_injected_rng_for_the_new_ball(self):
        rng = random.Random(20260728)
        simulation = MatchSimulation(rng=rng)
        first_ball = simulation.ball

        simulation.reset()

        self.assertIsNot(simulation.ball, first_ball)
        self.assertIs(simulation.ball.rng, rng)

    def test_simulation_does_not_create_a_display(self):
        rng = random.Random(20260728)
        with patch.object(
            pygame.display,
            "set_mode",
            side_effect=AssertionError("simulation attempted to create a window"),
        ):
            simulation = MatchSimulation(rng=rng)
            simulation.step(1 / 60)
        self.assertIsNone(pygame.display.get_surface())


if __name__ == "__main__":
    unittest.main()
