import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.app import DEFAULT_GENERATIONS_PATH, create_app
from api.main import main, resolve_generations_path
from ga.artifacts import CSV_HEADER

FIRST_ROW = (
    0,
    10.5,
    2.25,
    -5.0,
    200.0,
    0.1,
    5.0,
)
SECOND_ROW = (
    1,
    20.0,
    12.75,
    1.5,
    320.0,
    0.05,
    8.0,
)
THIRD_ROW = (
    2,
    30.25,
    18.0,
    3.0,
    350.0,
    0.02,
    4.0,
)


def write_history(path, rows):
    with Path(path).open(
        "w",
        encoding="utf-8",
        newline="",
    ) as history_file:
        writer = csv.writer(history_file, lineterminator="\n")
        writer.writerow(CSV_HEADER)
        writer.writerows(rows)


class GenerationApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.history_path = self.root / "generations.csv"
        write_history(self.history_path, (FIRST_ROW, SECOND_ROW))
        self.client = TestClient(create_app(self.history_path))

    def tearDown(self):
        self.client.close()
        self.temporary_directory.cleanup()

    def test_health_does_not_depend_on_generation_log(self):
        self.history_path.unlink()

        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_root_describes_read_only_api_without_local_path(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "name": "AI Ping Pong API",
                "read_only": True,
                "source": "logs/generations.csv",
                "docs": "/docs",
            },
        )
        self.assertNotIn(str(self.root), response.text)

    def test_generations_preserve_order_and_include_genomes(self):
        response = self.client.get("/generations")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            [record["generation"] for record in payload],
            [0, 1],
        )
        self.assertEqual(
            payload[0],
            {
                "generation": 0,
                "best_fitness": 10.5,
                "mean_fitness": 2.25,
                "worst_fitness": -5.0,
                "genome": {
                    "paddle_speed": 200.0,
                    "reaction_time": 0.1,
                    "movement_threshold": 5.0,
                },
            },
        )

    def test_fitness_omits_genomes(self):
        response = self.client.get("/fitness")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {
                    "generation": 0,
                    "best_fitness": 10.5,
                    "mean_fitness": 2.25,
                    "worst_fitness": -5.0,
                },
                {
                    "generation": 1,
                    "best_fitness": 20.0,
                    "mean_fitness": 12.75,
                    "worst_fitness": 1.5,
                },
            ],
        )
        self.assertNotIn("genome", response.text)

    def test_generation_endpoint_returns_requested_record(self):
        response = self.client.get("/generations/1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["generation"], 1)
        self.assertEqual(response.json()["genome"]["paddle_speed"], 320.0)

    def test_unknown_and_negative_generations_return_stable_404(self):
        for generation in ("2", "-1"):
            with self.subTest(generation=generation):
                response = self.client.get(f"/generations/{generation}")
                self.assertEqual(response.status_code, 404)
                self.assertEqual(
                    response.json(),
                    {"detail": "generation not found"},
                )

    def test_non_integer_generation_uses_fastapi_validation(self):
        response = self.client.get("/generations/not-an-int")

        self.assertEqual(response.status_code, 422)
        self.assertIn("detail", response.json())

    def test_missing_log_returns_stable_404_without_local_details(self):
        self.history_path.unlink()

        response = self.client.get("/generations")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {"detail": "generation log not found"},
        )
        self.assertNotIn(str(self.root), response.text)
        self.assertNotIn("Traceback", response.text)

    def test_invalid_log_returns_stable_500_without_local_details(self):
        self.history_path.write_text(
            "wrong,header\nbroken,row\n",
            encoding="utf-8",
        )

        response = self.client.get("/fitness")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {"detail": "generation log is invalid"},
        )
        self.assertNotIn(str(self.root), response.text)
        self.assertNotIn("Traceback", response.text)

    def test_unreadable_text_is_reported_as_invalid_log(self):
        self.history_path.write_bytes(b"\xff\xfe\xfa")

        response = self.client.get("/generations")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {"detail": "generation log is invalid"},
        )

    def test_log_is_reloaded_on_every_request(self):
        first_response = self.client.get("/generations")
        write_history(
            self.history_path,
            (FIRST_ROW, SECOND_ROW, THIRD_ROW),
        )

        second_response = self.client.get("/generations")

        self.assertEqual(len(first_response.json()), 2)
        self.assertEqual(
            [item["generation"] for item in second_response.json()],
            [0, 1, 2],
        )

    def test_get_requests_do_not_change_log_bytes(self):
        original = self.history_path.read_bytes()

        for endpoint in (
            "/",
            "/health",
            "/generations",
            "/generations/0",
            "/fitness",
            "/docs",
        ):
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.client.get(endpoint).status_code, 200)

        self.assertEqual(self.history_path.read_bytes(), original)

    def test_openapi_contains_only_the_read_only_business_endpoints(self):
        schema = self.client.get("/openapi.json").json()

        self.assertEqual(
            set(schema["paths"]),
            {
                "/",
                "/health",
                "/generations",
                "/generations/{generation}",
                "/fitness",
            },
        )
        for operations in schema["paths"].values():
            self.assertEqual(set(operations), {"get"})

    def test_factory_uses_passed_path_instead_of_canonical_global(self):
        other_path = self.root / "other.csv"
        write_history(other_path, (FIRST_ROW,))
        with TestClient(create_app(other_path)) as client:
            response = client.get("/generations")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_canonical_history_exposes_generation_23(self):
        with TestClient(create_app(DEFAULT_GENERATIONS_PATH)) as client:
            response = client.get("/generations/23")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["generation"], 23)


