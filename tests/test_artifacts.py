import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ga.artifacts import (
    CSV_HEADER,
    GenerationRecord,
    atomic_write_text,
    load_best_genome,
    load_generation_history,
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


class GenerationHistoryLoadingTests(unittest.TestCase):
    def _write_history(self, directory, rows, header=CSV_HEADER):
        path = Path(directory) / "generations.csv"
        lines = [",".join(header)]
        lines.extend(",".join(str(value) for value in row) for row in rows)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def test_canonical_history_loads_in_order_with_converted_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_history(
                directory,
                [
                    (0, 10.5, 2.25, -5, 200, 0.1, 5),
                    (1, 20, 12.75, 1.5, 320, 0.05, 8),
                ],
            )

            records = load_generation_history(path)

        self.assertEqual(
            records,
            (
                GenerationRecord(
                    generation=0,
                    best_fitness=10.5,
                    mean_fitness=2.25,
                    worst_fitness=-5.0,
                    genome=FIRST_GENOME,
                ),
                GenerationRecord(
                    generation=1,
                    best_fitness=20.0,
                    mean_fitness=12.75,
                    worst_fitness=1.5,
                    genome=BEST_GENOME,
                ),
            ),
        )
        self.assertIsInstance(records, tuple)
        self.assertIsInstance(records[0].generation, int)
        self.assertIsInstance(records[0].best_fitness, float)

    def test_writer_and_loader_round_trip(self):
        result = sample_result()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "generations.csv"
            write_generations_csv(result, path)

            records = load_generation_history(str(path))

        self.assertEqual(
            [record.genome for record in records],
            [stats.best_genome for stats in result.history],
        )
        self.assertEqual(
            [record.best_fitness for record in records],
            [stats.best_fitness for stats in result.history],
        )

    def test_empty_file_and_header_only_file_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            empty_path = Path(directory) / "empty.csv"
            empty_path.write_text("", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_generation_history(empty_path)

            header_only_path = Path(directory) / "header-only.csv"
            header_only_path.write_text(
                ",".join(CSV_HEADER) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "at least one"):
                load_generation_history(header_only_path)

    def test_header_must_have_exact_columns_and_order(self):
        invalid_headers = (
            CSV_HEADER[:-1],
            CSV_HEADER + ("extra",),
            tuple(reversed(CSV_HEADER)),
        )

        for header in invalid_headers:
            with self.subTest(header=header):
                with tempfile.TemporaryDirectory() as directory:
                    path = self._write_history(
                        directory,
                        [(0, 1, 1, 1, 200, 0.1, 5)],
                        header=header,
                    )

                    with self.assertRaisesRegex(ValueError, "header"):
                        load_generation_history(path)

    def test_header_error_reports_physical_line_one(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_history(
                directory,
                [(0, 1, 1, 1, 200, 0.1, 5)],
                header=tuple(reversed(CSV_HEADER)),
            )

            with self.assertRaisesRegex(ValueError, r"line 1\b"):
                load_generation_history(path)

    def test_row_error_reports_physical_csv_line(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "generations.csv"
            path.write_text(
                ",".join(CSV_HEADER)
                + "\n\n"
                + "0,invalid,1,1,200,0.1,5\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, r"line 3\b"):
                load_generation_history(path)

    def test_row_must_match_header_width(self):
        for row in (
            (0, 1, 1, 1, 200, 0.1),
            (0, 1, 1, 1, 200, 0.1, 5, "extra"),
        ):
            with self.subTest(row=row):
                with tempfile.TemporaryDirectory() as directory:
                    path = self._write_history(directory, [row])

                    with self.assertRaisesRegex(ValueError, "header"):
                        load_generation_history(path)

    def test_fitness_values_must_be_numeric_and_finite(self):
        for value in ("invalid", "nan", "inf", "-inf"):
            with self.subTest(value=value):
                with tempfile.TemporaryDirectory() as directory:
                    path = self._write_history(
                        directory,
                        [(0, value, 1, 1, 200, 0.1, 5)],
                    )

                    with self.assertRaises(ValueError):
                        load_generation_history(path)

    def test_invalid_genome_is_rejected_with_original_cause(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_history(
                directory,
                [(0, 1, 1, 1, 1000, 0.1, 5)],
            )

            with self.assertRaisesRegex(ValueError, "invalid genome") as raised:
                load_generation_history(path)

        self.assertIsInstance(raised.exception.__cause__, ValueError)

    def test_generations_must_start_at_zero_without_gaps_or_duplicates(self):
        invalid_generations = (
            (1,),
            (0, 2),
            (0, 0),
        )

        for generations in invalid_generations:
            with self.subTest(generations=generations):
                with tempfile.TemporaryDirectory() as directory:
                    rows = [
                        (generation, 1, 1, 1, 200, 0.1, 5)
                        for generation in generations
                    ]
                    path = self._write_history(directory, rows)

                    with self.assertRaisesRegex(ValueError, "consecutive"):
                        load_generation_history(path)

    def test_missing_file_preserves_file_not_found_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.csv"

            with self.assertRaises(FileNotFoundError):
                load_generation_history(path)


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
    def test_public_atomic_writer_creates_parents_and_exact_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "report.txt"

            atomic_write_text(path, "first\n")
            atomic_write_text(path, "second\n")

            self.assertEqual(path.read_bytes(), b"second\n")
            self.assertEqual(
                {item.name for item in path.parent.iterdir()},
                {"report.txt"},
            )

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
