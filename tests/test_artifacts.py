import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ga.artifacts import (
    CSV_HEADER,
    load_best_genome,
    write_best_genome_json,
    write_generations_csv,
)
from ga.fitness import FitnessConfig
from ga.genetic_algorithm import (
    EvolutionConfig,
    EvolutionResult,
    GenerationStats,
)
from ga.genome import BotGenome
from game.match_runner import MatchConfig

FIRST_GENOME = BotGenome(200.0, 0.1, 5.0)
BEST_GENOME = BotGenome(320.0, 0.05, 8.0)


def sample_result():
    evolution_config = EvolutionConfig(
        seed=-7,
        population_size=2,
        generations=2,
        elite_count=1,
        tournament_size=2,
        crossover_rate=0.5,
        mutation_rate=0.25,
        mutation_sigma=0.1,
    )
    fitness_config = FitnessConfig(
        seeds=(-1, 2),
        match_config=MatchConfig(
            dt=0.25,
            max_steps=20,
            score_limit=2,
        ),
        score_weight=100,
        return_weight=1,
    )
    history = (
        GenerationStats(
            generation=0,
            best_genome=FIRST_GENOME,
            best_fitness=10.5,
            mean_fitness=2.25,
            worst_fitness=-5.0,
        ),
        GenerationStats(
            generation=1,
            best_genome=BEST_GENOME,
            best_fitness=20.0,
            mean_fitness=12.75,
            worst_fitness=1.5,
        ),
    )
    return EvolutionResult(
        evolution_config=evolution_config,
        fitness_config=fitness_config,
        best_genome=BEST_GENOME,
        best_fitness=20.0,
        history=history,
    )


class GenerationsCsvTests(unittest.TestCase):
    def test_csv_has_fixed_header_and_one_ordered_row_per_generation(self):
        result = sample_result()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "generations.csv"
            write_generations_csv(result, path)
            content = path.read_text(encoding="utf-8")

        self.assertEqual(
            content,
            ",".join(CSV_HEADER)
            + "\n"
            + "0,10.5,2.25,-5.0,200.0,0.1,5.0\n"
            + "1,20.0,12.75,1.5,320.0,0.05,8.0\n",
        )

    def test_repeated_write_replaces_old_content(self):
        result = sample_result()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "generations.csv"
            path.write_text("old content\n", encoding="utf-8")

            write_generations_csv(result, str(path))
            first_bytes = path.read_bytes()
            write_generations_csv(result, path)
            second_bytes = path.read_bytes()

        self.assertEqual(first_bytes, second_bytes)
        self.assertNotIn(b"old content", second_bytes)
        self.assertEqual(second_bytes.count(b"\n"), len(result.history) + 1)

    def test_parent_directories_are_created_and_newlines_are_lf(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "logs" / "generations.csv"

            write_generations_csv(sample_result(), path)
            content = path.read_bytes()

        self.assertTrue(content.endswith(b"\n"))
        self.assertNotIn(b"\r\n", content)


class BestGenomeJsonTests(unittest.TestCase):
    def test_json_has_fixed_schema_without_history(self):
        result = sample_result()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "best_bot.json"
            write_best_genome_json(result, path)
            content = path.read_bytes()
            payload = json.loads(content)

        self.assertTrue(content.endswith(b"\n"))
        self.assertNotIn(b"\r\n", content)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["fitness"], result.best_fitness)
        self.assertEqual(payload["genome"], result.best_genome.to_dict())
        self.assertEqual(
            payload["evolution_config"],
            result.evolution_config.to_dict(),
        )
        self.assertEqual(
            payload["fitness_config"],
            result.fitness_config.to_dict(),
        )
        self.assertNotIn("history", payload)

    def test_same_result_produces_identical_csv_and_json_bytes(self):
        result = sample_result()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_csv = root / "first.csv"
            second_csv = root / "second.csv"
            first_json = root / "first.json"
            second_json = root / "second.json"

            write_generations_csv(result, first_csv)
            write_generations_csv(result, second_csv)
            write_best_genome_json(result, first_json)
            write_best_genome_json(result, second_json)

            self.assertEqual(first_csv.read_bytes(), second_csv.read_bytes())
            self.assertEqual(first_json.read_bytes(), second_json.read_bytes())

    def test_round_trip_loads_only_the_validated_genome(self):
        result = sample_result()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "models" / "best_bot.json"
            write_best_genome_json(result, path)

            loaded = load_best_genome(str(path))

        self.assertEqual(loaded, result.best_genome)
        self.assertIsInstance(loaded, BotGenome)


class BestGenomeLoadingErrorsTests(unittest.TestCase):
    def _write_payload(self, directory, content):
        path = Path(directory) / "best_bot.json"
        path.write_text(content, encoding="utf-8", newline="\n")
        return path

    def test_missing_file_preserves_file_not_found_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"

            with self.assertRaises(FileNotFoundError):
                load_best_genome(path)

    def test_invalid_json_is_wrapped_in_value_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_payload(directory, "{invalid")

            with self.assertRaisesRegex(ValueError, "invalid JSON") as raised:
                load_best_genome(path)

        self.assertIsInstance(raised.exception.__cause__, json.JSONDecodeError)

    def test_root_must_be_an_object(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_payload(directory, "[]")

            with self.assertRaisesRegex(ValueError, "root"):
                load_best_genome(path)

    def test_schema_version_requires_exact_int_one(self):
        for version in (True, 2, "1", None):
            with self.subTest(version=version):
                with tempfile.TemporaryDirectory() as directory:
                    content = json.dumps(
                        {
                            "schema_version": version,
                            "genome": BEST_GENOME.to_dict(),
                        }
                    )
                    path = self._write_payload(directory, content)

                    with self.assertRaisesRegex(ValueError, "schema_version"):
                        load_best_genome(path)

    def test_genome_must_be_present_and_an_object(self):
        for payload in (
            {"schema_version": 1},
            {"schema_version": 1, "genome": None},
            {"schema_version": 1, "genome": []},
        ):
            with self.subTest(payload=payload):
                with tempfile.TemporaryDirectory() as directory:
                    path = self._write_payload(directory, json.dumps(payload))

                    with self.assertRaisesRegex(ValueError, "genome"):
                        load_best_genome(path)

    def test_invalid_genome_is_wrapped_with_original_cause(self):
        payload = {
            "schema_version": 1,
            "genome": {
                "paddle_speed": 1000,
                "reaction_time": 0.1,
                "movement_threshold": 5,
            },
        }

        with tempfile.TemporaryDirectory() as directory:
            path = self._write_payload(directory, json.dumps(payload))

            with self.assertRaisesRegex(ValueError, "invalid genome") as raised:
                load_best_genome(path)

        self.assertIsInstance(raised.exception.__cause__, ValueError)


class AtomicWriteTests(unittest.TestCase):
    def test_no_temporary_file_remains_after_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            csv_path = root / "generations.csv"
            json_path = root / "best_bot.json"

            write_generations_csv(sample_result(), csv_path)
            write_best_genome_json(sample_result(), json_path)

            self.assertEqual(
                {path.name for path in root.iterdir()},
                {"generations.csv", "best_bot.json"},
            )

    def test_temporary_file_is_removed_when_replace_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "generations.csv"

            with patch(
                "ga.artifacts.os.replace",
                side_effect=OSError("replace failed"),
            ):
                with self.assertRaisesRegex(OSError, "replace failed"):
                    write_generations_csv(sample_result(), target)

            self.assertEqual(list(root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
