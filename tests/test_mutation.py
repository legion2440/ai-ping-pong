import math
import random
import unittest

from ga.genome import BotGenome
from ga.mutation import mutate_genome

GENOME = BotGenome(260.0, 0.15, 20.0)


class ForbiddenRng:
    def random(self):
        raise AssertionError("mutation_rate=0 consumed random()")

    def gauss(self, mean, sigma):
        raise AssertionError("mutation_rate=0 consumed gauss()")


class RecordingRng:
    def __init__(self, noise):
        self.noise = iter(noise)
        self.calls = []

    def random(self):
        self.calls.append(("random",))
        return 0.0

    def gauss(self, mean, sigma):
        self.calls.append(("gauss", mean, sigma))
        return next(self.noise)


class MutationTests(unittest.TestCase):
    def test_zero_rate_returns_original_without_consuming_rng(self):
        result = mutate_genome(
            GENOME,
            ForbiddenRng(),
            mutation_rate=0,
            mutation_sigma=0.1,
        )

        self.assertIs(result, GENOME)

    def test_full_rate_checks_every_gene_in_fixed_rng_order(self):
        rng = RecordingRng([10.0, -1.0, 5.0])

        result = mutate_genome(
            GENOME,
            rng,
            mutation_rate=1,
            mutation_sigma=0.1,
        )

        self.assertEqual(result, BotGenome(270.0, 0.0, 25.0))
        self.assertEqual(
            rng.calls,
            [
                ("random",),
                ("gauss", 0, 30.0),
                ("random",),
                ("gauss", 0, 0.03),
                ("random",),
                ("gauss", 0, 4.0),
            ],
        )

    def test_mutated_values_are_clamped_to_genome_ranges(self):
        result = mutate_genome(
            GENOME,
            RecordingRng([1000.0, 1000.0, -1000.0]),
            mutation_rate=1,
            mutation_sigma=0.2,
        )

        self.assertEqual(result, BotGenome(420.0, 0.3, 0.0))

    def test_same_rng_state_produces_same_mutation(self):
        first = mutate_genome(
            GENOME,
            random.Random(4),
            mutation_rate=0.8,
            mutation_sigma=0.1,
        )
        second = mutate_genome(
            GENOME,
            random.Random(4),
            mutation_rate=0.8,
            mutation_sigma=0.1,
        )

        self.assertEqual(first, second)

    def test_original_genome_is_not_modified(self):
        original = GENOME.to_vector()

        mutate_genome(
            GENOME,
            random.Random(5),
            mutation_rate=1,
            mutation_sigma=0.1,
        )

        self.assertEqual(GENOME.to_vector(), original)

    def test_invalid_rate_and_sigma_are_rejected(self):
        for value in (True, "0.1"):
            with self.subTest(field="mutation_rate", value=value):
                with self.assertRaises(TypeError):
                    mutate_genome(
                        GENOME,
                        random.Random(1),
                        mutation_rate=value,
                        mutation_sigma=0.1,
                    )
            with self.subTest(field="mutation_sigma", value=value):
                with self.assertRaises(TypeError):
                    mutate_genome(
                        GENOME,
                        random.Random(1),
                        mutation_rate=0.1,
                        mutation_sigma=value,
                    )

        for value in (-0.1, 1.1, math.nan, math.inf, -math.inf):
            with self.subTest(field="mutation_rate", value=value):
                with self.assertRaises(ValueError):
                    mutate_genome(
                        GENOME,
                        random.Random(1),
                        mutation_rate=value,
                        mutation_sigma=0.1,
                    )

        for value in (0, -0.1, math.nan, math.inf, -math.inf):
            with self.subTest(field="mutation_sigma", value=value):
                with self.assertRaises(ValueError):
                    mutate_genome(
                        GENOME,
                        random.Random(1),
                        mutation_rate=0.1,
                        mutation_sigma=value,
                    )

    def test_mutation_does_not_change_global_random_state(self):
        state = random.getstate()

        mutate_genome(
            GENOME,
            random.Random(8),
            mutation_rate=1,
            mutation_sigma=0.1,
        )

        self.assertEqual(random.getstate(), state)


if __name__ == "__main__":
    unittest.main()
