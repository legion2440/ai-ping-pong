import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import sys
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    project_root = Path(__file__).resolve().parent.parent
    os.chdir(project_root)
    os.execv(
        sys.executable,
        [sys.executable, "-m", "ga.genetic_algorithm", *sys.argv[1:]],
    )

import argparse
import json
import math
import random
from dataclasses import dataclass
from numbers import Real

from game.match_runner import MatchConfig

from .crossover import blend_crossover
from .fitness import FitnessConfig, GenomeEvaluation, evaluate_genome
from .genome import (
    MOVEMENT_THRESHOLD_MAX,
    MOVEMENT_THRESHOLD_MIN,
    PADDLE_SPEED_MAX,
    PADDLE_SPEED_MIN,
    REACTION_TIME_MAX,
    REACTION_TIME_MIN,
    BotGenome,
)
from .mutation import mutate_genome
from .selection import tournament_select


def _validated_probability(name, value):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number")
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"{name} must be finite and between 0 and 1")
    return value


def _validated_positive_float(name, value):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number")
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return value


@dataclass(frozen=True, slots=True)
class EvolutionConfig:
    seed: int = 20260728
    population_size: int = 16
    generations: int = 8
    elite_count: int = 2
    tournament_size: int = 3
    crossover_rate: float = 0.8
    mutation_rate: float = 0.2
    mutation_sigma: float = 0.10

    def __post_init__(self):
        if type(self.seed) is not int:
            raise TypeError("seed must be an int")
        if type(self.population_size) is not int:
            raise TypeError("population_size must be an int")
        if self.population_size < 2:
            raise ValueError("population_size must be at least 2")
        if type(self.generations) is not int:
            raise TypeError("generations must be an int")
        if self.generations < 1:
            raise ValueError("generations must be at least 1")
        if type(self.elite_count) is not int:
            raise TypeError("elite_count must be an int")
        if not 1 <= self.elite_count < self.population_size:
            raise ValueError(
                "elite_count must be positive and smaller than population_size"
            )
        if type(self.tournament_size) is not int:
            raise TypeError("tournament_size must be an int")
        if not 2 <= self.tournament_size <= self.population_size:
            raise ValueError(
                "tournament_size must be between 2 and population_size"
            )

        object.__setattr__(
            self,
            "crossover_rate",
            _validated_probability("crossover_rate", self.crossover_rate),
        )
        object.__setattr__(
            self,
            "mutation_rate",
            _validated_probability("mutation_rate", self.mutation_rate),
        )
        object.__setattr__(
            self,
            "mutation_sigma",
            _validated_positive_float("mutation_sigma", self.mutation_sigma),
        )

    def to_dict(self):
        return {
            "seed": self.seed,
            "population_size": self.population_size,
            "generations": self.generations,
            "elite_count": self.elite_count,
            "tournament_size": self.tournament_size,
            "crossover_rate": self.crossover_rate,
            "mutation_rate": self.mutation_rate,
            "mutation_sigma": self.mutation_sigma,
        }


@dataclass(frozen=True, slots=True)
class GenerationStats:
    generation: int
    best_genome: BotGenome
    best_fitness: float
    mean_fitness: float
    worst_fitness: float

    def to_dict(self):
        return {
            "generation": self.generation,
            "best_genome": self.best_genome.to_dict(),
            "best_fitness": self.best_fitness,
            "mean_fitness": self.mean_fitness,
            "worst_fitness": self.worst_fitness,
        }


@dataclass(frozen=True, slots=True)
class EvolutionResult:
    evolution_config: EvolutionConfig
    fitness_config: FitnessConfig
    best_genome: BotGenome
    best_fitness: float
    history: tuple[GenerationStats, ...]

    def to_dict(self):
        return {
            "evolution_config": self.evolution_config.to_dict(),
            "fitness_config": self.fitness_config.to_dict(),
            "best_genome": self.best_genome.to_dict(),
            "best_fitness": self.best_fitness,
            "history": [item.to_dict() for item in self.history],
        }


def random_genome(rng: random.Random) -> BotGenome:
    return BotGenome(
        paddle_speed=rng.uniform(PADDLE_SPEED_MIN, PADDLE_SPEED_MAX),
        reaction_time=rng.uniform(REACTION_TIME_MIN, REACTION_TIME_MAX),
        movement_threshold=rng.uniform(
            MOVEMENT_THRESHOLD_MIN,
            MOVEMENT_THRESHOLD_MAX,
        ),
    )


