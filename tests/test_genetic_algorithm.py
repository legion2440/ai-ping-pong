import math
import os
import random
import tempfile
import unittest
from unittest.mock import patch

import pygame

from ga.fitness import FitnessConfig, GenomeEvaluation
from ga.genetic_algorithm import EvolutionConfig, evolve, random_genome
from ga.genome import (
    MOVEMENT_THRESHOLD_MAX,
    MOVEMENT_THRESHOLD_MIN,
    PADDLE_SPEED_MAX,
    PADDLE_SPEED_MIN,
    REACTION_TIME_MAX,
    REACTION_TIME_MIN,
    BotGenome,
)
from game.match_runner import MatchConfig


def evaluation_for(genome, fitness=None):
    if fitness is None:
        fitness = (
            genome.paddle_speed
            - 100 * genome.reaction_time
            - genome.movement_threshold
        )
    return GenomeEvaluation(
        genome=genome,
        fitness=fitness,
        matches=2,
        wins=1,
        draws=0,
        losses=1,
        points_for=1,
        points_against=1,
        returns=0,
    )


class EvolutionConfigTests(unittest.TestCase):
    def test_numeric_values_are_normalized_and_negative_seed_is_allowed(self):
        config = EvolutionConfig(
            seed=-1,
            population_size=4,
            generations=2,
            elite_count=1,
            tournament_size=2,
            crossover_rate=1,
            mutation_rate=0,
            mutation_sigma=1,
        )

        self.assertEqual(config.seed, -1)
        self.assertIsInstance(config.crossover_rate, float)
        self.assertIsInstance(config.mutation_rate, float)
        self.assertIsInstance(config.mutation_sigma, float)

    def test_integer_fields_reject_booleans_and_non_ints(self):
        for field_name in (
            "seed",
            "population_size",
            "generations",
            "elite_count",
            "tournament_size",
        ):
            for value in (True, 1.5, "1"):
                with self.subTest(field_name=field_name, value=value):
                    with self.assertRaises(TypeError):
                        EvolutionConfig(**{field_name: value})

    def test_population_and_generation_bounds_are_validated(self):
        for value in (0, 1, -1):
            with self.subTest(population_size=value):
                with self.assertRaises(ValueError):
                    EvolutionConfig(population_size=value)
        for value in (0, -1):
            with self.subTest(generations=value):
                with self.assertRaises(ValueError):
                    EvolutionConfig(generations=value)

    def test_elite_and_tournament_bounds_are_validated(self):
        for value in (0, -1, 4):
            with self.subTest(elite_count=value):
                with self.assertRaises(ValueError):
                    EvolutionConfig(population_size=4, elite_count=value)
        for value in (0, 1, 5):
            with self.subTest(tournament_size=value):
                with self.assertRaises(ValueError):
                    EvolutionConfig(population_size=4, tournament_size=value)

    def test_probabilities_and_sigma_are_validated(self):
        for field_name in ("crossover_rate", "mutation_rate"):
            for value in (True, "0.5"):
                with self.subTest(field_name=field_name, value=value):
                    with self.assertRaises(TypeError):
                        EvolutionConfig(**{field_name: value})
            for value in (-0.1, 1.1, math.nan, math.inf, -math.inf):
                with self.subTest(field_name=field_name, value=value):
                    with self.assertRaises(ValueError):
                        EvolutionConfig(**{field_name: value})

        for value in (True, "0.1"):
            with self.subTest(mutation_sigma=value):
                with self.assertRaises(TypeError):
                    EvolutionConfig(mutation_sigma=value)
        for value in (0, -0.1, math.nan, math.inf, -math.inf):
            with self.subTest(mutation_sigma=value):
                with self.assertRaises(ValueError):
                    EvolutionConfig(mutation_sigma=value)


