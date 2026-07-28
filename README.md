# AI Ping Pong

## Current status

This repository currently contains a visual Pygame prototype with Human vs
Bot and Bot vs Bot modes. Match state and physics are separated into
`game/simulation.py`, which can run without creating a window.

Bot behavior is parameterized by paddle speed, reaction time, and movement
threshold. The UI currently uses a baseline genome matching the original bot
behavior as the fixed training opponent. Headless training evolves an
in-memory random population and saves deterministic progress and model
artifacts. The frontend loads those artifacts to replay trained bots, but does
not run training itself.

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

By default, the frontend loads:

- `models/best_bot.json` for Human vs Bot
- `logs/generations.csv` for Bot vs Bot generation replay

Human vs Bot uses the saved global best genome. Bot vs Bot compares the
selected generation champion on the left with generation `0` on the right.
Use the left and right arrow keys to change the selected generation. This is a
visual replay, not formal evidence that a later generation outperforms an
earlier one.

Custom artifacts can be supplied explicitly:

```powershell
python -m game.main `
    --model-path models/best_bot.json `
    --generations-path logs/generations.csv
```

Canonical defaults are resolved from the repository root. Explicit relative
paths are resolved from the directory where the command was invoked, while
absolute paths are used unchanged. Missing, malformed, or mutually
inconsistent artifacts produce an explicit CLI error before Pygame opens a
window; there is no baseline fallback.

## Headless match evaluation

Run a deterministic bot-vs-bot match without creating a window:

```powershell
python -m game.match_runner --seed 20260728 --left 260,0,8 --right 300,0.1,12
```

Direct script execution is also supported:

```powershell
python game/match_runner.py --seed 20260728
```

The command prints one JSON object containing the score, returns by each bot,
longest rally, winner, simulated duration, and termination reason. The seed
makes repeated evaluations with the same genomes and configuration
reproducible.

## Genetic algorithm training

Run deterministic headless training:

```powershell
python -m ga.genetic_algorithm --population-size 8 --generations 3
```

Direct script execution is also supported:

```powershell
python ga/genetic_algorithm.py --population-size 8 --generations 3
```

Each candidate plays the fixed baseline twice for every match seed: first as
the left bot and then as the right bot. Fitness is maximized and calculated
for each match as:

```text
score_weight * (candidate_score - opponent_score)
    + return_weight * candidate_returns
```

The final fitness is the mean across all `2 * len(match_seeds)` matches.
Negative fitness is valid. The evolutionary cycle uses tournament selection,
per-gene blend crossover, per-gene Gaussian mutation, and direct elitism.

Default training parameters:

- Evolution seed: `20260728`
- Population size: `16`
- Evaluated generations: `8`
- Elite count: `2`
- Tournament size: `3`
- Crossover rate: `0.8`
- Mutation rate: `0.2`
- Mutation sigma: `0.10` of each gene's full range
- Match seeds: `20260728,20260729`
- Match limit: `1800` steps or `3` points
- Baseline opponent: `260,0,8`
- Score weight: `100.0`
- Return weight: `1.0`

The evolution seed controls initial genomes, selection, crossover, and
mutation. Match seeds independently control match physics. Reusing all
arguments produces the same result without changing Python's global random
state. The command prints one JSON object to stdout containing the best genome
and the in-memory best/mean/worst fitness history for every evaluated
generation.

### Training output and artifacts

During training, one progress line per generation is written to stderr. The
final machine-readable result remains one JSON line in stdout. A successful
run writes these files by default:

- `logs/generations.csv`
- `models/best_bot.json`

Relative artifact paths are resolved from the directory where training was
invoked. Override them with `--log-path` and `--model-path`.

The CSV contains one row per generation with these columns:

```text
generation,best_fitness,mean_fitness,worst_fitness,paddle_speed,reaction_time,movement_threshold
```

The JSON model uses schema version `1` and contains the global best fitness,
the best genome, the complete evolution config, and the complete fitness
config. Saving this reusable model is an implemented bonus; it is not yet
loaded by the GUI.

Suppress progress while still saving artifacts:

```powershell
python -m ga.genetic_algorithm --quiet
```

Run without creating either artifact:

```powershell
python -m ga.genetic_algorithm --no-artifacts --quiet
```

Load and validate a saved genome programmatically:

```python
from ga.artifacts import load_best_genome

genome = load_best_genome("models/best_bot.json")
```

## Controls

- Move the human paddle with the mouse while the pointer is over the court.
- Use `W`/`S` or the up/down arrow keys to move the human paddle.
- In Bot vs Bot, use the left/right arrow keys to change generation.
- Press `Esc` during a match to return to the menu.
- Close the window to exit.

## Repository structure

```text
ai-ping-pong/
├── game/       # Pygame frontend, controllers, simulation, and entities
├── ga/         # GA, training CLI, and artifact serialization
├── logs/       # Canonical per-generation fitness report
├── models/     # Canonical saved best genome
├── tests/      # Test package
├── requirements.txt
└── README.md
```

## Planned training visualization and integration

The following items are intentionally not implemented yet:

- A fitness chart
- Training inside the GUI
- Training screenshots or GIFs
- Evidence of improvement from a long training run
- Late-generation versus early-generation evaluation
