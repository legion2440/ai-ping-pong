import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ga.artifacts import CSV_HEADER, GenerationRecord
from ga.evaluation import (
    EvaluationConfig,
    EvaluationReport,
    GenerationEvaluation,
    main,
)
from ga.fitness import GenomeEvaluation
from ga.genome import BotGenome

INITIAL_GENOME = BotGenome(200.0, 0.1, 5.0)
FINAL_GENOME = BotGenome(320.0, 0.02, 4.0)
RECORDS = (
    GenerationRecord(0, 10.0, -5.0, -20.0, INITIAL_GENOME),
    GenerationRecord(1, 30.0, 8.0, -2.0, FINAL_GENOME),
)


def fake_evaluation(genome, fitness):
    return GenomeEvaluation(
        genome=genome,
        fitness=fitness,
        matches=2,
        wins=1,
        draws=1,
        losses=0,
        points_for=2,
        points_against=1,
        returns=3,
    )


def fake_report(config):
    generations = (
        GenerationEvaluation(
            generation=0,
            genome=INITIAL_GENOME,
            training_best_fitness=10.0,
            training_mean_fitness=-5.0,
            training_worst_fitness=-20.0,
            held_out=fake_evaluation(INITIAL_GENOME, -4.0),
        ),
        GenerationEvaluation(
            generation=1,
            genome=FINAL_GENOME,
            training_best_fitness=30.0,
            training_mean_fitness=8.0,
            training_worst_fitness=-2.0,
            held_out=fake_evaluation(FINAL_GENOME, 6.0),
        ),
    )
    return EvaluationReport(
        config=config,
        generations=generations,
        final_vs_initial=fake_evaluation(FINAL_GENOME, 12.0),
        training_mean_delta=13.0,
        held_out_fitness_delta=10.0,
        training_mean_improved=True,
        held_out_fitness_improved=True,
        final_outperformed_initial=True,
    )


