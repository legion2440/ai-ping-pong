import random
from collections.abc import Sequence

from .fitness import GenomeEvaluation
from .genome import BotGenome


def tournament_select(
    population: Sequence[GenomeEvaluation],
    tournament_size: int,
    rng: random.Random,
) -> BotGenome:
    if not population:
        raise ValueError("population must not be empty")
    if type(tournament_size) is not int:
        raise TypeError("tournament_size must be an int")
    if tournament_size <= 0:
        raise ValueError("tournament_size must be positive")
    if tournament_size > len(population):
        raise ValueError("tournament_size cannot exceed population size")

    participants = rng.sample(population, tournament_size)
    return max(participants, key=lambda evaluation: evaluation.fitness).genome
