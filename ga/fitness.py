import math
from dataclasses import dataclass
from numbers import Real

from game.match_runner import MatchConfig, run_match

from .genome import BotGenome


def _validated_weight(name, value):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number")
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return value


@dataclass(frozen=True, slots=True)
class FitnessConfig:
    seeds: tuple[int, ...] = (20260728, 20260729)
    match_config: MatchConfig = MatchConfig(
        dt=1 / 60,
        max_steps=1800,
        score_limit=3,
    )
    opponent_genome: BotGenome = BotGenome(260.0, 0.0, 8.0)
    score_weight: float = 100.0
    return_weight: float = 1.0

    def __post_init__(self):
        try:
            seeds = tuple(self.seeds)
        except TypeError as error:
            raise TypeError("seeds must be iterable") from error
        if not seeds:
            raise ValueError("seeds must not be empty")
        if any(type(seed) is not int for seed in seeds):
            raise TypeError("every seed must be an int")
        object.__setattr__(self, "seeds", seeds)

        if not isinstance(self.match_config, MatchConfig):
            raise TypeError("match_config must be a MatchConfig")
        if not isinstance(self.opponent_genome, BotGenome):
            raise TypeError("opponent_genome must be a BotGenome")

        score_weight = _validated_weight("score_weight", self.score_weight)
        return_weight = _validated_weight("return_weight", self.return_weight)
        if score_weight == 0 and return_weight == 0:
            raise ValueError("at least one fitness weight must be positive")
        object.__setattr__(self, "score_weight", score_weight)
        object.__setattr__(self, "return_weight", return_weight)

    def to_dict(self):
        return {
            "seeds": list(self.seeds),
            "match_config": self.match_config.to_dict(),
            "opponent_genome": self.opponent_genome.to_dict(),
            "score_weight": self.score_weight,
            "return_weight": self.return_weight,
        }


@dataclass(frozen=True, slots=True)
class GenomeEvaluation:
    genome: BotGenome
    fitness: float
    matches: int
    wins: int
    draws: int
    losses: int
    points_for: int
    points_against: int
    returns: int

    def to_dict(self):
        return {
            "genome": self.genome.to_dict(),
            "fitness": self.fitness,
            "matches": self.matches,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "points_for": self.points_for,
            "points_against": self.points_against,
            "returns": self.returns,
        }


def evaluate_genome(
    genome: BotGenome,
    config: FitnessConfig = FitnessConfig(),
) -> GenomeEvaluation:
    if not isinstance(genome, BotGenome):
        raise TypeError("genome must be a BotGenome")
    if not isinstance(config, FitnessConfig):
        raise TypeError("config must be a FitnessConfig")

    total_fitness = 0.0
    matches = 0
    wins = 0
    draws = 0
    losses = 0
    points_for = 0
    points_against = 0
    returns = 0

    for seed in config.seeds:
        left_result = run_match(
            genome,
            config.opponent_genome,
            seed=seed,
            config=config.match_config,
        )
        left_score = left_result.left_score
        left_against = left_result.right_score
        left_returns = left_result.left_returns

        right_result = run_match(
            config.opponent_genome,
            genome,
            seed=seed,
            config=config.match_config,
        )
        right_score = right_result.right_score
        right_against = right_result.left_score
        right_returns = right_result.right_returns

        for candidate_score, opponent_score, candidate_returns in (
            (left_score, left_against, left_returns),
            (right_score, right_against, right_returns),
        ):
            matches += 1
            points_for += candidate_score
            points_against += opponent_score
            returns += candidate_returns
            total_fitness += (
                config.score_weight * (candidate_score - opponent_score)
                + config.return_weight * candidate_returns
            )

            if candidate_score > opponent_score:
                wins += 1
            elif candidate_score < opponent_score:
                losses += 1
            else:
                draws += 1

    return GenomeEvaluation(
        genome=genome,
        fitness=total_fitness / (2 * len(config.seeds)),
        matches=matches,
        wins=wins,
        draws=draws,
        losses=losses,
        points_for=points_for,
        points_against=points_against,
        returns=returns,
    )