class InProcessEvaluationCliTests(unittest.TestCase):
    def _run_main(
        self,
        arguments,
        *,
        project_root,
        invocation_cwd,
    ):
        stdout = io.StringIO()
        stderr = io.StringIO()

        def evaluator(records, config):
            self.assertIs(records, RECORDS)
            return fake_report(config)

        with patch(
            "ga.evaluation.PROJECT_ROOT",
            project_root,
        ), patch(
            "ga.evaluation.INVOCATION_CWD",
            invocation_cwd,
        ), patch(
            "ga.evaluation.load_generation_history",
            return_value=RECORDS,
        ) as loader, patch(
            "ga.evaluation.evaluate_generation_history",
            side_effect=evaluator,
        ) as evaluate, redirect_stdout(stdout), redirect_stderr(stderr):
            main(arguments)

        return stdout.getvalue(), stderr.getvalue(), loader, evaluate

    def test_defaults_use_canonical_project_paths_and_write_artifacts(self):
        with tempfile.TemporaryDirectory() as project_directory:
            with tempfile.TemporaryDirectory() as invocation_directory:
                project_root = Path(project_directory)
                invocation_cwd = Path(invocation_directory)

                stdout, stderr, loader, evaluate = self._run_main(
                    [],
                    project_root=project_root,
                    invocation_cwd=invocation_cwd,
                )

                report_path = project_root / "reports" / "evaluation.json"
                chart_path = project_root / "docs" / "fitness_progress.svg"
                self.assertTrue(report_path.is_file())
                self.assertTrue(chart_path.is_file())
                self.assertEqual(
                    json.loads(stdout),
                    json.loads(report_path.read_text(encoding="utf-8")),
                )

        loader.assert_called_once_with(
            project_root / "logs" / "generations.csv"
        )
        self.assertEqual(evaluate.call_count, 1)
        self.assertEqual(len(stdout.splitlines()), 1)
        self.assertEqual(stderr, "")

    def test_relative_paths_and_cli_protocol_values_use_invocation_cwd(self):
        with tempfile.TemporaryDirectory() as project_directory:
            with tempfile.TemporaryDirectory() as invocation_directory:
                project_root = Path(project_directory)
                invocation_cwd = Path(invocation_directory)

                _, _, loader, evaluate = self._run_main(
                    [
                        "--generations-path",
                        "input/history.csv",
                        "--report-path",
                        "output/report.json",
                        "--chart-path",
                        "output/chart.svg",
                        "--seeds=-2,3",
                        "--match-dt",
                        "0.25",
                        "--match-max-steps",
                        "10",
                        "--match-score-limit",
                        "2",
                        "--baseline=260,0,8",
                    ],
                    project_root=project_root,
                    invocation_cwd=invocation_cwd,
                )

                self.assertTrue(
                    (invocation_cwd / "output" / "report.json").is_file()
                )
                self.assertTrue(
                    (invocation_cwd / "output" / "chart.svg").is_file()
                )

        loader.assert_called_once_with(
            invocation_cwd / "input" / "history.csv"
        )
        config = evaluate.call_args.args[1]
        self.assertEqual(config.seeds, (-2, 3))
        self.assertEqual(config.match_config.dt, 0.25)
        self.assertEqual(config.match_config.max_steps, 10)
        self.assertEqual(config.match_config.score_limit, 2)
        self.assertEqual(config.baseline_genome, BotGenome(260, 0, 8))

    def test_absolute_paths_are_not_rebased(self):
        with tempfile.TemporaryDirectory() as project_directory:
            with tempfile.TemporaryDirectory() as invocation_directory:
                with tempfile.TemporaryDirectory() as path_directory:
                    project_root = Path(project_directory)
                    invocation_cwd = Path(invocation_directory)
                    root = Path(path_directory)
                    history_path = root / "history.csv"
                    report_path = root / "report.json"
                    chart_path = root / "chart.svg"

                    _, _, loader, _ = self._run_main(
                        [
                            "--generations-path",
                            str(history_path),
                            "--report-path",
                            str(report_path),
                            "--chart-path",
                            str(chart_path),
                        ],
                        project_root=project_root,
                        invocation_cwd=invocation_cwd,
                    )

                    self.assertTrue(report_path.is_file())
                    self.assertTrue(chart_path.is_file())

        loader.assert_called_once_with(history_path)

    def test_no_artifacts_still_prints_one_json_line(self):
        with tempfile.TemporaryDirectory() as project_directory:
            with tempfile.TemporaryDirectory() as invocation_directory:
                project_root = Path(project_directory)
                invocation_cwd = Path(invocation_directory)

                stdout, stderr, _, _ = self._run_main(
                    ["--no-artifacts"],
                    project_root=project_root,
                    invocation_cwd=invocation_cwd,
                )

                self.assertEqual(list(project_root.iterdir()), [])
                self.assertEqual(list(invocation_cwd.iterdir()), [])

        self.assertEqual(len(stdout.splitlines()), 1)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout)["schema_version"], 1)

    def test_invalid_config_and_loading_errors_have_no_traceback(self):
        stderr = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as raised:
                main(["--seeds="])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("error:", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch(
                "ga.evaluation.PROJECT_ROOT",
                root,
            ), patch(
                "ga.evaluation.INVOCATION_CWD",
                root,
            ), patch(
                "ga.evaluation.load_generation_history",
                side_effect=ValueError("invalid history"),
            ), redirect_stdout(io.StringIO()), redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as raised:
                    main(["--no-artifacts"])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("error: invalid history", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


class EvaluationCliEntrypointTests(unittest.TestCase):
    def test_module_direct_and_external_cwd_match_stdout_and_artifacts(self):
        repository_root = Path(__file__).resolve().parents[1]
        script_path = repository_root / "ga" / "evaluation.py"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            history_path = root / "history.csv"
            history_path.write_text(
                ",".join(CSV_HEADER)
                + "\n"
                + "0,1.0,0.0,-1.0,260.0,0.0,8.0\n",
                encoding="utf-8",
            )
            external_cwd = root / "external"
            external_cwd.mkdir()
            cases = (
                (
                    [sys.executable, "-m", "ga.evaluation"],
                    repository_root,
                ),
                (
                    [sys.executable, str(script_path)],
                    repository_root,
                ),
                (
                    [sys.executable, str(script_path)],
                    external_cwd,
                ),
            )
            results = []
            for index, (command, cwd) in enumerate(cases):
                output_root = root / f"output-{index}"
                arguments = [
                    "--generations-path",
                    str(history_path),
                    "--report-path",
                    str(output_root / "report.json"),
                    "--chart-path",
                    str(output_root / "chart.svg"),
                    "--seeds=-2",
                    "--match-max-steps",
                    "2",
                    "--match-score-limit",
                    "1",
                ]
                completed = subprocess.run(
                    [*command, *arguments],
                    cwd=cwd,
                    text=True,
                    capture_output=True,
                    check=True,
                )
                results.append(
                    (
                        completed.stdout,
                        completed.stderr,
                        (output_root / "report.json").read_bytes(),
                        (output_root / "chart.svg").read_bytes(),
                    )
                )

        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0], results[2])
        self.assertEqual(len(results[0][0].splitlines()), 1)
        self.assertEqual(results[0][1], "")


if __name__ == "__main__":
    unittest.main()
