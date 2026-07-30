import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pygame

from ga.artifacts import CSV_HEADER
from ga.genome import BotGenome
from game.utils import SCREEN_H, SCREEN_W
from tools.capture_screenshots import (
    SCREENSHOT_DT,
    SCREENSHOT_SEED,
    SCREENSHOT_STEPS,
    _save_screen,
    main,
)

INITIAL_GENOME = BotGenome(260.0, 0.0, 8.0)
FINAL_GENOME = BotGenome(300.0, 0.1, 5.0)


def write_artifacts(root, final_genome=FINAL_GENOME):
    (root / "models").mkdir()
    (root / "logs").mkdir()
    (root / "models" / "best_bot.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "genome": final_genome.to_dict(),
            }
        ),
        encoding="utf-8",
    )
    rows = (
        (0, 1, 0, -1, *INITIAL_GENOME.to_vector()),
        (1, 2, 1, 0, *FINAL_GENOME.to_vector()),
    )
    (root / "logs" / "generations.csv").write_text(
        ",".join(CSV_HEADER)
        + "\n"
        + "\n".join(
            ",".join(str(value) for value in row)
            for row in rows
        )
        + "\n",
        encoding="utf-8",
    )


class ScreenshotCaptureTests(unittest.TestCase):
    def test_real_game_creates_three_nonempty_900_by_690_png_files(self):
        random_state = random.getstate()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_artifacts(root)
            capture_states = []

            def save_screen(game, path):
                capture_states.append(
                    (
                        path.name,
                        game.difficulty.ball_speed_multiplier,
                        game.difficulty.paddle_height,
                        game.difficulty.auto_enabled,
                    )
                )
                _save_screen(game, path)

            with patch(
                "tools.capture_screenshots.PROJECT_ROOT",
                root,
            ), patch(
                "tools.capture_screenshots._save_screen",
                side_effect=save_screen,
            ):
                main()

            screenshot_directory = root / "docs" / "screenshots"
            paths = (
                screenshot_directory / "menu.png",
                screenshot_directory / "generation-0.png",
                screenshot_directory / "generation-final.png",
            )
            for path in paths:
                with self.subTest(path=path.name):
                    self.assertTrue(path.is_file())
                    image = pygame.image.load(path)
                    self.assertEqual(image.get_size(), (SCREEN_W, SCREEN_H))
                    colors = pygame.transform.average_color(image)
                    self.assertNotEqual(colors[:3], (0, 0, 0))
            self.assertEqual(
                capture_states,
                [
                    ("menu.png", 1.0, 90, False),
                    ("generation-0.png", 1.0, 90, False),
                    ("generation-final.png", 1.0, 90, False),
                ],
            )
            first_capture = {
                path.name: path.read_bytes()
                for path in paths
            }

            with patch(
                "tools.capture_screenshots.PROJECT_ROOT",
                root,
            ):
                main()

            self.assertEqual(
                {
                    path.name: path.read_bytes()
                    for path in paths
                },
                first_capture,
            )

        self.assertEqual(random.getstate(), random_state)

    def test_fixed_capture_sequence_uses_game_api(self):
        game = MagicMock()
        game.screen = pygame.Surface((SCREEN_W, SCREEN_H))
        records = (MagicMock(), MagicMock(), MagicMock())
        records[-1].genome = FINAL_GENOME

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch(
                "tools.capture_screenshots.PROJECT_ROOT",
                root,
            ), patch(
                "tools.capture_screenshots.load_best_genome",
                return_value=FINAL_GENOME,
            ), patch(
                "tools.capture_screenshots.load_generation_history",
                return_value=records,
            ), patch(
                "tools.capture_screenshots.Game",
                return_value=game,
            ), patch(
                "tools.capture_screenshots.pygame.image.save"
            ) as save:
                main()

        self.assertEqual(SCREENSHOT_SEED, 20260728)
        self.assertEqual(SCREENSHOT_STEPS, 180)
        self.assertEqual(SCREENSHOT_DT, 1 / 60)
        self.assertEqual(game.draw.call_count, 3)
        self.assertEqual(game.update.call_count, 360)
        self.assertEqual(
            game.update.call_args_list,
            [call(1 / 60)] * 360,
        )
        game.start.assert_called_once_with("botvbot")
        game.change_generation.assert_called_once_with("left", 2)
        self.assertEqual(
            [item.args[1].name for item in save.call_args_list],
            ["menu.png", "generation-0.png", "generation-final.png"],
        )

    def test_model_history_mismatch_is_rejected_before_game(self):
        records = (MagicMock(),)
        records[-1].genome = INITIAL_GENOME

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch(
                "tools.capture_screenshots.PROJECT_ROOT",
                root,
            ), patch(
                "tools.capture_screenshots.load_best_genome",
                return_value=FINAL_GENOME,
            ), patch(
                "tools.capture_screenshots.load_generation_history",
                return_value=records,
            ), patch(
                "tools.capture_screenshots.Game"
            ) as game_class, patch(
                "tools.capture_screenshots.pygame.quit"
            ) as quit_pygame:
                with self.assertRaisesRegex(
                    ValueError,
                    "does not match",
                ):
                    main()

        game_class.assert_not_called()
        quit_pygame.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
