# AI Ping Pong

## Current status

This repository currently contains a visual Pygame prototype with Human vs
Bot and Bot vs Bot modes.

The current `Paddle.track()` method is a temporary fixed-speed controller.
The genetic algorithm is not connected yet.

## Requirements

- Python 3.13 or another version compatible with Pygame 2.6.1
- Pygame 2.6.1

## Installation

Create and activate a virtual environment, then install the pinned
dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Running the game

The recommended command is:

```powershell
python -m game.main
```

Direct script execution is also supported:

```powershell
python game/main.py
```

## Controls

- Move the human paddle with the mouse while the pointer is over the court.
- Use `W`/`S` or the up/down arrow keys to move the human paddle.
- Press `Esc` during a match to return to the menu.
- Close the window to exit.

## Repository structure

```text
ai-ping-pong/
├── game/       # Pygame frontend, entities, and shared constants
├── ga/         # Placeholder for the future genetic algorithm
├── logs/       # Future training logs
├── models/     # Future saved bot parameters
├── tests/      # Test package
├── requirements.txt
└── README.md
```

## Planned genetic algorithm integration

A future step will replace the temporary `Paddle.track()` controller with
behavior driven by evolved bot parameters. Selection, crossover, mutation,
fitness evaluation, training logs, and model persistence are not implemented
at the current stage.
