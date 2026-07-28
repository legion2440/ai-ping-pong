import random
import unittest

from ga.fitness import GenomeEvaluation
from ga.genome import BotGenome
from ga.selection import tournament_select


def evaluation(speed, fitness):
    return GenomeEvaluation(
        genome=BotGenome(speed, 0.1, 10.0),
        fitness=fitness,
        matches=2,
        wins=0,
        draws=2,
        losses=0,
        points_for=0,
        points_against=0,
        returns=0,
    )


class RecordingRng:
    def __init__(self, participants):
        self.participants = participants
        self.calls = []

    def sample(self, population, size):
        self.calls.append((population, size))
        return self.participants


class TournamentSelectionTests(unittest.TestCase):
    def test_highest_fitness_participant_wins(self):
        population = [
            evaluation(200.0, 1.0),
            evaluation(250.0, 9.0),
            evaluation(300.0, 5.0),
        ]
        rng = RecordingRng([population[2], population[1]])

        selected = tournament_select(population, 2, rng)

        self.assertIs(selected, population[1].genome)
        self.assertEqual(rng.calls, [(population, 2)])

    def test_first_sampled_participant_wins_a_fitness_tie(self):
        population = [
            evaluation(200.0, 7.0),
            evaluation(250.0, 7.0),
        ]
        rng = RecordingRng([population[1], population[0]])

        selected = tournament_select(population, 2, rng)

        self.assertIs(selected, population[1].genome)

    def test_same_rng_state_produces_same_selection(self):
        population = [
            evaluation(200.0, 1.0),
            evaluation(250.0, 2.0),
            evaluation(300.0, 3.0),
            evaluation(350.0, 4.0),
        ]

        first = tournament_select(population, 3, random.Random(10))
        second = tournament_select(population, 3, random.Random(10))

        self.assertEqual(first, second)

    def test_population_is_not_modified(self):
        population = [
            evaluation(200.0, 1.0),
            evaluation(250.0, 2.0),
            evaluation(300.0, 3.0),
        ]
        before = list(population)

        tournament_select(population, 2, random.Random(1))

        self.assertEqual(population, before)

    def test_invalid_population_and_tournament_size_are_rejected(self):
        with self.assertRaises(ValueError):
            tournament_select([], 1, random.Random(1))

        population = [evaluation(200.0, 1.0), evaluation(250.0, 2.0)]
        for value in (True, 1.5, "1"):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    tournament_select(population, value, random.Random(1))
        for value in (0, -1, 3):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    tournament_select(population, value, random.Random(1))


if __name__ == "__main__":
    unittest.main()
