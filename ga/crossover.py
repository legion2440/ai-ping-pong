import random

from .genome import BotGenome


def blend_crossover(
    first: BotGenome,
    second: BotGenome,
    rng: random.Random,
) -> BotGenome:
    child_vector = [
        (alpha := rng.random()) * first_gene
        + (1 - alpha) * second_gene
        for first_gene, second_gene in zip(
            first.to_vector(),
            second.to_vector(),
        )
    ]
    return BotGenome.from_vector(child_vector)