class RandomGenomeTests(unittest.TestCase):
    def test_genomes_are_reproducible_and_within_full_ranges(self):
        first_rng = random.Random(12)
        second_rng = random.Random(12)

        first_population = [random_genome(first_rng) for _ in range(5)]
        second_population = [random_genome(second_rng) for _ in range(5)]

        self.assertEqual(first_population, second_population)
        for genome in first_population:
            self.assertGreaterEqual(genome.paddle_speed, PADDLE_SPEED_MIN)
            self.assertLessEqual(genome.paddle_speed, PADDLE_SPEED_MAX)
            self.assertGreaterEqual(genome.reaction_time, REACTION_TIME_MIN)
            self.assertLessEqual(genome.reaction_time, REACTION_TIME_MAX)
            self.assertGreaterEqual(
                genome.movement_threshold,
                MOVEMENT_THRESHOLD_MIN,
            )
            self.assertLessEqual(
                genome.movement_threshold,
                MOVEMENT_THRESHOLD_MAX,
            )

    def test_different_seeds_produce_different_genomes(self):
        self.assertNotEqual(
            random_genome(random.Random(1)),
            random_genome(random.Random(2)),
        )

    def test_random_genome_does_not_change_global_random_state(self):
        state = random.getstate()

        random_genome(random.Random(1))

        self.assertEqual(random.getstate(), state)


