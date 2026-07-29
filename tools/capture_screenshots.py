import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import random
from pathlib import Path

import pygame

from ga.artifacts import load_best_genome, load_generation_history
from game.main import BOTVBOT, Game

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOT_SEED = 20260728
SCREENSHOT_STEPS = 180
SCREENSHOT_DT = 1 / 60


def _save_screen(game, path):
    game.draw()
    pygame.image.save(game.screen, path)


def main():
    model_path = PROJECT_ROOT / "models" / "best_bot.json"
    history_path = PROJECT_ROOT / "logs" / "generations.csv"
    output_directory = PROJECT_ROOT / "docs" / "screenshots"
    random_state = random.getstate()

    try:
        best_genome = load_best_genome(model_path)
        records = load_generation_history(history_path)
        if best_genome != records[-1].genome:
            raise ValueError(
                "best model genome does not match the final "
                "generation champion"
            )

        output_directory.mkdir(parents=True, exist_ok=True)
        random.seed(SCREENSHOT_SEED)
        game = Game(best_genome, records)

        _save_screen(game, output_directory / "menu.png")

        game.start(BOTVBOT)
        for _ in range(SCREENSHOT_STEPS):
            game.update(SCREENSHOT_DT)
        _save_screen(game, output_directory / "generation-0.png")

        game.change_generation(len(records) - 1)
        for _ in range(SCREENSHOT_STEPS):
            game.update(SCREENSHOT_DT)
        _save_screen(game, output_directory / "generation-final.png")
    finally:
        random.setstate(random_state)
        pygame.quit()


if __name__ == "__main__":
    main()