def evolve(
    evolution_config: EvolutionConfig = EvolutionConfig(),
    fitness_config: FitnessConfig = FitnessConfig(),
) -> EvolutionResult:
    if not isinstance(evolution_config, EvolutionConfig):
        raise TypeError("evolution_config must be an EvolutionConfig")
    if not isinstance(fitness_config, FitnessConfig):
        raise TypeError("fitness_config must be a FitnessConfig")

    rng = random.Random(evolution_config.seed)
    population = [
        random_genome(rng)
        for _ in range(evolution_config.population_size)
    ]
    history = []
    global_best = None

    for generation in range(evolution_config.generations):
        evaluations = [
            evaluate_genome(genome, fitness_config)
            for genome in population
        ]
        generation_best = max(
            evaluations,
            key=lambda evaluation: evaluation.fitness,
        )
        generation_worst = min(
            evaluations,
            key=lambda evaluation: evaluation.fitness,
        )
        mean_fitness = (
            sum(evaluation.fitness for evaluation in evaluations)
            / len(evaluations)
        )
        history.append(
            GenerationStats(
                generation=generation,
                best_genome=generation_best.genome,
                best_fitness=generation_best.fitness,
                mean_fitness=mean_fitness,
                worst_fitness=generation_worst.fitness,
            )
        )

        if global_best is None or generation_best.fitness > global_best.fitness:
            global_best = generation_best

        if generation == evolution_config.generations - 1:
            break

        ranked = sorted(
            evaluations,
            key=lambda evaluation: evaluation.fitness,
            reverse=True,
        )
        next_population = [
            evaluation.genome
            for evaluation in ranked[: evolution_config.elite_count]
        ]

        while len(next_population) < evolution_config.population_size:
            parent_a = tournament_select(
                evaluations,
                evolution_config.tournament_size,
                rng,
            )
            parent_b = tournament_select(
                evaluations,
                evolution_config.tournament_size,
                rng,
            )

            if rng.random() < evolution_config.crossover_rate:
                child = blend_crossover(parent_a, parent_b, rng)
            else:
                child = parent_a

            child = mutate_genome(
                child,
                rng,
                mutation_rate=evolution_config.mutation_rate,
                mutation_sigma=evolution_config.mutation_sigma,
            )
            next_population.append(child)

        population = next_population

    return EvolutionResult(
        evolution_config=evolution_config,
        fitness_config=fitness_config,
        best_genome=global_best.genome,
        best_fitness=global_best.fitness,
        history=tuple(history),
    )


def _parse_genome(value):
    try:
        vector = (float(item.strip()) for item in value.split(","))
        return BotGenome.from_vector(vector)
    except (TypeError, ValueError) as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def _parse_seeds(value):
    try:
        return tuple(int(item.strip()) for item in value.split(","))
    except ValueError as error:
        raise argparse.ArgumentTypeError("match seeds must be integers") from error


def _build_parser():
    evolution_defaults = EvolutionConfig()
    fitness_defaults = FitnessConfig()
    parser = argparse.ArgumentParser(
        description="Run deterministic genetic algorithm training"
    )
    parser.add_argument("--seed", type=int, default=evolution_defaults.seed)
    parser.add_argument(
        "--population-size",
        type=int,
        default=evolution_defaults.population_size,
    )
    parser.add_argument(
        "--generations",
        type=int,
        default=evolution_defaults.generations,
    )
    parser.add_argument(
        "--elite-count",
        type=int,
        default=evolution_defaults.elite_count,
    )
    parser.add_argument(
        "--tournament-size",
        type=int,
        default=evolution_defaults.tournament_size,
    )
    parser.add_argument(
        "--crossover-rate",
        type=float,
        default=evolution_defaults.crossover_rate,
    )
    parser.add_argument(
        "--mutation-rate",
        type=float,
        default=evolution_defaults.mutation_rate,
    )
    parser.add_argument(
        "--mutation-sigma",
        type=float,
        default=evolution_defaults.mutation_sigma,
    )
    parser.add_argument(
        "--match-seeds",
        type=_parse_seeds,
        default=fitness_defaults.seeds,
    )
    parser.add_argument(
        "--match-dt",
        type=float,
        default=fitness_defaults.match_config.dt,
    )
    parser.add_argument(
        "--match-max-steps",
        type=int,
        default=fitness_defaults.match_config.max_steps,
    )
    parser.add_argument(
        "--match-score-limit",
        type=int,
        default=fitness_defaults.match_config.score_limit,
    )
    parser.add_argument(
        "--opponent",
        type=_parse_genome,
        default=fitness_defaults.opponent_genome,
    )
    parser.add_argument(
        "--score-weight",
        type=float,
        default=fitness_defaults.score_weight,
    )
    parser.add_argument(
        "--return-weight",
        type=float,
        default=fitness_defaults.return_weight,
    )
    return parser


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        evolution_config = EvolutionConfig(
            seed=args.seed,
            population_size=args.population_size,
            generations=args.generations,
            elite_count=args.elite_count,
            tournament_size=args.tournament_size,
            crossover_rate=args.crossover_rate,
            mutation_rate=args.mutation_rate,
            mutation_sigma=args.mutation_sigma,
        )
        match_config = MatchConfig(
            dt=args.match_dt,
            max_steps=args.match_max_steps,
            score_limit=args.match_score_limit,
        )
        fitness_config = FitnessConfig(
            seeds=args.match_seeds,
            match_config=match_config,
            opponent_genome=args.opponent,
            score_weight=args.score_weight,
            return_weight=args.return_weight,
        )
        result = evolve(evolution_config, fitness_config)
    except (TypeError, ValueError) as error:
        parser.error(str(error))

    print(json.dumps(result.to_dict(), sort_keys=True))


if __name__ == "__main__":
    main()
