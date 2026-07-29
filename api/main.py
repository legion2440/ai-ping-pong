"""Command-line entry point for the generation fitness API."""
import os
import sys
from pathlib import Path

_INVOCATION_CWD_ENV = "_AI_PING_PONG_API_INVOCATION_CWD"
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__" and __package__ is None:
    os.environ[_INVOCATION_CWD_ENV] = os.getcwd()
    os.chdir(PROJECT_ROOT)
    os.execv(
        sys.executable,
        [sys.executable, "-m", "api.main", *sys.argv[1:]],
    )

INVOCATION_CWD = Path(
    os.environ.pop(_INVOCATION_CWD_ENV, os.getcwd())
).resolve()

import argparse

import uvicorn

from .app import DEFAULT_GENERATIONS_PATH, create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Serve generation fitness data through a read-only API",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--generations-path", type=Path, default=None)
    return parser


def resolve_generations_path(path: Path | None) -> Path:
    if path is None:
        return DEFAULT_GENERATIONS_PATH
    if path.is_absolute():
        return path
    return INVOCATION_CWD / path


def main(argv=None):
    arguments = build_parser().parse_args(argv)
    generations_path = resolve_generations_path(arguments.generations_path)
    application = create_app(generations_path)
    uvicorn.run(
        application,
        host=arguments.host,
        port=arguments.port,
    )


if __name__ == "__main__":
    main()