class EvolutionTests(unittest.TestCase):
    def test_history_population_size_and_elitism_are_preserved(self):
        evolution_config = EvolutionConfig(
            seed=5,
            population_size=5,
            generations=4,
            elite_count=1,
            tournament_size=2,
        )
        fitness_config = FitnessConfig(
            seeds=(1,),
            match_config=MatchConfig(max_steps=5),
        )
        evaluated_genomes = []

        def evaluator(genome, config):
            self.assertIs(config, fitness_config)
            evaluated_genomes.append(genome)
            return evaluation_for(genome)

        with patch(
            "ga.genetic_algorithm.evaluate_genome",
            side_effect=evaluator,
        ):
            result = evolve(evolution_config, fitness_config)

        self.assertEqual(len(result.history), evolution_config.generations)
        self.assertEqual(
            [item.generation for item in result.history],
            list(range(evolution_config.generations)),
        )
        self.assertEqual(
            len(evaluated_genomes),
            evolution_config.population_size * evolution_config.generations,
        )
        for start in range(0, len(evaluated_genomes), evolution_config.population_size):
            self.assertEqual(
                len(evaluated_genomes[start : start + evolution_config.population_size]),
                evolution_config.population_size,
            )

        best_values = [item.best_fitness for item in result.history]
        self.assertEqual(best_values, sorted(best_values))
        self.assertEqual(result.best_fitness, max(best_values))

    def test_generation_stats_and_result_are_reproducible(self):
        evolution_config = EvolutionConfig(
            seed=8,
            population_size=4,
            generations=3,
            elite_count=1,
            tournament_size=2,
        )
        fitness_config = FitnessConfig(seeds=(2,))

        with patch(
            "ga.genetic_algorithm.evaluate_genome",
            side_effect=lambda genome, config: evaluation_for(genome),
        ):
            first = evolve(evolution_config, fitness_config)
            second = evolve(evolution_config, fitness_config)

        self.assertEqual(first, second)
        self.assertEqual(first.to_dict(), second.to_dict())
        payload = first.to_dict()
        self.assertIsInstance(payload["history"], list)
        self.assertIsInstance(payload["fitness_config"]["seeds"], list)
        for item in first.history:
            self.assertLessEqual(item.worst_fitness, item.mean_fitness)
            self.assertLessEqual(item.mean_fitness, item.best_fitness)

    def test_generation_and_global_ties_keep_first_population_genome(self):
        genomes = [
            BotGenome(120.0, 0.0, 0.0),
            BotGenome(220.0, 0.1, 10.0),
            BotGenome(320.0, 0.2, 20.0),
        ]
        config = EvolutionConfig(
            population_size=3,
            generations=1,
            elite_count=1,
            tournament_size=2,
        )

        with patch(
            "ga.genetic_algorithm.random_genome",
            side_effect=genomes,
        ), patch(
            "ga.genetic_algorithm.evaluate_genome",
            side_effect=lambda genome, fitness_config: evaluation_for(
                genome,
                fitness=4.0,
            ),
        ):
            result = evolve(config, FitnessConfig(seeds=(1,)))

        self.assertIs(result.history[0].best_genome, genomes[0])
        self.assertIs(result.best_genome, genomes[0])

    def test_elite_is_carried_directly_without_mutation(self):
        genomes = [
            BotGenome(120.0, 0.0, 0.0),
            BotGenome(220.0, 0.1, 10.0),
            BotGenome(320.0, 0.2, 20.0),
            BotGenome(420.0, 0.3, 40.0),
        ]
        evaluated = []

        def evaluator(genome, fitness_config):
            evaluated.append(genome)
            return evaluation_for(genome, fitness=genome.paddle_speed)

        with patch(
            "ga.genetic_algorithm.random_genome",
            side_effect=genomes,
        ), patch(
            "ga.genetic_algorithm.evaluate_genome",
            side_effect=evaluator,
        ), patch(
            "ga.genetic_algorithm.tournament_select",
            return_value=genomes[0],
        ), patch(
            "ga.genetic_algorithm.blend_crossover",
        ) as crossover, patch(
            "ga.genetic_algorithm.mutate_genome",
            side_effect=lambda genome, rng, **kwargs: genome,
        ) as mutate:
            evolve(
                EvolutionConfig(
                    population_size=4,
                    generations=2,
                    elite_count=1,
                    tournament_size=2,
                    crossover_rate=0,
                    mutation_rate=0,
                ),
                FitnessConfig(seeds=(1,)),
            )

        second_generation = evaluated[4:]
        self.assertIs(second_generation[0], genomes[-1])
        self.assertEqual(mutate.call_count, 3)
        self.assertTrue(
            all(call_args.args[0] is genomes[0] for call_args in mutate.call_args_list)
        )
        crossover.assert_not_called()

    def test_evolve_does_not_change_global_random_state(self):
        state = random.getstate()

        with patch(
            "ga.genetic_algorithm.evaluate_genome",
            side_effect=lambda genome, config: evaluation_for(genome),
        ):
            evolve(
                EvolutionConfig(
                    population_size=3,
                    generations=2,
                    elite_count=1,
                    tournament_size=2,
                ),
                FitnessConfig(seeds=(1,)),
            )

        self.assertEqual(random.getstate(), state)

    def test_evolve_rejects_invalid_config_objects(self):
        with self.assertRaises(TypeError):
            evolve("invalid", FitnessConfig())
        with self.assertRaises(TypeError):
            evolve(EvolutionConfig(), "invalid")

    def test_evolve_does_not_create_files(self):
        previous_directory = os.getcwd()
        with tempfile.TemporaryDirectory() as temporary_directory:
            try:
                os.chdir(temporary_directory)
                with patch(
                    "ga.genetic_algorithm.evaluate_genome",
                    side_effect=lambda genome, config: evaluation_for(genome),
                ):
                    evolve(
                        EvolutionConfig(
                            population_size=3,
                            generations=2,
                            elite_count=1,
                            tournament_size=2,
                        ),
                        FitnessConfig(seeds=(1,)),
                    )
                self.assertEqual(os.listdir(temporary_directory), [])
            finally:
                os.chdir(previous_directory)

    def test_small_real_end_to_end_run_is_headless(self):
        forbidden = AssertionError("GA training used a graphical API")
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
            result = evolve(
                EvolutionConfig(
                    population_size=2,
                    generations=1,
                    elite_count=1,
                    tournament_size=2,
                ),
                FitnessConfig(
                    seeds=(1,),
                    match_config=MatchConfig(max_steps=10),
                ),
            )

        self.assertEqual(len(result.history), 1)


if __name__ == "__main__":
    unittest.main()
