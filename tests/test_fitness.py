import math
import random
import unittest
from types import SimpleNamespace
from unittest.mock import call, patch

import pygame

from ga.fitness import FitnessConfig, GenomeEvaluation, evaluate_genome
from ga.genome import BotGenome
from game.match_runner import MatchConfig

CANDIDATE = BotGenome(300.0, 0.1, 12.0)
OPPONENT = BotGenome(260.0, 0.0, 8.0)


def match_result(left_score, right_score, left_returns, right_returns):
    return SimpleNamespace(
        left_score=left_score,
        right_score=right_score,
        left_returns=left_returns,
        right_returns=right_returns,
    )


class FitnessConfigTests(unittest.TestCase):
    def test_values_are_normalized_and_to_dict_uses_lists_for_seeds(self):
        config = FitnessConfig(
            seeds=(seed for seed in (5, -5, 5)),
            score_weight=2,
            return_weight=3,
        )

        self.assertEqual(config.seeds, (5, -5, 5))
        self.assertIsInstance(config.score_weight, float)
        self.assertIsInstance(config.return_weight, float)
        self.assertEqual(config.to_dict()["seeds"], [5, -5, 5])
        self.assertIsInstance(config.to_dict()["seeds"], list)

    def test_seeds_must_be_a_non_empty_iterable_of_real_ints(self):
        for seeds in (None, 1):
            with self.subTest(seeds=seeds):
                with self.assertRaises(TypeError):
                    FitnessConfig(seeds=seeds)

        with self.assertRaises(ValueError):
            FitnessConfig(seeds=())

        for seeds in ((True,), (1.5,), ("1",)):
            with self.subTest(seeds=seeds):
                with self.assertRaises(TypeError):
                    FitnessConfig(seeds=seeds)

    def test_config_and_opponent_require_expected_types(self):
        with self.assertRaises(TypeError):
            FitnessConfig(match_config="invalid")
        with self.assertRaises(TypeError):
            FitnessConfig(opponent_genome="invalid")

    def test_weights_must_be_finite_non_negative_numbers(self):
        for field_name in ("score_weight", "return_weight"):
            for value in (True, "1"):
                with self.subTest(field_name=field_name, value=value):
                    with self.assertRaises(TypeError):
                        FitnessConfig(**{field_name: value})

            for value in (-1, math.nan, math.inf, -math.inf):
                with self.subTest(field_name=field_name, value=value):
                    with self.assertRaises(ValueError):
                        FitnessConfig(**{field_name: value})

        with self.assertRaises(ValueError):
            FitnessConfig(score_weight=0, return_weight=0)


class FitnessEvaluationTests(unittest.TestCase):
    def test_candidate_plays_both_sides_for_each_seed_in_order(self):
        config = FitnessConfig(
            seeds=(11, -7),
            match_config=MatchConfig(max_steps=10, score_limit=2),
            opponent_genome=OPPONENT,
            score_weight=100,
            return_weight=1,
        )
        results = [
            match_result(3, 1, 4, 40),
            match_result(2, 2, 20, 5),
            match_result(0, 1, 6, 60),
            match_result(1, 3, 70, 7),
        ]

        with patch("ga.fitness.run_match", side_effect=results) as run_match:
            evaluation = evaluate_genome(CANDIDATE, config)

        self.assertEqual(
            run_match.call_args_list,
            [
                call(CANDIDATE, OPPONENT, seed=11, config=config.match_config),
                call(OPPONENT, CANDIDATE, seed=11, config=config.match_config),
                call(CANDIDATE, OPPONENT, seed=-7, config=config.match_config),
                call(OPPONENT, CANDIDATE, seed=-7, config=config.match_config),
            ],
        )
        self.assertEqual(evaluation.matches, 2 * len(config.seeds))
        self.assertEqual((evaluation.wins, evaluation.draws, evaluation.losses), (2, 1, 1))
        self.assertEqual((evaluation.points_for, evaluation.points_against), (8, 5))
        self.assertEqual(evaluation.returns, 22)
        self.assertEqual(evaluation.fitness, 80.5)

    def test_negative_fitness_is_preserved(self):
        config = FitnessConfig(seeds=(1,), score_weight=10, return_weight=0)
        results = [
            match_result(0, 2, 100, 0),
            match_result(3, 0, 0, 100),
        ]

        with patch("ga.fitness.run_match", side_effect=results):
            evaluation = evaluate_genome(CANDIDATE, config)

        self.assertEqual(evaluation.fitness, -25.0)
        self.assertLess(evaluation.fitness, 0)

    def test_identical_inputs_are_deterministic(self):
        config = FitnessConfig(
            seeds=(1,),
            match_config=MatchConfig(max_steps=30, score_limit=2),
        )

        first = evaluate_genome(CANDIDATE, config)
        second = evaluate_genome(CANDIDATE, config)

        self.assertEqual(first, second)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_evaluation_does_not_change_global_random_state(self):
        state = random.getstate()

        evaluate_genome(
            CANDIDATE,
            FitnessConfig(
                seeds=(-1,),
                match_config=MatchConfig(max_steps=20),
            ),
        )

        self.assertEqual(random.getstate(), state)

    def test_invalid_genome_and_config_are_rejected(self):
        with self.assertRaises(TypeError):
            evaluate_genome("invalid")
        with self.assertRaises(TypeError):
            evaluate_genome(CANDIDATE, "invalid")

    def test_small_real_evaluation_is_headless(self):
        forbidden = AssertionError("fitness evaluation used a graphical API")
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
            result = evaluate_genome(
                CANDIDATE,
                FitnessConfig(
                    seeds=(1,),
                    match_config=MatchConfig(max_steps=10),
                ),
            )

        self.assertIsInstance(result, GenomeEvaluation)
        self.assertEqual(result.matches, 2)


if __name__ == "__main__":
    unittest.main()
