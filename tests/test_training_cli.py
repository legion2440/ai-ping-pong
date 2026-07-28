import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ga.fitness import FitnessConfig
from ga.genetic_algorithm import (
    EvolutionConfig,
    EvolutionResult,
    GenerationStats,
    main,
)
from ga.genome import BotGenome

FIRST_GENOME = BotGenome(200.0, 0.1, 5.0)
BEST_GENOME = BotGenome(320.0, 0.05, 8.0)


def fake_evolve(evolution_config, fitness_config, *, on_generation=None):
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
    if on_generation is not None:
        for stats in history:
            on_generation(stats)
    return EvolutionResult(
        evolution_config=evolution_config,
        fitness_config=fitness_config,
        best_genome=BEST_GENOME,
        best_fitness=20.0,
        history=history,
    )


class InProcessTrainingCliTests(unittest.TestCase):
    def _run_main(self, invocation_cwd, arguments):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch(
            "ga.genetic_algorithm.INVOCATION_CWD",
            invocation_cwd,
        ), patch(
            "ga.genetic_algorithm.evolve",
            side_effect=fake_evolve,
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            main(arguments)
        return stdout.getvalue(), stderr.getvalue()

    def test_default_cli_creates_artifacts_and_separates_output_streams(self):
        with tempfile.TemporaryDirectory() as directory:
            invocation_cwd = Path(directory)

            stdout, stderr = self._run_main(invocation_cwd, [])

            csv_path = invocation_cwd / "logs" / "generations.csv"
            model_path = invocation_cwd / "models" / "best_bot.json"
            self.assertTrue(csv_path.is_file())
            self.assertTrue(model_path.is_file())
            self.assertEqual(len(csv_path.read_text().splitlines()), 3)

        self.assertEqual(len(stdout.splitlines()), 1)
        self.assertEqual(json.loads(stdout)["best_fitness"], 20.0)
        self.assertEqual(
            stderr.splitlines(),
            [
                "generation=0 best=10.5 mean=2.25 worst=-5.0 "
                "genome=200.0,0.1,5.0",
                "generation=1 best=20.0 mean=12.75 worst=1.5 "
                "genome=320.0,0.05,8.0",
            ],
        )
        self.assertNotIn("pygame", stdout.lower())
        self.assertNotIn("pygame", stderr.lower())

    def test_quiet_suppresses_progress_but_keeps_json_and_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            invocation_cwd = Path(directory)

            stdout, stderr = self._run_main(invocation_cwd, ["--quiet"])

            self.assertTrue(
                (invocation_cwd / "logs" / "generations.csv").is_file()
            )
            self.assertTrue(
                (invocation_cwd / "models" / "best_bot.json").is_file()
            )

        self.assertEqual(len(stdout.splitlines()), 1)
        self.assertEqual(stderr, "")

    def test_no_artifacts_keeps_progress_and_creates_no_files(self):
        with tempfile.TemporaryDirectory() as directory:
            invocation_cwd = Path(directory)

            stdout, stderr = self._run_main(
                invocation_cwd,
                ["--no-artifacts"],
            )

            self.assertEqual(list(invocation_cwd.iterdir()), [])

        self.assertEqual(len(stdout.splitlines()), 1)
        self.assertEqual(len(stderr.splitlines()), 2)

    def test_custom_relative_paths_use_patched_invocation_cwd(self):
        with tempfile.TemporaryDirectory() as directory:
            invocation_cwd = Path(directory)

            self._run_main(
                invocation_cwd,
                [
                    "--quiet",
                    "--log-path",
                    "reports/training.csv",
                    "--model-path",
                    "saved/model.json",
                ],
            )

            self.assertTrue(
                (invocation_cwd / "reports" / "training.csv").is_file()
            )
            self.assertTrue(
                (invocation_cwd / "saved" / "model.json").is_file()
            )

    def test_absolute_paths_are_used_without_rebasing(self):
        with tempfile.TemporaryDirectory() as invocation_directory:
            with tempfile.TemporaryDirectory() as output_directory:
                invocation_cwd = Path(invocation_directory)
                output_root = Path(output_directory)
                csv_path = output_root / "training.csv"
                model_path = output_root / "model.json"

                self._run_main(
                    invocation_cwd,
                    [
                        "--quiet",
                        "--log-path",
                        str(csv_path),
                        "--model-path",
                        str(model_path),
                    ],
                )

                self.assertTrue(csv_path.is_file())
                self.assertTrue(model_path.is_file())
                self.assertEqual(list(invocation_cwd.iterdir()), [])

    def test_invalid_log_path_becomes_argparse_error_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            invocation_cwd = Path(directory)
            blocked_path = invocation_cwd / "blocked"
            blocked_path.mkdir()
            stdout = io.StringIO()
            stderr = io.StringIO()

            with patch(
                "ga.genetic_algorithm.INVOCATION_CWD",
                invocation_cwd,
            ), patch(
                "ga.genetic_algorithm.evolve",
                side_effect=fake_evolve,
            ), redirect_stdout(stdout), redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as raised:
                    main(["--quiet", "--log-path", "blocked"])

        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("error:", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_successful_csv_is_not_rolled_back_when_model_write_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            invocation_cwd = Path(directory)
            blocked_model_path = invocation_cwd / "blocked-model"
            blocked_model_path.mkdir()
            stderr = io.StringIO()

            with patch(
                "ga.genetic_algorithm.INVOCATION_CWD",
                invocation_cwd,
            ), patch(
                "ga.genetic_algorithm.evolve",
                side_effect=fake_evolve,
            ), redirect_stdout(io.StringIO()), redirect_stderr(stderr):
                with self.assertRaises(SystemExit):
                    main(
                        [
                            "--quiet",
                            "--log-path",
                            "training.csv",
                            "--model-path",
                            "blocked-model",
                        ]
                    )

            self.assertTrue((invocation_cwd / "training.csv").is_file())
            self.assertTrue(blocked_model_path.is_dir())
            self.assertNotIn("Traceback", stderr.getvalue())


class TrainingCliEntrypointTests(unittest.TestCase):
    def test_module_direct_and_external_cwd_match(self):
        repository_root = Path(__file__).resolve().parents[1]
        script_path = repository_root / "ga" / "genetic_algorithm.py"
        common_arguments = [
            "--seed",
            "-1",
            "--population-size",
            "2",
            "--generations",
            "1",
            "--elite-count",
            "1",
            "--tournament-size",
            "2",
            "--match-seeds=-2",
            "--match-max-steps",
            "2",
            "--match-score-limit",
            "1",
            "--quiet",
        ]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            module_root = root / "module"
            direct_root = root / "direct"
            external_root = root / "external"
            module_root.mkdir()
            direct_root.mkdir()
            external_root.mkdir()

            cases = (
                (
                    [sys.executable, "-m", "ga.genetic_algorithm"],
                    repository_root,
                    module_root,
                    True,
                ),
                (
                    [sys.executable, str(script_path)],
                    repository_root,
                    direct_root,
                    True,
                ),
                (
                    [sys.executable, str(script_path)],
                    external_root,
                    external_root,
                    False,
                ),
            )
            completed = []

            for command, cwd, output_root, use_absolute_paths in cases:
                if use_absolute_paths:
                    log_path = output_root / "logs" / "generations.csv"
                    model_path = output_root / "models" / "best_bot.json"
                else:
                    log_path = Path("logs/generations.csv")
                    model_path = Path("models/best_bot.json")

                process = subprocess.run(
                    command
                    + common_arguments
                    + [
                        "--log-path",
                        str(log_path),
                        "--model-path",
                        str(model_path),
                    ],
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(process.stderr, "")
                self.assertEqual(len(process.stdout.splitlines()), 1)
                self.assertNotIn("pygame", process.stdout.lower())
                completed.append(
                    (
                        process.stdout,
                        (output_root / "logs" / "generations.csv").read_bytes(),
                        (output_root / "models" / "best_bot.json").read_bytes(),
                    )
                )

        self.assertEqual(completed[0], completed[1])
        self.assertEqual(completed[1], completed[2])


if __name__ == "__main__":
    unittest.main()