class ApiCliTests(unittest.TestCase):
    def test_default_relative_and_absolute_path_resolution(self):
        with tempfile.TemporaryDirectory() as invocation_directory:
            with tempfile.TemporaryDirectory() as path_directory:
                invocation_cwd = Path(invocation_directory)
                absolute_path = Path(path_directory) / "history.csv"
                with patch(
                    "api.main.INVOCATION_CWD",
                    invocation_cwd,
                ):
                    self.assertEqual(
                        resolve_generations_path(None),
                        DEFAULT_GENERATIONS_PATH,
                    )
                    self.assertEqual(
                        resolve_generations_path(
                            Path("custom/history.csv")
                        ),
                        invocation_cwd / "custom" / "history.csv",
                    )
                    self.assertEqual(
                        resolve_generations_path(absolute_path),
                        absolute_path,
                    )

    def test_cli_passes_created_app_host_and_port_to_uvicorn(self):
        with tempfile.TemporaryDirectory() as directory:
            invocation_cwd = Path(directory)
            application = object()
            with patch(
                "api.main.INVOCATION_CWD",
                invocation_cwd,
            ), patch(
                "api.main.create_app",
                return_value=application,
            ) as create, patch(
                "api.main.uvicorn.run"
            ) as run:
                main(
                    [
                        "--host",
                        "0.0.0.0",
                        "--port",
                        "9001",
                        "--generations-path",
                        "input/history.csv",
                    ]
                )

        create.assert_called_once_with(
            invocation_cwd / "input" / "history.csv"
        )
        run.assert_called_once_with(
            application,
            host="0.0.0.0",
            port=9001,
        )

    def test_cli_uses_canonical_default_path(self):
        application = object()
        with patch(
            "api.main.create_app",
            return_value=application,
        ) as create, patch(
            "api.main.uvicorn.run"
        ):
            main([])

        create.assert_called_once_with(DEFAULT_GENERATIONS_PATH)

    def test_module_and_direct_help_entrypoints_succeed(self):
        repository_root = Path(__file__).resolve().parents[1]
        script_path = repository_root / "api" / "main.py"

        with tempfile.TemporaryDirectory() as directory:
            cases = (
                (
                    [sys.executable, "-m", "api.main", "--help"],
                    repository_root,
                ),
                (
                    [sys.executable, str(script_path), "--help"],
                    Path(directory),
                ),
            )
            for command, cwd in cases:
                with self.subTest(command=command, cwd=cwd):
                    completed = subprocess.run(
                        command,
                        cwd=cwd,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(
                        completed.returncode,
                        0,
                        completed.stderr,
                    )
                    self.assertIn(
                        "--generations-path",
                        completed.stdout,
                    )
                    self.assertNotIn("Traceback", completed.stderr)


if __name__ == "__main__":
    unittest.main()
