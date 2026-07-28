import math
import unittest
from dataclasses import FrozenInstanceError, fields

from ga.genome import (
    MOVEMENT_THRESHOLD_MAX,
    MOVEMENT_THRESHOLD_MIN,
    PADDLE_SPEED_MAX,
    PADDLE_SPEED_MIN,
    REACTION_TIME_MAX,
    REACTION_TIME_MIN,
    BotGenome,
)


class BotGenomeTests(unittest.TestCase):
    def test_valid_genome_is_normalized_to_floats(self):
        genome = BotGenome(260, 0, 8)

        self.assertEqual(
            genome,
            BotGenome(
                paddle_speed=260.0,
                reaction_time=0.0,
                movement_threshold=8.0,
            ),
        )
        self.assertIsInstance(genome.paddle_speed, float)
        self.assertIsInstance(genome.reaction_time, float)
        self.assertIsInstance(genome.movement_threshold, float)

    def test_baseline_values_are_valid(self):
        genome = BotGenome(260.0, 0.0, 8.0)

        self.assertEqual(genome.to_vector(), [260.0, 0.0, 8.0])

    def test_vector_order_matches_dataclass_field_order(self):
        genome = BotGenome(240.0, 0.15, 12.0)

        self.assertEqual(
            [field.name for field in fields(BotGenome)],
            ["paddle_speed", "reaction_time", "movement_threshold"],
        )
        self.assertEqual(genome.to_vector(), [240.0, 0.15, 12.0])

    def test_vector_round_trip(self):
        genome = BotGenome(315.0, 0.12, 18.0)

        self.assertEqual(BotGenome.from_vector(genome.to_vector()), genome)

    def test_from_vector_accepts_an_iterable(self):
        vector = (value for value in (315.0, 0.12, 18.0))

        self.assertEqual(
            BotGenome.from_vector(vector),
            BotGenome(315.0, 0.12, 18.0),
        )

    def test_dict_round_trip(self):
        genome = BotGenome(315.0, 0.12, 18.0)

        self.assertEqual(BotGenome(**genome.to_dict()), genome)

    def test_vector_requires_exactly_three_elements(self):
        for vector in ((260.0, 0.0), (260.0, 0.0, 8.0, 1.0)):
            with self.subTest(vector=vector):
                with self.assertRaises(ValueError):
                    BotGenome.from_vector(vector)

    def test_range_boundaries_are_inclusive(self):
        lower_bound = BotGenome(
            PADDLE_SPEED_MIN,
            REACTION_TIME_MIN,
            MOVEMENT_THRESHOLD_MIN,
        )
        upper_bound = BotGenome(
            PADDLE_SPEED_MAX,
            REACTION_TIME_MAX,
            MOVEMENT_THRESHOLD_MAX,
        )

        self.assertEqual(
            lower_bound.to_vector(),
            [PADDLE_SPEED_MIN, REACTION_TIME_MIN, MOVEMENT_THRESHOLD_MIN],
        )
        self.assertEqual(
            upper_bound.to_vector(),
            [PADDLE_SPEED_MAX, REACTION_TIME_MAX, MOVEMENT_THRESHOLD_MAX],
        )

    def test_values_outside_ranges_are_rejected(self):
        invalid_values = (
            ("paddle_speed", PADDLE_SPEED_MIN - 1),
            ("paddle_speed", PADDLE_SPEED_MAX + 1),
            ("reaction_time", REACTION_TIME_MIN - 0.01),
            ("reaction_time", REACTION_TIME_MAX + 0.01),
            ("movement_threshold", MOVEMENT_THRESHOLD_MIN - 1),
            ("movement_threshold", MOVEMENT_THRESHOLD_MAX + 1),
        )

        for field_name, value in invalid_values:
            with self.subTest(field_name=field_name, value=value):
                parameters = {
                    "paddle_speed": 260.0,
                    "reaction_time": 0.0,
                    "movement_threshold": 8.0,
                }
                parameters[field_name] = value
                with self.assertRaises(ValueError):
                    BotGenome(**parameters)

    def test_non_numeric_and_boolean_values_are_rejected(self):
        for field_name in (
            "paddle_speed",
            "reaction_time",
            "movement_threshold",
        ):
            for value in (True, "1.0"):
                with self.subTest(field_name=field_name, value=value):
                    parameters = {
                        "paddle_speed": 260.0,
                        "reaction_time": 0.0,
                        "movement_threshold": 8.0,
                    }
                    parameters[field_name] = value
                    with self.assertRaises(TypeError):
                        BotGenome(**parameters)

    def test_nan_and_infinity_are_rejected(self):
        for field_name in (
            "paddle_speed",
            "reaction_time",
            "movement_threshold",
        ):
            for value in (math.nan, math.inf, -math.inf):
                with self.subTest(field_name=field_name, value=value):
                    parameters = {
                        "paddle_speed": 260.0,
                        "reaction_time": 0.0,
                        "movement_threshold": 8.0,
                    }
                    parameters[field_name] = value
                    with self.assertRaises(ValueError):
                        BotGenome(**parameters)

    def test_genome_is_immutable(self):
        genome = BotGenome(260.0, 0.0, 8.0)

        with self.assertRaises(FrozenInstanceError):
            genome.paddle_speed = 300.0


if __name__ == "__main__":
    unittest.main()
