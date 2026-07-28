import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import sys
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    project_root = Path(__file__).resolve().parent.parent
    os.chdir(project_root)
    os.execv(
        sys.executable,
        [sys.executable, "-m", "game.match_runner", *sys.argv[1:]],
    )

import argparse
import json
import math
import random
from dataclasses import dataclass
from numbers import Real

from ga.genome import BotGenome

from .controllers import BotController
from .simulation import MatchSimulation
from .utils import COURT_H, COURT_Y


@dataclass(frozen=True, slots=True)
class MatchConfig:
    dt: float = 1 / 60
    max_steps: int = 3600
    score_limit: int = 5

    def __post_init__(self):
        if isinstance(self.dt, bool) or not isinstance(self.dt, Real):
            raise TypeError("dt must be a real number")
        dt = float(self.dt)
        if not math.isfinite(dt) or dt <= 0:
            raise ValueError("dt must be a finite positive number")
        object.__setattr__(self, "dt", dt)

        if type(self.max_steps) is not int:
            raise TypeError("max_steps must be an int")
        if self.max_steps <= 0:
            raise ValueError("max_steps must be positive")

        if type(self.score_limit) is not int:
            raise TypeError("score_limit must be an int")
        if self.score_limit <= 0:
            raise ValueError("score_limit must be positive")

    def to_dict(self):
        return {
            "dt": self.dt,
            "max_steps": self.max_steps,
            "score_limit": self.score_limit,
        }


@dataclass(frozen=True, slots=True)
class MatchResult:
    seed: int
    config: MatchConfig
    left_genome: BotGenome
    right_genome: BotGenome
    steps: int
    simulated_seconds: float
    left_score: int
    right_score: int
    left_returns: int
    right_returns: int
    longest_rally: int
    winner: str
    termination_reason: str

    def to_dict(self):
        return {
            "seed": self.seed,
            "config": self.config.to_dict(),
            "left_genome": self.left_genome.to_dict(),
            "right_genome": self.right_genome.to_dict(),
            "steps": self.steps,
            "simulated_seconds": self.simulated_seconds,
            "left_score": self.left_score,
            "right_score": self.right_score,
            "left_returns": self.left_returns,
            "right_returns": self.right_returns,
            "longest_rally": self.longest_rally,
            "winner": self.winner,
            "termination_reason": self.termination_reason,
        }


def run_match(
    left_genome: BotGenome,
    right_genome: BotGenome,
    *,
    seed: int,
    config: MatchConfig = MatchConfig(),
) -> MatchResult:
    if type(seed) is not int:
        raise TypeError("seed must be an int")
    if not isinstance(config, MatchConfig):
        raise TypeError("config must be a MatchConfig")

    rng = random.Random(seed)
    simulation = MatchSimulation(rng=rng)
    left_controller = BotController(left_genome)
    right_controller = BotController(right_genome)

    steps = 0
    left_returns = 0
    right_returns = 0
    current_rally = 0
    longest_rally = 0
    termination_reason = "max_steps"

    while steps < config.max_steps:
        left_controller.update(simulation.p1, simulation.ball, config.dt)
        simulation.p1.clamp(COURT_Y, COURT_Y + COURT_H)

        right_controller.update(simulation.p2, simulation.ball, config.dt)
        simulation.p2.clamp(COURT_Y, COURT_Y + COURT_H)

        events = simulation.step(config.dt)
        steps += 1

        if events.left_return:
            left_returns += 1
            current_rally += 1
        if events.right_return:
            right_returns += 1
            current_rally += 1
        if events.point_winner is not None:
            longest_rally = max(longest_rally, current_rally)
            current_rally = 0

        if (
            simulation.score1 >= config.score_limit
            or simulation.score2 >= config.score_limit
        ):
            termination_reason = "score_limit"
            break

    longest_rally = max(longest_rally, current_rally)

    if simulation.score1 > simulation.score2:
        winner = "left"
    elif simulation.score2 > simulation.score1:
        winner = "right"
    else:
        winner = "draw"

    return MatchResult(
        seed=seed,
        config=config,
        left_genome=left_genome,
        right_genome=right_genome,
        steps=steps,
        simulated_seconds=steps * config.dt,
        left_score=simulation.score1,
        right_score=simulation.score2,
        left_returns=left_returns,
        right_returns=right_returns,
        longest_rally=longest_rally,
        winner=winner,
        termination_reason=termination_reason,
    )


def _parse_genome(value):
    try:
        vector = (float(item.strip()) for item in value.split(","))
        return BotGenome.from_vector(vector)
    except (TypeError, ValueError) as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def _build_parser():
    baseline_genome = BotGenome(260.0, 0.0, 8.0)
    parser = argparse.ArgumentParser(description="Run a headless bot-vs-bot match")
    parser.add_argument("--seed", type=int, default=20260728)
    parser.add_argument("--dt", type=float, default=1 / 60)
    parser.add_argument("--max-steps", type=int, default=3600)
    parser.add_argument("--score-limit", type=int, default=5)
    parser.add_argument("--left", type=_parse_genome, default=baseline_genome)
    parser.add_argument("--right", type=_parse_genome, default=baseline_genome)
    return parser


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        config = MatchConfig(
            dt=args.dt,
            max_steps=args.max_steps,
            score_limit=args.score_limit,
        )
        result = run_match(
            args.left,
            args.right,
            seed=args.seed,
            config=config,
        )
    except (TypeError, ValueError) as error:
        parser.error(str(error))

    print(json.dumps(result.to_dict(), sort_keys=True))


if __name__ == "__main__":
    main()
