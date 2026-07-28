import random
import unittest

from ga.crossover import blend_crossover
from ga.genome import BotGenome

FIRST = BotGenome(120.0, 0.0, 40.0)
SECOND = BotGenome(420.0, 0.3, 0.0)


class SequenceRng:
    def __init__(self, values):
        self.values = iter(values)
        self.calls = 0

    def random(self):
        self.calls += 1
        return next(self.values)


class BlendCrossoverTests(unittest.TestCase):
    def test_three_independent_alphas_are_consumed_in_gene_order(self):
        rng = SequenceRng([0.0, 0.5, 1.0])

        child = blend_crossover(FIRST, SECOND, rng)

        self.assertEqual(child, BotGenome(420.0, 0.15, 40.0))
        self.assertEqual(rng.calls, 3)

    def test_child_genes_stay_between_parent_genes(self):
        child = blend_crossover(FIRST, SECOND, random.Random(5))

        for child_gene, first_gene, second_gene in zip(
            child.to_vector(),
            FIRST.to_vector(),
            SECOND.to_vector(),
        ):
            self.assertGreaterEqual(child_gene, min(first_gene, second_gene))
            self.assertLessEqual(child_gene, max(first_gene, second_gene))
        self.assertIsInstance(child, BotGenome)

    def test_same_rng_state_produces_same_child(self):
        first_child = blend_crossover(FIRST, SECOND, random.Random(7))
        second_child = blend_crossover(FIRST, SECOND, random.Random(7))

        self.assertEqual(first_child, second_child)

    def test_parents_are_not_modified(self):
        first_vector = FIRST.to_vector()
        second_vector = SECOND.to_vector()

        blend_crossover(FIRST, SECOND, random.Random(3))

        self.assertEqual(FIRST.to_vector(), first_vector)
        self.assertEqual(SECOND.to_vector(), second_vector)

    def test_crossover_does_not_change_global_random_state(self):
        state = random.getstate()

        blend_crossover(FIRST, SECOND, random.Random(9))

        self.assertEqual(random.getstate(), state)


if __name__ == "__main__":
    unittest.main()
