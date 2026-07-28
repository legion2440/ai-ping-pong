import math
import random
from numbers import Real

from .genome import (
    MOVEMENT_THRESHOLD_MAX,
    MOVEMENT_THRESHOLD_MIN,
    PADDLE_SPEED_MAX,
    PADDLE_SPEED_MIN,
    REACTION_TIME_MAX,
    REACTION_TIME_MIN,
    BotGenome,
)

GENE_RANGES = (
    (PADDLE_SPEED_MIN, PADDLE_SPEED_MAX),
    (REACTION_TIME_MIN, REACTION_TIME_MAX),
    (MOVEMENT_THRESHOLD_MIN, MOVEMENT_THRESHOLD_MAX),
)


def _validated_rate(value):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError("mutation_rate must be a real number")
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("mutation_rate must be finite and between 0 and 1")
    return value


def _validated_sigma(value):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError("mutation_sigma must be a real number")
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError("mutation_sigma must be finite and positive")
    return value


def mutate_genome(
    genome: BotGenome,
    rng: random.Random,
    *,
    mutation_rate: float,
    mutation_sigma: float,
) -> BotGenome:
    if not isinstance(genome, BotGenome):
        raise TypeError("genome must be a BotGenome")

    mutation_rate = _validated_rate(mutation_rate)
    mutation_sigma = _validated_sigma(mutation_sigma)
    if mutation_rate == 0:
        return genome

    mutated_vector = []
    for value, (minimum, maximum) in zip(genome.to_vector(), GENE_RANGES):
        if rng.random() < mutation_rate:
            noise = rng.gauss(0, mutation_sigma * (maximum - minimum))
            value = min(maximum, max(minimum, value + noise))
        mutated_vector.append(value)

    return BotGenome.from_vector(mutated_vector)
