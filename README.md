# AI Ping Pong

## Current status

This repository contains a visual Pygame frontend with Human vs Bot and Bot vs
Bot modes. Match state and physics are separated into `game/simulation.py`,
which can run without creating a window. Training is performed headlessly and
separately from the GUI.

Bot behavior is parameterized by paddle speed, reaction time, and movement
threshold. The frontend loads the canonical trained model and its 24-generation
history: Human vs Bot uses the saved global best, while Bot vs Bot replays
generation champions against generation `0`. The `260,0,8` baseline is the
fixed training and evaluation opponent; it is not the bot loaded by the GUI.

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

### Canonical training run

The committed model and generation history were produced by a larger
deterministic run. These parameters describe the canonical artifacts, not the
CLI defaults above:

- Evolution seed: `20260730`
- Population size: `32`
- Evaluated generations: `24`
- Elite count: `4`
- Tournament size: `4`
- Crossover rate: `0.8`
- Mutation rate: `0.2`
- Mutation sigma: `0.1` of each gene's full range
- Training seeds: `2000,2001,2002,2003,2004,2005,2006,2007`
- Match limit: `3600` steps or `5` points
- Baseline opponent: `260,0,8`
- Score weight: `100.0`
- Return weight: `1.0`

Promoted best genome:

- Paddle speed: `420.0`
- Reaction time: `0.039498692275418835`
- Movement threshold: `29.790193846648812`
- Training fitness: `218.375`

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
config. Saving this reusable model is an implemented bonus, and the frontend
loads it for Human vs Bot.

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

## Deterministic evaluation

Reproduce the canonical locked evaluation and its fitness chart:

```powershell
python -m ga.evaluation
```

The locked seeds `1000..1019` were not used during training. Every evaluated
genome plays once on the left and once on the right for each seed. Training
mean fitness is read directly from the canonical CSV; held-out fitness comes
from real matches against the fixed baseline. The final champion is also
evaluated directly against generation `0`.

A GUI replay is useful for inspection, but is not formal evidence of
improvement. The deterministic numerical report provides that evidence:

| Metric | Generation 0 | Generation 23 | Result |
| --- | ---: | ---: | ---: |
| Training mean fitness | -144.814453125 | 198.83984375 | +343.654296875 |
| Held-out fitness | 155.05 | 182.225 | +27.175 |
| Final vs initial | — | 13 W / 27 D / 0 L | 13:0 points |

[Full deterministic evaluation report](reports/evaluation.json)

![Training and held-out fitness by generation](docs/fitness_progress.svg)

The chart shows training best, training mean, and held-out champion fitness
for every generation. The saved history contains generation champions rather
than complete historical populations, so held-out evaluation is available
for those champions.

## Frontend screenshots

![Main menu](docs/screenshots/menu.png)

![Generation 0 replay](docs/screenshots/generation-0.png)

![Final generation replay](docs/screenshots/generation-final.png)

In the final replay, generation `23` plays against generation `0`. The
screenshots can be regenerated with:

```powershell
python -m tools.capture_screenshots
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
├── docs/       # Fitness chart and frontend screenshots
├── game/       # Pygame frontend, controllers, simulation, and entities
├── ga/         # GA, training, evaluation, and artifact serialization
├── logs/       # Canonical per-generation fitness history
├── models/     # Canonical saved best genome
├── reports/    # Deterministic locked evaluation
├── tests/      # Test package
├── tools/      # Screenshot capture utility
├── requirements.txt
└── README.md
```

## Planned integration

The following items are intentionally not implemented yet:

- Training inside the GUI
- API control
- Gradual difficulty adjustment
- GIF recording
